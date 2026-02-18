#!/usr/bin/env python3
"""
Test wallet cache corruption detection and automatic recovery.

Tests the features added for fixing restore_height=0 corruption:
- delete_corrupted_cache() function
- Enhanced check_wallet_health() function  
- Automatic cache recovery in setup_wallet()
"""

import sys
import os
import tempfile
from pathlib import Path

def test_delete_corrupted_cache_function():
    """Test that delete_corrupted_cache function exists and has proper safety checks"""
    print("\n" + "=" * 70)
    print("Test 1: delete_corrupted_cache() Function")
    print("=" * 70)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    checks = [
        ('def delete_corrupted_cache(wallet_path: str) -> bool:', 'Function signature'),
        ('cache_file = Path(wallet_path)', 'Cache file path'),
        ('keys_file = Path(f"{wallet_path}.keys")', 'Keys file path'),
        ('if not keys_file.exists():', 'Safety check for keys file'),
        ('logger.error("❌ Keys file not found - cannot delete cache!")', 'Error on missing keys'),
        ('cache_file.unlink()', 'Delete cache file'),
        ('logger.info(f"✓ Keys file preserved: {keys_file.name}")', 'Confirm keys preserved'),
        ('return True', 'Return success'),
        ('return False', 'Return failure'),
    ]
    
    all_found = True
    for check, description in checks:
        if check in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description} - NOT FOUND")
            all_found = False
    
    return all_found


def test_enhanced_check_wallet_health():
    """Test that check_wallet_health has enhanced detection"""
    print("\n" + "=" * 70)
    print("Test 2: Enhanced check_wallet_health() Function")
    print("=" * 70)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    checks = [
        ('cache_file = Path(wallet_path)', 'Use Path object'),
        ('file_size_mb = cache_file.stat().st_size / (1024 * 1024)', 'Check file size'),
        ('if file_size_mb > 50:', 'Warn on large cache'),
        ('consecutive_zeros = 0', 'Track consecutive zeros'),
        ('for byte in after_marker:', 'Iterate through bytes after marker'),
        ('if byte == 0:', 'Check for zero byte'),
        ('consecutive_zeros += 1', 'Count zeros'),
        ('if consecutive_zeros > WALLET_HEALTH_ZERO_THRESHOLD:', 'Check threshold'),
        ('logger.warning("⚠ DETECTED: Wallet cache corrupted (restore_height=0)")', 'Clear detection message'),
        ('return False, "Corrupted cache detected (restore_height=0)"', 'Return corruption detected'),
    ]
    
    all_found = True
    for check, description in checks:
        if check in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description} - NOT FOUND")
            all_found = False
    
    return all_found


def test_setup_wallet_cache_recovery():
    """Test that setup_wallet has automatic cache recovery"""
    print("\n" + "=" * 70)
    print("Test 3: setup_wallet() Automatic Cache Recovery")
    print("=" * 70)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    checks = [
        ('logger.info("🔍 Checking wallet cache health...")', 'Log cache health check'),
        ('if not is_healthy:', 'Check if unhealthy'),
        ('logger.warning(f"⚠ Wallet cache corrupted: {reason}")', 'Log corruption'),
        ('logger.warning("⚠ This would cause RPC to hang trying to sync from block 0")', 'Explain impact'),
        ('logger.info("🔧 Attempting automatic cache repair...")', 'Log repair attempt'),
        ('if delete_corrupted_cache(wallet_path_str):', 'Call delete_corrupted_cache'),
        ('logger.info("✓ Corrupted cache removed")', 'Log cache removed'),
        ('logger.info("🔧 Will rebuild cache from current blockchain height")', 'Log rebuild plan'),
        ('logger.info("✓ Keys file preserved - wallet intact")', 'Log keys preserved'),
        ('logger.warning("⚠ Falling back to full wallet recreation...")', 'Fallback message'),
    ]
    
    all_found = True
    for check, description in checks:
        if check in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description} - NOT FOUND")
            all_found = False
    
    return all_found


