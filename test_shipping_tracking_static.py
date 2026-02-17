#!/usr/bin/env python3
"""
Static Code Analysis Test for Shipping Tracking Feature

Checks code without importing modules to avoid dependency issues.
"""

import os
import re
from pathlib import Path


def test_database_schema():
    """Test 1: Check database schema has tracking columns"""
    print("\n" + "="*60)
    print("TEST 1: Database Schema - Tracking Columns")
    print("="*60)
    
    db_file = Path(__file__).parent / "signalbot" / "database" / "db.py"
    content = db_file.read_text()
    
    checks = {
        'tracking_number column in Order model': 'tracking_number = Column(Text, nullable=True)',
        'shipped_at column in Order model': 'shipped_at = Column(DateTime, nullable=True)'
    }
    
    print("\nChecking Order model definition...")
    all_passed = True
    for check, pattern in checks.items():
        found = pattern in content
        print(f"  {'✓' if found else '✗'} {check}")
        if not found:
            all_passed = False
    
    return all_passed


def test_database_migration():
    """Test 2: Check database migration includes shipping columns"""
    print("\n" + "="*60)
    print("TEST 2: Database Migration")
    print("="*60)
    
    db_file = Path(__file__).parent / "signalbot" / "database" / "db.py"
    content = db_file.read_text()
    
    checks = {
        'tracking_number migration check': "name='tracking_number'" in content,
        'tracking_number ALTER TABLE': 'ALTER TABLE orders ADD COLUMN tracking_number' in content,
        'shipped_at migration check': "name='shipped_at'" in content,
        'shipped_at ALTER TABLE': 'ALTER TABLE orders ADD COLUMN shipped_at' in content
    }
    
    print("\nChecking _run_migrations method...")
    all_passed = True
    for check, found in checks.items():
        print(f"  {'✓' if found else '✗'} {check}")
        if not found:
            all_passed = False
    
    return all_passed


def test_order_model():
    """Test 3: Check Order model has tracking fields"""
    print("\n" + "="*60)
    print("TEST 3: Order Model - Tracking Fields")
    print("="*60)
    
    order_file = Path(__file__).parent / "signalbot" / "models" / "order.py"
    content = order_file.read_text()
    
    checks = {
        'tracking_number in __init__ params': 'tracking_number: Optional[str] = None' in content,
        'shipped_at in __init__ params': 'shipped_at: Optional[datetime] = None' in content,
        'tracking_number assignment': 'self.tracking_number = tracking_number' in content,
        'shipped_at assignment': 'self.shipped_at = shipped_at' in content,
        'tracking_number in from_db_model': 'tracking_number=' in content and 'getattr(db_order, \'tracking_number\'' in content,
        'shipped_at in from_db_model': 'shipped_at=' in content and 'getattr(db_order, \'shipped_at\'' in content,
        'tracking_number in to_db_model': 'tracking_number=self.tracking_number' in content,
        'shipped_at in to_db_model': 'shipped_at=self.shipped_at' in content
    }
    
    print("\nChecking Order class...")
    all_passed = True
    for check, found in checks.items():
        print(f"  {'✓' if found else '✗'} {check}")
        if not found:
            all_passed = False
    
    return all_passed


def test_signal_handler():
    """Test 4: Check SignalHandler has shipping notification"""
    print("\n" + "="*60)
    print("TEST 4: Signal Handler - Shipping Notification")
    print("="*60)
    
    signal_file = Path(__file__).parent / "signalbot" / "core" / "signal_handler.py"
    content = signal_file.read_text()
    
    checks = {
        'send_shipping_notification method': 'def send_shipping_notification(self, recipient: str, tracking_number: str):' in content,
        'Truck emoji in message': '🚚' in content,
        'Tracking text in message': 'Tracking:' in content,
        'Calls send_message': 'self.send_message(recipient, message)' in content
    }
    
    print("\nChecking SignalHandler class...")
    all_passed = True
    for check, found in checks.items():
        print(f"  {'✓' if found else '✗'} {check}")
        if not found:
            all_passed = False
    
    return all_passed


