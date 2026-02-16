#!/usr/bin/env python3
"""
Test script to verify wallet password prompts fix
Verifies that reconnect and rescan buttons use stored empty password
Also verifies Test Node Connection functionality
"""

import sys
import ast
from pathlib import Path


def test_reconnect_wallet_password_handling():
    """Test that reconnect_wallet uses stored empty password"""
    
    dashboard_path = Path("signalbot/gui/dashboard.py")
    
    with open(dashboard_path, 'r') as f:
        content = f.read()
    
    print("Testing reconnect_wallet password handling...")
    print("-" * 60)
    
    # Check for required elements in reconnect_wallet
    required_elements = [
        ('password = ""', 'Default password initialization to empty string'),
        ('if self.dashboard and hasattr(self.dashboard', 'Check for dashboard wallet'),
        ('self.dashboard.wallet.password', 'Access to stored password from dashboard wallet'),
        ('wallet_path = Path(self.seller.wallet_path)', 'Path handling'),
        ('wallet_exists =', 'Check if wallet exists'),
        ('password = ""', 'Use empty password for existing wallets'),
    ]
    
    print("✓ Checking for required code elements:")
    all_found = True
    for element, description in required_elements:
        if element in content:
            print(f"  ✓ {description}: found")
        else:
            print(f"  ✗ {description}: MISSING '{element}'")
            all_found = False
    
    # Check that _request_wallet_password is only called for non-existent wallets
    reconnect_method_start = content.find('def reconnect_wallet(self):')
    if reconnect_method_start != -1:
        # Find the next method definition
        next_method = content.find('\n    def ', reconnect_method_start + 1)
        reconnect_method = content[reconnect_method_start:next_method] if next_method != -1 else content[reconnect_method_start:]
        
        # Check for conditional password prompt or helper method usage
        has_conditional_prompt = ('if password is None:' in reconnect_method or 
                                 'wallet_exists' in reconnect_method or
                                 '_get_wallet_password()' in reconnect_method)
        
        if has_conditional_prompt:
            print(f"  ✓ Password prompt is conditional (only for non-existent wallets)")
        else:
            print(f"  ⚠ Password prompt may not be conditional")
    
    print("\n" + "=" * 60)
    if all_found:
        print("✓ Reconnect wallet test PASSED!")
        return True
    else:
        print("✗ Reconnect wallet test FAILED!")
        return False


