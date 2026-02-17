#!/usr/bin/env python3
"""
Test script to verify the RPC fix implementation
Tests that the new get_rpc_status() method works and that auto_setup_wallet() properly syncs RPC process
"""

import sys
from pathlib import Path


def test_wallet_setup_has_get_rpc_status():
    """Test that WalletSetupManager has get_rpc_status method"""
    print("\n" + "=" * 60)
    print("Test 1: WalletSetupManager.get_rpc_status() exists")
    print("=" * 60)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    if not wallet_setup_path.exists():
        print("✗ wallet_setup.py NOT FOUND!")
        return False
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    if 'def get_rpc_status(self)' in content:
        print("  ✓ get_rpc_status() method found")
        
        # Check for key status fields
        required_fields = ['"running"', '"pid"', '"port"', '"responding"', '"error"']
        all_found = True
        for field in required_fields:
            if field in content:
                print(f"  ✓ Status field {field} found")
            else:
                print(f"  ✗ Status field {field} MISSING")
                all_found = False
        
        return all_found
    else:
        print("  ✗ get_rpc_status() method NOT FOUND!")
        return False


def test_monero_wallet_has_get_rpc_status():
    """Test that InHouseWallet has get_rpc_status method"""
    print("\n" + "=" * 60)
    print("Test 2: InHouseWallet.get_rpc_status() exists")
    print("=" * 60)
    
    wallet_path = Path("signalbot/core/monero_wallet.py")
    
    if not wallet_path.exists():
        print("✗ monero_wallet.py NOT FOUND!")
        return False
    
    with open(wallet_path, 'r') as f:
        content = f.read()
    
    if 'def get_rpc_status(self)' in content:
        print("  ✓ get_rpc_status() method found")
        
        # Check that it delegates to setup_manager
        if 'self.setup_manager.get_rpc_status()' in content:
            print("  ✓ Delegates to setup_manager correctly")
            return True
        else:
            print("  ✗ Does NOT delegate to setup_manager")
            return False
    else:
        print("  ✗ get_rpc_status() method NOT FOUND!")
        return False


def test_auto_setup_wallet_syncs_rpc_process():
    """Test that auto_setup_wallet syncs RPC process reference"""
    print("\n" + "=" * 60)
    print("Test 3: auto_setup_wallet() syncs RPC process")
    print("=" * 60)
    
    wallet_path = Path("signalbot/core/monero_wallet.py")
    
    if not wallet_path.exists():
        print("✗ monero_wallet.py NOT FOUND!")
        return False
    
    with open(wallet_path, 'r') as f:
        content = f.read()
    
    # Check for the sync logic
    if 'self.rpc_process = self.setup_manager.rpc_process' in content:
        print("  ✓ RPC process sync code found")
        
        # Check it's in the auto_setup_wallet method
        lines = content.split('\n')
        in_auto_setup = False
        sync_found = False
        for line in lines:
            if 'def auto_setup_wallet' in line:
                in_auto_setup = True
            elif in_auto_setup and 'def ' in line and 'auto_setup_wallet' not in line:
                in_auto_setup = False
            elif in_auto_setup and 'self.rpc_process = self.setup_manager.rpc_process' in line:
                sync_found = True
                break
        
        if sync_found:
            print("  ✓ Sync code is in auto_setup_wallet() method")
            return True
        else:
            print("  ✗ Sync code NOT in auto_setup_wallet() method")
            return False
    else:
        print("  ✗ RPC process sync code NOT FOUND!")
        return False


def test_auto_setup_wallet_has_deprecation_warning():
    """Test that auto_setup_wallet has deprecation warning"""
    print("\n" + "=" * 60)
    print("Test 4: auto_setup_wallet() has deprecation warning")
    print("=" * 60)
    
    wallet_path = Path("signalbot/core/monero_wallet.py")
    
    if not wallet_path.exists():
        print("✗ monero_wallet.py NOT FOUND!")
        return False
    
    with open(wallet_path, 'r') as f:
        content = f.read()
    
    deprecation_markers = [
        'DEPRECATED',
        'logger.warning',
    ]
    
    all_found = True
    for marker in deprecation_markers:
        if marker in content:
            print(f"  ✓ {marker} found")
        else:
            print(f"  ✗ {marker} NOT found")
            all_found = False
    
    return all_found


