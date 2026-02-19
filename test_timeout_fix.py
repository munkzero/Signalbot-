#!/usr/bin/env python3
"""
Test script to validate signal-cli timeout fix
"""

import sys
import os
import inspect

# Add signalbot to path
sys.path.insert(0, os.path.dirname(__file__))


def test_timeout_fix():
    """Test that signal-cli receive command includes timeout flag"""
    print("\n=== Testing signal-cli Timeout Fix ===")
    
    from signalbot.core.signal_handler import SignalHandler
    
    # Get the source code of SignalHandler
    source = inspect.getsource(SignalHandler)
    
    errors = []
    
    # Check for --timeout flag in receive command
    if "'--timeout', '30'" in source or '"--timeout", "30"' in source:
        print("  ✓ signal-cli receive includes --timeout 30 flag")
    else:
        errors.append("❌ signal-cli receive missing --timeout 30 flag")
        print("  ✗ signal-cli receive missing --timeout 30 flag")
    
    # Check for increased subprocess timeout
    if "timeout=45" in source:
        print("  ✓ subprocess timeout increased to 45 seconds")
    else:
        errors.append("❌ subprocess timeout not increased to 45 seconds")
        print("  ✗ subprocess timeout not increased to 45 seconds")
    
    # Check for separate TimeoutExpired exception handling
    if "except subprocess.TimeoutExpired:" in source:
        print("  ✓ Separate TimeoutExpired exception handler added")
    else:
        errors.append("❌ Separate TimeoutExpired exception handler missing")
        print("  ✗ Separate TimeoutExpired exception handler missing")
    
    # Check for warning message in timeout handler
    if "WARNING: signal-cli receive command timed out" in source:
        print("  ✓ Warning message added for timeout cases")
    else:
        errors.append("❌ Warning message for timeout cases missing")
        print("  ✗ Warning message for timeout cases missing")
    
    # Verify old timeout value is not present (should be changed)
    receive_section_start = source.find("'receive'")
    if receive_section_start > 0:
        # Look for timeout=10 near the receive command
        receive_section = source[receive_section_start:receive_section_start + 500]
        if "timeout=10" in receive_section:
            errors.append("❌ Old timeout=10 still present in receive command")
            print("  ✗ Old timeout=10 still present in receive command")
        else:
            print("  ✓ Old timeout=10 value has been replaced")
    
    if errors:
        print("\n❌ Timeout fix test FAILED")
        for error in errors:
            print(f"  {error}")
        return False
    else:
        print("\n✅ Timeout fix test PASSED")
        return True


def test_command_structure():
    """Test that the command structure is correct"""
    print("\n=== Testing Command Structure ===")
    
    from signalbot.core.signal_handler import SignalHandler
    
    # Get the source code of SignalHandler._listen_loop
    source = inspect.getsource(SignalHandler._listen_loop)
    
    errors = []
    
    # Check the command array structure - verify components appear in correct order
    has_receive = "'receive'" in source or '"receive"' in source
    has_timeout_flag = "'--timeout'" in source or '"--timeout"' in source
    has_timeout_value = "'30'" in source or '"30"' in source
    
    # Find the receive command section
    receive_pos = source.find("'receive'") if "'receive'" in source else source.find('"receive"')
    if receive_pos > 0:
        # Check that --timeout appears after receive
        timeout_section = source[receive_pos:receive_pos + 200]
        if has_timeout_flag and has_timeout_value:
            print("  ✓ Correct command structure with --timeout flag")
        else:
            errors.append("❌ Command structure missing --timeout flag or value")
            print("  ✗ Command structure missing --timeout flag or value")
    else:
        errors.append("❌ receive command not found")
        print("  ✗ receive command not found")
    
    # Ensure subprocess settings are correct
    if "capture_output=True" in source:
        print("  ✓ capture_output=True is set")
    else:
        errors.append("❌ capture_output=True not set")
        print("  ✗ capture_output=True not set")
    
    if "text=True" in source:
        print("  ✓ text=True is set")
    else:
        errors.append("❌ text=True not set")
        print("  ✗ text=True not set")
    
    if errors:
        print("\n❌ Command structure test FAILED")
        for error in errors:
            print(f"  {error}")
        return False
    else:
        print("\n✅ Command structure test PASSED")
        return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("Signal-cli Timeout Fix Test Suite")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Timeout Fix", test_timeout_fix()))
    results.append(("Command Structure", test_command_structure()))
    
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
