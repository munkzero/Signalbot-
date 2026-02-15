#!/bin/bash

# Quick script to check and fix auto-trust configuration

PHONE_NUMBER=$(grep PHONE_NUMBER .env | cut -d '=' -f2)

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

# Check current setting
CONFIG_FILE="$HOME/.local/share/signal-cli/data/$PHONE_NUMBER"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Config file not found: $CONFIG_FILE"
    echo "Number may not be registered"
    exit 1
fi

if command -v jq &> /dev/null; then
    TRUST_MODE=$(jq -r '.trustNewIdentities // "NOT_SET"' "$CONFIG_FILE")
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
            signal-cli -u "$PHONE_NUMBER" updateConfiguration --trust-new-identities always
            echo "✅ Auto-trust enabled!"
        fi
    fi
else
    echo "⚠️  'jq' not installed - cannot check config"
    echo "   Install: sudo apt install jq"
    echo ""
    echo "Attempting to enable auto-trust anyway..."
    signal-cli -u "$PHONE_NUMBER" updateConfiguration --trust-new-identities always
fi

echo ""
echo "========================================="
echo "Done"
echo "========================================="
