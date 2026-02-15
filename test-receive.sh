#!/bin/bash

# Test message receiving in isolation

set -e

# Parse PHONE_NUMBER from .env
PHONE_NUMBER=$(grep -v '^#' .env 2>/dev/null | grep -v '^$' | grep '^PHONE_NUMBER=' | cut -d '=' -f2 | tr -d ' ' || echo "")

if [ -z "$PHONE_NUMBER" ]; then
    echo "❌ PHONE_NUMBER not found in .env"
    exit 1
fi

echo "========================================="
echo "Signal Message Receiving Test"
echo "========================================="
echo ""
echo "Phone: $PHONE_NUMBER"
echo ""
echo "This script will listen for messages for 30 seconds."
echo "Send a test message to $PHONE_NUMBER now!"
echo ""
echo "Listening..."
echo ""

# Listen for messages with verbose output
timeout 30 signal-cli -u "$PHONE_NUMBER" receive --json || true

echo ""
echo "========================================="
echo "Test Complete"
echo "========================================="
echo ""
echo "If you saw JSON output above, messages are being received!"
echo "If no output, check:"
echo "  1. Is $PHONE_NUMBER registered? Run: signal-cli listAccounts"
echo "  2. Did you send a message during the 30 second window?"
echo "  3. Is signal-cli working? Run: signal-cli -u $PHONE_NUMBER listIdentities"
