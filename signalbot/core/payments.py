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
from ..config.settings import PAYMENT_CHECK_INTERVAL, MONERO_CONFIRMATIONS_REQUIRED
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
            label=f"Order-{order.order_id}"
        )
        
        # Update order with payment details
        order.payment_address = subaddress_info['address']
        order.address_index = subaddress_info.get('address_index', None)
        order.price_xmr = xmr_amount
        order.commission_amount = commission_amount
        order.seller_amount = seller_amount
        
        return {
            'address': subaddress_info['address'],
            'address_index': subaddress_info.get('address_index', None),
            'amount': xmr_amount,
            'seller_amount': seller_amount,
            'commission_amount': commission_amount,
            'order_id': order.order_id
        }
    
    def check_order_payment(self, order: Order) -> Dict[str, any]:
        """
        Check payment status for order using subaddress monitoring
        
        Args:
            order: Order to check
            
        Returns:
            Payment status info with detailed transaction data
        """
        try:
            # Use subaddress index for efficient monitoring if available
            if order.address_index is not None:
                transfers = self.wallet.get_transfers(
                    subaddr_indices=[order.address_index],
                    account_index=0
                )
            else:
                # Fallback to address-based lookup
                transfers = self.wallet.get_transfers(address=order.payment_address)
            
            total_received = 0.0
            max_confirmations = 0
            latest_txid = None
            
            # Process all transfers to this address
            for transfer in transfers:
                # Convert from atomic units to XMR
                amount = transfer.get('amount', 0) / 1e12
                confirmations = transfer.get('confirmations', 0)
                
                total_received += amount
                if confirmations > max_confirmations:
                    max_confirmations = confirmations
                    latest_txid = transfer.get('txid', None)
            
            # Determine payment status
            is_complete = (
                total_received >= order.price_xmr and
                max_confirmations >= MONERO_CONFIRMATIONS_REQUIRED
            )
            
            is_unconfirmed = (
                total_received >= order.price_xmr and
                max_confirmations < MONERO_CONFIRMATIONS_REQUIRED
            )
            
            is_partial = (
                total_received > 0 and
                total_received < order.price_xmr
            )
            
            return {
                'received': is_complete,
                'amount': total_received,
                'expected': order.price_xmr,
                'confirmations': max_confirmations,
                'txid': latest_txid,
                'complete': is_complete,
                'unconfirmed': is_unconfirmed,
                'partial': is_partial
            }
        except Exception as e:
            print(f"Error checking payment for order {order.order_id}: {e}")
            return {
                'received': False,
                'amount': 0.0,
                'expected': order.price_xmr,
                'confirmations': 0,
                'txid': None,
                'complete': False,
                'unconfirmed': False,
                'partial': False
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
            
            # Update order with payment details
            order.payment_status = 'paid'
            order.amount_paid = status['amount']
            order.payment_txid = status['txid']
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
            True if commission forwarded successfully, or if view-only (cannot send)
        """
        try:
            # CRITICAL FIX: Check if wallet is view-only
            if self.wallet.is_view_only():
                print(f"INFO: View-only wallet detected - Commission {amount:.6f} XMR for order {order_id} must be paid manually")
                commission_wallet = self.commission.get_commission_wallet()
                print(f"INFO: Send {amount:.6f} XMR to: {commission_wallet}")
                # Don't fail the order - just log for manual payout
                return True
            
            # Get commission wallet address
            commission_wallet = self.commission.get_commission_wallet()
            
            # Send commission
            print(f"DEBUG: Sending commission for order {order_id}: {amount:.6f} XMR")
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
            print(f"ERROR: Failed to forward commission: {e}")
            return False
    
    def start_monitoring(self):
        """Start monitoring pending orders for payments"""
        if self.monitoring:
            print("DEBUG: start_monitoring() called but already monitoring")
            return
        
        print("DEBUG: Payment monitoring started")
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop monitoring payments"""
        print("DEBUG: Stopping payment monitoring")
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
    
    def _monitor_loop(self):
        """
        Background loop to monitor pending orders
        """
        print("DEBUG: Payment monitor loop started")
        
        while self.monitoring:
            try:
                # Get pending orders
                pending_orders = self.orders.list_orders(payment_status='pending')
                
                if pending_orders:
                    print(f"DEBUG: Checking {len(pending_orders)} pending orders for payments")
                
                for order in pending_orders:
                    # Check if expired
                    if order.expires_at < datetime.utcnow():
                        continue
                    
                    print(f"DEBUG: Checking payment for order #{order.order_id}")
                    
                    # Check payment
                    status = self.check_order_payment(order)
                    
                    if status['complete']:
                        print(f"✓ Payment confirmed! {status['amount']:.6f} XMR for order #{order.order_id}")
                        print(f"  TX: {status['txid']}")
                        print(f"  Confirmations: {status['confirmations']}")
                        # Process payment (confirm and forward commission)
                        self.process_payment(order)
                    elif status['unconfirmed']:
                        print(f"⏳ Payment detected (unconfirmed): {status['amount']:.6f} XMR for order #{order.order_id}")
                        print(f"  TX: {status['txid']}")
                        print(f"  Confirmations: {status['confirmations']}/{MONERO_CONFIRMATIONS_REQUIRED}")
                        # Update status to unconfirmed
                        order.payment_status = 'unconfirmed'
                        order.amount_paid = status['amount']
                        order.payment_txid = status['txid']
                        self.orders.update_order(order)
                    elif status['partial']:
                        print(f"⚠ Partial payment: {status['amount']:.6f}/{status['expected']:.6f} XMR for order #{order.order_id}")
                        # Partial payment
                        order.payment_status = 'partial'
                        order.amount_paid = status['amount']
                        if status['txid']:
                            order.payment_txid = status['txid']
                        self.orders.update_order(order)
                
                # Also check unconfirmed orders for confirmation
                unconfirmed_orders = self.orders.list_orders(payment_status='unconfirmed')
                for order in unconfirmed_orders:
                    status = self.check_order_payment(order)
                    if status['complete']:
                        print(f"✓ Payment now confirmed for order #{order.order_id}")
                        self.process_payment(order)
                
                # Expire old orders
                self.orders.expire_old_orders()
                
            except Exception as e:
                print(f"ERROR: Error in payment monitoring: {e}")
            
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
