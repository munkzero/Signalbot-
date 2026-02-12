#!/usr/bin/env python3
"""
Test script to verify the QButtonGroup registerField fix
Tests that NodeConfigPage can be instantiated and properly tracks button selections
"""

import sys
import os

# Set Qt platform before importing PyQt5
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PyQt5.QtWidgets import QApplication, QWizard
from signalbot.gui.wizard import NodeConfigPage
from signalbot.database.db import DatabaseManager

def test_node_config_page_instantiation():
    """Test that NodeConfigPage can be instantiated without registerField errors"""
    print("Testing NodeConfigPage instantiation...")
    
    app = QApplication(sys.argv)
    
    try:
        page = NodeConfigPage()
        print("  ✓ NodeConfigPage created successfully")
        
        # Verify proxy widget exists
        assert hasattr(page, 'selected_node_value'), "Proxy widget not found"
        print("  ✓ Proxy widget (selected_node_value) exists")
        
        # Verify button group exists
        assert hasattr(page, 'node_button_group'), "Button group not found"
        print("  ✓ QButtonGroup (node_button_group) exists")
        
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_initial_value():
    """Test that initial button selection sets proxy value"""
    print("\nTesting initial value...")
    
    app = QApplication(sys.argv)
    
    try:
        page = NodeConfigPage()
        
        # Check that a button is initially selected
        checked = page.node_button_group.checkedButton()
        assert checked is not None, "No button initially checked"
        print("  ✓ Initial button is checked")
        
        # Check that proxy value is set
        proxy_value = page.selected_node_value.text()
        assert proxy_value, "Proxy value not set"
        print(f"  ✓ Proxy value is set: {proxy_value}")
        
        # Verify proxy matches checked ID
        checked_id = page.node_button_group.checkedId()
        assert str(checked_id) == proxy_value, f"Mismatch: {checked_id} != {proxy_value}"
        print(f"  ✓ Proxy value matches checked ID: {checked_id}")
        
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_button_click_updates():
    """Test that clicking buttons updates the proxy value"""
    print("\nTesting button click updates...")
    
    app = QApplication(sys.argv)
    
    try:
        page = NodeConfigPage()
        buttons = page.node_button_group.buttons()
        
        print(f"  Testing {min(3, len(buttons))} button clicks...")
        
        for i, button in enumerate(buttons[:3]):
            button.click()
            checked_id = page.node_button_group.checkedId()
            proxy_value = page.selected_node_value.text()
            
            assert str(checked_id) == proxy_value, f"Button {i}: Mismatch {checked_id} != {proxy_value}"
            print(f"  ✓ Button {i}: ID={checked_id}, Proxy={proxy_value}")
        
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_wizard_integration():
    """Test that SetupWizard can be created with the fixed NodeConfigPage"""
    print("\nTesting wizard integration...")
    
    app = QApplication(sys.argv)
    
    # Clean up any existing test db
    test_db = 'signalbot.db'
    backup_exists = os.path.exists(test_db)
    if backup_exists:
        os.rename(test_db, test_db + '.backup')
    
    try:
        from signalbot.gui.wizard import SetupWizard
        
        db_manager = DatabaseManager('test_password')
        wizard = SetupWizard(db_manager)
        
        print(f"  ✓ SetupWizard created with {len(wizard.pageIds())} pages")
        print("  ✓ No registerField error occurred")
        
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        if os.path.exists(test_db):
            os.remove(test_db)
        if backup_exists and os.path.exists(test_db + '.backup'):
            os.rename(test_db + '.backup', test_db)

def test_field_retrieval():
    """Test that the registered field can be retrieved as an integer"""
    print("\nTesting field retrieval...")
    
    app = QApplication(sys.argv)
    
    try:
        wizard = QWizard()
        page = NodeConfigPage()
        wizard.addPage(page)
        
        # Simulate clicking the second button
        buttons = page.node_button_group.buttons()
        if len(buttons) > 1:
            buttons[1].click()
            
            # Get field value (this is how the wizard retrieves it)
            field_value = page.field("selected_node_index")
            print(f"  ✓ Field value retrieved: {field_value} (type: {type(field_value).__name__})")
            
            # Verify it can be converted to int (as done in the fix)
            int_value = int(field_value)
            print(f"  ✓ Converted to int: {int_value}")
            
            # Verify it matches the checked button
            checked_id = page.node_button_group.checkedId()
            assert int_value == checked_id, f"Mismatch: {int_value} != {checked_id}"
            print(f"  ✓ Field value matches checked ID: {checked_id}")
        
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 70)
    print("QBUTTONGROUP REGISTERFIELD FIX VERIFICATION")
    print("=" * 70)
    
    tests = [
        ("NodeConfigPage instantiation", test_node_config_page_instantiation),
        ("Initial value", test_initial_value),
        ("Button click updates", test_button_click_updates),
        ("Wizard integration", test_wizard_integration),
        ("Field retrieval", test_field_retrieval),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test '{name}' failed with exception: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 70)
    print("TEST RESULTS")
    print("=" * 70)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n✅ ALL TESTS PASSED - QButtonGroup fix is working correctly!")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        return 1

if __name__ == '__main__':
    sys.exit(main())
