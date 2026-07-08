#!/usr/bin/env python3
"""
Signal Native Client - Command Line Interface
Replacement for signal-cli
Usage: python signal_native.py [command] [args]
"""

import sys
import argparse
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from signalbot.core.signal_native import NativeSignalClient
from signalbot.core.signal_storage import SignalStorage

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def register_command(args):
    """Register new phone number"""
    phone_number = args.phone_number
    
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number
    
    client = NativeSignalClient(phone_number)
    captcha_url = client.register(phone_number)
    
    return 0


def verify_command(args):
    """Verify captcha or SMS code"""
    phone_number = args.phone_number
    
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number
    
    client = NativeSignalClient(phone_number)
    
    if args.captcha:
        # Step 2: Verify captcha token
        captcha_token = args.captcha
        success = client.verify(phone_number, captcha_token=captcha_token)
        return 0 if success else 1
    
    elif args.sms:
        # Step 3: Verify SMS code
        sms_code = args.sms
        success = client.verify(phone_number, sms_code=sms_code)
        return 0 if success else 1
    
    else:
        print("Error: Must provide --captcha or --sms")
        return 1


def link_command(args):
    """Generate device linking QR code"""
    client = NativeSignalClient()
    linking_uri = client.create_linking_uri()
    
    # Try to generate QR code
    try:
        import qrcode
        qr = qrcode.QRCode()
        qr.add_data(linking_uri)
        qr.make()
        qr.print_ascii()
    except ImportError:
        print("Install qrcode: pip install qrcode")
    
    return 0


def send_command(args):
    """Send message"""
    phone_number = args.phone_number
    recipient = args.recipient
    message = args.message
    
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number
    if not recipient.startswith('+'):
        recipient = '+' + recipient
    
    client = NativeSignalClient(phone_number)
    
    # Load identity
    if not client.load_identity(phone_number):
        print(f"Error: No identity found for {phone_number}")
        print("Register first: python signal_native.py register {phone_number}")
        return 1
    
    # Send message
    success = client.send_message(recipient, message)
    return 0 if success else 1


def list_identities_command(args):
    """List all registered identities"""
    storage = SignalStorage()
    identities = storage.list_identities()
    
    if not identities:
        print("No identities found")
    else:
        print("\nRegistered identities:")
        for phone in identities:
            print(f"  ✓ {phone}")
    
    return 0


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Signal Native Client - Replacement for signal-cli',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Register new phone number
  python signal_native.py register +64123456789
  
  # Verify with captcha token
  python signal_native.py verify +64123456789 --captcha abc123xyz
  
  # Verify with SMS code
  python signal_native.py verify +64123456789 --sms 123456
  
  # Generate device linking QR
  python signal_native.py link
  
  # Send message
  python signal_native.py -u +64123456789 send +1234567890 "Hello!"
  
  # List all registered phone numbers
  python signal_native.py list-identities
        """
    )
    
    # Global options
    parser.add_argument(
        '-u', '--username',
        dest='phone_number',
        help='Phone number (e.g., +64123456789)'
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Register command
    register_parser = subparsers.add_parser('register', help='Register phone number')
    register_parser.add_argument('phone_number', help='Phone number (e.g., +64123456789)')
    register_parser.set_defaults(func=register_command)
    
    # Verify command
    verify_parser = subparsers.add_parser('verify', help='Verify captcha or SMS code')
    verify_parser.add_argument('phone_number', help='Phone number')
    verify_parser.add_argument('--captcha', help='Captcha token from browser')
    verify_parser.add_argument('--sms', help='SMS code from phone')
    verify_parser.set_defaults(func=verify_command)
    
    # Link command
    link_parser = subparsers.add_parser('link', help='Generate device linking QR code')
    link_parser.set_defaults(func=link_command)
    
    # Send command
    send_parser = subparsers.add_parser('send', help='Send message')
    send_parser.add_argument('recipient', help='Recipient phone number')
    send_parser.add_argument('message', help='Message text')
    send_parser.set_defaults(func=send_command)
    
    # List identities command
    list_parser = subparsers.add_parser('list-identities', help='List all registered phone numbers')
    list_parser.set_defaults(func=list_identities_command)
    
    # Parse arguments
    args = parser.parse_args()
    
    # Execute command
    if hasattr(args, 'func'):
        return args.func(args)
    else:
        parser.print_help()
        return 0


if __name__ == '__main__':
    sys.exit(main())
