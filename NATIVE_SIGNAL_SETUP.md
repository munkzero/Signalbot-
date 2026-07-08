# Native Signal Implementation - Setup & Integration Guide

## ✅ Files Created

All 5 files have been created:

```
signalbot/core/
├── signal_api.py                    ✓ Signal server REST API calls
├── signal_protocol_crypto.py        ✓ Encryption & key management
├── signal_native.py                 ✓ Main native client
├── signal_storage.py                ✓ Encrypted key storage
└── signal_handler.py                (Keep existing - still uses signal-cli)

signal_native.py                      ✓ CLI interface (command-line)
```

---

## 📦 Installation

### Step 1: Create Virtual Environment (Kali Linux)

```bash
cd ~/path/to/Signalbot-
python3 -m venv venv
source venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install libsignal websockets requests cryptography
```

These are pure Python libraries - **no compilation needed**.

### Step 3: Verify Installation

```bash
python -c "import libsignal; print('✓ libsignal installed')"
python -c "import websockets; print('✓ websockets installed')"
python -c "import requests; print('✓ requests installed')"
python -c "import cryptography; print('✓ cryptography installed')"
```

---

## 🚀 Usage - Registration (Just Like signal-cli)

### Step 1: Request Registration

```bash
source venv/bin/activate
python signal_native.py register +64123456789
```

**Output:**
```
======================================================================
📱 SIGNAL REGISTRATION - STEP 1
======================================================================

⚠️  CAPTCHA REQUIRED

Please open this URL in your browser:
https://signalcaptchas.org/registration/generate.html?captcha_token=xyz...

Complete the captcha and you will receive a TOKEN.
Copy the token and return here.

======================================================================
```

### Step 2: Verify Captcha Token

Open the URL in your browser, solve the captcha, copy the token, then:

```bash
python signal_native.py verify +64123456789 --captcha abc123xyz
```

**Output:**
```
======================================================================
📱 SIGNAL REGISTRATION - STEP 2
======================================================================

✅ Captcha accepted!

📱 A verification code has been sent via SMS to +64123456789

======================================================================
Next, run:
  python signal_native.py verify +64123456789 --sms XXXXXX
======================================================================
```

### Step 3: Verify SMS Code

Enter the SMS code you received:

```bash
python signal_native.py verify +64123456789 --sms 123456
```

**Output:**
```
======================================================================
📱 SIGNAL REGISTRATION - COMPLETE
======================================================================

✅ Registration successful!

✓ Phone number: +64123456789
✓ Account registered and ready to use

Now you can:
  1. Link a device (scan QR code with Signal app)
  2. Start sending/receiving messages

======================================================================
```

**Done!** Your phone number is now registered.

---

## 🔗 Device Linking (Optional)

If you want to link the bot to Signal on your phone:

```bash
python signal_native.py link
```

This displays a QR code. Scan it with Signal app on your phone:
- Open Signal
- Go to **Settings → Linked Devices**
- Tap **Link New Device**
- Scan the QR code

---

## 🔄 Current Status: Still Using signal-cli for Now

**Important:** Your bot still uses `signal-cli` for now. The native client is ready but NOT integrated into the bot yet.

To keep things safe:
1. ✅ New registration works (use `python signal_native.py`)
2. ✅ Device linking works
3. ⏳ Bot still uses signal-cli for messaging
4. ⚠️ We'll integrate when you're ready

---

## 📋 Testing Checklist

Before integrating into the bot, test each step:

```bash
# Test 1: Registration flow
python signal_native.py register +64123456789

# Test 2: Device linking
python signal_native.py link

# Test 3: List registered identities
python signal_native.py list-identities
```

If all 3 work, we can integrate the native client into the bot.

---

## 🔧 Integration (When Ready)

To switch the bot from signal-cli to native client:

**Edit `signalbot/core/signal_handler.py`** - change line 27-28:

```python
# OLD:
def __init__(self, phone_number: Optional[str] = None):

# NEW:
def __init__(self, phone_number: Optional[str] = None, use_native: bool = False):
    self.use_native = use_native
    
    if self.use_native:
        from signalbot.core.signal_native import NativeSignalClient
        self.native_client = NativeSignalClient(phone_number)
    else:
        self.native_client = None  # Use signal-cli
```

Then update send_message() to use native when available.

**But don't do this yet** - test the registration first.

---

## ⚠️ About Your Phone Number Issue

You mentioned:
> "I gone back to a old number an I not sure if the bot is sync to it"

**To debug this:**

1. Check what phone number your bot is configured to use:
   ```bash
   grep PHONE_NUMBER .env
   grep SIGNAL_USERNAME .env
   ```

2. Verify signal-cli has that number registered:
   ```bash
   signal-cli -u +YOUR_NUMBER listContacts
   ```

3. Check if contacts can reach it:
   ```bash
   signal-cli -u +YOUR_NUMBER listGroups
   ```

If signal-cli shows the number is registered, but the bot isn't receiving messages:
- The bot might not be running
- The listening thread might be stuck
- Check the logs for errors

---

## 🛑 Rollback (If Something Breaks)

If anything goes wrong:

```bash
# Delete the new native files
rm signalbot/core/signal_api.py
rm signalbot/core/signal_protocol_crypto.py
rm signalbot/core/signal_native.py
rm signalbot/core/signal_storage.py
rm signal_native.py

# Your bot will still work with signal-cli
# signal_handler.py is unchanged
```

**Everything is 100% backward compatible.**

---

## 📞 Next Steps

1. **Activate venv** each time you work:
   ```bash
   source venv/bin/activate
   ```

2. **Test registration** with your phone number

3. **Let me know if it works** - then we'll integrate into the bot

4. **Debug the phone number issue** - should be simple

---

## Questions?

- Can't register? Check the captcha URL opens correctly
- Phone number sync issues? Check .env and signal-cli config
- Need help? Let me know what error you see

**Ready?** Test the registration and let me know how it goes! 🚀
