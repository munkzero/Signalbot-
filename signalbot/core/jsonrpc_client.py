"""
JSON-RPC 2.0 client for signal-cli daemon TCP communication.

signal-cli daemon listens on a TCP socket and speaks JSON-RPC 2.0.
Incoming Signal messages arrive as unsolicited JSON-RPC notifications
(objects without an ``id`` field).  Outgoing commands are sent as
JSON-RPC requests (objects with a sequential ``id``).
"""

import json
import socket
import threading
import time
from typing import Callable, Dict, List, Optional


class JsonRpcError(Exception):
    """Raised when the daemon returns a JSON-RPC error response."""

    def __init__(self, code: int, message: str, data=None):
        self.code = code
        self.data = data
        super().__init__(f"JSON-RPC error {code}: {message}")


class JsonRpcClient:
    """
    Persistent TCP client for the signal-cli JSON-RPC daemon.

    A background reader thread continuously reads newline-delimited JSON
    frames from the socket.  Responses to requests are matched by ``id``
    and returned to the caller.  Notifications (frames without ``id``) are
    dispatched to a registered callback.
    """

    # How long to wait for a request response before giving up (seconds).
    DEFAULT_REQUEST_TIMEOUT = 60
    # How long to wait between reconnect attempts (seconds).
    RECONNECT_DELAY = 3
    # Maximum reconnect attempts before giving up.
    MAX_RECONNECT_ATTEMPTS = 5

    def __init__(
        self,
        host: str = "localhost",
        port: int = 7583,
        notification_callback: Optional[Callable[[Dict], None]] = None,
    ):
        self.host = host
        self.port = port
        self.notification_callback = notification_callback

        self._sock: Optional[socket.socket] = None
        self._lock = threading.Lock()
        self._pending: Dict[int, dict] = {}  # id -> response (once received)
        self._pending_events: Dict[int, threading.Event] = {}
        self._next_id = 1
        self._reader_thread: Optional[threading.Thread] = None
        self._running = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """
        Open a TCP connection to the daemon and start the background reader.

        Returns:
            True on success, False on failure.
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((self.host, self.port))
            sock.settimeout(None)  # switch to blocking mode for the reader
            self._sock = sock
            self._running = True
            self._reader_thread = threading.Thread(
                target=self._reader_loop, daemon=True, name="jsonrpc-reader"
            )
            self._reader_thread.start()
            return True
        except (OSError, ConnectionRefusedError) as exc:
            print(f"ERROR: JsonRpcClient could not connect to {self.host}:{self.port}: {exc}")
            return False

    def disconnect(self):
        """Close the TCP connection and stop the background reader."""
        self._running = False
        if self._sock is not None:
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        # Wake up any pending request waiters so they can fail cleanly.
        with self._lock:
            for event in self._pending_events.values():
                event.set()

    def is_connected(self) -> bool:
        """Return True if the socket is open."""
        return self._sock is not None and self._running

    def send_request(
        self,
        method: str,
        params: Optional[Dict] = None,
        timeout: float = DEFAULT_REQUEST_TIMEOUT,
    ) -> Dict:
        """
        Send a JSON-RPC 2.0 request and wait for the response.

        Args:
            method: JSON-RPC method name (e.g. ``"send"``, ``"receive"``).
            params: Optional parameter dict.
            timeout: Seconds to wait for a response.

        Returns:
            The ``result`` field of the JSON-RPC response.

        Raises:
            JsonRpcError: If the daemon returns an error frame.
            TimeoutError: If no response arrives within *timeout* seconds.
            RuntimeError: If not connected.
        """
        if not self.is_connected():
            raise RuntimeError("JsonRpcClient is not connected")

        with self._lock:
            request_id = self._next_id
            self._next_id += 1
            event = threading.Event()
            self._pending_events[request_id] = event

        frame: Dict = {"jsonrpc": "2.0", "method": method, "id": request_id}
        if params:
            frame["params"] = params

        self._send_frame(frame)

        if not event.wait(timeout=timeout):
            with self._lock:
                self._pending_events.pop(request_id, None)
                self._pending.pop(request_id, None)
            raise TimeoutError(
                f"No JSON-RPC response for '{method}' within {timeout}s"
            )

        with self._lock:
            self._pending_events.pop(request_id, None)
            response = self._pending.pop(request_id, None)

        if response is None:
            raise RuntimeError("JsonRpcClient was disconnected while waiting for a response")

        if "error" in response:
            err = response["error"]
            raise JsonRpcError(
                code=err.get("code", -1),
                message=err.get("message", "unknown error"),
                data=err.get("data"),
            )

        return response.get("result", {})

    def send_message(
        self,
        recipient: str,
        message: str,
        attachments: Optional[List[str]] = None,
    ) -> Dict:
        """
        Send a Signal message via the daemon.

        Args:
            recipient: Phone number, UUID, or username of the recipient.
            message: Message body.
            attachments: Optional list of attachment file paths.

        Returns:
            The JSON-RPC result dict from the daemon.
        """
        params: Dict = {"recipient": [recipient], "message": message}
        if attachments:
            params["attachment"] = attachments
        return self.send_request("send", params)

    def receive_messages(self) -> List[Dict]:
        """
        Explicitly poll for pending messages (returns the list from the daemon).

        In daemon mode messages normally arrive as unsolicited notifications,
        so this method is provided for completeness / testing.
        """
        result = self.send_request("receive", {"timeout": 0})
        if isinstance(result, list):
            return result
        return []

    def trust_identity(self, recipient: str) -> Dict:
        """
        Trust a contact's identity key (accept all fingerprints).

        **Security note**: ``trustAllKnownKeys=True`` tells signal-cli to accept
        every known fingerprint for *recipient* without manual verification.
        This is intentional for a shop bot where every inbound customer must be
        trusted automatically, but should not be used in contexts where
        man-in-the-middle protection is critical.

        Args:
            recipient: Phone number or UUID.

        Returns:
            JSON-RPC result dict.
        """
        return self.send_request(
            "trust",
            {"recipient": recipient, "trustAllKnownKeys": True},
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _send_frame(self, frame: Dict):
        """Serialise *frame* as JSON and write it to the socket."""
        data = json.dumps(frame) + "\n"
        if self._sock is not None:
            try:
                self._sock.sendall(data.encode())
            except OSError as exc:
                print(f"ERROR: JsonRpcClient send failed: {exc}")
                self.disconnect()

    def _reader_loop(self):
        """Background thread: read newline-delimited JSON from the socket."""
        buf = b""
        while self._running and self._sock is not None:
            try:
                chunk = self._sock.recv(4096)
                if not chunk:
                    # Server closed the connection.
                    print("DEBUG: JsonRpcClient: daemon closed the connection")
                    break
                buf += chunk
                while b"\n" in buf:
                    line_bytes, buf = buf.split(b"\n", 1)
                    line = line_bytes.decode("utf-8", errors="replace").strip()
                    if line:
                        self._handle_frame(line)
            except OSError:
                if self._running:
                    print("DEBUG: JsonRpcClient: socket error in reader loop")
                break

        self._running = False
        # Unblock any pending waiters.
        with self._lock:
            for event in self._pending_events.values():
                event.set()

    def _handle_frame(self, line: str):
        """Parse one JSON line and route it to a waiter or the notification callback."""
        try:
            frame = json.loads(line)
        except json.JSONDecodeError:
            print(f"DEBUG: JsonRpcClient: could not parse frame: {line[:200]}")
            return

        frame_id = frame.get("id")

        if frame_id is not None:
            # This is a response to one of our requests.
            with self._lock:
                self._pending[frame_id] = frame
                event = self._pending_events.get(frame_id)
            if event is not None:
                event.set()
        else:
            # Unsolicited notification (incoming Signal message, receipt, etc.)
            if self.notification_callback is not None:
                try:
                    self.notification_callback(frame)
                except Exception as exc:
                    print(f"ERROR: JsonRpcClient notification callback raised: {exc}")
