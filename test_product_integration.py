#!/usr/bin/env python3
"""
Integration test for product catalog with encrypted image paths
"""

import sys
import os
import tempfile

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from signalbot.database.db import DatabaseManager
from signalbot.models.product import Product, ProductManager


def test_product_with_encrypted_image_path():
    """Test creating and retrieving a product with encrypted image path"""
    print("=" * 60)
    print("INTEGRATION TEST: Product with Encrypted Image Path")
    print("=" * 60)
    
    # Create a unique temporary database for this test
    import time
    temp_db = f"/tmp/test_product_{int(time.time() * 1000)}.db"
    
    # Override DATABASE_FILE for this test
    import signalbot.config.settings as settings
    original_db = settings.DATABASE_FILE
    settings.DATABASE_FILE = temp_db
    
    try:
        # Initialize database manager with a test password
        db = DatabaseManager(master_password="test_password_12345")
        product_manager = ProductManager(db)
        
        # Create a test product with an image path
        test_image_path = "/home/user/test/data/products/images/test_product.jpg"
        
        print("\n1. Creating product with image path...")
        product = Product(
            product_id=f"TEST{os.getpid()}",  # Use process ID to make unique
            name="Test Product",
            description="A test product with an encrypted image path",
            price=99.99,
            currency="USD",
            stock=10,
            category="Test",
            image_path=test_image_path,
            active=True
        )
        
        # Save the product (this should encrypt the image path)
        created_product = product_manager.create_product(product)
        print(f"   ✓ Product created with ID: {created_product.id}")
        print(f"   ✓ Original image_path: {test_image_path}")
        
        # Verify the image path is encrypted in the database
        from signalbot.database.db import Product as ProductModel
        db_product = db.session.query(ProductModel).filter_by(id=created_product.id).first()
        print(f"\n2. Verifying encryption in database...")
        print(f"   ✓ Encrypted image_path in DB: {db_product.image_path[:50]}...")
        print(f"   ✓ Image path salt: {db_product.image_path_salt[:50]}...")
        
        # Verify the encrypted value is different from original
        assert db_product.image_path != test_image_path, "Image path should be encrypted in database"
        print(f"   ✓ Confirmed: Image path is encrypted (not plain text)")
        
        # Retrieve the product (this should decrypt the image path)
        print(f"\n3. Retrieving product (should decrypt image_path)...")
        retrieved_product = product_manager.get_product(created_product.id)
        
        print(f"   ✓ Retrieved product: {retrieved_product.name}")
        print(f"   ✓ Decrypted image_path: {retrieved_product.image_path}")
        
        # Verify the decrypted path matches the original
        assert retrieved_product.image_path == test_image_path, \
            f"Decrypted path '{retrieved_product.image_path}' should match original '{test_image_path}'"
        print(f"   ✓ Confirmed: Decrypted path matches original")
        
        # Test list_products (the method used by send_catalog)
        print(f"\n4. Testing list_products (used by send_catalog)...")
        products = product_manager.list_products(active_only=True)
        
        # Find our test product in the list
        test_product = None
        for p in products:
            if p.id == created_product.id:
                test_product = p
                break
        
        assert test_product is not None, f"Should find our test product (ID {created_product.id}) in list"
        
        print(f"   ✓ Found test product in {len(products)} active product(s)")
        print(f"   ✓ Product name: {test_product.name}")
        print(f"   ✓ Decrypted image_path: {test_product.image_path}")
        
        # Verify the image path is properly decrypted in the list
        assert test_product.image_path == test_image_path, \
            f"Listed product image path '{test_product.image_path}' should match original '{test_image_path}'"
        print(f"   ✓ Confirmed: image_path is decrypted in list_products()")
        
        # Simulate catalog sending logic
        print(f"\n5. Simulating catalog sending logic...")
        for product in products:
            print(f"   Product: {product.name}")
            print(f"   Image path: {product.image_path}")
            
            if product.image_path:
                # This is what buyer_handler.py and dashboard.py do
                if os.path.exists(product.image_path):
                    print(f"   ✓ Image file exists at: {product.image_path}")
                else:
                    print(f"   ℹ Image file would need to exist at: {product.image_path}")
                    print(f"   ℹ (File doesn't exist, but path is correctly decrypted)")
        
        print("\n" + "=" * 60)
        print("✅ ALL INTEGRATION TESTS PASSED")
        print("=" * 60)
        print("\nSummary:")
        print("  ✓ Image paths are encrypted when stored in database")
        print("  ✓ Image paths are decrypted when retrieved")
        print("  ✓ list_products() returns decrypted image paths")
        print("  ✓ Catalog sending logic receives decrypted paths")
        print()
        
        db.close()
        return True
        
    except AssertionError as e:
        print("\n" + "=" * 60)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 60)
        return False
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ ERROR: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Restore original DATABASE_FILE
        settings.DATABASE_FILE = original_db
        # Clean up
        if os.path.exists(temp_db):
            os.unlink(temp_db)


if __name__ == "__main__":
    success = test_product_with_encrypted_image_path()
    sys.exit(0 if success else 1)
