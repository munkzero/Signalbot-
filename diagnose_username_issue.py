#!/usr/bin/env python3
"""
Signal Username Diagnostic Tool

This script helps diagnose and fix Signal username/phone conversation split issues.

Usage:
    python diagnose_username_issue.py

What it checks:
1. Phone number configuration
2. Username registration status
3. Signal-cli version and capabilities
4. Receive command functionality
5. Provides recommendations
"""

import sys
import os
import subprocess
import json

# Add signalbot to path
sys.path.insert(0, os.path.dirname(__file__))

from signalbot.core.signal_handler import SignalHandler


def print_section(title):
    """Print a section header"""
    print("\n" + "="*70)
    print(f" {title}")
    print("="*70)


def check_signal_cli_installed():
    """Check if signal-cli is installed"""
    print_section("1. Checking signal-cli Installation")
    
    try:
        result = subprocess.run(
            ['signal-cli', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ signal-cli is installed")
            print(f"   Version: {version}")
            return True
        else:
            print(f"❌ signal-cli returned error: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print(f"❌ signal-cli is NOT installed")
        print(f"   Install it from: https://github.com/AsamK/signal-cli")
        return False
    except Exception as e:
        print(f"❌ Error checking signal-cli: {e}")
        return False


def check_phone_configuration():
    """Check phone number configuration"""
    print_section("2. Checking Phone Number Configuration")
    
    try:
        handler = SignalHandler()
        phone = handler.phone_number
        
        print(f"✅ Phone number configured: {phone}")
        return phone
        
    except Exception as e:
        print(f"❌ Phone number not configured: {e}")
        print(f"   Run: ./setup.sh to configure your phone number")
        return None


def check_registered_accounts(phone):
    """Check registered accounts"""
    print_section("3. Checking Registered Accounts")
    
    try:
        result = subprocess.run(
            ['signal-cli', 'listAccounts'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            accounts = result.stdout.strip()
            if accounts:
                print(f"✅ Registered accounts:")
                for line in accounts.split('\n'):
                    line = line.strip()
                    if line:
                        status = "✅ (matches config)" if phone and phone in line else "⚠️"
                        print(f"   {status} {line}")
                return True
            else:
                print(f"❌ No registered accounts found")
                print(f"   You need to register {phone} with signal-cli")
                return False
        else:
            print(f"❌ Error listing accounts: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def check_username_status(phone):
    """Check username status"""
    print_section("4. Checking Username Status")
    
    if not phone:
        print("⚠️  Skipping - phone not configured")
        return None
    
    try:
        handler = SignalHandler(phone_number=phone)
        status = handler.check_account_status()
        
        print(f"📱 Phone: {status['phone_number']}")
        
        if status['username']:
            print(f"✅ Username: {status['username']}")
            if status['username_link']:
                print(f"🔗 Link: {status['username_link']}")
        else:
            print(f"⚠️  Username: Not set")
            print(f"   Messages to username will NOT work without a username!")
            print(f"   To set username, use: signal-cli -a {phone} updateAccount -u YOUR_USERNAME")
        
        return status['username']
        
    except Exception as e:
        print(f"⚠️  Could not check username: {e}")
        print(f"   This might be normal if signal-cli version doesn't support getUserStatus")
        return None


def test_receive_command(phone):
    """Test the receive command"""
    print_section("5. Testing Message Receiving")
    
    if not phone:
        print("⚠️  Skipping - phone not configured")
        return False
    
    print(f"Testing command: signal-cli -u {phone} receive --timeout 1")
    print(f"(This will poll for 1 second to see if receive works)")
    
    try:
        result = subprocess.run(
            ['signal-cli', '--output', 'json', '-u', phone, 'receive', '--timeout', '1'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print(f"✅ Receive command works!")
            
            if result.stdout:
                print(f"   Received messages:")
                for line in result.stdout.strip().split('\n'):
                    if line:
                        try:
                            msg = json.loads(line)
                            account = msg.get('account', 'unknown')
                            envelope = msg.get('envelope', {})
                            source = envelope.get('source', 'unknown')
                            print(f"     - From: {source} → To: {account}")
                        except:
                            print(f"     - {line[:50]}...")
            else:
                print(f"   No messages in queue (this is normal)")
            
            return True
        else:
            if result.stderr:
                print(f"⚠️  Receive command had errors: {result.stderr}")
            else:
                print(f"⚠️  Receive command returned non-zero exit code: {result.returncode}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing receive: {e}")
        return False


def provide_recommendations(has_signal_cli, has_phone, has_username, receive_works):
    """Provide recommendations based on checks"""
    print_section("DIAGNOSIS & RECOMMENDATIONS")
    
    if not has_signal_cli:
        print("""
❌ CRITICAL: signal-cli is not installed

Action required:
1. Install signal-cli from: https://github.com/AsamK/signal-cli
2. Re-run this diagnostic script
        """)
        return
    
    if not has_phone:
        print("""
❌ CRITICAL: Phone number not configured

Action required:
1. Run: ./setup.sh
2. Or set PHONE_NUMBER in .env file
3. Re-run this diagnostic script
        """)
        return
    
    if not has_username:
        print("""
⚠️  WARNING: Username is NOT set

This is likely the cause of your issue!

📋 Understanding the Issue:
   - Signal usernames are OPTIONAL
   - If not set, users CANNOT message you via username
   - They can ONLY message your phone number

💡 Solution:
   1. Set a username with this command (replace <PHONE> and <USERNAME>):
      signal-cli -a <YOUR_PHONE_NUMBER> updateAccount -u <DESIRED_USERNAME>
   
   2. Example with actual values:
      signal-cli -a +64274757293 updateAccount -u shopbot.223
   
   3. Then re-run this diagnostic to verify

❗ IMPORTANT: Once username is set:
   - Users can message EITHER your username OR phone
   - Both go to the SAME conversation (Signal merges them)
   - Bot will receive ALL messages with 'signal-cli receive'
   - Bot replies will show as your username (Signal client preference)
        """)
        return
    
    if not receive_works:
        print("""
⚠️  WARNING: Message receiving may have issues

Possible causes:
1. Trust/safety number issues - run: signal-cli -u {PHONE} listIdentities
2. Registration incomplete
3. Network connectivity issues

Try:
1. Check trust for known contacts
2. Verify registration is complete
3. Check network connectivity
        """)
        return
    
    # If everything checks out
    print("""
✅ ALL CHECKS PASSED!

Your configuration looks good:
- signal-cli is installed ✅
- Phone number is configured ✅  
- Username is set ✅
- Message receiving works ✅

🎯 Next Steps:

1. Verify username with Signal client:
   - Open Signal on your phone
   - Go to Settings → Profile
   - Confirm username matches what's set in signal-cli

2. Test receiving:
   - Have someone message your USERNAME
   - Have someone message your PHONE NUMBER
   - Both should arrive as messages to your phone account
   - Check logs for: "DEBUG: Received dataMessage from..."

3. If users still see "two conversations":
   - Ask them to DELETE both conversations
   - Have them message you again
   - Should now see only ONE conversation
   - This might be a Signal client caching issue

📝 How Signal Username System Works:
   - Username and phone are LINKED (same account)
   - Messages to either go to SAME conversation
   - signal-cli -u +PHONE receive gets ALL messages
   - Bot sends from phone, Signal displays as username
   - Users see ONE conversation (not split!)

🐛 If Issue Persists:
   - Check Signal app is updated on user's device
   - Verify username is properly linked in Signal settings
   - Look for trust/safety number warnings
   - Check if user is contacting the CORRECT account
    """)


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║        Signal Username/Phone Conversation Split Diagnostic        ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝

This tool will diagnose why users might be seeing split conversations
when messaging your bot via username vs phone number.
    """)
    
    # Run all checks
    has_signal_cli = check_signal_cli_installed()
    phone = check_phone_configuration()
    has_accounts = check_registered_accounts(phone) if phone else False
    has_username = check_username_status(phone)
    receive_works = test_receive_command(phone)
    
    # Provide recommendations
    provide_recommendations(has_signal_cli, phone, has_username, receive_works)
    
    print("\n" + "="*70)
    print(" Diagnostic Complete")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
