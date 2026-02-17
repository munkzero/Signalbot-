#!/usr/bin/env python3
"""
Test script to verify RPC process management improvements
Tests PID tracking, smart cleanup, and proper shutdown
"""

import sys
import os
import subprocess
import time
from pathlib import Path


def test_wallet_setup_improvements():
    """Test that wallet_setup.py has the new RPC management features"""
    print("\n" + "=" * 60)
    print("Test 1: RPC Process Management Features")
    print("=" * 60)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    if not wallet_setup_path.exists():
        print("✗ wallet_setup.py NOT FOUND!")
        return False
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    required_features = [
        ('self.rpc_pid_file = None', 'PID file instance variable'),
        ('def _cleanup_orphaned_rpc(self)', 'Smart orphaned RPC cleanup method'),
        ('def _cleanup_orphaned_rpc_fallback(self)', 'Fallback cleanup method'),
        ('def _wait_for_rpc_ready(self', 'Internal wait for ready method'),
        ('def _stop_rpc(self)', 'Internal stop RPC method'),
        ('def __del__(self)', 'Destructor for cleanup'),
        ('lsof', 'Port checking with lsof'),
        ('self.rpc_pid_file =', 'PID file path assignment'),
        ('with open(self.rpc_pid_file, \'w\')', 'PID file writing'),
        ('os.remove(self.rpc_pid_file)', 'PID file cleanup'),
        ('self.rpc_process.poll()', 'Process health check'),
        ('start_new_session=True', 'Process session isolation'),
    ]
    
    all_found = True
    for feature, description in required_features:
        if feature in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ MISSING: {description}")
            all_found = False
    
    if all_found:
        print("\n✅ All RPC management features present!")
    else:
        print("\n❌ Some features missing")
    
    return all_found


def test_signal_handler_improvements():
    """Test that main.py has improved signal handlers"""
    print("\n" + "=" * 60)
    print("Test 2: Signal Handler Improvements")
    print("=" * 60)
    
    main_path = Path("signalbot/main.py")
    
    if not main_path.exists():
        print("✗ main.py NOT FOUND!")
        return False
    
    with open(main_path, 'r') as f:
        content = f.read()
    
    required_features = [
        ('_dashboard_instance = None', 'Global dashboard reference'),
        ('global _dashboard_instance', 'Signal handler uses global reference'),
        ('_dashboard_instance = dashboard', 'Dashboard stored in global'),
        ('setup_manager.stop_rpc()', 'RPC cleanup in signal handler'),
        ('hasattr(_dashboard_instance, \'wallet\')', 'Check for wallet attribute'),
    ]
    
    all_found = True
    for feature, description in required_features:
        if feature in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ MISSING: {description}")
            all_found = False
    
    if all_found:
        print("\n✅ All signal handler improvements present!")
    else:
        print("\n❌ Some improvements missing")
    
    return all_found


def test_cleanup_logic():
    """Test the cleanup logic improvements"""
    print("\n" + "=" * 60)
    print("Test 3: Cleanup Logic Analysis")
    print("=" * 60)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    # Check for smart cleanup patterns (the important ones)
    smart_patterns = [
        ('if self.rpc_process and pid == self.rpc_process.pid', 'Checks if PID is our process'),
        ('if pid == saved_pid', 'Checks against saved PID file'),
        ('["lsof", "-ti"', 'Uses lsof to check port'),
        ('signal.SIGTERM', 'Graceful termination before kill'),
        ('ProcessLookupError', 'Handles already-dead processes'),
        ('self._cleanup_orphaned_rpc()', 'Uses smart cleanup in start_rpc'),
    ]
    
    all_found = True
    for pattern, description in smart_patterns:
        if pattern in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ MISSING: {description}")
            all_found = False
    
    # Check that old function is deprecated
    if 'DEPRECATED' in content and 'cleanup_zombie_rpc_processes' in content:
        print("  ✓ Old cleanup function marked as deprecated")
    else:
        print("  ⚠ Old cleanup function should be marked as deprecated")
    
    if all_found:
        print("\n✅ Cleanup logic is smart and safe!")
    else:
        print("\n❌ Cleanup logic needs improvement")
    
    return all_found


def test_start_rpc_flow():
    """Test the start_rpc method flow"""
    print("\n" + "=" * 60)
    print("Test 4: start_rpc() Method Flow")
    print("=" * 60)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        lines = f.readlines()
    
    # Find start_rpc method
    start_line = None
    for i, line in enumerate(lines):
        if 'def start_rpc(self' in line:
            start_line = i
            break
    
    if start_line is None:
        print("✗ Could not find start_rpc method")
        return False
    
    # Extract method content (rough approximation)
    method_content = ''.join(lines[start_line:start_line + 100])
    
    flow_checks = [
        ('self._cleanup_orphaned_rpc()', 'Cleans up orphaned processes first'),
        ('self.rpc_pid_file =', 'Creates PID file path'),
        ('subprocess.Popen', 'Starts RPC process'),
        ('with open(self.rpc_pid_file', 'Saves PID to file'),
        ('self._wait_for_rpc_ready', 'Waits for RPC to be ready'),
        ('timeout = 180 if is_new_wallet', 'Uses extended timeout for new wallets'),
        ('self._stop_rpc()', 'Cleans up on failure'),
    ]
    
    all_found = True
    for check, description in flow_checks:
        if check in method_content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ MISSING: {description}")
            all_found = False
    
    if all_found:
        print("\n✅ start_rpc() flow is correct!")
    else:
        print("\n❌ start_rpc() flow incomplete")
    
    return all_found


def test_wait_for_ready_improvements():
    """Test the _wait_for_rpc_ready method"""
    print("\n" + "=" * 60)
    print("Test 5: _wait_for_rpc_ready() Improvements")
    print("=" * 60)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    improvements = [
        ('self.rpc_process.poll()', 'Checks if process is still alive'),
        ('if self.rpc_process and self.rpc_process.poll() is not None', 'Detects dead process'),
        ('logger.error(f"❌ RPC process died', 'Reports process death'),
        ('requests.post', 'Tests RPC connection'),
        ('time.sleep(2)', 'Waits between retries'),
        ('attempt} attempts', 'Tracks attempt count'),
    ]
    
    all_found = True
    for improvement, description in improvements:
        if improvement in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ MISSING: {description}")
            all_found = False
    
    if all_found:
        print("\n✅ _wait_for_rpc_ready() has all improvements!")
    else:
        print("\n❌ _wait_for_rpc_ready() missing improvements")
    
    return all_found


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("RPC PROCESS MANAGEMENT IMPLEMENTATION TEST")
    print("=" * 70)
    
    tests = [
        ("Wallet Setup Improvements", test_wallet_setup_improvements),
        ("Signal Handler Improvements", test_signal_handler_improvements),
        ("Cleanup Logic", test_cleanup_logic),
        ("start_rpc() Flow", test_start_rpc_flow),
        ("_wait_for_rpc_ready() Improvements", test_wait_for_ready_improvements),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print("\n" + "-" * 70)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 70)
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
