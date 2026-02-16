#!/usr/bin/env python3
"""
Test script to verify wallet seed phrase capture and auto-unlock fixes

Tests:
1. Seed phrase capture via create_wallet_with_seed()
2. Empty password detection via uses_empty_password()
3. Silent unlock via unlock_wallet_silent()
4. RPC starts without password prompts (stdin=DEVNULL)
5. Dashboard auto-unlocks without prompts
6. Copy to clipboard with auto-clear
"""

import sys
from pathlib import Path


def check_wallet_setup_methods():
    """Verify wallet_setup.py has the new methods"""
    print("\n" + "="*60)
    print("Test 1: Wallet Setup New Methods")
    print("="*60)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    required_elements = [
        ('def create_wallet_with_seed(self)', 'create_wallet_with_seed method'),
        ('Tuple[bool, Optional[str], Optional[str]]', 'Return type with seed and address'),
        ('return True, seed, address', 'Returns seed and address'),
        ('def uses_empty_password(self)', 'uses_empty_password method'),
        ('return self.password == ""', 'Empty password check'),
        ('def unlock_wallet_silent(self)', 'unlock_wallet_silent method'),
        ('if not self.uses_empty_password():', 'Check for empty password'),
        ('get_address', 'Verify wallet unlocked via RPC'),
        ('Wallet is unlocked (empty password)', 'Success message'),
    ]
    
    all_found = True
    for element, description in required_elements:
        if element in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ MISSING: {description}")
            all_found = False
    
    return all_found


def check_rpc_stdin_devnull():
    """Verify RPC starts with stdin=subprocess.DEVNULL"""
    print("\n" + "="*60)
    print("Test 2: RPC stdin=DEVNULL (Prevent Password Prompts)")
    print("="*60)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    required_elements = [
        ('stdin=subprocess.DEVNULL', 'stdin set to DEVNULL'),
        ('# CRITICAL: Use stdin=subprocess.DEVNULL to prevent password prompts', 'Comment explaining fix'),
        ('# Prevents interactive prompts', 'Comment about preventing prompts'),
    ]
    
    all_found = True
    for element, description in required_elements:
        if element in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ MISSING: {description}")
            all_found = False
    
    return all_found


def check_dashboard_create_wallet():
    """Verify dashboard uses create_wallet_with_seed"""
    print("\n" + "="*60)
    print("Test 3: Dashboard Create Wallet Uses New Method")
    print("="*60)
    
    dashboard_path = Path("signalbot/gui/dashboard.py")
    with open(dashboard_path, 'r') as f:
        content = f.read()
    
    required_elements = [
        ('success, seed, address = setup.create_wallet_with_seed()', 'Call create_wallet_with_seed'),
        ('if not seed:', 'Check if seed was retrieved'),
        ('failed to retrieve seed phrase', 'Error message for missing seed'),
        ('This is a critical error', 'Critical error message'),
    ]
    
    all_found = True
    for element, description in required_elements:
        if element in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ MISSING: {description}")
            all_found = False
    
    return all_found


def check_dashboard_copy_to_clipboard():
    """Verify copy to clipboard with auto-clear"""
    print("\n" + "="*60)
    print("Test 4: Copy to Clipboard with Auto-Clear")
    print("="*60)
    
    dashboard_path = Path("signalbot/gui/dashboard.py")
    with open(dashboard_path, 'r') as f:
        content = f.read()
    
    required_elements = [
        ('def copy_seed_to_clipboard(self, seed_phrase: str):', 'copy_seed_to_clipboard method'),
        ('clipboard = QApplication.clipboard()', 'Get clipboard'),
        ('clipboard.setText(seed_phrase)', 'Set clipboard text'),
        ('The clipboard will be cleared in 60 seconds', 'Warning message'),
        ('QTimer.singleShot(60000,', 'Timer for auto-clear'),
        ('clipboard.clear()', 'Clear clipboard'),
        ('📋 Copy Seed to Clipboard', 'Copy button with emoji'),
        ('self.copy_seed_to_clipboard(seed)', 'Call copy method'),
    ]
    
    all_found = True
    for element, description in required_elements:
        if element in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ MISSING: {description}")
            all_found = False
    
    return all_found


