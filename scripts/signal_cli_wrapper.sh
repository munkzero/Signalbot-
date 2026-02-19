#!/bin/bash
# Wrapper to isolate signal-cli from Python's subprocess environment.
#
# When signal-cli is called from a Python subprocess it can inherit open file
# descriptors, signal handlers, and a controlling TTY from the Python process.
# Any of these can cause signal-cli (a JVM application) to block waiting on an
# fd that will never become ready, making the subprocess appear to hang.
#
# This wrapper defends against the hang by:
#   1. Redirecting stdin from /dev/null so the JVM never blocks on user input.
#   2. Closing all non-standard file descriptors (3-1023) before exec-ing so
#      signal-cli cannot inherit leaked fds from the parent Python process.
#   3. Using exec so no extra shell process remains after signal-cli exits.
#
# Usage (from Python):
#   cmd = ['/path/to/scripts/signal_cli_wrapper.sh', '--output', 'json',
#          '-u', phone_number, 'receive', '--timeout', '30']

# Redirect stdin from /dev/null
exec 0</dev/null

# Close all non-standard file descriptors to prevent fd inheritance
for fd in $(seq 3 1023); do
    eval "exec $fd>&-" 2>/dev/null
done

# Replace this shell process with signal-cli (no extra shell in process tree)
exec signal-cli "$@"
