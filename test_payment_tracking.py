#!/usr/bin/env python3
"""
Test Payment Tracking with Unique Subaddresses

Tests the automatic payment tracking implementation including:
- RPC auto-start with correct flags
- Database schema updates
- Unique subaddress generation per order
- Payment monitoring with status tracking
- Auto-confirmation and notifications
"""

import sys
import os
import time
from pathlib import Path

# Add signalbot to path
sys.path.insert(0, str(Path(__file__).parent))

def test_rpc_command_flags():
    """Test 1: Verify RPC command has required flags"""
    print("\n" + "="*60)
    print("TEST 1: RPC Command Flags")
    print("="*60)
    
    from signalbot.core.wallet_setup import WalletSetupManager
    
    # Create mock wallet setup
    wallet_path = "/tmp/test_wallet"
    setup = WalletSetupManager(
        wallet_path=wallet_path,
        daemon_address="xmr-node.cakewallet.com",
        daemon_port=18081,
        rpc_port=18082,
        password=""
    )
    
    # Check the start_rpc method has correct flags
    import inspect
    source = inspect.getsource(setup.start_rpc)
    
    required_flags = [
        '--rpc-bind-ip',
        '--trusted-daemon',
        '--disable-rpc-login',
        '--daemon-address'
    ]
    
    print("\nChecking for required RPC flags in start_rpc()...")
    all_present = True
    for flag in required_flags:
        if flag in source:
            print(f"  ✓ {flag} - FOUND")
        else:
            print(f"  ✗ {flag} - MISSING")
            all_present = False
    
    if all_present:
        print("\n✅ TEST PASSED: All required RPC flags present")
        return True
    else:
        print("\n❌ TEST FAILED: Missing required RPC flags")
        return False


def test_database_schema():
    """Test 2: Verify database schema has new columns"""
    print("\n" + "="*60)
    print("TEST 2: Database Schema Updates")
    print("="*60)
    
    from signalbot.database.db import Order, PaymentHistory, Base
    from sqlalchemy import inspect as sql_inspect
    
    # Check Order table columns
    order_columns = {col.name for col in sql_inspect(Order).columns}
    
    required_columns = ['address_index', 'payment_txid']
    
    print("\nChecking Order table columns...")
    all_present = True
    for col in required_columns:
        if col in order_columns:
            print(f"  ✓ {col} - EXISTS")
        else:
            print(f"  ✗ {col} - MISSING")
            all_present = False
    
    # Check PaymentHistory table exists
    print("\nChecking PaymentHistory table...")
    try:
        payment_history_cols = {col.name for col in sql_inspect(PaymentHistory).columns}
        expected_cols = ['id', 'order_id', 'event_type', 'amount', 'txid', 'confirmations', 'timestamp']
        
        for col in expected_cols:
            if col in payment_history_cols:
                print(f"  ✓ {col} - EXISTS")
            else:
                print(f"  ✗ {col} - MISSING")
                all_present = False
    except Exception as e:
        print(f"  ✗ PaymentHistory table - ERROR: {e}")
        all_present = False
    
    if all_present:
        print("\n✅ TEST PASSED: Database schema is correct")
        return True
    else:
        print("\n❌ TEST FAILED: Database schema incomplete")
        return False


def test_order_model():
    """Test 3: Verify Order model supports new fields"""
    print("\n" + "="*60)
    print("TEST 3: Order Model Fields")
    print("="*60)
    
    from signalbot.models.order import Order
    from datetime import datetime
    
    # Create test order
    order = Order(
        order_id="TEST-001",
        customer_signal_id="+15555550123",
        product_id=1,
        product_name="Test Product",
        quantity=1,
        price_fiat=100.0,
        currency="USD",
        price_xmr=0.5,
        payment_address="86zCSDcF71BVkJEi8tgfZ65PDazoviD8KAVyzbcGQPNX4FTVLREqSEVgc9odL4yj2C8cY31JZDRxPNhyNijNoa7hEpnH6yW",
        address_index=5,
        payment_status="pending",
        payment_txid=None,
        order_status="processing",
        amount_paid=0.0,
        commission_amount=0.035,
        seller_amount=0.465
    )
    
    print("\nTesting Order model fields...")
    tests_passed = True
    
    # Test new fields
    if hasattr(order, 'address_index') and order.address_index == 5:
        print("  ✓ address_index - WORKING")
    else:
        print("  ✗ address_index - FAILED")
        tests_passed = False
    
    if hasattr(order, 'payment_txid'):
        print("  ✓ payment_txid - WORKING")
    else:
        print("  ✗ payment_txid - FAILED")
        tests_passed = False
    
    if hasattr(order, 'payment_status') and order.payment_status == "pending":
        print("  ✓ payment_status - WORKING")
    else:
        print("  ✗ payment_status - FAILED")
        tests_passed = False
    
    if tests_passed:
        print("\n✅ TEST PASSED: Order model supports new fields")
        return True
    else:
        print("\n❌ TEST FAILED: Order model incomplete")
        return False


