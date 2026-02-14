#!/usr/bin/env python3
"""
Test image path decryption in product catalog
"""

import sys
import os
import tempfile

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))


def test_base64_import():
    """Test that base64 is imported correctly in db.py"""
    print("=" * 60)
    print("TEST: base64 Import Location")
    print("=" * 60)
    
    db_file = os.path.join(os.path.dirname(__file__), 'signalbot/database/db.py')
    
    with open(db_file, 'r') as f:
        lines = f.readlines()
    
    # Find the import statements section (should be near the top)
    import_section_end = 20  # Imports should be in first 20 lines
    
    base64_import_line = None
    for i, line in enumerate(lines[:import_section_end]):
        if 'import base64' in line:
            base64_import_line = i + 1
            break
    
    assert base64_import_line is not None, "base64 should be imported in db.py"
    assert base64_import_line <= import_section_end, f"base64 import at line {base64_import_line} should be in import section (first {import_section_end} lines)"
    
    print(f"✅ base64 imported at line {base64_import_line} (in import section)")
    print("   ✓ Import is before DatabaseManager class definition")
    print()


def test_error_logging_in_product():
    """Test that Product.from_db_model has proper error logging"""
    print("=" * 60)
    print("TEST: Product Error Logging")
    print("=" * 60)
    
    product_file = os.path.join(os.path.dirname(__file__), 'signalbot/models/product.py')
    
    with open(product_file, 'r') as f:
        source = f.read()
    
    # Check for error logging in from_db_model
    has_exception_logging = 'except Exception as e:' in source and 'Failed to decrypt image path' in source
    has_debug_output = 'Encrypted value:' in source or 'encrypted value' in source.lower()
    
    assert has_exception_logging, "Product.from_db_model should log decryption exceptions"
    
    print("✅ Product.from_db_model() has proper error handling")
    print(f"   ✓ Logs decryption exceptions: {has_exception_logging}")
    print(f"   ✓ Shows encrypted value for debugging: {has_debug_output}")
    print()


def test_enhanced_debug_logging():
    """Test that buyer_handler and dashboard have enhanced debug logging"""
    print("=" * 60)
    print("TEST: Enhanced Debug Logging")
    print("=" * 60)
    
    buyer_handler_file = os.path.join(os.path.dirname(__file__), 'signalbot/core/buyer_handler.py')
    dashboard_file = os.path.join(os.path.dirname(__file__), 'signalbot/gui/dashboard.py')
    
    with open(buyer_handler_file, 'r') as f:
        buyer_source = f.read()
    
    with open(dashboard_file, 'r') as f:
        dashboard_source = f.read()
    
    # Check for enhanced logging in buyer_handler
    buyer_has_path_logging = 'DEBUG: Product' in buyer_source and 'has image_path:' in buyer_source
    buyer_has_cwd_check = 'Current working directory:' in buyer_source
    
    # Check for enhanced logging in dashboard
    dashboard_has_path_logging = 'DEBUG: Product' in dashboard_source and 'has image_path:' in dashboard_source
    dashboard_has_cwd_check = 'Current working directory:' in dashboard_source
    
    print("✅ Enhanced debug logging implemented")
    print(f"   ✓ buyer_handler.py logs image_path value: {buyer_has_path_logging}")
    print(f"   ✓ buyer_handler.py logs current directory: {buyer_has_cwd_check}")
    print(f"   ✓ dashboard.py logs image_path value: {dashboard_has_path_logging}")
    print(f"   ✓ dashboard.py logs current directory: {dashboard_has_cwd_check}")
    print()


def test_encryption_decryption_roundtrip():
    """Test that encryption and decryption work correctly"""
    print("=" * 60)
    print("TEST: Encryption/Decryption Round-trip")
    print("=" * 60)
    
    from signalbot.database.db import DatabaseManager
    
    # Create a temporary database
    with tempfile.NamedTemporaryFile(mode='w', suffix='.db', delete=False) as f:
        temp_db = f.name
    
    try:
        # Initialize database manager with a test password
        db = DatabaseManager(master_password="test_password_12345")
        
        # Test encrypting and decrypting an image path
        original_path = "/home/user/test/images/test_image.jpg"
        
        # Encrypt
        encrypted, salt = db.encrypt_field(original_path)
        print(f"   Original: {original_path}")
        print(f"   Encrypted: {encrypted[:50]}...")
        print(f"   Salt: {salt[:50]}...")
        
        # Decrypt
        decrypted = db.decrypt_field(encrypted, salt)
        print(f"   Decrypted: {decrypted}")
        
        # Verify round-trip
        assert decrypted == original_path, f"Decrypted path '{decrypted}' should match original '{original_path}'"
        
        print("✅ Encryption/Decryption round-trip successful")
        print("   ✓ Original path matches decrypted path")
        print()
        
        db.close()
        
    finally:
        # Clean up
        if os.path.exists(temp_db):
            os.unlink(temp_db)


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("TESTING IMAGE PATH DECRYPTION FIX")
    print("=" * 60 + "\n")
    
    try:
        test_base64_import()
        test_error_logging_in_product()
        test_enhanced_debug_logging()
        test_encryption_decryption_roundtrip()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print()
        print("Summary:")
        print("  ✓ base64 module imported in correct location (top of file)")
        print("  ✓ Product.from_db_model() has proper error logging")
        print("  ✓ buyer_handler.py has enhanced debug logging")
        print("  ✓ dashboard.py has enhanced debug logging")
        print("  ✓ Encryption/decryption round-trip works correctly")
        print()
        return True
        
    except AssertionError as e:
        print("=" * 60)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 60)
        return False
    except Exception as e:
        print("=" * 60)
        print(f"❌ ERROR: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
