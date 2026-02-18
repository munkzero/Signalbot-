"""
Signal messaging handler
Manages Signal messaging integration for buyer-seller communication
"""

from typing import Optional, Callable, Dict, List
import subprocess
import json
import threading
import time
import os
import re


class SignalHandler:
    """
    Handles Signal messaging for the shop bot
    Note: Requires signal-cli to be installed and configured
    """
    
    def __init__(self, phone_number: Optional[str] = None):
        """
        Initialize Signal handler
        
        Args:
            phone_number: Seller's Signal phone number (if not provided, reads from environment)
        """
        # Get phone number from parameter or environment
        self.phone_number = phone_number or os.getenv('PHONE_NUMBER') or os.getenv('SIGNAL_USERNAME')
        
        if not self.phone_number:
            raise ValueError(
                "Phone number not configured! "
                "Run './setup.sh' to configure your Signal number, "
                "or set PHONE_NUMBER in .env file."
            )
        
        # Validate format
        if not self.phone_number.startswith('+'):
            raise ValueError(
                f"Invalid phone number format: {self.phone_number}\n"
                "Must start with '+' (e.g., +64274757293)"
            )
        
        self.message_callbacks = []
        self.buyer_handler = None  # Will be set by dashboard
        self.listening = False
        self.listen_thread = None
        self.trusted_contacts = set()  # Track already-trusted contacts to avoid redundant calls
        self._trust_attempted = set()  # Cache of contacts we've attempted to trust
        
        print(f"DEBUG: SignalHandler initialized with phone_number={self.phone_number}")
        
        # Verify auto-trust is working
        self._verify_auto_trust_config()
    
    @staticmethod
    def _is_uuid(identifier: str) -> bool:
        """
        Check if a string is a valid UUID format
        
        Args:
            identifier: String to check
            
        Returns:
            True if the string matches UUID format (8-4-4-4-12 hex digits)
        """
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        return bool(uuid_pattern.match(identifier))
    
    def link_device(self) -> str:
        """
        Generate linking URI for Signal account
        
        Returns:
            Device linking URI (can be converted to QR code)
        """
        try:
            # This would use signal-cli to generate linking info
            # Placeholder for actual implementation
            result = subprocess.run(
                ['signal-cli', 'link', '-n', 'ShopBot'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Extract URI from output
                return result.stdout.strip()
            else:
                raise RuntimeError(f"Failed to generate link: {result.stderr}")
        except Exception as e:
            raise RuntimeError(f"Signal linking failed: {e}")
    
    def auto_trust_contact(self, contact_number: str) -> bool:
        """
        Automatically trust a contact's identity.
        Called when receiving message from any contact.
        
        Args:
            contact_number: Phone number to trust
            
        Returns:
            True if successful, False otherwise
        """
        # Don't trust self
        if contact_number == self.phone_number:
            return True
        
        # Check cache to avoid re-trusting
        if contact_number in self._trust_attempted:
            return True
        
        try:
            # First, try to trust the contact
            result = subprocess.run(
                ['signal-cli', '-u', self.phone_number, 'trust', contact_number, '-a'],
                capture_output=True,
                timeout=1,
                text=True
            )
            
            if result.returncode == 0:
                print(f"✓ Auto-trusted contact {contact_number}")
                # Add to cache only after successful trust
                self._trust_attempted.add(contact_number)
                return True
            else:
                # Check if already trusted or other non-critical error
                stderr = result.stderr.lower()
                if 'already' in stderr or 'trusted' in stderr:
                    print(f"DEBUG: {contact_number} already trusted")
                    # Already trusted, add to cache
                    self._trust_attempted.add(contact_number)
                    return True
                elif 'not registered' in stderr:
                    # They haven't messaged us yet, will trust when they do
                    print(f"DEBUG: {contact_number} will be trusted when they message")
                    return False
                else:
                    print(f"DEBUG: Trust command for {contact_number}: {result.stderr.strip()}")
                    return False
                
        except subprocess.TimeoutExpired:
            print(f"WARNING: Trust command timed out for {contact_number}")
            return False
        except Exception as e:
            print(f"WARNING: Could not auto-trust {contact_number}: {e}")
            return False
    
    def send_message(
        self,
        recipient: str,
        message: str,
        attachments: Optional[List[str]] = None,
        sender_identity: Optional[str] = None
    ) -> bool:
        """
        Send message via Signal using direct mode
        
        Args:
            recipient: Recipient phone number (e.g., "+15555550123") or username (e.g., "randomuser.01")
            message: Message text
            attachments: Optional list of file paths to attach
            sender_identity: Identity to send from (phone or username). If not provided, uses default phone number
            
        Returns:
            True if message sent successfully
        """
        if not self.phone_number:
            raise RuntimeError("Signal not configured")
        
        # Use sender_identity if provided, otherwise use default phone_number
        sender = sender_identity if sender_identity else self.phone_number
        
        return self._send_direct(recipient, message, attachments, sender)
    
    def _send_direct(self, recipient: str, message: str, attachments: Optional[List[str]] = None, sender: Optional[str] = None) -> bool:
        """
        Send message directly via signal-cli
        
        Args:
            recipient: Recipient phone number, username, or UUID
            message: Message text
            attachments: Optional list of file paths
            sender: Sender identity (phone or username). If not provided, uses self.phone_number
            
        Returns:
            True if sent successfully
        """
        try:
            # Use provided sender or default to phone_number
            if not sender:
                sender = self.phone_number
            
            # Determine recipient type and build command accordingly
            # Phone numbers and UUIDs use direct addressing
            # Usernames require the --username flag
            if recipient.startswith('+') or self._is_uuid(recipient):
                # Phone number or UUID - send directly
                cmd = [
                    'signal-cli',
                    '-u', sender,
                    'send',
                    '-m', message,
                    recipient
                ]
            else:
                # Username - requires --username flag
                cmd = [
                    'signal-cli',
                    '-u', sender,
                    'send',
                    '-m', message,
                    '--username', recipient
                ]
            
            if attachments:
                for attachment in attachments:
                    cmd.extend(['-a', attachment])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60  # Increased for slow network (600-700ms latency to Signal servers)
            )
            
            if result.returncode == 0:
                print(f"DEBUG: Message sent successfully to {recipient}")
                return True
            else:
                print(f"ERROR: Failed to send message to {recipient}: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print(f"ERROR: Timeout sending message to {recipient}")
            print(f"  Timeout was set to 60 seconds - connection may be unstable")
            print(f"  Consider checking network or using smaller images")
            return False
        except Exception as e:
            print(f"ERROR: Failed to send Signal message: {e}")
            print(f"  Recipient: {recipient}")
            print(f"  Attachments: {len(attachments) if attachments else 0}")
            return False
    
    def send_image(self, recipient: str, image_path: str, caption: Optional[str] = None) -> bool:
        """
        Send image via Signal
        
        Args:
            recipient: Recipient phone number
            image_path: Path to image file
            caption: Optional caption
            
        Returns:
            True if sent successfully
        """
        message = caption if caption else ""
        return self.send_message(recipient, message, attachments=[image_path])
    
    def start_listening(self):
        """Start listening for incoming messages"""
        if self.listening:
            print("DEBUG: start_listening() called but already listening")
            return
        
        print(f"DEBUG: start_listening() called for {self.phone_number}")
        self.listening = True
        self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listen_thread.start()
        print("DEBUG: Listen thread started successfully")
    
    def stop_listening(self):
        """Stop listening for messages"""
        self.listening = False
        if self.listen_thread:
            self.listen_thread.join(timeout=5)
    
    def is_listening(self):
        """
        Check if message listener is running
        
        Returns:
            bool: True if listening for messages
        """
        return self.listening
    
    def _listen_loop(self):
        """Background loop to receive messages with adaptive polling"""
        if not self.phone_number:
            print("DEBUG: _listen_loop cannot start - no phone number configured")
            return
        
        print(f"DEBUG: Listen loop active for {self.phone_number}")
        
        # Adaptive polling: longer sleep when idle, shorter when active
        idle_sleep = 5  # 5 seconds when no messages
        active_sleep = 2  # 2 seconds after receiving messages
        current_sleep = idle_sleep
        
        while self.listening:
            try:
                print("DEBUG: Polling for messages... (signal-cli timeout: 5s, subprocess timeout: 20s)")
                result = subprocess.run(
                    ['signal-cli', '--output', 'json', '-u', self.phone_number, 'receive', '--timeout', '5'],
                    capture_output=True,
                    text=True,
                    timeout=20  # Increased from 15 for better reliability
                )
                
                if result.returncode != 0 and result.stderr:
                    print(f"DEBUG: signal-cli receive error: {result.stderr}")
                
                messages_received = False
                
                if result.returncode == 0 and result.stdout:
                    print(f"DEBUG: Received data from signal-cli")
                    # Parse JSON messages
                    for line in result.stdout.strip().split('\n'):
                        if line:
                            try:
                                message_data = json.loads(line)
                                self._handle_message(message_data)
                                messages_received = True
                            except json.JSONDecodeError:
                                print(f"DEBUG: Failed to parse JSON: {line[:100]}")
                else:
                    print(f"DEBUG: No messages (will retry in {idle_sleep}s)")
                
                # Adaptive sleep: poll faster when active, slower when idle
                if messages_received:
                    current_sleep = active_sleep
                    print(f"DEBUG: Active mode - next check in {active_sleep}s")
                else:
                    current_sleep = idle_sleep
                
            except subprocess.TimeoutExpired:
                print(f"WARNING: signal-cli receive command timed out after 20 seconds")
            except Exception as e:
                print(f"ERROR: Error receiving messages: {e}")
            
            time.sleep(current_sleep)
    
    def _handle_message(self, message_data: Dict):
        """
        Handle received message
        
        Args:
            message_data: Message data from signal-cli
        """
        # Extract message info
        envelope = message_data.get('envelope', {})
        
        # Extract recipient identity (which account/identity received this message)
        recipient_identity = message_data.get('account', self.phone_number)
        
        # Check if this is a sync message (self-sent) or regular message
        sync_message = envelope.get('syncMessage', {})
        sent_message = sync_message.get('sentMessage', {})
        
        if sent_message:
            # This is a message we sent to ourselves or others
            source = envelope.get('sourceNumber') or envelope.get('source', '')
            timestamp = sent_message.get('timestamp', 0)
            message_text = sent_message.get('message', '')
            destination = sent_message.get('destination') or sent_message.get('destinationNumber', '')
            group_info = sent_message.get('groupInfo')
            
            # For self-messages, we might want to skip processing
            if destination == self.phone_number:
                # Skip messages we sent to ourselves
                print(f"DEBUG: Skipping self-sent message (syncMessage)")
                return
            
            print(f"DEBUG: Received syncMessage from {source}: {message_text[:50] if message_text else '(no text)'}")
        else:
            # Regular incoming message from someone else
            source = envelope.get('sourceNumber') or envelope.get('source', '')
            timestamp = envelope.get('timestamp', 0)
            
            data_message = envelope.get('dataMessage', {})
            message_text = data_message.get('message', '')
            group_info = data_message.get('groupInfo')
            
            print(f"DEBUG: Received dataMessage from {source}: {message_text[:50] if message_text else '(no text)'}")
        
        # Log recipient type for debugging
        if source:
            if source.startswith('+'):
                print(f"DEBUG: Message from phone number (length: {len(source)})")
            elif self._is_uuid(source):
                print(f"DEBUG: Message from UUID (privacy enabled)")
            else:
                print(f"DEBUG: Message from username: {source}")
        
        # Auto-trust all message senders to handle message requests
        # This ensures message requests are accepted automatically for every sender
        if source and source != self.phone_number:
            print(f"DEBUG: Message from {source}, auto-trusting...")
            if self.auto_trust_contact(source):
                self.trusted_contacts.add(source)
        
        # Create message object
        message = {
            'sender': source,
            'text': message_text,
            'timestamp': timestamp,
            'is_group': group_info is not None,
            'group_id': group_info.get('groupId') if group_info else None,
            'recipient_identity': recipient_identity  # Track which identity received this
        }
        
        # If buyer handler exists, process buyer commands
        if self.buyer_handler and message_text:
            try:
                print(f"DEBUG: Processing message from {source} to {recipient_identity}")
                self.buyer_handler.handle_buyer_message(source, message_text, recipient_identity)
            except Exception as e:
                print(f"ERROR: Error in buyer handler: {e}")
        
        # Call registered callbacks
        for callback in self.message_callbacks:
            try:
                callback(message)
            except Exception as e:
                print(f"ERROR: Error in message callback: {e}")
    
    def register_message_callback(self, callback: Callable):
        """
        Register callback for incoming messages
        
        Args:
            callback: Function to call when message received
        """
        self.message_callbacks.append(callback)
    
    def send_product_info(
        self,
        recipient: str,
        product_name: str,
        description: str,
        price_fiat: str,
        price_xmr: str,
        stock: int,
        image_path: Optional[str] = None
    ):
        """
        Send product information to buyer
        
        Args:
            recipient: Buyer's phone number
            product_name: Product name
            description: Product description
            price_fiat: Price in fiat currency
            price_xmr: Price in XMR
            stock: Stock availability
            image_path: Optional product image
        """
        message = f"""
🛍️ {product_name}

{description}

💰 Price: {price_fiat} ({price_xmr})
📦 Stock: {stock} available

Reply with 'BUY {product_name}' to purchase.
        """.strip()
        
        if image_path:
            self.send_image(recipient, image_path, message)
        else:
            self.send_message(recipient, message)
    
    def send_payment_instructions(
        self,
        recipient: str,
        order_id: str,
        payment_address: str,
        amount_xmr: float,
        qr_image_path: str,
        expires_in_minutes: int
    ):
        """
        Send payment instructions to buyer
        
        Args:
            recipient: Buyer's phone number
            order_id: Order ID
            payment_address: Monero payment address
            amount_xmr: Amount in XMR
            qr_image_path: Path to QR code image
            expires_in_minutes: Order expiration time
        """
        message = f"""
✅ Order {order_id} Created!

💳 Payment Instructions:
Amount: {amount_xmr:.12f} XMR

Address:
{payment_address}

⏰ Pay within {expires_in_minutes} minutes

Scan QR code or copy address to your Monero wallet.
You'll receive confirmation when payment is detected.
        """.strip()
        
        self.send_image(recipient, qr_image_path, message)
    
    def send_payment_confirmation(
        self,
        recipient: str,
        order_id: str,
        amount_paid: float
    ):
        """
        Send payment confirmation
        
        Args:
            recipient: Buyer's phone number
            order_id: Order ID
            amount_paid: Amount paid in XMR
        """
        message = f"""
✅ Payment Received!

Order: {order_id}
Amount: {amount_paid:.12f} XMR

Your order is being processed. You'll be notified when it ships.

Thank you for your purchase!
        """.strip()
        
        self.send_message(recipient, message)
    
    def send_shipping_notification(self, recipient: str, order_id: str, tracking_number: str, shipped_at):
        """
        Send shipping notification to customer
        
        Args:
            recipient: Buyer's phone number
            order_id: Order ID
            tracking_number: Shipping tracking number
            shipped_at: DateTime when order was shipped
        """
        from datetime import datetime
        
        # Format shipped date
        if shipped_at:
            shipped_date = shipped_at.strftime("%B %d, %Y")
        else:
            shipped_date = datetime.utcnow().strftime("%B %d, %Y")
        
        if tracking_number and tracking_number.strip():
            message = f"""🚚 Your order #{order_id} has been shipped!

Tracking Number: {tracking_number}
Shipped: {shipped_date}

Your package is on its way! 📦

Thanks for your order!"""
        else:
            # No tracking number provided
            message = f"""🚚 Your order #{order_id} has been shipped!

Shipped: {shipped_date}

Your package is on its way! 📦

Thanks for your order!"""
        
        self.send_message(recipient, message)
    
    def send_group_redirect(self, group_id: str, member: str):
        """
        Send message redirecting to private chat
        
        Args:
            group_id: Group ID
            member: Member to redirect
        """
        message = "I've sent you a private message with the product catalog. Check your DMs! 📱"
        # In actual implementation, would send to group
        # For now, just send to member directly
        self.send_message(member, message)
    
    def list_groups(self) -> List[Dict]:
        """
        List all Signal groups
        
        Returns:
            List of group dictionaries with 'id', 'name', and 'members'
        """
        if not self.phone_number:
            raise RuntimeError("Signal not configured")
        
        try:
            result = subprocess.run(
                ['signal-cli', '-u', self.phone_number, 'listGroups', '--detailed'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            groups = []
            if result.returncode == 0 and result.stdout:
                # Parse group information
                # Note: Actual parsing would depend on signal-cli output format
                for line in result.stdout.strip().split('\n'):
                    if line:
                        try:
                            # Example parsing - adjust based on actual format
                            parts = line.split()
                            if len(parts) >= 2:
                                groups.append({
                                    'id': parts[0],
                                    'name': ' '.join(parts[1:]),
                                    'members': []
                                })
                        except:
                            pass
            
            return groups
        except Exception as e:
            print(f"Failed to list groups: {e}")
            return []
    
    def _verify_auto_trust_config(self):
        """Verify that auto-trust configuration is active"""
        try:
            import urllib.parse
            
            # Check signal-cli config file
            encoded_number = urllib.parse.quote(self.phone_number, safe='')
            config_paths = [
                f"{os.path.expanduser('~')}/.local/share/signal-cli/data/{self.phone_number}",
                f"{os.path.expanduser('~')}/.local/share/signal-cli/data/{encoded_number}"
            ]
            
            for path in config_paths:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        trust_mode = config.get('trustNewIdentities', 'NOT_SET')
                        
                        if trust_mode == 'ALWAYS':
                            print(f"✓ Signal auto-trust verified: {trust_mode}")
                            return True
                        else:
                            print(f"⚠ Signal auto-trust not optimal: {trust_mode}")
                            print(f"   Run: ./check-trust.sh to fix")
                            # Still return True - code-level auto-trust will work
                            return True
            
            print("ℹ Signal config file not found - using code-level auto-trust")
            return True
            
        except Exception as e:
            print(f"DEBUG: Could not verify signal auto-trust config: {e}")
            print("       Code-level auto-trust will still work")
            return True
