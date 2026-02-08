# Signal Shop Bot - Installation & Setup Guide

## Quick Start

### 1. Install Python Dependencies

```bash
cd Signalbot-
pip install -r requirements.txt
```

This will install:
- cryptography (AES-256 encryption)
- qrcode & Pillow (QR codes & image processing)
- requests (API calls)
- sqlalchemy (database)
- PyQt5 (GUI)
- pysignalcli (Signal integration)
- monero (Monero wallet)
- python-dotenv & pydantic (utilities)

### 2. Install Signal CLI

Signal CLI is required for Signal messaging integration.

**Linux/macOS:**
```bash
# Using Homebrew
brew install signal-cli

# Or download release
wget https://github.com/AsamK/signal-cli/releases/latest/download/signal-cli-*.tar.gz
tar xf signal-cli-*.tar.gz
sudo cp -r signal-cli-* /opt/signal-cli
sudo ln -s /opt/signal-cli/bin/signal-cli /usr/local/bin/
```

**Windows:**
```powershell
# Download from GitHub releases
# https://github.com/AsamK/signal-cli/releases
# Extract to C:\Program Files\signal-cli
# Add to PATH
```

**Verify Installation:**
```bash
signal-cli --version
```

### 3. Install Monero Wallet RPC

Download Monero from https://www.getmonero.org/downloads/

**Linux:**
```bash
wget https://downloads.getmonero.org/cli/linux64
tar xf linux64
sudo cp monero-*/monero-wallet-rpc /usr/local/bin/
```

**macOS:**
```bash
# Download macOS binary from getmonero.org
# Extract and copy to /usr/local/bin/
```

**Windows:**
```powershell
# Download Windows binary
# Extract to C:\Program Files\Monero
# Add to PATH
```

**Verify Installation:**
```bash
monero-wallet-rpc --version
```

### 4. Set Up Monero Wallet

#### Option A: Use Existing Wallet (RPC Mode)

1. Start wallet RPC server:
```bash
monero-wallet-rpc \
  --wallet-file /path/to/your/wallet \
  --password "your_wallet_password" \
  --rpc-bind-port 18083 \
  --disable-rpc-login \
  --daemon-address node.moneroworld.com:18089
```

2. Keep this running in background
3. Use host: 127.0.0.1, port: 18083 in wizard

#### Option B: Use Wallet File (File Mode)

1. Locate your wallet file (e.g., my_wallet.keys)
2. Have wallet password ready
3. Select file mode in wizard
4. Bot will open/close wallet as needed

### 5. First Run

```bash
python signalbot/main.py
```

The setup wizard will launch automatically.

## Setup Wizard Walkthrough

### Step 1: Welcome & Commission Disclosure

- Read the welcome message
- Review commission terms (4% automatic)
- Click "Next" to accept and continue

### Step 2: Create Secure PIN

- Enter a PIN (minimum 6 characters/digits)
- Confirm PIN
- **REMEMBER THIS** - required to access dashboard
- Click "Next"

### Step 3: Link Signal Account

**Method 1: QR Code (Recommended)**
1. Click "Generate QR Code"
2. Open Signal on phone → Settings → Linked Devices
3. Tap "Link New Device"
4. Scan QR code shown in wizard
5. Wait for confirmation
6. Click "Next"

**Method 2: Phone Number**
1. Enter your Signal phone number (e.g., +1234567890)
2. Click "Next"

### Step 4: Configure Monero Wallet

**For RPC Mode:**
1. Select "RPC Wallet (remote)"
2. Enter RPC Host: 127.0.0.1
3. Enter RPC Port: 18083
4. Username/Password: (leave blank if disabled auth)
5. Click "Test Connection"
6. Wait for success message
7. Click "Next"

**For File Mode:**
1. Select "Wallet File (local)"
2. Click "Browse" to select wallet file
3. Enter wallet password
4. Click "Next"

### Step 5: Select Default Currency

1. Choose currency (USD, EUR, GBP, etc.)
2. This is for product pricing
3. XMR conversion happens at checkout
4. Click "Finish"

### Step 6: Complete

- Configuration saved
- Dashboard will open after PIN verification

## Using the Dashboard

### Dashboard Access

Every time you start the application:
1. Enter your PIN
2. Dashboard opens

### Managing Products

**Add Product:**
1. Click "Products" tab
2. Click "Add Product"
3. Enter:
   - Product name
   - Description
   - Price (in your default currency)
   - Stock quantity
   - Category
   - Upload image (optional)
4. Click "Save"
5. Image automatically stripped of metadata

**Edit Product:**
1. Select product in table
2. Click "Edit"
3. Update fields
4. Click "Save"

**Delete Product:**
1. Select product
2. Click "Delete"
3. Confirm deletion

### Managing Orders

**View Orders:**
1. Click "Orders" tab
2. See all orders with status

**Update Order Status:**
1. Select order
2. Click "Update Status"
3. Choose new status:
   - Processing (default)
   - Shipped (triggers buyer notification)
   - Delivered (completes order)
4. Add tracking info (optional)
5. Click "Save"

**Order Lifecycle:**
1. Buyer places order → Pending payment
2. Payment received → Paid (automatic)
3. You mark → Shipped
4. You mark → Delivered
5. If no payment → Expired (after 60 min)

