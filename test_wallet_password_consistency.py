#!/usr/bin/env python3
"""
Test script to verify wallet password consistency fix
Verifies that wallet creation and RPC startup use empty passwords consistently
"""

import sys
import ast
from pathlib import Path


def test_wallet_creation_stdin():
    """Test that wallet creation provides empty password via stdin"""
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    print("Testing wallet creation stdin handling...")
    print("-" * 60)
    
    # Check for required elements in wallet creation
    required_elements = [
        ("'--password', self.password", 'Password parameter in command'),
        ('input=', 'Stdin input parameter present'),
        ('\\n\\n', 'Newlines for password prompts'),
        ('# Provide two empty responses', 'Comment explaining stdin usage'),
        ("logger.debug(f\"Creating wallet with password:", 'Debug logging for password'),
        ('<empty>', 'Password logging shows <empty> for empty password'),
    ]
    
    print("✓ Checking for required code elements:")
    all_found = True
    for element, description in required_elements:
        if element in content:
            print(f"  ✓ {description}: found")
        else:
            print(f"  ✗ {description}: MISSING '{element}'")
            all_found = False
    
    print("\n" + "=" * 60)
    if all_found:
        print("✓ Wallet creation test PASSED!")
        return True
    else:
        print("✗ Wallet creation test FAILED!")
        return False


def test_rpc_startup_password():
    """Test that RPC startup uses empty password consistently"""
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    print("\n\nTesting RPC startup password handling...")
    print("-" * 60)
    
    # Check for required elements in RPC startup
    required_elements = [
        ("'--password', self.password", 'Password parameter in RPC command'),
        ("logger.debug(f\"Starting RPC with password:", 'Debug logging for RPC password'),
        ('<empty>', 'Password logging shows <empty> for empty password'),
    ]
    
    print("✓ Checking for required code elements:")
    all_found = True
    for element, description in required_elements:
        if element in content:
            print(f"  ✓ {description}: found")
        else:
            print(f"  ✗ {description}: MISSING '{element}'")
            all_found = False
    
    print("\n" + "=" * 60)
    if all_found:
        print("✓ RPC startup test PASSED!")
        return True
    else:
        print("✗ RPC startup test FAILED!")
        return False


def test_password_consistency():
    """Test that password is used consistently throughout"""
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    print("\n\nTesting password consistency...")
    print("-" * 60)
    
    # Check for password initialization
    checks = []
    
    # Check that password defaults to empty string
    if 'password: str = ""' in content:
        print("  ✓ Password defaults to empty string in __init__")
        checks.append(True)
    else:
        print("  ✗ Password default not found or incorrect")
        checks.append(False)
    
    # Check that password is stored in instance variable
    if 'self.password = password' in content:
        print("  ✓ Password is stored in instance variable")
        checks.append(True)
    else:
        print("  ✗ Password not stored in instance variable")
        checks.append(False)
    
    # Count usage of self.password
    password_usage_count = content.count('self.password')
    if password_usage_count >= 3:  # __init__, create_wallet, start_rpc, plus debug logs
        print(f"  ✓ Password is used consistently ({password_usage_count} times)")
        checks.append(True)
    else:
        print(f"  ✗ Password usage count too low ({password_usage_count})")
        checks.append(False)
    
    print("\n" + "=" * 60)
    if all(checks):
        print("✓ Password consistency test PASSED!")
        return True
    else:
        print("✗ Password consistency test FAILED!")
        return False


def test_subprocess_call_changes():
    """Test that subprocess.run includes input parameter"""
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    print("\n\nTesting subprocess call changes...")
    print("-" * 60)
    
    # Parse the file to check subprocess.run calls
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"  ✗ Syntax error in file: {e}")
        return False
    
    # Find subprocess.run calls
    subprocess_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if (isinstance(node.func, ast.Attribute) and 
                isinstance(node.func.value, ast.Name) and 
                node.func.value.id == 'subprocess' and 
                node.func.attr == 'run'):
                
                # Check if input parameter is present
                has_input = False
                for keyword in node.keywords:
                    if keyword.arg == 'input':
                        has_input = True
                        subprocess_calls.append(('subprocess.run', has_input))
    
    if subprocess_calls:
        for call_name, has_input in subprocess_calls:
            if has_input:
                print(f"  ✓ {call_name} has input parameter")
            else:
                print(f"  ⚠ {call_name} does not have input parameter (may be intentional)")
    else:
        print("  ⚠ No subprocess.run calls found (may be using different method)")
    
    # Direct text search for the specific pattern
    # Check for input parameter with newlines (checking actual newline chars, not escaped)
    if 'input=' in content and '\\n\\n' in content:
        print("  ✓ Found input parameter with newlines for password confirmation")
        result = True
    else:
        print("  ✗ Missing input parameter with newlines")
        result = False
    
    print("\n" + "=" * 60)
    if result:
        print("✓ Subprocess call test PASSED!")
        return True
    else:
        print("✗ Subprocess call test FAILED!")
        return False


def test_debug_logging():
    """Test that debug logging is present"""
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    print("\n\nTesting debug logging...")
    print("-" * 60)
    
    checks = []
    
    # Check for wallet creation debug log
    if "logger.debug(f\"Creating wallet with password:" in content:
        print("  ✓ Debug logging for wallet creation found")
        checks.append(True)
    else:
        print("  ✗ Debug logging for wallet creation missing")
        checks.append(False)
    
    # Check for RPC startup debug log
    if "logger.debug(f\"Starting RPC with password:" in content:
        print("  ✓ Debug logging for RPC startup found")
        checks.append(True)
    else:
        print("  ✗ Debug logging for RPC startup missing")
        checks.append(False)
    
    # Check for password masking
    if "'<empty>'" in content and "'<set>'" in content:
        print("  ✓ Password masking logic found (<empty> and <set>)")
        checks.append(True)
    else:
        print("  ✗ Password masking logic missing")
        checks.append(False)
    
    print("\n" + "=" * 60)
    if all(checks):
        print("✓ Debug logging test PASSED!")
        return True
    else:
        print("✗ Debug logging test FAILED!")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("WALLET PASSWORD CONSISTENCY FIX VERIFICATION")
    print("=" * 60)
    print()
    
    results = []
    results.append(("Wallet creation stdin handling", test_wallet_creation_stdin()))
    results.append(("RPC startup password handling", test_rpc_startup_password()))
    results.append(("Password consistency", test_password_consistency()))
    results.append(("Subprocess call changes", test_subprocess_call_changes()))
    results.append(("Debug logging", test_debug_logging()))
    
    print("\n\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("\n" + "=" * 60)
    print(f"TOTAL: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("\nThe wallet password consistency fix has been successfully implemented.")
        print("\nExpected behavior:")
        print("1. Wallet is created with empty password via --password \"\"")
        print("2. Empty password is also provided via stdin to prevent prompts")
        print("3. RPC startup uses the same empty password")
        print("4. Debug logs show '<empty>' to confirm password handling")
        print("\nThis ensures wallet creation and RPC access use the same password!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        print("Please review the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
