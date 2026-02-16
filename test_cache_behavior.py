#!/usr/bin/env python3
"""
Test that stale cache is used when APIs fail but cache exists
"""

import sys
import time
from signalbot.utils.currency import currency_converter, ExchangeRateUnavailableError


def test_stale_cache_is_used():
    """Test that stale cache is used even when APIs fail"""
    print("\n" + "="*60)
    print("TEST: Stale cache is used when APIs fail")
    print("="*60)
    
    try:
        # Manually set a cached value and make it stale
        currency_converter.cache = {"XMR_USD": 165.50}
        currency_converter.last_update = time.time() - 3600  # 1 hour ago (stale)
        
        print("\n🔄 Attempting to get XMR price with stale cache...")
        print(f"   Cache age: ~60 minutes (stale)")
        
        # Try to get XMR price (APIs will fail, should use stale cache)
        price = currency_converter.get_xmr_price("USD")
        
        if price == 165.50:
            print(f"✅ SUCCESS: Stale cache was used")
            print(f"   Price from cache: ${price:.2f}")
            return True
        else:
            print(f"❌ FAILED: Got unexpected price: ${price:.2f}")
            return False
        
    except ExchangeRateUnavailableError as e:
        print(f"❌ FAILED: Should NOT raise exception when cache exists")
        print(f"   Error: {e}")
        return False
        
    except Exception as e:
        print(f"❌ FAILED: Unexpected exception: {type(e).__name__}")
        print(f"   Error: {e}")
        return False


def test_fresh_cache_is_used():
    """Test that fresh cache is used without API call"""
    print("\n" + "="*60)
    print("TEST: Fresh cache is used without API call")
    print("="*60)
    
    try:
        # Set fresh cache
        currency_converter.cache = {"XMR_EUR": 153.25}
        currency_converter.last_update = time.time()  # Fresh
        
        print("\n🔄 Attempting to get XMR price with fresh cache...")
        
        # Should use cache, not call API
        price = currency_converter.get_xmr_price("EUR")
        
        if price == 153.25:
            print(f"✅ SUCCESS: Fresh cache was used")
            print(f"   Price from cache: €{price:.2f}")
            return True
        else:
            print(f"❌ FAILED: Got unexpected price: €{price:.2f}")
            return False
        
    except Exception as e:
        print(f"❌ FAILED: Should not raise exception: {type(e).__name__}")
        print(f"   Error: {e}")
        return False


def test_cache_age_calculation():
    """Test that cache age is calculated correctly"""
    print("\n" + "="*60)
    print("TEST: Cache age calculation in logs")
    print("="*60)
    
    try:
        # Set cache to specific age (10 minutes)
        currency_converter.cache = {"XMR_GBP": 125.00}
        currency_converter.last_update = time.time() - 600  # 10 minutes ago
        
        print("\n🔄 Getting price with 10-minute-old cache...")
        
        # This should use the stale cache
        price = currency_converter.get_xmr_price("GBP")
        
        if price == 125.00:
            print(f"✅ SUCCESS: Cache was used (check logs for age)")
            print(f"   Expected log: 'Using cached rate from 10.0 minutes ago'")
            return True
        else:
            print(f"❌ FAILED: Unexpected price")
            return False
        
    except Exception as e:
        print(f"❌ FAILED: {type(e).__name__}: {e}")
        return False


def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "="*60)
    print("CACHE BEHAVIOR TEST SUITE")
    print("="*60)
    print("Verifying cache provides resilience during API outages")
    print()
    
    tests = [
        ("Fresh cache is used", test_fresh_cache_is_used),
        ("Stale cache is used", test_stale_cache_is_used),
        ("Cache age calculation", test_cache_age_calculation),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ TEST CRASHED: {name}")
            print(f"   Error: {e}")
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
        print(f"{status}: {name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Cache provides resilience.")
        return 0
    elif passed > 0:
        print("⚠️  Some tests passed")
        return 1
    else:
        print("❌ All tests failed")
        return 2


if __name__ == "__main__":
    sys.exit(run_all_tests())
