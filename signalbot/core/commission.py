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
# This is encrypted and will be decrypted at runtime only
# Tampering with this will cause the bot to fail integrity checks
ENCRYPTED_COMMISSION_WALLET = ""  # To be set during compilation
COMMISSION_WALLET_SALT = ""  # To be set during compilation
COMMISSION_CHECKSUM = ""  # To be set during compilation

# Commission rate (4% = 0.04)
COMMISSION_RATE = 0.04


class CommissionManager:
    """Manages commission calculations and forwarding"""
    
    def __init__(self, master_key: bytes):
        """
        Initialize commission manager
        
        Args:
            master_key: Master encryption key for decrypting commission wallet
        """
        self._master_key = master_key
        self._commission_wallet = None
        self._decrypted = False
    
    def _decrypt_commission_wallet(self) -> str:
        """
        Decrypt commission wallet address
        Only called when needed, immediately cleared from memory after use
        
        Returns:
            Decrypted commission wallet address
            
        Raises:
            ValueError: If decryption fails or checksum invalid
        """
        if not ENCRYPTED_COMMISSION_WALLET or not COMMISSION_WALLET_SALT:
            raise ValueError("Commission wallet not configured")
        
        try:
            # Decrypt wallet address
            wallet = security_manager.decrypt_string(
                ENCRYPTED_COMMISSION_WALLET,
                self._master_key.decode(),
                COMMISSION_WALLET_SALT
            )
            
            # Verify integrity
            checksum = security_manager.generate_checksum(wallet.encode())
            if COMMISSION_CHECKSUM and checksum != COMMISSION_CHECKSUM:
                raise ValueError("Commission wallet integrity check failed - tampering detected")
            
            return wallet
        except Exception as e:
            raise ValueError(f"Failed to decrypt commission wallet: {e}")
    
    def get_commission_wallet(self) -> str:
        """
        Get commission wallet address
        Decrypts on first access, then caches for session
        
        Returns:
            Commission wallet address
        """
        if not self._decrypted:
            self._commission_wallet = self._decrypt_commission_wallet()
            self._decrypted = True
        
        return self._commission_wallet
    
    def calculate_commission(self, total_amount: float) -> tuple[float, float]:
        """
        Calculate commission and seller amount
        
        Args:
            total_amount: Total payment amount in XMR
            
        Returns:
            Tuple of (seller_amount, commission_amount)
        """
        commission = total_amount * COMMISSION_RATE
        seller_amount = total_amount - commission
        
        return (seller_amount, commission)
    
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
    
    def verify_integrity(self) -> bool:
        """
        Verify commission system integrity
        Checks for tampering attempts
        
        Returns:
            True if integrity verified, False if tampering detected
        """
        try:
            # Try to decrypt wallet address
            wallet = self._decrypt_commission_wallet()
            
            # Verify checksum
            checksum = security_manager.generate_checksum(wallet.encode())
            if COMMISSION_CHECKSUM and checksum != COMMISSION_CHECKSUM:
                return False
            
            # Verify commission rate hasn't been modified
            if COMMISSION_RATE != 0.04:
                return False
            
            return True
        except:
            return False
    
    def clear_from_memory(self):
        """
        Clear decrypted commission wallet from memory
        Called after use for security
        """
        if self._commission_wallet:
            # Overwrite with random data before clearing
            self._commission_wallet = os.urandom(len(self._commission_wallet)).hex()
            self._commission_wallet = None
            self._decrypted = False


def setup_commission_wallet(wallet_address: str, master_password: str) -> dict:
    """
    Utility function to encrypt commission wallet for compilation
    This should be run once before compilation to generate encrypted values
    
    Args:
        wallet_address: Monero wallet address for commission
        master_password: Master password for encryption
        
    Returns:
        Dictionary with encrypted values to be hardcoded
    """
    # Encrypt wallet address
    encrypted, salt = security_manager.encrypt_string(wallet_address, master_password)
    
    # Generate checksum
    checksum = security_manager.generate_checksum(wallet_address.encode())
    
    return {
        'ENCRYPTED_COMMISSION_WALLET': encrypted,
        'COMMISSION_WALLET_SALT': salt,
        'COMMISSION_CHECKSUM': checksum
    }
