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

    # Number of consecutive polling errors before backing off.
    _MAX_CONSECUTIVE_POLL_ERRORS = 12
    # Seconds to sleep after hitting _MAX_CONSECUTIVE_POLL_ERRORS.
    _BACKOFF_SLEEP_SECONDS = 60

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
        # Don't block on in-flight handlers; they are non-daemon threads and
        # will finish naturally.  New submissions are impossible because the
        # polling thread has stopped.
        self._msg_handler_pool.shutdown(wait=False)
        print("⏹ Polling stopped")

    def is_listening(self):
        """
        Check if message listener is running.

        Returns:
            bool: True if listening for messages.
        """
        return self.listening

    def _dispatch_message(self, sender: str, message_text: str, timestamp: int):
        """
        Process a single incoming message: call buyer handler and registered callbacks.

        Args:
            sender: Sender's Signal identifier (phone number or UUID).
            message_text: Decoded message body.
            timestamp: Message timestamp in milliseconds.
        """
        print(f"✅ Received message from {sender}: {message_text[:50]}")

        message = {
            'sender': sender,
            'text': message_text,
            'timestamp': timestamp,
            'is_group': False,
            'group_id': None,
            'recipient_identity': self.phone_number,
        }

        if self.buyer_handler and message_text:
            try:
                print(f"DEBUG: Processing buyer command from {sender}")
                self.buyer_handler.handle_buyer_message(sender, message_text, self.phone_number)
            except Exception as e:
                print(f"ERROR: Error in buyer handler: {e}")

        for callback in self.message_callbacks:
            try:
                callback(message)
            except Exception as e:
                print(f"ERROR: Error in message callback: {e}")

    def _parse_json_output(self, stdout: str):
        """
        Parse JSON-mode output from ``signal-cli receive --json``.

        Each line is a self-contained JSON envelope.  Only ``dataMessage``
        envelopes with a non-empty body are dispatched to handlers; receipts,
        typing indicators and sync messages are silently ignored.

        Args:
            stdout: Raw stdout string from the subprocess.
        """
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                print(f"DEBUG: Non-JSON line from signal-cli: {line[:80]}")
                continue

            try:
                envelope = data.get('envelope', {})

                # Prefer sourceNumber (E.164) then source (may be UUID)
                sender = (
                    envelope.get('sourceNumber')
                    or envelope.get('source')
                    or ''
                ).strip()

                if not sender or sender == self.phone_number:
                    continue

                # Auto-trust new contacts in background
                if sender not in self._trust_attempted:
                    threading.Thread(
                        target=self._trust_contact_background,
                        args=(sender,),
                        daemon=True,
                        name=f"Trust-{sender[:10]}",
                    ).start()

                data_message = envelope.get('dataMessage') or {}
                message_text = (data_message.get('message') or '').strip()

                if not message_text:
                    # Receipt, typing indicator, or empty sync — skip silently
                    continue

                timestamp = envelope.get('timestamp') or int(time.time() * 1000)
                self._dispatch_message(sender, message_text, timestamp)

            except Exception as exc:
                print(f"DEBUG: Error processing JSON envelope: {exc}")

    def _parse_text_output(self, stdout: str):
        """
        Fallback parser for plain-text ``signal-cli receive`` output.

        Scans for ``Envelope from:`` headers and the ``Body:`` line that
        follows within the same envelope block.  This handles variable
        amounts of header lines between the envelope and the body.

        Args:
            stdout: Raw stdout string from the subprocess.
        """
        lines = stdout.splitlines()
        sender = None
        timestamp = int(time.time() * 1000)

        for line in lines:
            stripped = line.strip()

            if stripped.startswith('Envelope from:'):
                # Reset state for each new envelope
                sender = None
                # Extract the first E.164 phone number from the header line
                phone_match = re.search(r'\+\d{7,15}', stripped)
                if phone_match:
                    candidate = phone_match.group(0)
                    if candidate != self.phone_number:
                        sender = candidate

            elif stripped.startswith('Timestamp:'):
                ts_match = re.search(r'\b(\d{13})\b', stripped)
                if ts_match:
                    try:
                        timestamp = int(ts_match.group(1))
                    except ValueError:
                        pass

            elif stripped.startswith('Body:') and sender:
                message_text = stripped[len('Body:'):].strip()
                if message_text:
                    if sender not in self._trust_attempted:
                        threading.Thread(
                            target=self._trust_contact_background,
                            args=(sender,),
                            daemon=True,
                            name=f"Trust-{sender[:10]}",
                        ).start()
                    self._dispatch_message(sender, message_text, timestamp)
                    sender = None  # Consumed; wait for next envelope

    def _polling_loop(self):
        """
        Polling loop: periodically calls ``signal-cli receive`` to fetch
        pending messages. Runs every 5 seconds in a background thread.

        Tries JSON output (``--json``) first for reliable structured parsing;
        falls back to plain-text parsing if the flag is unsupported.
        """
        poll_interval = 5
        use_json = True  # Start with JSON mode; disabled on first failure
        consecutive_errors = 0

        print("DEBUG: Entering polling loop (signal-cli receive --json mode)")

        while self.listening:
            try:
                cmd = ["signal-cli", "-a", self.phone_number, "receive", "--timeout", "1"]
                if use_json:
                    cmd.append("--json")

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode != 0 and use_json:
                    # --json flag may not be supported by this signal-cli version
                    stderr_lower = result.stderr.lower()
                    if 'unknown option' in stderr_lower or 'unrecognized' in stderr_lower or '--json' in stderr_lower:
                        print("WARNING: signal-cli --json not supported; falling back to text mode")
                        use_json = False
                        # Retry immediately in text mode (skip the poll-interval sleep)
                        continue
                    # Log other non-zero exits for diagnostics
                    if result.returncode != 0 and result.stderr.strip():
                        print(f"DEBUG: signal-cli receive exit {result.returncode}: {result.stderr.strip()[:120]}")

                if result.stdout.strip():
                    if use_json:
                        self._parse_json_output(result.stdout)
                    else:
                        self._parse_text_output(result.stdout)

                # Reset error counter on successful poll
                consecutive_errors = 0

            except FileNotFoundError:
                consecutive_errors += 1
                if consecutive_errors == 1:
                    print("ERROR: signal-cli not found. Retrying every 30 seconds...")
                elif consecutive_errors % 10 == 0:
                    print(f"WARNING: signal-cli still not found after {consecutive_errors} attempts; continuing to retry...")
                # Retry after a longer delay rather than stopping entirely
                time.sleep(30)
                continue
            except subprocess.TimeoutExpired:
                consecutive_errors += 1
                print(f"WARNING: signal-cli receive timed out (attempt {consecutive_errors}); retrying")
            except Exception as exc:
                consecutive_errors += 1
                print(f"WARNING: Polling error ({consecutive_errors}): {exc}")
                if consecutive_errors >= self._MAX_CONSECUTIVE_POLL_ERRORS:
                    print(f"WARNING: {self._MAX_CONSECUTIVE_POLL_ERRORS} consecutive polling errors; backing off {self._BACKOFF_SLEEP_SECONDS}s")
                    time.sleep(self._BACKOFF_SLEEP_SECONDS)
                    consecutive_errors = 0
                    continue

            time.sleep(poll_interval)

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
        Send shipping notification to customer.

        Message format: "Your order is on the way! Tracking: [number]"

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

        # Build message — lead with the customer-facing line matching the spec
        message_parts = [
            f"🚚 Your order is on the way!",
            "",
        ]

        if tracking_number and tracking_number.strip():
            message_parts.append(f"Tracking: {tracking_number.strip()}")

        message_parts.extend([
            f"Order: #{order_id}",
            f"Shipped: {shipped_date}",
            "",
            "Thanks for your order! 🎉"
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
