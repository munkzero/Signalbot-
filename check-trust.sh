#!/bin/bash

# Quick script to check and fix auto-trust configuration

# Parse .env correctly (ignore comments and blank lines)
PHONE_NUMBER=$(grep -v '^#' .env 2>/dev/null | grep -v '^$' | grep '^PHONE_NUMBER=' | cut -d '=' -f2 | tr -d ' ' || echo "")

if [ -z "$PHONE_NUMBER" ]; then
    echo "❌ PHONE_NUMBER not found in .env"
    echo "Run ./setup.sh first"
    exit 1
fi

echo "========================================="
echo "Auto-Trust Configuration Checker"
echo "========================================="
echo ""
echo "Phone: $PHONE_NUMBER"
echo ""

# Find the actual config file (might be URL-encoded)
CONFIG_FILE=""
POSSIBLE_PATHS=(
    "$HOME/.local/share/signal-cli/data/$PHONE_NUMBER"
    "$HOME/.local/share/signal-cli/data/$(echo $PHONE_NUMBER | sed 's/+/%2B/g')"
)

for path in "${POSSIBLE_PATHS[@]}"; do
    if [ -f "$path" ]; then
        CONFIG_FILE="$path"
        echo "✓ Found config file: $CONFIG_FILE"
        break
    fi
done

if [ -z "$CONFIG_FILE" ]; then
    echo "❌ Config file not found for $PHONE_NUMBER"
    echo ""
    echo "Checked paths:"
    for path in "${POSSIBLE_PATHS[@]}"; do
        echo "  - $path"
    done
    echo ""
    echo "Available configs:"
    ls -la ~/.local/share/signal-cli/data/ 2>/dev/null || echo "  No data directory found"
    echo ""
    echo "Number may not be registered. Run: signal-cli -u $PHONE_NUMBER listIdentities"
    exit 1
fi

if command -v jq &> /dev/null; then
    TRUST_MODE=$(jq -r '.trustNewIdentities // "NOT_SET"' "$CONFIG_FILE" 2>/dev/null)
    echo ""
    echo "Current setting: $TRUST_MODE"
    echo ""
    
    if [ "$TRUST_MODE" = "ALWAYS" ]; then
        echo "✅ Auto-trust is ENABLED"
        echo "   Bot will accept all message requests automatically"
    else
        echo "⚠️  Auto-trust is NOT enabled (current: $TRUST_MODE)"
        echo ""
        read -p "Enable auto-trust now? (y/n): " ENABLE
        
        if [[ "$ENABLE" =~ ^[Yy]$ ]]; then
            # Backup config
            cp "$CONFIG_FILE" "$CONFIG_FILE.backup"
            
            # Update config
            jq '.trustNewIdentities = "ALWAYS"' "$CONFIG_FILE" > "${CONFIG_FILE}.tmp" && mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"
            
            echo "✅ Auto-trust enabled in config file!"
            echo "   Restart the bot: ./start.sh"
        fi
    fi
else
    echo "⚠️  'jq' not installed - cannot check config"
    echo "   Install: sudo apt install jq"
fi

echo ""
echo "========================================="
echo "Done"
echo "========================================="
