"""
Seller model and configuration
"""

from typing import Optional, Dict
import json
from ..database.db import Seller as SellerModel, DatabaseManager
from ..core.security import security_manager


class Seller:
    """Seller entity with configuration"""
    
    def __init__(
        self,
        id: Optional[int] = None,
        signal_id: Optional[str] = None,
        wallet_path: Optional[str] = None,
        default_currency: str = "USD"
    ):
        self.id = id
        self.signal_id = signal_id
        self.wallet_path = wallet_path
        self.default_currency = default_currency
    
    @classmethod
    def from_db_model(cls, db_seller: SellerModel, db_manager: DatabaseManager) -> 'Seller':
        """
        Create Seller from database model
        
        Args:
            db_seller: Database seller model
            db_manager: Database manager for decryption
            
        Returns:
            Seller instance
        """
        signal_id = None
        if db_seller.signal_id and db_seller.signal_id_salt:
            try:
                signal_id = db_manager.decrypt_field(
                    db_seller.signal_id,
                    db_seller.signal_id_salt
                )
            except Exception:
                signal_id = None
        
        return cls(
            id=db_seller.id,
            signal_id=signal_id,
            wallet_path=db_seller.wallet_path,
            default_currency=db_seller.default_currency
        )
    
    def to_db_model(self, db_manager: DatabaseManager, pin: str) -> SellerModel:
        """
        Convert to database model
        
        Args:
            db_manager: Database manager for encryption
            pin: Seller PIN for hashing
            
        Returns:
            Database seller model
        """
        # Hash PIN
        pin_hash, pin_salt = security_manager.hash_pin(pin)
        
        # Encrypt Signal ID
        signal_id_enc = None
        signal_id_salt = None
        if self.signal_id:
            signal_id_enc, signal_id_salt = db_manager.encrypt_field(self.signal_id)
        
        db_seller = SellerModel(
            pin_hash=pin_hash,
            pin_salt=pin_salt,
            signal_id=signal_id_enc,
            signal_id_salt=signal_id_salt,
            wallet_path=self.wallet_path,
            default_currency=self.default_currency
        )
        
        if self.id:
            db_seller.id = self.id
        
        return db_seller


class SellerManager:
    """Manages seller operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_seller(self, seller: Seller, pin: str) -> Seller:
        """
        Create seller account
        
        Args:
            seller: Seller to create
            pin: Seller PIN
            
        Returns:
            Created seller with ID
        """
        db_seller = seller.to_db_model(self.db, pin)
        self.db.session.add(db_seller)
        self.db.session.commit()
        
        seller.id = db_seller.id
        return seller
    
    def get_seller(self, seller_id: int = 1) -> Optional[Seller]:
        """
        Get seller by ID
        
        Args:
            seller_id: Seller ID (default 1 for single seller)
            
        Returns:
            Seller or None
        """
        db_seller = self.db.session.query(SellerModel).filter_by(id=seller_id).first()
        if db_seller:
            return Seller.from_db_model(db_seller, self.db)
        return None
    
    def update_seller(self, seller: Seller, pin: Optional[str] = None) -> Seller:
        """
        Update seller
        
        Args:
            seller: Seller to update
            pin: New PIN (optional)
            
        Returns:
            Updated seller
        """
        db_seller = self.db.session.query(SellerModel).filter_by(id=seller.id).first()
        if not db_seller:
            raise ValueError(f"Seller with ID {seller.id} not found")
        
        # Update PIN if provided
        if pin:
            pin_hash, pin_salt = security_manager.hash_pin(pin)
            db_seller.pin_hash = pin_hash
            db_seller.pin_salt = pin_salt
        
        # Update Signal ID
        if seller.signal_id:
            signal_id_enc, signal_id_salt = self.db.encrypt_field(seller.signal_id)
            db_seller.signal_id = signal_id_enc
            db_seller.signal_id_salt = signal_id_salt
        
        db_seller.wallet_path = seller.wallet_path
        db_seller.default_currency = seller.default_currency
        
        self.db.session.commit()
        return seller
    
    def verify_pin(self, seller_id: int, pin: str) -> bool:
        """
        Verify seller PIN
        
        Args:
            seller_id: Seller ID
            pin: PIN to verify
            
        Returns:
            True if PIN correct
        """
        db_seller = self.db.session.query(SellerModel).filter_by(id=seller_id).first()
        if not db_seller:
            return False
        
        return security_manager.verify_pin(
            pin,
            db_seller.pin_hash,
            db_seller.pin_salt
        )
    
    def seller_exists(self) -> bool:
        """
        Check if seller account exists
        
        Returns:
            True if seller exists
        """
        count = self.db.session.query(SellerModel).count()
        return count > 0
