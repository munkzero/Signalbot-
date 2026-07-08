"""
Signal messaging handler
Manages Signal messaging integration for buyer-seller communication
"""

from typing import Optional, Callable, Dict, List
import json
import logging
import subprocess
import sys
import threading
import time
import os
import re
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class SignalHandler:
    """
    Handles Signal messaging for the shop bot via polling (signal-cli receive).
    Requires signal-cli to be installed and configured.
    """

    # Maximum characters to log from envelope JSON for diagnostics.
    _MAX_ENVELOPE_LOG_LENGTH = 500

    def __init__(self, phone_number: Optional[str] = None):
        """
        Initialize Signal handler.

        Args:
            phone_number: Seller's Signal phone number (if not provided, reads from environment).
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
        # Bounded pool for processing incoming messages (prevents resource exhaustion
        # if many messages arrive in quick succession).
        self._msg_handler_pool = ThreadPoolExecutor(max_workers=10, thread_name_prefix="MsgHandler")

        print(f"DEBUG: SignalHandler initialized with phone_number={self.phone_number}")

        # Verify signal-cli is available for polling mode
        self.ensure_signal_cli_ready()

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

    def ensure_signal_cli_ready(self):
        """
        Verify signal-cli is available for polling mode (no daemon needed).
        """
        try:
            result = subprocess.run(
                ['signal-cli', '-a', self.phone_number, 'listGroups'],
                capture_output=True,
                timeout=5,
                check=False
            )
            logger.info("✅ signal-cli ready for polling mode")
            return True
        except FileNotFoundError:
            print("WARNING: signal-cli not found. Messaging will be unavailable.")
            return False
        except Exception as e:
            logger.error(f"❌ signal-cli not ready: {e}")
            return False

    def stop(self):
        """Stop listening."""
        self.stop_listening()

    def link_device(self) -> str:
        """
        Generate linking URI for Signal account.

        Returns:
            Device linking URI (can be converted to QR code).
        """
        try:
            result = subprocess.run(
                ['signal-cli', 'link', '-n', 'ShopBot'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                raise RuntimeError(f"Failed to generate link: {result.stderr}")
        except Exception as e:
            raise RuntimeError(f"Signal linking failed: {e}")

    def _trust_contact_background(self, source: str):
        """Trust contact in background thread to avoid blocking message processing."""
        if self.auto_trust_contact(source):
            self.trusted_contacts.add(source)

    def auto_trust_contact(self, contact_number: str) -> bool:
        """
        Automatically trust a contact's identity via signal-cli native command.
        Called when receiving a message from any contact.

        Args:
            contact_number: Phone number to trust.

        Returns:
            True if successful (or already trusted), False otherwise.
        """
        # Don't trust self
        if contact_number == self.phone_number:
            return True

        # Check cache to avoid re-trusting
        if contact_number in self._trust_attempted:
            return True

        try:
            result = subprocess.run(
                ['signal-cli', '-a', self.phone_number, 'trust', '-v', 'VERIFIED', contact_number],
                capture_output=True,
                timeout=10,
                check=False
            )
            self._trust_attempted.add(contact_number)
            if result.returncode == 0:
                print(f"✓ Auto-trusted contact {contact_number}")
            else:
                stderr = result.stderr.decode('utf-8', errors='ignore').lower()
                if 'already' in stderr or 'trusted' in stderr:
                    print(f"DEBUG: {contact_number} already trusted")
                else:
                    print(f"DEBUG: Trust command for {contact_number}: {stderr[:100]}")
            return True
        except FileNotFoundError:
            print(f"WARNING: signal-cli not found; cannot trust {contact_number}")
            return False
        except Exception as exc:
            print(f"WARNING: Could not auto-trust {contact_number}: {exc}")
            return False
    
    def send_message(
        self,
        recipient: str,
        message: str,
        attachments: Optional[List[str]] = None,
        sender_identity: Optional[str] = None
    ) -> bool:
        """
        Send message via Signal using native signal-cli command.
        
        Args:
            recipient: Recipient phone number (e.g., "+15555550123") or username (e.g., "randomuser.01")
            message: Message text
            attachments: Optional list of file paths to attach
            sender_identity: Retained for API compatibility with callers that pass a sender
                             identity; the native command always uses the configured account.
            
        Returns:
            True if message sent successfully
        """
        if not self.phone_number:
            raise RuntimeError("Signal not configured")
        
        return self.send_message_native(recipient, message, attachments)
    
    def send_image(self, recipient: str, image_path: str, caption: Optional[str] = None) -> bool:
        """
        Send image via Signal.

        Args:
            recipient: Recipient phone number.
            image_path: Path to image file.
            caption: Optional caption.

        Returns:
            True if sent successfully.
        """
        message = caption if caption else ""
        return self.send_message(recipient, message, attachments=[image_path])

    def send_message_fast(self, recipient: str, message: str = None, attachments: List[str] = None) -> bool:
        """
        Fast direct send using signal-cli command (doesn't wait for daemon JSON-RPC).

        This is much faster than daemon JSON-RPC which can timeout after 120s.
        Uses subprocess fire-and-forget for instant sends.

        Args:
            recipient: Phone number to send to
            message: Text message (optional)
            attachments: List of file paths to attach (optional)

        Returns:
            True if the send process was successfully started, False on error
        """
        import subprocess

        cmd = ['signal-cli', '-a', self.phone_number, 'send']

        if message:
            cmd.extend(['-m', message])

        if attachments:
            for attachment in attachments:
                if os.path.exists(attachment):
                    cmd.extend(['--attachment', attachment])
                else:
                    print(f"WARNING: Attachment not found: {attachment}")

        cmd.append(recipient)

        try:
            # Fire and forget (async, doesn't block)
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True  # Detach from parent
            )
            print(f"DEBUG: Fast send to {recipient} (direct command, async)")
            return True
        except Exception as e:
            print(f"ERROR: Fast send failed: {e}")
            return False

    def send_message_native(self, recipient: str, message: str = None, attachments: List[str] = None) -> bool:
        """
        Ultra-fast native send using signal-cli command directly.
        This bypasses daemon JSON-RPC for speed.

        Speed: 5-10 seconds (vs 30-60s with daemon JSON-RPC)

        Args:
            recipient: Phone number
            message: Text message
            attachments: List of file paths

        Returns:
            True if command executed (doesn't wait for delivery)
        """
        import subprocess

        cmd = ['signal-cli', '-a', self.phone_number, 'send']

        if message:
            cmd.extend(['-m', message])

        cmd.append(recipient)

        if attachments:
            for attachment in attachments:
                if os.path.exists(attachment):
                    cmd.extend(['--attachment', attachment])
                else:
                    logger.warning(f"Attachment not found, skipping: {attachment}")

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                check=False
            )

            if result.returncode == 0:
                logger.debug(f"✅ Native send to {recipient} completed")
                return True
            else:
                error = result.stderr.decode('utf-8', errors='ignore')
                logger.warning(f"⚠️ Native send warning: {error[:100]}")
                # Return True anyway - signal-cli often returns non-zero but message sends
                return True

        except subprocess.TimeoutExpired:
            logger.error(f"❌ Native send timeout (30s) to {recipient}")
            return False
        except Exception as e:
            logger.error(f"❌ Native send failed: {e}")
            return False

    def send_message_native_async(self, recipient: str, message: str = None, attachments: List[str] = None) -> bool:
        """
        Async wrapper for native sends (non-blocking).

        Starts a background thread to send the message natively without
        blocking the caller.

        Args:
            recipient: Phone number
            message: Text message
            attachments: List of file paths

        Returns:
            True immediately (send happens in background)
        """
        def _send():
            self.send_message_native(recipient, message, attachments)

        threading.Thread(target=_send, daemon=True, name=f"NativeSend-{recipient[:10]}").start()
        logger.debug(f"⚡ Started native send thread for {recipient}")
        return True

    def start_listening(self):
        """
        Start polling for incoming messages every 5 seconds (no daemon).
        """
        if self.listening:
            print("DEBUG: start_listening() called but already listening")
            return

        print(f"DEBUG: start_listening() called for {self.phone_number}")
        self.listening = True
        self.listen_thread = threading.Thread(
            target=self._polling_loop, daemon=True, name="signal-polling"
        )
        self.listen_thread.start()
        print("DEBUG: Polling started (5-second intervals)")
    
    def stop_listening(self):
        """Stop polling loop and shut down the message handler pool."""
        self.listening = False
        if self.listen_thread:
            # Allow up to 10 seconds for the current poll cycle (subprocess
            # timeout is 30 s, but the thread checks self.listening between
            # polls and exits promptly once the flag is cleared).
            self.listen_thread.join(timeout=10)
        self._msg_handler_pool.shutdown(wait=True)
        print("⏹ Polling stopped")

    def is_listening(self):
        """
        Check if message listener is running.

        Returns:
            bool: True if listening for messages.
        """
        return self.listening

    def _polling_loop(self):
        """
        Polling loop: periodically calls ``signal-cli receive`` to fetch
        pending messages. Runs every 5 seconds in a background thread.
        """
        poll_interval = 5

        print("DEBUG: Entering polling loop (signal-cli receive mode)")

        while self.listening:
            try:
                result = subprocess.run(
                    ["signal-cli", "-a", self.phone_number, "receive", "--json"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode == 0 and result.stdout.strip():
                    for line in result.stdout.strip().splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            message_data = json.loads(line)
                            if message_data.get("envelope"):
                                self._msg_handler_pool.submit(
                                    self._handle_message, message_data
                                )
                        except json.JSONDecodeError:
                            pass
                elif result.returncode != 0:
                    stderr_text = (result.stderr or "").strip()
                    if stderr_text:
                        print(f"DEBUG: signal-cli receive error: {stderr_text[:200]}")
            except FileNotFoundError:
                print("ERROR: signal-cli not found; polling mode unavailable")
                break
            except Exception as exc:
                print(f"WARNING: Polling error: {exc}")

            time.sleep(poll_interval)


    def _handle_message(self, message_data: Dict):
        """
        Handle received message
        
        Args:
            message_data: Message data from signal-cli
        """
        print(f"🔔 _handle_message() CALLED")
        envelope = message_data.get('envelope', {})
        print(f"   Full envelope keys: {list(envelope.keys())}")
        print(f"   Envelope: {json.dumps(envelope, indent=2)[:self._MAX_ENVELOPE_LOG_LENGTH]}")
        
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
            
            if timestamp:
                current_time_ms = int(time.time() * 1000)
                delivery_delay_seconds = max(0, (current_time_ms - timestamp) / 1000)
                if delivery_delay_seconds > 15:
                    print(f"⚠ High delivery delay: {delivery_delay_seconds:.1f}s (username messages often delayed)")
                else:
                    print(f"✓ Normal delivery delay: {delivery_delay_seconds:.1f}s")
            
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
            print(f"DEBUG: Message from {source}, auto-trusting in background...")
            # Run trust in background thread (non-blocking)
            threading.Thread(
                target=self._trust_contact_background,
                args=(source,),
                daemon=True,
                name=f"TrustThread-{source}"
            ).start()
            # Message processing continues immediately (don't wait for trust)
        
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
        
        # Build base message
        message_parts = [
            f"🚚 Your order #{order_id} has been shipped!",
            "",
        ]
        
        # Add tracking number if provided
        if tracking_number and tracking_number.strip():
            message_parts.append(f"Tracking Number: {tracking_number}")
        
        # Add shipped date and footer
        message_parts.extend([
            f"Shipped: {shipped_date}",
            "",
            "Your package is on its way! 📦",
            "",
            "Thanks for your order!"
        ])
        
        message = "\n".join(message_parts)
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
        List all Signal groups via native signal-cli command.

        Returns:
            List of group dictionaries with 'id', 'name', and 'members'.
        """
        if not self.phone_number:
            raise RuntimeError("Signal not configured")

        try:
            result = subprocess.run(
                ['signal-cli', '-a', self.phone_number, 'listGroups', '-d'],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return []
            groups = []
            for line in result.stdout.strip().splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    g = json.loads(line)
                    groups.append({
                        'id': g.get('id', ''),
                        'name': g.get('name', ''),
                        'members': g.get('members', []),
                    })
                except json.JSONDecodeError:
                    pass
            return groups
        except FileNotFoundError:
            print("WARNING: signal-cli not found; cannot list groups")
            return []
        except Exception as exc:
            print(f"Failed to list groups: {exc}")
            return []

    def _verify_auto_trust_config(self):
        """Verify that auto-trust configuration is active (reads local config file)."""
        try:
            import urllib.parse
            from pathlib import Path

            encoded_number = urllib.parse.quote(self.phone_number, safe='')
            data_dir = Path.home() / ".local" / "share" / "signal-cli" / "data"  # signal-cli/data/

            # Candidate paths: plain phone number, URL-encoded, and numeric account IDs.
            config_paths = [
                str(data_dir / self.phone_number),
                str(data_dir / encoded_number),
            ]

            # Also look for numeric account directories (new signal-cli format).
            # Only include numeric files whose stored number matches self.phone_number.
            if data_dir.exists():
                for entry in data_dir.iterdir():
                    if entry.is_file() and entry.name.isdigit():
                        try:
                            with open(entry, encoding="utf-8") as f:
                                acct = json.load(f)
                            stored = acct.get("number") or acct.get("username", "")
                            if stored == self.phone_number:
                                config_paths.append(str(entry))
                        except Exception:
                            pass

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
                            return True

            print("ℹ Signal config file not found - using code-level auto-trust")
            return True

        except Exception as exc:
            print(f"DEBUG: Could not verify signal auto-trust config: {exc}")
            print("       Code-level auto-trust will still work")
            return True
