# Signal Username/Phone Number - Complete Guide

## Understanding the Issue

### The Reported Problem
Users reported seeing **two separate conversations** with the bot:
1. One when they message the **phone number** (+64274757293)
2. Another when they message the **username** (e.g., shopbot.223)

Bot also seemed to only receive messages sent to phone, not username.

### The Reality: How Signal Actually Works

**IMPORTANT**: Signal's username and phone number are **NOT separate accounts**. They are **linked identities for the SAME account**.

#### Key Facts About Signal Usernames:

1. **Single Account, Multiple Identifiers**
   - Your Signal account has ONE phone number (required)
   - You can OPTIONALLY set a username
   - Both point to the SAME account

2. **Unified Conversations**
   - When someone messages your username OR phone, it's the **SAME conversation**
   - Signal merges these on BOTH sides
   - There should NEVER be two separate conversations

3. **Receiving Messages**
   - `signal-cli -u +PHONE receive` gets ALL messages to your account
   - Doesn't matter if user typed your username or phone
   - Both arrive as messages to your phone account
   - The JSON `account` field always shows your phone number

4. **Sending Messages**
   - `signal-cli -u +PHONE send` sends from your phone account
   - Signal client MAY DISPLAY sender as your username (client preference)
   - This is purely a display/UI decision, not a protocol change

## The Actual Root Cause

If users are seeing "two conversations", the root cause is usually:

### Cause 1: Username Not Set (MOST COMMON)
```bash
# Check if username is set
signal-cli -u +64274757293 getUserStatus

# If no username, set one
signal-cli -u +64274757293 setUsername shopbot.223
```

**What happens when username is NOT set:**
- Users messaging phone number: ✅ Works
- Users messaging username: ❌ FAILS (no such user)
- User might accidentally create/contact DIFFERENT account

### Cause 2: Wrong Username
- User typing wrong username (e.g., shopbot vs shopbot.223)
- Contacts a different Signal account entirely
- Creates appearance of "split conversation"

### Cause 3: Signal Client Cache (RARE)
- Very rare, but Signal client might have cached old state
- Solution: Delete both conversations, restart Signal app, message again

### Cause 4: Trust/Safety Number Issues
- If trust/safety number changed, conversation might split
- Check with: `signal-cli -u +PHONE listIdentities`
- Trust contact: `signal-cli -u +PHONE trust +CONTACT -a`

## Solution & Implementation

### Step 1: Verify Username is Set

Run the diagnostic tool:
```bash
python diagnose_username_issue.py
```

This will check:
- ✅ signal-cli installed
- ✅ Phone configured
- ✅ Username set
- ✅ Receive command works

### Step 2: Set Username (if not set)

```bash
# Set your username
signal-cli -u +64274757293 setUsername shopbot.223

# Get sharable link
signal-cli -u +64274757293 getUsernameLink
```

### Step 3: Verify in Signal App

1. Open Signal on your phone
2. Go to Settings → Profile
3. Confirm username is shown
4. Share username link with users

### Step 4: Test Both Methods

```bash
# Terminal 1: Start listening
signal-cli -u +64274757293 receive --timeout 30 --output json

# Ask someone to:
# 1. Message your phone number
# 2. Message your username
# Both should appear in Terminal 1
```

### Step 5: User Side - Clear Cache (if needed)

If a user STILL sees two conversations:
1. Delete BOTH conversations in Signal
2. Close Signal completely
3. Restart Signal
4. Message you again (either method)
5. Should now see only ONE conversation

## Code Changes Made

### 1. Added Username Management Methods

File: `signalbot/core/signal_handler.py`

```python
def get_username(self) -> Optional[str]:
    """Get the Signal username for this account"""
    
def set_username(self, username: str) -> bool:
    """Set Signal username for this account"""
    
def get_username_link(self) -> Optional[str]:
    """Get sharable username link"""
    
def check_account_status(self) -> Dict:
    """Check account status including username configuration"""
```

### 2. Added Diagnostic Tool

File: `diagnose_username_issue.py`

- Checks signal-cli installation
- Verifies phone configuration
- Checks username status
- Tests receive functionality
- Provides actionable recommendations

### 3. Added Understanding Tests

File: `test_signal_username_understanding.py`

- Demonstrates how Signal handles usernames
- Shows JSON message format
- Explains why conversations are NOT split

## Testing & Verification

### Test 1: Verify Username Set

