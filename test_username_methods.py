#!/usr/bin/env python3
"""
Test the new username management methods in SignalHandler

This test verifies that the new methods work without requiring actual signal-cli
"""

import sys
import os

# Add signalbot to path
sys.path.insert(0, os.path.dirname(__file__))

from signalbot.core.signal_handler import SignalHandler


def test_username_methods_exist():
    """Test that the new methods exist"""
    print("\n" + "="*70)
    print("Test 1: Verify New Methods Exist")
    print("="*70)
    
    handler = SignalHandler(phone_number="+64274757293")
    
    methods = [
        'get_username',
        'set_username',
        'get_username_link',
        'check_account_status'
    ]
    
    for method in methods:
        if hasattr(handler, method):
            print(f"  ✅ {method}() exists")
        else:
            print(f"  ❌ {method}() MISSING!")
            return False
    
    return True


def test_check_account_status():
    """Test check_account_status method"""
    print("\n" + "="*70)
    print("Test 2: Test check_account_status()")
    print("="*70)
    
    handler = SignalHandler(phone_number="+64274757293")
    
    try:
        status = handler.check_account_status()
        
        print(f"\n  Status returned: {type(status)}")
        print(f"  Keys: {list(status.keys())}")
        
        required_keys = ['phone_number', 'username', 'username_link', 'status']
        for key in required_keys:
            if key in status:
                print(f"  ✅ '{key}' present: {status[key]}")
            else:
                print(f"  ❌ '{key}' MISSING!")
                return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def test_graceful_failure():
    """Test that methods fail gracefully without signal-cli"""
    print("\n" + "="*70)
    print("Test 3: Test Graceful Failure (no signal-cli required)")
    print("="*70)
    
    handler = SignalHandler(phone_number="+64274757293")
    
    # These should not crash, even if signal-cli is not installed
    try:
        print("\n  Testing get_username()...")
        result = handler.get_username()
        print(f"    Result: {result} (None is expected if signal-cli not available)")
        
        print("\n  Testing get_username_link()...")
        result = handler.get_username_link()
        print(f"    Result: {result} (None is expected if signal-cli not available)")
        
        print("\n  Testing check_account_status()...")
        result = handler.check_account_status()
        print(f"    Result: {result}")
        print(f"    Has phone_number: {'phone_number' in result}")
        
        print("\n  ✅ All methods handle missing signal-cli gracefully")
        return True
        
    except Exception as e:
        print(f"\n  ❌ Method crashed: {e}")
        print(f"     Methods should not crash even without signal-cli!")
        return False


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║            Username Management Methods - Unit Tests               ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝

Testing the new username management methods added to SignalHandler.
These tests verify the API works correctly.
    """)
    
    results = []
    
    # Run tests
    results.append(("Methods Exist", test_username_methods_exist()))
    results.append(("check_account_status()", test_check_account_status()))
    results.append(("Graceful Failure", test_graceful_failure()))
    
    # Summary
    print("\n" + "="*70)
    print("Test Summary")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n  🎉 All tests passed!")
        print("\n  Next steps:")
        print("    1. Run: python diagnose_username_issue.py")
        print("    2. Follow recommendations to set username if needed")
        print("    3. Test with actual Signal account")
    else:
        print("\n  ⚠️  Some tests failed - please review output above")
    
    print("\n" + "="*70 + "\n")
    
    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
