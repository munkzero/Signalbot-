"""
Monero Wallet Auto-Setup and Management
Handles wallet creation, RPC startup, and connection management
"""

import os
import subprocess
import time
import requests
import socket
import threading
import shutil
import signal
import glob
from pathlib import Path
from typing import Optional, Tuple, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Configuration constants
RESTORE_HEIGHT_OFFSET = 1000  # Blocks to subtract from current height for restore
NEW_WALLET_RPC_TIMEOUT = 180  # Seconds to wait for new wallet RPC (3 minutes)
EXISTING_WALLET_RPC_TIMEOUT = 60  # Seconds to wait for existing wallet RPC

# Wallet health check constants
# This threshold is used to detect wallets stuck at restore_height=0
# A healthy wallet cache should not have this pattern near the restore_height field
WALLET_HEALTH_ZERO_THRESHOLD = 15  # Number of consecutive zeros indicating height 0

# Maximum expected cache file size in MB
# A healthy cache file is typically under 5-10MB. Files over 50MB may indicate
# a wallet trying to sync from block 0, which would take hours and create huge cache files.
# This is used as a warning threshold, not a hard limit.
MAX_HEALTHY_CACHE_SIZE_MB = 50


class WalletCreationError(Exception):
    """Raised when wallet creation or setup fails"""
    pass


