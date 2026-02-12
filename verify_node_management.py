#!/usr/bin/env python3
"""
Verification script for node management features
"""

import ast
import sys
from pathlib import Path

def verify_implementation():
    """Verify node management implementation"""
    print("Verifying node management implementation...")
    
    # Use Path for cross-platform compatibility
    base_dir = Path(__file__).parent
    dashboard_path = base_dir / "signalbot" / "gui" / "dashboard.py"
    
    with open(dashboard_path, 'r') as f:
        content = f.read()
    
    # Parse the AST
    try:
        tree = ast.parse(content)
        print("✅ Python syntax is valid")
    except SyntaxError as e:
        print(f"❌ Syntax error: {e}")
        return False
    
    # Check imports
    required_imports = [
        "NodeManager",
        "MoneroNodeConfig"
    ]
    
    imports_found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and 'node' in node.module:
                for alias in node.names:
                    imports_found.append(alias.name)
    
    for imp in required_imports:
        if imp in imports_found:
            print(f"✅ Import found: {imp}")
        else:
            print(f"❌ Missing import: {imp}")
            return False
    
    # Check classes
    required_classes = [
        "TestNodeWorker",
        "ReconnectWalletWorker",
        "RescanBlockchainWorker",
        "WalletSettingsDialog",
        "AddNodeDialog",
        "EditNodeDialog"
    ]
    
    classes_found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes_found.append(node.name)
    
    for cls in required_classes:
        if cls in classes_found:
            print(f"✅ Class found: {cls}")
        else:
            print(f"❌ Missing class: {cls}")
            return False
    
    # Check WalletSettingsDialog methods
    wallet_dialog_methods = [
        "_create_connect_tab",
        "_create_nodes_tab",
        "refresh_nodes_table",
        "reconnect_wallet",
        "rescan_blockchain",
        "add_node",
        "edit_node",
        "delete_node",
        "set_default_node"
    ]
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "WalletSettingsDialog":
            methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
            for method in wallet_dialog_methods:
                if method in methods:
                    print(f"✅ WalletSettingsDialog method: {method}")
                else:
                    print(f"❌ Missing WalletSettingsDialog method: {method}")
                    return False
            break
    
    # Check AddNodeDialog methods
    add_dialog_methods = [
        "test_connection",
        "on_test_finished",
        "save_node"
    ]
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "AddNodeDialog":
            methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
            for method in add_dialog_methods:
                if method in methods:
                    print(f"✅ AddNodeDialog method: {method}")
                else:
                    print(f"❌ Missing AddNodeDialog method: {method}")
                    return False
            break
    
    # Check EditNodeDialog methods
    edit_dialog_methods = [
        "test_connection",
        "on_test_finished",
        "save_node"
    ]
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "EditNodeDialog":
            methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
            for method in edit_dialog_methods:
                if method in methods:
                    print(f"✅ EditNodeDialog method: {method}")
                else:
                    print(f"❌ Missing EditNodeDialog method: {method}")
                    return False
            break
    
    # Check SettingsTab has open_wallet_settings
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "SettingsTab":
            methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
            if "open_wallet_settings" in methods:
                print(f"✅ SettingsTab method: open_wallet_settings")
            else:
                print(f"❌ Missing SettingsTab method: open_wallet_settings")
                return False
            break
    
    # Check for QThread usage in workers
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if node.name in ["TestNodeWorker", "ReconnectWalletWorker", "RescanBlockchainWorker"]:
                if node.bases:
                    base_names = []
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            base_names.append(base.id)
                    if "QThread" in base_names:
                        print(f"✅ {node.name} extends QThread")
                    else:
                        print(f"❌ {node.name} does not extend QThread")
                        return False
    
    # Verify updated wallet section
    if "wallet_settings_btn = QPushButton" in content and '"Wallet Settings"' in content:
        print("✅ Updated wallet section with 'Wallet Settings' button")
    else:
        print("❌ Missing updated wallet section")
        return False
    
    if "node_manager = NodeManager" in content:
        print("✅ NodeManager instantiation in SettingsTab")
    else:
        print("❌ Missing NodeManager instantiation")
        return False
    
    if "default_node = node_manager.get_default_node()" in content:
        print("✅ Default node retrieval in SettingsTab")
    else:
        print("❌ Missing default node retrieval")
        return False
    
    # Check for proper signals in workers
    signal_checks = [
        ('TestNodeWorker', 'finished = pyqtSignal'),
        ('ReconnectWalletWorker', 'finished = pyqtSignal'),
        ('ReconnectWalletWorker', 'progress = pyqtSignal'),
        ('RescanBlockchainWorker', 'finished = pyqtSignal'),
        ('RescanBlockchainWorker', 'progress = pyqtSignal'),
    ]
    
    for worker_class, signal_pattern in signal_checks:
        # Find class in content
        class_start = content.find(f"class {worker_class}")
        if class_start == -1:
            continue
        class_end = content.find("\nclass ", class_start + 1)
        if class_end == -1:
            class_end = len(content)
        class_content = content[class_start:class_end]
        
        if signal_pattern in class_content:
            print(f"✅ {worker_class} has signal: {signal_pattern}")
        else:
            print(f"❌ {worker_class} missing signal: {signal_pattern}")
            return False
    
    print("\n" + "="*60)
    print("✅ All verification checks passed!")
    print("="*60)
    return True

if __name__ == "__main__":
    success = verify_implementation()
    sys.exit(0 if success else 1)
