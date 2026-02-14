#!/bin/bash
# Signal Shop Bot - Temp Directory Monitor
# Checks temp directory usage and alerts if over threshold

# Get the script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMPDIR="$SCRIPT_DIR/tmp"

# Threshold in MB (1GB = 1024MB)
THRESHOLD_MB=1024

echo "========================================="
echo "Temp Directory Monitor"
echo "========================================="
echo ""

# Check if temp directory exists
if [ ! -d "$TMPDIR" ]; then
    echo "Status: OK (directory doesn't exist yet)"
    echo "Location: $TMPDIR"
    echo "Usage: 0 MB"
    echo ""
    echo "The temp directory will be created on first startup."
    exit 0
fi

# Get current usage in MB
USAGE_KB=$(du -sk "$TMPDIR" 2>/dev/null | cut -f1)
USAGE_MB=$((USAGE_KB / 1024))
USAGE_HUMAN=$(du -sh "$TMPDIR" 2>/dev/null | cut -f1)

echo "Location: $TMPDIR"
echo "Usage: $USAGE_HUMAN ($USAGE_MB MB)"
echo "Threshold: ${THRESHOLD_MB} MB"
echo ""

# Count libsignal directories
TOTAL_LIBSIGNAL=$(find "$TMPDIR" -maxdepth 1 -name "libsignal*" -type d 2>/dev/null | wc -l)
ORPHANED_LIBSIGNAL=$(find "$TMPDIR" -maxdepth 1 -name "libsignal*" -type d -mtime +1 2>/dev/null | wc -l)

echo "libsignal directories:"
echo "  Total: $TOTAL_LIBSIGNAL"
echo "  Orphaned (>1 day): $ORPHANED_LIBSIGNAL"
echo ""

# Check against threshold
if [ $USAGE_MB -gt $THRESHOLD_MB ]; then
    echo "⚠️  WARNING: Usage exceeds threshold!"
    echo "Status: ALERT"
    echo ""
    echo "Orphaned directories (older than 1 day):"
    echo "----------------------------------------"
    
    FOUND_ORPHANS=0
    while IFS= read -r dir; do
        if [ -d "$dir" ]; then
            SIZE=$(du -sh "$dir" 2>/dev/null | cut -f1)
            MTIME=$(stat -c %y "$dir" 2>/dev/null | cut -d' ' -f1,2 | cut -d'.' -f1)
            echo "  $dir"
            echo "    Size: $SIZE"
            echo "    Modified: $MTIME"
            FOUND_ORPHANS=1
        fi
    done < <(find "$TMPDIR" -maxdepth 1 -name "libsignal*" -type d -mtime +1 2>/dev/null)
    
    if [ $FOUND_ORPHANS -eq 0 ]; then
        echo "  (none found)"
    fi
    
    echo ""
    echo "Recommended actions:"
    echo "  1. Run start.sh to auto-cleanup orphaned directories"
    echo "  2. Or manually cleanup: rm -rf $TMPDIR/libsignal*"
    echo "  3. Consider increasing available disk space"
    
    exit 1
else
    echo "✓ Status: OK (under threshold)"
    
    if [ $ORPHANED_LIBSIGNAL -gt 0 ]; then
        echo ""
        echo "Note: $ORPHANED_LIBSIGNAL orphaned directories found."
        echo "Run start.sh to auto-cleanup, or manually remove with:"
        echo "  find $TMPDIR -name 'libsignal*' -type d -mtime +1 -exec rm -rf {} +"
    fi
    
    exit 0
fi
