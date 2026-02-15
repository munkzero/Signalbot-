#!/usr/bin/env python3
"""
Test script to verify the auto-wallet creation fix
Verifies that create_if_missing=True is set in dashboard.py
"""

import sys
from pathlib import Path


def test_dashboard_auto_wallet_creation():
    """Test that dashboard.py calls auto_setup_wallet with create_if_missing=True"""
    print("\n" + "=" * 60)
    print("Test: Dashboard Auto-Wallet Creation Fix")
    print("=" * 60)
    
    dashboard_path = Path("signalbot/gui/dashboard.py")
    
    if not dashboard_path.exists():
        print("✗ dashboard.py NOT FOUND!")
        return False
    
    with open(dashboard_path, 'r') as f:
        content = f.read()
    
    # Check that the correct call is present
    correct_call = "self.wallet.auto_setup_wallet(create_if_missing=True)"
    wrong_call = "self.wallet.auto_setup_wallet(create_if_missing=False)"
    
    if correct_call in content:
        print(f"  ✓ Found correct call: {correct_call}")
        has_correct = True
    else:
        print(f"  ✗ MISSING correct call: {correct_call}")
        has_correct = False
    
    if wrong_call in content:
        print(f"  ✗ FOUND INCORRECT CALL: {wrong_call}")
        print(f"     This will prevent auto-wallet creation!")
        has_wrong = True
    else:
        print(f"  ✓ No incorrect calls found")
        has_wrong = False
    
    # Additional checks
    print("\nAdditional verification:")
    
    # Ensure the auto_setup_wallet method is called
    if "auto_setup_wallet(" in content:
        print("  ✓ auto_setup_wallet method is called")
    else:
        print("  ✗ auto_setup_wallet method is not called")
        return False
    
    # Check that seed phrase handling is present (for when wallet is created)
    if "seed_phrase" in content and "_show_seed_phrase_dialog" in content:
        print("  ✓ Seed phrase handling is present")
    else:
        print("  ⚠ Seed phrase handling may be missing")
    
    print("\n" + "=" * 60)
    
    if has_correct and not has_wrong:
        print("✅ TEST PASSED!")
        print("Auto-wallet creation feature is properly configured.")
        return True
    else:
        print("❌ TEST FAILED!")
        if not has_correct:
            print("Missing correct call to auto_setup_wallet(create_if_missing=True)")
        if has_wrong:
            print("Found incorrect call with create_if_missing=False")
        return False


def test_wallet_setup_defaults():
    """Test that both setup methods have correct defaults"""
    print("\n" + "=" * 60)
    print("Test: Auto-Setup Default Parameters")
    print("=" * 60)
    
    all_passed = True
    
    # Check WalletSetupManager.setup_wallet
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    if not wallet_setup_path.exists():
        print("✗ wallet_setup.py NOT FOUND!")
        all_passed = False
    else:
        with open(wallet_setup_path, 'r') as f:
            content = f.read()
        
        # Check that setup_wallet has create_if_missing=True as default
        if "def setup_wallet(self, create_if_missing: bool = True)" in content:
            print("  ✓ WalletSetupManager.setup_wallet() has create_if_missing=True as default")
        elif "def setup_wallet(self, create_if_missing: bool = False)" in content:
            print("  ⚠ WalletSetupManager.setup_wallet() has create_if_missing=False as default")
            print("     This is not ideal but works if auto_setup_wallet passes True explicitly")
        else:
            print("  ✗ Could not find WalletSetupManager.setup_wallet method signature")
            all_passed = False
    
    # Check InHouseWallet.auto_setup_wallet
    monero_wallet_path = Path("signalbot/core/monero_wallet.py")
    
    if not monero_wallet_path.exists():
        print("✗ monero_wallet.py NOT FOUND!")
        all_passed = False
    else:
        with open(monero_wallet_path, 'r') as f:
            content = f.read()
        
        # Check that auto_setup_wallet has create_if_missing=True as default
        if "def auto_setup_wallet(self, create_if_missing: bool = True)" in content:
            print("  ✓ InHouseWallet.auto_setup_wallet() has create_if_missing=True as default")
        elif "def auto_setup_wallet(self, create_if_missing: bool = False)" in content:
            print("  ✗ InHouseWallet.auto_setup_wallet() has create_if_missing=False as default")
            print("     This will prevent auto-creation if dashboard doesn't explicitly pass True!")
            all_passed = False
        else:
            print("  ✗ Could not find InHouseWallet.auto_setup_wallet method signature")
            all_passed = False
    
    return all_passed


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("WALLET AUTO-CREATION FIX VERIFICATION")
    print("=" * 70)
    
    results = []
    
    # Run tests
    results.append(("Dashboard Auto-Wallet Creation", test_dashboard_auto_wallet_creation()))
    results.append(("Auto-Setup Default Parameters", test_wallet_setup_defaults()))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("\n" + "=" * 70)
    print(f"TOTAL: {passed}/{total} tests passed")
    print("=" * 70)
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! The auto-wallet creation fix is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
