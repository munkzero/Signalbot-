#!/usr/bin/env python3
"""
Project Structure Verification Script
Tests that all modules can be imported (without external dependencies)
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_core_modules():
    """Test core modules that don't require external dependencies"""
    print("=" * 60)
    print("TESTING CORE MODULES")
    print("=" * 60)
    
    try:
        from signalbot.config.settings import COMMISSION_RATE, SUPPORTED_CURRENCIES
        print("✓ Config module imported")
        print(f"  - Commission rate: {COMMISSION_RATE * 100}%")
        print(f"  - Supported currencies: {', '.join(SUPPORTED_CURRENCIES)}")
        
        from signalbot.core.security import security_manager
        print("✓ Security module imported")
        
        # Test encryption
        plaintext = "test_data"
        encrypted, salt = security_manager.encrypt_string(plaintext, "password")
        decrypted = security_manager.decrypt_string(encrypted, "password", salt)
        assert decrypted == plaintext
        print("  - Encryption/decryption: OK")
        
        # Test PIN hashing
        pin_hash, pin_salt = security_manager.hash_pin("123456")
        assert security_manager.verify_pin("123456", pin_hash, pin_salt)
        assert not security_manager.verify_pin("wrong", pin_hash, pin_salt)
        print("  - PIN hashing/verification: OK")
        
        from signalbot.core.commission import CommissionManager, setup_commission_wallet
        print("✓ Commission module imported")
        
        # Test commission calculation
        test_amount = 1.0
        commission = test_amount * COMMISSION_RATE
        assert commission == 0.04
        print(f"  - Commission calculation: {commission} XMR (4%)")
        
        # Test wallet encryption
        config = setup_commission_wallet("test_wallet_address", "password")
        assert 'ENCRYPTED_COMMISSION_WALLET' in config
        print("  - Wallet encryption: OK")
        
        return True
        
    except Exception as e:
        print(f"✗ Core module test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_models():
    """Test model imports"""
    print("\n" + "=" * 60)
    print("TESTING MODEL MODULES")
    print("=" * 60)
    
    try:
        from signalbot.models.product import Product
        print("✓ Product model imported")
        
        from signalbot.models.order import Order
        print("✓ Order model imported")
        
        from signalbot.models.seller import Seller
        print("✓ Seller model imported")
        
        return True
        
    except Exception as e:
        print(f"✗ Model test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_project_structure():
    """Verify project directory structure"""
    print("\n" + "=" * 60)
    print("VERIFYING PROJECT STRUCTURE")
    print("=" * 60)
    
    required_dirs = [
        'signalbot',
        'signalbot/core',
        'signalbot/models',
        'signalbot/utils',
        'signalbot/database',
        'signalbot/config',
        'signalbot/gui',
        'signalbot/gui/components'
    ]
    
    required_files = [
        'signalbot/main.py',
        'signalbot/core/security.py',
        'signalbot/core/commission.py',
        'signalbot/core/monero_wallet.py',
        'signalbot/core/payments.py',
        'signalbot/core/signal_handler.py',
        'signalbot/models/product.py',
        'signalbot/models/order.py',
        'signalbot/models/seller.py',
        'signalbot/database/db.py',
        'signalbot/config/settings.py',
        'signalbot/gui/wizard.py',
        'signalbot/gui/dashboard.py',
        'requirements.txt',
        'README.md',
        '.gitignore'
    ]
    
    all_ok = True
    
    for directory in required_dirs:
        if os.path.isdir(directory):
            print(f"✓ {directory}/")
        else:
            print(f"✗ {directory}/ - MISSING")
            all_ok = False
    
    print()
    for filepath in required_files:
        if os.path.isfile(filepath):
            size = os.path.getsize(filepath)
            print(f"✓ {filepath} ({size} bytes)")
        else:
            print(f"✗ {filepath} - MISSING")
            all_ok = False
    
    return all_ok


def count_lines_of_code():
    """Count lines of code"""
    print("\n" + "=" * 60)
    print("CODE STATISTICS")
    print("=" * 60)
    
    total_lines = 0
    total_files = 0
    
    for root, dirs, files in os.walk('signalbot'):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r') as f:
                    lines = len(f.readlines())
                    total_lines += lines
                    total_files += 1
    
    print(f"Total Python files: {total_files}")
    print(f"Total lines of code: {total_lines}")
    
    return total_files, total_lines


def main():
    """Main test runner"""
    print("\n" + "=" * 60)
    print("SIGNAL SHOP BOT - PROJECT VERIFICATION")
    print("=" * 60)
    
    results = []
    
    # Test structure
    results.append(("Project Structure", verify_project_structure()))
    
    # Test core modules
    results.append(("Core Modules", test_core_modules()))
    
    # Test models
    results.append(("Model Modules", test_models()))
    
    # Count code
    files, lines = count_lines_of_code()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED - PROJECT READY!")
        print("=" * 60)
        print(f"\n📊 Stats: {files} files, {lines} lines of code")
        print("\n📝 Next steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Run the application: python signalbot/main.py")
        print("3. Complete setup wizard")
        print("4. Start selling with privacy!")
        return 0
    else:
        print("\n" + "=" * 60)
        print("❌ SOME TESTS FAILED")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
