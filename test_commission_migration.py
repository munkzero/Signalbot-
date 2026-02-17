#!/usr/bin/env python3
"""Test Database Migration for Commission Columns"""

import sys
import os
import sqlite3
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def test_migration():
    """Test migration adds commission columns"""
    print("\n" + "="*70)
    print("Testing Commission Column Migration")
    print("="*70)
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        tmp_db_path = tmp_db.name
    
    try:
        # Create old schema without commission columns
        conn = sqlite3.connect(tmp_db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                order_id VARCHAR(100),
                customer_signal_id TEXT,
                customer_signal_id_salt VARCHAR(255),
                product_id INTEGER,
                product_name VARCHAR(255),
                price_fiat FLOAT,
                currency VARCHAR(10),
                price_xmr FLOAT,
                payment_address TEXT,
                payment_address_salt VARCHAR(255),
                payment_status VARCHAR(20),
                order_status VARCHAR(20),
                amount_paid FLOAT,
                expires_at TIMESTAMP,
                created_at TIMESTAMP
            )
        ''')
        
        # Create other tables (using hardcoded names for safety)
        cursor.execute('CREATE TABLE sellers (id INTEGER PRIMARY KEY)')
        cursor.execute('CREATE TABLE products (id INTEGER PRIMARY KEY)')
        cursor.execute('CREATE TABLE contacts (id INTEGER PRIMARY KEY)')
        cursor.execute('CREATE TABLE messages (id INTEGER PRIMARY KEY)')
        cursor.execute('CREATE TABLE payment_history (id INTEGER PRIMARY KEY)')
        cursor.execute('CREATE TABLE monero_nodes (id INTEGER PRIMARY KEY)')
        conn.commit()
        
        cursor.execute("PRAGMA table_info(orders)")
        cols_before = [row[1] for row in cursor.fetchall()]
        conn.close()
        
        print(f"✓ Created old schema: {len(cols_before)} columns")
        print(f"✓ commission_amount exists: {'commission_amount' in cols_before}")
        
        # Set database path and initialize
        import signalbot.config.settings as settings
        orig = settings.DATABASE_FILE
        settings.DATABASE_FILE = tmp_db_path
        
        import importlib
        import signalbot.database.db as db_mod
        importlib.reload(db_mod)
        
        print("\n🔄 Initializing DatabaseManager...")
        db_mgr = db_mod.DatabaseManager(master_password="test123")
        
        # Check after migration
        conn = sqlite3.connect(tmp_db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(orders)")
        cols_after = [row[1] for row in cursor.fetchall()]
        conn.close()
        
        print(f"\n✓ Schema after migration: {len(cols_after)} columns")
        
        commission_cols = ['commission_amount', 'seller_amount', 'commission_paid', 
                          'commission_txid', 'commission_paid_at']
        
        for col in commission_cols:
            exists = col in cols_after
            print(f"  {'✓' if exists else '❌'} {col}: {exists}")
            assert exists, f"{col} missing"
        
        db_mgr.close()
        settings.DATABASE_FILE = orig
        importlib.reload(db_mod)
        
        print("\n✅ TEST PASSED - All commission columns added!")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if os.path.exists(tmp_db_path):
            os.unlink(tmp_db_path)


if __name__ == "__main__":
    success = test_migration()
    sys.exit(0 if success else 1)
