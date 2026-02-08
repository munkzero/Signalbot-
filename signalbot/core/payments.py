"""
Payment processing and monitoring
Handles payment detection and commission forwarding
"""

import time
from typing import Optional, Dict, Callable
from datetime import datetime
from .monero_wallet import MoneroWallet
from .commission import CommissionManager
from ..models.order import Order, OrderManager
from ..config.settings import PAYMENT_CHECK_INTERVAL
import threading


class PaymentProcessor:
    """Processes payments and monitors orders"""
    
    def __init__(
        self,
        wallet: MoneroWallet,
        commission_manager: CommissionManager,
        order_manager: OrderManager
    ):
        """
        Initialize payment processor
        
        Args:
            wallet: Monero wallet instance
            commission_manager: Commission manager
            order_manager: Order manager
        """
        self.wallet = wallet
        self.commission = commission_manager
        self.orders = order_manager
        self.monitoring = False
        self.monitor_thread = None
        self.payment_callbacks = {}
    
    def create_payment_request(
        self,
        order: Order,
        xmr_amount: float
    ) -> Dict[str, any]:
        """
        Create payment request for order
        
        Args:
            order: Order instance
            xmr_amount: Amount in XMR
            
        Returns:
            Payment request info
        """
        # Calculate commission
        seller_amount, commission_amount = self.commission.calculate_commission(xmr_amount)
        
        # Create subaddress for this payment
        subaddress_info = self.wallet.create_subaddress(
            account_index=0,
            label=f"Order {order.order_id}"
        )
        
        # Update order
        order.payment_address = subaddress_info['address']
        order.price_xmr = xmr_amount
        order.commission_amount = commission_amount
        order.seller_amount = seller_amount
        
        return {
            'address': subaddress_info['address'],
            'amount': xmr_amount,
            'seller_amount': seller_amount,
            'commission_amount': commission_amount,
            'order_id': order.order_id
        }
    
    def check_order_payment(self, order: Order) -> Dict[str, any]:
        """
        Check payment status for order
        
        Args:
            order: Order to check
            
        Returns:
            Payment status info
        """
        payment_received, amount_received, confirmations = self.wallet.check_payment(
            order.payment_address,
            order.price_xmr
        )
        
        return {
            'received': payment_received,
            'amount': amount_received,
            'expected': order.price_xmr,
            'confirmations': confirmations,
            'complete': payment_received and confirmations >= 10
        }
    
    def process_payment(self, order: Order) -> bool:
        """
        Process payment for order
        Forwards commission and updates order status
        
        Args:
            order: Order with payment
            
        Returns:
            True if payment processed successfully
        """
        try:
            # Check payment
            status = self.check_order_payment(order)
            
            if not status['complete']:
                return False
            
            # Forward commission
            commission_sent = self._forward_commission(
                order.commission_amount,
                order.order_id
            )
            
            if not commission_sent:
                # Log but don't fail the order
                print(f"Warning: Failed to forward commission for order {order.order_id}")
            
            # Update order
            order.payment_status = 'paid'
            order.amount_paid = status['amount']
            order.paid_at = datetime.utcnow()
            self.orders.update_order(order)
            
            # Trigger callback if registered
            if order.order_id in self.payment_callbacks:
                self.payment_callbacks[order.order_id](order)
            
            return True
        except Exception as e:
            print(f"Error processing payment for order {order.order_id}: {e}")
            return False
    
    def _forward_commission(self, amount: float, order_id: str) -> bool:
        """
        Forward commission to creator wallet
        
        Args:
            amount: Commission amount in XMR
            order_id: Order ID for reference
            
        Returns:
            True if commission forwarded successfully
        """
        try:
            # Get commission wallet address
            commission_wallet = self.commission.get_commission_wallet()
            
            # Send commission
            result = self.wallet.transfer(
                destinations=[{
                    'address': commission_wallet,
                    'amount': amount
                }],
                priority=1  # Normal priority
            )
            
            print(f"Commission forwarded for order {order_id}: {amount} XMR")
            print(f"TX Hash: {result['tx_hash']}")
            
            return True
        except Exception as e:
            print(f"Failed to forward commission: {e}")
            return False
    
    def start_monitoring(self):
        """Start monitoring pending orders for payments"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop monitoring payments"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
    
    def _monitor_loop(self):
        """
        Background loop to monitor pending orders
        """
        while self.monitoring:
            try:
                # Get pending orders
                pending_orders = self.orders.list_orders(payment_status='pending')
                
                for order in pending_orders:
                    # Check if expired
                    if order.expires_at < datetime.utcnow():
                        continue
                    
                    # Check payment
                    status = self.check_order_payment(order)
                    
                    if status['complete']:
                        # Process payment
                        self.process_payment(order)
                    elif status['amount'] > 0:
                        # Partial payment
                        order.payment_status = 'partial'
                        order.amount_paid = status['amount']
                        self.orders.update_order(order)
                
                # Expire old orders
                self.orders.expire_old_orders()
                
            except Exception as e:
                print(f"Error in payment monitoring: {e}")
            
            # Sleep between checks
            time.sleep(PAYMENT_CHECK_INTERVAL)
    
    def register_payment_callback(self, order_id: str, callback: Callable):
        """
        Register callback for payment notification
        
        Args:
            order_id: Order ID
            callback: Callback function(order)
        """
        self.payment_callbacks[order_id] = callback
    
    def unregister_payment_callback(self, order_id: str):
        """
        Unregister payment callback
        
        Args:
            order_id: Order ID
        """
        if order_id in self.payment_callbacks:
            del self.payment_callbacks[order_id]
