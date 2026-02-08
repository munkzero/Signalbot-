"""
Currency conversion utilities
Handles XMR to fiat conversion using real-time prices
"""

import requests
from typing import Optional, Dict
from ..config.settings import XMR_PRICE_API, SUPPORTED_CURRENCIES
import time


class CurrencyConverter:
    """Handles currency conversion for XMR"""
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = 300  # 5 minutes
        self.last_update = 0
    
    def get_xmr_price(self, currency: str = "USD") -> float:
        """
        Get current XMR price in specified currency
        
        Args:
            currency: Currency code (USD, EUR, GBP, etc.)
            
        Returns:
            Price of 1 XMR in specified currency
            
        Raises:
            ValueError: If API request fails
        """
        currency = currency.upper()
        
        if currency not in SUPPORTED_CURRENCIES:
            raise ValueError(f"Unsupported currency: {currency}")
        
        # Check cache
        now = time.time()
        cache_key = f"XMR_{currency}"
        
        if cache_key in self.cache and (now - self.last_update) < self.cache_duration:
            return self.cache[cache_key]
        
        # Fetch from API
        try:
            response = requests.get(
                XMR_PRICE_API,
                params={
                    'ids': 'monero',
                    'vs_currencies': currency.lower()
                },
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            price = data['monero'][currency.lower()]
            
            # Update cache
            self.cache[cache_key] = price
            self.last_update = now
            
            return price
        except Exception as e:
            # If cache exists, return cached value even if expired
            if cache_key in self.cache:
                return self.cache[cache_key]
            raise ValueError(f"Failed to fetch XMR price: {e}")
    
    def fiat_to_xmr(self, amount: float, currency: str = "USD") -> float:
        """
        Convert fiat amount to XMR
        
        Args:
            amount: Amount in fiat currency
            currency: Currency code
            
        Returns:
            Amount in XMR
        """
        price = self.get_xmr_price(currency)
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
            'JPY': '¥'
        }
        
        symbol = symbols.get(currency, currency)
        
        if currency == 'JPY':
            return f"{symbol}{amount:.0f}"
        else:
            return f"{symbol}{amount:.2f}"


# Singleton instance
currency_converter = CurrencyConverter()
