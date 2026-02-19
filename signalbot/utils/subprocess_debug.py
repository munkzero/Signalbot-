"""
Subprocess diagnostic utilities for signal-cli.

Helps identify why signal-cli may hang or produce no output when called from
a Python subprocess by logging the environment, open file descriptors, and
the results of several different subprocess invocation strategies.
"""

import os
import subprocess
import time
import threading
from typing import Optional


def log_open_fds() -> list:
    """
    Return a list of file descriptors currently open in this process.

    Useful for diagnosing fd leaks that could cause signal-cli to block when
    it inherits fds that will never close.

    Returns:
        List of open fd numbers.
    """
    fd_dir = "/proc/self/fd"
    if not os.path.isdir(fd_dir):
        return []

    open_fds = []
    try:
        for entry in os.listdir(fd_dir):
            try:
                fd = int(entry)
                target = os.readlink(os.path.join(fd_dir, entry))
                open_fds.append((fd, target))
            except (ValueError, OSError):
                pass
    except OSError:
        pass

    return open_fds


def log_environment_diff(reference_env: Optional[dict] = None) -> dict:
    """
    Return the current process environment, optionally diffed against a
    reference snapshot.

    Args:
        reference_env: A previous snapshot of os.environ to compare against.

    Returns:
        Dict with keys 'current', 'added', 'removed', 'changed'.
    """
    current = dict(os.environ)
    result = {"current": current}

    if reference_env is not None:
        added = {k: current[k] for k in current if k not in reference_env}
        removed = {k: reference_env[k] for k in reference_env if k not in current}
        changed = {
            k: (reference_env[k], current[k])
            for k in current
            if k in reference_env and current[k] != reference_env[k]
        }
        result["added"] = added
        result["removed"] = removed
        result["changed"] = changed

    return result


def _run_with_method(
    cmd: list,
    method_name: str,
    kwargs: dict,
    hard_timeout: float,
) -> dict:
    """
    Run *cmd* with the given Popen *kwargs* and return a diagnostics dict.

    Args:
        cmd: Command + args list.
        method_name: Human-readable label for this invocation method.
        kwargs: Extra kwargs passed to subprocess.Popen.
        hard_timeout: Seconds before forcibly killing the process.

    Returns:
        Dict with keys: method, returncode, stdout_len, stderr_snippet,
        duration_s, timed_out, error.
    """
    result = {
        "method": method_name,
        "returncode": None,
        "stdout_len": 0,
        "stderr_snippet": "",
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
            **kwargs,
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
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            result["timed_out"] = True
            stdout, stderr = "", ""
        finally:
            killed.set()

        result["returncode"] = process.returncode
        result["stdout_len"] = len(stdout)
        result["stderr_snippet"] = (stderr or "")[:200]
    except Exception as exc:
        result["error"] = str(exc)

    result["duration_s"] = round(time.monotonic() - start, 3)
    return result


def run_signal_cli_diagnostic(
    phone_number: str,
    receive_timeout: int = 3,
    hard_timeout: float = 10.0,
) -> list:
    """
    Run signal-cli ``receive`` with several different subprocess strategies and
    return a list of diagnostic result dicts.

    This is intended as a pre-flight check to identify which (if any)
    invocation method works reliably on the current system.

    Args:
        phone_number: Registered Signal phone number (e.g. "+64274757293").
        receive_timeout: Value passed to signal-cli ``--timeout``.
        hard_timeout: Maximum seconds to wait for each attempt before giving up.

    Returns:
        List of result dicts (one per method tried).
    """
    base_cmd = [
        "signal-cli",
        "--output", "json",
        "-u", phone_number,
        "receive",
        "--timeout", str(receive_timeout),
    ]

    methods = [
        (
            "default (no extra flags)",
            {},
        ),
        (
            "close_fds=True",
            {"close_fds": True},
        ),
        (
            "start_new_session=True",
            {"start_new_session": True},
        ),
        (
            "close_fds=True + start_new_session=True",
            {"close_fds": True, "start_new_session": True},
        ),
    ]

    results = []
    for label, kwargs in methods:
        print(f"[subprocess_debug] Trying method: {label} ...")
        diag = _run_with_method(base_cmd, label, kwargs, hard_timeout)
        status = "HUNG" if diag["timed_out"] else f"rc={diag['returncode']}"
        print(
            f"[subprocess_debug]   → {status}, "
            f"stdout_len={diag['stdout_len']}, "
            f"duration={diag['duration_s']}s"
        )
        if diag["stderr_snippet"]:
            print(f"[subprocess_debug]   stderr: {diag['stderr_snippet']!r}")
        results.append(diag)

    return results


def print_fd_report():
    """Print a human-readable report of open file descriptors."""
    fds = log_open_fds()
    if not fds:
        print("[subprocess_debug] (fd report not available on this platform)")
        return

    print(f"[subprocess_debug] Open file descriptors ({len(fds)} total):")
    for fd, target in sorted(fds):
        print(f"  fd {fd:3d} -> {target}")
