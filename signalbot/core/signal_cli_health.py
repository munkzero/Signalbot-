"""
Health check for signal-cli availability and responsiveness.

Provides a lightweight pre-flight check that verifies signal-cli can be
invoked from a Python subprocess without hanging, and surfaces actionable
diagnostics when it cannot.
"""

import subprocess
import threading
import time
import os
from typing import Optional


# Maximum seconds to wait for the health-check subprocess before declaring
# signal-cli unresponsive.
_HEALTH_CHECK_HARD_TIMEOUT = 10
# signal-cli --timeout value used during health checks (short, just enough to
# get a response or an empty receive).
_HEALTH_CHECK_RECEIVE_TIMEOUT = 2


def _run_receive_with_isolation(
    phone_number: str,
    receive_timeout: int = _HEALTH_CHECK_RECEIVE_TIMEOUT,
    hard_timeout: float = _HEALTH_CHECK_HARD_TIMEOUT,
) -> dict:
    """
    Invoke ``signal-cli receive`` in an isolated subprocess and return a result
    dict.  Isolation flags mirror those used in the main listen loop.

    Args:
        phone_number: Signal account phone number.
        receive_timeout: Value passed to ``--timeout`` in the signal-cli call.
        hard_timeout: Absolute deadline (seconds) before force-killing.

    Returns:
        Dict with keys: returncode, stdout, stderr, duration_s, timed_out,
        error.
    """
    cmd = [
        "signal-cli",
        "--output", "json",
        "-u", phone_number,
        "receive",
        "--timeout", str(receive_timeout),
    ]

    result = {
        "returncode": None,
        "stdout": "",
        "stderr": "",
        "duration_s": 0.0,
        "timed_out": False,
        "error": None,
    }

    start = time.monotonic()
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            close_fds=True,
            start_new_session=True,
            env={**os.environ},
        )

        killed = threading.Event()

        def _watchdog(proc, event):
            if not event.wait(timeout=hard_timeout):
                result["timed_out"] = True
                try:
                    proc.kill()
                except OSError:
                    pass

        wt = threading.Thread(target=_watchdog, args=(process, killed), daemon=True)
        wt.start()
        try:
            stdout, stderr = process.communicate(timeout=hard_timeout)
            result["stdout"] = stdout
            result["stderr"] = stderr
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            result["timed_out"] = True
        finally:
            killed.set()

        result["returncode"] = process.returncode
    except FileNotFoundError:
        result["error"] = "signal-cli not found in PATH"
    except Exception as exc:
        result["error"] = str(exc)

    result["duration_s"] = round(time.monotonic() - start, 3)
    return result


def check_signal_cli_health(
    phone_number: str,
    retries: int = 2,
    retry_delay: float = 2.0,
) -> bool:
    """
    Verify that signal-cli responds without hanging.

    Runs a short ``receive`` command up to *retries* times.  Considers the
    check passed if signal-cli exits within the hard timeout (even with a
    non-zero return code, which can be normal when there are no messages).

    Args:
        phone_number: Registered Signal phone number.
        retries: Maximum number of attempts.
        retry_delay: Seconds to wait between retries.

    Returns:
        True if signal-cli responded before the hard timeout, False otherwise.
    """
    for attempt in range(1, retries + 1):
        print(
            f"[signal_cli_health] Health check attempt {attempt}/{retries} "
            f"for {phone_number} ..."
        )
        result = _run_receive_with_isolation(phone_number)

        if result["error"]:
            print(f"[signal_cli_health] Error: {result['error']}")
            if attempt < retries:
                time.sleep(retry_delay)
            continue

        if result["timed_out"]:
            print(
                f"[signal_cli_health] ⚠ signal-cli DID NOT respond within "
                f"{_HEALTH_CHECK_HARD_TIMEOUT}s (attempt {attempt}/{retries})"
            )
            if attempt < retries:
                time.sleep(retry_delay)
            continue

        # Responded in time - health check passes
        print(
            f"[signal_cli_health] ✓ signal-cli responded in "
            f"{result['duration_s']}s (rc={result['returncode']})"
        )
        return True

    print(
        "[signal_cli_health] ✗ signal-cli health check failed after "
        f"{retries} attempt(s). See TROUBLESHOOTING.md for help."
    )
    return False


def check_dbus_available() -> bool:
    """
    Check whether a signal-cli dbus daemon is reachable on the session bus.

    Returns:
        True if the dbus service is available, False otherwise.
    """
    try:
        result = subprocess.run(
            [
                "dbus-send",
                "--session",
                "--print-reply",
                "--dest=org.asamk.Signal",
                "/org/asamk/Signal",
                "org.freedesktop.DBus.Peer.Ping",
            ],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=3,
        )
        available = result.returncode == 0
        if available:
            print("[signal_cli_health] ✓ signal-cli dbus daemon is available")
        else:
            print("[signal_cli_health] ✗ signal-cli dbus daemon not available")
        return available
    except FileNotFoundError:
        print("[signal_cli_health] ✗ dbus-send not found; dbus mode unavailable")
        return False
    except subprocess.TimeoutExpired:
        print("[signal_cli_health] ✗ dbus ping timed out")
        return False
    except Exception as exc:
        print(f"[signal_cli_health] ✗ dbus check error: {exc}")
        return False
