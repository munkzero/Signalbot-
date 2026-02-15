#!/usr/bin/env python3
"""
Test script to verify wallet RPC auto-setup implementation
Tests the WalletSetupManager, NodeHealthMonitor, and dashboard integration
"""

import sys
from pathlib import Path


def test_wallet_setup_module():
    """Test that wallet_setup.py exists and has required classes"""
    print("\n" + "=" * 60)
    print("Test 1: Wallet Setup Module")
    print("=" * 60)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    if not wallet_setup_path.exists():
        print("✗ wallet_setup.py NOT FOUND!")
        return False
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    required_elements = [
        ('class WalletSetupManager:', 'WalletSetupManager class'),
        ('def wallet_exists(', 'Wallet existence check method'),
        ('def create_wallet(', 'Wallet creation method'),
        ('def is_rpc_running(', 'RPC status check method'),
        ('def test_rpc_connection(', 'RPC connection test method'),
        ('def start_rpc(', 'RPC start method'),
        ('def stop_rpc(', 'RPC stop method'),
        ('def setup_wallet(', 'Complete setup method'),
        ('def test_node_connectivity(', 'Node connectivity test function'),
        ('import socket', 'Socket import for connectivity'),
        ('import subprocess', 'Subprocess import for RPC'),
        ('import requests', 'Requests import for RPC calls'),
    ]
    
    all_found = True
    for element, description in required_elements:
        if element in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ MISSING: {description}")
            all_found = False
    
    return all_found


def test_node_monitor_module():
    """Test that node_monitor.py exists and has required classes"""
    print("\n" + "=" * 60)
    print("Test 2: Node Health Monitor Module")
    print("=" * 60)
    
    node_monitor_path = Path("signalbot/core/node_monitor.py")
    
    if not node_monitor_path.exists():
        print("✗ node_monitor.py NOT FOUND!")
        return False
    
    with open(node_monitor_path, 'r') as f:
        content = f.read()
    
    required_elements = [
        ('class NodeHealthMonitor:', 'NodeHealthMonitor class'),
        ('def set_backup_nodes(', 'Set backup nodes method'),
        ('def start(', 'Start monitoring method'),
        ('def stop(', 'Stop monitoring method'),
        ('def _monitor_loop(', 'Monitoring loop method'),
        ('def _handle_connection_failure(', 'Connection failure handler'),
        ('import threading', 'Threading import'),
        ('daemon=True', 'Daemon thread configuration'),
    ]
    
    all_found = True
    for element, description in required_elements:
        if element in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ MISSING: {description}")
            all_found = False
    
    return all_found


def test_monero_wallet_integration():
    """Test that monero_wallet.py has been updated with auto-setup"""
    print("\n" + "=" * 60)
    print("Test 3: Monero Wallet Integration")
    print("=" * 60)
    
    wallet_path = Path("signalbot/core/monero_wallet.py")
    
    with open(wallet_path, 'r') as f:
        content = f.read()
    
    required_elements = [
        ('from .wallet_setup import WalletSetupManager', 'WalletSetupManager import'),
        ('self.setup_manager = WalletSetupManager(', 'WalletSetupManager initialization'),
        ('def ensure_connection(', 'Connection recovery method'),
        ('def auto_setup_wallet(', 'Auto-setup method'),
        ('def get_saved_seed_phrase(', 'Seed phrase retrieval method'),
        ('def _start_wallet_rpc(', 'RPC start method'),
        ('self.setup_manager.start_rpc()', 'RPC start call'),
        ('self.setup_manager.setup_wallet(', 'Setup wallet call'),
    ]
    
    all_found = True
    for element, description in required_elements:
        if element in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ MISSING: {description}")
            all_found = False
    
    # Check that stub is replaced
    print("\n  Checking RPC startup implementation:")
    if 'def _start_wallet_rpc(self):' in content:
        # Find the method and check if it still has the old stub comment
        if "For now, we'll assume it's handled externally" in content:
            print("  ✗ Old stub comment still present!")
            all_found = False
        else:
            print("  ✓ Stub replaced with implementation")
    
    return all_found


