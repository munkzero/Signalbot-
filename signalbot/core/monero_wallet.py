"""
Monero wallet integration
Handles RPC wallet and wallet file operations
"""

import requests
from typing import Optional, Dict, List, Tuple
import json
import subprocess
import time
from ..config.settings import MONERO_CONFIRMATIONS_REQUIRED


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
                raise RuntimeError(f"RPC error: {result['error']}")
            
            return result.get('result', {})
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
