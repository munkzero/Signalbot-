"""
Database models and encrypted storage for Signal Shop Bot
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from typing import Optional
import json
from ..config.settings import DATABASE_FILE
from ..core.security import security_manager


Base = declarative_base()


class Seller(Base):
    """Seller configuration and credentials"""
    __tablename__ = 'sellers'
    
    id = Column(Integer, primary_key=True)
    pin_hash = Column(String(255), nullable=False)
    pin_salt = Column(String(255), nullable=False)
    signal_id = Column(Text, nullable=True)  # Encrypted
    signal_id_salt = Column(String(255), nullable=True)
    wallet_type = Column(String(20), nullable=True)  # 'rpc' or 'file'
    wallet_config = Column(Text, nullable=True)  # Encrypted JSON
    wallet_config_salt = Column(String(255), nullable=True)
    default_currency = Column(String(10), default='USD')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Product(Base):
    """Product catalog"""
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(String(50), nullable=True, unique=True)  # User-visible ID (NULL allowed for backwards compatibility)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)  # In seller's default currency
    currency = Column(String(10), nullable=False)
    stock = Column(Integer, default=0)
    category = Column(String(100), nullable=True)
    image_path = Column(String(500), nullable=True)  # Encrypted path
    image_path_salt = Column(String(255), nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Order(Base):
    """Order tracking"""
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(String(100), unique=True, nullable=False)
    customer_signal_id = Column(Text, nullable=False)  # Encrypted
    customer_signal_id_salt = Column(String(255), nullable=False)
    product_id = Column(Integer, nullable=False)
    product_name = Column(String(255), nullable=False)
    quantity = Column(Integer, default=1)
    price_fiat = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False)
    price_xmr = Column(Float, nullable=False)
    payment_address = Column(Text, nullable=False)  # Encrypted Monero sub-address
    payment_address_salt = Column(String(255), nullable=False)
    payment_status = Column(String(20), default='pending')  # pending, paid, partial, expired
    order_status = Column(String(20), default='processing')  # processing, shipped, delivered
    amount_paid = Column(Float, default=0.0)
    commission_amount = Column(Float, nullable=False)
    seller_amount = Column(Float, nullable=False)
    shipping_info = Column(Text, nullable=True)  # Encrypted
    shipping_info_salt = Column(String(255), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Contact(Base):
    """Contact information"""
    __tablename__ = 'contacts'
    
    id = Column(Integer, primary_key=True)
    signal_id = Column(Text, nullable=False, unique=True)  # Encrypted
    signal_id_salt = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Message(Base):
    """Message history"""
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True)
    sender_signal_id = Column(Text, nullable=False)  # Encrypted
    sender_signal_id_salt = Column(String(255), nullable=False)
    recipient_signal_id = Column(Text, nullable=False)  # Encrypted
    recipient_signal_id_salt = Column(String(255), nullable=False)
    message_body = Column(Text, nullable=True)
    is_outgoing = Column(Boolean, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class DatabaseManager:
    """Manages database operations with encryption support"""
    
    def __init__(self, master_password: str):
        """
        Initialize database manager
        
        Args:
            master_password: Master password for encryption/decryption
        """
        self.master_password = master_password
        self.engine = create_engine(f'sqlite:///{DATABASE_FILE}')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def encrypt_field(self, value: str, salt: Optional[str] = None) -> tuple[str, str]:
        """
        Encrypt a field value
        
        Args:
            value: Value to encrypt
            salt: Optional salt (generated if not provided)
            
        Returns:
            Tuple of (encrypted_value, salt)
        """
        encrypted, salt = security_manager.encrypt_string(
            value,
            self.master_password,
            None if salt is None else base64.b64decode(salt)
        )
        return encrypted, salt
    
    def decrypt_field(self, encrypted_value: str, salt: str) -> str:
        """
        Decrypt a field value
        
        Args:
            encrypted_value: Encrypted value
            salt: Salt used for encryption
            
        Returns:
            Decrypted value
        """
        return security_manager.decrypt_string(
            encrypted_value,
            self.master_password,
            salt
        )
    
    def close(self):
        """Close database connection"""
        self.session.close()


# Import base64 for decrypt_field
import base64
