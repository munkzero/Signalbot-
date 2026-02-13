#!/usr/bin/env python3
"""
Test script to verify the deferred dialog fixes for wallet initialization
Checks that blocking dialogs are deferred using QTimer.singleShot()
"""

import sys
from pathlib import Path


def check_deferred_connection_warning():
    """Verify connection warning is deferred"""
    print("\n" + "="*60)
    print("Test 1: Deferred Connection Warning")
    print("="*60)
    
    dashboard_path = Path("signalbot/gui/dashboard.py")
    with open(dashboard_path, 'r') as f:
        content = f.read()
    
    required_elements = [
        # Check class constant
        ('DIALOG_DEFER_DELAY_MS = 500',
         'Dialog defer delay constant'),
        # Check deferred call uses constant
        ('QTimer.singleShot(self.DIALOG_DEFER_DELAY_MS, lambda: self._show_connection_warning())', 
         'Deferred connection warning call with constant'),
        # Check helper method exists
        ('def _show_connection_warning(self):', 
         'Connection warning helper method'),
        ('🔧 DEBUG: Showing deferred connection warning',
         'Debug message in helper'),
        ('"Wallet Connection Failed"',
         'Dialog title in helper'),
        ('Possible reasons:', 
         'Helpful error information'),
        ('• Node is down or unreachable',
         'Node down reason'),
        ('Settings → Wallet Settings → Manage Nodes',
         'Recovery instructions'),
        # Ensure old blocking call is removed
    ]
    
    all_found = True
    for element, description in required_elements:
        if element in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ MISSING: {description}")
            all_found = False
    
    # Verify old blocking call is removed from connection failure section
    print("\n  Checking that old blocking call is removed:")
    # We need to check context - the blocking call should not be in the connection failure section
    # Look for the pattern around connection failure
    if 'print("⚠ Wallet initialized but connection failed")' in content:
        # Find the section
        idx = content.find('print("⚠ Wallet initialized but connection failed")')
        section = content[idx:idx+500]
        
        # Check that QMessageBox.warning with "Connection Failed" is NOT in this section
        if 'QMessageBox.warning' in section and '"Connection Failed"' in section:
            print(f"  ✗ Old blocking QMessageBox.warning still present in connection failure section")
            all_found = False
        else:
            print(f"  ✓ Old blocking QMessageBox.warning removed from connection failure section")
    
    return all_found


def check_deferred_initialization_error():
    """Verify initialization error is deferred"""
    print("\n" + "="*60)
    print("Test 2: Deferred Initialization Error")
    print("="*60)
    
    dashboard_path = Path("signalbot/gui/dashboard.py")
    with open(dashboard_path, 'r') as f:
        content = f.read()
    
    required_elements = [
        # Check deferred call
        ('error_msg = str(e)', 
         'Error message captured'),
        ('QTimer.singleShot(self.DIALOG_DEFER_DELAY_MS, lambda: self._show_initialization_error(error_msg))', 
         'Deferred initialization error call with constant'),
        # Check helper method exists
        ('def _show_initialization_error(self, error_msg):', 
         'Initialization error helper method'),
        ('🔧 DEBUG: Showing deferred initialization error',
         'Debug message in helper'),
        ('"Wallet Initialization Error"',
         'Dialog title in helper'),
        ('Settings → Wallet Settings → Connect & Sync → Reconnect Now',
         'Recovery instructions'),
    ]
    
    all_found = True
    for element, description in required_elements:
        if element in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ MISSING: {description}")
            all_found = False
    
    # Verify old blocking call is removed from exception handler
    print("\n  Checking that old blocking call is removed:")
    if '❌ ERROR: Failed to initialize wallet:' in content:
        # Find the exception handler section
        idx = content.find('❌ ERROR: Failed to initialize wallet:')
        section = content[idx:idx+600]
        
        # Check that immediate QMessageBox.critical is NOT in this section
        # (it should be in the helper method instead)
        if 'QMessageBox.critical' in section and 'def _show_initialization_error' not in section:
            # This might be the old blocking call
            # Let's be more specific - check if it's within the exception handler
            if 'traceback.print_exc()' in section:
                exc_idx = section.find('traceback.print_exc()')
                after_traceback = section[exc_idx:]
                if 'QMessageBox.critical' in after_traceback[:200] and 'QTimer.singleShot' not in after_traceback[:200]:
                    print(f"  ✗ Old blocking QMessageBox.critical still present in exception handler")
                    all_found = False
                else:
                    print(f"  ✓ Old blocking QMessageBox.critical removed from exception handler")
        else:
            print(f"  ✓ Old blocking QMessageBox.critical removed from exception handler")
    
    return all_found


def check_dashboard_completion_log():
    """Verify dashboard initialization completion log"""
    print("\n" + "="*60)
    print("Test 3: Dashboard Initialization Completion Log")
    print("="*60)
    
    dashboard_path = Path("signalbot/gui/dashboard.py")
    with open(dashboard_path, 'r') as f:
        content = f.read()
    
    required_elements = [
        ('print("✓ DEBUG: Dashboard initialization completed successfully")',
         'Completion debug log'),
    ]
    
    all_found = True
    for element, description in required_elements:
        if element in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ MISSING: {description}")
            all_found = False
    
    # Verify it's at the end of __init__
    if 'self.setCentralWidget(tabs)' in content:
        idx = content.find('self.setCentralWidget(tabs)')
        # Check that the debug log comes shortly after
        section_after = content[idx:idx+200]
        if 'Dashboard initialization completed successfully' in section_after:
            print(f"  ✓ Completion log is placed at end of __init__")
        else:
            print(f"  ✗ Completion log not at end of __init__")
            all_found = False
    
    return all_found


def check_qtimer_import():
    """Verify QTimer is imported"""
    print("\n" + "="*60)
    print("Test 4: QTimer Import")
    print("="*60)
    
    dashboard_path = Path("signalbot/gui/dashboard.py")
    with open(dashboard_path, 'r') as f:
        content = f.read()
    
    # Check for QTimer in imports
    import_section = content[:2000]  # Check first 2000 chars for imports
    
    if 'QTimer' in import_section and 'from PyQt5.QtCore import' in import_section:
        print(f"  ✓ QTimer is imported from PyQt5.QtCore")
        return True
    else:
        print(f"  ✗ QTimer import missing or incorrect")
        return False


def main():
    """Run all verification tests"""
    print("="*60)
    print("DEFERRED DIALOG FIXES VERIFICATION")
    print("="*60)
    
    test1 = check_deferred_connection_warning()
    test2 = check_deferred_initialization_error()
    test3 = check_dashboard_completion_log()
    test4 = check_qtimer_import()
    
    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    
    if test1 and test2 and test3 and test4:
        print("✓ ALL FIXES VERIFIED!")
        print("\nSummary of fixes:")
        print("1. Connection warning dialog is deferred using QTimer")
        print("2. Initialization error dialog is deferred using QTimer")
        print("3. Dashboard initialization completion is logged")
        print("4. QTimer is properly imported")
        print("\nExpected behavior:")
        print("• Dashboard loads completely even if wallet connection fails")
        print("• Warning/error dialogs appear 500ms AFTER dashboard is visible")
        print("• User can access Settings to fix node configuration")
        print("• App never crashes due to wallet initialization failures")
        return 0
    else:
        print("✗ Some verification tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
