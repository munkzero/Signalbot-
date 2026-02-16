#!/usr/bin/env python3
"""
Test script to verify wallet creation and PIN security features
"""

import sys
from pathlib import Path


def test_wallet_backup_method():
    """Test that backup_wallet method exists in wallet_setup.py"""
    print("\n" + "=" * 60)
    print("Test 1: Wallet Backup Method")
    print("=" * 60)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    if not wallet_setup_path.exists():
        print("✗ wallet_setup.py NOT FOUND!")
        return False
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    # Check for backup_wallet method
    if "def backup_wallet(self)" in content:
        print("  ✓ backup_wallet method exists")
    else:
        print("  ✗ backup_wallet method NOT FOUND")
        return False
    
    # Check for timestamp in backup
    if "datetime.now().strftime" in content:
        print("  ✓ Timestamp generation found")
    else:
        print("  ✗ Timestamp generation NOT FOUND")
        return False
    
    # Check for backup directory usage
    if "BACKUP_DIR" in content:
        print("  ✓ BACKUP_DIR configuration used")
    else:
        print("  ✗ BACKUP_DIR NOT USED")
        return False
    
    # Check for shutil.copy2 (file copying)
    if "shutil.copy2" in content or "shutil.copy" in content:
        print("  ✓ File copying implementation found")
    else:
        print("  ✗ File copying NOT FOUND")
        return False
    
    print("✓ Test PASSED")
    return True


def test_new_wallet_with_backup():
    """Test that create_new_wallet_with_backup method exists"""
    print("\n" + "=" * 60)
    print("Test 2: New Wallet Creation with Backup")
    print("=" * 60)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    # Check for create_new_wallet_with_backup method
    if "def create_new_wallet_with_backup(self)" in content:
        print("  ✓ create_new_wallet_with_backup method exists")
    else:
        print("  ✗ create_new_wallet_with_backup method NOT FOUND")
        return False
    
    # Check that it calls backup_wallet
    if "self.backup_wallet()" in content:
        print("  ✓ Calls backup_wallet method")
    else:
        print("  ✗ Does NOT call backup_wallet")
        return False
    
    # Check that it creates new wallet
    if "self.create_wallet()" in content:
        print("  ✓ Creates new wallet")
    else:
        print("  ✗ Does NOT create new wallet")
        return False
    
    print("✓ Test PASSED")
    return True


def test_pin_manager_module():
    """Test that PIN manager module exists and has required functionality"""
    print("\n" + "=" * 60)
    print("Test 3: PIN Manager Module")
    print("=" * 60)
    
    pin_manager_path = Path("signalbot/core/pin_manager.py")
    
    if not pin_manager_path.exists():
        print("✗ pin_manager.py NOT FOUND!")
        return False
    
    print("  ✓ pin_manager.py exists")
    
    with open(pin_manager_path, 'r') as f:
        content = f.read()
    
    # Check for PINVerificationSession class
    if "class PINVerificationSession" in content:
        print("  ✓ PINVerificationSession class exists")
    else:
        print("  ✗ PINVerificationSession class NOT FOUND")
        return False
    
    # Check for timeout functionality
    if "timeout_seconds" in content and "is_expired" in content:
        print("  ✓ Timeout functionality implemented")
    else:
        print("  ✗ Timeout functionality NOT FOUND")
        return False
    
    # Check for PINManager class
    if "class PINManager" in content:
        print("  ✓ PINManager class exists")
    else:
        print("  ✗ PINManager class NOT FOUND")
        return False
    
    # Check for session management methods
    required_methods = ["create_session", "get_session", "clear_session", "has_active_session"]
    all_found = True
    for method in required_methods:
        if f"def {method}" in content:
            print(f"  ✓ {method} method exists")
        else:
            print(f"  ✗ {method} method NOT FOUND")
            all_found = False
    
    if not all_found:
        return False
    
    print("✓ Test PASSED")
    return True


