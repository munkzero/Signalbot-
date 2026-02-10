#!/usr/bin/env python3
"""
Test script to validate the improvements made to Signalbot
"""

import sys
import os

# Add signalbot to path
sys.path.insert(0, os.path.dirname(__file__))

def test_database_tables():
    """Test that database tables are created correctly"""
    print("\n=== Testing Database Table Creation ===")
    
    from signalbot.database.db import DatabaseManager, Base
    import sqlite3
    from sqlalchemy import create_engine
    
    # Create test database
    test_db = '/tmp/test_signalbot_improvements.db'
    if os.path.exists(test_db):
        os.remove(test_db)
    
    # Create engine and tables directly
    engine = create_engine(f'sqlite:///{test_db}')
    Base.metadata.create_all(engine)
    
    # Check tables
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    expected_tables = ['sellers', 'products', 'orders', 'contacts', 'messages']
    
    print(f"Expected tables: {expected_tables}")
    print(f"Found tables: {tables}")
    
    for table in expected_tables:
        if table in tables:
            print(f"  ✓ {table} - CREATED")
        else:
            print(f"  ✗ {table} - MISSING")
            return False
    
    # Cleanup
    if os.path.exists(test_db):
        os.remove(test_db)
    
    print("✓ All database tables created successfully!\n")
    return True


def test_imports():
    """Test that all improved modules import correctly"""
    print("\n=== Testing Module Imports ===")
    
    try:
        from signalbot.gui.dashboard import MessagesTab, MessageSendThread
        print("  ✓ MessageSendThread class imported")
        print("  ✓ MessagesTab class imported")
        
        from signalbot.core.signal_handler import SignalHandler
        print("  ✓ SignalHandler class imported")
        
        from signalbot.models.message import MessageManager
        print("  ✓ MessageManager class imported")
        
        print("✓ All modules import successfully!\n")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}\n")
        return False


def test_message_manager_delete():
    """Test that message deletion works"""
    print("\n=== Testing Message Deletion ===")
    
    from signalbot.database.db import DatabaseManager
    from signalbot.models.message import MessageManager
    
    # Create test database
    test_db = '/tmp/test_message_delete.db'
    if os.path.exists(test_db):
        os.remove(test_db)
    
    import signalbot.config.settings as settings
    original_db = settings.DATABASE_FILE
    settings.DATABASE_FILE = test_db
    
    # Initialize
    db_manager = DatabaseManager('test_password')
    msg_manager = MessageManager(db_manager)
    
    # Add test messages
    my_id = "+1234567890"
    contact_id = "+0987654321"
    
    msg_manager.add_message(my_id, contact_id, "Test message 1", is_outgoing=True)
    msg_manager.add_message(contact_id, my_id, "Test message 2", is_outgoing=False)
    msg_manager.add_message(my_id, contact_id, "Test message 3", is_outgoing=True)
    
    # Verify messages added
    messages = msg_manager.get_conversation(contact_id, my_id)
    print(f"  Added {len(messages)} test messages")
    
    if len(messages) != 3:
        print(f"  ✗ Expected 3 messages, got {len(messages)}")
        return False
    
    # Test deletion
    result = msg_manager.delete_conversation(contact_id, my_id)
    print(f"  Delete operation returned: {result}")
    
    # Verify deletion
    messages = msg_manager.get_conversation(contact_id, my_id)
    print(f"  Messages after deletion: {len(messages)}")
    
    if len(messages) == 0:
        print("  ✓ Messages deleted successfully")
    else:
        print(f"  ✗ Expected 0 messages after deletion, got {len(messages)}")
        return False
    
    db_manager.close()
    
    # Restore and cleanup
    settings.DATABASE_FILE = original_db
    if os.path.exists(test_db):
        os.remove(test_db)
    
    print("✓ Message deletion works correctly!\n")
    return True


def test_threading_class():
    """Test that MessageSendThread class is properly defined"""
    print("\n=== Testing Threading Implementation ===")
    
    try:
        from signalbot.gui.dashboard import MessageSendThread
        from PyQt5.QtCore import QThread, pyqtSignal
        
        # Check if it's a QThread subclass
        if not issubclass(MessageSendThread, QThread):
            print("  ✗ MessageSendThread is not a QThread subclass")
            return False
        
        print("  ✓ MessageSendThread is a QThread subclass")
        
        # Check for finished signal
        if hasattr(MessageSendThread, 'finished'):
            print("  ✓ MessageSendThread has 'finished' signal")
        else:
            print("  ✗ MessageSendThread missing 'finished' signal")
            return False
        
        print("✓ Threading implementation is correct!\n")
        return True
    except Exception as e:
        print(f"✗ Threading test failed: {e}\n")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("Signalbot Improvements Test Suite")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Module Imports", test_imports()))
    results.append(("Database Tables", test_database_tables()))
    results.append(("Message Deletion", test_message_manager_delete()))
    results.append(("Threading Class", test_threading_class()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
