"""
Order model and management
"""

from typing import Optional, List
from datetime import datetime, timedelta
import secrets
from ..database.db import Order as OrderModel, DatabaseManager
from ..config.settings import ORDER_EXPIRATION_MINUTES


class ShippingNotificationError(Exception):
    """Raised when shipping notification fails to send"""
    pass



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
        address_index: Optional[int] = None,
        payment_status: str = "pending",
        payment_txid: Optional[str] = None,
        order_status: str = "processing",
        amount_paid: float = 0.0,
        commission_amount: float = 0.0,
        seller_amount: float = 0.0,
        commission_paid: bool = False,
        commission_txid: Optional[str] = None,
        commission_paid_at: Optional[datetime] = None,
        shipping_info: Optional[str] = None,
        tracking_number: Optional[str] = None,
        shipped_at: Optional[datetime] = None,
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
        self.address_index = address_index
        self.payment_status = payment_status
        self.payment_txid = payment_txid
        self.order_status = order_status
        self.amount_paid = amount_paid
        self.commission_amount = commission_amount
        self.seller_amount = seller_amount
        self.commission_paid = commission_paid
        self.commission_txid = commission_txid
        self.commission_paid_at = commission_paid_at
        self.shipping_info = shipping_info
        self.tracking_number = tracking_number
        self.shipped_at = shipped_at
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
            address_index=db_order.address_index,
            payment_status=db_order.payment_status,
            payment_txid=db_order.payment_txid,
            order_status=db_order.order_status,
            amount_paid=db_order.amount_paid,
            commission_amount=db_order.commission_amount,
            seller_amount=db_order.seller_amount,
            commission_paid=getattr(db_order, 'commission_paid', False),
            commission_txid=getattr(db_order, 'commission_txid', None),
            commission_paid_at=getattr(db_order, 'commission_paid_at', None),
            shipping_info=shipping_info,
            tracking_number=getattr(db_order, 'tracking_number', None),
            shipped_at=getattr(db_order, 'shipped_at', None),
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
            address_index=self.address_index,
            payment_status=self.payment_status,
            payment_txid=self.payment_txid,
            order_status=self.order_status,
            amount_paid=self.amount_paid,
            commission_amount=self.commission_amount,
            seller_amount=self.seller_amount,
            commission_paid=self.commission_paid,
            commission_txid=self.commission_txid,
            commission_paid_at=self.commission_paid_at,
            shipping_info=shipping_info_enc,
            shipping_info_salt=shipping_info_salt,
            tracking_number=self.tracking_number,
            shipped_at=self.shipped_at,
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
        db_order.address_index = order.address_index
        db_order.payment_txid = order.payment_txid
        db_order.tracking_number = order.tracking_number
        db_order.shipped_at = order.shipped_at
        
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
    
    def mark_order_shipped(self, order_id: str, tracking_number: str, signal_handler) -> Order:
        """
        Mark order as shipped and notify customer
        
        Args:
            order_id: Order ID
            tracking_number: Shipping tracking number
            signal_handler: SignalHandler instance for sending notifications
            
        Returns:
            Updated order
            
        Raises:
            ValueError: If tracking number is empty or order not found
        """
        # Validate tracking number
        if not tracking_number or len(tracking_number.strip()) == 0:
            raise ValueError("Tracking number cannot be empty")
        
        # Get order
        order = self.get_order(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        # Update order
        order.order_status = "shipped"
        order.tracking_number = tracking_number.strip()
        order.shipped_at = datetime.utcnow()
        
        # Save to database
        self.update_order(order)
        
        # Send notification to customer
        try:
            signal_handler.send_shipping_notification(
                order.customer_signal_id, 
                order.order_id,
                tracking_number,
                order.shipped_at
            )
        except Exception as e:
            # Raise custom exception for better error handling in GUI
            raise ShippingNotificationError(f"Order marked as shipped but notification failed: {str(e)}")
        
        return order
    
    def update_tracking_number(self, order_id: str, new_tracking: str, notify_customer: bool, signal_handler) -> Order:
        """
        Update tracking number for a shipped order and optionally notify customer
        
        Args:
            order_id: Order ID
            new_tracking: New tracking number
            notify_customer: Whether to send notification to customer
            signal_handler: SignalHandler instance for sending notifications
            
        Returns:
            Updated order
            
        Raises:
            ValueError: If tracking number is empty or order not found
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Validate tracking number
        if not new_tracking or len(new_tracking.strip()) == 0:
            raise ValueError("Tracking number cannot be empty")
        
        # Get order
        order = self.get_order(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        old_tracking = order.tracking_number
        
        # Update tracking number
        order.tracking_number = new_tracking.strip()
        self.update_order(order)
        
        # Log the update
        logger.info(f"Updated tracking for order {order_id}: {old_tracking} → {new_tracking}")
        
        # Notify customer if requested
        if notify_customer and signal_handler:
            try:
                message = f"🚚 Updated tracking information:\nTracking: {new_tracking.strip()}"
                signal_handler.send_message(order.customer_signal_id, message)
                logger.info(f"Sent tracking update notification to {order.customer_signal_id}")
            except Exception as e:
                logger.error(f"Failed to send tracking update notification: {str(e)}")
                raise ShippingNotificationError(f"Tracking updated but notification failed: {str(e)}")
        
        return order
    
    def resend_tracking_notification(self, order_id: str, signal_handler) -> Order:
        """
        Resend shipping notification to customer
        
        Args:
            order_id: Order ID
            signal_handler: SignalHandler instance for sending notifications
            
        Returns:
            Order
            
        Raises:
            ValueError: If order not found, not shipped, or no tracking number
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Get order
        order = self.get_order(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        if order.order_status != "shipped":
            raise ValueError("Order must be shipped to resend tracking")
        
        if not order.tracking_number:
            raise ValueError("No tracking number to send")
        
        # Send notification
        try:
            signal_handler.send_shipping_notification(
                order.customer_signal_id, 
                order.order_id,
                order.tracking_number,
                order.shipped_at
            )
            logger.info(f"Resent tracking notification for order {order_id} to {order.customer_signal_id}")
        except Exception as e:
            logger.error(f"Failed to resend tracking notification: {str(e)}")
            raise ShippingNotificationError(f"Failed to resend tracking: {str(e)}")
        
        return order
    
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
    
    def delete_order(self, order_id: str) -> bool:
        """
        Delete a single order by order ID.
        
        Args:
            order_id: Order ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        db_order = self.db.session.query(OrderModel).filter_by(order_id=order_id).first()
        if not db_order:
            return False
        
        self.db.session.delete(db_order)
        self.db.session.commit()
        return True
