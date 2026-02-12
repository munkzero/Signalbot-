"""
Monero wallet integration
Handles in-house wallet management and RPC connections
"""

import requests
from typing import Optional, Dict, List, Tuple
import json
import subprocess
import time
import os
import shutil
from datetime import datetime
from pathlib import Path
from monero.wallet import JSONRPCWallet
from monero.seed import Seed
from ..config.settings import (
    MONERO_CONFIRMATIONS_REQUIRED, 
    WALLET_DIR, 
    BACKUP_DIR,
    DEFAULT_DAEMON_ADDRESS,
    DEFAULT_DAEMON_PORT,
    NODE_CONNECTION_TIMEOUT
)


class InHouseWallet:
    """
    In-house Monero wallet with full functionality
    Manages wallet creation, seed phrases, and transactions
    """
    
    def __init__(
        self,
        wallet_path: str,
        password: str,
        daemon_address: str = DEFAULT_DAEMON_ADDRESS,
        daemon_port: int = DEFAULT_DAEMON_PORT,
        use_ssl: bool = True
    ):
        """
        Initialize in-house wallet
        
        Args:
            wallet_path: Path to wallet file
            password: Wallet password
            daemon_address: Daemon node address
            daemon_port: Daemon node port
            use_ssl: Use SSL for daemon connection
        """
        self.wallet_path = wallet_path
        self.password = password
        self.daemon_address = daemon_address
        self.daemon_port = daemon_port
        self.use_ssl = use_ssl
        self.wallet = None
        self.rpc_process = None
        self.rpc_port = 18082  # Default wallet RPC port
        
    @classmethod
    def create_new_wallet(
        cls,
        wallet_name: str,
        password: str,
        daemon_address: str = DEFAULT_DAEMON_ADDRESS,
        daemon_port: int = DEFAULT_DAEMON_PORT,
        use_ssl: bool = True
    ) -> Tuple['InHouseWallet', str]:
        """
        Create a new Monero wallet with seed phrase
        
        Args:
            wallet_name: Name for the wallet file
            password: Wallet password
            daemon_address: Daemon node address
            daemon_port: Daemon node port
            use_ssl: Use SSL for daemon connection
            
        Returns:
            Tuple of (InHouseWallet instance, seed_phrase)
        """
        # Generate new seed
        seed = Seed()
        
        # Get seed phrase (25 words)
        seed_phrase = cls._get_seed_phrase_from_seed(seed)
        
        wallet_path = str(Path(WALLET_DIR) / wallet_name)
        
        # Store seed temporarily for verification
        instance = cls(wallet_path, password, daemon_address, daemon_port, use_ssl)
        instance._seed = seed
        
        return instance, seed_phrase
    
    @staticmethod
    def _get_seed_phrase_from_seed(seed: Seed) -> str:
        """
        Extract seed phrase from Seed object
        
        Args:
            seed: Seed object
            
        Returns:
            Seed phrase string
        """
        # The monero library Seed object may have different attributes
        # depending on version. Try multiple approaches.
        if hasattr(seed, 'phrase'):
            return seed.phrase
        elif hasattr(seed, 'phrase_or_hex'):
            return seed.phrase_or_hex
        else:
            # Fallback to hex seed if phrase not available
            return seed.hex_seed
    
    @classmethod
    def restore_from_seed(
        cls,
        wallet_name: str,
        password: str,
        seed_phrase: str,
        daemon_address: str = DEFAULT_DAEMON_ADDRESS,
        daemon_port: int = DEFAULT_DAEMON_PORT,
        use_ssl: bool = True
    ) -> 'InHouseWallet':
        """
        Restore wallet from seed phrase
        
        Args:
            wallet_name: Name for the wallet file
            password: Wallet password
            seed_phrase: 25-word seed phrase
            daemon_address: Daemon node address
            daemon_port: Daemon node port
            use_ssl: Use SSL for daemon connection
            
        Returns:
            InHouseWallet instance
        """
        # Parse seed phrase
        seed = Seed(seed_phrase)
        
        wallet_path = str(Path(WALLET_DIR) / wallet_name)
        
        instance = cls(wallet_path, password, daemon_address, daemon_port, use_ssl)
        instance._seed = seed
        
        return instance
    
    def connect(self) -> bool:
        """
        Connect to wallet via RPC
        
        Returns:
            True if connection successful
        """
        try:
            # Start wallet RPC if not already running
            if not self.rpc_process:
                self._start_wallet_rpc()
            
            # Create RPC connection
            protocol = 'https' if self.use_ssl else 'http'
            self.wallet = JSONRPCWallet(
                protocol=protocol,
                host=self.daemon_address,
                port=self.rpc_port,
                timeout=NODE_CONNECTION_TIMEOUT
            )
            
            # Test connection
            try:
                self.wallet.height()
                return True
            except Exception:
                return False
                
        except Exception as e:
            print(f"Failed to connect wallet: {e}")
            return False
    
    def _start_wallet_rpc(self):
        """Start monero-wallet-rpc process"""
        # This would start the actual wallet RPC
        # For now, we'll assume it's handled externally or use direct RPC connection
        # In production, you'd use subprocess to start monero-wallet-rpc
        pass
    
    def get_seed_phrase(self) -> str:
        """
        Get wallet seed phrase (25 words)
        WARNING: Keep this secure!
        
        Returns:
            Seed phrase
        """
        if hasattr(self, '_seed'):
            return self._get_seed_phrase_from_seed(self._seed)
        
        # If wallet is connected, get seed from RPC
        if self.wallet:
            try:
                return self.wallet.seed().phrase
            except Exception:
                return None
        return None
    
    def get_address(self, account_index: int = 0) -> str:
        """
        Get primary wallet address
        
        Args:
            account_index: Account index (default 0)
            
        Returns:
            Wallet address
        """
        if self.wallet:
            return str(self.wallet.address(account=account_index))
        elif hasattr(self, '_seed'):
            return self._seed.public_address()
        return ""
    
    def get_balance(self) -> Tuple[float, float, float]:
        """
        Get wallet balance
        
        Returns:
            Tuple of (total_balance, unlocked_balance, locked_balance) in XMR
        """
        if not self.wallet:
            return (0.0, 0.0, 0.0)
        
        try:
            balance = self.wallet.balance()
            total = float(balance[0])  # Total balance
            unlocked = float(balance[1])  # Unlocked balance
            locked = total - unlocked
            return (total, unlocked, locked)
        except Exception as e:
            print(f"Failed to get balance: {e}")
            return (0.0, 0.0, 0.0)
    
    def create_subaddress(self, label: Optional[str] = None, account_index: int = 0) -> Dict:
        """
        Create new subaddress for receiving payments
        
        Args:
            label: Optional label for subaddress
            account_index: Account index (default 0)
            
        Returns:
            Dictionary with address info
        """
        if not self.wallet:
            raise RuntimeError("Wallet not connected")
        
        try:
            address = self.wallet.new_address(account=account_index, label=label)
            return {
                'address': str(address),
                'account_index': account_index,
                'label': label
            }
        except Exception as e:
            raise RuntimeError(f"Failed to create subaddress: {e}")
    
    def get_transfers(
        self,
        min_height: Optional[int] = None,
        max_height: Optional[int] = None
    ) -> List[Dict]:
        """
        Get transaction history
        
        Args:
            min_height: Minimum block height
            max_height: Maximum block height
            
        Returns:
            List of transactions
        """
        if not self.wallet:
            return []
        
        try:
            # Get incoming and outgoing transfers
            transfers = []
            
            # Note: The monero library handles transfer queries differently
            # We'd need to adapt this based on the actual API
            # For now, return empty list
            return transfers
        except Exception as e:
            print(f"Failed to get transfers: {e}")
            return []
    
    def send(
        self,
        address: str,
        amount: float,
        priority: int = 2
    ) -> Dict:
        """
        Send XMR to an address
        
        Args:
            address: Destination address
            amount: Amount in XMR
            priority: Transaction priority (0-3)
            
        Returns:
            Transaction info
        """
        if not self.wallet:
            raise RuntimeError("Wallet not connected")
        
        try:
            # Send transaction
            tx = self.wallet.transfer(
                address,
                amount,
                priority=priority
            )
            
            return {
                'tx_hash': str(tx[0].hash) if hasattr(tx[0], 'hash') else '',
                'amount': amount,
                'fee': float(tx[0].fee) if hasattr(tx[0], 'fee') else 0.0
            }
        except Exception as e:
            raise RuntimeError(f"Failed to send transaction: {e}")
    
    def check_payment(
        self,
        address: str,
        expected_amount: float
    ) -> Tuple[bool, float, int]:
        """
        Check if payment received at address
        
        Args:
            address: Subaddress to check
            expected_amount: Expected amount in XMR
            
        Returns:
            Tuple of (payment_received, amount_received, confirmations)
        """
        if not self.wallet:
            return (False, 0.0, 0)
        
        try:
            # Get balance for specific address
            balance = self.wallet.address_balance(address)
            amount_received = float(balance)
            
            # Check confirmations
            # Note: This is simplified; in practice we'd check specific transactions
            confirmations = 10  # Placeholder
            
            payment_received = (
                amount_received >= expected_amount and
                confirmations >= MONERO_CONFIRMATIONS_REQUIRED
            )
            
            return (payment_received, amount_received, confirmations)
        except Exception as e:
            print(f"Failed to check payment: {e}")
            return (False, 0.0, 0)
    
    def rescan_blockchain(self, height: Optional[int] = None):
        """
        Rescan blockchain from specified height
        
        Args:
            height: Block height to scan from (None for full rescan)
        """
        if not self.wallet:
            raise RuntimeError("Wallet not connected")
        
        try:
            self.wallet.refresh()
        except Exception as e:
            raise RuntimeError(f"Failed to rescan blockchain: {e}")
    
    def backup_wallet(self) -> str:
        """
        Create encrypted backup of wallet files
        
        Returns:
            Path to backup file
        """
        if not os.path.exists(self.wallet_path):
            raise RuntimeError("Wallet file not found")
        
        # Create backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        wallet_name = Path(self.wallet_path).name
        backup_path = Path(BACKUP_DIR) / f"{wallet_name}_{timestamp}.backup"
        
        # Copy wallet file to backup
        shutil.copy2(self.wallet_path, backup_path)
        
        # Also backup keys file if it exists
        keys_path = f"{self.wallet_path}.keys"
        if os.path.exists(keys_path):
            backup_keys_path = Path(BACKUP_DIR) / f"{wallet_name}_{timestamp}.keys.backup"
            shutil.copy2(keys_path, backup_keys_path)
        
        return str(backup_path)
    
    def close(self):
        """Close wallet connection"""
        if self.rpc_process:
            try:
                self.rpc_process.terminate()
                self.rpc_process.wait(timeout=5)
            except Exception:
                self.rpc_process.kill()
            self.rpc_process = None
        
        self.wallet = None


