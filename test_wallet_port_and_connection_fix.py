#!/usr/bin/env python3
"""
Test script to verify RPC port fix and wallet connection improvements.
Tests:
1. Port consistency between monero_wallet.py and wallet_setup.py (both 18083)
2. Wallet object initialization method exists in wallet_setup.py
3. Safe wallet methods exist in InHouseWallet (is_connected, address, new_address)
4. Dashboard uses safe wallet methods
"""

import sys
from pathlib import Path


def test_port_consistency():
    """Test that both files use port 18083"""
    print("\n" + "=" * 60)
    print("Test 1: Port Consistency (both should use 18083)")
    print("=" * 60)
    
    # Check monero_wallet.py
    wallet_path = Path("signalbot/core/monero_wallet.py")
    if not wallet_path.exists():
        print("✗ monero_wallet.py NOT FOUND!")
        return False
    
    with open(wallet_path, 'r') as f:
        wallet_content = f.read()
    
    # Check wallet_setup.py
    setup_path = Path("signalbot/core/wallet_setup.py")
    if not setup_path.exists():
        print("✗ wallet_setup.py NOT FOUND!")
        return False
    
    with open(setup_path, 'r') as f:
        setup_content = f.read()
    
    # Check for correct port in InHouseWallet
    if 'self.rpc_port = 18083' in wallet_content:
        print("  ✓ monero_wallet.py: InHouseWallet uses port 18083")
        wallet_ok = True
    else:
        print("  ✗ monero_wallet.py: InHouseWallet NOT using port 18083")
        wallet_ok = False
    
    # Check for correct port in WalletSetupManager default
    if 'rpc_port: int = 18083' in setup_content:
        print("  ✓ wallet_setup.py: WalletSetupManager default port is 18083")
        setup_ok = True
    else:
        print("  ✗ wallet_setup.py: WalletSetupManager default port NOT 18083")
        setup_ok = False
    
    # Check for old port references
    if '18082' in wallet_content and 'self.rpc_port = 18082' in wallet_content:
        print("  ✗ WARNING: Found old port 18082 in monero_wallet.py")
        wallet_ok = False
    
    if '18082' in setup_content and 'rpc_port: int = 18082' in setup_content:
        print("  ✗ WARNING: Found old port 18082 in wallet_setup.py")
        setup_ok = False
    
    return wallet_ok and setup_ok


def test_wallet_object_initialization():
    """Test that wallet object initialization method exists"""
    print("\n" + "=" * 60)
    print("Test 2: Wallet Object Initialization Method")
    print("=" * 60)
    
    setup_path = Path("signalbot/core/wallet_setup.py")
    if not setup_path.exists():
        print("✗ wallet_setup.py NOT FOUND!")
        return False
    
    with open(setup_path, 'r') as f:
        content = f.read()
    
    # Check for _initialize_wallet_object method
    if 'def _initialize_wallet_object(self)' in content:
        print("  ✓ _initialize_wallet_object() method found")
        
        # Check for key components
        checks = [
            ('from monero.wallet import Wallet', 'Wallet import'),
            ('from monero.backends.jsonrpc import JSONRPCWallet', 'JSONRPCWallet import'),
            ('self.wallet = Wallet(backend)', 'Wallet object creation'),
            ('self.wallet.address()', 'Connection test'),
        ]
        
        all_ok = True
        for check_str, description in checks:
            if check_str in content:
                print(f"  ✓ {description} found")
            else:
                print(f"  ✗ {description} MISSING")
                all_ok = False
        
        # Check it's called in setup_wallet
        if 'self._initialize_wallet_object()' in content:
            print("  ✓ Method called in setup_wallet()")
        else:
            print("  ✗ Method NOT called in setup_wallet()")
            all_ok = False
        
        return all_ok
    else:
        print("  ✗ _initialize_wallet_object() method NOT FOUND!")
        return False