def test_buyer_handler_commands():
    """Test that buyer_handler has new wallet and send commands"""
    print("\n" + "=" * 60)
    print("Test 4: Buyer Handler Commands")
    print("=" * 60)
    
    buyer_handler_path = Path("signalbot/core/buyer_handler.py")
    
    if not buyer_handler_path.exists():
        print("✗ buyer_handler.py NOT FOUND!")
        return False
    
    with open(buyer_handler_path, 'r') as f:
        content = f.read()
    
    # Check for new wallet command handling
    if "'new wallet'" in content or '"new wallet"' in content:
        print("  ✓ New wallet command detection found")
    else:
        print("  ✗ New wallet command detection NOT FOUND")
        return False
    
    # Check for send command parsing
    if "_parse_send_command" in content:
        print("  ✓ Send command parsing method exists")
    else:
        print("  ✗ Send command parsing method NOT FOUND")
        return False
    
    # Check for PIN entry handling
    if "_handle_pin_entry" in content:
        print("  ✓ PIN entry handling method exists")
    else:
        print("  ✗ PIN entry handling method NOT FOUND")
        return False
    
    # Check for confirmation handling
    if "_handle_confirmation" in content:
        print("  ✓ Confirmation handling method exists")
    else:
        print("  ✗ Confirmation handling method NOT FOUND")
        return False
    
    # Check for settings menu
    if "send_settings_menu" in content:
        print("  ✓ Settings menu method exists")
    else:
        print("  ✗ Settings menu method NOT FOUND")
        return False
    
    # Check for wallet_manager and seller_manager in __init__
    if "wallet_manager" in content and "seller_manager" in content:
        print("  ✓ wallet_manager and seller_manager parameters added")
    else:
        print("  ✗ wallet_manager or seller_manager NOT FOUND")
        return False
    
    # Check for PIN manager import
    if "from .pin_manager import pin_manager" in content:
        print("  ✓ PIN manager imported")
    else:
        print("  ✗ PIN manager NOT imported")
        return False
    
    print("✓ Test PASSED")
    return True


def test_transaction_execution():
    """Test that transaction execution methods exist"""
    print("\n" + "=" * 60)
    print("Test 5: Transaction Execution")
    print("=" * 60)
    
    buyer_handler_path = Path("signalbot/core/buyer_handler.py")
    
    with open(buyer_handler_path, 'r') as f:
        content = f.read()
    
    # Check for execute_send_transaction method
    if "_execute_send_transaction" in content:
        print("  ✓ _execute_send_transaction method exists")
    else:
        print("  ✗ _execute_send_transaction method NOT FOUND")
        return False
    
    # Check for RPC transaction call
    if '"method": "transfer"' in content or "'method': 'transfer'" in content:
        print("  ✓ RPC transfer method call found")
    else:
        print("  ✗ RPC transfer method call NOT FOUND")
        return False
    
    # Check for amount conversion to atomic units
    if "1e12" in content:
        print("  ✓ XMR to atomic units conversion found")
    else:
        print("  ✗ XMR to atomic units conversion NOT FOUND")
        return False
    
    # Check for execute_new_wallet method
    if "_execute_new_wallet" in content:
        print("  ✓ _execute_new_wallet method exists")
    else:
        print("  ✗ _execute_new_wallet method NOT FOUND")
        return False
    
    # Check that it calls create_new_wallet_with_backup
    if "create_new_wallet_with_backup" in content:
        print("  ✓ Calls create_new_wallet_with_backup")
    else:
        print("  ✗ Does NOT call create_new_wallet_with_backup")
        return False
    
    print("✓ Test PASSED")
    return True


def test_empty_password_consistency():
    """Test that wallet password remains empty as per PR #35"""
    print("\n" + "=" * 60)
    print("Test 6: Empty Password Consistency (PR #35)")
    print("=" * 60)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    # Check for password parameter default
    if 'password: str = ""' in content or "password: str = ''" in content:
        print("  ✓ Default empty password found in __init__")
    else:
        print("  ✗ Default password NOT empty")
        return False
    
    # Check that wallet creation uses the password parameter
    if "'--password', self.password" in content or '"--password", self.password' in content:
        print("  ✓ Wallet creation uses password parameter")
    else:
        print("  ✗ Wallet creation does NOT use password parameter")
        return False
    
    print("✓ Test PASSED")
    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("WALLET CREATION AND PIN SECURITY FEATURE TESTS")
    print("=" * 60)
    
    tests = [
        test_wallet_backup_method,
        test_new_wallet_with_backup,
        test_pin_manager_module,
        test_buyer_handler_commands,
        test_transaction_execution,
        test_empty_password_consistency
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
            print(f"  ✗ Test FAILED with exception: {e}")
            failed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"  Passed: {passed}/{len(tests)}")
    print(f"  Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n✓ ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n✗ {failed} TEST(S) FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
