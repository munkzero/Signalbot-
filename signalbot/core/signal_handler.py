"""
SignalHandler - High-level interface for sending/receiving Signal messages.

Wraps the JSON-RPC daemon client and the signal-cli subprocess to provide
a unified API used by the dashboard and buyer handler.
"""

import logging
import os
import subprocess
import threading
import time
from typing import Callable, Dict, List, Optional

from .jsonrpc_client import JsonRpcClient, JsonRpcError
from .signal_daemon import SignalDaemon
from ..config.settings import SIGNAL_DAEMON_PORT

logger = logging.getLogger(__name__)


class SignalHandler:
    """
    High-level Signal messaging interface.

    Manages a ``SignalDaemon`` (signal-cli TCP daemon) and a ``JsonRpcClient``
    for JSON-RPC communication.  Also exposes a fast native ``send_message_native``
    path that calls signal-cli directly (bypassing the daemon for speed).
    """

    def __init__(self, phone_number: Optional[str] = None):
        """
        Args:
            phone_number: Signal account phone number (e.g. ``+64274757293``).
        """
        self.phone_number = phone_number

        # Daemon lifecycle manager
        self._daemon = SignalDaemon(
            phone_number=phone_number or "",
            port=SIGNAL_DAEMON_PORT,
        ) if phone_number else None

        # JSON-RPC client
        self._client: Optional[JsonRpcClient] = None

        # Listening state
        self._listening = False
        self._listen_thread: Optional[threading.Thread] = None

        # Registered message callbacks (called for every incoming message)
        self._message_callbacks: List[Callable] = []

        # In-memory live conversation store: {contact_id: [msg_dict, ...]}
        self._live_conversations: Dict[str, List[Dict]] = {}
        self._live_lock = threading.Lock()

        # Optional buyer handler (attached externally by the dashboard)
        self.buyer_handler = None

    # ------------------------------------------------------------------
    # Daemon / connection management
    # ------------------------------------------------------------------

    def _ensure_connected(self) -> bool:
        """Start daemon and connect the JSON-RPC client if not already done."""
        if self._client and self._client.is_connected():
            return True

        # Start daemon if we manage one
        if self._daemon:
            if not self._daemon.start():
                logger.error("Failed to start signal-cli daemon")
                return False

        port = SIGNAL_DAEMON_PORT
        self._client = JsonRpcClient(
            host="localhost",
            port=port,
            notification_callback=self._on_notification,
        )
        if not self._client.connect():
            logger.error(f"Failed to connect JsonRpcClient on port {port}")
            self._client = None
            return False

        logger.info(f"Connected to signal-cli daemon on port {port}")
        return True

    def stop(self):
        """Stop listening and disconnect from the daemon."""
        self._listening = False
        if self._listen_thread and self._listen_thread.is_alive():
            self._listen_thread.join(timeout=5)
        if self._client:
            self._client.disconnect()
            self._client = None
        if self._daemon:
            self._daemon.stop()
        logger.info("SignalHandler stopped")

    # ------------------------------------------------------------------
    # Sending messages
    # ------------------------------------------------------------------

    def send_message(
        self,
        recipient: str,
        message: str,
        attachments: Optional[List[str]] = None,
    ) -> bool:
        """
        Send a message via the JSON-RPC daemon.

        Args:
            recipient: Recipient phone number or UUID.
            message: Text body.
            attachments: Optional list of file paths to attach.

        Returns:
            True on success, False on failure.
        """
        if not self._ensure_connected():
            logger.error("send_message: could not connect to daemon")
            return False

        try:
            self._client.send_message(recipient, message, attachments)
            self._record_live_message(
                recipient,
                message or ("[Attachment]" if attachments else ""),
                int(time.time() * 1000),
                is_outgoing=True,
            )
            logger.debug("✅ Message sent successfully")
            return True
        except (JsonRpcError, TimeoutError, RuntimeError) as exc:
            logger.error(f"send_message failed: {exc}")
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
            True if command executed successfully, False on error
        """
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
                self._record_live_message(
                    recipient,
                    message or ("[Attachment]" if attachments else ""),
                    int(time.time() * 1000),
                    is_outgoing=True,
                )
                return True
            else:
                error = result.stderr.decode('utf-8', errors='ignore')
                error_msg = error.strip()
                print(f"⚠️ Native send FAILED with returncode {result.returncode}")
                print(f"   Error: {error_msg}")
                print(f"   Command: signal-cli -a <phone> send -m '<message>' {recipient}")
                logger.warning(f"⚠️ Native send failed with returncode {result.returncode}: {error_msg[:250]}")
                # Return False on actual error
                return False

        except subprocess.TimeoutExpired:
            print(f"❌ Native send timeout (30s) to {recipient}")
            logger.error(f"❌ Native send timeout (30s) to {recipient}")
            return False
        except Exception as e:
            print(f"❌ Native send exception: {e}")
            logger.error(f"❌ Native send failed: {e}")
            return False

    def send_shipping_notification(
        self,
        recipient: str,
        order_id: str,
        tracking_number: str,
        shipped_at,
    ) -> bool:
        """
        Send a shipping notification message to a customer.

        Args:
            recipient: Customer Signal phone number / UUID.
            order_id: Order identifier string.
            tracking_number: Shipping tracking number.
            shipped_at: Datetime when the order was shipped.

        Returns:
            True on success, False on failure.
        """
        try:
            shipped_str = shipped_at.strftime("%Y-%m-%d %H:%M UTC") if hasattr(shipped_at, 'strftime') else str(shipped_at)
            message = (
                f"📦 Your order {order_id} has been shipped!\n"
                f"Tracking: {tracking_number}\n"
                f"Shipped: {shipped_str}"
            )
            return self.send_message(recipient, message)
        except Exception as exc:
            logger.error(f"send_shipping_notification failed: {exc}")
            return False

    # ------------------------------------------------------------------
    # Receiving / listening
    # ------------------------------------------------------------------

    def register_message_callback(self, callback: Callable):
        """Register a callback that receives incoming message dicts."""
        self._message_callbacks.append(callback)

    def start_listening(self):
        """Connect to the daemon and start processing incoming messages."""
        if self._listening:
            logger.debug("Already listening")
            return

        if not self._ensure_connected():
            logger.error("start_listening: could not connect to daemon")
            return

        self._listening = True
        logger.info("SignalHandler: started listening for messages")

    def is_listening(self) -> bool:
        """Return True if currently listening for messages."""
        return self._listening and bool(self._client and self._client.is_connected())

    def _on_notification(self, frame: Dict):
        """Handle unsolicited JSON-RPC notifications from the daemon."""
        try:
            # signal-cli daemon wraps incoming messages in a "receive" result
            params = frame.get("params", {})
            envelope = params.get("envelope", {})
            if not envelope:
                return

            data_message = envelope.get("dataMessage") or envelope.get("syncMessage", {}).get("sentMessage", {})
            if not data_message:
                return

            sender = envelope.get("sourceNumber") or envelope.get("source", "")
            message_text = data_message.get("message", "")
            timestamp = envelope.get("timestamp", int(time.time() * 1000))

            msg = {
                "sender": sender,
                "text": message_text,
                "timestamp": timestamp,
                "envelope": envelope,
            }

            self._record_live_message(sender, message_text, timestamp, is_outgoing=False)

            # Auto-trust the sender so future sends succeed
            if self._client and sender:
                try:
                    self._client.trust_identity(sender)
                except Exception:
                    pass

            # Dispatch to buyer handler first
            if self.buyer_handler and message_text:
                try:
                    self.buyer_handler.handle_message(sender, message_text)
                except Exception as exc:
                    logger.error(f"BuyerHandler error: {exc}")

            # Then call registered callbacks
            for callback in self._message_callbacks:
                try:
                    callback(msg)
                except Exception as exc:
                    logger.error(f"Message callback error: {exc}")

        except Exception as exc:
            logger.error(f"_on_notification error: {exc}")

    # ------------------------------------------------------------------
    # Groups
    # ------------------------------------------------------------------

    def list_groups(self) -> List[Dict]:
        """
        Return a list of groups the account belongs to.

        Returns:
            List of group info dicts (keys: ``groupId``, ``name``, etc.)
            or an empty list on failure.
        """
        if not self._ensure_connected():
            return []
        try:
            result = self._client.send_request("listGroups")
            if isinstance(result, list):
                return result
            return []
        except Exception as exc:
            logger.error(f"list_groups failed: {exc}")
            return []

    def join_group(self, invite_link: str) -> bool:
        """
        Join a group via an invite link.

        Args:
            invite_link: The ``https://signal.group/#...`` invite URL.

        Returns:
            True on success, False on failure.
        """
        if not self._ensure_connected():
            return False
        try:
            self._client.send_request("joinGroup", {"uri": invite_link})
            return True
        except Exception as exc:
            logger.error(f"join_group failed: {exc}")
            return False

    def leave_group(self, group_id: str) -> bool:
        """
        Leave a group.

        Args:
            group_id: The group identifier.

        Returns:
            True on success, False on failure.
        """
        if not self._ensure_connected():
            return False
        try:
            self._client.send_request("quitGroup", {"groupId": group_id})
            return True
        except Exception as exc:
            logger.error(f"leave_group failed: {exc}")
            return False

    # ------------------------------------------------------------------
    # Device linking
    # ------------------------------------------------------------------

    def link_device(self) -> str:
        """
        Generate a device-linking URI (for QR-code display).

        Returns:
            The ``tsdevice://`` URI string, or an empty string on failure.
        """
        if not self._ensure_connected():
            return ""
        try:
            result = self._client.send_request("startLink")
            return result.get("deviceLinkUri", "")
        except Exception as exc:
            logger.error(f"link_device failed: {exc}")
            return ""

    # ------------------------------------------------------------------
    # Live conversation store
    # ------------------------------------------------------------------

    def _record_live_message(
        self,
        contact_id: str,
        text: str,
        timestamp: int,
        is_outgoing: bool = False,
    ):
        """Append a message to the in-memory live conversation store."""
        with self._live_lock:
            if contact_id not in self._live_conversations:
                self._live_conversations[contact_id] = []
            self._live_conversations[contact_id].append({
                "contact_id": contact_id,
                "text": text,
                "timestamp": timestamp,
                "is_outgoing": is_outgoing,
            })

    def get_live_conversations(self) -> List[Dict]:
        """
        Return a summary list of all active live conversations.

        Returns:
            List of dicts with keys ``contact_id``, ``last_message``, ``timestamp``.
        """
        with self._live_lock:
            summaries = []
            for contact_id, messages in self._live_conversations.items():
                if messages:
                    last = messages[-1]
                    summaries.append({
                        "contact_id": contact_id,
                        "last_message": last.get("text", ""),
                        "timestamp": last.get("timestamp", 0),
                        "unread_count": sum(1 for m in messages if not m.get("is_outgoing")),
                    })
            return summaries

    def get_live_conversation(self, contact_id: str) -> List[Dict]:
        """
        Return all messages for a specific conversation.

        Args:
            contact_id: Phone number or UUID of the contact.

        Returns:
            List of message dicts for that contact.
        """
        with self._live_lock:
            return list(self._live_conversations.get(contact_id, []))

    def clear_live_conversation(self, contact_id: str):
        """Remove all in-memory messages for the given contact."""
        with self._live_lock:
            self._live_conversations.pop(contact_id, None)

    def clear_all_live_conversations(self):
        """Remove all in-memory live conversations."""
        with self._live_lock:
            self._live_conversations.clear()

    # ------------------------------------------------------------------
    # Health / diagnostics
    # ------------------------------------------------------------------

    def get_health_status(self) -> Dict:
        """
        Return a dict describing the current health of the signal handler.

        Returns:
            Dict with keys: ``listening``, ``connected``, ``daemon_healthy``.
        """
        return {
            "listening": self._listening,
            "connected": bool(self._client and self._client.is_connected()),
            "daemon_healthy": self._daemon.is_healthy() if self._daemon else False,
        }