def test_safe_wallet_methods():
    """Test that safe wallet methods exist in InHouseWallet"""
    print("\n" + "=" * 60)
    print("Test 3: Safe Wallet Methods in InHouseWallet")
    print("=" * 60)
    
    wallet_path = Path("signalbot/core/monero_wallet.py")
    if not wallet_path.exists():
        print("✗ monero_wallet.py NOT FOUND!")
        return False
    
    with open(wallet_path, 'r') as f:
        content = f.read()
    
    # Check for required methods
    methods = [
        ('def is_connected(self)', 'is_connected() method', [
            'if not self.wallet:',
            'self.wallet.address()',
            'self._connected = True',
        ]),
        ('def address(self, account: int = 0)', 'address() method', [
            'if not self.is_connected():',
            'return None',
        ]),
        ('def new_address(self, account: int = 0, label: str = "")', 'new_address() method', [
            'if not self.is_connected():',
            'raise Exception("Wallet not connected")',
        ]),
    ]
    
    all_ok = True
    for method_sig, description, key_parts in methods:
        if method_sig in content:
            print(f"  ✓ {description} found")
            
            # Check for key parts
            for part in key_parts:
                if part in content:
                    print(f"    ✓ Contains: {part[:50]}")
                else:
                    print(f"    ✗ Missing: {part[:50]}")
                    all_ok = False
        else:
            print(f"  ✗ {description} NOT FOUND!")
            all_ok = False
    
    # Check for _connected flag initialization
    if 'self._connected = False' in content:
        print("  ✓ _connected flag initialized")
    else:
        print("  ✗ _connected flag NOT initialized")
        all_ok = False
    
    # Check wallet object sync in auto_setup_wallet
    if 'self.wallet = self.setup_manager.wallet' in content:
        print("  ✓ Wallet object synced in auto_setup_wallet()")
    else:
        print("  ✗ Wallet object NOT synced in auto_setup_wallet()")
        all_ok = False
    
    return all_ok


def test_dashboard_safe_usage():
    """Test that dashboard uses safe wallet methods"""
    print("\n" + "=" * 60)
    print("Test 4: Dashboard Uses Safe Wallet Methods")
    print("=" * 60)
    
    dashboard_path = Path("signalbot/gui/dashboard.py")
    if not dashboard_path.exists():
        print("✗ dashboard.py NOT FOUND!")
        return False
    
    with open(dashboard_path, 'r') as f:
        content = f.read()
    
    # Check refresh_addresses uses safe address() method
    if 'self.wallet.address()' in content:
        print("  ✓ Uses self.wallet.address() method")
    else:
        print("  ✗ Does NOT use self.wallet.address() method")
        return False
    
    # Check generate_subaddress uses is_connected check
    if 'self.wallet.is_connected()' in content:
        print("  ✓ Checks wallet.is_connected()")
    else:
        print("  ✗ Does NOT check wallet.is_connected()")
        return False
    
    # Check generate_subaddress uses safe new_address() method
    if 'self.wallet.new_address(' in content:
        print("  ✓ Uses self.wallet.new_address() method")
    else:
        print("  ✗ Does NOT use self.wallet.new_address() method")
        return False
    
    return True


def test_monero_library_requirement():
    """Test that monero library is in requirements.txt"""
    print("\n" + "=" * 60)
    print("Test 5: Monero Library Requirement")
    print("=" * 60)
    
    req_path = Path("requirements.txt")
    if not req_path.exists():
        print("✗ requirements.txt NOT FOUND!")
        return False
    
    with open(req_path, 'r') as f:
        content = f.read()
    
    if 'monero>=1.1' in content:
        print("  ✓ monero>=1.1.0 found in requirements.txt")
        return True
    else:
        print("  ✗ monero library NOT found in requirements.txt")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("WALLET PORT AND CONNECTION FIX - TEST SUITE")
    print("=" * 60)
    
    results = []
    
    results.append(("Port Consistency", test_port_consistency()))
    results.append(("Wallet Object Init", test_wallet_object_initialization()))
    results.append(("Safe Wallet Methods", test_safe_wallet_methods()))
    results.append(("Dashboard Safe Usage", test_dashboard_safe_usage()))
    results.append(("Monero Library", test_monero_library_requirement()))
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("=" * 60)
    print(f"Total: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed > 0:
        print("\n❌ Some tests FAILED!")
        return 1
    else:
        print("\n✅ All tests PASSED!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
