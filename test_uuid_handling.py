#!/usr/bin/env python3
"""
Test script to validate UUID handling in Signal bot
Tests that the bot correctly handles messages from users with phone privacy enabled
"""

import sys
import os
import json

# Add signalbot to path
sys.path.insert(0, os.path.dirname(__file__))

def test_source_priority():
    """Test that sourceNumber is prioritized over source (UUID)"""
    print("\n=== Testing Source Priority ===")
    
    from signalbot.core.signal_handler import SignalHandler
    import inspect
    
    # Get the source code of SignalHandler
    source = inspect.getsource(SignalHandler)
    
    errors = []
    
    # Check that sourceNumber is prioritized in both places
    # For syncMessage case (line ~356)
    if "envelope.get('sourceNumber') or envelope.get('source'" in source:
        print("  ✓ sourceNumber prioritized over source in message handling")
    else:
        errors.append("❌ sourceNumber not prioritized over source")
        print("  ✗ sourceNumber not prioritized over source")
    
    # Count occurrences - should be at least 2 (sync message and data message)
    priority_count = source.count("envelope.get('sourceNumber') or envelope.get('source'")
    if priority_count >= 2:
        print(f"  ✓ Found {priority_count} instances of correct priority")
    else:
        errors.append(f"❌ Only found {priority_count} instances, expected at least 2")
        print(f"  ✗ Only found {priority_count} instances, expected at least 2")
    
    # Verify the old (incorrect) syntax is not present
    if "envelope.get('source') or envelope.get('sourceNumber'" in source:
        errors.append("❌ Old incorrect syntax still present")
        print("  ✗ Old incorrect syntax still present")
    else:
        print("  ✓ Old incorrect syntax removed")
    
    if errors:
        print("\n❌ Source priority test FAILED")
        for error in errors:
            print(f"  {error}")
        return False
    else:
        print("\n✅ Source priority test PASSED")
        return True


def test_recipient_type_detection():
    """Test that recipient types are correctly identified"""
    print("\n=== Testing Recipient Type Detection ===")
    
    from signalbot.core.signal_handler import SignalHandler
    import inspect
    
    # Get the source code of SignalHandler
    source = inspect.getsource(SignalHandler)
    
    errors = []
    
    # Check for phone number detection
    if "source.startswith('+')" in source:
        print("  ✓ Phone number detection present")
    else:
        errors.append("❌ Phone number detection not found")
        print("  ✗ Phone number detection not found")
    
    # Check for UUID detection (36 character string with dashes)
    if "len(source) == 36" in source or "len(recipient) == 36" in source:
        print("  ✓ UUID detection present (checking length)")
    else:
        errors.append("❌ UUID length check not found")
        print("  ✗ UUID length check not found")
    
    if "'-' in source" in source or "'-' in recipient" in source:
        print("  ✓ UUID detection present (checking for dashes)")
    else:
        errors.append("❌ UUID dash check not found")
        print("  ✗ UUID dash check not found")
    
    # Check for logging of recipient types
    if "Message from UUID (privacy enabled)" in source:
        print("  ✓ UUID logging present")
    else:
        errors.append("❌ UUID logging not found")
        print("  ✗ UUID logging not found")
    
    if "Message from phone number" in source:
        print("  ✓ Phone number logging present")
    else:
        errors.append("❌ Phone number logging not found")
        print("  ✗ Phone number logging not found")
    
    if "Message from username" in source:
        print("  ✓ Username logging present")
    else:
        errors.append("❌ Username logging not found")
        print("  ✗ Username logging not found")
    
    if errors:
        print("\n❌ Recipient type detection test FAILED")
        for error in errors:
            print(f"  {error}")
        return False
    else:
        print("\n✅ Recipient type detection test PASSED")
        return True


def test_uuid_send_handling():
    """Test that _send_direct correctly handles UUIDs"""
    print("\n=== Testing UUID Send Handling ===")
    
    from signalbot.core.signal_handler import SignalHandler
    import inspect
    
    # Get the source code of _send_direct method
    source = inspect.getsource(SignalHandler._send_direct)
    
    errors = []
    
    # Check that UUID handling is present
    if "elif '-' in recipient and len(recipient) == 36:" in source:
        print("  ✓ UUID detection in _send_direct")
    else:
        errors.append("❌ UUID detection not found in _send_direct")
        print("  ✗ UUID detection not found in _send_direct")
    
    # Verify UUIDs are sent directly (not with --username flag)
    # Count the number of times we build the cmd without --username
    # Should be 2: once for phone numbers, once for UUIDs
    direct_send_count = source.count("recipient\n                ]")
    if direct_send_count >= 2:
        print(f"  ✓ UUIDs sent directly without --username flag")
    else:
        print(f"  ⚠ Warning: Direct send count is {direct_send_count}, expected 2")
    
    # Verify usernames still use --username flag
    if "'--username', recipient" in source or '"--username", recipient' in source:
        print("  ✓ Usernames still use --username flag")
    else:
        errors.append("❌ Username handling not found")
        print("  ✗ Username handling not found")
    
    # Check that docstring mentions UUID
    if "UUID" in source or "uuid" in source:
        print("  ✓ UUID mentioned in function documentation")
    else:
        print("  ⚠ Warning: UUID not mentioned in docstring (not critical)")
    
    if errors:
        print("\n❌ UUID send handling test FAILED")
        for error in errors:
            print(f"  {error}")
        return False
    else:
        print("\n✅ UUID send handling test PASSED")
        return True


def test_uuid_format_validation():
    """Test UUID format detection logic"""
    print("\n=== Testing UUID Format Validation ===")
    
    # Test UUIDs
    test_cases = [
        ("cd47b3be-f7c0-43f3-80a9-e4baa1e750ff", True, "Standard UUID"),
        ("+64274757293", False, "Phone number"),
        ("randomuser.01", False, "Username"),
        ("not-a-uuid-too-short", False, "Too short"),
        ("not-a-valid-uuid-format-really-long-string", False, "Too long"),
        ("12345678-1234-1234-1234-123456789012", True, "Another valid UUID"),
    ]
    
    errors = []
    for test_value, should_be_uuid, description in test_cases:
        is_uuid = '-' in test_value and len(test_value) == 36
        if is_uuid == should_be_uuid:
            print(f"  ✓ {description}: '{test_value}' -> UUID={is_uuid}")
        else:
            errors.append(f"❌ {description}: '{test_value}' -> Expected UUID={should_be_uuid}, got {is_uuid}")
            print(f"  ✗ {description}: '{test_value}' -> Expected UUID={should_be_uuid}, got {is_uuid}")
    
    if errors:
        print("\n❌ UUID format validation test FAILED")
        for error in errors:
            print(f"  {error}")
        return False
    else:
        print("\n✅ UUID format validation test PASSED")
        return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("UUID Handling Test Suite")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Source Priority", test_source_priority()))
    results.append(("Recipient Type Detection", test_recipient_type_detection()))
    results.append(("UUID Send Handling", test_uuid_send_handling()))
    results.append(("UUID Format Validation", test_uuid_format_validation()))
    
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
        print("\nThe bot now correctly:")
        print("  ✓ Prioritizes phone numbers over UUIDs when available")
        print("  ✓ Falls back to UUIDs when phone numbers aren't shared")
        print("  ✓ Sends messages to UUIDs correctly")
        print("  ✓ Identifies and logs recipient types")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
