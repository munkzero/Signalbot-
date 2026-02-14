"""
Signal messaging handler
Manages Signal messaging integration for buyer-seller communication
"""

from typing import Optional, Callable, Dict, List
import subprocess
import json
import threading
import time


class SignalHandler:
    """
    Handles Signal messaging for the shop bot
    Note: Requires signal-cli to be installed and configured
    """
    
    def __init__(self, phone_number: Optional[str] = None, auto_daemon: bool = False):
        """
        Initialize Signal handler
        
        Args:
            phone_number: Seller's Signal phone number
            auto_daemon: Automatically start daemon mode for faster messaging (disabled by default due to reliability issues)
        """
        self.phone_number = phone_number
        self.message_callbacks = []
        self.buyer_handler = None  # Will be set by dashboard
        self.listening = False
        self.listen_thread = None
        self.daemon_process = None
        self.daemon_running = False
        
        print(f"DEBUG: SignalHandler initialized with phone_number={phone_number}, auto_daemon={auto_daemon}")
        
        # Auto-start daemon for faster messaging (disabled by default)
        if auto_daemon and phone_number:
            self.start_daemon()
    
    def start_daemon(self):
        """
        Start signal-cli in daemon mode for faster messaging
        
        Returns:
            True if daemon started successfully
        """
        if self.daemon_running and self.daemon_process and self.daemon_process.poll() is None:
            return True  # Already running
        
        if not self.phone_number:
            print("Cannot start daemon: No phone number configured")
            return False
        
        try:
            # Start daemon in background
            self.daemon_process = subprocess.Popen(
                ['signal-cli', '--output', 'json', '-u', self.phone_number, 'daemon'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE
            )
            print(f"Signal daemon started (PID: {self.daemon_process.pid})")
            
            # Give it 2 seconds to initialize
            time.sleep(2)
            
            # Check if it's still running
            if self.daemon_process.poll() is None:
                self.daemon_running = True
                return True
            else:
                print("Daemon failed to start")
                return False
        except FileNotFoundError:
            print("signal-cli not found - falling back to direct mode")
            return False
        except Exception as e:
            print(f"Failed to start daemon: {e}")
            return False
    
    def stop_daemon(self):
        """Stop the signal-cli daemon"""
        if self.daemon_process:
            try:
                self.daemon_process.terminate()
                self.daemon_process.wait(timeout=5)
                print("Signal daemon stopped")
            except Exception as e:
                print(f"Error stopping daemon: {e}")
            finally:
                self.daemon_process = None
                self.daemon_running = False
    
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
    
    def send_message(
        self,
        recipient: str,
        message: str,
        attachments: Optional[List[str]] = None
    ) -> bool:
        """
        Send message via Signal
        Uses daemon mode if available for faster sending (2-3s vs 10-15s)
        
        Args:
            recipient: Recipient phone number (e.g., "+15555550123") or username (e.g., "randomuser.01")
            message: Message text
            attachments: Optional list of file paths to attach
            
        Returns:
            True if message sent successfully
        """
        if not self.phone_number:
            raise RuntimeError("Signal not configured")
        
        # Try daemon mode first (faster)
        if self.daemon_running and self.daemon_process and self.daemon_process.poll() is None:
            try:
                return self._send_via_daemon(recipient, message, attachments)
            except Exception as e:
                print(f"Daemon send failed, falling back to direct: {e}")
                self.daemon_running = False
        
        # Fallback to direct mode (slower but more reliable)
        return self._send_direct(recipient, message, attachments)
    
    def _send_via_daemon(self, recipient: str, message: str, attachments: Optional[List[str]] = None) -> bool:
        """
        Send message via running daemon (faster: 2-3 seconds)
        
        Args:
            recipient: Recipient phone number or username
            message: Message text
            attachments: Optional list of file paths
            
        Returns:
            True if sent successfully
        """
        # For daemon mode, we still use direct for now
        # Full daemon integration would require D-Bus or JSON-RPC
        # For this implementation, just fall back to direct
        return self._send_direct(recipient, message, attachments)
    
    def _send_direct(self, recipient: str, message: str, attachments: Optional[List[str]] = None) -> bool:
        """
        Send message directly via signal-cli (slower: 10-15 seconds)
        
        Args:
            recipient: Recipient phone number or username
            message: Message text
            attachments: Optional list of file paths
            
        Returns:
            True if sent successfully
        """
        try:
            # Check if recipient is a username or phone number
            if recipient.startswith('+'):
                # Phone number
                cmd = [
                    'signal-cli',
                    '-u', self.phone_number,
                    'send',
                    '-m', message,
                    recipient
                ]
            else:
                # Username
                cmd = [
                    'signal-cli',
                    '-u', self.phone_number,
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
                timeout=20  # Increased timeout for reliability
            )
            
            if result.returncode == 0:
                print(f"DEBUG: Message sent successfully to {recipient}")
                return True
            else:
                print(f"ERROR: Failed to send message to {recipient}: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print(f"ERROR: Timeout sending message to {recipient}")
            return False
        except Exception as e:
            print(f"ERROR: Failed to send Signal message: {e}")
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
        """Stop listening for messages and clean up daemon"""
        self.listening = False
        if self.listen_thread:
            self.listen_thread.join(timeout=5)
        
        # Also stop daemon if running
        self.stop_daemon()
    
    def is_listening(self):
        """
        Check if message listener is running
        
        Returns:
            bool: True if listening for messages
        """
        return self.listening
    
    def _listen_loop(self):
        """
        Background loop to receive messages
        """
        if not self.phone_number:
            print("DEBUG: _listen_loop cannot start - no phone number configured")
            return
        
        print(f"DEBUG: Listen loop active for {self.phone_number}")
        
        while self.listening:
            try:
                print("DEBUG: Checking for messages...")
                # Receive messages using signal-cli
                result = subprocess.run(
                    ['signal-cli', '--output', 'json', '-u', self.phone_number, 'receive'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode != 0 and result.stderr:
                    print(f"DEBUG: signal-cli receive error: {result.stderr}")
                
                if result.returncode == 0 and result.stdout:
                    print(f"DEBUG: Received data from signal-cli")
                    # Parse JSON messages
                    for line in result.stdout.strip().split('\n'):
                        if line:
                            try:
                                message_data = json.loads(line)
                                self._handle_message(message_data)
                            except json.JSONDecodeError:
                                print(f"DEBUG: Failed to parse JSON: {line[:100]}")
                
            except Exception as e:
                print(f"ERROR: Error receiving messages: {e}")
            
            time.sleep(2)
    
    def _handle_message(self, message_data: Dict):
        """
        Handle received message
        
        Args:
            message_data: Message data from signal-cli
        """
        # Extract message info
        envelope = message_data.get('envelope', {})
        source = envelope.get('source') or envelope.get('sourceNumber', '')
        timestamp = envelope.get('timestamp', 0)
        
        data_message = envelope.get('dataMessage', {})
        message_text = data_message.get('message', '')
        group_info = data_message.get('groupInfo')
        
        print(f"DEBUG: Received message from {source}: {message_text[:50] if message_text else '(no text)'}")
        
        # Create message object
        message = {
            'sender': source,
            'text': message_text,
            'timestamp': timestamp,
            'is_group': group_info is not None,
            'group_id': group_info.get('groupId') if group_info else None
        }
        
        # If buyer handler exists, process buyer commands
        if self.buyer_handler and message_text:
            try:
                print(f"DEBUG: Passing message to buyer handler")
                self.buyer_handler.handle_buyer_message(source, message_text)
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
