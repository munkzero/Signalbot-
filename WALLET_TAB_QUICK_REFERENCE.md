# WalletTab Quick Reference Guide

## Quick Stats
- **Total Implementation**: 843 lines of code
- **Worker Threads**: 4 classes
- **Dialogs**: 3 classes  
- **Main Tab Class**: WalletTab
- **Location**: Lines 1296-2138 in `signalbot/gui/dashboard.py`

## Class Overview

### Worker Threads (Background Operations)
1. **RefreshBalanceWorker** - Line 1296
2. **RefreshTransfersWorker** - Line 1313
3. **SendFundsWorker** - Line 1330
4. **BackupWalletWorker** - Line 1350

### User Dialogs
1. **SendFundsDialog** - Line 1367
2. **ReceiveDialog** - Line 1449
3. **BackupDialog** - Line 1527

### Main Tab
**WalletTab** - Line 1568

## Key Methods in WalletTab

### Initialization
- `__init__(wallet)` - Initialize with optional wallet instance
- `init_ui()` - Create all UI components

### UI Creation
- `create_sync_status_bar()` - Top status bar
- `create_balance_section()` - Balance display
- `create_address_section()` - Address management
- `create_actions_section()` - Quick action buttons
- `create_history_section()` - Transaction table

### Data Refresh
- `refresh_all()` - Refresh everything
- `refresh_balance()` - Update balances
- `refresh_addresses()` - Update addresses
- `refresh_transactions()` - Update transaction history
- `auto_refresh()` - Timer-triggered refresh (30s)

### User Actions
- `generate_subaddress()` - Create new subaddress
- `copy_address(address)` - Copy to clipboard
- `show_receive_dialog()` - Show QR code
- `send_funds()` - Open send dialog
- `backup_wallet()` - Create backup
- `export_transactions()` - Export to CSV
- `view_all_transactions()` - Show all TX

### Event Handlers
- `on_balance_refreshed(balance)` - Balance update complete
- `on_balance_error(error_msg)` - Balance update failed
- `on_transfers_refreshed(transfers)` - TX update complete
- `on_transfers_error(error_msg)` - TX update failed
- `on_send_complete(result, progress)` - Send successful
- `on_send_error(error_msg, progress)` - Send failed
- `on_backup_complete(path, progress)` - Backup successful
- `on_backup_error(error_msg, progress)` - Backup failed

### Utilities
- `show_not_connected()` - Wallet disconnected warning

## Integration Points

### DashboardWindow Changes

**Line 3417**: Initialize wallet reference
```python
self.wallet = None  # Store wallet reference for WalletTab
```

**Line 3438**: Store wallet instance
```python
self.wallet = wallet
```

**Line 3484**: Add WalletTab to tabs
```python
tabs.addTab(WalletTab(self.wallet), "💰 Wallet")
```

## Import Additions

Added to PyQt5.QtWidgets imports:
- `QProgressBar`
- `QFrame`
- `QInputDialog`

Added to PyQt5.QtGui imports:
- `QColor`

Added module imports:
- `from ..core.monero_wallet import InHouseWallet`

## Features Checklist

### ✅ Balance Display Section
- [x] Total XMR balance (12 decimals)
- [x] Unlocked balance (green)
- [x] Locked balance (yellow)
- [x] Refresh button
- [x] Last updated timestamp

### ✅ Address Management Section
- [x] Primary address display
- [x] Copy button
- [x] Generate subaddress
- [x] Subaddress list
- [x] Copy buttons for each

### ✅ Quick Actions Section
- [x] Send Funds (opens dialog)
- [x] Receive (shows QR)
- [x] Backup Wallet
- [x] Export Transactions

### ✅ Transaction History Section
- [x] Type column (IN/OUT)
- [x] Amount column (12 decimals)
- [x] Address column
- [x] Confirmations column
- [x] Date column
- [x] Color-coded (green/red)
- [x] View All button
- [x] Auto-refresh (30s)

### ✅ Sync Status Bar
- [x] Connection indicator (●)
- [x] Block height display
- [x] Progress bar
- [x] Last sync timestamp

## Testing Commands

### Syntax Check
```bash
python3 -m py_compile signalbot/gui/dashboard.py
```

### Import Test (requires PyQt5)
```python
from signalbot.gui.dashboard import WalletTab
tab = WalletTab(wallet=None)
```

## Wallet Methods Used

```python
# From InHouseWallet
wallet.get_balance() → (total, unlocked, locked)
wallet.get_address() → str
wallet.create_subaddress(label) → dict
wallet.get_transfers() → list[dict]
wallet.send(address, amount, priority) → dict
wallet.backup_wallet() → str
```

## Color Scheme

- **Green (#00ff00)**: Unlocked balance, incoming transactions, connected
- **Red (#ff0000)**: Outgoing transactions, disconnected
- **Yellow/Orange (#ff9900)**: Pending/locked balance
- **Gray**: Disabled/secondary text

## Auto-Refresh Behavior

Timer: 30 seconds (30000ms)
Triggers: `auto_refresh()` → `refresh_all()`
Refreshes:
1. Balance
2. Addresses  
3. Transactions

## Error Handling

All operations wrapped in try-catch with:
- User-friendly QMessageBox errors
- Console logging for debugging
- Graceful degradation when wallet not connected
- Thread-safe UI updates

## Security Features

1. Transaction confirmation dialog
2. Address validation (min 95 chars)
3. Backup warnings
4. No seed phrase display
5. Amount validation (>0)

## Future Enhancement Ideas

- Real-time block sync
- Transaction filtering
- Address book
- Multi-account support
- Transaction notes
- Fee estimation
- Advanced settings

## Common Use Cases

### Send Monero
1. Click "💸 Send Funds"
2. Enter recipient address
3. Enter amount (XMR)
4. Select priority
5. Confirm transaction
6. Wait for worker thread
7. View result

### Receive Monero
1. Click "📥 Receive (Show QR)"
2. Share address or QR code
3. Or generate new subaddress
4. Monitor transactions table

### Backup Wallet
1. Click "💾 Backup Wallet"
2. Confirm backup
3. Note backup path
4. Store securely

### Export Transactions
1. Click "📊 Export Transactions"
2. Choose save location
3. Open CSV in spreadsheet

## Performance Notes

- Worker threads prevent UI freezing
- Transaction table limited to 20 by default
- Auto-refresh on 30s timer
- Balance updates ~1-2s depending on network
- Send operations ~5-30s depending on network

## Dependencies

**Required**:
- PyQt5
- InHouseWallet class

**Optional**:
- qrcode (for QR generation)
- csv (built-in, for export)

## Troubleshooting

**Wallet not connected**:
- Configure wallet in Settings tab
- Check RPC connection
- Verify daemon is running

**QR code not showing**:
- Install: `pip install qrcode[pil]`

**Slow refresh**:
- Check network connection
- Verify daemon responsiveness
- Consider increasing refresh interval