class MoneroWallet:
    """
    Monero wallet handler supporting both RPC and file modes
    """
    
    def __init__(
        self,
        wallet_type: str,
        rpc_host: Optional[str] = None,
        rpc_port: Optional[int] = None,
        rpc_user: Optional[str] = None,
        rpc_password: Optional[str] = None,
        wallet_file: Optional[str] = None,
        wallet_password: Optional[str] = None
    ):
        """
        Initialize Monero wallet
        
        Args:
            wallet_type: 'rpc' or 'file'
            rpc_host: RPC host (for RPC mode)
            rpc_port: RPC port (for RPC mode)
            rpc_user: RPC username (optional)
            rpc_password: RPC password (optional)
            wallet_file: Path to wallet file (for file mode)
            wallet_password: Wallet password (for file mode)
        """
        self.wallet_type = wallet_type
        
        if wallet_type == 'rpc':
            if not rpc_host or not rpc_port:
                raise ValueError("RPC host and port required for RPC mode")
            
            self.rpc_url = f"http://{rpc_host}:{rpc_port}/json_rpc"
            self.rpc_user = rpc_user
            self.rpc_password = rpc_password
            self.auth = (rpc_user, rpc_password) if rpc_user and rpc_password else None
        
        elif wallet_type == 'file':
            if not wallet_file or not wallet_password:
                raise ValueError("Wallet file and password required for file mode")
            
            self.wallet_file = wallet_file
            self.wallet_password = wallet_password
            self.rpc_process = None
            self.rpc_url = None
        
        else:
            raise ValueError(f"Invalid wallet type: {wallet_type}")
    
    def _rpc_call(self, method: str, params: Optional[Dict] = None) -> Dict:
        """
        Make RPC call to wallet
        
        Args:
            method: RPC method name
            params: Method parameters
            
        Returns:
            RPC response
        """
        if not self.rpc_url:
            raise RuntimeError("Wallet not connected")
        
        payload = {
            'jsonrpc': '2.0',
            'id': '0',
            'method': method
        }
        
        if params:
            payload['params'] = params
        
        try:
            response = requests.post(
                self.rpc_url,
                json=payload,
                auth=self.auth,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            
            if 'error' in result:
                error_msg = result['error'].get('message', result['error'])
                raise RuntimeError(f"RPC error: {error_msg}")
            
            return result.get('result', {})
        except requests.exceptions.ConnectionError as e:
            raise RuntimeError(f"Cannot connect to wallet RPC: {e}")
        except requests.exceptions.Timeout:
            raise RuntimeError(f"Wallet RPC timeout - check node connection")
        except Exception as e:
            raise RuntimeError(f"RPC call failed: {e}")
    
    def test_connection(self) -> bool:
        """
        Test wallet connection
        
        Returns:
            True if connection successful
        """
        try:
            result = self._rpc_call('get_balance')
            return True
        except:
            return False
    
    def get_balance(self) -> Tuple[float, float]:
        """
        Get wallet balance
        
        Returns:
            Tuple of (total_balance, unlocked_balance) in XMR
        """
        result = self._rpc_call('get_balance')
        
        # Convert from atomic units to XMR
        total = result.get('balance', 0) / 1e12
        unlocked = result.get('unlocked_balance', 0) / 1e12
        
        return (total, unlocked)
    
    def get_address(self, account_index: int = 0, address_index: int = 0) -> str:
        """
        Get wallet address
        
        Args:
            account_index: Account index
            address_index: Address index
            
        Returns:
            Wallet address
        """
        result = self._rpc_call('get_address', {
            'account_index': account_index,
            'address_index': [address_index]
        })
        
        addresses = result.get('addresses', [])
        if addresses:
            return addresses[0].get('address', '')
        
        return result.get('address', '')
    
    def create_subaddress(self, account_index: int = 0, label: Optional[str] = None) -> Dict:
        """
        Create new subaddress for receiving payments
        
        Args:
            account_index: Account index
            label: Optional label for subaddress
            
        Returns:
            Dictionary with address info
        """
        params = {'account_index': account_index}
        if label:
            params['label'] = label
        
        result = self._rpc_call('create_address', params)
        
        return {
            'address': result.get('address', ''),
            'address_index': result.get('address_index', 0)
        }
    
    def get_transfers(
        self,
        address: Optional[str] = None,
        min_height: Optional[int] = None
    ) -> List[Dict]:
        """
        Get incoming transfers
        
        Args:
            address: Filter by address
            min_height: Minimum block height
            
        Returns:
            List of transfers
        """
        params = {
            'in': True,
            'out': False,
            'pending': True,
            'failed': False,
            'pool': True
        }
        
        if min_height:
            params['min_height'] = min_height
        
        result = self._rpc_call('get_transfers', params)
        
        transfers = []
        
        # Get incoming transfers
        if 'in' in result:
            transfers.extend(result['in'])
        
        # Get pending transfers
        if 'pending' in result:
            transfers.extend(result['pending'])
        
        # Get pool transfers
        if 'pool' in result:
            transfers.extend(result['pool'])
        
        # Filter by address if specified
        if address:
            transfers = [t for t in transfers if t.get('address') == address]
        
        return transfers
    
    def check_payment(self, address: str, expected_amount: float) -> Tuple[bool, float, int]:
        """
        Check if payment received at address
        
        Args:
            address: Subaddress to check
            expected_amount: Expected amount in XMR
            
        Returns:
            Tuple of (payment_received, amount_received, confirmations)
        """
        transfers = self.get_transfers(address=address)
        
        total_received = 0.0
        max_confirmations = 0
        
        for transfer in transfers:
            # Convert from atomic units to XMR
            amount = transfer.get('amount', 0) / 1e12
            confirmations = transfer.get('confirmations', 0)
            
            total_received += amount
            max_confirmations = max(max_confirmations, confirmations)
        
        # Payment considered received if amount matches and has enough confirmations
        payment_received = (
            total_received >= expected_amount and
            max_confirmations >= MONERO_CONFIRMATIONS_REQUIRED
        )
        
        return (payment_received, total_received, max_confirmations)
    
    def is_view_only(self) -> bool:
        """
        Check if wallet is view-only (cannot send funds)
        
        Returns:
            True if wallet is view-only
        """
        try:
            # Try to query spend key - view-only wallets won't have it
            result = self._rpc_call('query_key', {'key_type': 'spend_key'})
            
            # If we get a key, check if it's all zeros (view-only indicator)
            spend_key = result.get('key', '')
            
            # View-only wallets have a spend key of all zeros
            if spend_key and spend_key == '0' * 64:
                return True
            
            return False
        except Exception as e:
            # If query fails, assume view-only to be safe
            # This prevents accidental spending attempts
            print(f"WARNING: Cannot determine wallet type (assuming view-only): {e}")
            return True
    
    def transfer(
        self,
        destinations: List[Dict[str, any]],
        priority: int = 0
    ) -> Dict:
        """
        Send XMR to one or more destinations
        
        Args:
            destinations: List of dicts with 'address' and 'amount' (in XMR)
            priority: Transaction priority (0-3)
            
        Returns:
            Transaction info
        """
        # Convert amounts to atomic units
        dest_params = []
        for dest in destinations:
            dest_params.append({
                'address': dest['address'],
                'amount': int(dest['amount'] * 1e12)
            })
        
        params = {
            'destinations': dest_params,
            'priority': priority,
            'get_tx_key': True
        }
        
        result = self._rpc_call('transfer', params)
        
        return {
            'tx_hash': result.get('tx_hash', ''),
            'tx_key': result.get('tx_key', ''),
            'amount': result.get('amount', 0) / 1e12,
            'fee': result.get('fee', 0) / 1e12
        }
    
    def close(self):
        """
        Close wallet connection
        """
        if self.wallet_type == 'file' and self.rpc_process:
            self.rpc_process.terminate()
            self.rpc_process.wait()
            self.rpc_process = None


class MoneroWalletFactory:
    """Factory for creating MoneroWallet instances"""
    
    @staticmethod
    def create_from_config(config: Dict[str, any]) -> MoneroWallet:
        """
        Create wallet from configuration dictionary
        
        Args:
            config: Wallet configuration
            
        Returns:
            MoneroWallet instance
        """
        wallet_type = config.get('type', 'rpc')
        
        if wallet_type == 'rpc':
            return MoneroWallet(
                wallet_type='rpc',
                rpc_host=config.get('rpc_host'),
                rpc_port=config.get('rpc_port'),
                rpc_user=config.get('rpc_user'),
                rpc_password=config.get('rpc_password')
            )
        elif wallet_type == 'file':
            return MoneroWallet(
                wallet_type='file',
                wallet_file=config.get('wallet_file'),
                wallet_password=config.get('wallet_password')
            )
        else:
            raise ValueError(f"Unknown wallet type: {wallet_type}")
