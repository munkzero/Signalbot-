#!/bin/bash
# Background cleanup daemon - runs every 30 minutes

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP_DIR="$SCRIPT_DIR/tmp"

echo "🧹 Cleanup daemon starting..."
echo "   Monitoring: $TMP_DIR"
echo "   Cleanup interval: 30 minutes"
echo "   Orphan threshold: 30 minutes old"
echo ""

while true; do
    # Clean orphaned libsignal directories older than 30 minutes
    CLEANED=0
    if [ -d "$TMP_DIR" ]; then
        while IFS= read -r dir; do
            if [ -d "$dir" ]; then
                rm -rf "$dir" 2>/dev/null && ((CLEANED++))
            fi
        done < <(find "$TMP_DIR" -maxdepth 1 -name "libsignal*" -type d -mmin +30 2>/dev/null)
    fi
    
    # Get current usage
    USAGE=$(du -sh "$TMP_DIR" 2>/dev/null | cut -f1)
    TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
    
    if [ "$CLEANED" -gt 0 ]; then
        echo "[$TIMESTAMP] 🗑️  Cleaned $CLEANED orphaned directories - Usage: $USAGE"
    else
        echo "[$TIMESTAMP] ✓ No cleanup needed - Usage: $USAGE"
    fi
    
    # Wait 30 minutes (1800 seconds)
    sleep 1800
done