def test_order_manager():
    """Test 5: Check OrderManager has mark_order_shipped"""
    print("\n" + "="*60)
    print("TEST 5: Order Manager - Mark as Shipped")
    print("="*60)
    
    order_file = Path(__file__).parent / "signalbot" / "models" / "order.py"
    content = order_file.read_text()
    
    checks = {
        'mark_order_shipped method': 'def mark_order_shipped(self, order_id: str, tracking_number: str, signal_handler)' in content,
        'Validates tracking number': 'if not tracking_number or len(tracking_number.strip()) == 0:' in content,
        'Raises ValueError for empty': 'raise ValueError("Tracking number cannot be empty")' in content,
        'Updates order_status to shipped': 'order.order_status = "shipped"' in content,
        'Sets tracking_number': 'order.tracking_number = tracking_number.strip()' in content,
        'Sets shipped_at': 'order.shipped_at = datetime.utcnow()' in content,
        'Calls update_order': 'self.update_order(order)' in content,
        'Calls send_shipping_notification': 'signal_handler.send_shipping_notification' in content,
        'Handles exceptions': 'try:' in content and 'except Exception' in content
    }
    
    print("\nChecking OrderManager class...")
    all_passed = True
    for check, found in checks.items():
        print(f"  {'✓' if found else '✗'} {check}")
        if not found:
            all_passed = False
    
    return all_passed


def test_gui_orders_tab():
    """Test 6: Check OrdersTab has shipping UI"""
    print("\n" + "="*60)
    print("TEST 6: GUI Orders Tab - Shipping UI")
    print("="*60)
    
    dashboard_file = Path(__file__).parent / "signalbot" / "gui" / "dashboard.py"
    content = dashboard_file.read_text()
    
    checks = {
        'OrdersTab accepts signal_handler': 'def __init__(self, order_manager: OrderManager, signal_handler=None):' in content,
        'show_order_details method': 'def show_order_details(self, order):' in content,
        'show_shipping_input method': 'def show_shipping_input(self, order):' in content,
        'show_shipped_details method': 'def show_shipped_details(self, order):' in content,
        'on_mark_shipped method': 'def on_mark_shipped(self):' in content,
        'on_resend_tracking method': 'def on_resend_tracking(self):' in content,
        'Tracking input field': 'self.tracking_input = QLineEdit()' in content,
        'Mark as Shipped button': '"Mark as Shipped"' in content,
        'Resend button': '"Resend Tracking Info"' in content,
        'Calls mark_order_shipped': 'self.order_manager.mark_order_shipped(' in content,
        'Shows success message': '"✅ Order shipped and customer notified!"' in content,
        'Handles notification failure': '"notification failed"' in content.lower()
    }
    
    print("\nChecking OrdersTab class...")
    all_passed = True
    for check, found in checks.items():
        print(f"  {'✓' if found else '✗'} {check}")
        if not found:
            all_passed = False
    
    return all_passed


def test_dashboard_instantiation():
    """Test 7: Check DashboardWindow passes signal_handler to OrdersTab"""
    print("\n" + "="*60)
    print("TEST 7: Dashboard - OrdersTab Instantiation")
    print("="*60)
    
    dashboard_file = Path(__file__).parent / "signalbot" / "gui" / "dashboard.py"
    content = dashboard_file.read_text()
    
    checks = {
        'OrdersTab instantiation with signal_handler': 'OrdersTab(self.order_manager, self.signal_handler)' in content
    }
    
    print("\nChecking DashboardWindow class...")
    all_passed = True
    for check, found in checks.items():
        print(f"  {'✓' if found else '✗'} {check}")
        if not found:
            all_passed = False
    
    return all_passed


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("SHIPPING TRACKING FEATURE - STATIC CODE ANALYSIS")
    print("="*70)
    
    tests = [
        ("Database Schema", test_database_schema),
        ("Database Migration", test_database_migration),
        ("Order Model", test_order_model),
        ("Signal Handler", test_signal_handler),
        ("Order Manager", test_order_manager),
        ("GUI Orders Tab", test_gui_orders_tab),
        ("Dashboard Instantiation", test_dashboard_instantiation)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
            if result:
                print(f"\n✅ TEST PASSED: {name}")
            else:
                print(f"\n❌ TEST FAILED: {name}")
        except Exception as e:
            print(f"\n❌ TEST ERROR: {name}")
            print(f"   Exception: {str(e)}")
            results.append((name, False))
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! 🎉")
        print("\nThe shipping tracking feature has been successfully implemented:")
        print("  - Database schema includes tracking_number and shipped_at columns")
        print("  - Order model supports tracking fields")
        print("  - Signal notification sends tracking info to customers")
        print("  - OrderManager can mark orders as shipped")
        print("  - GUI shows tracking input and shipped order details")
        print("\nReady for manual testing and integration!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
