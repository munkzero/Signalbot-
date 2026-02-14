#!/usr/bin/env python3
"""
Test script to verify comprehensive bot optimizations
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Test that all modified modules can be imported"""
    print("Testing imports...")
    
    try:
        from signalbot.config.settings import should_log, LOG_LEVEL
        print(f"  ✓ settings.py - LOG_LEVEL={LOG_LEVEL}")
    except Exception as e:
        print(f"  ✗ settings.py: {e}")
        return False
    
    try:
        from signalbot.utils.logger import log_debug, log_info, log_warning, log_error
        print(f"  ✓ logger.py")
    except Exception as e:
        print(f"  ✗ logger.py: {e}")
        return False
    
    return True

def test_signal_handler():
    """Test SignalHandler changes"""
    print("\nTesting SignalHandler...")
    
    try:
        from signalbot.core.signal_handler import SignalHandler
        
        # Create instance without phone number (should not crash)
        handler = SignalHandler()
        
        # Check that daemon-related attributes are removed
        if hasattr(handler, 'daemon_process'):
            print(f"  ✗ daemon_process attribute still exists!")
            return False
        if hasattr(handler, 'daemon_running'):
            print(f"  ✗ daemon_running attribute still exists!")
            return False
        
        # Check that daemon methods are removed
        if hasattr(handler, 'start_daemon'):
            print(f"  ✗ start_daemon method still exists!")
            return False
        if hasattr(handler, 'stop_daemon'):
            print(f"  ✗ stop_daemon method still exists!")
            return False
        if hasattr(handler, '_send_via_daemon'):
            print(f"  ✗ _send_via_daemon method still exists!")
            return False
        
        print(f"  ✓ Daemon mode completely removed")
        print(f"  ✓ SignalHandler initialized successfully")
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_buyer_handler():
    """Test BuyerHandler changes"""
    print("\nTesting BuyerHandler...")
    
    try:
        from signalbot.core.buyer_handler import ProductCache, BuyerHandler
        
        print(f"  ✓ ProductCache class imported")
        print(f"  ✓ BuyerHandler class imported")
        
        # Check that image optimization method exists
        if hasattr(BuyerHandler, '_optimize_image_for_signal'):
            print(f"  ✓ _optimize_image_for_signal method exists")
        else:
            print(f"  ✗ _optimize_image_for_signal method missing!")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database():
    """Test database changes"""
    print("\nTesting Database...")
    
    try:
        # Check that imports work (syntax is valid)
        import ast
        with open('signalbot/database/db.py', 'r') as f:
            code = f.read()
        
        # Verify text import is present
        if 'from sqlalchemy import' in code and ', text' in code:
            print(f"  ✓ text import added")
        else:
            print(f"  ✗ text import missing!")
            return False
        
        # Verify _create_indexes method exists
        if 'def _create_indexes' in code:
            print(f"  ✓ _create_indexes method exists")
        else:
            print(f"  ✗ _create_indexes method missing!")
            return False
        
        # Verify indexes are created
        index_names = [
            'idx_products_active',
            'idx_products_product_id',
            'idx_orders_status',
            'idx_orders_payment_address',
            'idx_orders_pending'
        ]
        
        for index_name in index_names:
            if index_name in code:
                print(f"  ✓ Index {index_name} defined")
            else:
                print(f"  ✗ Index {index_name} missing!")
                return False
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_logging():
    """Test logging configuration"""
    print("\nTesting Logging...")
    
    try:
        from signalbot.config.settings import should_log, LOG_LEVEL
        
        # Test should_log function
        levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
        for level in levels:
            result = should_log(level)
            print(f"  ✓ should_log('{level}') = {result}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cleanup_daemon():
    """Test cleanup daemon script"""
    print("\nTesting Cleanup Daemon...")
    
    try:
        import os
        
        # Check cleanup_daemon.sh exists
        if os.path.exists('cleanup_daemon.sh'):
            print(f"  ✓ cleanup_daemon.sh exists")
            
            # Check if it's executable
            if os.access('cleanup_daemon.sh', os.X_OK):
                print(f"  ✓ cleanup_daemon.sh is executable")
            else:
                print(f"  ⚠ cleanup_daemon.sh is not executable (chmod +x needed)")
            
            # Check content
            with open('cleanup_daemon.sh', 'r') as f:
                content = f.read()
            
            if 'mmin +30' in content:
                print(f"  ✓ Uses 30-minute threshold")
            else:
                print(f"  ✗ 30-minute threshold not found!")
                return False
            
            if 'sleep 1800' in content:
                print(f"  ✓ 30-minute sleep interval configured")
            else:
                print(f"  ✗ 30-minute sleep interval not found!")
                return False
            
        else:
            print(f"  ✗ cleanup_daemon.sh not found!")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_start_script():
    """Test start.sh modifications"""
    print("\nTesting start.sh...")
    
    try:
        with open('start.sh', 'r') as f:
            content = f.read()
        
        # Check cleanup threshold changed
        if 'mmin +60' in content:
            print(f"  ✓ Cleanup threshold changed to 60 minutes")
        else:
            print(f"  ✗ Cleanup threshold not updated!")
            return False
        
        # Check cleanup daemon launch
        if 'cleanup_daemon.sh' in content and 'cleanup_daemon.pid' in content:
            print(f"  ✓ Cleanup daemon launch configured")
        else:
            print(f"  ✗ Cleanup daemon launch not configured!")
            return False
        
        # Check log level setting
        if 'LOG_LEVEL=' in content:
            print(f"  ✓ LOG_LEVEL environment variable configured")
        else:
            print(f"  ✗ LOG_LEVEL not configured!")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("="*60)
    print("COMPREHENSIVE BOT OPTIMIZATION TEST SUITE")
    print("="*60)
    
    tests = [
        ("Imports", test_imports),
        ("SignalHandler", test_signal_handler),
        ("BuyerHandler", test_buyer_handler),
        ("Database", test_database),
        ("Logging", test_logging),
        ("Cleanup Daemon", test_cleanup_daemon),
        ("Start Script", test_start_script),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} test crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print("="*60)
    print(f"Overall: {passed}/{total} tests passed")
    print("="*60)
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