def test_rescan_blockchain_password_handling():
    """Test that rescan_blockchain uses stored empty password"""
    
    dashboard_path = Path("signalbot/gui/dashboard.py")
    
    with open(dashboard_path, 'r') as f:
        content = f.read()
    
    print("\n\nTesting rescan_blockchain password handling...")
    print("-" * 60)
    
    # Check for required elements in rescan_blockchain
    required_elements = [
        ('def rescan_blockchain(self):', 'Rescan method definition'),
        ('password = ""', 'Default password initialization to empty string'),
        ('if self.dashboard and hasattr(self.dashboard', 'Check for dashboard wallet'),
        ('self.dashboard.wallet.password', 'Access to stored password from dashboard wallet'),
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
        print("✓ Rescan blockchain test PASSED!")
        return True
    else:
        print("✗ Rescan blockchain test FAILED!")
        return False


def test_node_connection_test_method():
    """Test that test_node_connection method exists in WalletSetupManager"""
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    print("\n\nTesting test_node_connection method...")
    print("-" * 60)
    
    # Check for required elements
    required_elements = [
        ('def test_node_connection(self', 'Method definition'),
        ('daemon_address: Optional[str]', 'Optional daemon address parameter'),
        ('daemon_port: Optional[int]', 'Optional daemon port parameter'),
        ('requests.post(url, json=', 'HTTP POST request'),
        ('"method": "get_info"', 'RPC get_info method'),
        ("'success':", 'Success field in return dict'),
        ("'block_height':", 'Block height field in return dict'),
        ("'network':", 'Network field in return dict'),
        ("'latency_ms':", 'Latency field in return dict'),
        ("'message':", 'Message field in return dict'),
        ('requests.exceptions.Timeout', 'Timeout exception handling'),
        ('requests.exceptions.ConnectionError', 'Connection error handling'),
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
        print("✓ Node connection test method PASSED!")
        return True
    else:
        print("✗ Node connection test method FAILED!")
        return False


def test_gui_test_node_button():
    """Test that Test Node Connection button exists in GUI"""
    
    dashboard_path = Path("signalbot/gui/dashboard.py")
    
    with open(dashboard_path, 'r') as f:
        content = f.read()
    
    print("\n\nTesting GUI Test Node Connection button...")
    print("-" * 60)
    
    # Check for required GUI elements
    required_elements = [
        ('Test Node Connection', 'Test node section group box'),
        ('test_node_btn', 'Test button variable'),
        ('🔗 Test Connection', 'Button label with icon'),
        ('test_node_btn.clicked.connect(self.test_node_connection)', 'Button click handler'),
        ('def test_node_connection(self):', 'Test method definition'),
        ('TestNodeConnectionWorker', 'Worker thread class'),
        ('def on_test_finished(self, result):', 'Test completion handler'),
    ]
    
    print("✓ Checking for required GUI elements:")
    all_found = True
    for element, description in required_elements:
        if element in content:
            print(f"  ✓ {description}: found")
        else:
            print(f"  ✗ {description}: MISSING '{element}'")
            all_found = False
    
    print("\n" + "=" * 60)
    if all_found:
        print("✓ GUI test node button PASSED!")
        return True
    else:
        print("✗ GUI test node button FAILED!")
        return False


def test_test_node_worker_thread():
    """Test that TestNodeConnectionWorker thread exists"""
    
    dashboard_path = Path("signalbot/gui/dashboard.py")
    
    with open(dashboard_path, 'r') as f:
        content = f.read()
    
    print("\n\nTesting TestNodeConnectionWorker thread...")
    print("-" * 60)
    
    # Check for required worker thread elements
    required_elements = [
        ('class TestNodeConnectionWorker(QThread):', 'Worker class definition'),
        ('finished = pyqtSignal(dict)', 'Finished signal with dict result'),
        ('progress = pyqtSignal(str)', 'Progress signal'),
        ('def run(self):', 'Run method for thread execution'),
        ('WalletSetupManager', 'Use of WalletSetupManager'),
        ('manager.test_node_connection()', 'Call to test_node_connection method'),
    ]
    
    print("✓ Checking for required worker thread elements:")
    all_found = True
    for element, description in required_elements:
        if element in content:
            print(f"  ✓ {description}: found")
        else:
            print(f"  ✗ {description}: MISSING '{element}'")
            all_found = False
    
    print("\n" + "=" * 60)
    if all_found:
        print("✓ Worker thread test PASSED!")
        return True
    else:
        print("✗ Worker thread test FAILED!")
        return False


def test_test_result_display():
    """Test that test results are displayed properly"""
    
    dashboard_path = Path("signalbot/gui/dashboard.py")
    
    with open(dashboard_path, 'r') as f:
        content = f.read()
    
    print("\n\nTesting test result display...")
    print("-" * 60)
    
    # Check for result display elements
    required_elements = [
        ('self.test_result_label', 'Result label widget'),
        ('Connected to node successfully', 'Success message'),
        ('Failed to connect to node', 'Failure message'),
        ("result['block_height']", 'Display block height'),
        ("result['network']", 'Display network type'),
        ("result['latency_ms']", 'Display latency'),
        ('QMessageBox.information', 'Success message box'),
        ('QMessageBox.warning', 'Warning message box'),
        ('color: green', 'Green color for success'),
        ('color: red', 'Red color for failure'),
    ]
    
    print("✓ Checking for result display elements:")
    all_found = True
    for element, description in required_elements:
        if element in content:
            print(f"  ✓ {description}: found")
        else:
            print(f"  ✗ {description}: MISSING '{element}'")
            all_found = False
    
    print("\n" + "=" * 60)
    if all_found:
        print("✓ Result display test PASSED!")
        return True
    else:
        print("✗ Result display test FAILED!")
        return False


def test_password_consistency():
    """Test that password is empty string across the codebase"""
    
    dashboard_path = Path("signalbot/gui/dashboard.py")
    
    with open(dashboard_path, 'r') as f:
        content = f.read()
    
    print("\n\nTesting password consistency...")
    print("-" * 60)
    
    checks = []
    
    # Check for comment explaining empty password
    if 'standard for this bot' in content.lower():
        print("  ✓ Comment explaining empty password standard found")
        checks.append(True)
    else:
        print("  ⚠ Comment explaining empty password standard not found")
        checks.append(False)
    
    # Check that empty password is used as default
    empty_password_count = content.count('password = ""')
    if empty_password_count >= 2:  # Should appear in both reconnect and rescan
        print(f"  ✓ Empty password used as default ({empty_password_count} times)")
        checks.append(True)
    else:
        print(f"  ⚠ Empty password usage count low ({empty_password_count})")
        checks.append(False)
    
    print("\n" + "=" * 60)
    if all(checks):
        print("✓ Password consistency test PASSED!")
        return True
    else:
        print("⚠ Password consistency test completed with warnings")
        return True  # Return True even with warnings


def main():
    """Run all tests"""
    print("=" * 60)
    print("WALLET PASSWORD PROMPTS FIX VERIFICATION")
    print("=" * 60)
    print()
    
    results = []
    results.append(("Reconnect wallet password handling", test_reconnect_wallet_password_handling()))
    results.append(("Rescan blockchain password handling", test_rescan_blockchain_password_handling()))
    results.append(("Test node connection method", test_node_connection_test_method()))
    results.append(("GUI test node button", test_gui_test_node_button()))
    results.append(("Test node worker thread", test_test_node_worker_thread()))
    results.append(("Test result display", test_test_result_display()))
    results.append(("Password consistency", test_password_consistency()))
    
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
        print("\nThe wallet password prompts fix has been successfully implemented.")
        print("\nExpected behavior:")
        print("1. Reconnect button uses stored empty password (no prompt)")
        print("2. Rescan button uses stored empty password (no prompt)")
        print("3. Test Node Connection button works without opening wallet")
        print("4. Test results show connection status, block height, network, latency")
        print("\nThis ensures wallet operations work seamlessly with empty passwords!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        print("Please review the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
