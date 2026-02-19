# Troubleshooting

## signal-cli hangs when called from Python subprocess

### Symptoms

* `subprocess.Popen` / `subprocess.run` never returns when calling `signal-cli receive`.
* Running the identical command manually from a shell works instantly.
* Bot debug output shows `returncode=0, stdout_length=0, stderr=''`.
* `process.communicate(timeout=N)` raises `TimeoutExpired`.

### Root Cause

When Python spawns a subprocess it passes down all of its open file
descriptors (fds).  The JVM inside signal-cli may block waiting for one of
those inherited fds to close (e.g. a pipe end, a socket, or a terminal that
Python is still holding open).  Because the Python process never closes those
fds, signal-cli waits indefinitely.

Additional contributing factors:

* **Session / TTY attachment** – if Python itself is attached to a terminal,
  signal-cli inherits that TTY and may behave differently than in a plain
  shell session.
* **Signal handler inheritance** – custom signal handlers set in Python are
  inherited by child processes and can interfere with the JVM's own handlers.
* **stdin not closed** – if stdin is left as the parent's stdin, the JVM may
  wait for input.

### Fix Applied

The bot's `_listen_loop` now invokes `subprocess.Popen` with the following
isolation flags:

```python
process = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    stdin=subprocess.DEVNULL,   # EOF on stdin immediately
    text=True,
    bufsize=1,
    close_fds=True,             # Don't inherit parent file descriptors
    start_new_session=True,     # Detach from parent TTY / process group
    env={**os.environ},
)
```

A **watchdog thread** (`threading.Thread`) also force-kills any process that
still hasn't exited after the hard deadline.

### Additional Tools

#### scripts/signal_cli_wrapper.sh

A bash wrapper that explicitly closes inherited fds before exec-ing
signal-cli.  Useful as a fallback if Python-level isolation is insufficient:

```bash
chmod +x scripts/signal_cli_wrapper.sh
```

Then in Python replace `'signal-cli'` with `'scripts/signal_cli_wrapper.sh'`
in the command list.

#### signalbot/utils/subprocess_debug.py

Run a diagnostic sweep that tries several subprocess invocation strategies
and reports which ones succeed:

```python
from signalbot.utils.subprocess_debug import run_signal_cli_diagnostic, print_fd_report

print_fd_report()
results = run_signal_cli_diagnostic("+64274757293")
for r in results:
    print(r)
```

#### signalbot/core/signal_cli_health.py

Pre-flight health check before starting the listen loop:

```python
from signalbot.core.signal_cli_health import check_signal_cli_health

if not check_signal_cli_health("+64274757293"):
    print("signal-cli is not responding; check installation")
```

### Checking for fd Leaks

```bash
ls -la /proc/$(pgrep -f "python.*signalbot")/fd
```

A large number of open fds (especially pipes) indicates a leak.

### Verifying the Fix

```python
import subprocess
import time

start = time.time()
process = subprocess.Popen(
    ['signal-cli', '-u', '+64274757293', 'receive', '--timeout', '3'],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    stdin=subprocess.DEVNULL,
    close_fds=True,
    start_new_session=True,
)
stdout, stderr = process.communicate(timeout=10)
duration = time.time() - start
print(f"signal-cli finished in {duration:.1f}s (should be ~3s)")
assert duration < 8, f"signal-cli hung for {duration:.1f}s"
```

### Setting Up dbus Mode (Alternative)

If subprocess-based polling continues to be unreliable, run signal-cli as a
dbus daemon:

```bash
signal-cli -u +64274757293 daemon --socket /run/user/$UID/signal-cli.sock
```

Then check availability with:

```python
from signalbot.core.signal_cli_health import check_dbus_available
check_dbus_available()
```

## Messages from phone numbers not processed

### Symptoms

Messages from UUID contacts are processed (dark ticks appear), but messages
from phone numbers are silently dropped.

### Cause

Signal's privacy features can deliver messages under the sender's UUID rather
than their phone number.  The bot's envelope parser checks both
`sourceNumber` and `source` fields, so this should be transparent.  If
messages are still missing, ensure:

1. The sender has been trusted: run `./check-trust.sh`.
2. `trustNewIdentities` is set to `ALWAYS` in the signal-cli config file.
3. No competing `signal-cli receive` processes are running
   (`ps aux | grep signal-cli`).

## Watchdog timer fires repeatedly

If you see `WARNING: signal-cli watchdog fired after Xs` in the logs, check:

1. Network latency to Signal servers (`ping signal.org`).
2. JVM heap space (`java -Xmx256m` may need increasing).
3. Whether the isolation flags above actually resolved the hanging (run the
   diagnostic utility).
