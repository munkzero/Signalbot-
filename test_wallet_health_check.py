#!/usr/bin/env python3
"""
Test wallet health check and backup functionality.

Tests the new features added in PR #XX:
- check_wallet_health() function
- backup_wallet() function
- delete_wallet_files() function
- Enhanced setup_wallet() with health checks
"""

import sys
from pathlib import Path

def test_check_wallet_health_function():
    """Test that check_wallet_health function exists"""
    print("\n" + "=" * 70)
    print("Test 1: check_wallet_health() Function")
    print("=" * 70)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    checks = [
        ('def check_wallet_health(wallet_path: str) -> Tuple[bool, Optional[str]]:', 'Function signature'),
        ('cache_file = wallet_path', 'Cache file path'),
        ('os.path.exists(cache_file)', 'Check cache exists'),
        ("b'restore_height'", 'Look for restore_height in cache'),
        ('zero_count = remaining[:20].count', 'Count zeros'),
        ('return False, "Wallet restore height appears to be 0', 'Return unhealthy'),
        ('return True, None', 'Return healthy'),
    ]
    
    all_found = True
    for check, description in checks:
        if check in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description} - NOT FOUND")
            all_found = False
    
    return all_found


def test_backup_wallet_function():
    """Test that backup_wallet function exists"""
    print("\n" + "=" * 70)
    print("Test 2: backup_wallet() Function")
    print("=" * 70)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    checks = [
        ('def backup_wallet(wallet_path: str) -> bool:', 'Function signature'),
        ('import shutil', 'Import shutil'),
        ('from datetime import datetime', 'Import datetime'),
        ('timestamp = datetime.now().strftime', 'Create timestamp'),
        ('backup_dir = os.path.join(os.path.dirname(wallet_path), "backups")', 'Backup directory'),
        ('os.makedirs(backup_dir, exist_ok=True)', 'Create backup directory'),
        ('keys_file = f"{wallet_path}.keys"', 'Keys file path'),
        ('shutil.copy2(keys_file, backup_keys)', 'Copy keys file'),
        ('return True', 'Return success'),
    ]
    
    all_found = True
    for check, description in checks:
        if check in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description} - NOT FOUND")
            all_found = False
    
    return all_found


def test_delete_wallet_files_function():
    """Test that delete_wallet_files function exists"""
    print("\n" + "=" * 70)
    print("Test 3: delete_wallet_files() Function")
    print("=" * 70)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    checks = [
        ('def delete_wallet_files(wallet_path: str) -> bool:', 'Function signature'),
        ('keys_file = f"{wallet_path}.keys"', 'Keys file path'),
        ('os.remove(keys_file)', 'Remove keys file'),
        ('os.remove(wallet_path)', 'Remove cache file'),
        ('address_file = f"{wallet_path}.address.txt"', 'Address file path'),
        ('return True', 'Return success'),
    ]
    
    all_found = True
    for check, description in checks:
        if check in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description} - NOT FOUND")
            all_found = False
    
    return all_found


def test_setup_wallet_health_check_integration():
    """Test that setup_wallet uses health check"""
    print("\n" + "=" * 70)
    print("Test 4: setup_wallet() Health Check Integration")
    print("=" * 70)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    checks = [
        ('is_healthy, reason = check_wallet_health(wallet_path_str)', 'Call health check'),
        ('logger.info(f"Wallet healthy: {is_healthy}")', 'Log health status'),
        ('if not is_healthy:', 'Check if unhealthy'),
        ('logger.warning(f"⚠ Wallet unhealthy: {reason}")', 'Log unhealthy reason'),
        ('logger.warning("⚠ Will backup and recreate wallet")', 'Log recreation plan'),
        ('if backup_wallet(wallet_path_str):', 'Call backup function'),
        ('if delete_wallet_files(wallet_path_str):', 'Call delete function'),
        ('wallet_exists = False  # Force recreation', 'Force recreation'),
    ]
    
    all_found = True
    for check, description in checks:
        if check in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description} - NOT FOUND")
            all_found = False
    
    return all_found


def test_enhanced_logging():
    """Test that enhanced logging is present"""
    print("\n" + "=" * 70)
    print("Test 5: Enhanced Logging")
    print("=" * 70)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    checks = [
        ('logger.info("WALLET INITIALIZATION STARTING")', 'Initialization start log'),
        ('logger.info(f"Wallet path: {wallet_path_str}")', 'Wallet path log'),
        ('logger.info(f"Wallet exists: {wallet_exists}")', 'Wallet exists log'),
        ('logger.info(f"🚀 Starting RPC on port {rpc_port}...")', 'RPC start log'),
        ('logger.info("✓ Wallet creation SUCCESS")', 'Creation success log'),
        ('logger.info("📋 Seed phrase captured successfully")', 'Seed capture log'),
        ('logger.warning("⚠ Seed phrase not captured!")', 'Seed warning log'),
        ('logger.info("✅ WALLET INITIALIZATION COMPLETE")', 'Initialization complete log'),
    ]
    
    all_found = True
    for check, description in checks:
        if check in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description} - NOT FOUND")
            all_found = False
    
    return all_found


def test_rpc_port_consistency():
    """Test that RPC port is used consistently"""
    print("\n" + "=" * 70)
    print("Test 6: RPC Port Consistency")
    print("=" * 70)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    monero_wallet_path = Path("signalbot/core/monero_wallet.py")
    settings_path = Path("signalbot/config/settings.py")
    
    # Check settings.py has DEFAULT_RPC_PORT
    with open(settings_path, 'r') as f:
        settings_content = f.read()
    
    port_found = 'DEFAULT_RPC_PORT = 18082' in settings_content
    if port_found:
        print(f"  ✓ DEFAULT_RPC_PORT = 18082 in settings.py")
    else:
        print(f"  ✗ DEFAULT_RPC_PORT not found in settings.py")
        return False
    
    # Check monero_wallet.py uses port 18082
    with open(monero_wallet_path, 'r') as f:
        wallet_content = f.read()
    
    port_found = 'self.rpc_port = 18082' in wallet_content
    if port_found:
        print(f"  ✓ self.rpc_port = 18082 in monero_wallet.py")
    else:
        print(f"  ✗ rpc_port not set correctly in monero_wallet.py")
        return False
    
    # Check wallet_setup.py uses self.rpc_port consistently
    with open(wallet_setup_path, 'r') as f:
        setup_content = f.read()
    
    checks = [
        ('rpc_port: int = 18082', 'Default parameter'),
        ('self.rpc_port = rpc_port', 'Store in instance'),
        ('port=self.rpc_port', 'Use in wait_for_rpc_ready'),
        ('f"http://localhost:{self.rpc_port}/json_rpc"', 'Use in RPC calls'),
    ]
    
    all_found = True
    for check, description in checks:
        if check in setup_content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description} - NOT FOUND")
            all_found = False
    
    return all_found


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("WALLET HEALTH CHECK AND BACKUP TESTS")
    print("=" * 70)
    
    tests = [
        test_check_wallet_health_function,
        test_backup_wallet_function,
        test_delete_wallet_files_function,
        test_setup_wallet_health_check_integration,
        test_enhanced_logging,
        test_rpc_port_consistency,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n❌ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(results)
    total = len(results)
    
    for i, (test, result) in enumerate(zip(tests, results), 1):
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"Test {i}: {test.__name__:50s} {status}")
    
    print("\n" + "=" * 70)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 70)
    
    # Exit with appropriate code
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
