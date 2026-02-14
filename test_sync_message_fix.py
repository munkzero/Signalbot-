#!/usr/bin/env python3
"""
Test script to validate syncMessage handling in SignalHandler
Tests the fix for parsing messages from Signal Desktop (syncMessage) 
and regular messages from other users (dataMessage)
"""

import sys
import os
import json

# Add signalbot to path
sys.path.insert(0, os.path.dirname(__file__))

from signalbot.core.signal_handler import SignalHandler


def test_regular_data_message():
    """Test handling of regular incoming messages from other users"""
    print("\n=== Testing Regular dataMessage ===")
    
    handler = SignalHandler(phone_number="+64274268090")
    received_messages = []
    
    def callback(message):
        received_messages.append(message)
    
    handler.register_message_callback(callback)
    
    # Simulate regular incoming message
    message_data = {
        "envelope": {
            "source": "+15555550123",
            "sourceNumber": "+15555550123",
            "sourceUuid": "abc-123-def-456",
            "sourceName": "Alice",
            "timestamp": 1771049391838,
            "dataMessage": {
                "timestamp": 1771049391838,
                "message": "Hello from Alice",
                "expiresInSeconds": 0,
                "viewOnce": False
            }
        },
        "account": "+64274268090"
    }
    
    handler._handle_message(message_data)
    
    # Verify message was processed
    if len(received_messages) == 1:
        msg = received_messages[0]
        if msg['sender'] == '+15555550123' and msg['text'] == 'Hello from Alice':
            print("  ✓ Regular dataMessage parsed correctly")
            print(f"    Sender: {msg['sender']}")
            print(f"    Text: {msg['text']}")
            return True
        else:
            print(f"  ✗ Message data incorrect: {msg}")
            return False
    else:
        print(f"  ✗ Expected 1 message, got {len(received_messages)}")
        return False


def test_sync_message_to_self():
    """Test handling of syncMessage when user messages themselves"""
    print("\n=== Testing syncMessage to Self (Should Skip) ===")
    
    handler = SignalHandler(phone_number="+64274268090")
    received_messages = []
    
    def callback(message):
        received_messages.append(message)
    
    handler.register_message_callback(callback)
    
    # Simulate sync message to self (should be skipped)
    message_data = {
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
                    "message": "Hello to myself",
                    "expiresInSeconds": 0,
                    "isExpirationUpdate": False,
                    "viewOnce": False
                }
            }
        },
        "account": "+64274268090"
    }
    
    handler._handle_message(message_data)
    
    # Verify message was skipped
    if len(received_messages) == 0:
        print("  ✓ Self-sent syncMessage correctly skipped")
        return True
    else:
        print(f"  ✗ Self-sent message should have been skipped, but got {len(received_messages)} message(s)")
        return False


def test_sync_message_to_other():
    """Test handling of syncMessage when user messages someone else"""
    print("\n=== Testing syncMessage to Other User ===")
    
    handler = SignalHandler(phone_number="+64274268090")
    received_messages = []
    
    def callback(message):
        received_messages.append(message)
    
    handler.register_message_callback(callback)
    
    # Simulate sync message to another user
    message_data = {
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
                    "message": "Hello from Signal Desktop",
                    "expiresInSeconds": 0,
                    "isExpirationUpdate": False,
                    "viewOnce": False
                }
            }
        },
        "account": "+64274268090"
    }
    
    handler._handle_message(message_data)
    
    # Verify message was processed
    if len(received_messages) == 1:
        msg = received_messages[0]
        if msg['sender'] == '+64274268090' and msg['text'] == 'Hello from Signal Desktop':
            print("  ✓ syncMessage to other user parsed correctly")
            print(f"    Sender: {msg['sender']}")
            print(f"    Text: {msg['text']}")
            return True
        else:
            print(f"  ✗ Message data incorrect: {msg}")
            return False
    else:
        print(f"  ✗ Expected 1 message, got {len(received_messages)}")
        return False


def test_message_without_text():
    """Test handling of messages without text (reactions, typing indicators, etc.)"""
    print("\n=== Testing Message Without Text ===")
    
    handler = SignalHandler(phone_number="+64274268090")
    received_messages = []
    
    def callback(message):
        received_messages.append(message)
    
    handler.register_message_callback(callback)
    
    # Simulate message without text (e.g., reaction)
    message_data = {
        "envelope": {
            "source": "+15555550123",
            "sourceNumber": "+15555550123",
            "timestamp": 1771049391838,
            "dataMessage": {
                "timestamp": 1771049391838,
                "reaction": {
                    "emoji": "👍",
                    "targetAuthor": "+64274268090"
                }
            }
        },
        "account": "+64274268090"
    }
    
    handler._handle_message(message_data)
    
    # Verify message was processed (but with empty text)
    if len(received_messages) == 1:
        msg = received_messages[0]
        if msg['sender'] == '+15555550123' and msg['text'] == '':
            print("  ✓ Message without text handled correctly (empty text)")
            print(f"    Sender: {msg['sender']}")
            print(f"    Text: '{msg['text']}' (empty)")
            return True
        else:
            print(f"  ✗ Message data incorrect: {msg}")
            return False
    else:
        print(f"  ✗ Expected 1 message, got {len(received_messages)}")
        return False


def test_group_message():
    """Test handling of group messages"""
    print("\n=== Testing Group dataMessage ===")
    
    handler = SignalHandler(phone_number="+64274268090")
    received_messages = []
    
    def callback(message):
        received_messages.append(message)
    
    handler.register_message_callback(callback)
    
    # Simulate group message
    message_data = {
        "envelope": {
            "source": "+15555550123",
            "sourceNumber": "+15555550123",
            "timestamp": 1771049391838,
            "dataMessage": {
                "timestamp": 1771049391838,
                "message": "Hello group!",
                "groupInfo": {
                    "groupId": "group123",
                    "type": "DELIVER"
                }
            }
        },
        "account": "+64274268090"
    }
    
    handler._handle_message(message_data)
    
    # Verify group message was processed
    if len(received_messages) == 1:
        msg = received_messages[0]
        if msg['sender'] == '+15555550123' and msg['text'] == 'Hello group!' and msg['is_group'] and msg['group_id'] == 'group123':
            print("  ✓ Group message parsed correctly")
            print(f"    Sender: {msg['sender']}")
            print(f"    Text: {msg['text']}")
            print(f"    Is Group: {msg['is_group']}")
            print(f"    Group ID: {msg['group_id']}")
            return True
        else:
            print(f"  ✗ Message data incorrect: {msg}")
            return False
    else:
        print(f"  ✗ Expected 1 message, got {len(received_messages)}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("syncMessage Fix Test Suite")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Regular dataMessage", test_regular_data_message()))
    results.append(("syncMessage to Self (Skip)", test_sync_message_to_self()))
    results.append(("syncMessage to Other", test_sync_message_to_other()))
    results.append(("Message Without Text", test_message_without_text()))
    results.append(("Group Message", test_group_message()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for result in results if result[1])
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
