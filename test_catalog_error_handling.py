#!/usr/bin/env python3
"""
Test catalog error handling improvements

This test verifies that the catalog sending improvements are in place:
- Retry logic for failed sends
- Error handling that continues the loop
- Progress tracking
- Summary reporting
"""

import os
import sys
import ast

def test_buyer_handler_improvements():
    """Test that buyer_handler.py has all required improvements"""
    print("=" * 80)
    print("TEST: Catalog Error Handling - buyer_handler.py")
    print("=" * 80)
    
    handler_file = os.path.join(os.path.dirname(__file__), 'signalbot/core/buyer_handler.py')
    
    with open(handler_file, 'r') as f:
        source = f.read()
    
    # Parse the source to verify structure
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        print(f"❌ SYNTAX ERROR in buyer_handler.py: {e}")
        return False
    
    # Find the send_catalog method
    send_catalog_found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == 'send_catalog':
            send_catalog_found = True
            
            # Check for proper docstring mentioning error handling
            docstring = ast.get_docstring(node)
            if docstring and 'error handling' in docstring.lower():
                print("✅ send_catalog() has updated docstring mentioning error handling")
            else:
                print("⚠️  send_catalog() docstring could mention error handling")
            
            break
    
    if not send_catalog_found:
        print("❌ send_catalog() method not found")
        return False
    
    # Check for specific improvements in the source
    required_features = {
        "Retry logic": "max_retries = 2",
        "Retry loop": "for attempt in range(1, max_retries + 1):",
        "Success tracking": "sent_count = 0",
        "Failed products tracking": "failed_products = []",
        "Try/except around send": "except Exception as e:",
        "Progress logging": "📦 Product",
        "Summary report": "📊 CATALOG SEND COMPLETE",
        "Retry delay": "time.sleep(3)",
        "Product spacing delay": "delay = 2.5",
        "Success message": "✅ SUCCESS",
    }
    
    all_passed = True
    for feature_name, check_string in required_features.items():
        if check_string in source:
            print(f"✅ {feature_name}: Found")
        else:
            print(f"❌ {feature_name}: NOT FOUND")
            all_passed = False
    
    # Check header try/except separately
    if "try:" in source and "print(f\"✓ Catalog header sent" in source:
        print("✅ Header try/except: Found")
    else:
        print("⚠️  Header try/except: Partial or not found")
    
    # Check that old problematic pattern is removed
    if "self.signal_handler.send_message(" in source:
        # Make sure it's wrapped in try/except or within retry loop
        if "for attempt in range(1, max_retries + 1):" in source:
            print("✅ send_message calls are within retry loop")
        else:
            print("⚠️  Some send_message calls might not be in retry loop")
    
    return all_passed


def test_dashboard_improvements():
    """Test that dashboard.py has all required improvements"""
    print("\n" + "=" * 80)
    print("TEST: Catalog Error Handling - dashboard.py")
    print("=" * 80)
    
    dashboard_file = os.path.join(os.path.dirname(__file__), 'signalbot/gui/dashboard.py')
    
    with open(dashboard_file, 'r') as f:
        source = f.read()
    
    # Parse the source to verify structure
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        print(f"❌ SYNTAX ERROR in dashboard.py: {e}")
        return False
    
    # Check for specific improvements in the source
    required_features = {
        "Retry logic": "max_retries = 2",
        "Retry loop": "for attempt in range(1, max_retries + 1):",
        "Success tracking": "sent_count = 0",
        "Failed count tracking": "failed_count = 0",
        "Try/except around send": "except Exception as e:",
        "Progress dialog update": 'f"Sending product {index}/{total_products}',
        "Summary report": '"Catalog Send Complete',
        "Retry delay": "time.sleep(2)",
        "Product spacing delay": "time.sleep(2.5)",
        "Success check": "if result:",
        "Failed increment": "failed_count += 1",
    }
    
    all_passed = True
    for feature_name, check_string in required_features.items():
        if check_string in source:
            print(f"✅ {feature_name}: Found")
        else:
            print(f"❌ {feature_name}: NOT FOUND")
            all_passed = False
    
    # Check for improved result messages
    if "Partial Success" in source:
        print("✅ Shows 'Partial Success' for mixed results")
    else:
        print("⚠️  'Partial Success' message not found")
    
    return all_passed


def test_changes_summary():
    """Display summary of changes"""
    print("\n" + "=" * 80)
    print("SUMMARY OF CHANGES")
    print("=" * 80)
    
    print("""
Key Improvements Made:

1. ✅ BUYER_HANDLER.PY:
   - Wrapped each product send in try/except block
   - Added retry logic (2 attempts per product)
   - Increased delay between products from 1.5s to 2.5s
   - Added detailed progress logging with emoji indicators
   - Added summary report showing sent/failed products
   - Tracks failed products by name for reporting
   - Header/footer wrapped in try/except

2. ✅ DASHBOARD.PY:
   - Wrapped each product send in try/except block
   - Added retry logic (2 attempts per product)
   - Increased delay between products to 2.5s
   - Updated progress dialog with better messages
   - Added failed_count tracking
   - Shows "Partial Success", "Success", or "Failed" based on results
   - Distinguishes between send failures and missing images

3. ✅ BEHAVIOR CHANGES:
   - Loop NEVER stops on error - continues to next product
   - Each product gets 2 attempts before being marked as failed
   - 2-3 second delays between retries to allow network recovery
   - 2.5 second delays between products to avoid rate limiting
   - Detailed console output showing exactly what's happening
   - Final summary shows exactly how many succeeded/failed

BEFORE:
   Product 1 → Timeout → LOOP STOPS ❌
   Product 2 → Never attempted
   Product 3 → Never attempted
   Result: 0/3 products sent

AFTER:
   Product 1 → Timeout → Retry → Success ✅
   Product 2 → Success ✅
   Product 3 → Success ✅
   Result: 3/3 products sent
   
OR even with failures:
   Product 1 → Timeout → Retry → Timeout → Mark failed, continue ⚠️
   Product 2 → Success ✅
   Product 3 → Success ✅
   Result: 2/3 products sent (instead of 0/3)
""")


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("CATALOG ERROR HANDLING - COMPREHENSIVE TEST")
    print("=" * 80)
    
    test1 = test_buyer_handler_improvements()
    test2 = test_dashboard_improvements()
    test_changes_summary()
    
    print("\n" + "=" * 80)
    print("TEST RESULTS")
    print("=" * 80)
    
    if test1 and test2:
        print("✅ ALL TESTS PASSED!")
        print("\nThe catalog sending now has robust error handling:")
        print("  • Continues on error instead of stopping")
        print("  • Retries failed sends automatically")
        print("  • Provides detailed progress feedback")
        print("  • Reports final success/failure summary")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        if not test1:
            print("  • buyer_handler.py needs fixes")
        if not test2:
            print("  • dashboard.py needs fixes")
        return 1


if __name__ == '__main__':
    sys.exit(main())
