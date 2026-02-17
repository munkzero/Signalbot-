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
from pathlib import Path
from typing import Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)


class WalletCreationError(Exception):
    """Raised when wallet creation or setup fails"""
    pass


def cleanup_zombie_rpc_processes():
    """
    Kill any orphaned monero-wallet-rpc processes from previous runs.
    
    This prevents wallet lock file issues when bot was force-killed
    and didn't clean up properly.
    """
    try:
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


def wait_for_rpc_ready(port=18083, max_wait=60, retry_interval=2):
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
        
    Returns:
        True if RPC is ready, False if timeout
    """
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


class WalletSetupManager:
    """Manages Monero wallet creation and RPC lifecycle"""
    
    def __init__(self, wallet_path: str, daemon_address: str, daemon_port: int, 
                 rpc_port: int = 18082, password: str = ""):
        self.wallet_path = Path(wallet_path)
        self.daemon_address = daemon_address
        self.daemon_port = daemon_port
        self.rpc_port = rpc_port
        self.password = password
        self.rpc_process = None
        
    def wallet_exists(self) -> bool:
        """Check if wallet files exist"""
        keys_file = Path(str(self.wallet_path) + ".keys")
        return keys_file.exists()
    
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
        
        try:
            # Create wallet using monero-wallet-cli
            cmd = [
                'monero-wallet-cli',
                '--generate-new-wallet', str(self.wallet_path),
                '--password', self.password,
                '--mnemonic-language', 'English',
                '--command', 'seed',
                '--command', 'address',
                '--command', 'exit'
            ]
            
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
            
            # Display seed phrase to console ONLY (not to log files)
            # User must copy this immediately - it's not stored anywhere
            if seed:
                # Use print to console, not logger (which may write to files)
                print("=" * 70)
                print("🔐 SAVE YOUR SEED PHRASE (NOT STORED ANYWHERE):")
                print(seed)
                print("=" * 70)
                # Log a reminder without the actual seed
                logger.warning("⚠️ IMPORTANT: Seed phrase displayed in console - save it now!")
            
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
    
    def start_rpc(self, daemon_address: Optional[str] = None, 
                  daemon_port: Optional[int] = None) -> bool:
        """
        Start monero-wallet-rpc process
        
        Args:
            daemon_address: Override default daemon address
            daemon_port: Override default daemon port
            
        Returns:
            True if RPC started successfully
        """
        if self.is_rpc_running():
            logger.info(f"✅ Wallet RPC already running on port {self.rpc_port}")
            return True
        
        if not self.wallet_exists():
            logger.error("❌ Cannot start RPC: wallet file doesn't exist")
            return False
        
        daemon_addr = daemon_address or self.daemon_address
        daemon_port_to_use = daemon_port or self.daemon_port
        
        logger.info(f"🔧 Starting wallet RPC process...")
        logger.info(f"  Daemon: {daemon_addr}:{daemon_port_to_use}")
        logger.info(f"  RPC Port: {self.rpc_port}")
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
            
            # Use Popen to capture process handle (don't use --detach)
            # CRITICAL: Use stdin=subprocess.DEVNULL to prevent password prompts
            self.rpc_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL  # Prevents interactive prompts
            )
            
            logger.info(f"Started RPC process with PID: {self.rpc_process.pid}")
            
            # Wait for RPC to be ready with improved retry logic
            if not wait_for_rpc_ready(port=self.rpc_port, max_wait=60, retry_interval=2):
                logger.error("❌ RPC process started but not responding")
                logger.error("💡 Check if monero-wallet-rpc is installed: monero-wallet-rpc --version")
                return False
            
            logger.info(f"✅ Wallet RPC started successfully!")
            return True
            
        except FileNotFoundError:
            logger.error("❌ monero-wallet-rpc not found. Is it installed?")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to start RPC: {e}")
            return False
    
    def stop_rpc(self):
        """Stop monero-wallet-rpc process"""
        try:
            # Use the process handle if we have it
            if self.rpc_process and hasattr(self.rpc_process, 'pid'):
                import signal
                try:
                    os.kill(self.rpc_process.pid, signal.SIGTERM)
                    self.rpc_process.wait(timeout=5)
                    logger.info(f"Stopped wallet RPC (PID: {self.rpc_process.pid})")
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate gracefully
                    os.kill(self.rpc_process.pid, signal.SIGKILL)
                    logger.warning(f"Force killed wallet RPC (PID: {self.rpc_process.pid})")
                except ProcessLookupError:
                    # Process already dead
                    logger.debug("RPC process already terminated")
                self.rpc_process = None
            else:
                logger.debug("No RPC process to stop")
        except Exception as e:
            logger.error(f"Error stopping RPC: {e}")
            self.rpc_process = None
    
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
        logger.info("WALLET SETUP")
        logger.info("="*60)
        
        # Step 1: Cleanup zombie RPC processes
        cleanup_zombie_rpc_processes()
        
        wallet_path_str = str(self.wallet_path)
        
        # Cleanup orphaned files
        wallet_dir = str(self.wallet_path.parent)
        cleanup_orphaned_wallets(wallet_dir)
        
        # Check if wallet already exists
        if check_existing_wallet(wallet_path_str):
            logger.info("✓ Using existing wallet")
            
            # Validate wallet files
            if not validate_wallet_files(wallet_path_str):
                logger.warning("⚠ Existing wallet files incomplete, will recreate")
                # Fall through to create new wallet
            else:
                # Start RPC for existing wallet
                logger.info("🔌 Starting wallet RPC...")
                if not self.start_rpc():
                    logger.error("❌ Failed to start wallet RPC")
                    logger.info("="*60)
                    return False, None
                
                logger.info("✓ RPC started successfully")
                
                # Check and monitor sync status
                self._check_and_monitor_sync()
                
                logger.info("✅ Wallet system initialized successfully")
                logger.info("="*60)
                return True, None
        
        # Create new wallet if it doesn't exist
        if create_if_missing and not check_existing_wallet(wallet_path_str):
            logger.info("🔧 Creating new wallet...")
            try:
                success, address, seed = self.create_wallet()
                if seed:
                    logger.warning("⚠️  SAVE YOUR SEED PHRASE!")
                    logger.warning(f"   {seed}")
                    logger.warning("   This is the ONLY way to recover your wallet!")
                
                # Start RPC after creation
                logger.info("🔌 Starting wallet RPC...")
                if not self.start_rpc():
                    logger.error("❌ Failed to start wallet RPC")
                    logger.info("="*60)
                    return False, None
                
                logger.info("✓ RPC started successfully")
                
                # Check and monitor sync status
                self._check_and_monitor_sync()
                
                logger.info("✅ Wallet system initialized successfully")
                logger.info("="*60)
                return True, seed
                
            except WalletCreationError as e:
                logger.error(f"❌ {e}")
                logger.info("="*60)
                return False, None
        
        if not create_if_missing:
            logger.error("❌ Wallet doesn't exist and auto-create disabled")
            logger.info("="*60)
            return False, None
        
        # Should not reach here, but just in case
        logger.error("❌ Unexpected state in wallet setup")
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
                            rpc_port: int = 18082, password: str = "") -> Optional[WalletSetupManager]:
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
