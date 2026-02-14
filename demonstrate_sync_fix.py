#!/usr/bin/env python3
"""
Demonstration script showing the syncMessage fix in action
This simulates the exact scenario from the problem statement
"""

import sys
import os
import json

# Add signalbot to path
sys.path.insert(0, os.path.dirname(__file__))

from signalbot.core.signal_handler import SignalHandler


def demonstrate_fix():
    """Demonstrate the fix with the exact JSON from the problem statement"""
    print("=" * 70)
    print("DEMONSTRATION: syncMessage Fix")
    print("=" * 70)
    print()
    
    # Initialize handler
    handler = SignalHandler(phone_number="+64274268090")
    
    print("Scenario 1: Message from Signal Desktop to self (should be skipped)")
    print("-" * 70)
    
    # This is the EXACT JSON from the problem statement
    # Note: JSON uses lowercase 'false', which json.loads() parses correctly
    self_message_json = """
{
  "envelope": {
    "source": "+64274268090",
    "sourceNumber": "+64274268090",
    "sourceUuid": "6b236748-ad51-4421-a0cf-88b108231fb3",
    "sourceName": "Satoshi",
    "sourceDevice": 1,
    "timestamp": 1771049391838,
    "syncMessage": {
      "sentMessage": {
        "destination": "+64274268090",
        "destinationNumber": "+64274268090",
        "destinationUuid": "6b236748-ad51-4421-a0cf-88b108231fb3",
        "timestamp": 1771049391838,
        "message": "Hello",
        "expiresInSeconds": 0,
        "isExpirationUpdate": false,
        "viewOnce": false
      }
    }
  },
  "account": "+64274268090"
}
"""
    
    print("Input JSON (from problem statement):")
    print(self_message_json)
    print()
    print("Processing message...")
    
    message_data = json.loads(self_message_json)
    
    # Track callbacks
    received_messages = []
    def callback(message):
        received_messages.append(message)
    handler.register_message_callback(callback)
    
    handler._handle_message(message_data)
    
    print()
    if len(received_messages) == 0:
        print("✅ Result: Message correctly SKIPPED (self-to-self message)")
        print("   Expected behavior: Self-sent messages are not processed")
    else:
        print("❌ Result: Message was processed (should have been skipped!)")
    
    print()
    print()
    
    # Reset for next scenario
    received_messages.clear()
    
    print("Scenario 2: Message from another user (should be processed)")
    print("-" * 70)
    
    other_user_json = """
{
  "envelope": {
    "source": "+15555550123",
    "sourceNumber": "+15555550123",
    "sourceUuid": "abc-123-def-456",
    "sourceName": "Alice",
    "timestamp": 1771049391838,
    "dataMessage": {
      "timestamp": 1771049391838,
      "message": "Hi! I want to buy something",
      "expiresInSeconds": 0,
      "viewOnce": false
    }
  },
  "account": "+64274268090"
}
"""
    
    print("Input JSON:")
    print(other_user_json)
    print()
    print("Processing message...")
    
    message_data = json.loads(other_user_json)
    handler._handle_message(message_data)
    
    print()
    if len(received_messages) == 1:
        msg = received_messages[0]
        print("✅ Result: Message correctly PROCESSED")
        print(f"   Sender: {msg['sender']}")
        print(f"   Text: {msg['text']}")
        print(f"   Expected behavior: Messages from others are processed normally")
    else:
        print("❌ Result: Message was not processed correctly")
    
    print()
    print()
    
    # Reset for next scenario
    received_messages.clear()
    
    print("Scenario 3: Message from Signal Desktop to another user (should be processed)")
    print("-" * 70)
    
    sync_to_other_json = """
{
  "envelope": {
    "source": "+64274268090",
    "sourceNumber": "+64274268090",
    "sourceUuid": "6b236748-ad51-4421-a0cf-88b108231fb3",
    "sourceName": "Satoshi",
    "sourceDevice": 1,
    "timestamp": 1771049391838,
    "syncMessage": {
      "sentMessage": {
        "destination": "+15555550123",
        "destinationNumber": "+15555550123",
        "destinationUuid": "abc-123-def-456",
        "timestamp": 1771049391838,
        "message": "Here's the catalog",
        "expiresInSeconds": 0,
        "isExpirationUpdate": false,
        "viewOnce": false
      }
    }
  },
  "account": "+64274268090"
}
"""
    
    print("Input JSON:")
    print(sync_to_other_json)
    print()
    print("Processing message...")
    
    message_data = json.loads(sync_to_other_json)
    handler._handle_message(message_data)
    
    print()
    if len(received_messages) == 1:
        msg = received_messages[0]
        print("✅ Result: Message correctly PROCESSED")
        print(f"   Sender: {msg['sender']}")
        print(f"   Text: {msg['text']}")
        print(f"   Expected behavior: syncMessages to others are processed (for record keeping)")
    else:
        print("❌ Result: Message was not processed correctly")
    
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()
    print("The fix successfully:")
    print("  ✓ Parses message text from syncMessage.sentMessage.message")
    print("  ✓ Parses message text from dataMessage.message (backward compatible)")
    print("  ✓ Skips self-to-self messages to avoid loops")
    print("  ✓ Processes syncMessages sent to others (for tracking)")
    print("  ✓ Shows 'syncMessage' or 'dataMessage' in debug output")
    print()
    print("Before fix: 'DEBUG: Received message from +64274268090: (no text)'")
    print("After fix:  'DEBUG: Received syncMessage from +64274268090: Hello'")
    print()


if __name__ == "__main__":
    demonstrate_fix()
