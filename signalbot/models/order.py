"""
Order model and management
"""

from typing import Optional, List
from datetime import datetime, timedelta
import secrets
from ..database.db import Order as OrderModel, DatabaseManager
from ..config.settings import ORDER_EXPIRATION_MINUTES


class Order:
    """Order entity with encryption support"""
    
    def __init__(
        self,
        id: Optional[int] = None,
        order_id: Optional[str] = None,
        customer_signal_id: str = "",
        product_id: int = 0,
        product_name: str = "",
        quantity: int = 1,
        price_fiat: float = 0.0,
        currency: str = "USD",
        price_xmr: float = 0.0,
        payment_address: str = "",
        payment_status: str = "pending",
        order_status: str = "processing",
        amount_paid: float = 0.0,
        commission_amount: float = 0.0,
        seller_amount: float = 0.0,
        shipping_info: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        paid_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None
    ):
        self.id = id
        self.order_id = order_id or self._generate_order_id()
        self.customer_signal_id = customer_signal_id
        self.product_id = product_id
        self.product_name = product_name
        self.quantity = quantity
        self.price_fiat = price_fiat
        self.currency = currency
        self.price_xmr = price_xmr
        self.payment_address = payment_address
        self.payment_status = payment_status
        self.order_status = order_status
        self.amount_paid = amount_paid
        self.commission_amount = commission_amount
        self.seller_amount = seller_amount
        self.shipping_info = shipping_info
        self.expires_at = expires_at or (datetime.utcnow() + timedelta(minutes=ORDER_EXPIRATION_MINUTES))
        self.paid_at = paid_at
        self.created_at = created_at or datetime.utcnow()
    
    @staticmethod
    def _generate_order_id() -> str:
        """Generate unique order ID"""
        return f"ORD-{secrets.token_hex(8).upper()}"
    
    @classmethod
    def from_db_model(cls, db_order: OrderModel, db_manager: DatabaseManager) -> 'Order':
        """
        Create Order from database model
        
        Args:
            db_order: Database order model
            db_manager: Database manager for decryption
            
        Returns:
            Order instance
        """
        customer_signal_id = db_manager.decrypt_field(
            db_order.customer_signal_id,
            db_order.customer_signal_id_salt
        )
        
        payment_address = db_manager.decrypt_field(
            db_order.payment_address,
            db_order.payment_address_salt
        )
        
        shipping_info = None
        if db_order.shipping_info and db_order.shipping_info_salt:
            try:
                shipping_info = db_manager.decrypt_field(
                    db_order.shipping_info,
                    db_order.shipping_info_salt
                )
            except:
                shipping_info = None
        
        return cls(
            id=db_order.id,
            order_id=db_order.order_id,
            customer_signal_id=customer_signal_id,
            product_id=db_order.product_id,
            product_name=db_order.product_name,
            quantity=db_order.quantity,
            price_fiat=db_order.price_fiat,
            currency=db_order.currency,
            price_xmr=db_order.price_xmr,
            payment_address=payment_address,
            payment_status=db_order.payment_status,
            order_status=db_order.order_status,
            amount_paid=db_order.amount_paid,
            commission_amount=db_order.commission_amount,
            seller_amount=db_order.seller_amount,
            shipping_info=shipping_info,
            expires_at=db_order.expires_at,
            paid_at=db_order.paid_at,
            created_at=db_order.created_at
        )
    
    def to_db_model(self, db_manager: DatabaseManager) -> OrderModel:
        """
        Convert to database model
        
        Args:
            db_manager: Database manager for encryption
            
        Returns:
            Database order model
        """
        customer_id_enc, customer_id_salt = db_manager.encrypt_field(self.customer_signal_id)
        payment_addr_enc, payment_addr_salt = db_manager.encrypt_field(self.payment_address)
        
        shipping_info_enc = None
        shipping_info_salt = None
        if self.shipping_info:
            shipping_info_enc, shipping_info_salt = db_manager.encrypt_field(self.shipping_info)
        
        db_order = OrderModel(
            order_id=self.order_id,
            customer_signal_id=customer_id_enc,
            customer_signal_id_salt=customer_id_salt,
            product_id=self.product_id,
            product_name=self.product_name,
            quantity=self.quantity,
            price_fiat=self.price_fiat,
            currency=self.currency,
            price_xmr=self.price_xmr,
            payment_address=payment_addr_enc,
            payment_address_salt=payment_addr_salt,
            payment_status=self.payment_status,
            order_status=self.order_status,
            amount_paid=self.amount_paid,
            commission_amount=self.commission_amount,
            seller_amount=self.seller_amount,
            shipping_info=shipping_info_enc,
            shipping_info_salt=shipping_info_salt,
            expires_at=self.expires_at,
            paid_at=self.paid_at
        )
        
        if self.id:
            db_order.id = self.id
        
        return db_order


