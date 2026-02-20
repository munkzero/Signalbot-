"""
signal-cli daemon lifecycle manager.

Starts ``signal-cli daemon --tcp --send-read-receipts`` on bot startup
(or reuses an already-running daemon) and provides a clean shutdown path.
The daemon exposes a JSON-RPC 2.0 API over a TCP socket on localhost:7583
(configurable via ``SIGNAL_DAEMON_PORT`` in the environment / settings).
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Optional


class SignalDaemon:
    """
    Manage the lifecycle of a signal-cli daemon process.

    If a daemon is already listening on the configured port this class will
    *not* start a second one – it will simply connect to the existing process.
    """

    # Default TCP port for the signal-cli daemon.
    DEFAULT_PORT = 7583
    # Default signal-cli data directory.
    SIGNAL_DATA_DIR = Path.home() / ".local" / "share" / "signal-cli" / "data"

    def __init__(
        self,
        phone_number: str,
        port: int = DEFAULT_PORT,
        startup_timeout: int = 30,
    ):
        """
        Args:
            phone_number: The Signal account phone number (e.g. ``+64274757293``).
            port:         TCP port the daemon should listen on.
            startup_timeout: Seconds to wait for the daemon to become ready.
        """
        self.phone_number = phone_number
        self.port = port
        self.startup_timeout = startup_timeout

        self._process: Optional[subprocess.Popen] = None
        self._we_started_it = False  # True only if *this* instance launched daemon

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> bool:
        """
        Ensure the daemon is running and listening on *self.port*.

        1. If a process is already listening on the port, return True
           (we will connect to the external daemon).
        2. Otherwise spawn a new daemon and wait until it is ready.

        Returns:
            True if the daemon is ready, False on failure.
        """
        if self._is_port_open():
            print(f"✓ signal-cli daemon already running on port {self.port}")
            self._we_started_it = False
            return True

        # Clean up stale lock files before starting to avoid conflicts
        self._cleanup_lock_files()

        return self._spawn_daemon()

    def stop(self):
        """
        Stop the daemon if *this* instance started it.

        If the daemon was already running before this instance was created
        it is left untouched.
        """
        if not self._we_started_it or self._process is None:
            return

        print("Stopping signal-cli daemon…")
        try:
            self._process.terminate()
            self._process.wait(timeout=10)
            print("✓ signal-cli daemon stopped")
        except subprocess.TimeoutExpired:
            print("WARNING: daemon did not stop cleanly, killing…")
            self._process.kill()
            self._process.wait()
        except Exception as exc:
            print(f"ERROR: Could not stop signal-cli daemon: {exc}")
        finally:
            self._process = None
            self._we_started_it = False

    def is_healthy(self) -> bool:
        """
        Return True if the daemon's TCP port is currently accepting connections.
        """
        return self._is_port_open()

    def find_account_id(self) -> Optional[str]:
        """
        Find the signal-cli account identifier for this phone number.

        Newer signal-cli versions (0.12+) may store accounts using a numeric
        ID (e.g. ``670916``) instead of the phone number as a filename.
        This method checks the data directory and returns the best identifier
        to use with the ``-a`` flag.

        Returns:
            The account identifier string, or None if not found.
        """
        import urllib.parse

        data_dir = self.SIGNAL_DATA_DIR
        if not data_dir.exists():
            return None

        # First try the direct phone number (legacy format).
        encoded_number = urllib.parse.quote(self.phone_number, safe='')
        for candidate in (self.phone_number, encoded_number):
            if (data_dir / candidate).exists():
                return self.phone_number

        # Try numbered account directories (new format in signal-cli 0.12+).
        # Each numeric directory may contain an account JSON referencing our number.
        for entry in data_dir.iterdir():
            if not entry.name.isdigit():
                continue
            try:
                import json
                with open(entry, encoding="utf-8") as f:
                    account_data = json.load(f)
                stored_number = account_data.get("number") or account_data.get("username", "")
                if stored_number == self.phone_number:
                    print(f"DEBUG: Found account with numeric ID {entry.name} for {self.phone_number}")
                    return self.phone_number
            except Exception:
                continue

        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_port_open(self) -> bool:
        """Return True if something is already listening on *self.port*."""
        import socket
        try:
            with socket.create_connection(("localhost", self.port), timeout=2):
                return True
        except (OSError, ConnectionRefusedError):
            return False

    def _cleanup_lock_files(self):
        """
        Remove stale signal-cli lock files from the data directory.

        signal-cli creates ``.lock`` files in the account data directory when
        running.  If a previous instance was killed unexpectedly the lock
        file may remain, causing the new daemon to wait indefinitely.
        """
        import urllib.parse
        import json

        data_dir = self.SIGNAL_DATA_DIR
        if not data_dir.exists():
            return

        cleaned = 0
        # Lock files may live inside per-account directories or directly in data/.
        encoded_number = urllib.parse.quote(self.phone_number, safe='')
        candidate_dirs = [
            data_dir / self.phone_number,
            data_dir / encoded_number,
        ]
        # Also search inside numeric account directories that belong to our account.
        for entry in data_dir.iterdir():
            if entry.is_dir() and entry.name.isdigit():
                # Only add if this directory contains an account file for our number.
                acct_file = entry / "account"
                for candidate_file in (acct_file, entry):
                    if candidate_file.is_file():
                        try:
                            with open(candidate_file, encoding="utf-8") as f:
                                acct = json.load(f)
                            stored = acct.get("number") or acct.get("username", "")
                            if stored == self.phone_number:
                                candidate_dirs.append(entry)
                        except Exception:
                            pass
                        break

        for acct_dir in candidate_dirs:
            if not acct_dir.is_dir():
                continue
            for lock_file in acct_dir.glob("*.lock"):
                try:
                    lock_file.unlink()
                    cleaned += 1
                    print(f"DEBUG: Removed stale lock file: {lock_file}")
                except OSError as exc:
                    print(f"WARNING: Could not remove lock file {lock_file}: {exc}")

        if cleaned:
            print(f"✓ Removed {cleaned} stale signal-cli lock file(s)")

    def _spawn_daemon(self) -> bool:
        """
        Launch ``signal-cli daemon --tcp --send-read-receipts`` and wait for it
        to start accepting connections.

        Tries ``-a`` (newer signal-cli) first; falls back to ``-u`` if the
        newer flag is not recognised by the installed version.
        """
        # Build base command using '-a' (works with both phone numbers and
        # numeric account IDs used by newer signal-cli versions).
        cmd = [
            "signal-cli",
            "-a", self.phone_number,
            "daemon",
            "--tcp",
            "--send-read-receipts",
        ]

        # Allow overriding the port via the command line if non-default.
        if self.port != self.DEFAULT_PORT:
            cmd.extend(["--tcp-port", str(self.port)])

        print(f"Starting signal-cli daemon: {' '.join(cmd)}")

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
                env={**os.environ},
            )
        except FileNotFoundError:
            print("ERROR: signal-cli not found. Please install signal-cli.")
            return False
        except Exception as exc:
            print(f"ERROR: Failed to start signal-cli daemon: {exc}")
            return False

        self._we_started_it = True
        ready = self._wait_for_ready()

        if not ready:
            # '-a' may not be supported on older signal-cli builds; retry with '-u'.
            print("DEBUG: Retrying daemon startup with legacy '-u' flag…")
            self._process = None
            self._we_started_it = False
            return self._spawn_daemon_legacy()

        return True

    def _spawn_daemon_legacy(self) -> bool:
        """Fall-back: start daemon using the legacy ``-u`` flag."""
        cmd = [
            "signal-cli",
            "-u", self.phone_number,
            "daemon",
            "--tcp",
            "--send-read-receipts",
        ]
        if self.port != self.DEFAULT_PORT:
            cmd.extend(["--tcp-port", str(self.port)])

        print(f"Starting signal-cli daemon (legacy mode): {' '.join(cmd)}")

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
                env={**os.environ},
            )
        except FileNotFoundError:
            print("ERROR: signal-cli not found. Please install signal-cli.")
            return False
        except Exception as exc:
            print(f"ERROR: Failed to start signal-cli daemon (legacy): {exc}")
            return False

        self._we_started_it = True
        return self._wait_for_ready()

    def _wait_for_ready(self) -> bool:
        """
        Poll the TCP port until it accepts connections or the timeout expires.
        Also checks that the subprocess has not crashed.
        """
        deadline = time.monotonic() + self.startup_timeout
        interval = 0.5

        while time.monotonic() < deadline:
            # Check that the process is still alive.
            if self._process is not None and self._process.poll() is not None:
                stderr_bytes = b""
                try:
                    _, stderr_bytes = self._process.communicate(timeout=2)
                except Exception:
                    pass
                stderr_text = stderr_bytes.decode(errors='replace').strip()
                print(
                    f"ERROR: signal-cli daemon exited unexpectedly "
                    f"(rc={self._process.returncode})"
                    + (f": {stderr_text}" if stderr_text else "")
                )
                self._we_started_it = False
                self._process = None
                return False

            if self._is_port_open():
                print(f"✓ signal-cli daemon ready on port {self.port}")
                return True

            time.sleep(interval)

        print(
            f"ERROR: signal-cli daemon did not become ready within "
            f"{self.startup_timeout}s"
        )
        self.stop()
        return False
