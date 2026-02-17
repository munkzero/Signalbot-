#!/usr/bin/env python3
"""
Test wallet initialization fixes:
- Restore height support
- Extended timeout for new wallets
- Formatted seed phrase display
- Blockchain height retrieval
"""

import sys
from pathlib import Path

def test_get_blockchain_height():
    """Test that get_current_blockchain_height function exists"""
    print("\n" + "=" * 70)
    print("Test 1: Get Blockchain Height Function")
    print("=" * 70)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    checks = [
        ('def get_current_blockchain_height(daemon_address: str, daemon_port: int)', 'Function signature'),
        ('requests.get', 'HTTP GET request'),
        ('/get_height', 'Get height endpoint'),
        ('response.json().get("height")', 'Parse height from response'),
        ('return height', 'Return height value'),
        ('return None', 'Return None on failure'),
    ]
    
    all_found = True
    for check, description in checks:
        if check in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description} - NOT FOUND: '{check}'")
            all_found = False
    
    return all_found

def test_wait_for_rpc_ready_updated():
    """Test that wait_for_rpc_ready function supports is_new_wallet parameter"""
    print("\n" + "=" * 70)
    print("Test 2: wait_for_rpc_ready Function Updated")
    print("=" * 70)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    checks = [
        ('def wait_for_rpc_ready(port=18083, max_wait=60, retry_interval=2, is_new_wallet=False)', 'Function signature with is_new_wallet'),
        ('if is_new_wallet:', 'Check for new wallet flag'),
        ('max_wait = 180', 'Extended timeout for new wallets'),
        ('New wallet - initial sync may take 2-3 minutes', 'New wallet message'),
    ]
    
    all_found = True
    for check, description in checks:
        if check in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description} - NOT FOUND")
            all_found = False
    
    return all_found

def test_display_seed_phrase():
    """Test that display_seed_phrase function exists with formatted box"""
    print("\n" + "=" * 70)
    print("Test 3: Display Seed Phrase Function")
    print("=" * 70)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    checks = [
        ('def display_seed_phrase(seed: str)', 'Function signature'),
        ('words = seed.split()', 'Split seed into words'),
        ('print("╔" + "═" * 60 + "╗")', 'Top border'),
        ('🔑 NEW WALLET CREATED - SAVE YOUR SEED PHRASE!', 'Title message'),
        ('⚠️  WRITE THIS DOWN!', 'Warning message'),
        ('without this seed phrase!', 'Recovery warning'),
        ('print("╚" + "═" * 60 + "╝")', 'Bottom border'),
    ]
    
    all_found = True
    for check, description in checks:
        if check in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description} - NOT FOUND")
            all_found = False
    
    return all_found

def test_create_wallet_with_restore_height():
    """Test that create_wallet method includes restore height"""
    print("\n" + "=" * 70)
    print("Test 4: create_wallet Method with Restore Height")
    print("=" * 70)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    checks = [
        ('get_current_blockchain_height(self.daemon_address, self.daemon_port)', 'Get blockchain height'),
        ('restore_height = max(0, current_height - 1000)', 'Calculate restore height'),
        ('Creating new wallet with restore height', 'Log restore height'),
        ("'--restore-height', str(restore_height)", 'Pass restore height to CLI'),
        ('display_seed_phrase(seed)', 'Display seed phrase in formatted box'),
    ]
    
    all_found = True
    for check, description in checks:
        if check in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description} - NOT FOUND")
            all_found = False
    
    return all_found

def test_start_rpc_updated():
    """Test that start_rpc method accepts is_new_wallet parameter"""
    print("\n" + "=" * 70)
    print("Test 5: start_rpc Method Updated")
    print("=" * 70)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    checks = [
        ('def start_rpc(self, daemon_address: Optional[str] = None,', 'start_rpc method signature'),
        ('is_new_wallet: bool = False', 'is_new_wallet parameter'),
        ('wait_for_rpc_ready(port=self.rpc_port, max_wait=60, retry_interval=2, is_new_wallet=is_new_wallet)', 'Pass is_new_wallet to wait function'),
    ]
    
    all_found = True
    for check, description in checks:
        if check in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description} - NOT FOUND")
            all_found = False
    
    return all_found

def test_setup_wallet_updated():
    """Test that setup_wallet calls start_rpc with is_new_wallet=True"""
    print("\n" + "=" * 70)
    print("Test 6: setup_wallet Method Updated")
    print("=" * 70)
    
    wallet_setup_path = Path("signalbot/core/wallet_setup.py")
    
    with open(wallet_setup_path, 'r') as f:
        content = f.read()
    
    checks = [
        ('self.start_rpc(is_new_wallet=True)', 'Call start_rpc with is_new_wallet=True for new wallets'),
    ]
    
    all_found = True
    for check, description in checks:
        if check in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description} - NOT FOUND")
            all_found = False
    
    return all_found

def main():
    """Run all tests"""
    print("=" * 70)
    print("WALLET INITIALIZATION FIXES VERIFICATION")
    print("=" * 70)
    
    results = []
    
    results.append(("Get Blockchain Height", test_get_blockchain_height()))
    results.append(("wait_for_rpc_ready Updated", test_wait_for_rpc_ready_updated()))
    results.append(("Display Seed Phrase", test_display_seed_phrase()))
    results.append(("create_wallet with Restore Height", test_create_wallet_with_restore_height()))
    results.append(("start_rpc Updated", test_start_rpc_updated()))
    results.append(("setup_wallet Updated", test_setup_wallet_updated()))
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    all_passed = True
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