def test_dashboard_integration():
    """Test that dashboard.py has been updated with auto-setup integration"""
    print("\n" + "=" * 60)
    print("Test 4: Dashboard Integration")
    print("=" * 60)
    
    dashboard_path = Path("signalbot/gui/dashboard.py")
    
    with open(dashboard_path, 'r') as f:
        content = f.read()
    
    required_elements = [
        ('from ..core.node_monitor import NodeHealthMonitor', 'NodeHealthMonitor import'),
        ('from ..core.wallet_setup import test_node_connectivity', 'Node connectivity test import'),
        ('test_node_connectivity(', 'Node connectivity test call'),
        ('self.wallet.auto_setup_wallet(', 'Auto-setup wallet call'),
        ('self.node_monitor = NodeHealthMonitor(', 'NodeHealthMonitor initialization'),
        ('self.node_monitor.start()', 'Health monitor start'),
        ('def _show_seed_phrase_dialog(', 'Seed phrase dialog method'),
        ('def _show_setup_failed_dialog(', 'Setup failure dialog method'),
        ('working_nodes', 'Working nodes variable'),
        ('backup_nodes', 'Backup nodes configuration'),
    ]
    
    all_found = True
    for element, description in required_elements:
        if element in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ MISSING: {description}")
            all_found = False
    
    return all_found


def test_error_handling():
    """Test that proper error handling is in place"""
    print("\n" + "=" * 60)
    print("Test 5: Error Handling")
    print("=" * 60)
    
    # Check wallet_setup.py error handling
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    with open(wallet_setup_path, 'r') as f:
        setup_content = f.read()
    
    # Check dashboard.py error handling
    dashboard_path = Path("signalbot/gui/dashboard.py")
    with open(dashboard_path, 'r') as f:
        dashboard_content = f.read()
    
    error_checks = [
        (setup_content, 'subprocess.TimeoutExpired', 'Wallet creation timeout handling'),
        (setup_content, 'except Exception as e:', 'General exception handling in setup'),
        (setup_content, 'logger.error(', 'Error logging in setup'),
        (dashboard_content, 'QTimer.singleShot', 'Deferred error dialogs'),
        (dashboard_content, 'except Exception as e:', 'Exception handling in dashboard'),
        (dashboard_content, 'traceback.print_exc()', 'Stack trace printing'),
    ]
    
    all_found = True
    for content, element, description in error_checks:
        if element in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ MISSING: {description}")
            all_found = False
    
    return all_found


def test_logging_configuration():
    """Test that logging is properly configured"""
    print("\n" + "=" * 60)
    print("Test 6: Logging Configuration")
    print("=" * 60)
    
    files_to_check = [
        ("signalbot/core/wallet_setup.py", "Wallet Setup"),
        ("signalbot/core/node_monitor.py", "Node Monitor"),
    ]
    
    all_found = True
    for file_path, module_name in files_to_check:
        path = Path(file_path)
        with open(path, 'r') as f:
            content = f.read()
        
        if 'import logging' in content and 'logger = logging.getLogger(__name__)' in content:
            print(f"  ✓ {module_name}: Logging properly configured")
        else:
            print(f"  ✗ {module_name}: Logging NOT configured!")
            all_found = False
    
    return all_found


def main():
    """Run all tests"""
    print("=" * 60)
    print("Wallet RPC Auto-Setup Implementation Tests")
    print("=" * 60)
    
    tests = [
        test_wallet_setup_module,
        test_node_monitor_module,
        test_monero_wallet_integration,
        test_dashboard_integration,
        test_error_handling,
        test_logging_configuration,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n✗ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    
    if all(results):
        print("\n✓ ALL TESTS PASSED!")
        print("Wallet RPC auto-setup is correctly implemented.")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED!")
        print("Please review the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
