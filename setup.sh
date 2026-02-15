#!/bin/bash

echo "========================================="
echo "Signal Shop Bot - Setup Wizard"
echo "========================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "This script will help you configure your Signal phone number."
echo ""

# Check if signal-cli is installed
if ! command -v signal-cli &> /dev/null; then
    echo -e "${RED}✗ signal-cli not found!${NC}"
    echo "  Please install signal-cli first:"
    echo "  https://github.com/AsamK/signal-cli"
    exit 1
fi

echo -e "${GREEN}✓ signal-cli found${NC}"
echo ""

# Get phone number
echo "Enter your Signal phone number (format: +[country_code][number]):"
read -p "> " PHONE_NUMBER

# Validate format (intentionally loose to support international numbers)
# Accepts any number with + followed by 10-15 digits total
# This covers most countries (e.g., +1XXXXXXXXXX for US, +64XXXXXXXXX for NZ)
if [[ ! "$PHONE_NUMBER" =~ ^\+[0-9]{10,15}$ ]]; then
    echo -e "${RED}✗ Invalid phone number format!${NC}"
    echo "  Must start with + and contain 10-15 digits total"
    echo "  Examples: +64274757293 (NZ), +15551234567 (US)"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Phone number format valid${NC}"
echo ""

# Check if number is registered with signal-cli
echo "Checking if $PHONE_NUMBER is registered with signal-cli..."

# List accounts
ACCOUNTS=$(signal-cli listAccounts 2>/dev/null | grep -o '+[0-9]*')

if echo "$ACCOUNTS" | grep -q "$PHONE_NUMBER"; then
    echo -e "${GREEN}✓ $PHONE_NUMBER is registered with signal-cli${NC}"
else
    echo -e "${YELLOW}⚠ $PHONE_NUMBER not found in signal-cli accounts${NC}"
    echo ""
    echo "Available accounts:"
    if [ -z "$ACCOUNTS" ]; then
        echo "  (none)"
    else
        echo "$ACCOUNTS" | sed 's/^/  /'
    fi
    echo ""
    echo "You need to either:"
    echo "  1. Link this number: signal-cli link -n 'SignalBot'"
    echo "  2. Register directly: signal-cli -u $PHONE_NUMBER register"
    echo ""
    read -p "Continue anyway? (y/n): " CONTINUE
    if [[ ! "$CONTINUE" =~ ^[Yy]$ ]]; then
        echo "Setup cancelled."
        exit 1
    fi
fi

echo ""

# Configure auto-trust for all contacts
echo "Configuring automatic message acceptance..."

# Configure signal-cli to auto-trust all new contacts
if signal-cli -u "$PHONE_NUMBER" updateConfiguration --trust-new-identities always &>/dev/null; then
    echo -e "${GREEN}✓ Auto-trust enabled for all contacts${NC}"
else
    echo -e "${YELLOW}⚠ Could not enable auto-trust (may not be supported in this signal-cli version)${NC}"
    echo "  Attempting alternative method..."
    
    # Alternative: Update config file directly
    CONFIG_FILE="$HOME/.local/share/signal-cli/data/$PHONE_NUMBER"
    if [ -f "$CONFIG_FILE" ]; then
        # Backup config
        cp "$CONFIG_FILE" "$CONFIG_FILE.backup"
        
        # Update trust setting using jq if available
        if command -v jq &> /dev/null; then
            jq '.trustNewIdentities = "ALWAYS"' "$CONFIG_FILE" > "$CONFIG_FILE.tmp" && mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"
            echo -e "${GREEN}✓ Auto-trust enabled via config file${NC}"
        else
            echo -e "${YELLOW}⚠ Install 'jq' for automatic config: sudo apt install jq${NC}"
            echo "  Or manually edit: $CONFIG_FILE"
            echo "  Set: \"trustNewIdentities\": \"ALWAYS\""
        fi
    fi
fi

# Trust self (for testing)
if signal-cli -u "$PHONE_NUMBER" trust "$PHONE_NUMBER" -a &>/dev/null; then
    echo -e "${GREEN}✓ Self-trust configured${NC}"
fi

echo ""
echo -e "${GREEN}✓ Bot will automatically accept ALL message requests${NC}"
echo "  (Required for business bot - customers get instant responses)"

echo ""

# Create or update .env file
echo "Updating configuration..."

if [ -f "$ENV_FILE" ]; then
    # Backup existing .env with timestamp
    BACKUP_FILE="$ENV_FILE.backup.$(date +%Y%m%d_%H%M%S 2>/dev/null || echo "old")"
    if cp "$ENV_FILE" "$BACKUP_FILE" 2>/dev/null; then
        echo -e "${GREEN}✓ Backed up existing .env to: $BACKUP_FILE${NC}"
    else
        echo -e "${YELLOW}⚠ Could not create backup${NC}"
    fi
fi

# Create/update .env
# Note: PHONE_NUMBER, SIGNAL_USERNAME, and SELLER_SIGNAL_ID are kept for backward compatibility
# with different parts of the codebase. They all reference the same phone number.
cat > "$ENV_FILE" << EOF
# Signal Configuration
# Updated: $(date)
# Note: PHONE_NUMBER is the primary configuration variable.
# SIGNAL_USERNAME and SELLER_SIGNAL_ID are aliases kept for backward compatibility.
PHONE_NUMBER=$PHONE_NUMBER
SIGNAL_USERNAME=$PHONE_NUMBER
SELLER_SIGNAL_ID=$PHONE_NUMBER

# Database
DATABASE_PATH=data/shop.db

# Logging
LOG_LEVEL=DEBUG

# Server
HOST=0.0.0.0
PORT=5000
EOF

chmod 600 "$ENV_FILE"
echo -e "${GREEN}✓ Configuration saved to .env${NC}"
echo ""

# Test the number
echo "Testing signal-cli with $PHONE_NUMBER..."

if signal-cli -u "$PHONE_NUMBER" listIdentities &>/dev/null; then
    echo -e "${GREEN}✓ signal-cli can access $PHONE_NUMBER${NC}"
    
    # Show identity info
    echo ""
    echo "Account information:"
    signal-cli -u "$PHONE_NUMBER" listIdentities 2>/dev/null | head -3
else
    echo -e "${RED}✗ Cannot access $PHONE_NUMBER with signal-cli${NC}"
    echo ""
    echo "This might mean:"
    echo "  - Number not registered/linked yet"
    echo "  - Permission issues"
    echo ""
    echo "Try running:"
    echo "  signal-cli link -n 'SignalBot-Desktop'"
fi

echo ""
echo "========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "========================================="
echo ""
echo "Configuration:"
echo "  Phone: $PHONE_NUMBER"
echo "  Config: $ENV_FILE"
echo ""
echo "Next steps:"
echo "  1. Review your .env file: cat .env"
echo "  2. Start the bot: ./start.sh"
echo ""
echo "To change number later, run: ./setup.sh"
echo ""