class OrderManager:
    """Manages order operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_order(self, order: Order) -> Order:
        """
        Create a new order
        
        Args:
            order: Order to create
            
        Returns:
            Created order with ID
        """
        db_order = order.to_db_model(self.db)
        self.db.session.add(db_order)
        self.db.session.commit()
        
        order.id = db_order.id
        return order
    
    def update_order(self, order: Order) -> Order:
        """
        Update existing order
        
        Args:
            order: Order to update
            
        Returns:
            Updated order
        """
        db_order = self.db.session.query(OrderModel).filter_by(id=order.id).first()
        if not db_order:
            raise ValueError(f"Order with ID {order.id} not found")
        
        # Update fields
        db_order.payment_status = order.payment_status
        db_order.order_status = order.order_status
        db_order.amount_paid = order.amount_paid
        db_order.paid_at = order.paid_at
        
        if order.shipping_info:
            shipping_enc, shipping_salt = self.db.encrypt_field(order.shipping_info)
            db_order.shipping_info = shipping_enc
            db_order.shipping_info_salt = shipping_salt
        
        self.db.session.commit()
        return order
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """
        Get order by order ID
        
        Args:
            order_id: Order ID
            
        Returns:
            Order or None if not found
        """
        db_order = self.db.session.query(OrderModel).filter_by(order_id=order_id).first()
        if db_order:
            return Order.from_db_model(db_order, self.db)
        return None
    
    def list_orders(
        self,
        payment_status: Optional[str] = None,
        order_status: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Order]:
        """
        List orders with filtering
        
        Args:
            payment_status: Filter by payment status
            order_status: Filter by order status
            limit: Maximum number of orders to return
            
        Returns:
            List of orders
        """
        query = self.db.session.query(OrderModel).order_by(OrderModel.created_at.desc())
        
        if payment_status:
            query = query.filter_by(payment_status=payment_status)
        
        if order_status:
            query = query.filter_by(order_status=order_status)
        
        if limit:
            query = query.limit(limit)
        
        db_orders = query.all()
        return [Order.from_db_model(o, self.db) for o in db_orders]
    
    def expire_old_orders(self):
        """
        Mark expired orders and restore stock
        
        Returns:
            List of expired order IDs
        """
        now = datetime.utcnow()
        expired_orders = self.db.session.query(OrderModel).filter(
            OrderModel.payment_status == 'pending',
            OrderModel.expires_at < now
        ).all()
        
        expired_ids = []
        for order in expired_orders:
            order.payment_status = 'expired'
            expired_ids.append(order.order_id)
        
        self.db.session.commit()
        return expired_ids
    
    def mark_paid(self, order_id: str, amount_paid: float):
        """
        Mark order as paid
        
        Args:
            order_id: Order ID
            amount_paid: Amount paid in XMR
        """
        db_order = self.db.session.query(OrderModel).filter_by(order_id=order_id).first()
        if not db_order:
            raise ValueError(f"Order {order_id} not found")
        
        db_order.amount_paid = amount_paid
        db_order.paid_at = datetime.utcnow()
        
        if amount_paid >= db_order.price_xmr:
            db_order.payment_status = 'paid'
        else:
            db_order.payment_status = 'partial'
        
        self.db.session.commit()
    
    def count_orders_matching(self, criteria: dict) -> int:
        """
        Count orders matching deletion criteria
        
        Args:
            criteria: dict with:
                - statuses: list of statuses to delete
                - older_than_days: int or None
        
        Returns:
            Number of orders matching criteria
        """
        query = self.db.session.query(OrderModel)
        
        # Filter by status
        if criteria.get('statuses'):
            query = query.filter(OrderModel.payment_status.in_(criteria['statuses']))
        
        # Filter by age
        if criteria.get('older_than_days'):
            # Using utcnow() for compatibility; consider datetime.now(timezone.utc) for Python 3.12+
            cutoff_date = datetime.utcnow() - timedelta(days=criteria['older_than_days'])
            query = query.filter(OrderModel.created_at < cutoff_date)
        
        return query.count()
    
    def delete_orders(self, criteria: dict) -> int:
        """
        Delete orders matching criteria
        
        Args:
            criteria: dict with:
                - statuses: list of statuses to delete
                - older_than_days: int or None
        
        Returns:
            Number of orders deleted
        """
        query = self.db.session.query(OrderModel)
        
        # Filter by status
        if criteria.get('statuses'):
            query = query.filter(OrderModel.payment_status.in_(criteria['statuses']))
        
        # Filter by age
        if criteria.get('older_than_days'):
            # Using utcnow() for compatibility; consider datetime.now(timezone.utc) for Python 3.12+
            cutoff_date = datetime.utcnow() - timedelta(days=criteria['older_than_days'])
            query = query.filter(OrderModel.created_at < cutoff_date)
        
        # Delete
        count = query.count()
        query.delete(synchronize_session=False)
        self.db.session.commit()
        
        return count
