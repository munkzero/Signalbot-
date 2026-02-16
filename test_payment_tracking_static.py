#!/usr/bin/env python3
"""
Static Code Analysis Test for Payment Tracking System

Tests the implementation through static code analysis without requiring
dependencies to be installed.
"""

import sys
import re
from pathlib import Path

def read_file(filepath):
    """Read file content"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None

def test_rpc_flags():
    """Test 1: Verify RPC command has required flags"""
    print("\n" + "="*60)
    print("TEST 1: RPC Command Flags")
    print("="*60)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    content = read_file(wallet_setup_path)
    
    if not content:
        return False
    
    required_flags = [
        '--rpc-bind-ip',
        '--trusted-daemon',
        '--disable-rpc-login',
        '--daemon-address'
    ]
    
    print("\nChecking for required RPC flags...")
    all_present = True
    for flag in required_flags:
        if flag in content:
            print(f"  ✓ {flag} - FOUND")
        else:
            print(f"  ✗ {flag} - MISSING")
            all_present = False
    
    if all_present:
        print("\n✅ TEST PASSED")
        return True
    else:
        print("\n❌ TEST FAILED")
        return False

def test_database_schema():
    """Test 2: Verify database schema has new columns"""
    print("\n" + "="*60)
    print("TEST 2: Database Schema Updates")
    print("="*60)
    
    db_path = Path("signalbot/database/db.py")
    content = read_file(db_path)
    
    if not content:
        return False
    
    # Check for new columns in Order table
    order_class = re.search(r'class Order\(Base\):.*?(?=class \w+|\Z)', content, re.DOTALL)
    if not order_class:
        print("  ✗ Could not find Order class")
        return False
    
    order_text = order_class.group(0)
    
    print("\nChecking Order table columns...")
    required_columns = [
        ('address_index', 'INTEGER'),
        ('payment_txid', 'TEXT'),
    ]
    
    all_present = True
    for col_name, col_type in required_columns:
        if col_name in order_text:
            print(f"  ✓ {col_name} ({col_type}) - FOUND")
        else:
            print(f"  ✗ {col_name} ({col_type}) - MISSING")
            all_present = False
    
    # Check for PaymentHistory table
    print("\nChecking PaymentHistory table...")
    if 'class PaymentHistory' in content:
        print("  ✓ PaymentHistory table - DEFINED")
        
        payment_history_class = re.search(r'class PaymentHistory\(Base\):.*?(?=class \w+|\Z)', content, re.DOTALL)
        if payment_history_class:
            ph_text = payment_history_class.group(0)
            required_ph_cols = ['order_id', 'event_type', 'amount', 'txid', 'confirmations']
            for col in required_ph_cols:
                if col in ph_text:
                    print(f"    ✓ {col} column")
                else:
                    print(f"    ✗ {col} column - MISSING")
                    all_present = False
    else:
        print("  ✗ PaymentHistory table - NOT DEFINED")
        all_present = False
    
    # Check for migration function
    print("\nChecking database migration...")
    if '_run_migrations' in content:
        print("  ✓ Migration function - DEFINED")
    else:
        print("  ✗ Migration function - MISSING")
        all_present = False
    
    if all_present:
        print("\n✅ TEST PASSED")
        return True
    else:
        print("\n❌ TEST FAILED")
        return False

def test_order_model():
    """Test 3: Verify Order model supports new fields"""
    print("\n" + "="*60)
    print("TEST 3: Order Model Fields")
    print("="*60)
    
    order_path = Path("signalbot/models/order.py")
    content = read_file(order_path)
    
    if not content:
        return False
    
    # Check __init__ parameters
    init_match = re.search(r'def __init__\s*\((.*?)\):', content, re.DOTALL)
    if not init_match:
        print("  ✗ Could not find __init__ method")
        return False
    
    init_params = init_match.group(1)
    
    print("\nChecking Order.__init__() parameters...")
    required_params = ['address_index', 'payment_txid']
    all_present = True
    
    for param in required_params:
        if param in init_params:
            print(f"  ✓ {param} - FOUND")
        else:
            print(f"  ✗ {param} - MISSING")
            all_present = False
    
    # Check from_db_model method
    print("\nChecking from_db_model() method...")
    if 'address_index=db_order.address_index' in content:
        print("  ✓ address_index mapping - FOUND")
    else:
        print("  ✗ address_index mapping - MISSING")
        all_present = False
    
    if 'payment_txid=db_order.payment_txid' in content:
        print("  ✓ payment_txid mapping - FOUND")
    else:
        print("  ✗ payment_txid mapping - MISSING")
        all_present = False
    
    if all_present:
        print("\n✅ TEST PASSED")
        return True
    else:
        print("\n❌ TEST FAILED")
        return False

def test_payment_processor():
    """Test 4: Verify PaymentProcessor enhancements"""
    print("\n" + "="*60)
    print("TEST 4: PaymentProcessor Enhancements")
    print("="*60)
    
    payments_path = Path("signalbot/core/payments.py")
    content = read_file(payments_path)
    
    if not content:
        return False
    
    print("\nChecking PaymentProcessor enhancements...")
    
    features = [
        ('subaddr_indices', 'Subaddress index monitoring'),
        ('unconfirmed', 'Unconfirmed payment state'),
        ('partial', 'Partial payment state'),
        ('payment_txid', 'Transaction ID storage'),
        ('_send_payment_confirmation', 'Payment confirmation notification'),
        ('MONERO_CONFIRMATIONS_REQUIRED', 'Confirmation threshold'),
    ]
    
    all_present = True
    for keyword, description in features:
        if keyword in content:
            print(f"  ✓ {description} - FOUND")
        else:
            print(f"  ✗ {description} - MISSING")
            all_present = False
    
    if all_present:
        print("\n✅ TEST PASSED")
        return True
    else:
        print("\n❌ TEST FAILED")
        return False

def test_monero_wallet():
    """Test 5: Verify MoneroWallet.get_transfers enhancements"""
    print("\n" + "="*60)
    print("TEST 5: MoneroWallet.get_transfers Enhancement")
    print("="*60)
    
    wallet_path = Path("signalbot/core/monero_wallet.py")
    content = read_file(wallet_path)
    
    if not content:
        return False
    
    # Find get_transfers method
    get_transfers_match = re.search(r'def get_transfers\s*\((.*?)\):', content, re.DOTALL)
    if not get_transfers_match:
        print("  ✗ get_transfers method not found")
        return False
    
    params = get_transfers_match.group(1)
    
    print("\nChecking get_transfers() parameters...")
    required_params = ['subaddr_indices', 'account_index']
    all_present = True
    
    for param in required_params:
        if param in params:
            print(f"  ✓ {param} - FOUND")
        else:
            print(f"  ✗ {param} - MISSING")
            all_present = False
    
    # Check implementation
    get_transfers_impl = re.search(r'def get_transfers.*?(?=\n    def |\Z)', content, re.DOTALL)
    if get_transfers_impl:
        impl_text = get_transfers_impl.group(0)
        if 'subaddr_indices' in impl_text and 'params[' in impl_text:
            print("  ✓ subaddr_indices used in params - FOUND")
        else:
            print("  ✗ subaddr_indices not properly used")
            all_present = False
    
    if all_present:
        print("\n✅ TEST PASSED")
        return True
    else:
        print("\n❌ TEST FAILED")
        return False

def test_gui_orders_tab():
    """Test 6: Verify GUI OrdersTab enhancements"""
    print("\n" + "="*60)
    print("TEST 6: GUI OrdersTab Payment Display")
    print("="*60)
    
    dashboard_path = Path("signalbot/gui/dashboard.py")
    content = read_file(dashboard_path)
    
    if not content:
        return False
    
    # Find OrdersTab class
    orders_tab_match = re.search(r'class OrdersTab.*?(?=class \w+|\Z)', content, re.DOTALL)
    if not orders_tab_match:
        print("  ✗ OrdersTab class not found")
        return False
    
    orders_tab_text = orders_tab_match.group(0)
    
    print("\nChecking OrdersTab enhancements...")
    
    features = [
        ('setColumnCount(9)', 'Extended column count'),
        ('payment_txid', 'Transaction ID display'),
        ('amount_paid', 'Paid amount display'),
        ('QColor', 'Color-coded status'),
        ('status_map', 'Status emoji indicators'),
        ('QTimer', 'Auto-refresh timer'),
        ('refresh_timer', 'Timer instance'),
    ]
    
    all_present = True
    for keyword, description in features:
        if keyword in orders_tab_text:
            print(f"  ✓ {description} - FOUND")
        else:
            print(f"  ✗ {description} - MISSING")
            all_present = False
    
    if all_present:
        print("\n✅ TEST PASSED")
        return True
    else:
        print("\n❌ TEST FAILED")
        return False

def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "="*60)
    print("PAYMENT TRACKING STATIC CODE ANALYSIS")
    print("="*60)
    print("Testing implementation through code analysis...")
    
    tests = [
        ("RPC Command Flags", test_rpc_flags),
        ("Database Schema", test_database_schema),
        ("Order Model", test_order_model),
        ("PaymentProcessor", test_payment_processor),
        ("MoneroWallet.get_transfers", test_monero_wallet),
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
    percentage = round(passed * 100 / total) if total > 0 else 0
    print(f"Results: {passed}/{total} tests passed ({percentage}%)")
    print("="*60)
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("\nThe payment tracking system implementation is complete!")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Start the bot: ./start.sh")
        print("3. Test RPC auto-start on launch")
        print("4. Create a test order and send payment")
        print("5. Verify payment monitoring and auto-confirmation")
        return 0
    else:
        print(f"\n⚠️  {total - passed} TEST(S) FAILED")
        print("\nPlease review the failed tests above.")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
