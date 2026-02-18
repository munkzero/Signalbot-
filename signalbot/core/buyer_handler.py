"""
Buyer Handler - Processes buyer commands and order creation
"""

import os
import re
import time
import logging
from typing import Optional, Tuple
from datetime import datetime, timedelta
from ..models.product import ProductManager
from ..models.order import OrderManager, Order
from ..config.settings import ORDER_EXPIRATION_MINUTES
from ..utils.qr_generator import qr_generator
from ..utils.currency import currency_converter, ExchangeRateUnavailableError

logger = logging.getLogger(__name__)

# Delay between catalog product messages to avoid rate limiting
CATALOG_SEND_DELAY_SECONDS = 1.5

# Common image directories to search for product images (in order of priority)
COMMON_IMAGE_SEARCH_DIRS = [
    'data/products/images',      # Expected location
    'data/images',                # Alternative location
    'data/product_images',        # Another common location
    'images',                     # Simple location
    '.',                          # Current directory
]


class ProductCache:
    """Cache for product data to reduce database queries"""
    
    def __init__(self, product_manager, cache_duration: int = 300):
        """
        Initialize product cache
        
        Args:
            product_manager: ProductManager instance
            cache_duration: Cache lifetime in seconds (default 5 minutes)
        """
        self.product_manager = product_manager
        self.cache = None
        self.last_refresh = 0
        self.cache_duration = cache_duration
    
    def get_products(self, active_only: bool = True) -> list:
        """
        Get products from cache or refresh if stale
        
        Args:
            active_only: Return only active products
            
        Returns:
            List of products
        """
        now = time.time()
        
        # Refresh cache if empty or expired
        if self.cache is None or (now - self.last_refresh) > self.cache_duration:
            self.cache = self.product_manager.list_products(active_only=active_only)
            self.last_refresh = now
            print(f"📦 Product cache refreshed ({len(self.cache)} products)")
        
        return self.cache
    
    def invalidate(self):
        """Force cache refresh on next get"""
        self.cache = None
        self.last_refresh = 0


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
        
        # Add product cache
        self.product_cache = ProductCache(product_manager, cache_duration=300)
        
        # Conversation state tracking for order flow
        # Format: {buyer_signal_id: {'state': 'awaiting_name'|'awaiting_address', 'product_id': str, 'quantity': int}}
        self.conversation_states = {}
    
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
    
    def _resolve_image_path(self, image_path: str) -> Optional[str]:
        """
        Resolve image path by checking multiple common locations.
        Handles both relative and absolute paths.
        
        Args:
            image_path: Image path from database (may be relative)
            
        Returns:
            Absolute path if file found, None otherwise
        """
        if not image_path:
            return None
        
        # If already absolute and exists, return it
        if os.path.isabs(image_path):
            if os.path.exists(image_path) and os.path.isfile(image_path):
                return image_path
            else:
                print(f"  Absolute path doesn't exist: {image_path}")
                return None
        
        # Relative path - search common directories
        base_dir = os.getcwd()
        
        # Try each directory
        for search_dir in COMMON_IMAGE_SEARCH_DIRS:
            full_path = os.path.join(base_dir, search_dir, image_path)
            
            if os.path.exists(full_path) and os.path.isfile(full_path):
                print(f"  ✓ Found image: {full_path}")
                return full_path
            else:
                print(f"  ✗ Not found: {full_path}")
        
        print(f"  ✗ Image not found in any common directory: {image_path}")
        print(f"    Searched: {', '.join(COMMON_IMAGE_SEARCH_DIRS)}")
        return None
    
    def _optimize_image_for_signal(self, image_path: str, max_size_kb: int = 800) -> str:
        """
        Optimize image for Signal sending - compress and resize if needed.
        
        Args:
            image_path: Path to original image
            max_size_kb: Maximum file size in KB (default 800KB)
            
        Returns:
            Path to optimized image (or original if already optimal)
        """
        try:
            from PIL import Image
            import tempfile
            
            # Check current size
            file_size_kb = os.path.getsize(image_path) / 1024
            file_ext = os.path.splitext(image_path)[1].lower()
            
            print(f"  📊 Original: {file_size_kb:.1f}KB, Format: {file_ext}")
            
            # If already small and JPG, use as-is
            if file_size_kb <= max_size_kb and file_ext in ['.jpg', '.jpeg']:
                print(f"  ✓ Image already optimized")
                return image_path
            
            # Open and optimize
            img = Image.open(image_path)
            
            # Convert RGBA to RGB if needed (for PNG with transparency)
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            # Resize if too large (max 1920px on longest side)
            max_dimension = 1920
            if img.width > max_dimension or img.height > max_dimension:
                ratio = max_dimension / max(img.width, img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                print(f"  📐 Resized to: {new_size[0]}x{new_size[1]}")
            
            # Save as optimized JPG
            optimized_path = os.path.join(
                tempfile.gettempdir(),
                f"signal_opt_{os.path.basename(image_path).rsplit('.', 1)[0]}.jpg"
            )
            
            # Start with quality 85, reduce if still too large
            quality = 85
            while quality >= 60:
                img.save(optimized_path, 'JPEG', quality=quality, optimize=True)
                new_size_kb = os.path.getsize(optimized_path) / 1024
                
                if new_size_kb <= max_size_kb or quality == 60:
                    print(f"  📉 Optimized: {file_size_kb:.1f}KB → {new_size_kb:.1f}KB (quality={quality})")
                    return optimized_path
                
                quality -= 5
            
            return optimized_path
            
        except ImportError:
            print(f"  ⚠️  PIL/Pillow not installed - cannot optimize images")
            print(f"     Install with: pip install Pillow")
            return image_path
        except Exception as e:
            print(f"  ⚠️  Image optimization failed: {e}")
            print(f"     Using original image")
            return image_path
    
    def handle_buyer_message(self, buyer_signal_id: str, message_text: str, recipient_identity: Optional[str] = None):
        """
        Parse buyer commands and execute actions
        
        Args:
            buyer_signal_id: Buyer's Signal ID
            message_text: Message content
            recipient_identity: Identity that received the message (phone or username)
        """
        if not message_text:
            return
        
        # Use seller_signal_id as fallback if no recipient_identity provided
        if not recipient_identity:
            recipient_identity = self.seller_signal_id
        
        message_lower = message_text.lower().strip()
        
        print(f"DEBUG: Processing buyer command: {message_text[:50]}")
        
        # Check if user is in a conversation flow (collecting shipping info)
        if buyer_signal_id in self.conversation_states:
            self._handle_conversation_state(buyer_signal_id, message_text, recipient_identity)
            return
        
        # Command: "catalog" or "show products" - improved matching to avoid false positives
        # Match specific keywords or common phrases
        catalog_keywords = ['catalog', 'catalogue', 'menu']
        catalog_phrases = ['show products', 'show catalog', 'show catalogue', 'show menu', 'view products', 'view catalog']
        
        # Also check if message is a simple request like "products" or "items"
        simple_requests = ['products', 'items', 'list']
        
        is_catalog_request = (
            any(word in message_lower for word in catalog_keywords) or
            any(phrase in message_lower for phrase in catalog_phrases) or
            message_lower in simple_requests
        )
        
        if is_catalog_request:
            print(f"DEBUG: Sending catalog to {buyer_signal_id}")
            self.send_catalog(buyer_signal_id, recipient_identity)
            return
        
        # Command: "order #1 qty 5" or "buy #2 qty 3"
        order_match = self._parse_order_command(message_text)
        if order_match:
            product_id, quantity = order_match
            print(f"DEBUG: Initiating order conversation for product {product_id} qty {quantity}")
            self._initiate_order_conversation(buyer_signal_id, product_id, quantity, recipient_identity)
            return
        
        # Command: "help"
        if 'help' in message_lower:
            print(f"DEBUG: Sending help to {buyer_signal_id}")
            self.send_help(buyer_signal_id, recipient_identity)
            return
    
    def _initiate_order_conversation(self, buyer_signal_id: str, product_id: str, quantity: int, recipient_identity: Optional[str] = None):
        """
        Start the order conversation flow by asking for customer name
        
        Args:
            buyer_signal_id: Buyer's Signal ID
            product_id: Product ID to order
            quantity: Quantity to order
            recipient_identity: Identity that received the message
        """
        # Store conversation state
        self.conversation_states[buyer_signal_id] = {
            'state': 'awaiting_name',
            'product_id': product_id,
            'quantity': quantity,
            'recipient_identity': recipient_identity
        }
        
        # Ask for name
        self.signal_handler.send_message(
            recipient=buyer_signal_id,
            message="📝 What's your name?",
            sender_identity=recipient_identity
        )
        print(f"DEBUG: Waiting for name from {buyer_signal_id}")
    
    def _handle_conversation_state(self, buyer_signal_id: str, message_text: str, recipient_identity: Optional[str] = None):
        """
        Handle conversation state for collecting shipping information
        
        Args:
            buyer_signal_id: Buyer's Signal ID
            message_text: Message content
            recipient_identity: Identity that received the message
        """
        state_info = self.conversation_states[buyer_signal_id]
        current_state = state_info['state']
        
        if current_state == 'awaiting_name':
            # Store the name and ask for address
            state_info['name'] = message_text.strip()
            state_info['state'] = 'awaiting_address'
            
            self.signal_handler.send_message(
                recipient=buyer_signal_id,
                message="📍 What's your shipping address?\n(Please include street, city, and postal code)",
                sender_identity=state_info.get('recipient_identity', recipient_identity)
            )
            print(f"DEBUG: Received name, waiting for address from {buyer_signal_id}")
        
        elif current_state == 'awaiting_address':
            # Store the address and create the order
            state_info['address'] = message_text.strip()
            
            # Create the order with shipping info
            self._create_order_with_shipping_info(
                buyer_signal_id,
                state_info['product_id'],
                state_info['quantity'],
                state_info['name'],
                state_info['address'],
                state_info.get('recipient_identity', recipient_identity)
            )
            
            # Clear conversation state
            del self.conversation_states[buyer_signal_id]
            print(f"DEBUG: Order creation completed for {buyer_signal_id}")
    
    def _create_order_with_shipping_info(self, buyer_signal_id: str, product_id: str, quantity: int, 
                                         name: str, address: str, recipient_identity: Optional[str] = None):
        """
        Create order with collected shipping information
        
        Args:
            buyer_signal_id: Buyer's Signal ID
            product_id: Product ID
            quantity: Quantity
            name: Customer name
            address: Shipping address
            recipient_identity: Identity that received the message
        """
        import json
        
        # Create shipping info as JSON
        shipping_info = json.dumps({
            'name': name,
            'address': address
        })
        
        # Call the existing create_order but with shipping_info parameter
        self.create_order(buyer_signal_id, product_id, quantity, recipient_identity, shipping_info=shipping_info)
    
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
    
    def send_catalog(self, buyer_signal_id: str, recipient_identity: Optional[str] = None):
        """
        Send catalog to buyer with robust error handling
        
        Args:
            buyer_signal_id: Buyer's Signal ID
            recipient_identity: Identity to send from (phone or username)
        """
        
        products = self.product_cache.get_products(active_only=True)
        
        if not products:
            self.signal_handler.send_message(
                recipient=buyer_signal_id,
                message="Sorry, no products are currently available.",
                sender_identity=recipient_identity
            )
            return
        
        total_products = len(products)
        print(f"\n{'='*60}")
        print(f"📦 SENDING CATALOG: {total_products} products")
        print(f"{'='*60}\n")
        
        # Send catalog header
        header = f"🛍️ PRODUCT CATALOG ({total_products} items)\n\n"
        try:
            self.signal_handler.send_message(
                recipient=buyer_signal_id,
                message=header,
                sender_identity=recipient_identity
            )
            print(f"✓ Catalog header sent\n")
        except Exception as e:
            print(f"✗ Failed to send header: {e}\n")
        
        # Track success/failure
        sent_count = 0
        failed_products = []
        
        # Send each product with robust error handling
        for index, product in enumerate(products, 1):
            product_id_str = self._format_product_id(product.product_id)
            
            print(f"{'─'*60}")
            print(f"📦 Product {index}/{total_products}: {product.name} ({product_id_str})")
            print(f"{'─'*60}")
            
            message = f"""━━━━━━━━━━━━━━━━━
{product_id_str} - {product.name}
━━━━━━━━━━━━━━━━━
{product.description}

💰 Price: {product.price} {product.currency}
📊 Stock: {product.stock} available
🏷️ Category: {product.category or 'N/A'}

To order: "order {product_id_str} qty [amount]"
"""
            
            # Resolve and optimize image
            attachments = []
            if product.image_path:
                print(f"  🔍 Resolving image path...")
                resolved_path = self._resolve_image_path(product.image_path)
                
                if resolved_path:
                    # Optimize image before sending
                    optimized_path = self._optimize_image_for_signal(resolved_path)
                    attachments.append(optimized_path)
                else:
                    print(f"  ⚠ No image found (will send text only)")
            
            # Attempt to send with exponential backoff retry logic
            max_retries = 5
            success = False
            
            for attempt in range(1, max_retries + 1):
                try:
                    print(f"  📤 Sending (attempt {attempt}/{max_retries})...")
                    
                    result = self.signal_handler.send_message(
                        recipient=buyer_signal_id,
                        message=message.strip(),
                        attachments=attachments if attachments else None,
                        sender_identity=recipient_identity
                    )
                    
                    if result:
                        sent_count += 1
                        success = True
                        print(f"  ✅ SUCCESS - Product sent!")
                        break  # Exit retry loop
                    else:
                        print(f"  ✗ Attempt {attempt} failed")
                        
                        if attempt < max_retries:
                            # Exponential backoff: 3s, 6s, 12s, 24s, 48s (capped at 60s)
                            retry_delay = min(3 * (2 ** (attempt - 1)), 60)
                            print(f"  ⏳ Waiting {retry_delay}s before retry...")
                            time.sleep(retry_delay)
                
                except Exception as e:
                    print(f"  ✗ Error on attempt {attempt}: {e}")
                    
                    if attempt < max_retries:
                        # Exponential backoff: 3s, 6s, 12s, 24s, 48s (capped at 60s)
                        retry_delay = min(3 * (2 ** (attempt - 1)), 60)
                        print(f"  ⏳ Waiting {retry_delay}s before retry...")
                        time.sleep(retry_delay)
            
            # Track failure if all attempts failed
            if not success:
                print(f"  ❌ FAILED after {max_retries} attempts")
                
                # Try one final time without image (text-only fallback)
                if attachments:
                    print(f"  📝 Attempting text-only fallback (no image)...")
                    try:
                        result = self.signal_handler.send_message(
                            recipient=buyer_signal_id,
                            message=message.strip(),
                            attachments=None,  # No image
                            sender_identity=recipient_identity
                        )
                        if result:
                            print(f"  ✅ Text-only version sent successfully")
                            sent_count += 1
                            success = True
                        else:
                            print(f"  ✗ Text-only fallback also failed")
                            failed_products.append(product.name)
                    except Exception as e:
                        print(f"  ✗ Text-only fallback error: {e}")
                        failed_products.append(product.name)
                else:
                    failed_products.append(product.name)
            
            # Delay between products (avoid rate limiting)
            if index < total_products:  # Don't delay after last product
                delay = 2.5
                print(f"  ⏸ Waiting {delay}s before next product...\n")
                time.sleep(delay)
            else:
                print()  # Just newline for last product
        
        # Send footer
        print(f"{'─'*60}")
        print(f"📋 Sending catalog footer...")
        print(f"{'─'*60}")
        
        footer = f"\n✨ End of catalog\n\nTo order, reply with 'ORDER {product_id_str} QTY X'"
        try:
            self.signal_handler.send_message(
                recipient=buyer_signal_id,
                message=footer,
                sender_identity=recipient_identity
            )
            print(f"✓ Footer sent\n")
        except Exception as e:
            print(f"✗ Failed to send footer: {e}\n")
        
        # Summary report
        print(f"\n{'='*60}")
        print(f"📊 CATALOG SEND COMPLETE")
        print(f"{'='*60}")
        print(f"✅ Sent: {sent_count}/{total_products} products")
        
        if failed_products:
            print(f"❌ Failed: {len(failed_products)} products")
            print(f"   Products that failed:")
            for name in failed_products:
                print(f"     • {name}")
        else:
            print(f"🎉 All products sent successfully!")
        
        print(f"{'='*60}\n")
    
    def create_order(self, buyer_signal_id: str, product_id: str, quantity: int, recipient_identity: Optional[str] = None, shipping_info: Optional[str] = None):
        """
        Create order with stock validation and payment info
        
        Args:
            buyer_signal_id: Buyer's Signal ID
            product_id: Product ID to order
            quantity: Quantity to order
            recipient_identity: Identity to send from (phone or username)
            shipping_info: JSON string with shipping information (name, address)
        """
        try:
            print(f"DEBUG: Creating order for {buyer_signal_id}, product {product_id}, qty {quantity}")
            
            # Find product
            product = self.product_manager.get_product_by_product_id(product_id)
            
            if not product:
                print(f"DEBUG: Product {product_id} not found")
                self.signal_handler.send_message(
                    recipient=buyer_signal_id,
                    message=f"❌ Product {product_id} not found. Type 'catalog' to see available products.",
                    sender_identity=recipient_identity
                )
                return
            
            # Check stock
            if product.stock < quantity:
                if product.stock == 0:
                    print(f"DEBUG: Product {product.name} out of stock")
                    self.signal_handler.send_message(
                        recipient=buyer_signal_id,
                        message=f"❌ {product.name} is OUT OF STOCK",
                        sender_identity=recipient_identity
                    )
                else:
                    print(f"DEBUG: Insufficient stock: requested {quantity}, available {product.stock}")
                    self.signal_handler.send_message(
                        recipient=buyer_signal_id,
                        message=f"""⚠️ STOCK LIMITATION

You requested: {quantity} units
Available: {product.stock} units

Would you like to order {product.stock} instead?
Reply "order {product_id} qty {product.stock}" to proceed.
""",
                        sender_identity=recipient_identity
                    )
                return
            
            # Calculate totals with 7% commission
            unit_price = float(product.price)
            subtotal = unit_price * quantity
            commission = subtotal * 0.07  # 7% commission
            total = subtotal + commission
            
            # Get XMR conversion using SECURE LIVE API
            try:
                total_xmr = currency_converter.fiat_to_xmr(total, product.currency)
                current_rate = currency_converter.get_xmr_price(product.currency)
                print(f"DEBUG: Exchange rate: 1 XMR = {current_rate:.2f} {product.currency}")
                print(f"DEBUG: Order total: {total} {product.currency} = {total_xmr:.6f} XMR")
                
            except ExchangeRateUnavailableError as e:
                # Exchange rate APIs are down - reject order
                print(f"ERROR: Exchange rate unavailable: {e}")
                
                # Alert seller immediately
                self.signal_handler.send_message(
                    recipient=self.seller_signal_id,
                    message=f"""🚨 CRITICAL ALERT 🚨

Exchange Rate APIs are DOWN!

A customer attempted to order but was rejected.

Customer: {buyer_signal_id}
Product: {product.name} ({product_id})
Quantity: {quantity}

Action Required:
1. Check CoinGecko API status
2. Check Kraken API status  
3. Verify internet connectivity
4. Check logs for details

The bot will NOT process orders until APIs are working.
"""
                )
                
                # Inform customer
                self.signal_handler.send_message(
                    recipient=buyer_signal_id,
                    message="""❌ Service Temporarily Unavailable

We're unable to process orders right now due to a technical issue with our exchange rate provider.

Please try again in 10-15 minutes.

We apologize for the inconvenience and appreciate your patience.
""",
                    sender_identity=recipient_identity
                )
                
                return  # Do not create order
            
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
                shipping_info=shipping_info,  # Add shipping info
                expires_at=datetime.utcnow() + timedelta(minutes=ORDER_EXPIRATION_MINUTES)
            )
            
            created_order = self.order_manager.create_order(order)
            print(f"DEBUG: Order #{created_order.order_id} created successfully")
            
            # Reduce stock (will be restored if order expires)
            product.stock -= quantity
            self.product_manager.update_product(product)
            
            # Send order confirmation with payment info
            self.send_order_confirmation(buyer_signal_id, created_order, product, payment_address, recipient_identity)
            
        except Exception as e:
            print(f"ERROR: Failed to create order: {e}")
            import traceback
            traceback.print_exc()
            self.signal_handler.send_message(
                recipient=buyer_signal_id,
                message="❌ Failed to create order. Please try again or contact support.",
                sender_identity=recipient_identity
            )
    
    def send_order_confirmation(self, buyer_signal_id: str, order: Order, product, payment_address: str, recipient_identity: Optional[str] = None):
        """
        Send order summary with payment QR code
        
        Args:
            buyer_signal_id: Buyer's Signal ID
            order: Order object
            product: Product object
            payment_address: Monero payment address
            recipient_identity: Identity to send from (phone or username)
        """
        try:
            print(f"DEBUG: Sending order confirmation to {buyer_signal_id} for order #{order.order_id}")
            
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
                
                print(f"DEBUG: QR code generated at {qr_path}")
                
                # Send message with QR code
                self.signal_handler.send_message(
                    recipient=buyer_signal_id,
                    message=message.strip(),
                    attachments=[qr_path],
                    sender_identity=recipient_identity
                )
            except Exception as e:
                print(f"ERROR: Error generating QR code: {e}")
                # Send without QR code
                self.signal_handler.send_message(
                    recipient=buyer_signal_id,
                    message=message.strip(),
                    sender_identity=recipient_identity
                )
        except Exception as e:
            print(f"ERROR: Failed to send order confirmation: {e}")
            self.signal_handler.send_message(
                recipient=buyer_signal_id,
                message="❌ Order created but failed to send confirmation. Check your orders in the dashboard.",
                sender_identity=recipient_identity
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
    
    def send_help(self, buyer_signal_id: str, recipient_identity: Optional[str] = None):
        """
        Send help message to buyer
        
        Args:
            buyer_signal_id: Buyer's Signal ID
            recipient_identity: Identity to send from (phone or username)
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
            message=help_message.strip(),
            sender_identity=recipient_identity
        )
