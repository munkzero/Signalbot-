"""
Signal messaging handler
Manages Signal messaging integration for buyer-seller communication
"""

from typing import Optional, Callable, Dict, List
import json
import threading
import time
import os
import re

from signalbot.core.jsonrpc_client import JsonRpcClient, JsonRpcError
from signalbot.core.signal_daemon import SignalDaemon
from signalbot.config.settings import SIGNAL_DAEMON_PORT, SIGNAL_DAEMON_STARTUP_TIMEOUT


class SignalHandler:
    """
    Handles Signal messaging for the shop bot via the signal-cli JSON-RPC daemon.
    Requires signal-cli to be installed and configured.
    """

    # Keepalive/health-check interval (seconds between daemon connection checks).
    _KEEPALIVE_INTERVAL_SECONDS = 30
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

        # Daemon and JSON-RPC client
        self._daemon = SignalDaemon(
            phone_number=self.phone_number,
            port=SIGNAL_DAEMON_PORT,
            startup_timeout=SIGNAL_DAEMON_STARTUP_TIMEOUT,
        )
        self._rpc: Optional[JsonRpcClient] = None

        print(f"DEBUG: SignalHandler initialized with phone_number={self.phone_number}")

        # Start daemon and connect RPC client
        self._start_daemon()

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

    def _start_daemon(self):
        """Start the signal-cli daemon and connect the JSON-RPC client."""
        if not self._daemon.start():
            print("WARNING: signal-cli daemon could not be started. "
                  "Messaging will be unavailable until the daemon is running.")
            return

        self._rpc = JsonRpcClient(
            host="localhost",
            port=SIGNAL_DAEMON_PORT,
            notification_callback=self._on_notification,
        )
        if not self._rpc.connect():
            print("WARNING: Could not connect to signal-cli daemon RPC socket.")
            self._rpc = None

    def stop(self):
        """Stop listening and shut down the daemon (if we started it)."""
        self.stop_listening()
        if self._rpc is not None:
            self._rpc.disconnect()
            self._rpc = None
        self._daemon.stop()

    def link_device(self) -> str:
        """
        Generate linking URI for Signal account.

        Returns:
            Device linking URI (can be converted to QR code).
        """
        import subprocess
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
        Automatically trust a contact's identity via the JSON-RPC daemon.
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

        if self._rpc is None:
            print(f"WARNING: Cannot trust {contact_number} - RPC not connected")
            return False

        try:
            self._rpc.trust_identity(contact_number)
            print(f"✓ Auto-trusted contact {contact_number}")
            self._trust_attempted.add(contact_number)
            return True
        except JsonRpcError as exc:
            msg = str(exc).lower()
            if 'already' in msg or 'trusted' in msg:
                print(f"DEBUG: {contact_number} already trusted")
                self._trust_attempted.add(contact_number)
                return True
            elif 'not registered' in msg:
                print(f"DEBUG: {contact_number} will be trusted when they message")
                return False
            else:
                print(f"DEBUG: Trust command for {contact_number}: {exc}")
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
        Send message via the JSON-RPC daemon.

        Args:
            recipient: Recipient phone number, username, or UUID.
            message: Message text.
            attachments: Optional list of file paths.
            sender: Retained for API compatibility; the daemon always uses the
                    configured account so this parameter has no effect.

        Returns:
            True if sent successfully.
        """
        if self._rpc is None:
            print(f"ERROR: Cannot send message - RPC not connected")
            return False

        try:
            params: Dict = {"recipient": [recipient], "message": message}
            if attachments:
                params["attachment"] = attachments
            # Use a longer timeout when sending attachments: image uploads to
            # Signal servers can take longer than the default 60 s window.
            timeout = (
                JsonRpcClient.SEND_WITH_ATTACHMENT_TIMEOUT
                if attachments
                else JsonRpcClient.DEFAULT_REQUEST_TIMEOUT
            )
            self._rpc.send_request("send", params, timeout=timeout)
            print(f"DEBUG: Message sent successfully to {recipient}")
            return True
        except TimeoutError:
            print(f"ERROR: Timeout sending message to {recipient}")
            print(f"  Note: Message may have been sent despite timeout")
            print(f"  Timeout occurred waiting for RPC response after {timeout}s")
            return False
        except JsonRpcError as exc:
            print(f"ERROR: Failed to send message to {recipient}: {exc}")
            return False
        except Exception as exc:
            print(f"ERROR: Failed to send Signal message: {exc}")
            print(f"  Recipient: {recipient}")
            print(f"  Attachments: {len(attachments) if attachments else 0}")
            return False

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

    def start_listening(self):
        """
        Start receiving incoming messages via the daemon notification channel.

        The JSON-RPC client's background reader dispatches incoming Signal
        message notifications to ``_on_notification`` which in turn calls
        ``_handle_message``.  The ``listening`` flag and ``listen_thread``
        are retained for compatibility with code that calls ``is_listening()``.

        If the JSON-RPC daemon is not available, falls back to polling mode
        (``signal-cli receive``) so the bot still receives messages.
        """
        if self.listening:
            print("DEBUG: start_listening() called but already listening")
            return

        print(f"DEBUG: start_listening() called for {self.phone_number}")

        if self._rpc is None or not self._rpc.is_connected():
            print("WARNING: RPC not connected; attempting to reconnect before listening…")
            self._start_daemon()

        if self._rpc is not None and self._rpc.is_connected():
            self.listening = True
            # Start a lightweight keepalive / health-check thread so that
            # is_listening() continues to return True while the daemon is running,
            # and reconnects if the daemon crashes.
            self.listen_thread = threading.Thread(
                target=self._keepalive_loop, daemon=True, name="signal-keepalive"
            )
            self.listen_thread.start()
            print("DEBUG: Listening via daemon notifications (JSON-RPC mode)")
        else:
            # Daemon not available – fall back to polling mode.
            print("WARNING: Daemon RPC unavailable; falling back to polling mode")
            self.listening = True
            self.listen_thread = threading.Thread(
                target=self._polling_loop, daemon=True, name="signal-polling"
            )
            self.listen_thread.start()
            print("DEBUG: Listening via polling mode (signal-cli receive)")
    
    def stop_listening(self):
        """Stop the keepalive loop and mark handler as not listening."""
        self.listening = False
        if self.listen_thread:
            self.listen_thread.join(timeout=5)

    def is_listening(self):
        """
        Check if message listener is running.

        Returns:
            bool: True if listening for messages.
        """
        return self.listening

    def _keepalive_loop(self):
        """
        Lightweight thread that periodically verifies the daemon is healthy
        and attempts to reconnect if it has crashed.
        If reconnect fails, switches to polling mode.
        """
        while self.listening:
            time.sleep(self._KEEPALIVE_INTERVAL_SECONDS)
            if not self.listening:
                break

            if self._rpc is None or not self._rpc.is_connected():
                print("WARNING: signal-cli daemon connection lost; reconnecting…")
                if self._rpc is not None:
                    self._rpc.disconnect()
                    self._rpc = None
                self._start_daemon()
                if self._rpc is not None and self._rpc.is_connected():
                    print("✓ Reconnected to signal-cli daemon")
                else:
                    print("WARNING: Could not reconnect to daemon; switching to polling mode")
                    # Switch the active thread to polling.
                    self.listen_thread = threading.Thread(
                        target=self._polling_loop, daemon=True, name="signal-polling"
                    )
                    self.listen_thread.start()
                    return  # Stop this keepalive thread; polling thread takes over.

    def _polling_loop(self):
        """
        Fallback polling loop: periodically calls ``signal-cli receive`` to
        fetch pending messages when the JSON-RPC daemon is not available.

        Uses a 5-second polling interval. Attempts to reconnect to the daemon
        every ``_KEEPALIVE_INTERVAL_SECONDS`` seconds; if reconnection succeeds
        this thread exits and the caller should start a keepalive thread instead.
        """
        import subprocess as _sp
        import json as _json

        poll_interval = 5
        reconnect_check_interval = self._KEEPALIVE_INTERVAL_SECONDS
        last_reconnect_check = time.monotonic()

        print("DEBUG: Entering polling loop (signal-cli receive mode)")

        while self.listening:
            # Periodically try to switch back to daemon mode.
            if time.monotonic() - last_reconnect_check >= reconnect_check_interval:
                last_reconnect_check = time.monotonic()
                self._start_daemon()
                if self._rpc is not None and self._rpc.is_connected():
                    print("✓ Daemon reconnected; switching from polling to daemon mode")
                    self.listen_thread = threading.Thread(
                        target=self._keepalive_loop, daemon=True, name="signal-keepalive"
                    )
                    self.listen_thread.start()
                    return

            try:
                result = _sp.run(
                    ["signal-cli", "-a", self.phone_number, "receive", "--output", "json"],
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
                            message_data = _json.loads(line)
                            if message_data.get("envelope"):
                                self._handle_message(message_data)
                        except _json.JSONDecodeError:
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

    def _on_notification(self, frame: Dict):
        """
        Called by the JSON-RPC reader thread for every unsolicited notification
        (i.e. incoming Signal messages / receipts pushed by the daemon).

        The daemon wraps incoming messages in a ``receive`` notification whose
        ``params`` field contains the same envelope structure that
        ``signal-cli receive --output json`` would print.
        """
        method = frame.get("method", "")
        params = frame.get("params")

        # The daemon sends notifications in one of these shapes:
        #   1. {"jsonrpc":"2.0","method":"receive","params":{"envelope":{...},"account":"..."}}
        #   2. Older builds: {"jsonrpc":"2.0","method":"receive","params":{...envelope fields...}}
        #   3. Envelope directly at frame level (some builds)
        if params is not None:
            message_data = params
        else:
            message_data = frame

        envelope = message_data.get("envelope")
        if envelope is None:
            # Some builds inline the envelope fields directly in params.
            # If the frame looks like an envelope itself, treat it as one.
            _message_keys = {"dataMessage", "syncMessage", "typingMessage"}
            if _message_keys & message_data.keys():
                print(f"DEBUG: Notification has inline envelope (method={method!r})")
                envelope = message_data
                message_data = {"envelope": envelope, "account": message_data.get("account", self.phone_number)}
            else:
                # Not a message notification we recognise; ignore.
                return

        print(f"🔔 Daemon notification received (method={method!r})")
        self._handle_message(message_data)


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
        List all Signal groups via the JSON-RPC daemon.

        Returns:
            List of group dictionaries with 'id', 'name', and 'members'.
        """
        if not self.phone_number:
            raise RuntimeError("Signal not configured")

        if self._rpc is None:
            print("WARNING: Cannot list groups - RPC not connected")
            return []

        try:
            result = self._rpc.send_request("listGroups")
            if isinstance(result, list):
                return [
                    {
                        'id': g.get('id', ''),
                        'name': g.get('name', ''),
                        'members': g.get('members', []),
                    }
                    for g in result
                ]
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
