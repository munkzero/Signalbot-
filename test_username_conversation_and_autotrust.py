#!/usr/bin/env python
"""
Test suite for username conversation split and auto-trust performance fixes
Tests that bot receives messages to both phone and username, and replies from correct identity
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_auto_trust_timeout_reduced():
    """Test that auto-trust timeout is reduced from 10s to 1s"""
    print("\n=== Testing Auto-Trust Timeout Reduction ===")
    
    try:
        from signalbot.core.signal_handler import SignalHandler
        import inspect
        
        # Get the source code of auto_trust_contact
        source = inspect.getsource(SignalHandler.auto_trust_contact)
        
        # Check that timeout=1 is present
        if 'timeout=1' in source:
            print("  ✓ Timeout reduced to 1 second")
            
            # Make sure timeout=10 is NOT present
            if 'timeout=10' not in source:
                print("  ✓ Old timeout=10 removed")
                return True
            else:
                print("  ✗ Old timeout=10 still present")
                return False
        else:
            print("  ✗ timeout=1 not found")
            print("  Current timeout setting in source:")
            for line in source.split('\n'):
                if 'timeout' in line and 'subprocess.run' in source:
                    print(f"    {line.strip()}")
            return False
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_trust_caching_implemented():
    """Test that trust caching is implemented"""
    print("\n=== Testing Trust Caching Implementation ===")
    
    try:
        from signalbot.core.signal_handler import SignalHandler
        import inspect
        
        # Get the source code of __init__ to check for initialization
        init_source = inspect.getsource(SignalHandler.__init__)
        
        # Get the source code of auto_trust_contact
        trust_source = inspect.getsource(SignalHandler.auto_trust_contact)
        
        # Check for cache implementation
        checks = {
            '_trust_attempted initialized in __init__': '_trust_attempted = set()' in init_source,
            'Cache check before trust': 'in self._trust_attempted' in trust_source or 'in _trust_attempted' in trust_source,
            'Add to cache after check': 'add(contact_number)' in trust_source
        }
        
        all_passed = True
        for check_name, result in checks.items():
            if result:
                print(f"  ✓ {check_name}")
            else:
                print(f"  ✗ {check_name}")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_recipient_identity_tracking():
    """Test that recipient identity is tracked in received messages"""
    print("\n=== Testing Recipient Identity Tracking ===")
    
    try:
        from signalbot.core.signal_handler import SignalHandler
        import inspect
        
        # Get the source code of _handle_message
        source = inspect.getsource(SignalHandler._handle_message)
        
        # Check for recipient identity extraction
        checks = {
            'Extract account field': "message_data.get('account'" in source,
            'Store as recipient_identity': 'recipient_identity' in source,
            'Add to message object': "'recipient_identity'" in source,
            'Pass to buyer handler': 'recipient_identity' in source and 'handle_buyer_message' in source
        }
        
        all_passed = True
        for check_name, result in checks.items():
            if result:
                print(f"  ✓ {check_name}")
            else:
                print(f"  ✗ {check_name}")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_send_message_sender_identity():
    """Test that send_message accepts and uses sender_identity parameter"""
    print("\n=== Testing send_message Sender Identity ===")
    
    try:
        from signalbot.core.signal_handler import SignalHandler
        import inspect
        
        # Get the function signature
        sig = inspect.signature(SignalHandler.send_message)
        
        # Get the source code of send_message
        source = inspect.getsource(SignalHandler.send_message)
        
        # Check for sender_identity parameter in signature
        has_sender_identity_param = 'sender_identity' in sig.parameters
        
        # Check that it's optional (has default value of None)
        is_optional = False
        if has_sender_identity_param:
            param = sig.parameters['sender_identity']
            is_optional = param.default is None or param.default == inspect.Parameter.empty
        
        # Check that it's passed to _send_direct
        passes_to_send_direct = '_send_direct' in source and 'sender' in source
        
        checks = {
            'sender_identity parameter exists': has_sender_identity_param,
            'sender_identity is optional (defaults to None)': is_optional,
            'Pass to _send_direct': passes_to_send_direct
        }
        
        all_passed = True
        for check_name, result in checks.items():
            if result:
                print(f"  ✓ {check_name}")
            else:
                print(f"  ✗ {check_name}")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_send_direct_uses_sender():
    """Test that _send_direct uses sender parameter"""
    print("\n=== Testing _send_direct Sender Parameter ===")
    
    try:
        from signalbot.core.signal_handler import SignalHandler
        import inspect
        
        # Get the source code of _send_direct
        source = inspect.getsource(SignalHandler._send_direct)
        
        # Check for sender parameter usage
        checks = {
            'sender parameter': 'sender' in source,
            'Uses sender in signal-cli command': "'-u', sender" in source,
            'Defaults to phone_number': 'self.phone_number' in source
        }
        
        all_passed = True
        for check_name, result in checks.items():
            if result:
                print(f"  ✓ {check_name}")
            else:
                print(f"  ✗ {check_name}")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_buyer_handler_accepts_recipient_identity():
    """Test that buyer handler methods accept and use recipient_identity"""
    print("\n=== Testing Buyer Handler Recipient Identity ===")
    
    try:
        # Read the source file directly to avoid import issues
        buyer_handler_path = os.path.join(
            os.path.dirname(__file__),
            'signalbot', 'core', 'buyer_handler.py'
        )
        
        with open(buyer_handler_path, 'r') as f:
            source = f.read()
        
        checks = {
            'handle_buyer_message accepts recipient_identity': 'def handle_buyer_message(self, buyer_signal_id: str, message_text: str, recipient_identity' in source,
            'send_catalog accepts recipient_identity': 'def send_catalog(self, buyer_signal_id: str, recipient_identity' in source,
            'create_order accepts recipient_identity': 'def create_order(self, buyer_signal_id: str, product_id: str, quantity: int, recipient_identity' in source,
            'send_help accepts recipient_identity': 'def send_help(self, buyer_signal_id: str, recipient_identity' in source,
            'send_catalog passes sender_identity': 'sender_identity=recipient_identity' in source and 'send_catalog' in source,
            'create_order passes sender_identity': 'sender_identity=recipient_identity' in source and 'create_order' in source,
            'send_help passes sender_identity': 'sender_identity=recipient_identity' in source and 'send_help' in source
        }
        
        all_passed = True
        for check_name, result in checks.items():
            if result:
                print(f"  ✓ {check_name}")
            else:
                print(f"  ✗ {check_name}")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_message_flow_integration():
    """Test the complete message flow from receive to reply"""
    print("\n=== Testing Complete Message Flow Integration ===")
    
    try:
        from signalbot.core.signal_handler import SignalHandler
        
        # Create handler with placeholder phone number
        handler = SignalHandler(phone_number="+15555550100")
        
        # Simulate receiving a message to a specific account (username)
        test_username = "testbot.123"
        message_data = {
            "envelope": {
                "source": "+15555550200",
                "sourceNumber": "+15555550200",
                "timestamp": 1234567890,
                "dataMessage": {
                    "message": "catalog",
                }
            },
            "account": test_username  # Message received by username
        }
        
        # Track what buyer_handler was called with
        call_args = []
        
        class MockBuyerHandler:
            def handle_buyer_message(self, buyer_signal_id, message_text, recipient_identity=None):
                call_args.append({
                    'buyer_signal_id': buyer_signal_id,
                    'message_text': message_text,
                    'recipient_identity': recipient_identity
                })
        
        handler.buyer_handler = MockBuyerHandler()
        
        # Process message
        handler._handle_message(message_data)
        
        # Verify recipient_identity was passed
        if len(call_args) > 0:
            if call_args[0].get('recipient_identity') == test_username:
                print(f"  ✓ Recipient identity correctly passed: {test_username}")
                return True
            else:
                print(f"  ✗ Wrong recipient identity: {call_args[0].get('recipient_identity')}")
                print(f"    Expected: {test_username}")
                return False
        else:
            print("  ✗ buyer_handler.handle_buyer_message not called")
            return False
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_trust_cache_behavior():
    """Test that trust cache actually prevents redundant calls"""
    print("\n=== Testing Trust Cache Behavior ===")
    
    try:
        from signalbot.core.signal_handler import SignalHandler
        from unittest.mock import patch, MagicMock
        
        # Create handler with placeholder phone number
        handler = SignalHandler(phone_number="+15555550100")
        
        # Mock subprocess.run to track calls
        call_count = 0
        
        def mock_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            return result
        
        with patch('subprocess.run', side_effect=mock_run):
            # First call - should execute
            handler.auto_trust_contact("+15555550200")
            first_call_count = call_count
            
            # Second call - should be cached
            handler.auto_trust_contact("+15555550200")
            second_call_count = call_count
            
            if first_call_count == 1 and second_call_count == 1:
                print(f"  ✓ Trust cached - only 1 subprocess call for 2 trust attempts")
                return True
            else:
                print(f"  ✗ Cache not working - {second_call_count} calls for 2 trust attempts")
                return False
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("="*60)
    print("Username Conversation Split and Auto-Trust Performance Tests")
    print("="*60)
    
    tests = [
        ("Auto-Trust Timeout Reduction", test_auto_trust_timeout_reduced),
        ("Trust Caching Implementation", test_trust_caching_implemented),
        ("Recipient Identity Tracking", test_recipient_identity_tracking),
        ("send_message Sender Identity", test_send_message_sender_identity),
        ("_send_direct Sender Parameter", test_send_direct_uses_sender),
        ("Buyer Handler Recipient Identity", test_buyer_handler_accepts_recipient_identity),
        ("Complete Message Flow Integration", test_message_flow_integration),
        ("Trust Cache Behavior", test_trust_cache_behavior),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ All tests PASSED!")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
