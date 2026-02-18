#!/usr/bin/env python3
"""
Static Code Analysis Test for Order Flow Improvements

Tests for:
1. Database table creation with logging
2. Name/Address collection during orders (conversation state)
3. Catalogue alias support
4. Tracking number workflow enhancements
"""

import os
import re
from pathlib import Path


def test_database_logging():
    """Test 1: Check database initialization has proper logging"""
    print("\n" + "="*60)
    print("TEST 1: Database Initialization Logging")
    print("="*60)
    
    db_file = Path(__file__).parent / "signalbot" / "database" / "db.py"
    content = db_file.read_text()
    
    checks = {
        'Log database file location': 'Database file:' in content,
        'Log tables to create': 'Tables to create:' in content,
        'Log successful creation': 'Database tables created successfully' in content,
        'Verify tables exist': 'Verified tables in database:' in content,
        'Check for missing tables': 'Some tables are missing' in content,
        'Import inspect for verification': 'from sqlalchemy import inspect' in content,
    }
    
    print("\nChecking DatabaseManager.__init__ logging...")
    all_passed = True
    for check, pattern in checks.items():
        if isinstance(pattern, bool):
            found = pattern
        else:
            found = pattern in content
        print(f"  {'✓' if found else '✗'} {check}")
        if not found:
            all_passed = False
    
    return all_passed


def test_conversation_state_tracking():
    """Test 2: Check conversation state tracking for order flow"""
    print("\n" + "="*60)
    print("TEST 2: Conversation State Tracking")
    print("="*60)
    
    buyer_handler_file = Path(__file__).parent / "signalbot" / "core" / "buyer_handler.py"
    content = buyer_handler_file.read_text()
    
    checks = {
        'Conversation states dictionary initialized': 'self.conversation_states = {}' in content,
        'Check conversation state in handle_buyer_message': 'if buyer_signal_id in self.conversation_states:' in content,
        '_handle_conversation_state method exists': 'def _handle_conversation_state(' in content,
        '_initiate_order_conversation method exists': 'def _initiate_order_conversation(' in content,
        '_create_order_with_shipping_info method exists': 'def _create_order_with_shipping_info(' in content,
        'Ask for name': "What's your name?" in content,
        'Ask for shipping address': "What's your shipping address?" in content,
        'State: awaiting_name': "'state': 'awaiting_name'" in content,
        'State: awaiting_address': "'awaiting_address'" in content,
        'Store name in state': "state_info['name'] = message_text.strip()" in content,
        'Store address in state': "state_info['address'] = message_text.strip()" in content,
        'Create JSON shipping info': 'import json' in content and "'name': name" in content and "'address': address" in content,
    }
    
    print("\nChecking BuyerHandler conversation flow...")
    all_passed = True
    for check, pattern in checks.items():
        if isinstance(pattern, bool):
            found = pattern
        else:
            found = pattern in content
        print(f"  {'✓' if found else '✗'} {check}")
        if not found:
            all_passed = False
    
    return all_passed


def test_order_creation_with_shipping_info():
    """Test 3: Check create_order accepts shipping_info parameter"""
    print("\n" + "="*60)
    print("TEST 3: Order Creation with Shipping Info")
    print("="*60)
    
    buyer_handler_file = Path(__file__).parent / "signalbot" / "core" / "buyer_handler.py"
    content = buyer_handler_file.read_text()
    
    checks = {
        'create_order has shipping_info parameter': 'def create_order(self, buyer_signal_id: str, product_id: str, quantity: int, recipient_identity: Optional[str] = None, shipping_info: Optional[str] = None)' in content,
        'shipping_info passed to Order object': 'shipping_info=shipping_info' in content,
        'shipping_info in docstring': 'shipping_info: JSON string with shipping information' in content,
    }
    
    print("\nChecking create_order method...")
    all_passed = True
    for check, pattern in checks.items():
        if isinstance(pattern, bool):
            found = pattern
        else:
            found = pattern in content
        print(f"  {'✓' if found else '✗'} {check}")
        if not found:
            all_passed = False
    
    return all_passed


def test_catalogue_alias():
    """Test 4: Check 'catalogue' alias is supported"""
    print("\n" + "="*60)
    print("TEST 4: Catalogue Alias Support")
    print("="*60)
    
    buyer_handler_file = Path(__file__).parent / "signalbot" / "core" / "buyer_handler.py"
    content = buyer_handler_file.read_text()
    
    # Check if 'catalogue' is in the catalog_keywords list
    catalog_keywords_match = re.search(r"catalog_keywords\s*=\s*\[(.*?)\]", content, re.DOTALL)
    
    checks = {
        'catalog_keywords list exists': catalog_keywords_match is not None,
        "'catalog' in keywords": False,
        "'catalogue' in keywords": False,
    }
    
    if catalog_keywords_match:
        keywords_str = catalog_keywords_match.group(1)
        checks["'catalog' in keywords"] = "'catalog'" in keywords_str
        checks["'catalogue' in keywords"] = "'catalogue'" in keywords_str
    
    print("\nChecking catalog command matching...")
    all_passed = True
    for check, result in checks.items():
        print(f"  {'✓' if result else '✗'} {check}")
        if not result:
            all_passed = False
    
    return all_passed