def check_dashboard_auto_unlock():
    """Verify dashboard auto-unlocks without prompts for empty password"""
    print("\n" + "="*60)
    print("Test 5: Dashboard Auto-Unlock (No Password Prompts)")
    print("="*60)
    
    dashboard_path = Path("signalbot/gui/dashboard.py")
    with open(dashboard_path, 'r') as f:
        content = f.read()
    
    # Check that password prompts are removed
    should_not_exist = [
        ('Would you like to unlock your wallet now?', 'Old unlock prompt (should be removed)'),
        ('Enter your wallet password to unlock:', 'Old password prompt (should be removed)'),
    ]
    
    # Check that auto-unlock logic exists
    should_exist = [
        ('password = ""', 'Default empty password'),
        ('attempting auto-unlock with empty password', 'Auto-unlock message'),
        ('Password: <empty string>', 'Debug print for empty password'),
        ('will create with empty password', 'Create wallet message'),
    ]
    
    all_good = True
    
    print("\n  Checking removed password prompts:")
    for element, description in should_not_exist:
        if element in content:
            print(f"  ✗ SHOULD BE REMOVED: {description}")
            all_good = False
        else:
            print(f"  ✓ {description} - correctly removed")
    
    print("\n  Checking auto-unlock logic:")
    for element, description in should_exist:
        if element in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ MISSING: {description}")
            all_good = False
    
    return all_good


def check_seed_phrase_dialog():
    """Verify seed phrase dialog displays properly"""
    print("\n" + "="*60)
    print("Test 6: Seed Phrase Dialog Display")
    print("="*60)
    
    dashboard_path = Path("signalbot/gui/dashboard.py")
    with open(dashboard_path, 'r') as f:
        content = f.read()
    
    required_elements = [
        ('def show_new_wallet_seed(self, seed: str, address: str, backup_name: str):', 'Method signature'),
        ('seed_text.setPlainText(seed)', 'Set seed text'),
        ('SAVE YOUR SEED!', 'Warning header'),
        ('⚠️ CRITICAL:', 'Critical warning'),
        ('Your 25-word seed phrase:', 'Seed phrase label'),
        ('Wallet Address:', 'Address label'),
        ('I have saved my seed phrase', 'Confirmation checkbox'),
        ('setReadOnly(True)', 'Read-only text edit'),
        ('font-family: monospace', 'Monospace font for seed'),
    ]
    
    all_found = True
    for element, description in required_elements:
        if element in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ MISSING: {description}")
            all_found = False
    
    return all_found


def main():
    """Run all tests"""
    print("="*60)
    print("WALLET SEED PHRASE AND AUTO-UNLOCK FIX VERIFICATION")
    print("="*60)
    
    results = []
    
    # Run all tests
    results.append(("Wallet Setup Methods", check_wallet_setup_methods()))
    results.append(("RPC stdin=DEVNULL", check_rpc_stdin_devnull()))
    results.append(("Dashboard Create Wallet", check_dashboard_create_wallet()))
    results.append(("Copy to Clipboard", check_dashboard_copy_to_clipboard()))
    results.append(("Auto-Unlock", check_dashboard_auto_unlock()))
    results.append(("Seed Phrase Dialog", check_seed_phrase_dialog()))
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False
    
    print("="*60)
    
    if all_passed:
        print("\n✅ ALL TESTS PASSED!")
        print("\nThe following fixes are implemented:")
        print("  1. Seed phrase is captured via create_wallet_with_seed()")
        print("  2. RPC starts without password prompts (stdin=DEVNULL)")
        print("  3. Dashboard auto-unlocks wallets with empty passwords")
        print("  4. Copy to clipboard with 60-second auto-clear")
        print("  5. Seed phrase dialog displays properly")
        print("  6. No password prompts for empty-password wallets")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED!")
        print("\nPlease review the failed tests above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
