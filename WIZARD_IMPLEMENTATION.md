# Wizard Implementation - In-House Wallet Creation

## Overview

The setup wizard has been completely rewritten to implement in-house Monero wallet creation with full seed phrase management and security features.

## Changes Made

### Removed
- `WalletPage` (old view-only/RPC selection page)
- Support for `wallet_type` and `wallet_config` in Seller model
- `MoneroWalletFactory` usage

### Added New Pages

1. **NodeConfigPage** - Select Monero node
   - Default nodes from `DEFAULT_NODES` config
   - Option to configure custom node
   - Conditional navigation to CustomNodePage if needed

2. **CustomNodePage** - Configure custom node
   - Node address/port input
   - SSL/TLS option
   - Optional authentication (username/password)
   - Validation of inputs

3. **WalletPasswordPage** - Create wallet password
   - Password strength indicator
   - Real-time strength feedback (weak/good/strong)
   - Minimum 8 characters requirement
   - Password confirmation

4. **WalletCreationPage** - Wallet generation progress
   - Background thread (`WalletCreationWorker`) for wallet creation
   - Progress bar and status updates
   - Calls `InHouseWallet.create_new_wallet()`
   - Generates 25-word seed phrase

5. **SeedPhrasePage** - Display and backup seed phrase
   - 25-word grid display (5x5 layout)
   - Critical security warnings
   - Copy to clipboard functionality
   - Save to file functionality
   - User confirmation required

6. **SeedVerificationPage** - Verify seed phrase backup
   - Randomly selects 3 words from the seed
   - User must enter correct words
   - Prevents advancing without correct verification
   - Ensures user has properly backed up seed

7. **WalletSummaryPage** - Show wallet info
   - Displays wallet path
   - Shows primary address (truncated)
   - Connected node information
   - Sync status message

### Updated Pages

- **SetupWizard** - Main wizard class
  - Added `NodeManager` for node configuration
  - Stores `wallet_path` and `seed_phrase`
  - Page ID tracking for conditional navigation
  - `save_configuration()` updated to:
    - Save node configuration via `NodeManager`
    - Create seller with `wallet_path` only (no wallet_type/config)
    - Proper error handling

- **WelcomePage, PINPage, SignalPage, CurrencyPage** - Unchanged
  - These pages remain as they were

## Flow Diagram

```
WelcomePage
    ↓
PINPage
    ↓
SignalPage
    ↓
NodeConfigPage
    ├─→ (Default Node) → WalletPasswordPage
    └─→ (Custom Node) → CustomNodePage → WalletPasswordPage
                            ↓
                    WalletCreationPage (background thread)
                            ↓
                    SeedPhrasePage (display + backup)
                            ↓
                    SeedVerificationPage (verify 3 random words)
                            ↓
                    WalletSummaryPage
                            ↓
                    CurrencyPage
                            ↓
                    FINISH (save to database)
```

## Security Features

### Password Protection
- Minimum 8 character requirement
- Real-time strength indicator
- Password confirmation
- Encrypted wallet file

### Seed Phrase Management
- 25-word Monero seed phrase
- Multiple backup options (write down, copy, save file)
- Critical security warnings displayed
- Verification of 3 random words
- Cannot proceed without acknowledgment

### Data Protection
- Node credentials encrypted in database (if provided)
- Signal ID encrypted
- PIN hashed with salt
- Wallet password used to encrypt wallet file

## Key Components

### WalletCreationWorker (QThread)
```python
- Runs wallet creation in background
- Emits progress signals (10%, 30%, 60%, 100%)
- Creates wallet directory if needed
- Calls InHouseWallet.create_new_wallet()
- Returns wallet_path and seed_phrase
```

### InHouseWallet Integration
```python
wallet, seed_phrase = InHouseWallet.create_new_wallet(
    wallet_name=f"shop_wallet_{timestamp}",
    password=user_password,
    daemon_address=node_config.address,
    daemon_port=node_config.port,
    use_ssl=node_config.use_ssl
)
```

### Node Configuration
```python
# Default node
node_config = MoneroNodeConfig(
    address=node_data['address'],
    port=node_data['port'],
    use_ssl=node_data['use_ssl'],
    node_name=node_data['name']
)

# Custom node
node_config = MoneroNodeConfig(
    address=custom_address,
    port=custom_port,
    use_ssl=use_ssl_checkbox,
    username=optional_username,
    password=optional_password,
    node_name="Custom Node"
)
```

### Seller Creation
```python
seller = Seller(
    signal_id=signal_phone,
    wallet_path=wallet.wallet_path,  # Only field needed now
    default_currency=currency
)
```

## User Experience

### Simplified Flow
1. User selects a node (or enters custom)
2. Creates wallet password
3. Wallet is created automatically
4. Seed phrase is displayed with clear warnings
5. User backs up seed phrase
6. User verifies they backed it up correctly
7. Setup complete!

### Safety Features
- Cannot skip seed phrase backup
- Must verify seed phrase before continuing
- Multiple warnings about seed phrase importance
- Clear instructions at each step

### Error Handling
- Wallet creation failures show detailed error
- Returns to previous page on error
- Input validation at each step
- Node configuration validation

## Testing

Run the verification test:
```bash
python test_wizard_implementation.py
```

This tests:
- All required classes exist
- Correct imports (InHouseWallet, NodeManager, etc.)
- Seed phrase handling
- Security features
- Flow logic
- Background thread usage

## Migration Notes

### From Old Wizard
- Old: User chose between view-only and RPC
- New: Always creates in-house wallet
- Old: wallet_type and wallet_config fields
- New: Only wallet_path field

### Database Changes Required
- Seller model must have `wallet_path` field
- Remove `wallet_type` and `wallet_config` if present
- MoneroNode table must exist for node configuration

## Future Enhancements

Potential improvements:
1. Seed phrase print functionality
2. QR code for seed phrase (for advanced users)
3. Test node connection before proceeding
4. Estimate sync time based on blockchain height
5. Option to restore from existing seed
6. Multi-language support for seed words

## File Size
- Original wizard.py: ~539 lines
- New wizard.py: ~1073 lines (100% increase)
- Added functionality: 7 new pages, background threading, seed management

## Dependencies
- PyQt5 (QWizard, QThread, widgets)
- InHouseWallet from core.monero_wallet
- MoneroNodeConfig, NodeManager from models.node
- Seller, SellerManager from models.seller
- DEFAULT_NODES from config.settings
