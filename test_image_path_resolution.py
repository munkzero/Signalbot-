#!/usr/bin/env python3
"""
Test image path resolution functionality in buyer_handler and dashboard
"""

import sys
import os
import tempfile
import shutil

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from signalbot.core.buyer_handler import BuyerHandler
from signalbot.models.product import Product


def test_resolve_image_path_absolute():
    """Test that absolute paths are handled correctly"""
    print("=" * 60)
    print("TEST: Resolve Absolute Image Path")
    print("=" * 60)
    
    # Create temporary directory with test image
    with tempfile.TemporaryDirectory() as tmpdir:
        test_image = os.path.join(tmpdir, "test_product.png")
        with open(test_image, 'w') as f:
            f.write("fake image data")
        
        # Create a mock BuyerHandler instance
        buyer_handler = BuyerHandler(None, None, None, None)
        
        # Test with absolute path that exists
        resolved = buyer_handler._resolve_image_path(test_image)
        assert resolved == test_image, f"Expected {test_image}, got {resolved}"
        print(f"✅ Absolute existing path resolved correctly: {test_image}")
        
        # Test with absolute path that doesn't exist
        fake_path = os.path.join(tmpdir, "nonexistent.png")
        resolved = buyer_handler._resolve_image_path(fake_path)
        assert resolved is None, f"Expected None for non-existent path, got {resolved}"
        print(f"✅ Non-existent absolute path returns None")
    
    print()


def test_resolve_image_path_relative():
    """Test that relative paths are searched in multiple directories"""
    print("=" * 60)
    print("TEST: Resolve Relative Image Path")
    print("=" * 60)
    
    # Save current directory
    original_dir = os.getcwd()
    
    try:
        # Create temporary working directory
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            
            # Create test directory structure
            os.makedirs("data/images", exist_ok=True)
            os.makedirs("data/products/images", exist_ok=True)
            os.makedirs("data/product_images", exist_ok=True)
            
            # Create test image in data/images/
            test_image = "product_1.png"
            full_path = os.path.join(tmpdir, "data/images", test_image)
            with open(full_path, 'w') as f:
                f.write("fake image data")
            
            # Create a mock BuyerHandler instance
            buyer_handler = BuyerHandler(None, None, None, None)
            
            # Test relative path resolution
            resolved = buyer_handler._resolve_image_path(test_image)
            assert resolved is not None, "Should find image in data/images/"
            assert resolved == full_path, f"Expected {full_path}, got {resolved}"
            print(f"✅ Relative path '{test_image}' resolved to: {resolved}")
            
            # Test with image in higher priority directory
            priority_path = os.path.join(tmpdir, "data/products/images", test_image)
            with open(priority_path, 'w') as f:
                f.write("fake image data 2")
            
            resolved = buyer_handler._resolve_image_path(test_image)
            assert resolved == priority_path, f"Should prioritize data/products/images/, got {resolved}"
            print(f"✅ Found image in priority directory: {priority_path}")
            
    finally:
        # Restore original directory
        os.chdir(original_dir)
    
    print()


def test_resolve_image_path_not_found():
    """Test that missing images return None"""
    print("=" * 60)
    print("TEST: Missing Image Returns None")
    print("=" * 60)
    
    # Save current directory
    original_dir = os.getcwd()
    
    try:
        # Create temporary working directory
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            
            # Create test directories (but no images)
            os.makedirs("data/images", exist_ok=True)
            os.makedirs("data/products/images", exist_ok=True)
            
            # Create a mock BuyerHandler instance
            buyer_handler = BuyerHandler(None, None, None, None)
            
            # Test with non-existent relative path
            resolved = buyer_handler._resolve_image_path("nonexistent.png")
            assert resolved is None, "Should return None for non-existent image"
            print(f"✅ Non-existent relative path returns None")
            
            # Test with empty path
            resolved = buyer_handler._resolve_image_path("")
            assert resolved is None, "Should return None for empty path"
            print(f"✅ Empty path returns None")
            
            # Test with None
            resolved = buyer_handler._resolve_image_path(None)
            assert resolved is None, "Should return None for None path"
            print(f"✅ None path returns None")
            
    finally:
        # Restore original directory
        os.chdir(original_dir)
    
    print()


