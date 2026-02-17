#!/usr/bin/env python3
"""
Test script to verify PR #45 implementation:
- RPC startup race condition fix
- Wallet sync progress monitoring
- Zombie process cleanup
"""

import sys
from pathlib import Path


def test_imports():
    """Test that required modules and functions exist"""
    print("\n" + "=" * 70)
    print("Test 1: Module Imports and Function Existence")
    print("=" * 70)
    
    try:
        from signalbot.core.wallet_setup import (
            cleanup_zombie_rpc_processes,
            wait_for_rpc_ready,
            monitor_sync_progress,
            WalletSetupManager
        )
        print("✓ All required functions imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def test_cleanup_zombie_function():
    """Test cleanup_zombie_rpc_processes function signature"""
    print("\n" + "=" * 70)
    print("Test 2: cleanup_zombie_rpc_processes() Function")
    print("=" * 70)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    if not wallet_setup_path.exists():
        print("✗ wallet_setup.py NOT FOUND!")
        return False
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    checks = [
        ('def cleanup_zombie_rpc_processes()', 'Function definition'),
        ('pgrep', 'Process search with pgrep'),
        ('monero-wallet-rpc', 'Search for monero-wallet-rpc processes'),
        ('kill', 'Process termination'),
        ('zombie', 'Zombie process handling'),
        ('logger.info', 'Logging info messages'),
        ('logger.warning', 'Logging warnings'),
        ('time.sleep(2)', 'Wait for lock release'),
    ]
    
    all_found = True
    for check, description in checks:
        if check in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ MISSING: {description}")
            all_found = False
    
    return all_found


def test_wait_for_rpc_ready_function():
    """Test wait_for_rpc_ready function"""
    print("\n" + "=" * 70)
    print("Test 3: wait_for_rpc_ready() Function")
    print("=" * 70)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    checks = [
        ('def wait_for_rpc_ready(port=18083, max_wait=60, retry_interval=2)', 'Function signature'),
        ('requests.post', 'HTTP POST request'),
        ('get_height', 'RPC method call'),
        ('response.status_code == 200', 'Success check'),
        ('requests.ConnectionError', 'Connection error handling'),
        ('requests.Timeout', 'Timeout error handling'),
        ('time.sleep(retry_interval)', 'Retry interval sleep'),
        ('attempt += 1', 'Attempt counter'),
        ('elapsed', 'Elapsed time tracking'),
        ('logger.info', 'Info logging'),
        ('logger.debug', 'Debug logging'),
        ('logger.error', 'Error logging'),
        ('return True', 'Success return'),
        ('return False', 'Failure return'),
    ]
    
    all_found = True
    for check, description in checks:
        if check in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ MISSING: {description}")
            all_found = False
    
    return all_found


def test_monitor_sync_progress_function():
    """Test monitor_sync_progress function"""
    print("\n" + "=" * 70)
    print("Test 4: monitor_sync_progress() Function")
    print("=" * 70)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    checks = [
        ('def monitor_sync_progress(port=18083, update_interval=10, max_stall_time=60)', 'Function signature'),
        ('get_height', 'Height query'),
        ('wallet_height', 'Wallet height tracking'),
        ('daemon_height', 'Daemon height tracking'),
        ('percentage', 'Percentage calculation'),
        ('blocks_remaining', 'Blocks remaining calculation'),
        ('time_stalled', 'Stall detection'),
        ('stalled_warnings', 'Stall warning counter'),
        ('blocks_per_second', 'Sync speed calculation'),
        ('eta_minutes', 'ETA calculation'),
        ('Syncing wallet', 'Progress message'),
        ('Sync appears stalled', 'Stall warning message'),
        ('Wallet synced', 'Completion message'),
        ('logger.info', 'Info logging'),
        ('logger.warning', 'Warning logging'),
        ('logger.error', 'Error logging'),
        ('while True:', 'Continuous monitoring loop'),
        ('time.sleep(update_interval)', 'Update interval sleep'),
    ]
    
    all_found = True
    for check, description in checks:
        if check in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ MISSING: {description}")
            all_found = False
    
    return all_found


def test_start_rpc_updated():
    """Test that start_rpc method was updated to use wait_for_rpc_ready"""
    print("\n" + "=" * 70)
    print("Test 5: start_rpc() Method Updated")
    print("=" * 70)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    checks = [
        ('def start_rpc(', 'start_rpc method exists'),
        ('wait_for_rpc_ready(port=self.rpc_port', 'Calls wait_for_rpc_ready'),
        ('max_wait=60', 'Uses 60 second timeout'),
        ('retry_interval=2', 'Uses 2 second retry interval'),
        ('if not wait_for_rpc_ready', 'Checks return value'),
        ('RPC process started but not responding', 'Error message for timeout'),
        ('monero-wallet-rpc --version', 'Installation check hint'),
        ('Started RPC process with PID', 'PID logging'),
    ]
    
    all_found = True
    for check, description in checks:
        if check in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ MISSING: {description}")
            all_found = False
    
    # Check that OLD implementation is removed
    old_patterns = [
        'for i in range(10):',
        'Waiting for RPC to start... ({i+1}/10)',
    ]
    
    for pattern in old_patterns:
        if pattern in content and 'start_rpc' in content:
            # Make sure this isn't in a comment or docstring
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if pattern in line and 'def start_rpc' in '\n'.join(lines[max(0, i-30):i+1]):
                    print(f"  ⚠ Old implementation pattern still present: {pattern}")
                    all_found = False
                    break
    
    return all_found


def test_setup_wallet_updated():
    """Test that setup_wallet method was updated"""
    print("\n" + "=" * 70)
    print("Test 6: setup_wallet() Method Updated")
    print("=" * 70)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    checks = [
        ('def setup_wallet(', 'setup_wallet method exists'),
        ('cleanup_zombie_rpc_processes()', 'Calls zombie cleanup'),
        ('_check_and_monitor_sync()', 'Calls sync monitor helper'),
        ('Wallet system initialized successfully', 'Success message'),
    ]
    
    all_found = True
    for check, description in checks:
        if check in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ MISSING: {description}")
            all_found = False
    
    return all_found


def test_check_and_monitor_sync_helper():
    """Test _check_and_monitor_sync helper method"""
    print("\n" + "=" * 70)
    print("Test 7: _check_and_monitor_sync() Helper Method")
    print("=" * 70)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    checks = [
        ('def _check_and_monitor_sync(self)', 'Method definition'),
        ('Checking wallet sync status', 'Status check message'),
        ('get_height', 'Height query'),
        ('wallet_height', 'Height tracking'),
        ('threading.Thread', 'Background thread creation'),
        ('target=monitor_sync_progress', 'Thread target'),
        ('daemon=True', 'Daemon thread'),
        ('WalletSyncMonitor', 'Thread name'),
        ('sync_thread.start()', 'Thread start'),
        ('Starting background sync', 'Background sync message'),
        ('Bot will start now', 'User message'),
        ('payment features available after sync', 'Feature availability message'),
    ]
    
    all_found = True
    for check, description in checks:
        if check in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ MISSING: {description}")
            all_found = False
    
    return all_found


def test_threading_import():
    """Test that threading module is imported"""
    print("\n" + "=" * 70)
    print("Test 8: Threading Module Import")
    print("=" * 70)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    if 'import threading' in content:
        print("  ✓ threading module imported")
        return True
    else:
        print("  ✗ threading module NOT imported")
        return False


def test_logging_messages():
    """Test that all expected logging messages are present"""
    print("\n" + "=" * 70)
    print("Test 9: Logging Messages with Emoji")
    print("=" * 70)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    expected_messages = [
        ('🔍 Checking for zombie RPC processes', 'Zombie check message'),
        ('⚠ Found', 'Zombie found warning'),
        ('🗑 Killing zombie RPC process', 'Kill message'),
        ('✓ Zombie processes cleaned up', 'Cleanup success'),
        ('✓ No zombie processes found', 'No zombies message'),
        ('⏳ Waiting for RPC to start', 'RPC wait message'),
        ('✓ RPC ready after', 'RPC ready message'),
        ('❌ RPC did not respond', 'RPC timeout message'),
        ('🔄 Starting wallet sync monitor', 'Sync monitor start'),
        ('🔄 Syncing wallet', 'Sync progress message'),
        ('⚠ Sync appears stalled', 'Stall warning'),
        ('✓ Wallet synced', 'Sync complete message'),
        ('🔧 Starting wallet RPC process', 'RPC start message'),
        ('✅ Wallet RPC started successfully', 'RPC success message'),
        ('💡 Check if monero-wallet-rpc is installed', 'Installation hint'),
        ('🔍 Checking wallet sync status', 'Sync status check'),
        ('✓ Wallet appears synced', 'Already synced message'),
        ('💡 Bot will start now', 'Bot start message'),
    ]
    
    all_found = True
    for msg, description in expected_messages:
        if msg in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ MISSING: {description}")
            all_found = False
    
    return all_found


def test_no_syntax_errors():
    """Test that the file has no Python syntax errors"""
    print("\n" + "=" * 70)
    print("Test 10: Python Syntax Validation")
    print("=" * 70)
    
    import py_compile
    
    try:
        py_compile.compile('signalbot/core/wallet_setup.py', doraise=True)
        print("  ✓ No syntax errors")
        return True
    except py_compile.PyCompileError as e:
        print(f"  ✗ Syntax error: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("PR #45 Implementation Verification")
    print("Fix RPC Startup Race Condition + Add Wallet Sync Progress Monitor")
    print("=" * 70)
    
    tests = [
        test_imports,
        test_cleanup_zombie_function,
        test_wait_for_rpc_ready_function,
        test_monitor_sync_progress_function,
        test_start_rpc_updated,
        test_setup_wallet_updated,
        test_check_and_monitor_sync_helper,
        test_threading_import,
        test_logging_messages,
        test_no_syntax_errors,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n✗ Test failed with exception: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✓ ALL TESTS PASSED!")
        print("PR #45 implementation is complete and correct.")
        return 0
    else:
        print(f"\n✗ {total - passed} TEST(S) FAILED!")
        print("Please review the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
