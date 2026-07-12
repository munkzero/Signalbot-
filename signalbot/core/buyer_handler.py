"""
Buyer Handler - Processes buyer commands and order creation
"""

import os
import re
import time
import threading
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

# Minimum character length for a valid shipping address
MIN_ADDRESS_LENGTH = 10

# Words that are not valid shipping addresses (single-word replies to dismiss)
INVALID_ADDRESS_WORDS = frozenset({'ok', 'yes', 'no', 'test', 'hi', 'hello', 'thanks'})

# Common image directories to search for product images (in order of priority)
COMMON_IMAGE_SEARCH_DIRS = [
    'data/products/images',
    'data/images',
    'data/product_images',
    'images',
    '.',
]


class ProductCache:
    """Cache for product data to reduce database queries"""
    
    def __init__(self, product_manager, cache_duration: int = 60):
        """
        Initialize product cache
        
        Args:
            product_manager: ProductManager instance
            cache_duration: Cache lifetime in seconds (default 1 minute)
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
    
    def __init__(self, product_manager, order_manager, signal_handler, seller_signal_id, wallet=None):
        """
        Initialize buyer handler
        
        Args:
            product_manager: ProductManager instance
            order_manager: OrderManager instance
            signal_handler: SignalHandler instance
            seller_signal_id: Seller's Signal ID
            wallet: Optional MoneroWallet or InHouseWallet instance for subaddress generation
        """
        self.product_manager = product_manager
        self.order_manager = order_manager
        self.signal_handler = signal_handler
        self.seller_signal_id = seller_signal_id
        self.wallet = wallet
        
        # Add product cache (1-minute cache for fresher stock data)
        self.product_cache = ProductCache(product_manager, cache_duration=60)
        
        # Conversation state tracking for order flow
        self.conversation_states = {}
        
        # Pre-optimize all product images in background so bot starts immediately
        threading.Thread(target=self._optimize_images_background, daemon=True).start()
    
    def _optimize_images_background(self):
        """Optimize product images in a background thread so bot starts immediately."""
        try:
            print("🔧 Pre-optimizing product images in background...")
            from ..utils.image_optimizer import optimize_image
            products = self.product_cache.get_products(active_only=True)
            optimized_count = 0
            for product in products:
                if product.image_path and os.path.exists(product.image_path):
                    optimize_image(product.image_path)
                    optimized_count += 1
            print(f"✓ {optimized_count} product images optimized and ready")
        except Exception as e:
            print(f"⚠️ Background image optimization error: {e}")

    @staticmethod
    def _format_product_id(product_id: Optional[str]) -> str:
        """Format product ID consistently"""
        if not product_id:
            return "N/A"
        if not product_id.startswith('#'):
            return f"#{product_id}"
        return product_id
    
    def _resolve_image_path(self, image_path: str) -> Optional[str]:
        """Resolve image path by checking multiple common locations."""
        if not image_path:
            return None
        
        if os.path.isabs(image_path):
            if os.path.exists(image_path) and os.path.isfile(image_path):
                return image_path
            else:
                print(f"  Absolute path doesn't exist: {image_path}")
                return None
        
        base_dir = os.getcwd()
        
        for search_dir in COMMON_IMAGE_SEARCH_DIRS:
            full_path = os.path.join(base_dir, search_dir, image_path)
            
            if os.path.exists(full_path) and os.path.isfile(full_path):
                print(f"  ✓ Found image: {full_path}")
                return full_path
        
        print(f"  ✗ Image not found in any common directory: {image_path}")
        print(f"    Searched: {', '.join(COMMON_IMAGE_SEARCH_DIRS)}")
        return None
    
    def _optimize_image_for_signal(self, image_path: str, max_size_kb: int = 800) -> str:
        """Optimize image for Signal sending - compress and resize if needed."""
        try:
            from PIL import Image
            import tempfile
            
            file_size_kb = os.path.getsize(image_path) / 1024
            file_ext = os.path.splitext(image_path)[1].lower()
            
            print(f"  📊 Original: {file_size_kb:.1f}KB, Format: {file_ext}")
            
            if file_size_kb <= max_size_kb and file_ext in ['.jpg', '.jpeg']:
                print(f"  ✓ Image already optimized")
                return image_path
            
            img = Image.open(image_path)
            
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            max_dimension = 1920
            if img.width > max_dimension or img.height > max_dimension:
                ratio = max_dimension / max(img.width, img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                print(f"  📐 Resized to: {new_size[0]}x{new_size[1]}")
            
            optimized_path = os.path.join(
                tempfile.gettempdir(),
                f"signal_opt_{os.path.basename(image_path).rsplit('.', 1)[0]}.jpg"
            )
            
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
            return image_path
        except Exception as e:
            print(f"  ⚠️  Image optimization failed: {e}")
            return image_path
    
    def handle_buyer_message(self, buyer_signal_id: str, message_text: str, recipient_identity: Optional[str] = None):
        """Parse buyer commands and execute actions"""
        print(f"BUYER_HANDLER: Received message from {buyer_signal_id}")
        if not message_text:
            return
        
        if not recipient_identity:
            recipient_identity = self.seller_signal_id
        
        message_lower = message_text.lower().strip()
        print(f"DEBUG: Processing buyer command: {message_text[:50]}")
        
        # Check if user is in a conversation flow
        if buyer_signal_id in self.conversation_states:
            state_info = self.conversation_states[buyer_signal_id]
            # Enforce 10-minute timeout on pending conversation states
            if time.time() - state_info.get('started_at', 0) > 600:
                del self.conversation_states[buyer_signal_id]
                self.signal_handler.send_message(
                    recipient=buyer_signal_id,
                    message="⏰ Your order request has expired. Please start a new order.",
                    sender_identity=recipient_identity
                )
                return
            self._handle_conversation_state(buyer_signal_id, message_text, recipient_identity)
            return
        
        # Catalog command
        catalog_keywords = ['catalog', 'catalogue', 'menu']
        catalog_phrases = ['show products', 'show catalog', 'show catalogue', 'show menu', 'view products', 'view catalog']
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
        
        # Order command
        order_match = self._parse_order_command(message_text)
        if order_match:
            product_id, quantity = order_match
            print(f"DEBUG: Initiating order conversation for product {product_id} qty {quantity}")
            self._initiate_order_conversation(buyer_signal_id, product_id, quantity, recipient_identity)
            return
        
        # Help command
        if 'help' in message_lower:
            print(f"DEBUG: Sending help to {buyer_signal_id}")
            self.send_help(buyer_signal_id, recipient_identity)
            return
        
        # Status command
        if 'status' in message_lower:
            print(f"DEBUG: Sending order status to {buyer_signal_id}")
            self.send_order_status(buyer_signal_id, recipient_identity)
            return
    
    def _initiate_order_conversation(self, buyer_signal_id: str, product_id: str, quantity: int, recipient_identity: Optional[str] = None):
        """Start the order conversation flow by asking for delivery address."""
        self.conversation_states[buyer_signal_id] = {
            'state': 'awaiting_address',
            'product_id': product_id,
            'quantity': quantity,
            'recipient_identity': recipient_identity,
            'started_at': time.time()
        }
        
        self.signal_handler.send_message(
            recipient=buyer_signal_id,
            message="📍 Please send your delivery address:\n(Include full address with street, city, and postal code)",
            sender_identity=recipient_identity
        )
        print(f"DEBUG: Waiting for delivery address from {buyer_signal_id}")
    
    def _handle_conversation_state(self, buyer_signal_id: str, message_text: str, recipient_identity: Optional[str] = None):
        """Handle conversation state for collecting shipping information"""
        state_info = self.conversation_states[buyer_signal_id]
        current_state = state_info['state']
        
        # Check 10-minute timeout
        if time.time() - state_info.get('started_at', 0) > 600:
            del self.conversation_states[buyer_signal_id]
            self.signal_handler.send_message(
                recipient=buyer_signal_id,
                message="⏰ Your order request has expired. Please start a new order.",
                sender_identity=recipient_identity
            )
            return
        
        if current_state == 'awaiting_address':
            address = message_text.strip()
            
            # Validate address before accepting
            if not self._validate_address(address):
                self.signal_handler.send_message(
                    recipient=buyer_signal_id,
                    message="❌ Please provide a complete address (street, city, postal code)",
                    sender_identity=recipient_identity
                )
                return
            
            state_info['address'] = address
            
            # Acknowledge receipt before creating order
            self.signal_handler.send_message(
                recipient=buyer_signal_id,
                message="✅ Address received! Creating order...",
                sender_identity=recipient_identity
            )
            
            # Create the order with shipping info
            self._create_order_with_shipping_info(
                buyer_signal_id,
                state_info['product_id'],
                state_info['quantity'],
                state_info['address'],
                state_info.get('recipient_identity', recipient_identity)
            )
            
            # Clear conversation state
            del self.conversation_states[buyer_signal_id]
            print(f"DEBUG: Order creation completed for {buyer_signal_id}")

    def _validate_address(self, address: str) -> bool:
        """Validate a shipping address."""
        stripped = address.strip()
        if len(stripped) < MIN_ADDRESS_LENGTH:
            return False
        if stripped.lower() in INVALID_ADDRESS_WORDS:
            return False
        return True

    def _create_order_with_shipping_info(self, buyer_signal_id: str, product_id: str, quantity: int, 
                                         address: str, recipient_identity: Optional[str] = None):
        """Create order with collected shipping information"""
        import json
        
        shipping_info = json.dumps({'address': address})
        self.create_order(buyer_signal_id, product_id, quantity, recipient_identity, shipping_info=shipping_info)
    
    def _parse_order_command(self, message: str) -> Optional[Tuple[str, int]]:
        """Parse order commands"""
        pattern = r'(order|buy)\s+(#?[\w-]+)\s+qty\s+(\d+)'
        match = re.search(pattern, message.lower())
        
        if match:
            product_id = match.group(2)
            if not product_id.startswith('#'):
                product_id = '#' + product_id
            quantity = int(match.group(3))
            return (product_id, quantity)
        
        pattern = r'(order|buy)\s+(#?[\w-]+)'
        match = re.search(pattern, message.lower())
        
        if match:
            product_id = match.group(2)
            if not product_id.startswith('#'):
                product_id = '#' + product_id
            return (product_id, 1)
        
        return None
    
    def send_catalog(self, buyer_signal_id: str, recipient_identity: Optional[str] = None):
        """Send catalog to buyer using parallel native sends for speed."""
        from concurrent.futures import ThreadPoolExecutor, wait as futures_wait
        from ..utils.image_optimizer import optimize_image

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
        print(f"📦 SENDING CATALOG: {total_products} products (PARALLEL MODE)")
        print(f"{'='*60}\n")

        # Send catalog header immediately
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

        # Prepare and submit all product sends in parallel
        send_tasks = []
        task_meta = []

        executor = ThreadPoolExecutor(max_workers=5)
        try:
            for index, product in enumerate(products, 1):
                product_id_str = self._format_product_id(product.product_id)
                print(f"📦 Queuing product {index}/{total_products}: {product.name} ({product_id_str})")

                full_message = (
                    f"━━━━━━━━━━━━━━━━━\n"
                    f"{product_id_str} - {product.name}\n"
                    f"━━━━━━━━━━━━━━━━━\n"
                    f"{product.description}\n\n"
                    f"💰 Price: {product.price} {product.currency}\n"
                    f"📊 Stock: {product.stock} available\n"
                    f"🏷️ Category: {product.category or 'N/A'}\n\n"
                    f"To order: \"order {product_id_str} qty [amount]\""
                )

                attachments = []
                if product.image_path:
                    resolved_path = self._resolve_image_path(product.image_path)
                    if resolved_path:
                        optimized_path = optimize_image(resolved_path)
                        attachments.append(optimized_path)

                send_tasks.append(
                    executor.submit(
                        self.signal_handler.send_message_native,
                        buyer_signal_id,
                        full_message,
                        attachments if attachments else None
                    )
                )
                task_meta.append((full_message, attachments))

            print(f"\n⚡ Waiting for {len(send_tasks)} parallel sends (max 30s)...")
            futures_wait(send_tasks, timeout=30)
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        # Retry failed tasks as text-only fallback
        sent_count = 0
        for task, (msg, att) in zip(send_tasks, task_meta):
            succeeded = False
            if task.done():
                try:
                    succeeded = task.result(timeout=0) is True
                except Exception:
                    pass

            if succeeded:
                sent_count += 1
            else:
                print(f"  📝 Attempting text-only fallback (no image)...")
                try:
                    result = self.signal_handler.send_message_native(
                        buyer_signal_id,
                        msg,
                        attachments=None
                    )
                    if result:
                        print(f"  ✅ Text-only fallback sent successfully")
                        sent_count += 1
                except Exception as e:
                    print(f"  ✗ Text-only fallback error: {e}")

        failed_count = total_products - sent_count

        # ===== SEND INSTRUCTIONS FOOTER WITH COMPREHENSIVE ERROR HANDLING =====
        instructions = """✨ CATALOG COMPLETE ✨

