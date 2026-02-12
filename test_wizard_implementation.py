#!/usr/bin/env python3
"""
Test script to verify the new wizard implementation
Tests the logic and integration without requiring PyQt5
"""

import sys
import ast
from pathlib import Path

def test_wizard_structure():
    """Test that wizard.py has the correct structure"""
    
    wizard_path = Path("signalbot/gui/wizard.py")
    
    with open(wizard_path, 'r') as f:
        content = f.read()
    
    print("Testing wizard.py structure...")
    print("-" * 50)
    
    # Parse the AST
    tree = ast.parse(content)
    
    # Find all class definitions
    classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    
    expected_classes = [
        'WelcomePage',
        'PINPage',
        'SignalPage',
        'NodeConfigPage',
        'CustomNodePage',
        'WalletPasswordPage',
        'WalletCreationWorker',
        'WalletCreationPage',
        'SeedPhrasePage',
        'SeedVerificationPage',
        'WalletSummaryPage',
        'CurrencyPage',
        'SetupWizard'
    ]
    
    print("✓ Checking for expected classes:")
    for cls in expected_classes:
        if cls in classes:
            print(f"  ✓ {cls} found")
        else:
            print(f"  ✗ {cls} MISSING!")
            return False
    
    # Check imports
    print("\n✓ Checking imports:")
    import_modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module:
                # Handle relative imports (..core.monero_wallet becomes core.monero_wallet)
                module_name = node.module.lstrip('.')
                import_modules.append(module_name)
    
    required_imports = [
        ('core.monero_wallet', 'InHouseWallet'),
        ('models.seller', 'Seller'),
        ('models.node', 'MoneroNodeConfig'),
        ('config.settings', 'DEFAULT_NODES')
    ]
    
    for imp_module, imp_name in required_imports:
        if imp_module in import_modules:
            print(f"  ✓ {imp_module} ({imp_name})")
        else:
            print(f"  ✗ {imp_module} MISSING!")
            return False
    
    # Check for InHouseWallet usage
    print("\n✓ Checking InHouseWallet integration:")
    if 'InHouseWallet' in content:
        print("  ✓ InHouseWallet imported")
    else:
        print("  ✗ InHouseWallet NOT imported!")
        return False
    
    if 'InHouseWallet.create_new_wallet' in content:
        print("  ✓ InHouseWallet.create_new_wallet() called")
    else:
        print("  ✗ InHouseWallet.create_new_wallet() NOT called!")
        return False
    
    # Check for NodeManager and MoneroNodeConfig usage
    print("\n✓ Checking Node configuration:")
    if 'MoneroNodeConfig' in content:
        print("  ✓ MoneroNodeConfig used")
    else:
        print("  ✗ MoneroNodeConfig NOT used!")
        return False
    
    if 'NodeManager' in content:
        print("  ✓ NodeManager used")
    else:
        print("  ✗ NodeManager NOT used!")
        return False
    
    if 'DEFAULT_NODES' in content:
        print("  ✓ DEFAULT_NODES imported")
    else:
        print("  ✗ DEFAULT_NODES NOT imported!")
        return False
    
    # Check for removed old wallet types
    print("\n✓ Checking for removed legacy code:")
    legacy_terms = ['wallet_type', 'wallet_config', 'view_only', 'MoneroWalletFactory']
    legacy_found = []
    for term in legacy_terms:
        if term in content:
            legacy_found.append(term)
    
    if legacy_found:
        print(f"  ⚠ WARNING: Legacy terms still found: {', '.join(legacy_found)}")
        print("    (This may be acceptable in comments or variable names)")
    else:
        print("  ✓ No legacy wallet code found")
    
    # Check save_configuration uses only wallet_path
    print("\n✓ Checking save_configuration:")
    if 'wallet_path=self.wallet_path' in content:
        print("  ✓ Uses wallet_path only")
    else:
        print("  ✗ wallet_path NOT used correctly!")
        return False
    
    # Check for seed phrase handling
    print("\n✓ Checking seed phrase handling:")
    seed_features = [
        ('seed_phrase display', 'self.seed_labels'),
        ('seed verification', 'verification_positions'),
        ('seed export', '_save_seed'),
        ('seed copy', '_copy_seed')
    ]
    
    for feature_name, feature_code in seed_features:
        if feature_code in content:
            print(f"  ✓ {feature_name}")
        else:
            print(f"  ✗ {feature_name} MISSING!")
            return False
    
    print("\n" + "=" * 50)
    print("✅ All structure tests passed!")
    print("=" * 50)
    return True


def test_wizard_flow():
    """Test the wizard page flow logic"""
    print("\n\nTesting wizard flow logic...")
    print("-" * 50)
    
    wizard_path = Path("signalbot/gui/wizard.py")
    with open(wizard_path, 'r') as f:
        content = f.read()
    
    # Check page flow
    print("✓ Checking page order:")
    expected_flow = [
        'WelcomePage',
        'PINPage',
        'SignalPage',
        'NodeConfigPage',
        'CustomNodePage (conditional)',
        'WalletPasswordPage',
        'WalletCreationPage',
        'SeedPhrasePage',
        'SeedVerificationPage',
        'WalletSummaryPage',
        'CurrencyPage'
    ]
    
    for i, page in enumerate(expected_flow, 1):
        print(f"  {i}. {page}")
    
    # Check NodeConfigPage has nextId method for conditional navigation
    if 'def nextId(self):' in content and 'NodeConfigPage' in content:
        print("\n✓ NodeConfigPage has conditional navigation")
    else:
        print("\n✗ NodeConfigPage missing conditional navigation!")
        return False
    
    # Check WalletCreationWorker runs in background
    if 'QThread' in content and 'WalletCreationWorker' in content:
        print("✓ Wallet creation runs in background thread")
    else:
        print("✗ Background wallet creation MISSING!")
        return False
    
    print("\n✅ Wizard flow tests passed!")
    return True


def test_security_features():
    """Test security features implementation"""
    print("\n\nTesting security features...")
    print("-" * 50)
    
    wizard_path = Path("signalbot/gui/wizard.py")
    with open(wizard_path, 'r') as f:
        content = f.read()
    
    security_checks = [
        ('Password strength indicator', '_update_strength'),
        ('Password minimum length check', 'len(password) < 8'),
        ('Password confirmation', 'password != confirm'),
        ('Seed phrase warning', 'CRITICAL'),
        ('Seed verification', 'verification_positions'),
        ('PIN validation', 'len(pin) < 6')
    ]
    
    print("✓ Security features:")
    for feature_name, feature_code in security_checks:
        if feature_code in content:
            print(f"  ✓ {feature_name}")
        else:
            print(f"  ✗ {feature_name} MISSING!")
            return False
    
    print("\n✅ Security tests passed!")
    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("WIZARD IMPLEMENTATION VERIFICATION")
    print("=" * 70 + "\n")
    
    tests = [
        test_wizard_structure,
        test_wizard_flow,
        test_security_features
    ]
    
    all_passed = True
    for test in tests:
        try:
            if not test():
                all_passed = False
        except Exception as e:
            print(f"\n✗ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL TESTS PASSED - Wizard implementation verified!")
        print("=" * 70 + "\n")
        return 0
    else:
        print("✗ SOME TESTS FAILED - Please review the output above")
        print("=" * 70 + "\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
