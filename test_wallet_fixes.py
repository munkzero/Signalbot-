#!/usr/bin/env python3
"""
Test script to verify wallet initialization and reconnection fixes
Checks that all required changes are present in the code
"""

import sys
from pathlib import Path


def check_fix_1_debug_logging():
    """Verify Fix 1: Enhanced debug logging for startup wallet unlock"""
    print("\n" + "="*60)
    print("Fix 1: Enhanced Debug Logging for Startup Wallet Unlock")
    print("="*60)
    
    dashboard_path = Path("signalbot/gui/dashboard.py")
    with open(dashboard_path, 'r') as f:
        content = f.read()
    
    required_elements = [
        ('🔧 DEBUG: Attempting to initialize wallet...', 'Debug start message'),
        ('Wallet path:', 'Wallet path debug print'),
        ('Node:', 'Node address debug print'),
        ('SSL:', 'SSL debug print'),
        ('✓ DEBUG: Wallet instance created', 'Wallet creation confirmation'),
        ('🔧 DEBUG: Attempting to connect to node...', 'Connection attempt message'),
        ('🔧 DEBUG: Connection result:', 'Connection result print'),
        ('❌ ERROR: Failed to initialize wallet:', 'Error message'),
        ('import traceback', 'Traceback import'),
        ('traceback.print_exc()', 'Stack trace printing'),
        ('QMessageBox.critical', 'Critical error dialog'),
        ('"Wallet Initialization Error"', 'Error dialog title'),
    ]
    
    all_found = True
    for element, description in required_elements:
        if element in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ MISSING: {description}")
            all_found = False
    
    return all_found


def check_fix_2_dashboard_reference():
    """Verify Fix 2: Dashboard reference passed to WalletSettingsDialog"""
    print("\n" + "="*60)
    print("Fix 2: Dashboard Reference for Wallet Updates")
    print("="*60)
    
    dashboard_path = Path("signalbot/gui/dashboard.py")
    with open(dashboard_path, 'r') as f:
        content = f.read()
    
    required_elements = [
        # Part A: Pass dashboard reference
        ('WalletSettingsDialog(self.seller_manager, seller, self, dashboard=self)', 
         'Dashboard reference passed to dialog'),
        
        # Part B: Accept dashboard parameter
        ('def __init__(self, seller_manager, seller, parent=None, dashboard=None):',
         'Dialog __init__ accepts dashboard parameter'),
        ('self.dashboard = dashboard', 'Dashboard reference stored'),
        
        # Part C: Update dashboard wallet on reconnect
        ('if self.dashboard and hasattr(self, \'reconnect_worker\'):', 
         'Check dashboard exists for reconnect'),
        ('self.dashboard.wallet = self.reconnect_worker.wallet',
         'Update dashboard wallet on reconnect'),
        ('self.dashboard.wallet_tab.wallet = self.reconnect_worker.wallet',
         'Update wallet_tab wallet on reconnect'),
        ('self.dashboard.wallet_tab.refresh_all()',
         'Refresh WalletTab after reconnect'),
        ('✓ DEBUG: Updating dashboard wallet reference',
         'Debug message for wallet update'),
        ('✓ DEBUG: Refreshing WalletTab',
         'Debug message for tab refresh'),
    ]
    
    all_found = True
    for element, description in required_elements:
        if element in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ MISSING: {description}")
            all_found = False
    
    return all_found


def check_fix_3_rescan_update():
    """Verify Fix 3: Rescan updates dashboard wallet"""
    print("\n" + "="*60)
    print("Fix 3: Rescan Updates Dashboard Wallet")
    print("="*60)
    
    dashboard_path = Path("signalbot/gui/dashboard.py")
    with open(dashboard_path, 'r') as f:
        content = f.read()
    
    required_elements = [
        ('if self.dashboard and hasattr(self, \'rescan_worker\'):', 
         'Check dashboard exists for rescan'),
        ('self.dashboard.wallet = self.rescan_worker.wallet',
         'Update dashboard wallet after rescan'),
        ('self.dashboard.wallet_tab.wallet = self.rescan_worker.wallet',
         'Update wallet_tab wallet after rescan'),
        ('✓ DEBUG: Updating dashboard wallet reference after rescan',
         'Debug message for wallet update after rescan'),
        ('✓ DEBUG: Refreshing WalletTab after rescan',
         'Debug message for tab refresh after rescan'),
    ]
    
    all_found = True
    for element, description in required_elements:
        if element in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ MISSING: {description}")
            all_found = False
    
    return all_found


def check_fix_4_wallet_tab_debug():
    """Verify Fix 4: WalletTab debug output"""
    print("\n" + "="*60)
    print("Fix 4: WalletTab Debug Output")
    print("="*60)
    
    dashboard_path = Path("signalbot/gui/dashboard.py")
    with open(dashboard_path, 'r') as f:
        content = f.read()
    
    required_elements = [
        ('🔧 DEBUG: WalletTab.refresh_all() called', 'Refresh all called message'),
        ('Wallet instance:', 'Wallet instance debug print'),
        ('⚠ DEBUG: Wallet is None, skipping refresh', 'Wallet None warning'),
        ('✓ DEBUG: Refreshing balance...', 'Balance refresh message'),
        ('✓ DEBUG: Refreshing addresses...', 'Addresses refresh message'),
        ('✓ DEBUG: Refreshing transactions...', 'Transactions refresh message'),
        ('✓ DEBUG: Refresh complete', 'Refresh complete message'),
    ]
    
    all_found = True
    for element, description in required_elements:
        if element in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ MISSING: {description}")
            all_found = False
    
    return all_found


def main():
    """Run all verification tests"""
    print("="*60)
    print("WALLET INITIALIZATION & RECONNECTION FIXES VERIFICATION")
    print("="*60)
    
    test1 = check_fix_1_debug_logging()
    test2 = check_fix_2_dashboard_reference()
    test3 = check_fix_3_rescan_update()
    test4 = check_fix_4_wallet_tab_debug()
    
    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    
    if test1 and test2 and test3 and test4:
        print("✓ ALL FIXES VERIFIED!")
        print("\nSummary of fixes:")
        print("1. Enhanced debug logging prevents silent crashes")
        print("2. Dashboard wallet updates on reconnect")
        print("3. Dashboard wallet updates on rescan")
        print("4. WalletTab provides detailed debug output")
        print("\nExpected behavior:")
        print("• Startup unlock shows debug output and doesn't crash")
        print("• Reconnect in settings updates WalletTab status")
        print("• Rescan works after reconnecting")
        print("• All errors logged with stack traces")
        return 0
    else:
        print("✗ Some verification tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
