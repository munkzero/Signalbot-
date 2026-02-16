"""
Buyer Handler - Processes buyer commands and order creation
"""

import os
import re
import time
from typing import Optional, Tuple
from datetime import datetime, timedelta
from ..models.product import ProductManager
from ..models.order import OrderManager, Order
from ..config.settings import ORDER_EXPIRATION_MINUTES
from ..utils.qr_generator import qr_generator


# TODO: Replace with real-time exchange rate API
XMR_EXCHANGE_RATE_USD = 150.0  # Placeholder: 1 XMR = $150 USD

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
    
    def __init__(self, product_manager, order_manager, signal_handler, seller_signal_id, wallet_manager=None, seller_manager=None):
        """
        Initialize buyer handler
        
        Args:
            product_manager: ProductManager instance
            order_manager: OrderManager instance
            signal_handler: SignalHandler instance
            seller_signal_id: Seller's Signal ID
            wallet_manager: Optional WalletSetupManager for wallet operations
            seller_manager: Optional SellerManager for PIN verification
        """
        self.product_manager = product_manager
        self.order_manager = order_manager
        self.signal_handler = signal_handler
        self.seller_signal_id = seller_signal_id
        self.wallet_manager = wallet_manager
        self.seller_manager = seller_manager
        
        # Add product cache
        self.product_cache = ProductCache(product_manager, cache_duration=300)
        
        # Track pending confirmations and PIN sessions
        self.pending_confirmations = {}  # {signal_id: {'action': str, 'data': dict}}
        
        # Import PIN manager
        from .pin_manager import pin_manager
        self.pin_manager = pin_manager
    
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
        
        print(f"DEBUG: Processing buyer command: {message_text[:50]}")
        
        # Check if this is the seller sending commands (admin mode)
        is_seller = (buyer_signal_id == self.seller_signal_id)
        
        # Handle pending confirmations (e.g., for new wallet creation)
        if buyer_signal_id in self.pending_confirmations:
            self._handle_confirmation(buyer_signal_id, message_text)
            return
        
        # Handle PIN entry for active sessions
        if self.pin_manager.has_active_session(buyer_signal_id):
            self._handle_pin_entry(buyer_signal_id, message_text)
            return
        
        # Seller-only commands
        if is_seller:
            # Command: "settings" or "menu"
            if message_lower in ['settings', 'menu', 'admin']:
                self.send_settings_menu(buyer_signal_id)
                return
            
            # Command: "new wallet"
            if 'new wallet' in message_lower or message_lower == 'create wallet':
                self.request_new_wallet(buyer_signal_id)
                return
            
            # Command: "send [amount] to [address]" or "send [amount] xmr to [address]"
            send_match = self._parse_send_command(message_text)
            if send_match:
                amount, address = send_match
                self.request_send_transaction(buyer_signal_id, amount, address)
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
            self.send_catalog(buyer_signal_id)
            return
        
        # Command: "order #1 qty 5" or "buy #2 qty 3"
        order_match = self._parse_order_command(message_text)
        if order_match:
            product_id, quantity = order_match
            print(f"DEBUG: Creating order for product {product_id} qty {quantity}")
            self.create_order(buyer_signal_id, product_id, quantity)
            return
        
        # Command: "help"
        if 'help' in message_lower:
            print(f"DEBUG: Sending help to {buyer_signal_id}")
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
    
    def _parse_send_command(self, message: str) -> Optional[Tuple[float, str]]:
        """
        Parse send transaction commands:
        - "send 1.5 to 4..."
        - "send 0.5 xmr to 4..."
        - "transfer 2 to 4..."
        
        Args:
            message: Message text to parse
            
        Returns:
            Tuple of (amount, address) or None
        """
        import re
        
        # Pattern: "send/transfer [amount] (xmr) to [address]"
        pattern = r'(send|transfer)\s+([\d.]+)\s*(?:xmr)?\s+to\s+([a-zA-Z0-9]+)'
        match = re.search(pattern, message.lower())
        
        if match:
            try:
                amount = float(match.group(2))
                address = match.group(3)
                return (amount, address)
            except ValueError:
                return None
        
        return None
    
    def _handle_confirmation(self, signal_id: str, message: str):
        """
        Handle confirmation responses (yes/no)
        
        Args:
            signal_id: User's Signal ID
            message: User's response
        """
        message_lower = message.lower().strip()
        confirmation = self.pending_confirmations[signal_id]
        action = confirmation['action']
        
        # Clear confirmation
        del self.pending_confirmations[signal_id]
        
        if message_lower in ['yes', 'y', 'confirm']:
            # User confirmed
            if action == 'new_wallet':
                self._execute_new_wallet(signal_id)
            else:
                self.signal_handler.send_message(
                    recipient=signal_id,
                    message="Unknown action. Operation cancelled."
                )
        else:
            # User declined or invalid response
            self.signal_handler.send_message(
                recipient=signal_id,
                message="Operation cancelled."
            )
    
    def _handle_pin_entry(self, signal_id: str, pin: str):
        """
        Handle PIN entry for transaction authorization
        
        Args:
            signal_id: User's Signal ID
            pin: Entered PIN
        """
        session = self.pin_manager.get_session(signal_id)
        
        if session is None:
            self.signal_handler.send_message(
                recipient=signal_id,
                message="⏱️ PIN entry timed out. Please try again."
            )
            return
        
        # Verify PIN
        if self.seller_manager is None:
            self.signal_handler.send_message(
                recipient=signal_id,
                message="❌ PIN verification not available."
            )
            self.pin_manager.clear_session(signal_id)
            return
        
        # Get seller ID (default to 1)
        is_valid = self.seller_manager.verify_pin(1, pin.strip())
        
        if is_valid:
            # PIN correct - execute the action
            action = session.action
            data = session.data
            
            # Clear session
            self.pin_manager.clear_session(signal_id)
            
            if action == 'send_transaction':
                self._execute_send_transaction(
                    signal_id,
                    data.get('amount'),
                    data.get('address')
                )
            else:
                self.signal_handler.send_message(
                    recipient=signal_id,
                    message="✅ PIN verified, but action not implemented."
                )
        else:
            # PIN incorrect
            self.pin_manager.clear_session(signal_id)
            self.signal_handler.send_message(
                recipient=signal_id,
                message="❌ Incorrect PIN. Transaction cancelled."
            )
    
    def send_catalog(self, buyer_signal_id: str):
        """
        Send catalog to buyer with robust error handling
        
        Args:
            buyer_signal_id: Buyer's Signal ID
        """
        
        products = self.product_cache.get_products(active_only=True)
        
        if not products:
            self.signal_handler.send_message(
                recipient=buyer_signal_id,
                message="Sorry, no products are currently available."
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
                message=header
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
                        attachments=attachments if attachments else None
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
                            attachments=None  # No image
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
                message=footer
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
    
    def create_order(self, buyer_signal_id: str, product_id: str, quantity: int):
        """
        Create order with stock validation and payment info
        
        Args:
            buyer_signal_id: Buyer's Signal ID
            product_id: Product ID to order
            quantity: Quantity to order
        """
        try:
            print(f"DEBUG: Creating order for {buyer_signal_id}, product {product_id}, qty {quantity}")
            
            # Find product
            product = self.product_manager.get_product_by_product_id(product_id)
            
            if not product:
                print(f"DEBUG: Product {product_id} not found")
                self.signal_handler.send_message(
                    recipient=buyer_signal_id,
                    message=f"❌ Product {product_id} not found. Type 'catalog' to see available products."
                )
                return
            
            # Check stock
            if product.stock < quantity:
                if product.stock == 0:
                    print(f"DEBUG: Product {product.name} out of stock")
                    self.signal_handler.send_message(
                        recipient=buyer_signal_id,
                        message=f"❌ {product.name} is OUT OF STOCK"
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
            
            print(f"DEBUG: Order total: {total} {product.currency} = {total_xmr:.6f} XMR")
            
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
            print(f"DEBUG: Order #{created_order.order_id} created successfully")
            
            # Reduce stock (will be restored if order expires)
            product.stock -= quantity
            self.product_manager.update_product(product)
            
            # Send order confirmation with payment info
            self.send_order_confirmation(buyer_signal_id, created_order, product, payment_address)
        except Exception as e:
            print(f"ERROR: Failed to create order: {e}")
            self.signal_handler.send_message(
                recipient=buyer_signal_id,
                message="❌ Failed to create order. Please try again or contact support."
            )
    
    def send_order_confirmation(self, buyer_signal_id: str, order: Order, product, payment_address: str):
        """
        Send order summary with payment QR code
        
        Args:
            buyer_signal_id: Buyer's Signal ID
            order: Order object
            product: Product object
            payment_address: Monero payment address
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
                    attachments=[qr_path]
                )
            except Exception as e:
                print(f"ERROR: Error generating QR code: {e}")
                # Send without QR code
                self.signal_handler.send_message(
                    recipient=buyer_signal_id,
                    message=message.strip()
                )
        except Exception as e:
            print(f"ERROR: Failed to send order confirmation: {e}")
            self.signal_handler.send_message(
                recipient=buyer_signal_id,
                message="❌ Order created but failed to send confirmation. Check your orders in the dashboard."
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
    
    def send_settings_menu(self, signal_id: str):
        """
        Send settings/admin menu to seller
        
        Args:
            signal_id: Seller's Signal ID
        """
        settings_message = """⚙️ SETTINGS MENU
        
🔧 Wallet Management:
  • "new wallet" - Create a new wallet (backs up current wallet)

💸 Send Transactions:
  • "send [amount] to [address]" - Send XMR (requires PIN)
  • Example: "send 1.5 to 4ABC..."

📋 Catalog Management:
  • "catalog" - View your products

❓ Help:
  • "help" - Show buyer help
"""
        
        self.signal_handler.send_message(
            recipient=signal_id,
            message=settings_message.strip()
        )
    
    def request_new_wallet(self, signal_id: str):
        """
        Request confirmation for creating a new wallet
        
        Args:
            signal_id: Seller's Signal ID
        """
        if self.wallet_manager is None:
            self.signal_handler.send_message(
                recipient=signal_id,
                message="❌ Wallet management not available."
            )
            return
        
        # Store pending confirmation
        self.pending_confirmations[signal_id] = {
            'action': 'new_wallet',
            'data': {}
        }
        
        confirmation_message = """⚠️ CREATE NEW WALLET

Are you sure you want to create a new wallet?

This will:
✓ Backup your current wallet with timestamp
✓ Create a new empty wallet
✓ Generate a new seed phrase (SAVE IT!)

Your current wallet will be safely backed up.

Reply 'yes' to continue or 'no' to cancel."""
        
        self.signal_handler.send_message(
            recipient=signal_id,
            message=confirmation_message
        )
    
    def _execute_new_wallet(self, signal_id: str):
        """
        Execute new wallet creation with backup
        
        Args:
            signal_id: Seller's Signal ID
        """
        if self.wallet_manager is None:
            self.signal_handler.send_message(
                recipient=signal_id,
                message="❌ Wallet management not available."
            )
            return
        
        # Stop RPC if running
        if self.wallet_manager.is_rpc_running():
            self.signal_handler.send_message(
                recipient=signal_id,
                message="🛑 Stopping wallet RPC..."
            )
            self.wallet_manager.stop_rpc()
            time.sleep(2)
        
        # Create new wallet with backup
        self.signal_handler.send_message(
            recipient=signal_id,
            message="🔄 Creating new wallet..."
        )
        
        success, address, seed, backup_path = self.wallet_manager.create_new_wallet_with_backup()
        
        if success:
            message = "✅ NEW WALLET CREATED\n\n"
            
            if backup_path:
                message += f"💾 Old wallet backed up to:\n{backup_path}\n\n"
            
            if address:
                message += f"📍 Address:\n{address}\n\n"
            
            if seed:
                message += f"🔑 SEED PHRASE (SAVE THIS!):\n{seed}\n\n"
                message += "⚠️ Write down your seed phrase and store it safely!\n"
                message += "This is the ONLY way to recover your wallet!\n\n"
            
            # Restart RPC
            message += "🔌 Starting wallet RPC..."
            self.signal_handler.send_message(
                recipient=signal_id,
                message=message
            )
            
            if self.wallet_manager.start_rpc():
                self.signal_handler.send_message(
                    recipient=signal_id,
                    message="✅ Wallet RPC started successfully!"
                )
            else:
                self.signal_handler.send_message(
                    recipient=signal_id,
                    message="⚠️ Failed to start wallet RPC. Please restart manually."
                )
        else:
            self.signal_handler.send_message(
                recipient=signal_id,
                message="❌ Failed to create new wallet. Check logs for details."
            )
    
    def request_send_transaction(self, signal_id: str, amount: float, address: str):
        """
        Request PIN for sending transaction
        
        Args:
            signal_id: Seller's Signal ID
            amount: Amount to send in XMR
            address: Destination address
        """
        if self.seller_manager is None:
            self.signal_handler.send_message(
                recipient=signal_id,
                message="❌ Transaction authorization not available."
            )
            return
        
        # Create PIN verification session
        session = self.pin_manager.create_session(
            user_id=signal_id,
            action='send_transaction',
            timeout_seconds=60,
            amount=amount,
            address=address
        )
        
        message = f"""🔐 TRANSACTION AUTHORIZATION

Amount: {amount} XMR
To: {address}

Enter your PIN to authorize this transaction.

⏱️ You have {session.timeout_seconds} seconds to enter your PIN."""
        
        self.signal_handler.send_message(
            recipient=signal_id,
            message=message
        )
    
    def _execute_send_transaction(self, signal_id: str, amount: float, address: str):
        """
        Execute send transaction after PIN verification
        
        Args:
            signal_id: Seller's Signal ID
            amount: Amount to send in XMR
            address: Destination address
        """
        if self.wallet_manager is None:
            self.signal_handler.send_message(
                recipient=signal_id,
                message="❌ Wallet not available."
            )
            return
        
        # Check if RPC is running
        if not self.wallet_manager.is_rpc_running():
            self.signal_handler.send_message(
                recipient=signal_id,
                message="❌ Wallet RPC is not running. Please start it first."
            )
            return
        
        self.signal_handler.send_message(
            recipient=signal_id,
            message=f"📤 Sending {amount} XMR to {address}..."
        )
        
        try:
            # Send transaction via RPC
            import requests
            
            rpc_url = f'http://127.0.0.1:{self.wallet_manager.rpc_port}/json_rpc'
            
            # Convert XMR to atomic units (1 XMR = 1e12 atomic units)
            amount_atomic = int(amount * 1e12)
            
            payload = {
                "jsonrpc": "2.0",
                "id": "0",
                "method": "transfer",
                "params": {
                    "destinations": [{"amount": amount_atomic, "address": address}],
                    "priority": 2,  # Normal priority
                    "get_tx_key": True
                }
            }
            
            response = requests.post(rpc_url, json=payload, timeout=30)
            result = response.json()
            
            if 'result' in result:
                tx_hash = result['result'].get('tx_hash', 'unknown')
                tx_key = result['result'].get('tx_key', 'unknown')
                
                success_message = f"""✅ TRANSACTION SENT

Amount: {amount} XMR
To: {address}
TX Hash: {tx_hash}
TX Key: {tx_key}

Transaction submitted successfully!"""
                
                self.signal_handler.send_message(
                    recipient=signal_id,
                    message=success_message
                )
            else:
                error = result.get('error', {}).get('message', 'Unknown error')
                self.signal_handler.send_message(
                    recipient=signal_id,
                    message=f"❌ Transaction failed: {error}"
                )
                
        except Exception as e:
            self.signal_handler.send_message(
                recipient=signal_id,
                message=f"❌ Error sending transaction: {str(e)}"
            )
