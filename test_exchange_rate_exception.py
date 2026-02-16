#!/usr/bin/env python3
"""
Test that ExchangeRateUnavailableError is raised when APIs are down and no cache exists
"""

import sys
from signalbot.utils.currency import currency_converter, ExchangeRateUnavailableError


def test_exception_when_no_cache_and_apis_down():
    """Test that exception is raised when APIs fail and cache is empty"""
    print("\n" + "="*60)
    print("TEST: ExchangeRateUnavailableError when APIs down + no cache")
    print("="*60)
    
    try:
        # Clear cache to simulate no cached rate
        currency_converter.cache = {}
        currency_converter.last_update = 0
        
        # Try to get XMR price (APIs will fail in isolated environment)
        print("\n🔄 Attempting to get XMR price with no cache...")
        price = currency_converter.get_xmr_price("USD")
        
        # If we get here, the test failed
        print(f"❌ FAILED: Should have raised ExchangeRateUnavailableError")
        print(f"   Instead got price: ${price}")
        return False
        
    except ExchangeRateUnavailableError as e:
        print(f"✅ SUCCESS: ExchangeRateUnavailableError was raised as expected")
        print(f"   Error message: {e}")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Wrong exception type: {type(e).__name__}")
        print(f"   Error: {e}")
        return False


def test_exception_in_fiat_to_xmr():
    """Test that exception propagates through fiat_to_xmr"""
    print("\n" + "="*60)
    print("TEST: ExchangeRateUnavailableError in fiat_to_xmr")
    print("="*60)
    
    try:
        # Clear cache
        currency_converter.cache = {}
        currency_converter.last_update = 0
        
        print("\n🔄 Attempting to convert fiat to XMR with no cache...")
        xmr = currency_converter.fiat_to_xmr(100.0, "USD")
        
        print(f"❌ FAILED: Should have raised ExchangeRateUnavailableError")
        print(f"   Instead got XMR amount: {xmr}")
        return False
        
    except ExchangeRateUnavailableError as e:
        print(f"✅ SUCCESS: ExchangeRateUnavailableError was raised in fiat_to_xmr")
        print(f"   Error message: {e}")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Wrong exception type: {type(e).__name__}")
        print(f"   Error: {e}")
        return False


def test_no_fallback_rate_attribute():
    """Verify that fallback_rate attribute does not exist"""
    print("\n" + "="*60)
    print("TEST: Verify fallback_rate attribute was removed")
    print("="*60)
    
    if hasattr(currency_converter, 'fallback_rate'):
        print(f"❌ FAILED: fallback_rate attribute still exists")
        print(f"   Value: {currency_converter.fallback_rate}")
        return False
    else:
        print(f"✅ SUCCESS: fallback_rate attribute has been removed")
        return True


def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "="*60)
    print("EXCHANGE RATE EXCEPTION TEST SUITE")
    print("="*60)
    print("Verifying 'No API = No Sales' requirement")
    print()
    
    tests = [
        ("Exception when no cache", test_exception_when_no_cache_and_apis_down),
        ("Exception in fiat_to_xmr", test_exception_in_fiat_to_xmr),
        ("No fallback_rate attribute", test_no_fallback_rate_attribute),
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
        print("🎉 All tests passed! 'No API = No Sales' is enforced.")
        return 0
    elif passed > 0:
        print("⚠️  Some tests passed")
        return 1
    else:
        print("❌ All tests failed")
        return 2


if __name__ == "__main__":
    sys.exit(run_all_tests())
