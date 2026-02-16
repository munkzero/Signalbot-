# Wallet Creation and PIN Security Features

## Overview
This implementation adds wallet management and transaction security features to the Signalbot, allowing sellers to:
1. Create new wallets with automatic backup of existing wallets
2. Protect send transactions with PIN verification
3. Access settings and admin commands via Signal messages

## Features Implemented

### 1. New Wallet Creation
Sellers can create a new Monero wallet while preserving their existing one.

**Command:** `new wallet`

**Flow:**
1. Seller sends "new wallet" via Signal
2. Bot prompts for confirmation: "Are you sure you want to create a new wallet? This will backup your current wallet. Reply 'yes' to continue or 'no' to cancel."
3. If seller replies "yes":
   - Bot backs up existing wallet with timestamp (e.g., `wallet_backup_2026-02-16_14-30-45`)
   - Creates a new wallet with empty password
   - Displays the new seed phrase (IMPORTANT: Save this!)
   - Restarts the wallet RPC
4. If seller replies "no" or anything else: operation cancelled

**Safety Features:**
- Automatic backup before wallet creation
- Clear confirmation prompt
- Seed phrase display for recovery
- Wallet password remains empty (consistent with PR #35)

### 2. PIN-Protected Transactions
Send transactions now require PIN verification for security.

**Command:** `send [amount] to [address]`

**Examples:**
- `send 1.5 to 4ABC123...`
- `send 0.5 xmr to 4XYZ789...`
- `transfer 2 to 4DEF456...`

**Flow:**
1. Seller sends send command
2. Bot requests PIN: "Enter your PIN to authorize this transaction. You have 60 seconds."
3. Seller enters PIN
4. Bot verifies PIN:
   - If correct: Sends transaction and displays TX hash and TX key
   - If incorrect: Transaction cancelled
5. PIN cleared from memory

**Security Features:**
- PIN hashed using PBKDF2 with SHA256 (100,000 iterations)
- PIN never stored in plaintext
- 60-second timeout for PIN entry
- PIN cleared from memory after use
- Separate from wallet password (application-level security)

### 3. Settings Menu
Access admin commands easily via the settings menu.

**Command:** `settings` or `menu` or `admin`

**Available Options:**
- New wallet creation
- Send transactions
- View catalog
- Help

## Technical Implementation

### Architecture

```
Seller Command (via Signal)
    ↓
BuyerHandler.handle_buyer_message()
    ↓
    ├─ Admin Commands (if seller)
    │  ├─ "settings" → send_settings_menu()
    │  ├─ "new wallet" → request_new_wallet()
    │  │                    ↓
    │  │               Confirmation Flow
    │  │                    ↓
    │  │               _execute_new_wallet()
    │  │                    ↓
    │  │               WalletSetupManager.create_new_wallet_with_backup()
    │  │
    │  └─ "send X to Y" → request_send_transaction()
    │                         ↓
    │                    PIN Session Created (60s timeout)
    │                         ↓
    │                    PIN Entry
    │                         ↓
    │                    _handle_pin_entry()
    │                         ↓
    │                    SellerManager.verify_pin()
    │                         ↓
    │                    _execute_send_transaction()
    │                         ↓
    │                    RPC JSON-RPC Call
    │
    └─ Regular Commands (buyers and sellers)
       ├─ "catalog" → send_catalog()
       ├─ "order #X" → create_order()
       └─ "help" → send_help()
```

### Key Files Modified

1. **`signalbot/core/wallet_setup.py`**
   - Added `backup_wallet()` - Creates timestamped backup
   - Added `create_new_wallet_with_backup()` - Safe wallet creation

2. **`signalbot/core/pin_manager.py`** (NEW)
   - `PINVerificationSession` - Tracks PIN sessions with timeout
   - `PINManager` - Manages session lifecycle

3. **`signalbot/core/buyer_handler.py`**
   - Admin command handling (new wallet, send, settings)
   - PIN verification flow
   - Confirmation handling
   - Transaction execution via RPC

4. **`signalbot/gui/dashboard.py`**
   - Updated BuyerHandler initialization to pass wallet_manager and seller_manager

### Wallet Password vs PIN

**Important Distinction:**

- **Wallet Password** (RPC level):
  - Remains **empty** (`""`)
  - Used by `monero-wallet-rpc`
  - Consistent with PR #35 fix

- **PIN** (Application level):
  - Application-level security in bot code
  - Does NOT affect RPC operations
  - Protects send transactions
  - Stored as PBKDF2 hash in database

These are completely separate security mechanisms.

### Database Schema

The PIN is stored in the `sellers` table:
```sql
CREATE TABLE sellers (
    id INTEGER PRIMARY KEY,
    pin_hash VARCHAR(255) NOT NULL,  -- PBKDF2 hash
    pin_salt VARCHAR(255) NOT NULL,  -- Random salt
    signal_id TEXT,                  -- Encrypted
    wallet_path VARCHAR(500),
    ...
);
```

## Usage Examples

### Creating a New Wallet

```
You: new wallet
Bot: ⚠️ CREATE NEW WALLET
     Are you sure you want to create a new wallet?
     This will:
     ✓ Backup your current wallet with timestamp
     ✓ Create a new empty wallet
     ✓ Generate a new seed phrase (SAVE IT!)
     Your current wallet will be safely backed up.
     Reply 'yes' to continue or 'no' to cancel.

You: yes
Bot: 🛑 Stopping wallet RPC...
Bot: 🔄 Creating new wallet...
Bot: ✅ NEW WALLET CREATED
     💾 Old wallet backed up to:
     /home/user/data/backups/wallet_backup_2026-02-16_14-30-45
     
     📍 Address:
     4ABC123XYZ789...
     
     🔑 SEED PHRASE (SAVE THIS!):
     abandon ability able about above absent absorb abstract...
     
     ⚠️ Write down your seed phrase and store it safely!
     This is the ONLY way to recover your wallet!
     
     🔌 Starting wallet RPC...
Bot: ✅ Wallet RPC started successfully!
```

### Sending a Transaction

```
You: send 1.5 to 4ABC123XYZ789DEF456GHI012JKL345MNO678PQR901STU234VWX567YZA890BCD123EFG456
Bot: 🔐 TRANSACTION AUTHORIZATION
     Amount: 1.5 XMR
     To: 4ABC123XYZ789DEF456GHI012JKL345MNO678PQR901STU234VWX567YZA890BCD123EFG456
     
     Enter your PIN to authorize this transaction.
     ⏱️ You have 60 seconds to enter your PIN.

You: 1234
Bot: 📤 Sending 1.5 XMR to 4ABC123...
Bot: ✅ TRANSACTION SENT
     Amount: 1.5 XMR
     To: 4ABC123XYZ789DEF456GHI012JKL345MNO678PQR901STU234VWX567YZA890BCD123EFG456
     TX Hash: abc123def456...
     TX Key: xyz789uvw012...
     
     Transaction submitted successfully!
```

### Accessing Settings

```
You: settings
Bot: ⚙️ SETTINGS MENU
     🔧 Wallet Management:
       • "new wallet" - Create a new wallet (backs up current wallet)
     
     💸 Send Transactions:
       • "send [amount] to [address]" - Send XMR (requires PIN)
       • Example: "send 1.5 to 4ABC..."
     
     📋 Catalog Management:
       • "catalog" - View your products
     
     ❓ Help:
       • "help" - Show buyer help
```

## Security Considerations

### What's Protected
- ✅ Send transactions require PIN
- ✅ PIN hashed with PBKDF2 (100,000 iterations)
- ✅ PIN never stored in plaintext
- ✅ PIN sessions have 60-second timeout
- ✅ Wallet backups created before destructive operations
- ✅ Seed phrase shown only once during wallet creation

### What's NOT Protected by PIN
- ❌ Wallet file access (file system security)
- ❌ RPC access (localhost only by default)
- ❌ Dashboard access (has separate PIN on startup)
- ❌ Incoming payments (automatic)

### Best Practices
1. **Save Your Seed Phrase**: Write down and securely store your seed phrase when creating a new wallet
2. **Strong PIN**: Use a secure PIN (not 0000 or 1234)
3. **Backup Regularly**: Keep your wallet backups in a safe location
4. **Verify Addresses**: Always double-check recipient addresses before confirming
5. **Test with Small Amounts**: Test the send feature with small amounts first

## Configuration

### Constants (in `buyer_handler.py`)
```python
RPC_SHUTDOWN_WAIT_SECONDS = 2  # Wait time after stopping RPC
XMR_TO_ATOMIC_UNITS = 1e12     # Conversion factor: 1 XMR = 1e12 atomic units
```

### Paths (in `settings.py`)
```python
WALLET_DIR = DATA_DIR / "wallet"    # Wallet files location
BACKUP_DIR = DATA_DIR / "backups"   # Backup location
```

### PIN Configuration
- Stored in database (sellers table)
- Set during initial setup wizard
- Can be changed via seller management (future feature)

## Testing

### Test Suite
Run the test suite to verify features:
```bash
python3 test_wallet_pin_features.py
```

Tests verify:
1. Wallet backup method exists and works
2. New wallet creation with backup
3. PIN manager module functionality
4. Command handler integration
5. Transaction execution
6. Empty password consistency

### Manual Testing Checklist
- [ ] Create new wallet with existing wallet (backup created?)
- [ ] Create new wallet without existing wallet
- [ ] Send transaction with correct PIN
- [ ] Send transaction with incorrect PIN
- [ ] PIN timeout (wait 61 seconds)
- [ ] Verify backup files exist
- [ ] Verify seed phrase is displayed
- [ ] Verify transaction appears in wallet

## Troubleshooting

### Issue: "Wallet management not available"
**Cause:** wallet_manager not initialized  
**Solution:** Ensure dashboard initialized the wallet before using admin commands

### Issue: "PIN verification not available"
**Cause:** seller_manager not initialized  
**Solution:** Ensure seller account exists in database

### Issue: "Wallet RPC is not running"
**Cause:** RPC process stopped or failed to start  
**Solution:** Check wallet RPC logs, restart dashboard

### Issue: "Transaction failed: insufficient funds"
**Cause:** Not enough unlocked balance  
**Solution:** Wait for confirmations or check balance

### Issue: PIN timeout
**Cause:** Waited more than 60 seconds to enter PIN  
**Solution:** Resend the transaction command and enter PIN quickly

## Future Enhancements

Potential improvements for future development:
1. Change PIN command for sellers
2. Transaction history via Signal
3. Balance check command
4. Multi-signature support
5. Address book management
6. Transaction confirmation limits
7. Rate limiting for security

## Support

For issues or questions:
1. Check logs in `data/logs/shopbot.log`
2. Review this documentation
3. Submit an issue on GitHub
4. Test with small amounts first

## Credits

Implemented as part of PR #XX following requirements from the problem statement.
Maintains compatibility with PR #35 (empty wallet password fix).