def test_corrupted_cache_simulation():
    """Test corruption detection with simulated corrupted cache"""
    print("\n" + "=" * 70)
    print("Test 4: Corrupted Cache Detection (Functional Test)")
    print("=" * 70)
    
    try:
        # Import the function
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from signalbot.core.wallet_setup import check_wallet_health
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            wallet_path = os.path.join(tmpdir, "test_wallet")
            
            # Test 1: No cache file (should be healthy)
            is_healthy, reason = check_wallet_health(wallet_path)
            if is_healthy:
                print(f"  ✓ No cache file - correctly marked as healthy")
            else:
                print(f"  ✗ No cache file - incorrectly marked as unhealthy")
                return False
            
            # Test 2: Create corrupted cache with restore_height=0 pattern
            with open(wallet_path, 'wb') as f:
                # Simulate corrupted cache with restore_height marker followed by many zeros
                f.write(b'some_other_data_here')
                f.write(b'restore_height')
                f.write(b'\x00' * 30)  # Many consecutive zeros = height 0
                f.write(b'more_data')
            
            is_healthy, reason = check_wallet_health(wallet_path)
            if not is_healthy and "restore_height=0" in reason:
                print(f"  ✓ Corrupted cache detected correctly")
                print(f"    Reason: {reason}")
            else:
                print(f"  ✗ Corrupted cache NOT detected")
                print(f"    is_healthy={is_healthy}, reason={reason}")
                return False
            
            # Test 3: Create healthy cache (restore_height with non-zero value)
            os.remove(wallet_path)
            with open(wallet_path, 'wb') as f:
                # Simulate healthy cache with restore_height marker followed by actual height bytes
                f.write(b'some_other_data_here')
                f.write(b'restore_height')
                # Simulate height 3576000 in little-endian (non-zero bytes)
                f.write(b'\x80\x8f\x36\x00')  # Example height bytes (not all zeros)
                f.write(b'more_data')
            
            is_healthy, reason = check_wallet_health(wallet_path)
            if is_healthy:
                print(f"  ✓ Healthy cache recognized correctly")
            else:
                print(f"  ✗ Healthy cache incorrectly marked as unhealthy")
                print(f"    reason={reason}")
                return False
        
        return True
        
    except Exception as e:
        print(f"  ✗ Functional test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_delete_corrupted_cache_simulation():
    """Test cache deletion with simulated files"""
    print("\n" + "=" * 70)
    print("Test 5: delete_corrupted_cache() Functional Test")
    print("=" * 70)
    
    try:
        # Import the function
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from signalbot.core.wallet_setup import delete_corrupted_cache
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            wallet_path = os.path.join(tmpdir, "test_wallet")
            cache_file = wallet_path
            keys_file = f"{wallet_path}.keys"
            
            # Test 1: No keys file (should fail safely)
            with open(cache_file, 'w') as f:
                f.write("corrupted cache")
            
            result = delete_corrupted_cache(wallet_path)
            if not result:
                print(f"  ✓ Correctly refused to delete cache without keys file")
            else:
                print(f"  ✗ Incorrectly deleted cache without keys file")
                return False
            
            # Cache should still exist
            if os.path.exists(cache_file):
                print(f"  ✓ Cache preserved when keys file missing")
            else:
                print(f"  ✗ Cache deleted when it should have been preserved")
                return False
            
            # Test 2: With keys file (should succeed)
            with open(keys_file, 'w') as f:
                f.write("important keys data")
            
            result = delete_corrupted_cache(wallet_path)
            if result:
                print(f"  ✓ Successfully deleted cache with keys file present")
            else:
                print(f"  ✗ Failed to delete cache with keys file present")
                return False
            
            # Cache should be gone
            if not os.path.exists(cache_file):
                print(f"  ✓ Cache file deleted")
            else:
                print(f"  ✗ Cache file still exists")
                return False
            
            # Keys should be preserved
            if os.path.exists(keys_file):
                print(f"  ✓ Keys file preserved")
            else:
                print(f"  ✗ Keys file was deleted (critical failure!)")
                return False
            
            # Test 3: Cache already deleted (should succeed)
            result = delete_corrupted_cache(wallet_path)
            if result:
                print(f"  ✓ Correctly handles already-deleted cache")
            else:
                print(f"  ✗ Failed when cache already deleted")
                return False
        
        return True
        
    except Exception as e:
        print(f"  ✗ Functional test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_logging_messages():
    """Test that proper logging messages are in place"""
    print("\n" + "=" * 70)
    print("Test 6: Enhanced Logging Messages")
    print("=" * 70)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    checks = [
        ('logger.info("🔍 Checking wallet cache health...")', 'Cache health check start'),
        ('logger.warning("⚠ DETECTED: Wallet cache corrupted (restore_height=0)")', 'Corruption detection'),
        ('logger.info("🔧 Attempting automatic cache repair...")', 'Repair attempt'),
        ('logger.warning(f"🗑 Deleting corrupted cache: {cache_file.name}")', 'Cache deletion'),
        ('logger.info("✓ Corrupted cache deleted")', 'Deletion success'),
        ('✓ Keys file preserved', 'Keys preservation'),
        ('logger.info("🔧 Will rebuild cache from current blockchain height")', 'Rebuild message'),
        ('logger.warning("⚠ This would cause RPC to hang trying to sync from block 0")', 'Impact explanation'),
    ]
    
    all_found = True
    for check, description in checks:
        if check in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description} - NOT FOUND")
            all_found = False
    
    return all_found


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("WALLET CACHE CORRUPTION FIX TESTS")
    print("=" * 70)
    
    tests = [
        test_delete_corrupted_cache_function,
        test_enhanced_check_wallet_health,
        test_setup_wallet_cache_recovery,
        test_corrupted_cache_simulation,
        test_delete_corrupted_cache_simulation,
        test_logging_messages,
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
