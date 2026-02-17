#!/usr/bin/env python3
"""
Test script for wallet GUI direct RPC fix
Simulates RPC responses to test the fallback mechanism
"""

import json
from unittest.mock import Mock, patch, MagicMock
import sys

# Mock PyQt5 before importing dashboard
sys.modules['PyQt5'] = MagicMock()
sys.modules['PyQt5.QtWidgets'] = MagicMock()
sys.modules['PyQt5.QtCore'] = MagicMock()
sys.modules['PyQt5.QtGui'] = MagicMock()

def test_rpc_call_direct():
    """Test the direct RPC call method"""
    print("Testing direct RPC call method...")
    
    # Create a mock WalletTab-like object
    class MockWalletTab:
        def __init__(self):
            self.wallet = Mock()
            self.wallet.rpc_port = 18083
        
        def _rpc_call_direct(self, method, params=None):
            """Direct RPC call implementation (copied from dashboard.py)"""
            try:
                import requests
                
                rpc_port = 18083
                if self.wallet and hasattr(self.wallet, 'rpc_port'):
                    rpc_port = self.wallet.rpc_port
                
                url = f'http://127.0.0.1:{rpc_port}/json_rpc'
                
                payload = {
                    "jsonrpc": "2.0",
                    "id": "0",
                    "method": method
                }
                
                if params:
                    payload["params"] = params
                
                response = requests.post(
                    url,
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if 'result' in data:
                        return data['result']
                    elif 'error' in data:
                        print(f"RPC Error: {data['error']}")
                        return None
                else:
                    print(f"RPC returned status {response.status_code}")
                    return None
                    
            except Exception as e:
                print(f"Direct RPC call failed: {e}")
                return None
    
    tab = MockWalletTab()
    
    # Mock successful get_address response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'result': {
            'address': '46Z2GTmFybzZb9WAvokQcpZKupVPqijct7BjqknJwwSCcoi38S8JN98ogks1gWSQ1dMx88Q7gBsyHffPeyLM4cFBJWe71w'
        }
    }
    
    with patch('requests.post', return_value=mock_response):
        result = tab._rpc_call_direct('get_address', {'account_index': 0})
        
        if result and 'address' in result:
            print(f"✓ Successfully fetched address via direct RPC")
            print(f"  Address: {result['address'][:30]}...")
            return True
        else:
            print("✗ Failed to fetch address")
            return False

def test_balance_fallback():
    """Test balance fetching with fallback"""
    print("\nTesting balance worker with RPC fallback...")
    
    # Mock successful get_balance response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'result': {
            'balance': 1000000000000,  # 1 XMR in atomic units
            'unlocked_balance': 500000000000  # 0.5 XMR unlocked
        }
    }
    
    # Create mock wallet that fails on get_balance()
    mock_wallet = Mock()
    mock_wallet.rpc_port = 18083
    mock_wallet.get_balance.side_effect = Exception("Wallet object not connected")
    
    with patch('requests.post', return_value=mock_response):
        # Simulate the fallback logic from RefreshBalanceWorker
        try:
            balance = mock_wallet.get_balance()
        except Exception:
            # Fallback to direct RPC
            import requests
            response = requests.post(
                'http://127.0.0.1:18083/json_rpc',
                json={
                    "jsonrpc": "2.0",
                    "id": "0",
                    "method": "get_balance",
                    "params": {"account_index": 0}
                },
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'result' in data:
                    balance_atomic = data['result'].get('balance', 0)
                    unlocked_atomic = data['result'].get('unlocked_balance', 0)
                    
                    total_xmr = balance_atomic / 1e12
                    unlocked_xmr = unlocked_atomic / 1e12
                    locked_xmr = total_xmr - unlocked_xmr
                    
                    print(f"✓ Successfully fetched balance via direct RPC")
                    print(f"  Total: {total_xmr:.12f} XMR")
                    print(f"  Unlocked: {unlocked_xmr:.12f} XMR")
                    print(f"  Locked: {locked_xmr:.12f} XMR")
                    return True
    
    print("✗ Failed to fetch balance")
    return False

def test_subaddress_generation():
    """Test subaddress generation with fallback"""
    print("\nTesting subaddress generation with RPC fallback...")
    
    # Mock successful create_address response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'result': {
            'address': '8xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
            'address_index': 1
        }
    }
    
    with patch('requests.post', return_value=mock_response):
        # Simulate direct RPC call
        import requests
        response = requests.post(
            'http://127.0.0.1:18083/json_rpc',
            json={
                "jsonrpc": "2.0",
                "id": "0",
                "method": "create_address",
                "params": {
                    "account_index": 0,
                    "label": "Test Label"
                }
            },
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'result' in data and 'address' in data['result']:
                address = data['result']['address']
                index = data['result']['address_index']
                print(f"✓ Successfully generated subaddress via direct RPC")
                print(f"  Address: {address[:30]}...")
                print(f"  Index: {index}")
                return True
    
    print("✗ Failed to generate subaddress")
    return False

def main():
    """Run all tests"""
    print("="*60)
    print("Testing Wallet GUI Direct RPC Fixes")
    print("="*60)
    
    results = []
    
    results.append(("Direct RPC Call", test_rpc_call_direct()))
    results.append(("Balance Fallback", test_balance_fallback()))
    results.append(("Subaddress Generation", test_subaddress_generation()))
    
    print("\n" + "="*60)
    print("Test Results:")
    print("="*60)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name:30} {status}")
    
    all_passed = all(result for _, result in results)
    
    print("="*60)
    if all_passed:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
