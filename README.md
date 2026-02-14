# Signal Shop Bot

A privacy-focused e-commerce platform that operates via Signal messenger, allowing sellers to create secure private shops for selling digital and physical goods with automatic Monero (XMR) payment processing.

## Features

### For Sellers
- **Easy Setup Wizard**: PIN-based security, Signal linking, and Monero wallet configuration
- **Product Management**: Full CRUD operations with image support and metadata removal
- **Inventory Control**: Automatic stock tracking and low-stock warnings
- **Order Management**: Track orders, update statuses, manage shipments
- **Encrypted Storage**: All sensitive data encrypted with AES-256
- **Dual Wallet Support**: Connect via RPC or wallet file mode

### For Buyers (Mobile-First)
- **Simple Shopping**: Browse products via Signal messages
- **Text Commands**: "Show me your products", "Browse electronics", etc.
- **QR Code Payments**: Scan with mobile Monero wallet
- **Automatic Notifications**: Payment confirmations via Signal
- **Privacy-Focused**: All interactions through Signal, supports disappearing messages

### Security & Privacy
- **AES-256 Encryption**: All sensitive data encrypted at rest
- **EXIF Metadata Removal**: Product images automatically stripped of metadata
- **Commission Protection**: 7% commission system with anti-tamper mechanisms
- **PIN Protection**: Dashboard access requires secure PIN
- **Encrypted Communications**: All buyer-seller communication via Signal

## Commission System

**IMPORTANT**: This bot charges a **7% commission** on all sales. This is disclosed during setup and is non-negotiable.

- Seller receives: 93% of each sale
- Creator receives: 7% of each sale (automatically forwarded)
- Commission wallet address is encrypted and tamper-proof
- Full transparency: Commission shown on each transaction

## Installation

### Prerequisites

1. **Python 3.9 or higher**
2. **Signal CLI** (for Signal integration):
   ```bash
   # Linux/macOS
   brew install signal-cli
   # Or download from https://github.com/AsamK/signal-cli
   ```
3. **Monero Wallet RPC** (for payments):
   ```bash
   # Download from https://www.getmonero.org/downloads/
   ```

### Install Dependencies

```bash
cd Signalbot-
pip install -r requirements.txt
```

### First Run

**Recommended:** Use the startup script for automatic temp directory management:

```bash
./start.sh
```

Or run directly (without temp directory management):

```bash
python signalbot/main.py
```

The setup wizard will guide you through:
1. Creating a secure PIN
2. Linking your Signal account (QR code)
3. Configuring Monero wallet (RPC or file mode)
4. Selecting default currency

> **Note on Disk Space:** Signal-cli extracts ~127MB of native libraries to temp directories on each startup. If the application crashes, these files may not be cleaned up automatically. The `start.sh` script manages this by using a project-local temp directory and cleaning up orphaned files. See [TEMP_DIRECTORY_MANAGEMENT.md](TEMP_DIRECTORY_MANAGEMENT.md) for details.

## Configuration

### Monero Wallet Setup

#### Option A: RPC Wallet (Recommended)
Start your Monero wallet RPC:
```bash
monero-wallet-rpc --wallet-file /path/to/wallet --rpc-bind-port 18083 --disable-rpc-login
```

In the wizard, enter:
- Host: `127.0.0.1`
- Port: `18083`

#### Option B: Wallet File
- Select your wallet file (.keys)
- Enter wallet password (stored encrypted)
- Wallet opened only when needed

### Signal Setup

1. Open Signal on your phone
2. Go to Settings → Linked Devices
3. Tap "Link New Device"
4. Scan QR code from wizard

Or enter your Signal phone number directly.

## Usage

### Adding Products

1. Open dashboard
2. Go to "Products" tab
3. Click "Add Product"
4. Enter details:
   - Name
   - Description
   - Price (in your default currency)
   - Stock quantity
   - Category
   - Upload image (metadata automatically removed)

### Managing Orders

1. Go to "Orders" tab
2. View all orders with status
3. Update order status (Processing → Shipped → Delivered)
4. Add shipping/tracking info
5. Buyers automatically notified via Signal

### Buyer Interaction

Buyers interact via Signal messages:

```
Buyer: "Show me your products"
Bot: [Sends product catalog with images and prices]

Buyer: "BUY Product Name"
Bot: [Creates order, sends payment instructions with QR code]

[Buyer pays with Monero wallet]
Bot: "Payment received! Order confirmed."
```

### Signal Group Support

Bot can operate in Signal groups:
- Tag bot to browse: `@shopbot show products`
- Sensitive operations (checkout, payment) move to private DMs
- Never shares payment details in groups

## Project Structure

```
signalbot/
├── main.py                 # Entry point
├── gui/
│   ├── dashboard.py       # Seller dashboard
│   ├── wizard.py          # Setup wizard
│   └── components/        # UI components
├── core/
│   ├── signal_handler.py  # Signal messaging
│   ├── monero_wallet.py   # Wallet integration (RPC + file)
│   ├── payments.py        # Payment processing
│   ├── commission.py      # Commission system (encrypted)
│   └── security.py        # Encryption, checksums
├── models/
│   ├── product.py         # Product model
│   ├── order.py           # Order model
│   └── seller.py          # Seller configuration
├── utils/
│   ├── image_tools.py     # EXIF stripping
│   ├── qr_generator.py    # QR code generation
│   └── currency.py        # XMR conversion
├── database/
│   └── db.py              # Encrypted local storage
└── config/
    └── settings.py        # Configuration
```

