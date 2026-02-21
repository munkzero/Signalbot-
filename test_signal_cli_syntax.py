#!/usr/bin/env python3
"""
Test script to validate signal-cli syntax fixes
"""

import sys
import os
import subprocess

# Add signalbot to path
sys.path.insert(0, os.path.dirname(__file__))


def test_signal_cli_syntax():
    """Test that signal-cli commands use correct 0.13.x syntax"""
    print("\n=== Testing signal-cli Command Syntax ===")
    
    from signalbot.core.signal_handler import SignalHandler
    import inspect
    
    # Get the source code of SignalHandler
    source = inspect.getsource(SignalHandler)
    
    # Check that old (invalid) syntax is not used
    errors = []
    
    # Check that invalid --output flag is not present
    if "'--output', 'json'" in source or '"--output", "json"' in source:
        errors.append("❌ Invalid syntax found: '--output json'")
        print("  ✗ Found invalid '--output json' syntax")
    else:
        print("  ✓ Invalid '--output json' syntax not found")
    
    # Check for correct --json flag in receive command
    if '"receive", "--json"' in source or "'receive', '--json'" in source:
        print("  ✓ Correct syntax found: 'receive --json'")
    else:
        errors.append("❌ Correct syntax not found: 'receive --json'")
        print("  ✗ Correct syntax not found: 'receive --json'")
    
    # Check for error logging in receive
    if "signal-cli receive error" in source:
        print("  ✓ Debug logging added for receive errors")
    else:
        errors.append("❌ Debug logging not added for receive errors")
        print("  ✗ Debug logging not added for receive errors")
    
    if errors:
        print("\n❌ Signal-cli syntax test FAILED")
        for error in errors:
            print(f"  {error}")
        return False
    else:
        print("\n✅ Signal-cli syntax test PASSED")
        return True


def test_catalog_image_sending():
    """Test that catalog functions include image attachment logic"""
    print("\n=== Testing Catalog Image Sending ===")
    
    try:
        # Read source files directly to avoid PyQt5 dependency
        dashboard_path = os.path.join(os.path.dirname(__file__), 'signalbot', 'gui', 'dashboard.py')
        buyer_handler_path = os.path.join(os.path.dirname(__file__), 'signalbot', 'core', 'buyer_handler.py')
        
        with open(dashboard_path, 'r') as f:
            dashboard_source = f.read()
        
        with open(buyer_handler_path, 'r') as f:
            buyer_source = f.read()
        
        # Find send_catalog method in dashboard
        dashboard_catalog_start = dashboard_source.find('def send_catalog(self):')
        if dashboard_catalog_start == -1:
            print("  ✗ send_catalog method not found in dashboard")
            return False
        
        # Extract just the send_catalog method (approximate)
        dashboard_catalog_end = dashboard_source.find('\n    def ', dashboard_catalog_start + 10)
        if dashboard_catalog_end == -1:
            # If no next method found, extract till end of file
            dashboard_catalog_end = len(dashboard_source)
        dashboard_catalog_method = dashboard_source[dashboard_catalog_start:dashboard_catalog_end]
        
        # Find send_catalog method in buyer_handler
        buyer_catalog_start = buyer_source.find('def send_catalog(self,')
        if buyer_catalog_start == -1:
            print("  ✗ send_catalog method not found in buyer_handler")
            return False
        
        # Extract just the send_catalog method (approximate)
        buyer_catalog_end = buyer_source.find('\n    def ', buyer_catalog_start + 10)
        if buyer_catalog_end == -1:
            # If no next method found, extract till end of file
            buyer_catalog_end = len(buyer_source)
        buyer_catalog_method = buyer_source[buyer_catalog_start:buyer_catalog_end]
        
        checks_passed = []
        
        # Check for image_path check in dashboard
        if "product.image_path" in dashboard_catalog_method:
            print("  ✓ Dashboard checks product.image_path")
            checks_passed.append(True)
        else:
            print("  ✗ Dashboard doesn't check product.image_path")
            checks_passed.append(False)
        
        # Check for os.path.exists in dashboard
        if "os.path.exists" in dashboard_catalog_method:
            print("  ✓ Dashboard validates image file exists")
            checks_passed.append(True)
        else:
            print("  ✗ Dashboard doesn't validate image file exists")
            checks_passed.append(False)
        
        # Check for attachments parameter in dashboard
        if "attachments" in dashboard_catalog_method:
            print("  ✓ Dashboard passes attachments to send_message")
            checks_passed.append(True)
        else:
            print("  ✗ Dashboard doesn't pass attachments to send_message")
            checks_passed.append(False)
        
        # Check for image_path check in buyer_handler
        if "product.image_path" in buyer_catalog_method:
            print("  ✓ BuyerHandler checks product.image_path")
            checks_passed.append(True)
        else:
            print("  ✗ BuyerHandler doesn't check product.image_path")
            checks_passed.append(False)
        
        # Check for os.path.exists in buyer_handler
        if "os.path.exists" in buyer_catalog_method:
            print("  ✓ BuyerHandler validates image file exists")
            checks_passed.append(True)
        else:
            print("  ✗ BuyerHandler doesn't validate image file exists")
            checks_passed.append(False)
        
        # Check for attachments parameter in buyer_handler
        if "attachments" in buyer_catalog_method:
            print("  ✓ BuyerHandler passes attachments to send_message")
            checks_passed.append(True)
        else:
            print("  ✗ BuyerHandler doesn't pass attachments to send_message")
            checks_passed.append(False)
        
        if all(checks_passed):
            print("\n✅ Catalog image sending test PASSED")
            return True
        else:
            print("\n❌ Catalog image sending test FAILED")
            return False
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("Signal-cli Syntax Fix Test Suite")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Signal-cli Syntax", test_signal_cli_syntax()))
    results.append(("Catalog Image Sending", test_catalog_image_sending()))
    
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
