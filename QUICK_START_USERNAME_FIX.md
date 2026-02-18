# Quick Start: Fix Username/Phone Conversation Split

## TL;DR - Run This First

```bash
# 1. Run the diagnostic tool
python diagnose_username_issue.py

# 2. Follow the recommendations shown
```

## Most Likely Fix

If the diagnostic shows "Username: Not set", run:

```bash
# Set your username (replace shopbot.223 with your desired username)
signal-cli -a +64274757293 updateAccount -u shopbot.223

# Verify it worked
python diagnose_username_issue.py
```

## What Was the Problem?

The issue reported was:
- ❌ Bot only receives messages to phone number
- ❌ Bot replies using username  
- ❌ Users see two conversations

**Reality**: This is usually because **username was never set**!

## How Signal Actually Works

```
┌─────────────────────────────────────────┐
│  Signal Account Structure               │
├─────────────────────────────────────────┤
│                                         │
│  Phone Number: +64274757293 (Required) │
│  Username:     shopbot.223  (Optional)  │
│                                         │
│  ↓                                      │
│  SAME ACCOUNT                           │
│  ONE conversation                       │
│                                         │
└─────────────────────────────────────────┘
```

**Key Points:**
1. Username and phone are **SAME account** (not separate)
2. Messages to either go to **ONE conversation**
3. `signal-cli receive` gets **ALL messages** (username + phone)
4. Bot **ALREADY works correctly**!

## What Changed in This PR

### Added Files:
1. **`diagnose_username_issue.py`** - Diagnostic tool to check configuration
2. **`SIGNAL_USERNAME_GUIDE.md`** - Complete documentation
3. **`test_signal_username_understanding.py`** - Demonstrates how Signal works

### Modified Files:
1. **`signalbot/core/signal_handler.py`**
   - Added `get_username()` - Check current username
   - Added `set_username(username)` - Set username
   - Added `get_username_link()` - Get sharable link
   - Added `check_account_status()` - Full status check

### No Changes to Core Logic:
- Message receiving: **Already works** ✅
- Message sending: **Already works** ✅  
- Conversation handling: **Already works** ✅

## Step-by-Step Fix

### Step 1: Run Diagnostic
```bash
python diagnose_username_issue.py
```

Expected output if username NOT set:
```
⚠️  WARNING: Username is NOT set

This is likely the cause of your issue!

💡 Solution:
   signal-cli -a +64274757293 updateAccount -u shopbot.223
```

### Step 2: Set Username (if needed)
```bash
# Use your own desired username
signal-cli -a +64274757293 updateAccount -u shopbot.223

# Expected output:
# ✅ Username set to: shopbot.223
```

### Step 3: Verify
```bash
# Run diagnostic again
python diagnose_username_issue.py

# Should now show:
# ✅ Username: shopbot.223
# 🔗 Link: https://signal.me/#p/...
```

### Step 4: Test
```bash
# Start the bot
python start.sh

# Ask someone to:
# 1. Message your phone: +64274757293
# 2. Message your username: shopbot.223
#
# Both should work and go to SAME conversation!
```

## Verification Checklist

After running the fix, verify:

- [ ] Diagnostic shows ✅ for all checks
- [ ] Username is set and displayed
- [ ] Bot receives messages to phone number
- [ ] Bot receives messages to username
- [ ] User sees only ONE conversation (not split)
- [ ] Bot commands (catalog, order, help) work from both methods

## If Issue Persists

### Check 1: Correct Username?
```bash
# Verify your username in Signal app
# Go to: Settings → Profile → Username

# Get sharable link (also in Signal app)
# Go to: Settings → Profile → Username → Share Link
# Or scan QR code in the app

# Share the username or link with users
```

### Check 2: User Side - Clear Cache
Ask user to:
1. Delete BOTH conversations with your bot
2. Close Signal app completely
3. Reopen Signal
4. Message you again (either phone or username)
5. Should now see only ONE conversation

### Check 3: Trust Issues?
```bash
# Check identities
signal-cli -u +64274757293 listIdentities

# If you see untrusted contacts, trust them:
signal-cli -u +64274757293 trust +CONTACT_PHONE -a
```

## Understanding the "Fix"

**What was "broken"**: Username was not configured ⚠️

**What was already working**: 
- ✅ Message receiving to phone
- ✅ Message sending  
- ✅ Signal's conversation merging

**What we added**:
- ✅ Username management methods
- ✅ Diagnostic tool
- ✅ Documentation
- ✅ Troubleshooting guide

**What we did NOT need to change**:
- ❌ Message receiving logic (already correct)
- ❌ Message sending logic (already correct)
- ❌ Conversation handling (Signal does this)

## Common Misconceptions

### ❌ Myth: "Username and phone are separate accounts"
**✅ Reality**: They're linked identities for ONE account

### ❌ Myth: "Need different code to receive username messages"
**✅ Reality**: `signal-cli receive` gets ALL messages automatically

### ❌ Myth: "Need to reply 'from username' specifically"
**✅ Reality**: signal-cli sends from your account, Signal client displays name

### ❌ Myth: "Split conversations are normal"
**✅ Reality**: Signal ALWAYS merges - if split, something is wrong

## Need Help?

1. **Read the full guide**: `SIGNAL_USERNAME_GUIDE.md`
2. **Run diagnostic**: `python diagnose_username_issue.py`
3. **Check logs**: Look for "DEBUG: Received dataMessage from..."
4. **Verify Signal app**: Settings → Profile → Username

## Summary

✅ **The "fix" is mainly configuration and documentation**
- Added tools to diagnose and fix username issues
- Documented how Signal's username system works
- No changes to core message handling logic

🎯 **Action Required**
1. Run: `python diagnose_username_issue.py`
2. Follow recommendations shown
3. Verify username is set
4. Test with both phone and username

📚 **Resources Added**
- `diagnose_username_issue.py` - Diagnostic tool
- `SIGNAL_USERNAME_GUIDE.md` - Complete guide
- `test_signal_username_understanding.py` - Understanding tests
- Username management methods in `signal_handler.py`
