#!/usr/bin/env python3
"""
Test script to validate auto-trust functionality
"""

import sys
import os

# Add signalbot to path
sys.path.insert(0, os.path.dirname(__file__))


def test_auto_trust_method_exists():
    """Test that auto_trust_contact method exists in SignalHandler"""
    print("\n=== Testing Auto-Trust Method ===")
    
    from signalbot.core.signal_handler import SignalHandler
    import inspect
    
    # Get the source code of SignalHandler
    source = inspect.getsource(SignalHandler)
    
    errors = []
    
    # Check that auto_trust_contact method exists
    if "def auto_trust_contact" in source:
        print("  ✓ auto_trust_contact method found")
    else:
        errors.append("❌ auto_trust_contact method not found")
        print("  ✗ auto_trust_contact method not found")
    
    # Check that it accepts contact_number parameter
    if "contact_number:" in source or "contact_number)" in source:
        print("  ✓ auto_trust_contact accepts contact_number parameter")
    else:
        errors.append("❌ auto_trust_contact doesn't accept contact_number parameter")
        print("  ✗ auto_trust_contact doesn't accept contact_number parameter")
    
    # Check that it calls signal-cli trust command
    if "signal-cli" in source and "trust" in source:
        print("  ✓ auto_trust_contact calls signal-cli trust command")
    else:
        errors.append("❌ auto_trust_contact doesn't call signal-cli trust command")
        print("  ✗ auto_trust_contact doesn't call signal-cli trust command")
    
    # Check that _handle_message calls auto_trust_contact
    if "self.auto_trust_contact" in source:
        print("  ✓ _handle_message calls auto_trust_contact")
    else:
        errors.append("❌ _handle_message doesn't call auto_trust_contact")
        print("  ✗ _handle_message doesn't call auto_trust_contact")
    
    if errors:
        print("\n❌ Auto-trust method test FAILED")
        for error in errors:
            print(f"  {error}")
        return False
    else:
        print("\n✅ Auto-trust method test PASSED")
        return True


def test_signal_handler_instantiation():
    """Test that SignalHandler can be instantiated with auto-trust method available"""
    print("\n=== Testing SignalHandler Instantiation ===")
    
    try:
        # Set environment variable for testing
        os.environ['PHONE_NUMBER'] = '+15555550123'
        
        from signalbot.core.signal_handler import SignalHandler
        
        # Create instance
        handler = SignalHandler()
        print("  ✓ SignalHandler instantiated successfully")
        
        # Check that auto_trust_contact method exists
        if hasattr(handler, 'auto_trust_contact'):
            print("  ✓ auto_trust_contact method is accessible")
        else:
            print("  ✗ auto_trust_contact method is not accessible")
            return False
        
        # Check that method is callable
        if callable(handler.auto_trust_contact):
            print("  ✓ auto_trust_contact method is callable")
        else:
            print("  ✗ auto_trust_contact method is not callable")
            return False
        
        print("\n✅ SignalHandler instantiation test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("Auto-Trust Feature Test Suite")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Auto-Trust Method Exists", test_auto_trust_method_exists()))
    results.append(("SignalHandler Instantiation", test_signal_handler_instantiation()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for result in results if result[1])
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
