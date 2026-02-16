"""
Currency conversion utilities with secure API integration
"""

import requests
from typing import Optional, Dict
from ..config.settings import XMR_PRICE_API, SUPPORTED_CURRENCIES
import time
import logging

# Fallback API (if primary fails)
FALLBACK_API = "https://api.kraken.com/0/public/Ticker?pair=XMRUSD"

logger = logging.getLogger(__name__)


class ExchangeRateUnavailableError(Exception):
    """Raised when exchange rate cannot be obtained from any source"""
    pass


class CurrencyConverter:
    """Secure currency conversion with fallback protection"""
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = 300  # 5 minutes
        self.last_update = 0
        self.request_timeout = 10  # 10 second timeout
        self.max_retries = 3
    
    def get_xmr_price(self, currency: str = "USD") -> float:
        """
        Get current XMR price with fallback chain
        
        Args:
            currency: Currency code (USD, EUR, GBP, etc.)
            
        Returns:
            Price of 1 XMR in specified currency
            
        Raises:
            ExchangeRateUnavailableError: If rate unavailable from all sources
        """
        currency = currency.upper()
        
        if currency not in SUPPORTED_CURRENCIES:
            logger.warning(f"Unsupported currency {currency}, defaulting to USD")
            currency = "USD"
        
        # Check cache first (within 5 minutes)
        now = time.time()
        cache_key = f"XMR_{currency}"
        
        if cache_key in self.cache and (now - self.last_update) < self.cache_duration:
            logger.debug(f"Using fresh cached rate for {currency}: {self.cache[cache_key]}")
            return self.cache[cache_key]
        
        # Try to fetch from API with retries
        for attempt in range(self.max_retries):
            try:
                price = self._fetch_from_api(currency)
                
                # Update cache
                self.cache[cache_key] = price
                self.last_update = now
                
                logger.info(f"Exchange rate updated: 1 XMR = {price} {currency}")
                return price
                
            except Exception as e:
                logger.warning(f"API attempt {attempt + 1}/{self.max_retries} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(1)  # Wait 1 second before retry
                    continue
        
        # All API attempts failed - use stale cache if available
        if cache_key in self.cache:
            cache_age = (now - self.last_update) / 60  # Age in minutes
            logger.warning(f"All APIs failed. Using cached rate from {cache_age:.1f} minutes ago")
            return self.cache[cache_key]
        
        # No cache available - raise exception
        logger.error(f"Exchange rate unavailable for {currency}: All APIs down and no cached rate")
        raise ExchangeRateUnavailableError(
            f"Exchange rate for {currency} unavailable. All APIs are down and no cached rate exists."
        )
    
    def _fetch_from_api(self, currency: str) -> float:
        """
        Fetch price from API with security measures
        
        Args:
            currency: Currency code
            
        Returns:
            Price in specified currency
        """
        # Primary API: CoinGecko (HTTPS, no auth required)
        try:
            response = requests.get(
                XMR_PRICE_API,
                params={
                    'ids': 'monero',
                    'vs_currencies': currency.lower()
                },
                timeout=self.request_timeout,
                headers={
                    'User-Agent': 'SignalBot/1.0',  # Identify ourselves
                }
            )
            
            # Validate response
            response.raise_for_status()
            
            data = response.json()
            
            # Validate data structure
            if 'monero' not in data or currency.lower() not in data['monero']:
                raise ValueError(f"Invalid API response structure")
            
            price = data['monero'][currency.lower()]
            
            # Sanity check: XMR price should be between $10 and $10,000
            if not (10 <= price <= 10000):
                raise ValueError(f"Suspicious price: {price} (out of expected range)")
            
            return price
            
        except Exception as e:
            logger.debug(f"Primary API failed: {e}, trying fallback")
            
            # Fallback API: Kraken (only supports USD)
            if currency == "USD":
                try:
                    response = requests.get(
                        FALLBACK_API,
                        timeout=self.request_timeout
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    
                    # Kraken returns price in their format
                    price_data = data['result']['XXMRZUSD']
                    price = float(price_data['c'][0])  # Last trade price
                    
                    # Sanity check
                    if not (10 <= price <= 10000):
                        raise ValueError(f"Suspicious price from fallback: {price}")
                    
                    return price
                    
                except Exception as fallback_error:
                    logger.error(f"Fallback API also failed: {fallback_error}")
            
            # Re-raise original exception if fallback not available or failed
            raise e
    
    def fiat_to_xmr(self, amount: float, currency: str = "USD") -> float:
        """
        Convert fiat amount to XMR
        
        Args:
            amount: Amount in fiat currency
            currency: Currency code
            
        Returns:
            Amount in XMR
            
        Raises:
            ValueError: If amount is negative
            ExchangeRateUnavailableError: If exchange rate unavailable
        """
        if amount < 0:
            raise ValueError("Amount cannot be negative")
        
        price = self.get_xmr_price(currency)  # May raise ExchangeRateUnavailableError
        return amount / price
    
    def xmr_to_fiat(self, amount: float, currency: str = "USD") -> float:
        """
        Convert XMR amount to fiat
        
        Args:
            amount: Amount in XMR
            currency: Currency code
            
        Returns:
            Amount in fiat currency
        """
        if amount < 0:
            raise ValueError("Amount cannot be negative")
        
        price = self.get_xmr_price(currency)
        return amount * price
    
    def format_xmr(self, amount: float) -> str:
        """
        Format XMR amount for display
        
        Args:
            amount: XMR amount
            
        Returns:
            Formatted string
        """
        return f"{amount:.12f} XMR"
    
    def format_fiat(self, amount: float, currency: str = "USD") -> str:
        """
        Format fiat amount for display
        
        Args:
            amount: Fiat amount
            currency: Currency code
            
        Returns:
            Formatted string
        """
        symbols = {
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
            'CAD': 'C$',
            'AUD': 'A$',
            'NZD': 'NZ$',
            'JPY': '¥'
        }
        
        symbol = symbols.get(currency, currency)
        
        if currency == 'JPY':
            return f"{symbol}{amount:.0f}"
        else:
            return f"{symbol}{amount:.2f}"


# Singleton instance
currency_converter = CurrencyConverter()