def test_search_directory_priority():
    """Test that directories are searched in the correct priority order"""
    print("=" * 60)
    print("TEST: Directory Search Priority")
    print("=" * 60)
    
    # Save current directory
    original_dir = os.getcwd()
    
    try:
        # Create temporary working directory
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            
            # Create all possible directories
            dirs = [
                "data/products/images",
                "data/images",
                "data/product_images",
                "images",
            ]
            
            for d in dirs:
                os.makedirs(d, exist_ok=True)
            
            test_image = "test.png"
            
            # Place image only in lower priority directory
            low_priority = os.path.join(tmpdir, "data/product_images", test_image)
            with open(low_priority, 'w') as f:
                f.write("low priority")
            
            buyer_handler = BuyerHandler(None, None, None, None)
            resolved = buyer_handler._resolve_image_path(test_image)
            assert resolved == low_priority, f"Should find in data/product_images/"
            print(f"✅ Found in lower priority directory when higher ones are empty")
            
            # Now add image to higher priority directory
            high_priority = os.path.join(tmpdir, "data/products/images", test_image)
            with open(high_priority, 'w') as f:
                f.write("high priority")
            
            resolved = buyer_handler._resolve_image_path(test_image)
            assert resolved == high_priority, f"Should prioritize data/products/images/"
            print(f"✅ Correctly prioritizes data/products/images/ over data/product_images/")
            
    finally:
        # Restore original directory
        os.chdir(original_dir)
    
    print()


def test_method_exists_in_classes():
    """Test that _resolve_image_path exists in both BuyerHandler and Dashboard"""
    print("=" * 60)
    print("TEST: Method Exists in Classes")
    print("=" * 60)
    
    # Test BuyerHandler
    assert hasattr(BuyerHandler, '_resolve_image_path'), "BuyerHandler should have _resolve_image_path method"
    print("✅ BuyerHandler has _resolve_image_path method")
    
    # Test Dashboard (if we can import it)
    try:
        # Dashboard requires PyQt5, which might not be available in all environments
        from signalbot.gui.dashboard import Dashboard
        assert hasattr(Dashboard, '_resolve_image_path'), "Dashboard should have _resolve_image_path method"
        print("✅ Dashboard has _resolve_image_path method")
    except ImportError as e:
        print(f"⚠️  Dashboard import skipped (PyQt5 not available): {e}")
    
    print()


def test_migration_script_exists():
    """Test that migration script exists and is valid Python"""
    print("=" * 60)
    print("TEST: Migration Script Exists")
    print("=" * 60)
    
    script_path = os.path.join(os.path.dirname(__file__), 'signalbot/utils/migrate_image_paths.py')
    
    assert os.path.exists(script_path), f"Migration script should exist at {script_path}"
    print(f"✅ Migration script exists: {script_path}")
    
    # Check it's valid Python
    with open(script_path, 'r') as f:
        content = f.read()
        compile(content, script_path, 'exec')
    print("✅ Migration script is valid Python")
    
    # Check it has the main function
    assert 'def migrate_image_paths' in content, "Should have migrate_image_paths function"
    print("✅ Migration script has migrate_image_paths function")
    
    print()


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("IMAGE PATH RESOLUTION TEST SUITE")
    print("=" * 60 + "\n")
    
    tests = [
        test_resolve_image_path_absolute,
        test_resolve_image_path_relative,
        test_resolve_image_path_not_found,
        test_search_directory_priority,
        test_method_exists_in_classes,
        test_migration_script_exists,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAILED: {test.__name__}")
            print(f"   Error: {e}")
            print()
            failed += 1
        except Exception as e:
            print(f"❌ ERROR in {test.__name__}: {e}")
            print()
            failed += 1
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"✅ Passed: {passed}")
    if failed > 0:
        print(f"❌ Failed: {failed}")
    else:
        print("🎉 All tests passed!")
    print("=" * 60 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
