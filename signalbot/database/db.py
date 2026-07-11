"""
Database models and encrypted storage for Signal Shop Bot
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from typing import Optional
import json
import base64
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
    wallet_path = Column(String(500), nullable=True)  # Path to in-house wallet file
    default_currency = Column(String(10), default='USD')
    message_retention_days = Column(Integer, default=30)
    order_archive_days = Column(Integer, default=90)
    archive_retention_days = Column(Integer, default=365)
    last_cleanup_at = Column(DateTime, nullable=True)
    cleanup_status = Column(Text, nullable=True)
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
    address_index = Column(Integer, nullable=True)  # Subaddress index for payment monitoring
    payment_status = Column(String(20), default='pending')  # pending, paid, partial, expired, unconfirmed
    order_status = Column(String(20), default='processing')  # processing, shipped, delivered
    amount_paid = Column(Float, default=0.0)
    payment_txid = Column(Text, nullable=True)  # Transaction hash
    commission_amount = Column(Float, nullable=False)
    seller_amount = Column(Float, nullable=False)
    commission_paid = Column(Boolean, default=False)  # Whether commission has been paid
    commission_txid = Column(Text, nullable=True)  # Commission payment transaction hash
    commission_paid_at = Column(DateTime, nullable=True)  # When commission was paid
    shipping_info = Column(Text, nullable=True)  # Encrypted
    shipping_info_salt = Column(String(255), nullable=True)
    tracking_number = Column(Text, nullable=True)  # Shipping tracking number
    shipped_at = Column(DateTime, nullable=True)  # When order was shipped
    expires_at = Column(DateTime, nullable=False)
    paid_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, nullable=True)
    purge_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PaymentHistory(Base):
    """Payment event tracking"""
    __tablename__ = 'payment_history'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, nullable=False)
    event_type = Column(String(50), nullable=False)  # created, payment_detected, confirmed
    amount = Column(Float, nullable=True)
    txid = Column(Text, nullable=True)
    confirmations = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow)


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
    expires_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class MessageArchive(Base):
    """Archived message history for retention cleanup"""
    __tablename__ = 'message_archives'

    id = Column(Integer, primary_key=True)
    original_message_id = Column(Integer, nullable=True)
    sender_signal_id = Column(Text, nullable=False)
    sender_signal_id_salt = Column(String(255), nullable=False)
    recipient_signal_id = Column(Text, nullable=False)
    recipient_signal_id_salt = Column(String(255), nullable=False)
    message_body = Column(Text, nullable=True)
    is_outgoing = Column(Boolean, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, default=datetime.utcnow)
    purge_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class MoneroNode(Base):
    """Monero node configurations"""
    __tablename__ = 'monero_nodes'
    
    id = Column(Integer, primary_key=True)
    address = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    use_ssl = Column(Boolean, default=False)
    username = Column(Text, nullable=True)  # Encrypted
    username_salt = Column(String(255), nullable=True)
    password = Column(Text, nullable=True)  # Encrypted
    password_salt = Column(String(255), nullable=True)
    node_name = Column(String(255), nullable=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OrderArchive(Base):
    """Archived orders and addresses retained for privacy-safe recovery"""
    __tablename__ = 'order_archives'

    id = Column(Integer, primary_key=True)
    original_order_db_id = Column(Integer, nullable=True)
    order_id = Column(String(100), nullable=False)
    customer_signal_id = Column(Text, nullable=False)
    customer_signal_id_salt = Column(String(255), nullable=False)
    product_id = Column(Integer, nullable=False)
    product_name = Column(String(255), nullable=False)
    quantity = Column(Integer, default=1)
    price_fiat = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False)
    price_xmr = Column(Float, nullable=False)
    payment_address = Column(Text, nullable=False)
    payment_address_salt = Column(String(255), nullable=False)
    address_index = Column(Integer, nullable=True)
    payment_status = Column(String(20), default='pending')
    order_status = Column(String(20), default='processing')
    amount_paid = Column(Float, default=0.0)
    payment_txid = Column(Text, nullable=True)
    commission_amount = Column(Float, nullable=False)
    seller_amount = Column(Float, nullable=False)
    commission_paid = Column(Boolean, default=False)
    commission_txid = Column(Text, nullable=True)
    commission_paid_at = Column(DateTime, nullable=True)
    shipping_info = Column(Text, nullable=True)
    shipping_info_salt = Column(String(255), nullable=True)
    tracking_number = Column(Text, nullable=True)
    shipped_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, default=datetime.utcnow)
    purge_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=True)


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
        
        # Log database file location
        print(f"📁 Database file: {DATABASE_FILE}")
        
        # Create all tables from Base metadata
        print(f"🔨 Creating database tables...")
        print(f"   Tables to create: {list(Base.metadata.tables.keys())}")
        Base.metadata.create_all(self.engine)
        print(f"✓ Database tables created successfully")
        
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        # Verify tables were created
        try:
            from sqlalchemy import inspect
            inspector = inspect(self.engine)
            actual_tables = inspector.get_table_names()
            print(f"✓ Verified tables in database: {actual_tables}")
            
            # Check if all expected tables exist
            expected_tables = set(Base.metadata.tables.keys())
            actual_tables_set = set(actual_tables)
            missing_tables = expected_tables - actual_tables_set
            
            if missing_tables:
                print(f"⚠️  WARNING: Some tables are missing: {missing_tables}")
            else:
                print(f"✓ All {len(expected_tables)} tables verified")
        except Exception as e:
            print(f"⚠️  Could not verify tables: {e}")
        
        # Create performance indexes
        self._create_indexes()
        
        # Run database migrations for new columns
        self._run_migrations()
    
    def _create_indexes(self):
        """Create database indexes for performance optimization"""
        try:
            with self.engine.connect() as conn:
                # Index for active products lookup
                conn.execute(text('''
                    CREATE INDEX IF NOT EXISTS idx_products_active 
                    ON products(active) 
                    WHERE active = 1
                '''))
                
                # Index for product ID lookups
                conn.execute(text('''
                    CREATE INDEX IF NOT EXISTS idx_products_product_id 
                    ON products(product_id)
                '''))
                
                # Index for order status queries
                conn.execute(text('''
                    CREATE INDEX IF NOT EXISTS idx_orders_status 
                    ON orders(payment_status)
                '''))
                
                # Index for payment address lookups (critical for payment detection)
                conn.execute(text('''
                    CREATE INDEX IF NOT EXISTS idx_orders_payment_address 
                    ON orders(payment_address)
                '''))
                
                # Index for pending orders (status + created_at)
                conn.execute(text('''
                    CREATE INDEX IF NOT EXISTS idx_orders_pending 
                    ON orders(payment_status, created_at)
                    WHERE payment_status = 'pending'
                '''))
                
                # Index for order status
                conn.execute(text('''
                    CREATE INDEX IF NOT EXISTS idx_orders_order_status 
                    ON orders(order_status)
                '''))

                conn.execute(text('''
                    CREATE INDEX IF NOT EXISTS idx_messages_sent_at
                    ON messages(sent_at)
                '''))

                conn.execute(text('''
                    CREATE INDEX IF NOT EXISTS idx_messages_expires_at
                    ON messages(expires_at)
                '''))

                conn.execute(text('''
                    CREATE INDEX IF NOT EXISTS idx_orders_archived_at
                    ON orders(archived_at)
                '''))

                conn.execute(text('''
                    CREATE INDEX IF NOT EXISTS idx_order_archives_purge_at
                    ON order_archives(purge_at)
                '''))

                conn.execute(text('''
                    CREATE INDEX IF NOT EXISTS idx_message_archives_purge_at
                    ON message_archives(purge_at)
                '''))
                
                conn.commit()
                print("✓ Database indexes created")
                
        except Exception as e:
            print(f"⚠️  Error creating indexes: {e}")
    
    def _run_migrations(self):
        """Run database migrations for schema updates"""
        print("Checking for database migrations...")
        migrations_applied = []
        
        try:
            with self.engine.connect() as conn:
                # Begin explicit transaction
                trans = conn.begin()
                try:
                    # Check if address_index column exists
                    result = conn.execute(text(
                        "SELECT COUNT(*) FROM pragma_table_info('orders') WHERE name='address_index'"
                    ))
                    if result.scalar() == 0:
                        print("🔄 Adding address_index column to orders table...")
                        conn.execute(text('ALTER TABLE orders ADD COLUMN address_index INTEGER'))
                        migrations_applied.append("address_index")
                        print("✓ Added address_index column")
                    
                    # Check if payment_txid column exists
                    result = conn.execute(text(
                        "SELECT COUNT(*) FROM pragma_table_info('orders') WHERE name='payment_txid'"
                    ))
                    if result.scalar() == 0:
                        print("🔄 Adding payment_txid column to orders table...")
                        conn.execute(text('ALTER TABLE orders ADD COLUMN payment_txid TEXT'))
                        migrations_applied.append("payment_txid")
                        print("✓ Added payment_txid column")
                    
                    # Check if commission_amount column exists
                    result = conn.execute(text(
                        "SELECT COUNT(*) FROM pragma_table_info('orders') WHERE name='commission_amount'"
                    ))
                    if result.scalar() == 0:
                        print("🔄 Adding commission_amount column to orders table...")
                        conn.execute(text('ALTER TABLE orders ADD COLUMN commission_amount REAL'))
                        migrations_applied.append("commission_amount")
                        print("✓ Added commission_amount column")
                    
                    # Check if seller_amount column exists
                    result = conn.execute(text(
                        "SELECT COUNT(*) FROM pragma_table_info('orders') WHERE name='seller_amount'"
                    ))
                    if result.scalar() == 0:
                        print("🔄 Adding seller_amount column to orders table...")
                        conn.execute(text('ALTER TABLE orders ADD COLUMN seller_amount REAL'))
                        migrations_applied.append("seller_amount")
                        print("✓ Added seller_amount column")
                    
                    # Check if commission_paid column exists
                    result = conn.execute(text(
                        "SELECT COUNT(*) FROM pragma_table_info('orders') WHERE name='commission_paid'"
                    ))
                    if result.scalar() == 0:
                        print("🔄 Adding commission_paid column to orders table...")
                        # SQLite stores BOOLEAN as INTEGER (0 or 1)
                        conn.execute(text('ALTER TABLE orders ADD COLUMN commission_paid BOOLEAN DEFAULT 0'))
                        migrations_applied.append("commission_paid")
                        print("✓ Added commission_paid column")
                    
                    # Check if commission_txid column exists
                    result = conn.execute(text(
                        "SELECT COUNT(*) FROM pragma_table_info('orders') WHERE name='commission_txid'"
                    ))
                    if result.scalar() == 0:
                        print("🔄 Adding commission_txid column to orders table...")
                        conn.execute(text('ALTER TABLE orders ADD COLUMN commission_txid TEXT'))
                        migrations_applied.append("commission_txid")
                        print("✓ Added commission_txid column")
                    
                    # Check if commission_paid_at column exists
                    result = conn.execute(text(
                        "SELECT COUNT(*) FROM pragma_table_info('orders') WHERE name='commission_paid_at'"
                    ))
                    if result.scalar() == 0:
                        print("🔄 Adding commission_paid_at column to orders table...")
                        conn.execute(text('ALTER TABLE orders ADD COLUMN commission_paid_at TIMESTAMP'))
                        migrations_applied.append("commission_paid_at")
                        print("✓ Added commission_paid_at column")
                    
                    # Check if tracking_number column exists
                    result = conn.execute(text(
                        "SELECT COUNT(*) FROM pragma_table_info('orders') WHERE name='tracking_number'"
                    ))
                    if result.scalar() == 0:
                        print("🔄 Adding tracking_number column to orders table...")
                        conn.execute(text('ALTER TABLE orders ADD COLUMN tracking_number TEXT'))
                        migrations_applied.append("tracking_number")
                        print("✓ Added tracking_number column")
                    
                    # Check if shipped_at column exists
                    result = conn.execute(text(
                        "SELECT COUNT(*) FROM pragma_table_info('orders') WHERE name='shipped_at'"
                    ))
                    if result.scalar() == 0:
                        print("🔄 Adding shipped_at column to orders table...")
                        conn.execute(text('ALTER TABLE orders ADD COLUMN shipped_at TIMESTAMP'))
                        migrations_applied.append("shipped_at")
                        print("✓ Added shipped_at column")

                    # Seller retention settings
                    seller_columns = {
                        'message_retention_days': 'INTEGER DEFAULT 30',
                        'order_archive_days': 'INTEGER DEFAULT 90',
                        'archive_retention_days': 'INTEGER DEFAULT 365',
                        'last_cleanup_at': 'TIMESTAMP',
                        'cleanup_status': 'TEXT',
                    }
                    for column_name, column_def in seller_columns.items():
                        result = conn.execute(text(
                            f"SELECT COUNT(*) FROM pragma_table_info('sellers') WHERE name='{column_name}'"
                        ))
                        if result.scalar() == 0:
                            print(f"🔄 Adding {column_name} column to sellers table...")
                            conn.execute(text(f'ALTER TABLE sellers ADD COLUMN {column_name} {column_def}'))
                            migrations_applied.append(column_name)
                            print(f"✓ Added {column_name} column")

                    # Message retention columns
                    message_columns = {
                        'expires_at': 'TIMESTAMP',
                        'archived_at': 'TIMESTAMP',
                    }
                    for column_name, column_def in message_columns.items():
                        result = conn.execute(text(
                            f"SELECT COUNT(*) FROM pragma_table_info('messages') WHERE name='{column_name}'"
                        ))
                        if result.scalar() == 0:
                            print(f"🔄 Adding {column_name} column to messages table...")
                            conn.execute(text(f'ALTER TABLE messages ADD COLUMN {column_name} {column_def}'))
                            migrations_applied.append(f"messages.{column_name}")
                            print(f"✓ Added {column_name} column")

                    # Order archival columns
                    order_columns = {
                        'archived_at': 'TIMESTAMP',
                        'purge_at': 'TIMESTAMP',
                    }
                    for column_name, column_def in order_columns.items():
                        result = conn.execute(text(
                            f"SELECT COUNT(*) FROM pragma_table_info('orders') WHERE name='{column_name}'"
                        ))
                        if result.scalar() == 0:
                            print(f"🔄 Adding {column_name} column to orders table...")
                            conn.execute(text(f'ALTER TABLE orders ADD COLUMN {column_name} {column_def}'))
                            migrations_applied.append(f"orders.{column_name}")
                            print(f"✓ Added {column_name} column")
                    
                    # Commit transaction
                    trans.commit()
                    
                    # Print summary
                    if migrations_applied:
                        print(f"✓ Applied migrations: {', '.join(migrations_applied)}")
                    else:
                        print("✓ Database schema up to date")
                    
                except Exception as e:
                    trans.rollback()
                    print(f"❌ Database migration failed: {str(e)}")
                    print("\nPlease backup your database before reporting this error:")
                    print(f"  cp {DATABASE_FILE} {DATABASE_FILE}.backup")
                    print(f"\nThen report this error on GitHub.")
                    raise e
                
        except Exception as e:
            print(f"⚠️  Error running migrations: {e}")

    
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