## Security Notes

### Data Encryption
- All sensitive data encrypted with AES-256
- Master password required for database access
- Wallet credentials never stored in plaintext

### Image Privacy
- All uploaded images automatically stripped of:
  - GPS coordinates
  - Camera information
  - Timestamps
  - Other EXIF metadata

### Commission Protection
- Commission wallet address encrypted in code
- Checksums verify integrity
- Tampering causes bot to refuse operation
- Runtime integrity checks

### Address Storage
Configurable address storage:
- **Standard**: Encrypted storage (default)
- **Auto-delete**: Purge after delivery
- **No storage**: Manual copy from Signal

## Building for Distribution

To compile as standalone executable (Nuitka):

```bash
# Install Nuitka
pip install nuitka

# Compile (Windows)
python -m nuitka --standalone --onefile --enable-plugin=pyqt5 signalbot/main.py

# Compile (Linux)
python -m nuitka --standalone --onefile --enable-plugin=pyqt5 signalbot/main.py
```

**Before compilation**: Set commission wallet address in `core/commission.py`:

```python
from signalbot.core.commission import setup_commission_wallet

config = setup_commission_wallet(
    "YOUR_MONERO_WALLET_ADDRESS",
    "STRONG_MASTER_PASSWORD"
)

# Update ENCRYPTED_COMMISSION_WALLET, COMMISSION_WALLET_SALT, COMMISSION_CHECKSUM
# in core/commission.py with values from config
```

## Environment Variables

```bash
# Optional: Set master password (otherwise uses default)
export MASTER_PASSWORD="your_secure_password"

# Optional: Enable debug mode
export DEBUG="True"
```

## Startup and Monitoring

### Using the Startup Script (Recommended)

The `start.sh` script provides automatic temp directory management:

```bash
./start.sh
```

This script:
- Sets up a project-local temp directory (./tmp)
- Cleans up orphaned signal-cli temp files from previous crashes
- Shows current temp directory usage
- Activates the virtual environment
- Launches the application

### Monitoring Temp Directory

Check temp directory usage at any time:

```bash
./check_temp.sh
```

This will show:
- Current temp directory size
- Number of active/orphaned libsignal directories
- Alerts if usage exceeds 1GB threshold
- Recommendations for cleanup if needed

See [TEMP_DIRECTORY_MANAGEMENT.md](TEMP_DIRECTORY_MANAGEMENT.md) for detailed information about temp directory management.

## Troubleshooting

### Signal Connection Issues
- Ensure signal-cli is installed and in PATH
- Check Signal account is linked
- Verify phone number format (+1234567890)

### Monero Wallet Issues
- Check wallet RPC is running
- Verify host/port configuration
- Test connection in wizard

### Database Issues
- Check data directory permissions
- Ensure master password matches
- Delete `data/db/shopbot.db` to reset (loses all data!)

### Disk Space Issues

If you encounter "No space left on device" errors:

1. **Check temp directory usage:**
   ```bash
   ./check_temp.sh
   ```

2. **Clean up orphaned files:**
   ```bash
   ./start.sh  # Automatically cleans up old files
   ```

3. **Manual cleanup (if needed):**
   ```bash
   rm -rf ./tmp/libsignal*
   ```

4. **Check overall disk space:**
   ```bash
   df -h
   ```

See [TEMP_DIRECTORY_MANAGEMENT.md](TEMP_DIRECTORY_MANAGEMENT.md) for more details on managing temp directory disk usage.

## Development

### Running in Development Mode

```bash
export DEBUG="True"
python signalbot/main.py
```

### Testing Components

```python
# Test encryption
from signalbot.core.security import security_manager

encrypted, salt = security_manager.encrypt_string("test", "password")
decrypted = security_manager.decrypt_string(encrypted, "password", salt)

# Test wallet connection
from signalbot.core.monero_wallet import MoneroWallet

wallet = MoneroWallet(
    wallet_type='rpc',
    rpc_host='127.0.0.1',
    rpc_port=18083
)
print(wallet.test_connection())
```

## License

This project is provided as-is. The 7% commission is built into the system and cannot be removed.

## Support

For issues or questions:
1. Check troubleshooting section above
2. Verify all dependencies installed
3. Check Signal CLI and Monero wallet RPC are running

## Disclaimer

- This is experimental software
- Use at your own risk
- Ensure compliance with local laws regarding cryptocurrency and e-commerce
- The 7% commission is mandatory and cannot be disabled
- Seller responsible for taxes, legal compliance, and customer service

## Credits

Built with:
- Python 3.9+
- PyQt5 (GUI)
- Cryptography (AES-256 encryption)
- signal-cli (Signal integration)
- monero-wallet-rpc (Payments)
- Pillow (Image processing)
- qrcode (QR generation)