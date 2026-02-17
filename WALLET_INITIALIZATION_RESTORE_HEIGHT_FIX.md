# Wallet Initialization Fixes - Implementation Summary

## Problem Statement
Users were experiencing wallet initialization failures with the following issues:

1. **Syncing from Block 0**: When wallets were created, they had no restore height set, causing them to scan from genesis block (2014), which takes hours/days
2. **60s Timeout Too Short**: Initial wallet sync couldn't complete in 60 seconds, causing "RPC did not respond" errors
3. **No Seed Phrase Display (Formatted)**: Users never saw their wallet seed phrase in a prominent, formatted display

## Solution Implemented

### 1. Added Blockchain Height Retrieval
**New Function**: `get_current_blockchain_height(daemon_address, daemon_port)`
- Queries Monero daemon's `/get_height` endpoint
- Returns current blockchain height or None on failure
- Used to calculate restore height for new wallets

### 2. Added Restore Height Support
**Updated**: `create_wallet()` method
- Gets current blockchain height from daemon
- Calculates restore height as `max(0, current_height - RESTORE_HEIGHT_OFFSET)`
- Passes `--restore-height` parameter to `monero-wallet-cli`
- **Result**: New wallets skip scanning old blocks, sync in seconds instead of hours

**Configuration**:
```python
RESTORE_HEIGHT_OFFSET = 1000  # Blocks to subtract (33 hours at 2 min/block)
```

The offset balances:
- **Performance**: Avoids scanning from genesis (2014)
- **Safety**: 1000 blocks provides reasonable buffer for most use cases

### 3. Extended Timeout for New Wallets
**Updated**: `wait_for_rpc_ready()` function
- Added `is_new_wallet` parameter (default: False)
- New wallets use 180s timeout (vs 60s for existing wallets)
- Displays: "⏳ New wallet - initial sync may take 2-3 minutes..."

**Configuration**:
```python
NEW_WALLET_RPC_TIMEOUT = 180  # 3 minutes for new wallets
EXISTING_WALLET_RPC_TIMEOUT = 60  # 1 minute for existing wallets
```

### 4. Enhanced Seed Phrase Display
**New Function**: `display_seed_phrase(seed)`
- Validates seed has exactly 25 words (Monero standard)
- Displays seed phrase in formatted box with borders
- Dynamic padding for maintainability
- Clear warning about backing up the seed

**Example Output**:
```
╔════════════════════════════════════════════════════════════╗
║  🔑 NEW WALLET CREATED - SAVE YOUR SEED PHRASE!          ║
║                                                            ║
║  word1 word2 word3 word4 word5 word6 word7 word8         ║
║  word9 word10 word11 word12 word13 word14 word15 word16  ║
║  word17 word18 word19 word20 word21 word22 word23 word24 ║
║  word25                                                    ║
║                                                            ║
║  ⚠️  WRITE THIS DOWN! You cannot recover your funds      ║
║     without this seed phrase!                             ║
╚════════════════════════════════════════════════════════════╝
```

### 5. Updated Wallet Setup Flow
**Updated**: `setup_wallet()` method
- Detects new wallet creation
- Calls `start_rpc(is_new_wallet=True)` for new wallets
- Removed duplicate seed phrase logging (now handled by `display_seed_phrase()`)

**Updated**: `start_rpc()` method
- Added `is_new_wallet` parameter
- Passes flag to `wait_for_rpc_ready()` for extended timeout

## Expected Behavior After Fix

### Before (Broken):
```
ℹ  No wallet found - will create with empty password...
🔧 DEBUG: Running wallet auto-setup...
⚠ Found orphaned wallet cache: shop_wallet_1770875498.OLD
❌ RPC did not respond after 60s
❌ RPC process started but not responding
❌ Failed to start wallet RPC
```

**Manual RPC log shows**: `Pulling blocks: start_height 0` (scanning from 2014)

### After (Fixed):
```
🔍 Testing Monero node connectivity...
ℹ  No wallet found - will create with empty password...
✓ Current blockchain height: 3,234,567
🔧 Creating new wallet with restore height 3,233,567...
✓ Wallet created successfully

╔════════════════════════════════════════════════════════════╗
║  🔑 NEW WALLET CREATED - SAVE YOUR SEED PHRASE!          ║
║                                                            ║
║  [25-word seed phrase displayed here]                    ║
║                                                            ║
║  ⚠️  WRITE THIS DOWN! You cannot recover your funds      ║
║     without this seed phrase!                             ║
╚════════════════════════════════════════════════════════════╝

🔧 Starting wallet RPC process...
⏳ New wallet - initial sync may take 2-3 minutes...
⏳ Waiting for RPC to start (max 180s)...
✓ RPC ready after 3 attempts (6.2s)
✅ Wallet RPC started successfully!
🔍 Checking wallet sync status...
✓ Wallet is fully synced! (blocks: 3,234,567/3,234,567)
✅ Wallet system initialized successfully
```

## Files Modified

### signalbot/core/wallet_setup.py
- Added configuration constants (lines 18-20)
- Added `get_current_blockchain_height()` function (lines 72-104)
- Updated `wait_for_rpc_ready()` with `is_new_wallet` parameter (lines 107-161)
- Added `display_seed_phrase()` function with validation (lines 371-427)
- Updated `create_wallet()` with restore height support (lines 448-546)
- Updated `start_rpc()` with `is_new_wallet` parameter (lines 661-696)
- Updated `setup_wallet()` to pass `is_new_wallet=True` (lines 901-920)

### test_wallet_restore_height.py (New)
- Comprehensive test suite for all changes
- Validates function signatures, parameters, and logic
- All tests passing

## Testing Results

### Unit Tests
✅ All new tests pass (test_wallet_restore_height.py)
✅ Existing wallet RPC tests pass (test_wallet_rpc_autostart.py)
✅ Python syntax validation passes

### Security Scan
✅ CodeQL analysis: 0 alerts found

### Code Review
✅ Addressed all feedback:
- Added configuration constants
- Added seed phrase validation (25 words)
- Implemented dynamic padding
- Added detailed documentation

## Benefits

1. **Fast Wallet Creation**: New wallets sync in seconds, not hours
2. **Better UX**: Clear seed phrase display with formatting and warnings
3. **Reliable Startup**: Extended timeout prevents false failures
4. **Maintainable Code**: Constants, validation, and clear documentation
5. **Safe Defaults**: Restore height offset provides good balance

## Configuration Options

To adjust the behavior, modify these constants in `wallet_setup.py`:

```python
RESTORE_HEIGHT_OFFSET = 1000  # Adjust for more/less historical scanning
NEW_WALLET_RPC_TIMEOUT = 180  # Adjust for slower/faster networks
EXISTING_WALLET_RPC_TIMEOUT = 60  # Adjust for existing wallet startup
```

## Backward Compatibility

✅ All existing functionality preserved
✅ New parameters have safe defaults (is_new_wallet=False)
✅ Existing wallets continue to work without changes
✅ Only new wallet creation flow is enhanced
