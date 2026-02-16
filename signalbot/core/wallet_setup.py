"""
Monero Wallet Auto-Setup and Management
Handles wallet creation, RPC startup, and connection management
"""

import os
import subprocess
import time
import requests
import socket
from pathlib import Path
from typing import Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)


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
        Create a new Monero wallet
        
        Returns:
            Tuple of (success, wallet_address, seed_phrase)
        """
        if self.wallet_exists():
            logger.info(f"Wallet already exists at {self.wallet_path}")
            return True, None, None
        
        logger.info(f"Creating new wallet at {self.wallet_path}")
        
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
                logger.error(f"Failed to create wallet: {result.stderr}")
                return False, None, None
            
            # Parse output for seed and address
            output = result.stdout
            seed = None
            address = None
            
            # Extract seed (25 words)
            if 'seed' in output.lower():
                lines = output.split('\n')
                for i, line in enumerate(lines):
                    if 'seed' in line.lower() and i + 1 < len(lines):
                        # Seed is usually on next line or same line
                        potential_seed = lines[i + 1].strip()
                        if len(potential_seed.split()) == 25:
                            seed = potential_seed
                            break
            
            # Extract address (starts with 4)
            for line in output.split('\n'):
                line = line.strip()
                if line.startswith('4') and len(line) == 95:
                    address = line
                    break
            
            logger.info(f"✅ Wallet created successfully!")
            if address:
                logger.info(f"   Address: {address[:20]}...{address[-10:]}")
            if seed:
                logger.info(f"   Seed: {seed[:30]}... (SAVE THIS!)")
            
            return True, address, seed
            
        except subprocess.TimeoutExpired:
            logger.error("Wallet creation timed out")
            return False, None, None
        except Exception as e:
            logger.error(f"Error creating wallet: {e}")
            return False, None, None
    
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
        daemon_prt = daemon_port or self.daemon_port
        
        logger.info(f"Starting wallet RPC...")
        logger.info(f"  Daemon: {daemon_addr}:{daemon_prt}")
        logger.info(f"  RPC Port: {self.rpc_port}")
        logger.info(f"  Wallet: {self.wallet_path}")
        
        # Log password handling for debugging
        logger.debug(f"Starting RPC with password: {'<empty>' if self.password == '' else '<set>'}")
        
        try:
            cmd = [
                'monero-wallet-rpc',
                '--daemon-address', f'{daemon_addr}:{daemon_prt}',
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
            
            # Wait for RPC to start
            for i in range(10):
                time.sleep(1)
                if self.test_rpc_connection():
                    logger.info(f"✅ Wallet RPC started successfully!")
                    return True
                logger.debug(f"Waiting for RPC to start... ({i+1}/10)")
            
            logger.error("❌ RPC started but not responding")
            return False
            
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
    
    def setup_wallet(self, create_if_missing: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Complete wallet setup: create if needed, start RPC
        
        Args:
            create_if_missing: Auto-create wallet if it doesn't exist
            
        Returns:
            Tuple of (success, seed_phrase_if_created)
        """
        logger.info("="*60)
        logger.info("WALLET SETUP")
        logger.info("="*60)
        
        # Step 1: Check/create wallet
        if not self.wallet_exists():
            if create_if_missing:
                logger.info("📝 Wallet doesn't exist, creating new wallet...")
                success, address, seed = self.create_wallet()
                if not success:
                    logger.error("❌ Failed to create wallet")
                    return False, None
                logger.info("✅ Wallet created successfully!")
                if seed:
                    logger.warning("⚠️  SAVE YOUR SEED PHRASE!")
                    logger.warning(f"   {seed}")
                    logger.warning("   This is the ONLY way to recover your wallet!")
                return True, seed
            else:
                logger.error("❌ Wallet doesn't exist and auto-create disabled")
                return False, None
        else:
            logger.info("✅ Wallet file exists")
        
        # Step 2: Start RPC
        logger.info("🔌 Starting wallet RPC...")
        if self.start_rpc():
            logger.info("✅ Wallet RPC connected!")
            logger.info("="*60)
            return True, None
        else:
            logger.error("❌ Failed to start wallet RPC")
            logger.info("="*60)
            return False, None


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
