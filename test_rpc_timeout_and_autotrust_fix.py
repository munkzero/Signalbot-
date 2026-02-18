#!/usr/bin/env python3
"""
Test script to validate wallet RPC timeout and Signal auto-trust fixes
"""

import sys
import os
import inspect

# Add signalbot to path
sys.path.insert(0, os.path.dirname(__file__))


def test_wallet_rpc_timeout_fix():
    """Test that wallet RPC timeouts have been increased"""
    print("\n=== Testing Wallet RPC Timeout Fix ===")
    
    from signalbot.core.wallet_setup import WalletSetupManager
    
    # Get the source code of WalletSetupManager
    source = inspect.getsource(WalletSetupManager)
    
    errors = []
    
    # Check for increased timeout values
    if "timeout = 300 if is_new_wallet else 180" in source:
        print("  ✓ RPC timeouts increased (180s for existing, 300s for new wallets)")
    else:
        errors.append("❌ RPC timeouts not properly increased")
        print("  ✗ RPC timeouts not properly increased")
    
    # Check for daemon connectivity test
    if "Testing daemon connectivity" in source and "get_info" in source:
        print("  ✓ Daemon connectivity test added before RPC start")
    else:
        errors.append("❌ Daemon connectivity test missing")
        print("  ✗ Daemon connectivity test missing")
    
    # Check for progress logging in _wait_for_rpc_ready
    if "Still waiting..." in source and "elapsed" in source:
        print("  ✓ Progress logging added to RPC ready check")
    else:
        errors.append("❌ Progress logging missing from RPC ready check")
        print("  ✗ Progress logging missing from RPC ready check")
    
    # Check for informational message about wallet refresh
    if "RPC needs to refresh wallet" in source or "First startup may take" in source:
        print("  ✓ Informational messages about wallet refresh added")
    else:
        errors.append("❌ Informational messages about wallet refresh missing")
        print("  ✗ Informational messages about wallet refresh missing")
    
    if errors:
        print("\n❌ Wallet RPC timeout fix FAILED")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print("\n✅ Wallet RPC timeout fix PASSED")
        return True


def test_signal_autotrust_verification():
    """Test that Signal auto-trust verification has been added"""
    print("\n=== Testing Signal Auto-Trust Verification ===")
    
    from signalbot.core.signal_handler import SignalHandler
    
    # Get the source code of SignalHandler
    source = inspect.getsource(SignalHandler)
    
    errors = []
    
    # Check for _verify_auto_trust_config method
    if "def _verify_auto_trust_config(self)" in source:
        print("  ✓ _verify_auto_trust_config method added")
    else:
        errors.append("❌ _verify_auto_trust_config method missing")
        print("  ✗ _verify_auto_trust_config method missing")
    
    # Check that method is called in __init__
    if "_verify_auto_trust_config()" in source:
        print("  ✓ Auto-trust verification called in __init__")
    else:
        errors.append("❌ Auto-trust verification not called in __init__")
        print("  ✗ Auto-trust verification not called in __init__")
    
    # Check for config file path checking
    if "signal-cli/data/" in source and "trustNewIdentities" in source:
        print("  ✓ Signal config file verification implemented")
    else:
        errors.append("❌ Signal config file verification missing")
        print("  ✗ Signal config file verification missing")
    
    # Check for trust mode verification
    if "trust_mode == 'ALWAYS'" in source or 'trust_mode == "ALWAYS"' in source:
        print("  ✓ Trust mode ALWAYS verification added")
    else:
        errors.append("❌ Trust mode ALWAYS verification missing")
        print("  ✗ Trust mode ALWAYS verification missing")
    
    if errors:
        print("\n❌ Signal auto-trust verification FAILED")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print("\n✅ Signal auto-trust verification PASSED")
        return True


def test_start_sh_autotrust_autofix():
    """Test that start.sh has auto-trust auto-fix capability"""
    print("\n=== Testing start.sh Auto-Trust Auto-Fix ===")
    
    # Read start.sh
    start_sh_path = os.path.join(os.path.dirname(__file__), 'start.sh')
    try:
        with open(start_sh_path, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print("  ✗ start.sh not found")
        return False
    
    errors = []
    
    # Check for auto-fix attempt
    if "Attempting to fix..." in content:
        print("  ✓ Auto-fix attempt message added")
    else:
        errors.append("❌ Auto-fix attempt message missing")
        print("  ✗ Auto-fix attempt message missing")
    
    # Check for updateConfiguration command
    if "updateConfiguration --trust-new-identities always" in content:
        print("  ✓ signal-cli updateConfiguration command added")
    else:
        errors.append("❌ signal-cli updateConfiguration command missing")
        print("  ✗ signal-cli updateConfiguration command missing")
    
    # Check for fallback message
    if "using code-level fallback" in content or "code-level auto-trust" in content:
        print("  ✓ Code-level fallback message present")
    else:
        errors.append("❌ Code-level fallback message missing")
        print("  ✗ Code-level fallback message missing")
    
    # Check for check-trust.sh recommendation
    if "./check-trust.sh" in content:
        print("  ✓ check-trust.sh recommendation added")
    else:
        errors.append("❌ check-trust.sh recommendation missing")
        print("  ✗ check-trust.sh recommendation missing")
    
    if errors:
        print("\n❌ start.sh auto-trust auto-fix FAILED")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print("\n✅ start.sh auto-trust auto-fix PASSED")
        return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("Wallet RPC Timeout & Signal Auto-Trust Fix Tests")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Wallet RPC Timeout Fix", test_wallet_rpc_timeout_fix()))
    results.append(("Signal Auto-Trust Verification", test_signal_autotrust_verification()))
    results.append(("start.sh Auto-Trust Auto-Fix", test_start_sh_autotrust_autofix()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\n{passed}/{total} test suites passed")
    
    if passed == total:
        print("\n✅ All tests PASSED!")
        return 0
    else:
        print(f"\n❌ {total - passed} test suite(s) FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(main())
