"""
Buyer Handler - Processes buyer commands and order creation
"""

import re
from typing import Optional, Tuple
from datetime import datetime, timedelta
from ..models.product import ProductManager
from ..models.order import OrderManager, Order
from ..config.settings import ORDER_EXPIRATION_MINUTES
from ..utils.qr_generator import qr_generator


# TODO: Replace with real-time exchange rate API
XMR_EXCHANGE_RATE_USD = 150.0  # Placeholder: 1 XMR = $150 USD


class BuyerHandler:
    """Handles buyer commands and order creation"""
    
    def __init__(self, product_manager, order_manager, signal_handler, seller_signal_id):
        """
        Initialize buyer handler
        
        Args:
            product_manager: ProductManager instance
            order_manager: OrderManager instance
            signal_handler: SignalHandler instance
            seller_signal_id: Seller's Signal ID
        """
        self.product_manager = product_manager
        self.order_manager = order_manager
        self.signal_handler = signal_handler
        self.seller_signal_id = seller_signal_id
    
    @staticmethod
    def _format_product_id(product_id: Optional[str]) -> str:
        """
        Format product ID consistently
        
        Args:
            product_id: Product ID to format
            
        Returns:
            Formatted product ID string
        """
        if not product_id:
            return "N/A"
        
        # Add # prefix if not already present
        if not product_id.startswith('#'):
            return f"#{product_id}"
        
        return product_id
    
    def handle_buyer_message(self, buyer_signal_id: str, message_text: str):
        """
        Parse buyer commands and execute actions
        
        Args:
            buyer_signal_id: Buyer's Signal ID
            message_text: Message content
        """
        if not message_text:
            return
        
        message_lower = message_text.lower().strip()
        
        # Command: "catalog" or "show products"
        if any(word in message_lower for word in ['catalog', 'products', 'menu']):
            self.send_catalog(buyer_signal_id)
            return
        
        # Command: "order #1 qty 5" or "buy #2 qty 3"
        order_match = self._parse_order_command(message_text)
        if order_match:
            product_id, quantity = order_match
            self.create_order(buyer_signal_id, product_id, quantity)
            return
        
        # Command: "help"
        if 'help' in message_lower:
            self.send_help(buyer_signal_id)
            return
    
    def _parse_order_command(self, message: str) -> Optional[Tuple[str, int]]:
        """
        Parse order commands:
        - "order #1 qty 5"
        - "buy #2 qty 3"
        - "I want #3"
        - "order SKU-001 qty 10"
        
        Args:
            message: Message text to parse
            
        Returns:
            Tuple of (product_id, quantity) or None
        """
        # Pattern: "order/buy [product_id] qty [number]"
        pattern = r'(order|buy)\s+(#?[\w-]+)\s+qty\s+(\d+)'
        match = re.search(pattern, message.lower())
        
        if match:
            product_id = match.group(2)
            if not product_id.startswith('#'):
                product_id = '#' + product_id
            quantity = int(match.group(3))
            return (product_id, quantity)
        
        # Pattern: "order/buy [product_id]" (quantity defaults to 1)
        pattern = r'(order|buy)\s+(#?[\w-]+)'
        match = re.search(pattern, message.lower())
        
        if match:
            product_id = match.group(2)
            if not product_id.startswith('#'):
                product_id = '#' + product_id
            return (product_id, 1)
        
        return None
    
    def send_catalog(self, buyer_signal_id: str):
        """
        Send catalog to buyer
        
        Args:
            buyer_signal_id: Buyer's Signal ID
        """
        products = self.product_manager.list_products(active_only=True)
        
        if not products:
            self.signal_handler.send_message(
                recipient=buyer_signal_id,
                message="Sorry, no products are currently available."
            )
            return
        
        # Send catalog header
        header = f"🛍️ PRODUCT CATALOG ({len(products)} items)\n\n"
        self.signal_handler.send_message(
            recipient=buyer_signal_id,
            message=header
        )
        
        # Send each product
        for product in products:
            product_id_str = self._format_product_id(product.product_id)
            message = f"""━━━━━━━━━━━━━━━━━
{product_id_str} - {product.name}
━━━━━━━━━━━━━━━━━
{product.description}

💰 Price: {product.price} {product.currency}
📊 Stock: {product.stock} available
🏷️ Category: {product.category or 'N/A'}

To order: "order {product_id_str} qty [amount]"
"""
            
            attachments = []
            if product.image_path:
                attachments.append(product.image_path)
            
            self.signal_handler.send_message(
                recipient=buyer_signal_id,
                message=message.strip(),
                attachments=attachments if attachments else None
            )
    
    def create_order(self, buyer_signal_id: str, product_id: str, quantity: int):
        """
        Create order with stock validation and payment info
        
        Args:
            buyer_signal_id: Buyer's Signal ID
            product_id: Product ID to order
            quantity: Quantity to order
        """
        # Find product
        product = self.product_manager.get_product_by_product_id(product_id)
        
        if not product:
            self.signal_handler.send_message(
                recipient=buyer_signal_id,
                message=f"❌ Product {product_id} not found. Type 'catalog' to see available products."
            )
            return
        
        # Check stock
        if product.stock < quantity:
            if product.stock == 0:
                self.signal_handler.send_message(
                    recipient=buyer_signal_id,
                    message=f"❌ {product.name} is OUT OF STOCK"
                )
            else:
                self.signal_handler.send_message(
                    recipient=buyer_signal_id,
                    message=f"""⚠️ STOCK LIMITATION

You requested: {quantity} units
Available: {product.stock} units

Would you like to order {product.stock} instead?
Reply "order {product_id} qty {product.stock}" to proceed.
"""
                )
            return
        
        # Calculate totals with 7% commission
        unit_price = float(product.price)
        subtotal = unit_price * quantity
        commission = subtotal * 0.07  # 7% commission
        total = subtotal + commission
        
        # Get XMR conversion using configured exchange rate
        total_xmr = total / XMR_EXCHANGE_RATE_USD
        
        # Generate payment address (placeholder)
        payment_address = self._generate_payment_address(product.id, buyer_signal_id)
        
        # Create order in database
        order = Order(
            customer_signal_id=buyer_signal_id,
            product_id=product.id,
            product_name=product.name,
            quantity=quantity,
            price_fiat=unit_price,
            currency=product.currency,
            price_xmr=total_xmr,
            payment_address=payment_address,
            payment_status='pending',
            order_status='processing',
            commission_amount=commission * total_xmr / total,  # Commission in XMR
            seller_amount=subtotal * total_xmr / total,  # Seller amount in XMR
            expires_at=datetime.utcnow() + timedelta(minutes=ORDER_EXPIRATION_MINUTES)
        )
        
        created_order = self.order_manager.create_order(order)
        
        # Reduce stock (will be restored if order expires)
        product.stock -= quantity
        self.product_manager.update_product(product)
        
        # Send order confirmation with payment info
        self.send_order_confirmation(buyer_signal_id, created_order, product, payment_address)
    
    def send_order_confirmation(self, buyer_signal_id: str, order: Order, product, payment_address: str):
        """
        Send order summary with payment QR code
        
        Args:
            buyer_signal_id: Buyer's Signal ID
            order: Order object
            product: Product object
            payment_address: Monero payment address
        """
        message = f"""🛒 ORDER CONFIRMATION
Order #{order.order_id}

━━━━━━━━━━━━━━━━━
📦 Product: {product.name}
🔢 Quantity: {order.quantity} units
💰 Unit Price: {order.price_fiat} {order.currency}
━━━━━━━━━━━━━━━━━
💵 Subtotal: {order.price_fiat * order.quantity:.2f} {order.currency}
🏦 Platform Fee (7%): {(order.price_fiat * order.quantity * 0.07):.2f} {order.currency}
━━━━━━━━━━━━━━━━━
✅ TOTAL: {(order.price_fiat * order.quantity * 1.07):.2f} {order.currency}
≈ {order.price_xmr:.6f} XMR (at current rate)

📊 Stock Reserved: {order.quantity} units
⏰ Order expires in: {ORDER_EXPIRATION_MINUTES} minutes

💳 Send EXACTLY {order.price_xmr:.6f} XMR to:
{payment_address}
"""
        
        # Generate payment QR code
        try:
            qr_data = qr_generator.generate_payment_qr(payment_address, order.price_xmr)
            qr_path = f"/tmp/order_{order.order_id}_qr.png"
            
            with open(qr_path, 'wb') as f:
                f.write(qr_data)
            
            # Send message with QR code
            self.signal_handler.send_message(
                recipient=buyer_signal_id,
                message=message.strip(),
                attachments=[qr_path]
            )
        except Exception as e:
            print(f"Error generating QR code: {e}")
            # Send without QR code
            self.signal_handler.send_message(
                recipient=buyer_signal_id,
                message=message.strip()
            )
    
    def _generate_payment_address(self, product_id: int, buyer_signal_id: str) -> str:
        """
        Generate unique Monero sub-address for order
        
        Args:
            product_id: Product ID
            buyer_signal_id: Buyer's Signal ID
            
        Returns:
            Monero payment address
        """
        # TODO: Integrate with MoneroWallet.create_subaddress()
        # This is a placeholder implementation
        import hashlib
        hash_input = f"{product_id}{buyer_signal_id}{datetime.utcnow().isoformat()}"
        hash_hex = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
        return f"4{hash_hex}WQHqFEXuCep9YkqJ6ZB7WCnnJiemkAn8UvSpAe71Hr..."
    
    def send_help(self, buyer_signal_id: str):
        """
        Send help message to buyer
        
        Args:
            buyer_signal_id: Buyer's Signal ID
        """
        help_message = """🤖 BUYER COMMANDS

📋 View Products:
  • "catalog" or "products" - See all available products

🛒 Place Order:
  • "order #1 qty 5" - Order 5 units of product #1
  • "buy #2" - Order 1 unit of product #2
  • "order SKU-001 qty 3" - Order using SKU

❓ Get Help:
  • "help" - Show this message

💳 Payment:
After placing an order, you'll receive:
  • Order confirmation
  • Payment address
  • QR code for easy payment

⏰ Orders expire in 60 minutes if unpaid
"""
        
        self.signal_handler.send_message(
            recipient=buyer_signal_id,
            message=help_message.strip()
        )
