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

# Clean up orphaned libsignal directories older than 1 day
echo "Cleaning up orphaned temp files..."
CLEANED=0
if [ -d "$TMPDIR" ]; then
    # Find and remove libsignal directories older than 1 day
    while IFS= read -r dir; do
        if [ -d "$dir" ]; then
            rm -rf "$dir" 2>/dev/null && ((CLEANED++))
        fi
    done < <(find "$TMPDIR" -maxdepth 1 -name "libsignal*" -type d -mtime +1 2>/dev/null)
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