## For Buyers - How Shopping Works

Buyers interact entirely through Signal messages.

### Browsing Products

```
Buyer: "Show me your products"
Bot: [Sends catalog with images and prices]
```

```
Buyer: "Browse electronics"
Bot: [Sends electronics category]
```

### Making a Purchase

```
Buyer: "BUY Product Name"
Bot: "Creating your order..."
Bot: [Sends payment instructions with QR code]
     "Pay 0.5 XMR to this address within 60 minutes"
```

### Payment

1. Buyer scans QR code with Monero wallet
2. Sends payment
3. Bot detects payment (automatic)
4. Bot sends confirmation: "Payment received!"

### Updates

```
Bot: "Your order has been shipped! Tracking: 1234567890"
```

```
Bot: "Your order has been delivered. Thank you!"
```

## Commission System

### How It Works

- Every sale: 4% goes to bot creator (you)
- Automatically deducted from payment
- Forwarded immediately after confirmation

### Example Transaction

Customer pays: 1.0 XMR
- Seller receives: 0.96 XMR (96%)
- Creator receives: 0.04 XMR (4%)

### Transparency

All commission amounts shown to seller:
```
Transaction: 1.0 XMR
Your earnings: 0.96 XMR
Commission (4%): 0.04 XMR
```

### Before Deployment

**Set Commission Wallet:**

1. Open `signalbot/core/commission.py`
2. Run setup utility:

```python
from signalbot.core.commission import setup_commission_wallet

config = setup_commission_wallet(
    "YOUR_MONERO_WALLET_ADDRESS_HERE",
    "STRONG_MASTER_PASSWORD_FOR_ENCRYPTION"
)

print(config)
```

3. Copy output values:
```python
ENCRYPTED_COMMISSION_WALLET = "paste_here"
COMMISSION_WALLET_SALT = "paste_here"
COMMISSION_CHECKSUM = "paste_here"
```

4. Replace placeholders in `commission.py`

## Building Standalone Executable

For distribution (hides source code):

```bash
pip install nuitka

# Windows
python -m nuitka \
  --standalone \
  --onefile \
  --enable-plugin=pyqt5 \
  --windows-disable-console \
  --output-filename=SignalShopBot.exe \
  signalbot/main.py

# Linux
python -m nuitka \
  --standalone \
  --onefile \
  --enable-plugin=pyqt5 \
  --output-filename=signalshopbot \
  signalbot/main.py
```

Executable will be in `main.dist/` directory.

## Advanced Configuration

### Environment Variables

```bash
# Set master encryption password
export MASTER_PASSWORD="your_secure_password_here"

# Enable debug mode
export DEBUG="True"
```

### Data Directory

All data stored in `data/`:
```
data/
├── db/shopbot.db          # Encrypted database
├── images/                # Product images (metadata stripped)
├── logs/shopbot.log       # Application logs
└── signal/                # Signal CLI data
```

### Security Best Practices

1. **PIN**: Use strong PIN (8+ characters)
2. **Master Password**: Set via environment variable
3. **Backups**: Backup `data/` directory regularly
4. **Wallet**: Use dedicated wallet for shop
5. **Signal**: Use dedicated Signal account

## Troubleshooting

### Signal Not Connecting

**Check signal-cli:**
```bash
signal-cli --version
```

**Re-link device:**
```bash
signal-cli link -n ShopBot
```

### Monero Wallet Issues

**Test RPC connection:**
```bash
curl http://127.0.0.1:18083/json_rpc \
  -d '{"jsonrpc":"2.0","id":"0","method":"get_balance"}' \
  -H 'Content-Type: application/json'
```

**Restart wallet RPC:**
```bash
killall monero-wallet-rpc
monero-wallet-rpc --wallet-file /path/to/wallet --rpc-bind-port 18083
```

### Database Locked

```bash
# Close all instances
# Delete lock file
rm data/db/shopbot.db-journal
```

### Reset Everything

**⚠️ WARNING: Deletes all data**

```bash
rm -rf data/
python signalbot/main.py  # Runs wizard again
```

## Support & Updates

### Checking for Updates

```bash
cd Signalbot-
git pull origin main
pip install -r requirements.txt --upgrade
```

### Getting Help

1. Check this guide
2. Review README.md
3. Check error logs in `data/logs/`
4. Verify all services running (Signal CLI, Wallet RPC)

## Security Reminders

- ✅ PIN required for dashboard access
- ✅ All sensitive data encrypted with AES-256
- ✅ Product images stripped of GPS/metadata
- ✅ Commission wallet tamper-protected
- ✅ Wallet credentials never in plaintext
- ✅ Buyer data encrypted in database

## Legal Compliance

⚠️ **Important**: You are responsible for:

- Tax reporting and payment
- Compliance with local e-commerce laws
- Compliance with cryptocurrency regulations
- Product legality in your jurisdiction
- Customer service and disputes
- Privacy laws (GDPR, etc.)

## Next Steps After Setup

1. ✅ Add your first products
2. ✅ Test with a friend (small order)
3. ✅ Share your Signal number
4. ✅ Monitor orders dashboard
5. ✅ Start selling with privacy!

---

**Remember**: This bot charges 4% commission on all sales. This is disclosed to you upfront and cannot be removed. The commission helps support continued development and maintenance of the platform.