def test_enhanced_shipping_notification():
    """Test 5: Check shipping notification enhancement"""
    print("\n" + "="*60)
    print("TEST 5: Enhanced Shipping Notification")
    print("="*60)
    
    signal_handler_file = Path(__file__).parent / "signalbot" / "core" / "signal_handler.py"
    content = signal_handler_file.read_text()
    
    checks = {
        'send_shipping_notification has order_id parameter': 'def send_shipping_notification(self, recipient: str, order_id: str, tracking_number: str, shipped_at)' in content,
        'Notification includes order ID': 'order #{order_id}' in content.lower(),
        'Notification includes tracking number': 'Tracking Number:' in content,
        'Notification includes shipped date': 'Shipped:' in content,
        'Notification includes emoji': '🚚' in content,
        'Handles missing tracking number': 'if tracking_number and tracking_number.strip():' in content,
        'Formats shipped date': "shipped_date = shipped_at.strftime" in content,
    }
    
    print("\nChecking SignalHandler.send_shipping_notification...")
    all_passed = True
    for check, pattern in checks.items():
        if isinstance(pattern, bool):
            found = pattern
        else:
            found = pattern in content
        print(f"  {'✓' if found else '✗'} {check}")
        if not found:
            all_passed = False
    
    return all_passed


def test_order_manager_calls_shipping_notification():
    """Test 6: Check OrderManager passes correct parameters"""
    print("\n" + "="*60)
    print("TEST 6: OrderManager Shipping Notification Calls")
    print("="*60)
    
    order_file = Path(__file__).parent / "signalbot" / "models" / "order.py"
    content = order_file.read_text()
    
    checks = {
        'mark_order_shipped method exists': 'def mark_order_shipped(' in content,
        'Calls send_shipping_notification': 'signal_handler.send_shipping_notification' in content,
        'Passes order.order_id': 'order.order_id,' in content,
        'Passes tracking_number': 'tracking_number,' in content,
        'Passes order.shipped_at': 'order.shipped_at' in content,
        'resend_tracking_notification method exists': 'def resend_tracking_notification(' in content,
    }
    
    print("\nChecking OrderManager shipping notification calls...")
    all_passed = True
    for check, pattern in checks.items():
        if isinstance(pattern, bool):
            found = pattern
        else:
            found = pattern in content
        print(f"  {'✓' if found else '✗'} {check}")
        if not found:
            all_passed = False
    
    return all_passed


def test_dashboard_mark_shipped_button():
    """Test 7: Verify dashboard has Mark as Shipped functionality"""
    print("\n" + "="*60)
    print("TEST 7: Dashboard Mark as Shipped Button")
    print("="*60)
    
    dashboard_file = Path(__file__).parent / "signalbot" / "gui" / "dashboard.py"
    content = dashboard_file.read_text()
    
    checks = {
        'show_shipping_input method exists': 'def show_shipping_input(' in content,
        'Mark as Shipped button created': '"Mark as Shipped"' in content,
        'on_mark_shipped handler exists': 'def on_mark_shipped(' in content,
        'Tracking input field': 'self.tracking_input' in content,
        'Calls order_manager.mark_order_shipped': 'self.order_manager.mark_order_shipped' in content,
        'show_shipped_details method exists': 'def show_shipped_details(' in content,
        'on_resend_tracking handler exists': 'def on_resend_tracking(' in content,
    }
    
    print("\nChecking Dashboard shipping functionality...")
    all_passed = True
    for check, pattern in checks.items():
        if isinstance(pattern, bool):
            found = pattern
        else:
            found = pattern in content
        print(f"  {'✓' if found else '✗'} {check}")
        if not found:
            all_passed = False
    
    return all_passed


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("ORDER FLOW IMPROVEMENTS - STATIC CODE ANALYSIS")
    print("="*60)
    
    tests = [
        test_database_logging,
        test_conversation_state_tracking,
        test_order_creation_with_shipping_info,
        test_catalogue_alias,
        test_enhanced_shipping_notification,
        test_order_manager_calls_shipping_notification,
        test_dashboard_mark_shipped_button,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n❌ TEST ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    # Final summary
    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n✅ Passed: {passed}/{total} tests")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! 🎉")
        print("\nImplementation Summary:")
        print("  ✓ Database table creation with detailed logging")
        print("  ✓ Conversation state tracking for name/address collection")
        print("  ✓ Order creation accepts shipping_info parameter")
        print("  ✓ 'catalogue' alias supported (already implemented)")
        print("  ✓ Enhanced shipping notification with order ID and date")
        print("  ✓ OrderManager properly calls shipping notification")
        print("  ✓ Dashboard Mark as Shipped functionality (already implemented)")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit(main())
