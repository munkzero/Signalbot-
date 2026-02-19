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
from typing import Optional


class SignalDaemon:
    """
    Manage the lifecycle of a signal-cli daemon process.

    If a daemon is already listening on the configured port this class will
    *not* start a second one – it will simply connect to the existing process.
    """

    # Default TCP port for the signal-cli daemon.
    DEFAULT_PORT = 7583

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

    def _spawn_daemon(self) -> bool:
        """
        Launch ``signal-cli daemon --tcp --send-read-receipts`` and wait for it
        to start accepting connections.
        """
        cmd = [
            "signal-cli",
            "-u", self.phone_number,
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
                _, stderr = self._process.communicate()
                print(
                    f"ERROR: signal-cli daemon exited unexpectedly "
                    f"(rc={self._process.returncode}): {stderr.decode(errors='replace').strip()}"
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