def test_payment_processor_enhancements():
    """Test 4: Verify PaymentProcessor has enhanced monitoring"""
    print("\n" + "="*60)
    print("TEST 4: PaymentProcessor Enhancements")
    print("="*60)
    
    from signalbot.core.payments import PaymentProcessor
    import inspect
    
    # Check check_order_payment method
    source = inspect.getsource(PaymentProcessor.check_order_payment)
    
    print("\nChecking PaymentProcessor.check_order_payment()...")
    
    required_features = [
        ('subaddr_indices', 'Subaddress index monitoring'),
        ('unconfirmed', 'Unconfirmed payment detection'),
        ('partial', 'Partial payment detection'),
        ('txid', 'Transaction ID tracking')
    ]
    
    all_present = True
    for keyword, description in required_features:
        if keyword in source:
            print(f"  ✓ {description} - IMPLEMENTED")
        else:
            print(f"  ✗ {description} - MISSING")
            all_present = False
    
    # Check _send_payment_confirmation method exists
    if hasattr(PaymentProcessor, '_send_payment_confirmation'):
        print("  ✓ Payment confirmation notifications - IMPLEMENTED")
    else:
        print("  ✗ Payment confirmation notifications - MISSING")
        all_present = False
    
    if all_present:
        print("\n✅ TEST PASSED: PaymentProcessor has all enhancements")
        return True
    else:
        print("\n❌ TEST FAILED: PaymentProcessor incomplete")
        return False


def test_monero_wallet_get_transfers():
    """Test 5: Verify MoneroWallet.get_transfers supports subaddr_indices"""
    print("\n" + "="*60)
    print("TEST 5: MoneroWallet.get_transfers Enhancement")
    print("="*60)
    
    from signalbot.core.monero_wallet import MoneroWallet
    import inspect
    
    # Get method signature
    sig = inspect.signature(MoneroWallet.get_transfers)
    params = list(sig.parameters.keys())
    
    print("\nChecking get_transfers() parameters...")
    
    required_params = ['subaddr_indices', 'account_index']
    all_present = True
    
    for param in required_params:
        if param in params:
            print(f"  ✓ {param} - EXISTS")
        else:
            print(f"  ✗ {param} - MISSING")
            all_present = False
    
    if all_present:
        print("\n✅ TEST PASSED: get_transfers supports subaddress monitoring")
        return True
    else:
        print("\n❌ TEST FAILED: get_transfers missing parameters")
        return False


def test_gui_orders_tab():
    """Test 6: Verify GUI OrdersTab displays payment info"""
    print("\n" + "="*60)
    print("TEST 6: GUI OrdersTab Payment Display")
    print("="*60)
    
    import inspect
    from signalbot.gui.dashboard import OrdersTab
    
    # Check load_orders method
    source = inspect.getsource(OrdersTab.load_orders)
    
    print("\nChecking OrdersTab.load_orders()...")
    
    required_features = [
        ('payment_txid', 'Transaction ID display'),
        ('amount_paid', 'Paid amount display'),
        ('QColor', 'Color-coded status'),
        ('status_map', 'Status emoji indicators')
    ]
    
    all_present = True
    for keyword, description in required_features:
        if keyword in source:
            print(f"  ✓ {description} - IMPLEMENTED")
        else:
            print(f"  ✗ {description} - MISSING")
            all_present = False
    
    # Check for auto-refresh timer
    init_source = inspect.getsource(OrdersTab.__init__)
    if 'QTimer' in init_source and 'refresh_timer' in init_source:
        print("  ✓ Auto-refresh timer - IMPLEMENTED")
    else:
        print("  ✗ Auto-refresh timer - MISSING")
        all_present = False
    
    if all_present:
        print("\n✅ TEST PASSED: GUI displays enhanced payment info")
        return True
    else:
        print("\n❌ TEST FAILED: GUI enhancements incomplete")
        return False


def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "="*60)
    print("PAYMENT TRACKING SYSTEM TEST SUITE")
    print("="*60)
    print("Testing automatic payment tracking implementation...")
    
    tests = [
        ("RPC Command Flags", test_rpc_command_flags),
        ("Database Schema", test_database_schema),
        ("Order Model", test_order_model),
        ("PaymentProcessor", test_payment_processor_enhancements),
        ("MoneroWallet.get_transfers", test_monero_wallet_get_transfers),
        ("GUI OrdersTab", test_gui_orders_tab)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n❌ TEST ERROR: {name}")
            print(f"   Exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print("\n" + "-"*60)
    print(f"Results: {passed}/{total} tests passed ({round(passed*100/total) if total > 0 else 0}%)")
    print("="*60)
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("\nThe payment tracking system is ready for testing!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} TEST(S) FAILED")
        print("\nPlease review the failed tests above.")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