```bash
# Run diagnostic
python diagnose_username_issue.py

# Expected output:
✅ Username: shopbot.223
🔗 Link: https://signal.me/#p/...
```

### Test 2: Receive Messages to Username

```bash
# Start bot
python start.sh

# Have someone message your USERNAME
# Check logs for:
DEBUG: Received dataMessage from +64XXXXXXXXX: catalog
DEBUG: Processing buyer command: catalog
```

### Test 3: Receive Messages to Phone

```bash
# Have someone message your PHONE NUMBER
# Check logs for:
DEBUG: Received dataMessage from +64XXXXXXXXX: catalog
DEBUG: Processing buyer command: catalog
```

Both should work identically!

### Test 4: Verify Single Conversation

Ask a user to:
1. Message your phone number
2. Get response
3. Message your username  
4. Get response
5. Confirm they see only ONE conversation thread

## Common Questions

### Q: Why does Signal show my username instead of phone when I reply?

**A**: This is Signal client's display preference. Signal prioritizes showing username when one is set. This is NOT causing split conversations - it's purely cosmetic.

### Q: Do I need to change my code to reply from username?

**A**: No! signal-cli ALWAYS sends from your phone account (`-u +PHONE`). Signal's client decides whether to DISPLAY it as phone or username. You cannot control this from signal-cli.

### Q: What if users still see two conversations?

**A**: Possible causes:
1. Username not properly set (run diagnostic)
2. They're contacting wrong username/number
3. Trust/safety number issue
4. Signal client cache (delete conversations, restart app)

### Q: Can I have multiple usernames?

**A**: No, one username per Signal account. But you can change it:
```bash
signal-cli -u +PHONE setUsername new_username
```

### Q: Do I need to receive differently for username vs phone?

**A**: No! `signal-cli -u +PHONE receive` gets ALL messages to your account, regardless of whether user typed phone or username.

## Signal Protocol Details

### JSON Message Format

When receiving a message (to phone OR username):
```json
{
  "envelope": {
    "source": "+15555550123",
    "sourceNumber": "+15555550123",
    "sourceUuid": "abc-123",
    "timestamp": 1234567890,
    "dataMessage": {
      "message": "Hello"
    }
  },
  "account": "+64274757293"
}
```

**Note**: `account` field ALWAYS shows your phone number, even if user messaged your username!

### Why Conversations Don't Split

```
User's Signal App:
┌─────────────────────────────────┐
│ shopbot.223                     │  ← Display name (shows username)
│ +64274757293                    │  ← Actual account (phone)
├─────────────────────────────────┤
│ User: Hello shopbot!            │  ← User types/sends
│ Bot: Hi! How can I help?        │  ← Bot replies
└─────────────────────────────────┘

ONE conversation, regardless of how user found you!
```

## Troubleshooting

### Issue: "Bot doesn't receive username messages"

**Diagnosis**:
```bash
python diagnose_username_issue.py
```

**Likely cause**: Username not set

**Fix**:
```bash
signal-cli -u +64274757293 setUsername shopbot.223
```

### Issue: "Users see two conversations"

**Diagnosis**: Check which username they're using
```bash
signal-cli -u +64274757293 getUsernameLink
```

**Fix**: 
1. Confirm they have correct username
2. Have them delete both conversations
3. Restart Signal
4. Message again

### Issue: "Messages not being received at all"

**Check**:
```bash
# 1. Is account registered?
signal-cli listAccounts

# 2. Can we receive?
signal-cli --output json -u +64274757293 receive --timeout 5

# 3. Trust issues?
signal-cli -u +64274757293 listIdentities
```

## Summary

✅ **Current Implementation is Correct**
- Bot ALREADY receives messages to both phone and username
- Bot ALREADY sends correctly
- Signal ALREADY merges conversations

❗ **Action Required**
- Verify username is SET in signal-cli
- Share correct username with users
- Document username for users to contact

✅ **No Code Changes Needed to Core Logic**
- Message receiving works correctly
- Message sending works correctly
- Conversation merging is Signal's behavior

📝 **Added Features**
- Username verification methods
- Diagnostic tool
- Documentation and troubleshooting guide

## References

- [Signal CLI GitHub](https://github.com/AsamK/signal-cli)
- [Signal Username Documentation](https://support.signal.org/hc/en-us/articles/6712070553754)
- [signal-cli Man Page](https://www.gsp.com/cgi-bin/man.cgi?topic=SIGNAL-CLI)