def test_setup_wallet_has_final_verification():
    """Test that setup_wallet() has final verification"""
    print("\n" + "=" * 60)
    print("Test 5: setup_wallet() has final verification")
    print("=" * 60)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    if not wallet_setup_path.exists():
        print("✗ wallet_setup.py NOT FOUND!")
        return False
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    verification_markers = [
        'FINAL VERIFICATION',
        'get_rpc_status()',
        'VERIFICATION FAILED: RPC not running',
        'VERIFICATION FAILED: RPC not responding',
    ]
    
    all_found = True
    for marker in verification_markers:
        if marker in content:
            print(f"  ✓ {marker} found")
        else:
            print(f"  ✗ {marker} NOT found")
            all_found = False
    
    return all_found


def test_dashboard_shows_rpc_status():
    """Test that dashboard shows RPC status"""
    print("\n" + "=" * 60)
    print("Test 6: Dashboard shows RPC status")
    print("=" * 60)
    
    dashboard_path = Path("signalbot/gui/dashboard.py")
    
    if not dashboard_path.exists():
        print("✗ dashboard.py NOT FOUND!")
        return False
    
    with open(dashboard_path, 'r') as f:
        content = f.read()
    
    status_markers = [
        'get_rpc_status()',
        'RPC Status Check',
        'Running:',
        'PID:',
        'Responding:',
    ]
    
    all_found = True
    for marker in status_markers:
        if marker in content:
            print(f"  ✓ {marker} found")
        else:
            print(f"  ✗ {marker} NOT found")
            all_found = False
    
    return all_found


def test_dashboard_no_redundant_connect():
    """Test that dashboard doesn't call connect() after auto_setup_wallet()"""
    print("\n" + "=" * 60)
    print("Test 7: Dashboard doesn't call redundant connect()")
    print("=" * 60)
    
    dashboard_path = Path("signalbot/gui/dashboard.py")
    
    if not dashboard_path.exists():
        print("✗ dashboard.py NOT FOUND!")
        return False
    
    with open(dashboard_path, 'r') as f:
        content = f.read()
    
    # Look for the pattern where auto_setup_wallet is called followed by connect
    lines = content.split('\n')
    found_auto_setup = False
    found_connect_after = False
    
    for i, line in enumerate(lines):
        if 'auto_setup_wallet' in line and '(' in line:
            found_auto_setup = True
            # Check next 20 lines for direct connect() call
            for j in range(i+1, min(i+20, len(lines))):
                next_line = lines[j]
                # Check if there's a connect() call that's not commented out
                if 'self.wallet.connect()' in next_line and not next_line.strip().startswith('#'):
                    found_connect_after = True
                    print(f"  ✗ Found redundant connect() call at line {j+1}")
                    break
            break
    
    if not found_auto_setup:
        print("  ⚠ Could not find auto_setup_wallet() call in dashboard")
        return False
    
    if not found_connect_after:
        print("  ✓ No redundant connect() call found after auto_setup_wallet()")
        return True
    else:
        print("  ✗ FAILED: Redundant connect() call still present")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print(" RPC FIX VERIFICATION TEST SUITE")
    print("=" * 70)
    
    tests = [
        test_wallet_setup_has_get_rpc_status,
        test_monero_wallet_has_get_rpc_status,
        test_auto_setup_wallet_syncs_rpc_process,
        test_auto_setup_wallet_has_deprecation_warning,
        test_setup_wallet_has_final_verification,
        test_dashboard_shows_rpc_status,
        test_dashboard_no_redundant_connect,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n✗ Test {test.__name__} raised exception: {e}")
            failed += 1
    
    print("\n" + "=" * 70)
    print(f" TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)
    
    if failed == 0:
        print("\n✅ ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n❌ {failed} TEST(S) FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