def cleanup_zombie_rpc_processes():
    """
    DEPRECATED: Kill any orphaned monero-wallet-rpc processes from previous runs.
    
    This function is deprecated and should not be used. It kills ALL monero-wallet-rpc
    processes indiscriminately, which can cause issues.
    
    Use WalletSetupManager._cleanup_orphaned_rpc() instead, which intelligently
    identifies and removes only truly orphaned processes.
    
    This prevents wallet lock file issues when bot was force-killed
    and didn't clean up properly.
    """
    try:
        logger.warning("⚠ cleanup_zombie_rpc_processes() is deprecated - use WalletSetupManager._cleanup_orphaned_rpc() instead")
        logger.info("🔍 Checking for zombie RPC processes...")
        
        # Find monero-wallet-rpc processes
        result = subprocess.run(
            ["pgrep", "-f", "monero-wallet-rpc"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            logger.warning(f"⚠ Found {len(pids)} zombie RPC process(es)")
            
            for pid in pids:
                try:
                    logger.info(f"🗑 Killing zombie RPC process (PID: {pid})")
                    subprocess.run(["kill", "-9", pid], check=True)
                except subprocess.CalledProcessError:
                    logger.warning(f"⚠ Could not kill process {pid} (may already be dead)")
            
            logger.info("✓ Zombie processes cleaned up")
            
            # Wait a moment for file locks to release
            time.sleep(2)
        else:
            logger.info("✓ No zombie processes found")
            
    except FileNotFoundError:
        # pgrep not available (Windows?)
        logger.debug("pgrep command not available, skipping zombie cleanup")
        
    except Exception as e:
        logger.warning(f"⚠ Could not cleanup zombie processes: {e}")


def get_current_blockchain_height(daemon_address: str, daemon_port: int) -> Optional[int]:
    """
    Get the current blockchain height from the Monero daemon.
    
    Args:
        daemon_address: Daemon address
        daemon_port: Daemon port
        
    Returns:
        Current blockchain height or None if failed
    """
    try:
        logger.debug(f"Getting blockchain height from {daemon_address}:{daemon_port}...")
        response = requests.get(
            f"http://{daemon_address}:{daemon_port}/get_height",
            timeout=10
        )
        
        if response.status_code == 200:
            height = response.json().get("height")
            if height:
                logger.info(f"✓ Current blockchain height: {height:,}")
                return height
        
        logger.warning(f"⚠ Failed to get blockchain height (status: {response.status_code})")
        return None
        
    except requests.RequestException as e:
        logger.warning(f"⚠ Could not reach daemon: {e}")
        return None
    except Exception as e:
        logger.warning(f"⚠ Error getting blockchain height: {e}")
        return None


def wait_for_rpc_ready(port=18083, max_wait=60, retry_interval=2, is_new_wallet=False):
    """
    Wait for wallet RPC to be ready to accept connections.
    
    Polls RPC with simple requests until it responds successfully.
    This ensures the full startup sequence has completed:
    1. Process started
    2. Wallet loaded
    3. Daemon connected
    4. Initial sync started
    5. RPC server listening ✓
    
    Args:
        port: RPC port to connect to
        max_wait: Maximum seconds to wait before giving up
        retry_interval: Seconds between connection attempts
        is_new_wallet: If True, use extended timeout (180s) for initial sync
        
    Returns:
        True if RPC is ready, False if timeout
    """
    # Use extended timeout for new wallets
    if is_new_wallet:
        max_wait = NEW_WALLET_RPC_TIMEOUT
        logger.info(f"⏳ New wallet - initial sync may take 2-3 minutes...")
    
    start_time = time.time()
    attempt = 0
    
    logger.info(f"⏳ Waiting for RPC to start (max {max_wait}s)...")
    
    while time.time() - start_time < max_wait:
        attempt += 1
        elapsed = time.time() - start_time
        
        try:
            # Try simple RPC call
            response = requests.post(
                f"http://localhost:{port}/json_rpc",
                json={"jsonrpc":"2.0","id":"0","method":"get_height"},
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info(f"✓ RPC ready after {attempt} attempts ({elapsed:.1f}s)")
                return True
                
        except (requests.ConnectionError, requests.Timeout) as e:
            # RPC not ready yet - this is expected
            logger.debug(f"⏳ Waiting for RPC... (attempt {attempt}, {elapsed:.1f}s)")
            time.sleep(retry_interval)
            
        except Exception as e:
            logger.warning(f"⚠ Unexpected error checking RPC: {e}")
            time.sleep(retry_interval)
    
    logger.error(f"❌ RPC did not respond after {max_wait}s")
    return False


def monitor_sync_progress(port=18083, update_interval=10, max_stall_time=60):
    """
    Monitor and display wallet sync progress with real-time updates.
    
    Shows:
    - Current sync percentage
    - Blocks synced vs total blocks
    - Blocks remaining
    - Stall detection
    
    Args:
        port: RPC port
        update_interval: Seconds between progress updates
        max_stall_time: Seconds without progress before warning
        
    Returns:
        True when sync complete, False on error
    """
    logger.info("🔄 Starting wallet sync monitor...")
    
    last_height = 0
    last_update_time = time.time()
    stalled_warnings = 0
    no_progress_iterations = 0
    
    while True:
        try:
            # Get wallet height
            height_response = requests.post(
                f"http://localhost:{port}/json_rpc",
                json={"jsonrpc":"2.0","id":"0","method":"get_height"},
                timeout=5
            )
            
            if height_response.status_code != 200:
                logger.warning("⚠ Failed to get wallet height")
                time.sleep(update_interval)
                continue
            
            wallet_height = height_response.json().get("result", {}).get("height", 0)
            
            # For wallet RPC, we can't easily get daemon height directly
            # We monitor progress by checking if height increases over time
            # If height stops increasing for too long, wallet is likely synced or stalled
            
            # Check if we're making progress
            if wallet_height == last_height:
                no_progress_iterations += 1
                time_stalled = time.time() - last_update_time
                
                # If no progress for a while, assume sync is complete or stalled
                if no_progress_iterations >= 3:  # 3 iterations with no progress
                    if time_stalled > max_stall_time:
                        stalled_warnings += 1
                        logger.warning(
                            f"⚠ No sync progress for {time_stalled:.0f}s at height {wallet_height:,}"
                        )
                        
                        if stalled_warnings > 3:
                            logger.warning("⚠ Sync appears stalled or already complete")
                            logger.info(f"✓ Wallet height stable at {wallet_height:,}")
                            return True
                    else:
                        # Just stable, probably synced
                        logger.info(f"✓ Wallet height stable at {wallet_height:,} - assuming synced")
                        return True
            else:
                # Progress made
                no_progress_iterations = 0
                last_update_time = time.time()
                stalled_warnings = 0
                
                # Calculate sync speed
                blocks_synced = wallet_height - last_height
                
                # Progress update - we don't know total, so just show current height
                logger.info(
                    f"🔄 Syncing wallet... Height: {wallet_height:,} "
                    f"(+{blocks_synced} blocks in {update_interval}s)"
                )
            
            last_height = wallet_height
            time.sleep(update_interval)
            
        except requests.RequestException as e:
            logger.debug(f"Connection error during sync monitor: {e}")
            time.sleep(update_interval)
            
        except Exception as e:
            logger.error(f"❌ Error monitoring sync: {e}")
            time.sleep(update_interval)


def check_existing_wallet(wallet_path: str) -> bool:
    """
    Check if wallet files already exist
    
    Args:
        wallet_path: Path to wallet file (without .keys extension)
        
    Returns:
        True if wallet exists
    """
    keys_file = f"{wallet_path}.keys"
    
    if os.path.exists(keys_file):
        logger.info(f"✓ Found existing wallet: {os.path.basename(wallet_path)}")
        return True
    
    return False


def validate_wallet_files(wallet_path: str) -> bool:
    """
    Validate that wallet has both required files:
    - wallet_name.keys (private keys - CRITICAL)
    - wallet_name (cache - can be rebuilt)
    
    Args:
        wallet_path: Path to wallet file (without .keys extension)
        
    Returns:
        True if wallet files are valid
    """
    keys_file = f"{wallet_path}.keys"
    cache_file = wallet_path
    
    # Keys file is CRITICAL
    if not os.path.exists(keys_file):
        logger.error(f"❌ Missing critical file: {keys_file}")
        return False
    
    # Cache file can be rebuilt, just warn
    if not os.path.exists(cache_file):
        logger.warning(f"⚠ Missing cache file: {cache_file} (will be rebuilt on sync)")
    
    logger.info(f"✓ Wallet files validated: {os.path.basename(wallet_path)}")
    return True


def cleanup_orphaned_wallets(wallet_dir: str):
    """
    Remove orphaned wallet cache files (files without matching .keys)
    
    Example: shop_wallet_1770875498 exists but shop_wallet_1770875498.keys doesn't
    
    Args:
        wallet_dir: Directory containing wallet files
    """
    if not os.path.exists(wallet_dir):
        return
    
    logger.info("Checking for orphaned wallet files...")
    
    cleaned = []
    
    for filename in os.listdir(wallet_dir):
        filepath = os.path.join(wallet_dir, filename)
        
        # Skip directories, .keys files, backups
        if os.path.isdir(filepath) or filename.endswith(".keys") or "backup" in filename:
            continue
        
        # Check if this looks like a wallet file
        if filename.startswith("shop_wallet"):
            keys_file = f"{filepath}.keys"
            
            if not os.path.exists(keys_file):
                logger.warning(f"⚠ Found orphaned wallet cache: {filename}")
                logger.info(f"🗑 Removing orphaned file (no .keys file exists)")
                
                try:
                    os.remove(filepath)
                    cleaned.append(filename)
                except Exception as e:
                    logger.error(f"Failed to remove {filename}: {e}")
    
    if cleaned:
        logger.info(f"✓ Cleaned up {len(cleaned)} orphaned wallet file(s)")
    else:
        logger.info("✓ No orphaned wallet files found")


def check_wallet_health(wallet_path: str) -> Tuple[bool, Optional[str]]:
    """
    Check if existing wallet cache is healthy or corrupted.
    
    Detects wallets stuck at restore_height=0 by checking the cache file for patterns
    indicating the wallet would try to sync from genesis block (block 0).
    
    The heuristic looks for the 'restore_height' string in the binary cache followed
    by a high number of null bytes, which indicates height 0 in little-endian format.
    Also checks for abnormally large cache files which may indicate a sync from block 0.
    
    Args:
        wallet_path: Path to wallet file (without .keys extension)
        
    Returns:
        Tuple of (is_healthy, reason_if_unhealthy)
    """
    cache_file = Path(wallet_path)
    
    # Check if cache exists
    if not cache_file.exists():
        # No cache is fine - it will be rebuilt
        logger.debug("✓ No cache file found (will be rebuilt on first sync)")
        return True, None
    
    try:
        # Check file size first - cache shouldn't be huge for normal operation
        file_size_mb = cache_file.stat().st_size / (1024 * 1024)
        if file_size_mb > MAX_HEALTHY_CACHE_SIZE_MB:
            logger.warning(f"⚠ Large cache file detected: {file_size_mb:.1f}MB")
            logger.warning("   This may indicate wallet is syncing from block 0")
        
        # Read first few KB of cache to check for restore_height markers
        # The cache file is binary, but we can scan for patterns
        with open(cache_file, 'rb') as f:
            # Read first 10KB which should contain header info
            data = f.read(10240)
            
            # Look for restore_height field followed by value 0
            # In the binary cache, this appears as 'restore_height' string followed by null bytes
            # Pattern: restore_height\x00\x00\x00\x00 (4 zero bytes = height 0 in little-endian)
            if b'restore_height' in data:
                # Find position of restore_height
                pos = data.find(b'restore_height')
                # Check bytes AFTER the 'restore_height' string for zeros
                # Skip past the string itself (14 bytes)
                after_marker = data[pos + 14:pos + 64]  # Check 50 bytes after marker
                
                # Count consecutive zeros after restore_height marker
                consecutive_zeros = 0
                for byte in after_marker:
                    if byte == 0:
                        consecutive_zeros += 1
                    else:
                        break
                
                # If we see many consecutive zeros, likely restore_height=0
                if consecutive_zeros > WALLET_HEALTH_ZERO_THRESHOLD:
                    logger.warning("⚠ DETECTED: Wallet cache corrupted (restore_height=0)")
                    logger.warning(f"   Found {consecutive_zeros} consecutive zero bytes after restore_height marker")
                    return False, "Corrupted cache detected (restore_height=0)"
        
        # If we got here, cache looks okay
        logger.debug("✓ Wallet cache appears healthy")
        return True, None
        
    except Exception as e:
        logger.warning(f"⚠ Could not check wallet health: {e}")
        # Err on side of caution - assume healthy to avoid unnecessary recreation
        return True, None


def backup_wallet(wallet_path: str) -> bool:
    """
    Create backup of wallet files before recreation.
    
    Args:
        wallet_path: Path to wallet file (without .keys extension)
        
    Returns:
        True if backup successful
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        wallet_name = os.path.basename(wallet_path)
        
        # Backup directory
        backup_dir = os.path.join(os.path.dirname(wallet_path), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        
        files_backed_up = []
        
        # Backup keys file (most important)
        keys_file = f"{wallet_path}.keys"
        if os.path.exists(keys_file):
            backup_keys = os.path.join(backup_dir, f"{wallet_name}_{timestamp}.keys.backup")
            shutil.copy2(keys_file, backup_keys)
            files_backed_up.append("keys")
        
        # Backup cache file
        if os.path.exists(wallet_path):
            backup_cache = os.path.join(backup_dir, f"{wallet_name}_{timestamp}.backup")
            shutil.copy2(wallet_path, backup_cache)
            files_backed_up.append("cache")
        
        # Backup address file if exists
        address_file = f"{wallet_path}.address.txt"
        if os.path.exists(address_file):
            backup_address = os.path.join(backup_dir, f"{wallet_name}_{timestamp}.address.txt.backup")
            shutil.copy2(address_file, backup_address)
            files_backed_up.append("address")
        
        if files_backed_up:
            logger.info(f"✓ Wallet backed up: {', '.join(files_backed_up)} files")
            logger.info(f"  Backup location: {backup_dir}")
            return True
        else:
            logger.warning("⚠ No wallet files found to backup")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to backup wallet: {e}")
        return False


def delete_corrupted_cache(wallet_path: str) -> bool:
    """
    Delete corrupted wallet cache file, keeping keys file safe.
    
    This is specifically for fixing corrupted cache files (e.g., restore_height=0)
    without recreating the entire wallet. Only the cache file is deleted,
    preserving the .keys file which contains the actual wallet.
    
    Args:
        wallet_path: Path to wallet (without extension)
        
    Returns:
        True if cache deleted successfully or doesn't exist
    """
    cache_file = Path(wallet_path)
    keys_file = Path(f"{wallet_path}.keys")
    
    # Safety check - keys file MUST exist
    if not keys_file.exists():
        logger.error("❌ Keys file not found - cannot delete cache!")
        logger.error("   Aborting to prevent data loss")
        return False
    
    # Delete cache file if it exists
    if cache_file.exists():
        try:
            logger.warning(f"🗑 Deleting corrupted cache: {cache_file.name}")
            cache_file.unlink()
            logger.info("✓ Corrupted cache deleted")
            logger.info(f"✓ Keys file preserved: {keys_file.name}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to delete cache: {e}")
            return False
    
    # Cache doesn't exist - that's fine
    logger.debug("Cache file doesn't exist (nothing to delete)")
    return True


def delete_wallet_files(wallet_path: str) -> bool:
    """
    Delete wallet files (after backup).
    
    Args:
        wallet_path: Path to wallet file (without .keys extension)
        
    Returns:
        True if deletion successful
    """
    try:
        files_deleted = []
        
        # Delete keys file
        keys_file = f"{wallet_path}.keys"
        if os.path.exists(keys_file):
            os.remove(keys_file)
            files_deleted.append("keys")
        
        # Delete cache file
        if os.path.exists(wallet_path):
            os.remove(wallet_path)
            files_deleted.append("cache")
        
        # Delete address file if exists
        address_file = f"{wallet_path}.address.txt"
        if os.path.exists(address_file):
            os.remove(address_file)
            files_deleted.append("address")
        
        if files_deleted:
            logger.info(f"✓ Deleted old wallet files: {', '.join(files_deleted)}")
            return True
        else:
            logger.debug("No wallet files to delete")
            return True
            
    except Exception as e:
        logger.error(f"❌ Failed to delete wallet files: {e}")
        return False


def extract_seed_from_output(output: str) -> Optional[str]:
    """
    Extract seed phrase from monero-wallet-cli output
    
    Args:
        output: stdout from wallet creation command
        
    Returns:
        Seed phrase (25 words) or None if not found
    """
    if 'seed' in output.lower():
        lines = output.split('\n')
        for i, line in enumerate(lines):
            if 'seed' in line.lower() and i + 1 < len(lines):
                # Seed is usually on next line or same line
                potential_seed = lines[i + 1].strip()
                if len(potential_seed.split()) == 25:
                    return potential_seed
    return None


def display_seed_phrase(seed: str):
    """
    Display seed phrase in a prominent formatted box.
    
    Args:
        seed: 25-word seed phrase
        
    Raises:
        ValueError: If seed doesn't have exactly 25 words
    """
    # Split seed into words for better formatting
    words = seed.split()
    
    # Validate seed has exactly 25 words (Monero standard)
    if len(words) != 25:
        logger.error(f"❌ Invalid seed phrase: expected 25 words, got {len(words)}")
        raise ValueError(f"Invalid seed phrase: expected 25 words, got {len(words)}")
    
    # Format seed phrase into 3 lines of 8 words + 1 word on last line
    line1 = " ".join(words[0:8])
    line2 = " ".join(words[8:16])
    line3 = " ".join(words[16:24])
    line4 = words[24]
    
    # Box configuration
    box_width = 60
    
    # Helper function to pad text to fit in box
    def pad_line(text: str, width: int = box_width - 2) -> str:
        """Pad text to fit within box width (accounting for borders)"""
        return text.ljust(width)
    
    # Print to console (not logger to avoid logging sensitive data)
    print("")
    print("╔" + "═" * box_width + "╗")
    
    # Title line
    title = "🔑 NEW WALLET CREATED - SAVE YOUR SEED PHRASE!"
    print("║  " + pad_line(title, box_width - 4) + "  ║")
    
    print("║" + " " * box_width + "║")
    
    # Seed phrase lines
    print("║  " + pad_line(line1, box_width - 4) + "  ║")
    print("║  " + pad_line(line2, box_width - 4) + "  ║")
    print("║  " + pad_line(line3, box_width - 4) + "  ║")
    print("║  " + pad_line(line4, box_width - 4) + "  ║")
    
    print("║" + " " * box_width + "║")
    
    # Warning lines
    warning1 = "⚠️  WRITE THIS DOWN! You cannot recover your funds"
    warning2 = "    without this seed phrase!"
    print("║  " + pad_line(warning1, box_width - 4) + "  ║")
    print("║  " + pad_line(warning2, box_width - 4) + "  ║")
    
    print("╚" + "═" * box_width + "╝")
    print("")


class WalletSetupManager:
    """Manages Monero wallet creation and RPC lifecycle"""
    
    def __init__(self, wallet_path: str, daemon_address: str, daemon_port: int, 
                 rpc_port: int = 18083, password: str = ""):
        self.wallet_path = Path(wallet_path)
        self.daemon_address = daemon_address
        self.daemon_port = daemon_port
        self.rpc_port = rpc_port
        self.password = password
        self.rpc_process = None
        self.rpc_pid_file = None
        self.rpc_log_file = None
        self._rpc_log_fd = None
        
    def wallet_exists(self) -> bool:
        """Check if wallet files exist"""
        keys_file = Path(str(self.wallet_path) + ".keys")
        return keys_file.exists()
    
    def _cleanup_wallet_locks(self):
        """Remove stale wallet lock files and kill orphaned RPC processes"""
        try:
            lock_files = list(self.wallet_path.parent.glob("*.keys.lock"))
            
            if lock_files:
                logger.warning(f"⚠ Found {len(lock_files)} stale wallet lock file(s)")
                for lock_file in lock_files:
                    try:
                        lock_file.unlink()
                        logger.info(f"  ✓ Removed: {lock_file.name}")
                    except Exception as e:
                        logger.warning(f"  ✗ Failed to remove {lock_file}: {e}")
            
            # Kill orphaned RPC processes
            try:
                result = subprocess.run(
                    ['pgrep', '-x', 'monero-wallet-rpc'],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    logger.warning("⚠ Found running monero-wallet-rpc process, killing...")
                    subprocess.run(['pkill', '-9', 'monero-wallet-rpc'])
                    time.sleep(2)
                    logger.info("  ✓ Killed orphaned RPC process")
            except Exception as e:
                logger.warning(f"  ⚠ Could not check for orphaned processes: {e}")
                
        except Exception as e:
            logger.warning(f"⚠ Wallet lock cleanup failed: {e}")
    
    def create_wallet(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Create a new Monero wallet with proper error handling
        
        Returns:
            Tuple of (success, wallet_address, seed_phrase)
            
        Raises:
            WalletCreationError: If wallet creation fails
        """
        if self.wallet_exists():
            logger.info(f"Wallet already exists at {self.wallet_path}")
            return True, None, None
        
        logger.info(f"Creating wallet: {self.wallet_path}")
        
        # Ensure directory exists
        self.wallet_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get current blockchain height for restore height
        current_height = get_current_blockchain_height(self.daemon_address, self.daemon_port)
        restore_height = None
        
        if current_height:
            # Set restore height to avoid scanning old blocks
            # The offset (RESTORE_HEIGHT_OFFSET) is intentionally set to 1000 blocks to balance:
            # - Performance: Avoids scanning from genesis (2014), reducing sync time from hours to seconds
            # - Safety: 1000 blocks (~33 hours at 2 min/block) provides reasonable buffer for most use cases
            # Note: For brand new wallets that just received their first transaction, the offset
            # means the wallet will sync from slightly before that transaction occurred
            restore_height = max(0, current_height - RESTORE_HEIGHT_OFFSET)
            logger.info(f"🔧 Creating new wallet with restore height {restore_height:,}...")
        else:
            logger.warning("⚠ Could not get blockchain height, wallet will sync from genesis")
        
        try:
            # Create wallet using monero-wallet-cli
            cmd = [
                'monero-wallet-cli',
                '--generate-new-wallet', str(self.wallet_path),
                '--password', self.password,
                '--mnemonic-language', 'English',
            ]
            
            # Add restore height if available
            if restore_height is not None:
                cmd.extend(['--restore-height', str(restore_height)])
            
            cmd.extend([
                '--command', 'seed',
                '--command', 'address',
                '--command', 'exit'
            ])
            
            # Log password handling for debugging
            logger.debug(f"Creating wallet with password: {'<empty>' if self.password == '' else '<set>'}")
            
            # Provide two empty responses via stdin to handle any password prompts
            # Even with --password "", some versions may prompt - these newlines ensure empty input
            result = subprocess.run(
                cmd,
                input="\n\n",  # Two newlines = empty responses for password and confirmation
                capture_output=True,
                text=True,  # Required for text mode when using string input
                timeout=30
            )
            
            if result.returncode != 0:
                # Capture actual error
                error_msg = result.stderr.strip() or result.stdout.strip()
                raise WalletCreationError(f"Wallet creation failed: {error_msg}")
            
            # Parse output for seed and address using helper function
            output = result.stdout
            seed = extract_seed_from_output(output)
            address = None
            
            # Extract address (starts with 4)
            for line in output.split('\n'):
                line = line.strip()
                if line.startswith('4') and len(line) == 95:
                    address = line
                    break
            
            # Display seed phrase in nice formatted box
            if seed:
                display_seed_phrase(seed)
                # Log a reminder without the actual seed
                logger.warning("⚠️ IMPORTANT: Seed phrase displayed above - save it now!")
            
            logger.info("✓ Wallet created successfully")
            if address:
                logger.info(f"   Address: {address[:20]}...{address[-10:]}")
            
            return True, address, seed
            
        except FileNotFoundError:
            raise WalletCreationError(
                "monero-wallet-cli not found!\n"
                "Install Monero CLI tools:\n"
                "  Ubuntu/Debian: sudo apt install monero\n"
                "  Download: https://www.getmonero.org/downloads/"
            )
        
        except subprocess.TimeoutExpired:
            raise WalletCreationError("Wallet creation timed out (30s)")
        
        except WalletCreationError:
            # Re-raise WalletCreationError as-is
            raise
        
        except Exception as e:
            raise WalletCreationError(f"Unexpected error creating wallet: {str(e)}")
    
    def create_wallet_with_seed(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Create wallet and return seed phrase + address
        This method wraps create_wallet() to ensure reliable seed phrase capture
        
        Returns:
            Tuple of (success, seed_phrase, primary_address)
        """
        logger.info(f"Creating new wallet with RPC at {self.wallet_path}")
        
        if self.wallet_exists():
            logger.warning(f"Wallet already exists at {self.wallet_path}")
            return False, None, None
        
        # Ensure directory exists
        self.wallet_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # First create the wallet using monero-wallet-cli to get seed immediately
            success, address, seed = self.create_wallet()
            
            if not success or not seed:
                logger.error("Failed to create wallet or retrieve seed")
                return False, None, None
            
            logger.info(f"✅ Wallet created with seed successfully!")
            logger.info(f"   Address: {address[:20]}...{address[-10:] if address else ''}")
            logger.info(f"   Seed: {seed[:30]}... (SAVE THIS!)")
            
            return True, seed, address
            
        except Exception as e:
            logger.error(f"Error in create_wallet_with_seed: {e}")
            return False, None, None
    
    def uses_empty_password(self) -> bool:
        """
        Check if wallet uses empty password
        
        Returns:
            True if wallet password is empty string
        """
        return self.password == ""
    
    def unlock_wallet_silent(self) -> bool:
        """
        Unlock wallet without user interaction (for empty passwords)
        Assumes RPC is already running
        
        Returns:
            True if successfully unlocked
        """
        try:
            if not self.uses_empty_password():
                logger.warning("Cannot silent unlock: wallet has a password")
                return False
            
            if not self.test_rpc_connection():
                logger.error("Cannot unlock: RPC is not running")
                return False
            
            # For wallets with empty password, they're already unlocked when RPC starts
            # Just verify we can access the wallet
            response = requests.post(
                f'http://127.0.0.1:{self.rpc_port}/json_rpc',
                json={
                    "jsonrpc": "2.0",
                    "id": "0",
                    "method": "get_address",
                    "params": {"account_index": 0}
                },
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'result' in result:
                    logger.info("✅ Wallet is unlocked (empty password)")
                    return True
            
            logger.error("Failed to verify wallet unlock")
            return False
            
        except Exception as e:
            logger.error(f"Silent unlock failed: {e}")
            return False
    
    def is_rpc_running(self) -> bool:
        """Check if monero-wallet-rpc is running on the specified port"""
        try:
            # Try to connect to RPC port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('127.0.0.1', self.rpc_port))
            sock.close()
            return result == 0
        except:
            return False
    
    def test_rpc_connection(self) -> bool:
        """Test if RPC is responsive via JSON-RPC"""
        try:
            response = requests.post(
                f'http://127.0.0.1:{self.rpc_port}/json_rpc',
                json={"jsonrpc": "2.0", "id": "0", "method": "get_version"},
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def _cleanup_orphaned_rpc(self):
        """Kill orphaned RPC processes on our port.
        
        We always kill processes on our port (even if they match our PID file) because:
        1. We need a proper process handle (self.rpc_process) for lifecycle management
        2. We can't reliably "attach" to an existing process in Python
        3. Restarting ensures clean state and proper initialization
        
        Exception: If it's our currently tracked process (self.rpc_process), we keep it.
        """
        
        try:
            # Check if something is already on our port
            result = subprocess.run(
                ["lsof", "-ti", f":{self.rpc_port}"],
                capture_output=True,
                text=True
            )
            
            if result.stdout:
                pid = int(result.stdout.strip())
                
                # Only exception: if it's our currently tracked process, keep it
                if self.rpc_process and pid == self.rpc_process.pid:
                    logger.debug(f"Port {self.rpc_port} in use by our tracked RPC (PID {pid})")
                    return
                
                # For all other cases (including PIDs from old PID files), kill and restart
                # This ensures we always have a proper process handle
                logger.warning(f"⚠ Found RPC on port {self.rpc_port} (PID {pid}), killing for clean restart...")
                
                # First try graceful termination
                try:
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(2)
                    
                    # Check if process is still alive before SIGKILL
                    try:
                        os.kill(pid, 0)  # Signal 0 checks if process exists
                        # Process still exists, force kill
                        logger.warning(f"Process {pid} didn't terminate gracefully, force killing...")
                        os.kill(pid, signal.SIGKILL)
                        time.sleep(1)  # Give it a moment to die
                    except ProcessLookupError:
                        # Process already terminated
                        logger.debug(f"Process {pid} terminated gracefully")
                except ProcessLookupError:
                    # Process already dead
                    logger.debug(f"Process {pid} already dead")
            
        except FileNotFoundError:
            # lsof not available, try alternative
            self._cleanup_orphaned_rpc_fallback()
        except Exception as e:
            logger.warning(f"Could not check for orphaned RPC: {e}")

    def _cleanup_orphaned_rpc_fallback(self):
        """Fallback cleanup using pgrep/netstat."""
        
        try:
            # Find all monero-wallet-rpc processes
            result = subprocess.run(
                ["pgrep", "-f", "monero-wallet-rpc"],
                capture_output=True,
                text=True
            )
            
            if not result.stdout:
                return
            
            pids = [int(pid) for pid in result.stdout.strip().split('\n')]
            
            for pid in pids:
                # Skip our own process
                if self.rpc_process and pid == self.rpc_process.pid:
                    continue
                
                # Check if this process is using our wallet file
                try:
                    with open(f"/proc/{pid}/cmdline", "r") as f:
                        cmdline = f.read()
                    
                    # If it's using our wallet file, it's probably orphaned
                    if str(self.wallet_path) in cmdline:
                        logger.warning(f"⚠ Found orphaned RPC using our wallet (PID {pid}), killing...")
                        os.kill(pid, signal.SIGTERM)
                        time.sleep(1)
                        try:
                            os.kill(pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                except:
                    # Can't read process info, skip
                    pass
                    
        except Exception as e:
            logger.warning(f"Fallback cleanup failed: {e}")
    
    def _wait_for_rpc_ready(self, timeout: int = 60) -> bool:
        """Wait for RPC to be ready to accept connections."""
        
        url = f"http://127.0.0.1:{self.rpc_port}/json_rpc"
        start_time = time.time()
        attempt = 0
        last_log_time = start_time
        
        logger.info(f"⏳ Waiting for RPC to be ready (timeout: {timeout}s)...")
        logger.info("   ℹ RPC needs to refresh wallet before accepting connections")
        
        while time.time() - start_time < timeout:
            attempt += 1
            elapsed = time.time() - start_time
            
            # Log progress every 15 seconds
            if time.time() - last_log_time >= 15:
                logger.info(f"   Still waiting... ({elapsed:.0f}s elapsed, {timeout - elapsed:.0f}s remaining)")
                last_log_time = time.time()
            
            # Check if process is still alive
            if self.rpc_process and self.rpc_process.poll() is not None:
                logger.error(f"❌ RPC process died (exit code: {self.rpc_process.poll()})")
                return False
            
            try:
                # Try to connect
                response = requests.post(
                    url,
                    json={"jsonrpc": "2.0", "id": "0", "method": "get_balance"},
                    timeout=5
                )
                
                if response.status_code == 200:
                    logger.info(f"✓ RPC ready after {attempt} attempts ({time.time() - start_time:.1f}s)")
                    return True
                    
            except requests.exceptions.ConnectionError:
                # Expected during startup
                pass
            except Exception as e:
                logger.debug(f"RPC check failed (attempt {attempt}): {e}")
            
            time.sleep(2)
        
        logger.error(f"❌ RPC did not become ready within {timeout}s")
        return False
    
    def start_rpc(self, daemon_address: Optional[str] = None, 
                  daemon_port: Optional[int] = None, is_new_wallet: bool = False) -> bool:
        """
        Start monero-wallet-rpc process and track it properly
        
        Args:
            daemon_address: Override default daemon address
            daemon_port: Override default daemon port
            is_new_wallet: True if this is a newly created wallet (uses extended timeout)
            
        Returns:
            True if RPC started successfully OR is already running under our control
        """
        # Check if we already have a running RPC process tracked
        if self.rpc_process and self.rpc_process.poll() is None:
            # Our process is still alive
            logger.debug(f"RPC already running under our control (PID: {self.rpc_process.pid})")
            return True
        
        # Check if port is already in use before attempting cleanup/start.
        if self.is_rpc_running():
            logger.info(f"ℹ Port {self.rpc_port} is already in use - attempting cleanup first")
        
        # Clean up any processes on our port (orphans from previous runs or dead processes)
        # This ensures we always get a fresh start with proper process tracking
        self._cleanup_orphaned_rpc()
        
        # Double-check that cleanup worked - port should be free now
        if self.is_rpc_running():
            logger.error(f"❌ Port {self.rpc_port} still in use after cleanup!")
            self._log_port_diagnostic()
            return False
        
        if not self.wallet_exists():
            logger.error("❌ Cannot start RPC: wallet file doesn't exist")
            return False

        # Check for stale wallet lock files before starting.
        self._cleanup_wallet_locks()
        
        daemon_addr = daemon_address or self.daemon_address
        daemon_port_to_use = daemon_port or self.daemon_port
        
        # Test daemon connectivity first
        logger.info(f"🔍 Testing daemon connectivity: {daemon_addr}:{daemon_port_to_use}")
        try:
            response = requests.post(
                f'http://{daemon_addr}:{daemon_port_to_use}/json_rpc',
                json={"jsonrpc":"2.0","id":"0","method":"get_info"},
                timeout=10
            )
            if response.status_code == 200:
                logger.info("✓ Daemon is reachable")
            else:
                logger.warning(f"⚠ Daemon returned status {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Cannot reach daemon: {e}")
            logger.error("   RPC may take longer to start or fail completely")
            # Don't abort - let RPC try and handle its own retries
        
        # Create PID file path
        self.rpc_pid_file = os.path.join(
            os.path.dirname(str(self.wallet_path)),
            '.rpc.pid'
        )
        self.rpc_log_file = os.path.join(
            os.path.dirname(str(self.wallet_path)),
            '.rpc.log'
        )
        
        logger.info(f"🚀 Starting wallet RPC on port {self.rpc_port}...")
        logger.info(f"  Daemon: {daemon_addr}:{daemon_port_to_use}")
        logger.info(f"  Wallet: {self.wallet_path}")
        
        # Log password handling for debugging
        logger.debug(f"Starting RPC with password: {'<empty>' if self.password == '' else '<set>'}")
        
        try:
            cmd = [
                'monero-wallet-rpc',
                '--daemon-address', f'{daemon_addr}:{daemon_port_to_use}',
                '--rpc-bind-port', str(self.rpc_port),
                '--rpc-bind-ip', '127.0.0.1',
                '--wallet-file', str(self.wallet_path),
                '--password', self.password,
                '--disable-rpc-login',
                '--trusted-daemon',
                '--log-level', '1'
            ]
            
            # Redirect stderr to log file so we can diagnose startup failures
            self._rpc_log_fd = open(self.rpc_log_file, 'w')
            self.rpc_process = subprocess.Popen(
                cmd,
                stdout=self._rpc_log_fd,
                stderr=self._rpc_log_fd,
                stdin=subprocess.DEVNULL,  # Prevents interactive prompts
                start_new_session=True
            )
            
            # Save PID to file
            with open(self.rpc_pid_file, 'w') as f:
                f.write(str(self.rpc_process.pid))
            
            logger.info(f"✓ RPC process started (PID: {self.rpc_process.pid})")
            
            # Increase timeout - wallet refresh can take 3-5 minutes when daemon is slow
            # Wait for RPC to be ready
            timeout = 300 if is_new_wallet else 180  # 5 minutes for new, 3 minutes for existing
            logger.info(f"⏳ Waiting for RPC to be ready (timeout: {timeout}s)...")
            logger.info("   Note: First startup may take 2-3 minutes while wallet refreshes")
            if not self._wait_for_rpc_ready(timeout):
                logger.error("❌ RPC failed to become ready")
                # Log diagnostic information regardless of whether process died.
                self._log_rpc_failure_diagnostics()
                self._stop_rpc()
                return False
            
            logger.info("✓ RPC is ready and accepting connections")
            return True
            
        except FileNotFoundError:
            logger.error("❌ monero-wallet-rpc not found. Is it installed?")
            logger.error("💡 Install: sudo apt install monero")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to start RPC: {e}")
            return False
    
    def _log_port_diagnostic(self):
        """Log diagnostic information about what is occupying the RPC port."""
        try:
            result = subprocess.run(
                ["ss", "-tlnp", f"sport = :{self.rpc_port}"],
                capture_output=True, text=True, timeout=5
            )
            if result.stdout.strip():
                logger.error(f"💡 Port {self.rpc_port} is occupied by:\n{result.stdout.strip()}")
        except Exception:
            try:
                result = subprocess.run(
                    ["netstat", "-tlnp"],
                    capture_output=True, text=True, timeout=5
                )
                for line in result.stdout.splitlines():
                    if f":{self.rpc_port}" in line:
                        logger.error(f"💡 Port {self.rpc_port} entry: {line.strip()}")
            except Exception:
                pass

    def _log_rpc_failure_diagnostics(self):
        """Log comprehensive diagnostics when RPC fails to become ready."""
        # Check if process is still alive.
        exit_code = self.rpc_process.poll() if self.rpc_process else None
        if exit_code is not None:
            logger.error(f"❌ RPC process died (exit code: {exit_code})")
        else:
            pid = self.rpc_process.pid if self.rpc_process else "N/A"
            logger.error(f"❌ RPC process (PID {pid}) is running but not responding")
            self._log_port_diagnostic()

        # Show last lines of the RPC log file for actionable error messages.
        if self.rpc_log_file and os.path.exists(self.rpc_log_file):
            try:
                with open(self.rpc_log_file, 'r') as f:
                    log_content = f.read()
                if log_content.strip():
                    tail = "\n".join(log_content.strip().splitlines()[-30:])
                    logger.error(f"📋 Last lines of RPC log ({self.rpc_log_file}):\n{tail}")
                    # Give specific hints for common errors.
                    if "is opened by another wallet program" in log_content or \
                            "Resource temporarily unavailable" in log_content:
                        logger.error("💡 Wallet is locked by another process")
                        logger.error("   Run: pkill -9 monero-wallet-rpc && sleep 2")
                    if "Error: Wallet file not found" in log_content or \
                            "Failed to open wallet" in log_content:
                        logger.error(f"💡 Wallet file not found at: {self.wallet_path}")
                    if "bind: Address already in use" in log_content:
                        logger.error(f"💡 Port {self.rpc_port} is already in use")
                        self._log_port_diagnostic()
            except Exception as exc:
                logger.warning(f"Could not read RPC log: {exc}")
        else:
            logger.warning("⚠ No RPC log file available for diagnostics")

    def stop_rpc(self):
        """Stop monero-wallet-rpc process (public method for backward compatibility)"""
        self._stop_rpc()
    
    def get_rpc_status(self) -> dict:
        """
        Get current RPC status for debugging.
        
        Returns:
            Dict with status info
        """
        status = {
            "running": False,
            "pid": None,
            "port": self.rpc_port,
            "responding": False,
            "error": None
        }
        
        # Check if process object exists
        if self.rpc_process:
            status["pid"] = self.rpc_process.pid
            
            # Check if process is still alive
            if self.rpc_process.poll() is None:
                status["running"] = True
            else:
                status["error"] = f"Process died with exit code {self.rpc_process.poll()}"
                return status
        else:
            status["error"] = "No RPC process tracked"
            return status
        
        # Check if RPC is responding
        try:
            url = f"http://127.0.0.1:{self.rpc_port}/json_rpc"
            response = requests.post(
                url,
                json={"jsonrpc": "2.0", "id": "0", "method": "get_balance"},
                timeout=5
            )
            
            if response.status_code == 200:
                status["responding"] = True
                
                # Get balance info
                result = response.json().get("result", {})
                status["balance"] = result.get("balance", 0)
                status["unlocked_balance"] = result.get("unlocked_balance", 0)
            else:
                status["error"] = f"RPC returned status {response.status_code}"
                
        except requests.exceptions.ConnectionError:
            status["error"] = "RPC not accepting connections"
        except Exception as e:
            status["error"] = f"RPC check failed: {str(e)}"
        
        return status
    
    def _initialize_wallet_object(self) -> bool:
        """
        Initialize monero-python Wallet object to connect to running RPC.
        
        This must be called AFTER start_rpc() succeeds.
        
        Returns:
            True if wallet object initialized successfully
        """
        try:
            from monero.wallet import Wallet
            from monero.backends.jsonrpc import JSONRPCWallet
            
            logger.info("🔗 Connecting monero-python Wallet to RPC...")
            
            # Create JSON-RPC backend pointing to our running RPC
            backend = JSONRPCWallet(
                host='127.0.0.1',
                port=self.rpc_port,
                user='',
                password=''
            )
            
            # Initialize Wallet object
            self.wallet = Wallet(backend)
            
            # Test connection by getting address
            address = self.wallet.address()
            logger.info(f"✓ Wallet object connected to RPC at 127.0.0.1:{self.rpc_port}")
            logger.info(f"✓ Primary address: {address}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize wallet object: {e}")
            logger.error(f"   Make sure 'monero' python package is installed")
            return False
    
    def _stop_rpc(self):
        """Stop the RPC process gracefully."""
        
        if self.rpc_process:
            logger.info("Stopping RPC process...")
            try:
                # Check if process is still running before terminating
                if self.rpc_process.poll() is None:
                    self.rpc_process.terminate()
                    self.rpc_process.wait(timeout=10)
                    logger.info(f"✓ Stopped wallet RPC (PID: {self.rpc_process.pid})")
                else:
                    logger.debug(f"RPC process already exited (exit code: {self.rpc_process.poll()})")
            except subprocess.TimeoutExpired:
                logger.warning("RPC didn't stop gracefully, killing...")
                self.rpc_process.kill()
            except Exception as e:
                logger.error(f"Error stopping RPC: {e}")
            
            self.rpc_process = None
        
        # Close RPC log file descriptor if open
        if self._rpc_log_fd:
            try:
                self._rpc_log_fd.close()
            except Exception:
                pass
            self._rpc_log_fd = None
        
        # Clean up PID file (handle race condition with try-except)
        if self.rpc_pid_file:
            try:
                os.remove(self.rpc_pid_file)
                logger.debug(f"✓ Removed PID file: {self.rpc_pid_file}")
            except FileNotFoundError:
                # File already removed, not an error
                logger.debug(f"PID file already removed: {self.rpc_pid_file}")
            except Exception as e:
                logger.warning(f"Could not remove PID file: {e}")
    
    def test_node_connection(self, daemon_address: Optional[str] = None, 
                            daemon_port: Optional[int] = None) -> dict:
        """
        Test connection to Monero node without opening wallet
        
        Args:
            daemon_address: Override default daemon address
            daemon_port: Override default daemon port
            
        Returns:
            Dictionary with connection test results:
            {
                'success': bool,
                'block_height': int,
                'network': str,
                'latency_ms': int,
                'message': str
            }
        """
        import time
        
        daemon_addr = daemon_address or self.daemon_address
        daemon_port_to_use = daemon_port or self.daemon_port
        
        try:
            url = f"http://{daemon_addr}:{daemon_port_to_use}/json_rpc"
            start_time = time.time()
            
            response = requests.post(url, json={
                "jsonrpc": "2.0",
                "id": "0",
                "method": "get_info"
            }, timeout=10)
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                data = response.json()
                result = data.get('result', {})
                
                # Map network type to readable name
                nettype = result.get('nettype', 'unknown')
                network_names = {
                    'mainnet': 'Mainnet',
                    'testnet': 'Testnet', 
                    'stagenet': 'Stagenet'
                }
                network = network_names.get(nettype, nettype)
                
                return {
                    'success': True,
                    'block_height': result.get('height', 0),
                    'network': network,
                    'latency_ms': latency_ms,
                    'message': f"Connected successfully ({latency_ms}ms)"
                }
            else:
                return {
                    'success': False,
                    'block_height': 0,
                    'network': 'unknown',
                    'latency_ms': 0,
                    'message': f"HTTP {response.status_code}: {response.text[:100]}"
                }
                
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'block_height': 0,
                'network': 'unknown',
                'latency_ms': 0,
                'message': "Connection timeout (>10s)"
            }
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'block_height': 0,
                'network': 'unknown',
                'latency_ms': 0,
                'message': "Cannot reach node - check address/port"
            }
        except Exception as e:
            return {
                'success': False,
                'block_height': 0,
                'network': 'unknown',
                'latency_ms': 0,
                'message': f"Error: {str(e)}"
            }
    
    def setup_wallet(self, create_if_missing: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Complete wallet setup: create if needed, start RPC, monitor sync
        Uses new validation, cleanup, and sync monitoring functions
        
        Args:
            create_if_missing: Auto-create wallet if it doesn't exist
            
        Returns:
            Tuple of (success, seed_phrase_if_created)
        """
        logger.info("="*60)
        logger.info("WALLET INITIALIZATION STARTING")
        logger.info("="*60)
        
        wallet_path_str = str(self.wallet_path)
        logger.info(f"Wallet path: {wallet_path_str}")
        
        # Clean up any stale locks BEFORE attempting to start RPC
        self._cleanup_wallet_locks()
        
        # Cleanup orphaned files
        wallet_dir = str(self.wallet_path.parent)
        cleanup_orphaned_wallets(wallet_dir)
        
        # Check if wallet already exists
        wallet_exists = check_existing_wallet(wallet_path_str)
        logger.info(f"Wallet exists: {wallet_exists}")
        
        if wallet_exists:
            # Validate wallet files
            if not validate_wallet_files(wallet_path_str):
                logger.warning("⚠ Existing wallet files incomplete, will recreate")
                wallet_exists = False  # Force recreation
            else:
                # Check wallet health (restore height 0 detection)
                logger.info("🔍 Checking wallet cache health...")
                is_healthy, reason = check_wallet_health(wallet_path_str)
                logger.info(f"Wallet healthy: {is_healthy}")
                
                if not is_healthy:
                    logger.warning(f"⚠ Wallet cache corrupted: {reason}")
                    logger.warning("⚠ This would cause RPC to hang trying to sync from block 0")
                    
                    # Try less aggressive fix first: delete only cache, keep keys
                    logger.info("🔧 Attempting automatic cache repair...")
                    if delete_corrupted_cache(wallet_path_str):
                        logger.info("✓ Corrupted cache removed")
                        logger.info("🔧 Will rebuild cache from current blockchain height")
                        logger.info("✓ Keys file preserved - wallet intact")
                        # Cache now gone, RPC will rebuild it correctly
                        # Continue to RPC startup below
                    else:
                        # Cache deletion failed - fall back to full recreation
                        logger.error("❌ Failed to delete corrupted cache")
                        logger.warning("⚠ Falling back to full wallet recreation...")
                        
                        # Backup existing wallet before recreation
                        if backup_wallet(wallet_path_str):
                            logger.info("✓ Wallet backed up successfully")
                            
                            # Delete old wallet files
                            if delete_wallet_files(wallet_path_str):
                                logger.info("✓ Old wallet files removed")
                                wallet_exists = False  # Force recreation
                            else:
                                logger.error("❌ Failed to delete old wallet files")
                                logger.info("="*60)
                                return False, None
                        else:
                            logger.error("❌ Failed to backup wallet")
                            logger.info("="*60)
                            return False, None
        
        # If wallet exists and is healthy, use it
        if wallet_exists:
            logger.info("✓ Using existing healthy wallet")
            
            # Start RPC for existing wallet
            rpc_port = self.rpc_port
            logger.info(f"🚀 Starting RPC on port {rpc_port}...")
            
            if not self.start_rpc():
                logger.error("❌ Failed to start wallet RPC")
                logger.info("="*60)
                return False, None
            
            logger.info(f"✓ RPC process started successfully")
            
            # Initialize wallet object to connect to RPC
            if not self._initialize_wallet_object():
                logger.error("❌ Failed to initialize wallet object")
                logger.warning("⚠ RPC is running but wallet object not connected")
                # Don't fail completely - RPC is still usable
                # But wallet features won't work
            
            # Check and monitor sync status
            logger.info("⏳ Waiting for RPC to be ready...")
            self._check_and_monitor_sync()
            
            # FINAL VERIFICATION before returning success
            logger.info("="*60)
            logger.info("FINAL VERIFICATION")
            logger.info("="*60)
            
            rpc_status = self.get_rpc_status()
            
            if not rpc_status["running"]:
                logger.error("❌ VERIFICATION FAILED: RPC not running!")
                logger.error(f"   Error: {rpc_status.get('error', 'Unknown')}")
                logger.info("="*60)
                return False, None
            
            if not rpc_status["responding"]:
                logger.error("❌ VERIFICATION FAILED: RPC not responding!")
                logger.error(f"   Error: {rpc_status.get('error', 'Unknown')}")
                logger.info("="*60)
                return False, None
            
            logger.info(f"✅ RPC is running (PID: {rpc_status['pid']})")
            logger.info(f"✅ RPC is responding on port {rpc_status['port']}")
            balance = rpc_status.get('balance') or 0
            logger.info(f"✅ Balance: {balance / 1e12:.12f} XMR")
            
            logger.info("="*60)
            logger.info("✅ WALLET INITIALIZATION COMPLETE")
            logger.info("="*60)
            return True, None
        
        # Create new wallet if it doesn't exist
        if create_if_missing:
            logger.info("📝 Creating new wallet...")
            try:
                success, address, seed = self.create_wallet()
                
                if not success:
                    logger.error("❌ Wallet creation FAILED")
                    logger.info("="*60)
                    return False, None
                
                logger.info("✓ Wallet creation SUCCESS")
                
                if seed:
                    logger.info("📋 Seed phrase captured successfully")
                else:
                    logger.warning("⚠ Seed phrase not captured!")
                
                # Start RPC after creation with extended timeout for new wallets
                rpc_port = self.rpc_port
                logger.info(f"🚀 Starting RPC on port {rpc_port}...")
                
                if not self.start_rpc(is_new_wallet=True):
                    logger.error("❌ Failed to start wallet RPC")
                    logger.info("="*60)
                    return False, None
                
                logger.info(f"✓ RPC process started (PID: {self.rpc_process.pid if self.rpc_process else 'unknown'})")
                
                # Initialize wallet object to connect to RPC
                if not self._initialize_wallet_object():
                    logger.error("❌ Failed to initialize wallet object")
                    logger.warning("⚠ RPC is running but wallet object not connected")
                    # Don't fail completely - RPC is still usable
                    # But wallet features won't work
                
                # Check and monitor sync status
                timeout = 180  # 3 minutes for new wallets
                logger.info(f"⏳ Waiting for RPC (timeout: {timeout}s)...")
                self._check_and_monitor_sync()
                
                # FINAL VERIFICATION before returning success
                logger.info("="*60)
                logger.info("FINAL VERIFICATION")
                logger.info("="*60)
                
                rpc_status = self.get_rpc_status()
                
                if not rpc_status["running"]:
                    logger.error("❌ VERIFICATION FAILED: RPC not running!")
                    logger.error(f"   Error: {rpc_status.get('error', 'Unknown')}")
                    logger.info("="*60)
                    return False, None
                
                if not rpc_status["responding"]:
                    logger.error("❌ VERIFICATION FAILED: RPC not responding!")
                    logger.error(f"   Error: {rpc_status.get('error', 'Unknown')}")
                    logger.info("="*60)
                    return False, None
                
                logger.info(f"✅ RPC is running (PID: {rpc_status['pid']})")
                logger.info(f"✅ RPC is responding on port {rpc_status['port']}")
                balance = rpc_status.get('balance') or 0
                logger.info(f"✅ Balance: {balance / 1e12:.12f} XMR")
                
                logger.info("="*60)
                logger.info("✅ WALLET INITIALIZATION COMPLETE")
                logger.info("="*60)
                return True, seed
                
            except WalletCreationError as e:
                logger.error(f"❌ Wallet creation failed: {e}")
                logger.info("="*60)
                return False, None
        
        # Create disabled and no wallet exists
        logger.error("❌ Wallet doesn't exist and auto-create disabled")
        logger.info("="*60)
        return False, None
    
    def _check_and_monitor_sync(self):
        """
        Check wallet sync status and start monitoring if needed.
        Internal helper method for setup_wallet.
        
        Monitors wallet height changes over time to detect if syncing is needed.
        """
        logger.info("🔍 Checking wallet sync status...")
        
        try:
            # Get initial wallet height
            height_response = requests.post(
                f"http://localhost:{self.rpc_port}/json_rpc",
                json={"jsonrpc":"2.0","id":"0","method":"get_height"},
                timeout=5
            )
            
            if height_response.status_code != 200:
                logger.warning("⚠ Could not check sync status, continuing anyway...")
                return
            
            initial_height = height_response.json().get("result", {}).get("height", 0)
            
            # Wait a moment and check again to see if height is increasing
            time.sleep(2)
            
            height_response2 = requests.post(
                f"http://localhost:{self.rpc_port}/json_rpc",
                json={"jsonrpc":"2.0","id":"0","method":"get_height"},
                timeout=5
            )
            
            if height_response2.status_code == 200:
                current_height = height_response2.json().get("result", {}).get("height", 0)
            else:
                current_height = initial_height
            
            # If height is changing or very low, wallet is syncing
            # Note: 100 blocks is roughly 200 minutes of blockchain history
            # A newly created wallet starts at 0, so < 100 indicates new/unsynced wallet
            MIN_SYNCED_HEIGHT = 100
            if current_height > initial_height or initial_height < MIN_SYNCED_HEIGHT:
                logger.info(f"⏳ Wallet syncing (height: {current_height})")
                logger.info("🔄 Starting background sync monitor...")
                logger.info("   This may take 5-60 minutes depending on internet speed")
                
                # Start sync monitor in background thread
                sync_thread = threading.Thread(
                    target=monitor_sync_progress,
                    args=(self.rpc_port, 10, 60),
                    daemon=True,
                    name="WalletSyncMonitor"
                )
                sync_thread.start()
                
                logger.info("✓ Sync monitor running in background")
                logger.info("💡 Bot will start now - payment features available after sync completes")
            else:
                # Height stable and reasonable, probably synced
                logger.info(f"✓ Wallet appears synced (height: {current_height:,})")
        
        except Exception as e:
            logger.warning(f"⚠ Could not check sync status: {e}")
            logger.info("💡 Continuing anyway - sync status unknown")
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        # Guard against cleanup during interpreter shutdown
        if hasattr(self, '_stop_rpc'):
            self._stop_rpc()



def test_node_connectivity(nodes: List[Tuple[str, int]]) -> List[Tuple[str, int]]:
    """
    Test connectivity to multiple nodes and return working ones
    
    Args:
        nodes: List of (address, port) tuples
        
    Returns:
        List of working (address, port) tuples
    """
    working = []
    
    for address, port in nodes:
        try:
            logger.debug(f"Testing node {address}:{port}...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((address, port))
            sock.close()
            
            if result == 0:
                logger.info(f"✅ Node reachable: {address}:{port}")
                working.append((address, port))
            else:
                logger.warning(f"❌ Node unreachable: {address}:{port}")
        except Exception as e:
            logger.warning(f"❌ Node test failed: {address}:{port} - {e}")
    
    return working


def initialize_wallet_system(wallet_path: str, daemon_address: str, daemon_port: int, 
                            rpc_port: int = 18083, password: str = "") -> Optional[WalletSetupManager]:
    """
    Initialize wallet system with graceful error handling.
    Returns WalletSetupManager instance or None if setup failed.
    
    This allows the bot to start in limited mode if wallet setup fails.
    
    Args:
        wallet_path: Path to wallet file
        daemon_address: Monero daemon address
        daemon_port: Monero daemon port
        rpc_port: Wallet RPC port
        password: Wallet password
        
    Returns:
        WalletSetupManager instance or None if setup failed
    """
    try:
        # Create wallet setup manager
        setup = WalletSetupManager(
            wallet_path=wallet_path,
            daemon_address=daemon_address,
            daemon_port=daemon_port,
            rpc_port=rpc_port,
            password=password
        )
        
        # Setup wallet (with cleanup and validation)
        success, seed = setup.setup_wallet(create_if_missing=True)
        
        if success:
            logger.info("✓ Wallet system initialized successfully")
            return setup
        else:
            logger.error("❌ Wallet setup failed")
            return None
        
    except WalletCreationError as e:
        logger.error("=" * 70)
        logger.error(f"❌ Wallet setup failed: {e}")
        logger.error("=" * 70)
        logger.error("⚠ Bot starting in LIMITED MODE")
        logger.error("⚠ Payment features will be DISABLED")
        logger.error("⚠ Signal messaging will still work")
        logger.error("=" * 70)
        logger.error("📋 To fix:")
        logger.error("   1. Install monero-wallet-cli")
        logger.error("   2. Check wallet file permissions")
        logger.error("   3. Check disk space")
        logger.error("=" * 70)
        return None
        
    except Exception as e:
        logger.error(f"❌ Unexpected wallet error: {e}")
        logger.error("⚠ Bot starting in LIMITED MODE")
        return None
