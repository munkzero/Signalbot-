#!/bin/bash
# Signal Shop Bot - Startup Script
# Manages temp directory for signal-cli native libraries

# Get the script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Use project-local temp directory instead of /tmp
export TMPDIR="$SCRIPT_DIR/tmp"
export JAVA_TOOL_OPTIONS="-Djava.io.tmpdir=$TMPDIR"

# Ensure directory exists
mkdir -p "$TMPDIR"

echo "========================================="
echo "Signal Shop Bot - Starting"
echo "========================================="

# Clean up orphaned libsignal directories older than 60 minutes
echo "Cleaning up orphaned temp files..."
CLEANED=0
if [ -d "$TMPDIR" ]; then
    # Find and remove libsignal directories older than 60 minutes
    while IFS= read -r dir; do
        if [ -d "$dir" ]; then
            rm -rf "$dir" 2>/dev/null && ((CLEANED++))
        fi
    done < <(find "$TMPDIR" -maxdepth 1 -name "libsignal*" -type d -mmin +60 2>/dev/null)
fi

if [ $CLEANED -gt 0 ]; then
    echo "✓ Cleaned up $CLEANED orphaned libsignal directories"
else
    echo "✓ No orphaned directories found"
fi

# Show temp directory usage
echo ""
echo "Temp directory: $TMPDIR"
if [ -d "$TMPDIR" ]; then
    USAGE=$(du -sh "$TMPDIR" 2>/dev/null | cut -f1)
    echo "Current usage: $USAGE"
    
    # Count active libsignal directories
    LIBSIGNAL_COUNT=$(find "$TMPDIR" -maxdepth 1 -name "libsignal*" -type d 2>/dev/null | wc -l)
    echo "Active libsignal directories: $LIBSIGNAL_COUNT"
else
    echo "Current usage: 0B (directory will be created)"
fi

echo ""
echo "========================================="

# Start background cleanup daemon
if [ ! -f "$SCRIPT_DIR/cleanup_daemon.pid" ] || ! kill -0 $(cat "$SCRIPT_DIR/cleanup_daemon.pid" 2>/dev/null) 2>/dev/null; then
    # Create logs directory if it doesn't exist
    mkdir -p "$SCRIPT_DIR/logs"
    
    # Start cleanup daemon in background
    "$SCRIPT_DIR/cleanup_daemon.sh" >> "$SCRIPT_DIR/logs/cleanup.log" 2>&1 &
    echo $! > "$SCRIPT_DIR/cleanup_daemon.pid"
    echo "✓ Cleanup daemon started (PID: $(cat "$SCRIPT_DIR/cleanup_daemon.pid"))"
else
    echo "✓ Cleanup daemon already running (PID: $(cat "$SCRIPT_DIR/cleanup_daemon.pid"))"
fi

echo ""
echo "========================================="
echo "Java Optimizations for signal-cli"
echo "========================================="

# Force IPv4 (IPv6 is broken on this network - 100% packet loss)
# Optimize JVM for faster startup
# Reduce memory footprint
export JAVA_OPTS="-Djava.net.preferIPv4Stack=true \
                  -Djava.net.preferIPv4Addresses=true \
                  -XX:+TieredCompilation \
                  -XX:TieredStopAtLevel=1 \
                  -XX:+UseParallelGC \
                  -Xms64m \
                  -Xmx128m"

# Update JAVA_TOOL_OPTIONS to include both temp dir and optimizations
export JAVA_TOOL_OPTIONS="-Djava.io.tmpdir=$TMPDIR $JAVA_OPTS"

echo "✓ Java optimized for signal-cli:"
echo "  - IPv4 forced (IPv6 broken)"
echo "  - Fast JVM startup enabled"
echo "  - Memory: 64-128MB"
echo ""

echo "========================================="
echo "Validating Configuration"
echo "========================================="

# Check if .env exists
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo "✗ .env file not found!"
    echo ""
    echo "Run the setup wizard:"
    echo "  ./setup.sh"
    echo ""
    exit 1
fi

# Load .env
set -a
source "$SCRIPT_DIR/.env" 2>/dev/null
set +a

# Check PHONE_NUMBER is set
if [ -z "$PHONE_NUMBER" ]; then
    echo "✗ PHONE_NUMBER not set in .env!"
    echo ""
    echo "Run the setup wizard:"
    echo "  ./setup.sh"
    echo ""
    exit 1
fi

# Validate format (intentionally loose to support international numbers)
# Accepts any number with + followed by 10-15 digits total
# This covers most countries (e.g., +1XXXXXXXXXX for US, +64XXXXXXXXX for NZ)
if [[ ! "$PHONE_NUMBER" =~ ^\+[0-9]{10,15}$ ]]; then
    echo "✗ Invalid PHONE_NUMBER format in .env: $PHONE_NUMBER"
    echo ""
    echo "Must start with + and contain 10-15 digits total"
    echo "Examples: +64274757293 (NZ), +15551234567 (US)"
    echo ""
    echo "Run the setup wizard to fix:"
    echo "  ./setup.sh"
    echo ""
    exit 1
fi

# Check if registered with signal-cli
echo "Verifying Signal account: $PHONE_NUMBER"

if signal-cli -u "$PHONE_NUMBER" listIdentities &>/dev/null; then
    echo "✓ $PHONE_NUMBER is registered"
else
    echo "✗ $PHONE_NUMBER not registered with signal-cli!"
    echo ""
    echo "Available accounts:"
    signal-cli listAccounts 2>/dev/null || echo "  (none)"
    echo ""
    echo "You need to either:"
    echo "  1. Link device: signal-cli link -n 'SignalBot-Desktop'"
    echo "  2. Register: signal-cli -u $PHONE_NUMBER register"
    echo ""
    echo "Or update .env with correct number: ./setup.sh"
    echo ""
    exit 1
fi

echo "✓ Configuration valid"
echo ""

echo "========================================="

# Change to project directory
cd "$SCRIPT_DIR" || exit 1

# Activate virtual environment if it exists
if [ -d "venv/bin" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
elif [ -d "env/bin" ]; then
    echo "Activating virtual environment..."
    source env/bin/activate
else
    echo "Warning: No virtual environment found"
fi

# Set log level (DEBUG for development, INFO for production)
export LOG_LEVEL="${LOG_LEVEL:-INFO}"
echo "Log level: $LOG_LEVEL"
echo ""

# Launch the application
echo "Starting Signal Shop Bot..."
echo ""
python3 signalbot/main.py

# Capture exit code
EXIT_CODE=$?

echo ""
echo "========================================="
echo "Signal Shop Bot - Stopped (exit code: $EXIT_CODE)"
echo "========================================="

exit $EXIT_CODE
