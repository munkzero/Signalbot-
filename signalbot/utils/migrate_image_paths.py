#!/usr/bin/env python3
"""
Migration script to convert relative image paths to absolute paths
"""

import os
import sys
import sqlite3


def migrate_image_paths(db_path='data/db/shopbot.db'):
    """
    Convert all relative image paths in database to absolute paths
    """
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return False
    
    base_dir = os.getcwd()
    
    db = sqlite3.connect(db_path)
    cursor = db.cursor()
    
    # Get all products with image paths
    cursor.execute("SELECT id, name, image_path FROM products WHERE image_path IS NOT NULL AND image_path != ''")
    products = cursor.fetchall()
    
    if not products:
        print("✓ No products with image paths found")
        return True
    
    print(f"Found {len(products)} products with image paths\n")
    
    updated_count = 0
    search_dirs = [
        'data/products/images',
        'data/images',
        'data/product_images',
        'images',
    ]
    
    for product_id, name, image_path in products:
        print(f"Product #{product_id}: {name}")
        print(f"  Current path: {image_path}")
        
        # Skip if already absolute and exists
        if os.path.isabs(image_path):
            if os.path.exists(image_path):
                print(f"  ✓ Already absolute and valid")
                continue
            else:
                print(f"  ⚠ Absolute but file missing")
        
        # Search for the file
        found_path = None
        filename = os.path.basename(image_path)
        
        for search_dir in search_dirs:
            test_path = os.path.join(base_dir, search_dir, filename)
            if os.path.exists(test_path):
                found_path = test_path
                print(f"  ✓ Found at: {test_path}")
                break
        
        if found_path:
            # Update database
            cursor.execute("UPDATE products SET image_path = ? WHERE id = ?", (found_path, product_id))
            updated_count += 1
            print(f"  ✓ Updated to absolute path")
        else:
            print(f"  ✗ File not found in any common directory")
        
        print()
    
    db.commit()
    db.close()
    
    print(f"\n{'='*50}")
    print(f"Migration complete!")
    print(f"Updated: {updated_count}/{len(products)} products")
    print(f"{'='*50}")
    
    return True


if __name__ == "__main__":
    migrate_image_paths()
