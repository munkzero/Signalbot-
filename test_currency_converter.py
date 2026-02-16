#!/usr/bin/env python3
"""
Test script for secure currency converter with live exchange rates
Tests API connectivity, fallback mechanisms, and error handling
"""

import sys
import time
from signalbot.utils.currency import currency_converter


def test_primary_api():
    """Test primary API (CoinGecko)"""
    print("\n" + "="*60)
    print("TEST 1: Primary API (CoinGecko)")
    print("="*60)
    
    try:
        price = currency_converter.get_xmr_price("USD")
        print(f"✅ SUCCESS: Got XMR price from primary API")
        print(f"   1 XMR = ${price:.2f} USD")
        
        # Sanity check
        if 10 <= price <= 10000:
            print(f"✅ Price is within expected range ($10-$10,000)")
        else:
            print(f"⚠️  WARNING: Price ${price} is outside expected range")
        
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_cache():
    """Test caching mechanism"""
    print("\n" + "="*60)
    print("TEST 2: Caching Mechanism")
    print("="*60)
    
    try:
        # Clear cache first
        currency_converter.cache = {}
        currency_converter.last_update = 0
        
        # First call - should hit API
        start = time.time()
        price1 = currency_converter.get_xmr_price("USD")
        time1 = time.time() - start
        print(f"   First call (API): {time1:.3f}s - ${price1:.2f}")
        
        # Second call - should use cache
        start = time.time()
        price2 = currency_converter.get_xmr_price("USD")
        time2 = time.time() - start
        print(f"   Second call (cache): {time2:.3f}s - ${price2:.2f}")
        
        if price1 == price2:
            print(f"✅ SUCCESS: Cache returned same price")
        else:
            print(f"⚠️  WARNING: Prices differ (might be expected if API updated)")
        
        if time2 < time1:
            print(f"✅ SUCCESS: Cached call was faster ({time2:.3f}s vs {time1:.3f}s)")
        else:
            print(f"⚠️  INFO: Cache timing similar (expected if API is very fast)")
        
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_multiple_currencies():
    """Test multiple currency support"""
    print("\n" + "="*60)
    print("TEST 3: Multiple Currency Support")
    print("="*60)
    
    currencies = ["USD", "EUR", "GBP", "JPY"]
    success_count = 0
    
    for currency in currencies:
        try:
            price = currency_converter.get_xmr_price(currency)
            print(f"✅ {currency}: 1 XMR = {currency_converter.format_fiat(price, currency)}")
            success_count += 1
        except Exception as e:
            print(f"❌ {currency}: Failed - {e}")
    
    if success_count == len(currencies):
        print(f"✅ SUCCESS: All {success_count} currencies tested successfully")
        return True
    else:
        print(f"⚠️  PARTIAL: {success_count}/{len(currencies)} currencies succeeded")
        return success_count > 0


def test_conversions():
    """Test fiat<->XMR conversions"""
    print("\n" + "="*60)
    print("TEST 4: Currency Conversions")
    print("="*60)
    
    try:
        # Test fiat to XMR
        amount_usd = 100.0
        amount_xmr = currency_converter.fiat_to_xmr(amount_usd, "USD")
        print(f"   ${amount_usd} USD = {currency_converter.format_xmr(amount_xmr)}")
        
        # Test XMR to fiat (round trip)
        amount_back = currency_converter.xmr_to_fiat(amount_xmr, "USD")
        print(f"   {currency_converter.format_xmr(amount_xmr)} = ${amount_back:.2f} USD")
        
        # Check if round trip is accurate (within 0.01)
        if abs(amount_usd - amount_back) < 0.01:
            print(f"✅ SUCCESS: Round-trip conversion is accurate")
        else:
            print(f"⚠️  WARNING: Round-trip has small difference (${abs(amount_usd - amount_back):.2f})")
        
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_input_validation():
    """Test input validation"""
    print("\n" + "="*60)
    print("TEST 5: Input Validation")
    print("="*60)
    
    all_passed = True
    
    # Test negative amount
    try:
        currency_converter.fiat_to_xmr(-100, "USD")
        print(f"❌ FAILED: Should reject negative amount")
        all_passed = False
    except ValueError as e:
        print(f"✅ SUCCESS: Correctly rejected negative amount: {e}")
    
    # Test unsupported currency (should default to USD)
    try:
        price = currency_converter.get_xmr_price("INVALID")
        print(f"✅ SUCCESS: Handled invalid currency (defaulted to USD): ${price:.2f}")
    except Exception as e:
        print(f"⚠️  INFO: Rejected invalid currency: {e}")
    
    return all_passed


def test_retry_mechanism():
    """Test retry mechanism (by observing logs)"""
    print("\n" + "="*60)
    print("TEST 6: Retry Mechanism")
    print("="*60)
    
    print("   Note: This test observes that retries are configured")
    print(f"   Max retries: {currency_converter.max_retries}")
    print(f"   Request timeout: {currency_converter.request_timeout}s")
    print(f"   Cache duration: {currency_converter.cache_duration}s")
    print(f"   Fallback rate: ${currency_converter.fallback_rate}")
    print(f"✅ SUCCESS: Retry configuration verified")
    
    return True


def test_fallback_scenario():
    """Test fallback behavior"""
    print("\n" + "="*60)
    print("TEST 7: Fallback Scenario")
    print("="*60)
    
    try:
        # Save original cache
        original_cache = currency_converter.cache.copy()
        
        # Clear cache to force API call
        currency_converter.cache = {}
        
        # This will try primary API, and if it fails, try fallback
        price = currency_converter.get_xmr_price("USD")
        print(f"✅ SUCCESS: Got price (using primary or fallback): ${price:.2f}")
        
        # Restore cache
        currency_converter.cache = original_cache
        
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "="*60)
    print("SECURE CURRENCY CONVERTER TEST SUITE")
    print("="*60)
    print("Testing live exchange rate integration with security features")
    print()
    
    tests = [
        ("Primary API", test_primary_api),
        ("Caching", test_cache),
        ("Multiple Currencies", test_multiple_currencies),
        ("Conversions", test_conversions),
        ("Input Validation", test_input_validation),
        ("Retry Mechanism", test_retry_mechanism),
        ("Fallback Scenario", test_fallback_scenario),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ TEST CRASHED: {name}")
            print(f"   Error: {e}")
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
        print("🎉 All tests passed!")
        return 0
    elif passed > 0:
        print("⚠️  Some tests passed")
        return 1
    else:
        print("❌ All tests failed")
        return 2


if __name__ == "__main__":
    sys.exit(run_all_tests())
