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
    
    def __init__(self, phone_number: Optional[str] = None):
        """
        Initialize Signal handler
        
        Args:
            phone_number: Seller's Signal phone number
        """
        self.phone_number = phone_number
        self.message_callbacks = []
        self.listening = False
        self.listen_thread = None
    
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
        
        Args:
            recipient: Recipient phone number (e.g., "+15555550123") or username (e.g., "randomuser.01")
            message: Message text
            attachments: Optional list of file paths to attach
            
        Returns:
            True if message sent successfully
        """
        if not self.phone_number:
            raise RuntimeError("Signal not configured")
        
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
                timeout=10
            )
            
            return result.returncode == 0
        except Exception as e:
            print(f"Failed to send Signal message: {e}")
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
            return
        
        self.listening = True
        self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listen_thread.start()
    
    def stop_listening(self):
        """Stop listening for messages"""
        self.listening = False
        if self.listen_thread:
            self.listen_thread.join(timeout=5)
    
    def _listen_loop(self):
        """
        Background loop to receive messages
        """
        if not self.phone_number:
            return
        
        while self.listening:
            try:
                # Receive messages using signal-cli
                result = subprocess.run(
                    ['signal-cli', '-u', self.phone_number, 'receive', '--json'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0 and result.stdout:
                    # Parse JSON messages
                    for line in result.stdout.strip().split('\n'):
                        if line:
                            try:
                                message_data = json.loads(line)
                                self._handle_message(message_data)
                            except json.JSONDecodeError:
                                pass
                
            except Exception as e:
                print(f"Error receiving messages: {e}")
            
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
        
        # Create message object
        message = {
            'sender': source,
            'text': message_text,
            'timestamp': timestamp,
            'is_group': group_info is not None,
            'group_id': group_info.get('groupId') if group_info else None
        }
        
        # Call registered callbacks
        for callback in self.message_callbacks:
            try:
                callback(message)
            except Exception as e:
                print(f"Error in message callback: {e}")
    
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
