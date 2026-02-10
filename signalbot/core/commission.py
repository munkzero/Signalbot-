"""
Commission System for Signal Shop Bot
Handles automatic 4% commission forwarding to bot creator

CRITICAL: This module is protected by anti-tamper mechanisms.
DO NOT modify commission rate or wallet address.
"""

import os
import base64
from typing import Optional
from .security import security_manager


# ENCRYPTED COMMISSION WALLET ADDRESS
# Multi-layer encoding for developer wallet (base64)
# Developer wallet: 45WQHqFEXuCep9YkqJ6ZB7WCnnJiemkAn8UvSpAe71HrWqE6b5y7jxqhG8RYJJHpUoPuK4D2jwZLyDftJVqnc1hT5aHw559
_ENCRYPTED_WALLET = "NDVXUUhxRkVYdUNlcDlZa3FKNlpCN1dDbm5KaWVta0FuOFV2U3BBZTcxSHJXcUU2YjV5N2p4cWhHOFJZSkpIcFVvUHVLNEQyandaTHlEZnRKVnFuYzFoVDVhSHc1NTk="

# Commission rate (4% = 0.04)
COMMISSION_RATE = 0.04


def get_commission_wallet() -> str:
    """
    Decrypt and return developer commission wallet
    
    Returns:
        Commission wallet address
    """
    try:
        return base64.b64decode(_ENCRYPTED_WALLET).decode('utf-8')
    except Exception:
        # Fallback to hardcoded wallet
        return "45WQHqFEXuCep9YkqJ6ZB7WCnnJiemkAn8UvSpAe71HrWqE6b5y7jxqhG8RYJJHpUoPuK4D2jwZLyDftJVqnc1hT5aHw559"


def calculate_commission(total_amount: float) -> tuple:
    """
    Calculate commission and net amount
    
    Args:
        total_amount: Total payment amount in XMR
        
    Returns:
        Tuple of (seller_amount, commission_amount)
    """
    commission = total_amount * COMMISSION_RATE
    seller_amount = total_amount - commission
    return (seller_amount, commission)


class CommissionManager:
    """Manages commission calculations and forwarding"""
    
    def __init__(self):
        """Initialize commission manager"""
        pass
    
    def get_commission_wallet(self) -> str:
        """
        Get commission wallet address
        
        Returns:
            Commission wallet address
        """
        return get_commission_wallet()
    
    def calculate_commission(self, total_amount: float) -> tuple:
        """
        Calculate commission and seller amount
        
        Args:
            total_amount: Total payment amount in XMR
            
        Returns:
            Tuple of (seller_amount, commission_amount)
        """
        return calculate_commission(total_amount)
    
    def format_commission_disclosure(self, total_amount: float) -> str:
        """
        Format commission disclosure message for sellers
        
        Args:
            total_amount: Total payment amount
            
        Returns:
            Formatted disclosure message
        """
        seller_amount, commission = self.calculate_commission(total_amount)
        
        return (
            f"Transaction: {total_amount:.6f} XMR\n"
            f"Your earnings: {seller_amount:.6f} XMR\n"
            f"Commission (4%): {commission:.6f} XMR"
        )
    
    def process_order_commission(self, order, monero_wallet):
        """
        When order is paid, calculate and log commission
        
        Args:
            order: Paid order object
            monero_wallet: MoneroWallet instance (for future auto-forwarding)
        
        Returns:
            Tuple of (seller_amount, commission_amount)
        """
        # Get total XMR amount from order
        total_xmr = order.price_xmr * order.quantity
        seller_amount, commission = self.calculate_commission(total_xmr)
        dev_wallet = self.get_commission_wallet()
        
        # Log commission (transparent)
        print(f"Order #{order.order_id}: Total {total_xmr:.6f} XMR")
        print(f"  → Seller receives: {seller_amount:.6f} XMR")
        print(f"  → Platform fee (4%): {commission:.6f} XMR")
        print(f"  → Commission wallet: {dev_wallet[:20]}...{dev_wallet[-10:]}")
        
        # Note: Actual transfer would happen here in production
        # For now, we just calculate and log
        # monero_wallet.transfer(address=dev_wallet, amount=commission, priority=1)
        
        return (seller_amount, commission)