📋 HOW TO ORDER:
Reply with: order #1 qty 2
(replace #1 with product number, 2 with quantity)

💳 AFTER YOU ORDER:
• You get payment address & QR code
• Send XMR amount to address
• We'll ship when paid

❓ CHECK ORDER STATUS:
Reply: "status" to see your order info

Need help? Reply: help"""
        
        sent_footer = False
        footer_error = None
        
        print(f"\n📝 Attempting to send order instructions (footer)...")
        
        # Attempt #1: Direct send_message_native with error details
        try:
            print(f"   [Attempt 1] Using send_message_native()...")
            result = self.signal_handler.send_message_native(
                recipient=buyer_signal_id,
                message=instructions.strip()
            )
            if result:
                print(f"✅ Footer sent successfully (send_message_native)\n")
                sent_footer = True
            else:
                footer_error = "send_message_native() returned False/None"
                print(f"   [Attempt 1 FAILED] {footer_error}\n")
        except Exception as e1:
            footer_error = str(e1)
            print(f"   [Attempt 1 FAILED] Exception: {e1}\n")
        
        # Attempt #2: Try again with explicit recipient handling
        if not sent_footer:
            try:
                print(f"   [Attempt 2] Retry with explicit recipient: {buyer_signal_id}")
                recipient = buyer_signal_id if buyer_signal_id.startswith(('+', '@')) else buyer_signal_id
                result = self.signal_handler.send_message_native(
                    recipient=recipient,
                    message=instructions.strip()
                )
                if result:
                    print(f"✅ Footer sent successfully (retry with explicit recipient)\n")
                    sent_footer = True
                else:
                    print(f"   [Attempt 2 FAILED] send_message_native() returned False/None\n")
            except Exception as e2:
                print(f"   [Attempt 2 FAILED] Exception: {e2}\n")
        
        # Attempt #3: Try sending in smaller chunks
        if not sent_footer:
            try:
                print(f"   [Attempt 3] Sending in two chunks (might be too long)...")
                
                chunk1 = "✨ CATALOG COMPLETE ✨\n\n📋 HOW TO ORDER:\nReply with: order #1 qty 2"
                chunk2 = "💳 AFTER YOU ORDER:\n• You get payment address & QR code\n• Send XMR amount to address\n• We'll ship when paid\n\n❓ CHECK ORDER STATUS:\nReply: \"status\"\n\nNeed help? Reply: help"
                
                result1 = self.signal_handler.send_message_native(
                    recipient=buyer_signal_id,
                    message=chunk1
                )
                time.sleep(0.5)
                result2 = self.signal_handler.send_message_native(
                    recipient=buyer_signal_id,
                    message=chunk2
                )
                
                if result1 and result2:
                    print(f"✅ Footer sent successfully (as two chunks)\n")
                    sent_footer = True
                else:
                    print(f"   [Attempt 3 FAILED] One or both chunks failed\n")
            except Exception as e3:
                print(f"   [Attempt 3 FAILED] Exception: {e3}\n")
        
        # Attempt #4: Emergency fallback
        if not sent_footer:
            try:
                print(f"   [Attempt 4] Emergency fallback - essentials only...")
                minimal = "✨ CATALOG COMPLETE ✨\nReply: order #1 qty 2\nReply: status\nReply: help"
                result = self.signal_handler.send_message_native(
                    recipient=buyer_signal_id,
                    message=minimal
                )
                if result:
                    print(f"✅ Footer sent successfully (emergency fallback)\n")
                    sent_footer = True
                else:
                    print(f"   [Attempt 4 FAILED] Emergency fallback also failed\n")
            except Exception as e4:
                print(f"   [Attempt 4 FAILED] Exception: {e4}\n")

        # Summary report
        print(f"\n{'='*60}")
        print(f"📊 CATALOG SEND COMPLETE")
        print(f"{'='*60}")
        print(f"✅ Products sent: {sent_count}/{total_products}")
        if failed_count:
            print(f"⚠️ Failed: {failed_count}")
        print(f"✅ Footer sent: {'YES' if sent_footer else 'NO - ALL ATTEMPTS FAILED'}")
        if not sent_footer and footer_error:
            print(f"❌ Last error: {footer_error}")
        print(f"{'='*60}\n")
    
    def create_order(self, buyer_signal_id: str, product_id: str, quantity: int, recipient_identity: Optional[str] = None, shipping_info: Optional[str] = None):
        """Create order with stock validation and payment info"""
        try:
            print(f"DEBUG: Creating order for {buyer_signal_id}, product {product_id}, qty {quantity}")
            
            product = self.product_manager.get_product_by_product_id(product_id)
            
            if not product:
                print(f"DEBUG: Product {product_id} not found")
                self.signal_handler.send_message(
                    recipient=buyer_signal_id,
                    message=f"❌ Product {product_id} not found. Type 'catalog' to see available products.",
                    sender_identity=recipient_identity
                )
                return
            
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
            
            unit_price = float(product.price)
            subtotal = unit_price * quantity
            commission = subtotal * 0.07
            total = subtotal + commission
            
            try:
                total_xmr = currency_converter.fiat_to_xmr(total, product.currency)
                current_rate = currency_converter.get_xmr_price(product.currency)
                print(f"DEBUG: Exchange rate: 1 XMR = {current_rate:.2f} {product.currency}")
                print(f"DEBUG: Order total: {total} {product.currency} = {total_xmr:.6f} XMR")
                
            except ExchangeRateUnavailableError as e:
                print(f"ERROR: Exchange rate unavailable: {e}")
                
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
                
                self.signal_handler.send_message(
                    recipient=buyer_signal_id,
                    message="""❌ Service Temporarily Unavailable

We're unable to process orders right now due to a technical issue with our exchange rate provider.

Please try again in 10-15 minutes.

We apologize for the inconvenience and appreciate your patience.
""",
                    sender_identity=recipient_identity
                )
                
                return
            
            order_id = Order._generate_order_id()
            try:
                payment_address = self._generate_payment_address(product.id, buyer_signal_id, order_id=order_id)
            except RuntimeError as addr_err:
                print(f"ERROR: {addr_err}")
                self.signal_handler.send_message(
                    recipient=buyer_signal_id,
                    message=(
                        "❌ Unable to process your order right now — "
                        "the payment system is temporarily unavailable.\n\n"
                        "Please try again later or contact support."
                    ),
                    sender_identity=recipient_identity
                )
                return
            
            order = Order(
                order_id=order_id,
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
                commission_amount=commission * total_xmr / total,
                seller_amount=subtotal * total_xmr / total,
                shipping_info=shipping_info,
                expires_at=datetime.utcnow() + timedelta(minutes=ORDER_EXPIRATION_MINUTES)
            )
            
            created_order = self.order_manager.create_order(order)
            print(f"DEBUG: Order #{created_order.order_id} created successfully")
            
            product.stock -= quantity
            self.product_manager.update_product(product)
            
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
        """Send order summary with payment QR code"""
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
            
            try:
                qr_data = qr_generator.generate_payment_qr(payment_address, order.price_xmr)
                qr_path = f"/tmp/order_{order.order_id}_qr.png"
                
                with open(qr_path, 'wb') as f:
                    f.write(qr_data)
                
                print(f"DEBUG: QR code generated at {qr_path}")
                
                self.signal_handler.send_message(
                    recipient=buyer_signal_id,
                    message=message.strip(),
                    attachments=[qr_path],
                    sender_identity=recipient_identity
                )
            except Exception as e:
                print(f"ERROR: Error generating QR code: {e}")
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
    
    def _generate_payment_address(self, product_id: int, buyer_signal_id: str, order_id: str = None) -> str:
        """Generate a unique Monero sub-address for an order using the connected wallet."""
        if self.wallet:
            label = f"Order-{order_id}" if order_id else f"Product-{product_id}"
            try:
                subaddr_info = self.wallet.create_subaddress(label=label)
                address = subaddr_info.get('address', '')
                if address:
                    print(f"DEBUG: Generated payment subaddress for order {order_id}: {address[:20]}...")
                    return address
                else:
                    print(f"ERROR: create_subaddress() returned no address for order {order_id}: {subaddr_info}")
            except Exception as subaddr_err:
                print(f"ERROR: Could not create subaddress for order {order_id} ({subaddr_err}); wallet may not be ready")

        raise RuntimeError(
            "Wallet not connected — cannot generate a payment address. "
            "Please configure and connect your Monero wallet in the Wallet tab."
        )
    
    def send_order_status(self, buyer_signal_id: str, recipient_identity: Optional[str] = None):
        """Send order status summary to buyer."""
        try:
            orders = self.order_manager.get_orders_by_customer(buyer_signal_id)
        except Exception as e:
            print(f"ERROR: Failed to fetch orders for {buyer_signal_id}: {e}")
            self.signal_handler.send_message(
                recipient=buyer_signal_id,
                message="❌ Unable to retrieve your orders. Please try again later.",
                sender_identity=recipient_identity
            )
            return

        if not orders:
            self.signal_handler.send_message(
                recipient=buyer_signal_id,
                message="📭 No orders found for your account.",
                sender_identity=recipient_identity
            )
            return

        status_badges = {
            'pending': '🟡',
            'processing': '🟡',
            'shipped': '🟢',
            'cancelled': '🔴',
            'completed': '✅',
            'expired': '⌛',
        }

        lines = ["📋 YOUR ORDERS\n"]
        for order in orders:
            badge = status_badges.get(order.order_status, '❓')
            lines.append(
                f"{badge} Order #{order.order_id}\n"
                f"   📦 {order.product_name} × {order.quantity}\n"
                f"   💰 {order.price_xmr:.6f} XMR\n"
                f"   Status: {order.order_status.capitalize()}\n"
            )

        self.signal_handler.send_message(
            recipient=buyer_signal_id,
            message="\n".join(lines).strip(),
            sender_identity=recipient_identity
        )

    def send_help(self, buyer_signal_id: str, recipient_identity: Optional[str] = None):
        """Send help message to buyer"""
        help_message = """🤖 BUYER COMMANDS

📋 View Products:
  • "catalog" or "products" - See all available products

🛒 Place Order:
  • "order #1 qty 5" - Order 5 units of product #1
  • "buy #2" - Order 1 unit of product #2
  • "order SKU-001 qty 3" - Order using SKU

📊 Check Orders:
  • "status" - See your current orders and their status

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
