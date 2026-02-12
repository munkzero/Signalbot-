"""
Setup Wizard for Signal Shop Bot
Guides seller through initial configuration with in-house wallet creation
"""

import sys
import os
import random
import time
from typing import Optional, Dict, List
from pathlib import Path
from datetime import datetime
from PyQt5.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QRadioButton, QButtonGroup,
    QTextEdit, QMessageBox, QComboBox, QFileDialog, QScrollArea,
    QWidget, QApplication, QGroupBox, QProgressBar, QGridLayout, QCheckBox
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont

from ..core.security import security_manager
from ..core.signal_handler import SignalHandler
from ..core.monero_wallet import InHouseWallet
from ..utils.qr_generator import qr_generator
from ..models.seller import Seller, SellerManager
from ..models.node import MoneroNodeConfig, NodeManager
from ..database.db import DatabaseManager
from ..config.settings import SUPPORTED_CURRENCIES, DEFAULT_NODES, WALLET_DIR


class WelcomePage(QWizardPage):
    """Welcome page with commission disclosure"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Welcome to Signal Shop Bot")
        
        layout = QVBoxLayout()
        
        # Welcome text
        welcome_text = QLabel(
            "Welcome to Signal Shop Bot - Privacy-focused e-commerce platform.\n\n"
            "This wizard will help you set up your shop in a few simple steps:\n"
            "1. Create a secure PIN\n"
            "2. Link your Signal account\n"
            "3. Configure your Monero wallet\n"
            "4. Set your default currency\n\n"
            "⚠️ IMPORTANT DISCLOSURE:\n"
            "This bot charges a 7% commission on all sales.\n"
            "For every sale, 93% goes to you and 7% goes to the bot creator.\n"
            "Commission is automatically deducted and forwarded.\n\n"
            "By continuing, you agree to this commission structure."
        )
        welcome_text.setWordWrap(True)
        
        font = QFont()
        font.setPointSize(10)
        welcome_text.setFont(font)
        
        layout.addWidget(welcome_text)
        self.setLayout(layout)


class PINPage(QWizardPage):
    """PIN creation page"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Create Your Secure PIN")
        self.setSubTitle("This PIN will be required to access your dashboard")
        
        layout = QVBoxLayout()
        
        # PIN input
        pin_label = QLabel("Enter PIN (minimum 6 digits):")
        self.pin_input = QLineEdit()
        self.pin_input.setEchoMode(QLineEdit.Password)
        self.pin_input.setMaxLength(20)
        
        # Confirm PIN
        confirm_label = QLabel("Confirm PIN:")
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.Password)
        self.confirm_input.setMaxLength(20)
        
        layout.addWidget(pin_label)
        layout.addWidget(self.pin_input)
        layout.addWidget(confirm_label)
        layout.addWidget(self.confirm_input)
        layout.addStretch()
        
        self.setLayout(layout)
        
        # Register fields
        self.registerField("pin*", self.pin_input)
        self.registerField("pin_confirm*", self.confirm_input)
    
    def validatePage(self):
        pin = self.pin_input.text()
        confirm = self.confirm_input.text()
        
        if len(pin) < 6:
            QMessageBox.warning(self, "Invalid PIN", "PIN must be at least 6 characters")
            return False
        
        if pin != confirm:
            QMessageBox.warning(self, "PIN Mismatch", "PINs do not match")
            return False
        
        return True


class SignalPage(QWizardPage):
    """Signal account linking page"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Link Signal Account")
        self.setSubTitle("Connect your Signal account to communicate with buyers")
        
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel(
            "Click 'Generate QR Code' below, then:\n"
            "1. Open Signal on your phone\n"
            "2. Go to Settings → Linked Devices\n"
            "3. Tap 'Link New Device'\n"
            "4. Scan the QR code shown below"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Generate button
        self.generate_btn = QPushButton("Generate QR Code")
        self.generate_btn.clicked.connect(self.generate_qr)
        layout.addWidget(self.generate_btn)
        
        # QR code display in scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(500)
        
        qr_container = QWidget()
        qr_layout = QVBoxLayout()
        
        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setMinimumSize(450, 450)
        qr_layout.addWidget(self.qr_label)
        
        qr_container.setLayout(qr_layout)
        scroll_area.setWidget(qr_container)
        layout.addWidget(scroll_area)
        
        # Timer label
        self.timer_label = QLabel("")
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.timer_label)
        
        # Link text display
        link_label = QLabel("Link text (for manual entry):")
        layout.addWidget(link_label)
        
        self.link_text = QTextEdit()
        self.link_text.setReadOnly(True)
        self.link_text.setMaximumHeight(60)
        layout.addWidget(self.link_text)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.save_qr_btn = QPushButton("Save QR as Image")
        self.save_qr_btn.clicked.connect(self.save_qr_image)
        self.save_qr_btn.setEnabled(False)
        
        self.copy_link_btn = QPushButton("Copy Link Text")
        self.copy_link_btn.clicked.connect(self.copy_link_text)
        self.copy_link_btn.setEnabled(False)
        
        button_layout.addWidget(self.save_qr_btn)
        button_layout.addWidget(self.copy_link_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Phone number input (alternative)
        phone_label = QLabel("\nOr enter your Signal phone number:")
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("+15555550123")
        
        layout.addWidget(phone_label)
        layout.addWidget(self.phone_input)
        
        self.setLayout(layout)
        
        self.registerField("signal_phone", self.phone_input)
        
        self.expiration_timer = None
        self.time_remaining = 300  # 5 minutes in seconds
    
    def generate_qr(self):
        """Generate QR code for linking"""
        try:
            # In actual implementation, would use signal-cli to generate link
            # For now, show placeholder
            link_data = "tsdevice:/?uuid=placeholder&pub_key=placeholder"
            qr_data = qr_generator.generate_simple_qr(link_data)
            
            pixmap = QPixmap()
            pixmap.loadFromData(qr_data)
            # Larger QR code: 400x400 instead of 300x300
            self.qr_label.setPixmap(pixmap.scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            
            # Show link text
            self.link_text.setPlainText(link_data)
            
            # Enable buttons
            self.save_qr_btn.setEnabled(True)
            self.copy_link_btn.setEnabled(True)
            
            # Start expiration timer
            self.start_expiration_timer()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to generate QR code: {e}")
    
    def start_expiration_timer(self):
        """Start countdown timer for QR code expiration"""
        self.time_remaining = 300  # Reset to 5 minutes
        
        if self.expiration_timer:
            self.expiration_timer.stop()
        
        self.expiration_timer = QTimer()
        self.expiration_timer.timeout.connect(self.update_timer)
        self.expiration_timer.start(1000)  # Update every second
        
        self.update_timer()
    
    def update_timer(self):
        """Update timer display"""
        if self.time_remaining > 0:
            minutes = self.time_remaining // 60
            seconds = self.time_remaining % 60
            self.timer_label.setText(f"QR code expires in: {minutes}:{seconds:02d}")
            self.time_remaining -= 1
        else:
            self.timer_label.setText("QR code expired! Please generate a new one.")
            if self.expiration_timer:
                self.expiration_timer.stop()
    
    def save_qr_image(self):
        """Save QR code as image to desktop"""
        if not self.qr_label.pixmap():
            return
        
        import os
        save_path = os.path.expanduser("~/Desktop/signal_qr.png")
        
        try:
            self.qr_label.pixmap().save(save_path)
            QMessageBox.information(self, "Saved", f"QR code saved to:\n{save_path}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save QR code: {e}")
    
    def copy_link_text(self):
        """Copy link text to clipboard"""
        link = self.link_text.toPlainText()
        if link:
            QApplication.clipboard().setText(link)
            QMessageBox.information(self, "Copied", "Link copied to clipboard!")


class NodeConfigPage(QWizardPage):
    """Monero node selection page"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Select Monero Node")
        self.setSubTitle("Choose a Monero node to connect your wallet")
        
        layout = QVBoxLayout()
        
        info_label = QLabel(
            "Your wallet needs to connect to a Monero node to sync and check for payments.\n"
            "Select a node from the list or configure a custom one."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Node selection group
        node_group = QGroupBox("Node Selection")
        node_layout = QVBoxLayout()
        
        self.node_button_group = QButtonGroup()
        
        # Add default nodes as radio buttons
        for i, node in enumerate(DEFAULT_NODES):
            radio_btn = QRadioButton(f"{node['name']} - {node['address']}:{node['port']}")
            self.node_button_group.addButton(radio_btn, i)
            node_layout.addWidget(radio_btn)
            if i == 0:
                radio_btn.setChecked(True)
        
        # Custom node option
        self.custom_radio = QRadioButton("Custom Node")
        self.node_button_group.addButton(self.custom_radio, len(DEFAULT_NODES))
        node_layout.addWidget(self.custom_radio)
        
        node_group.setLayout(node_layout)
        layout.addWidget(node_group)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # Register field for node selection
        self.registerField("selected_node_index", self.node_button_group, "checkedId")
    
    def nextId(self):
        """Determine next page based on node selection"""
        selected_id = self.node_button_group.checkedId()
        if selected_id == len(DEFAULT_NODES):  # Custom node
            return self.wizard().page_ids['custom_node']
        else:
            return self.wizard().page_ids['wallet_password']


class CustomNodePage(QWizardPage):
    """Custom node configuration page"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Configure Custom Node")
        self.setSubTitle("Enter your custom Monero node details")
        
        layout = QVBoxLayout()
        
        # Node address
        address_label = QLabel("Node Address*:")
        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("node.example.com or 127.0.0.1")
        layout.addWidget(address_label)
        layout.addWidget(self.address_input)
        
        # Node port
        port_label = QLabel("Node Port*:")
        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("18081")
        self.port_input.setText("18081")
        layout.addWidget(port_label)
        layout.addWidget(self.port_input)
        
        # SSL option
        self.ssl_checkbox = QCheckBox("Use SSL/TLS connection")
        layout.addWidget(self.ssl_checkbox)
        
        # Optional authentication
        auth_group = QGroupBox("Authentication (Optional)")
        auth_layout = QVBoxLayout()
        
        username_label = QLabel("Username:")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Optional")
        auth_layout.addWidget(username_label)
        auth_layout.addWidget(self.username_input)
        
        password_label = QLabel("Password:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Optional")
        auth_layout.addWidget(password_label)
        auth_layout.addWidget(self.password_input)
        
        auth_group.setLayout(auth_layout)
        layout.addWidget(auth_group)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # Register fields
        self.registerField("custom_node_address*", self.address_input)
        self.registerField("custom_node_port*", self.port_input)
        self.registerField("custom_node_ssl", self.ssl_checkbox)
        self.registerField("custom_node_username", self.username_input)
        self.registerField("custom_node_password", self.password_input)
    
    def validatePage(self):
        """Validate custom node inputs"""
        address = self.address_input.text().strip()
        port_text = self.port_input.text().strip()
        
        if not address:
            QMessageBox.warning(self, "Invalid Input", "Please enter a node address")
            return False
        
        try:
            port = int(port_text)
            if port < 1 or port > 65535:
                raise ValueError()
        except (ValueError, TypeError):
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid port number (1-65535)")
            return False
        
        return True


class WalletPasswordPage(QWizardPage):
    """Wallet password creation page"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Create Wallet Password")
        self.setSubTitle("Secure your wallet with a strong password")
        
        layout = QVBoxLayout()
        
        info_label = QLabel(
            "⚠️ IMPORTANT: This password will encrypt your wallet file.\n"
            "Choose a strong password and keep it safe - you'll need it to access your funds.\n"
            "If you lose this password, you can recover your wallet using the seed phrase."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #d9534f; font-weight: bold;")
        layout.addWidget(info_label)
        
        # Password input
        password_label = QLabel("Wallet Password*:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Minimum 8 characters")
        layout.addWidget(password_label)
        layout.addWidget(self.password_input)
        
        # Confirm password
        confirm_label = QLabel("Confirm Password*:")
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(confirm_label)
        layout.addWidget(self.confirm_input)
        
        # Password strength indicator
        self.strength_label = QLabel("Password strength: ")
        self.strength_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.strength_label)
        
        self.password_input.textChanged.connect(self._update_strength)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # Register fields
        self.registerField("wallet_password*", self.password_input)
        self.registerField("wallet_password_confirm*", self.confirm_input)
    
    def _update_strength(self, password):
        """Update password strength indicator"""
        if len(password) == 0:
            self.strength_label.setText("Password strength: ")
            return
        
        strength = 0
        if len(password) >= 8:
            strength += 1
        if len(password) >= 12:
            strength += 1
        if any(c.isupper() for c in password):
            strength += 1
        if any(c.isdigit() for c in password):
            strength += 1
        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            strength += 1
        
        colors = ["#d9534f", "#f0ad4e", "#5bc0de", "#5cb85c"]
        labels = ["Very Weak", "Weak", "Good", "Strong"]
        
        if strength <= 1:
            idx = 0
        elif strength == 2:
            idx = 1
        elif strength == 3:
            idx = 2
        else:
            idx = 3
        
        self.strength_label.setText(f"Password strength: {labels[idx]}")
        self.strength_label.setStyleSheet(f"font-weight: bold; color: {colors[idx]};")
    
    def validatePage(self):
        """Validate password inputs"""
        password = self.password_input.text()
        confirm = self.confirm_input.text()
        
        if len(password) < 8:
            QMessageBox.warning(self, "Weak Password", "Password must be at least 8 characters long")
            return False
        
        if password != confirm:
            QMessageBox.warning(self, "Password Mismatch", "Passwords do not match")
            return False
        
        return True


class WalletCreationWorker(QThread):
    """Background worker for wallet creation"""
    
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str, str)  # success, wallet_path, seed_phrase
    
    def __init__(self, wallet_name, password, node_config):
        super().__init__()
        self.wallet_name = wallet_name
        self.password = password
        self.node_config = node_config
    
    def run(self):
        try:
            self.progress.emit(10, "Initializing wallet creation...")
            
            # Create wallet directory if needed
            Path(WALLET_DIR).mkdir(parents=True, exist_ok=True)
            
            self.progress.emit(30, "Generating seed phrase...")
            
            # Create new wallet
            wallet, seed_phrase = InHouseWallet.create_new_wallet(
                wallet_name=self.wallet_name,
                password=self.password,
                daemon_address=self.node_config.address,
                daemon_port=self.node_config.port,
                use_ssl=self.node_config.use_ssl
            )
            
            self.progress.emit(60, "Wallet created successfully...")
            
            wallet_path = wallet.wallet_path
            
            self.progress.emit(100, "Complete!")
            
            self.finished.emit(True, wallet_path, seed_phrase)
            
        except Exception as e:
            self.finished.emit(False, "", str(e))


class WalletCreationPage(QWizardPage):
    """Wallet creation progress page"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Creating Your Wallet")
        self.setSubTitle("Please wait while your wallet is being created...")
        
        layout = QVBoxLayout()
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Initializing...")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        self.setLayout(layout)
        
        self.wallet_path = None
        self.seed_phrase = None
        self.worker = None
        
        # Disable back button during creation
        self.setCommitPage(True)
    
    def initializePage(self):
        """Start wallet creation when page is shown"""
        # Get configuration from previous pages
        wizard = self.wizard()
        wallet_password = wizard.field("wallet_password")
        
        # Get node configuration
        selected_node_index = wizard.field("selected_node_index")
        
        if selected_node_index == len(DEFAULT_NODES):  # Custom node
            node_config = MoneroNodeConfig(
                address=wizard.field("custom_node_address"),
                port=int(wizard.field("custom_node_port")),
                use_ssl=wizard.field("custom_node_ssl"),
                username=wizard.field("custom_node_username") or None,
                password=wizard.field("custom_node_password") or None,
                node_name="Custom Node"
            )
        else:
            node_data = DEFAULT_NODES[selected_node_index]
            node_config = MoneroNodeConfig(
                address=node_data['address'],
                port=node_data['port'],
                use_ssl=node_data['use_ssl'],
                node_name=node_data['name']
            )
        
        # Store node config for later use
        wizard.node_config = node_config
        
        # Generate unique wallet name
        wallet_name = f"shop_wallet_{int(time.time())}"
        
        # Start wallet creation in background
        self.worker = WalletCreationWorker(wallet_name, wallet_password, node_config)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()
    
    def _on_progress(self, value, message):
        """Update progress"""
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
    
    def _on_finished(self, success, wallet_path, result):
        """Handle wallet creation completion"""
        if success:
            self.wallet_path = wallet_path
            self.seed_phrase = result
            self.wizard().wallet_path = wallet_path
            self.wizard().seed_phrase = result
            self.wizard().next()
        else:
            QMessageBox.critical(
                self,
                "Wallet Creation Failed",
                f"Failed to create wallet:\n{result}\n\nPlease try again."
            )
            self.wizard().back()


class SeedPhrasePage(QWizardPage):
    """Seed phrase display and backup page"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("BACKUP YOUR SEED PHRASE")
        self.setSubTitle("Write down these 25 words in order - this is your wallet backup!")
        
        layout = QVBoxLayout()
        
        # Warning message
        warning = QLabel(
            "🔴 CRITICAL: Your seed phrase is the ONLY way to recover your wallet!\n\n"
            "• Write these 25 words on paper in the correct order\n"
            "• Store it in a safe place (fireproof safe recommended)\n"
            "• NEVER share it with anyone - it gives full access to your funds\n"
            "• NEVER store it digitally (no photos, no cloud storage)\n"
            "• If you lose both your password AND seed phrase, your funds are GONE FOREVER"
        )
        warning.setWordWrap(True)
        warning.setStyleSheet(
            "background-color: #d9534f; color: white; padding: 15px; "
            "font-weight: bold; border-radius: 5px;"
        )
        layout.addWidget(warning)
        
        # Seed phrase display in grid
        seed_group = QGroupBox("Your 25-Word Seed Phrase")
        seed_layout = QGridLayout()
        
        self.seed_labels = []
        for i in range(25):
            row = i // 5
            col = i % 5
            word_label = QLabel(f"{i+1}. ")
            word_label.setStyleSheet("font-weight: bold;")
            word_value = QLabel("")
            word_value.setStyleSheet("font-family: monospace; font-size: 11pt; background-color: #f5f5f5; padding: 5px;")
            seed_layout.addWidget(word_label, row, col*2)
            seed_layout.addWidget(word_value, row, col*2+1)
            self.seed_labels.append(word_value)
        
        seed_group.setLayout(seed_layout)
        layout.addWidget(seed_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.copy_btn = QPushButton("📋 Copy to Clipboard")
        self.copy_btn.clicked.connect(self._copy_seed)
        button_layout.addWidget(self.copy_btn)
        
        self.save_btn = QPushButton("💾 Save to File")
        self.save_btn.clicked.connect(self._save_seed)
        button_layout.addWidget(self.save_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Confirmation checkbox
        self.confirm_label = QLabel(
            "\n✅ I have written down my seed phrase and stored it safely"
        )
        self.confirm_label.setStyleSheet("font-weight: bold; color: #5cb85c;")
        layout.addWidget(self.confirm_label)
        
        self.setLayout(layout)
        
        self.seed_confirmed = False
    
    def initializePage(self):
        """Display seed phrase when page is shown"""
        seed_phrase = self.wizard().seed_phrase
        words = seed_phrase.split()
        
        for i, word in enumerate(words[:25]):
            if i < len(self.seed_labels):
                self.seed_labels[i].setText(word)
    
    def _copy_seed(self):
        """Copy seed phrase to clipboard"""
        seed_phrase = self.wizard().seed_phrase
        QApplication.clipboard().setText(seed_phrase)
        QMessageBox.warning(
            self,
            "Copied to Clipboard",
            "⚠️ Seed phrase copied to clipboard!\n\n"
            "Remember: Paste it into a text file and print it immediately.\n"
            "Do NOT leave it on your clipboard or in a digital file!"
        )
        self.seed_confirmed = True
    
    def _save_seed(self):
        """Save seed phrase to file"""
        seed_phrase = self.wizard().seed_phrase
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Seed Phrase",
            os.path.expanduser("~/Desktop/monero_seed_phrase.txt"),
            "Text Files (*.txt)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write("MONERO WALLET SEED PHRASE\n")
                    f.write("=" * 50 + "\n\n")
                    f.write("KEEP THIS SAFE AND SECRET!\n\n")
                    f.write(seed_phrase + "\n\n")
                    f.write("=" * 50 + "\n")
                    f.write(f"Wallet: {self.wizard().wallet_path}\n")
                    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                
                QMessageBox.warning(
                    self,
                    "Seed Phrase Saved",
                    f"⚠️ Seed phrase saved to:\n{file_path}\n\n"
                    "Remember to:\n"
                    "• Print this file immediately\n"
                    "• Delete the digital file after printing\n"
                    "• Store the printed copy in a safe place"
                )
                self.seed_confirmed = True
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file:\n{e}")
    
    def validatePage(self):
        """Ensure user has acknowledged seed phrase"""
        if not self.seed_confirmed:
            reply = QMessageBox.question(
                self,
                "Seed Phrase Backup",
                "Have you written down your 25-word seed phrase?\n\n"
                "Without it, you cannot recover your wallet if you lose your password!",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return False
            self.seed_confirmed = True
        
        return True


class SeedVerificationPage(QWizardPage):
    """Seed phrase verification page"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Verify Your Seed Phrase")
        self.setSubTitle("Confirm you wrote it down correctly by entering 3 random words")
        
        layout = QVBoxLayout()
        
        info_label = QLabel(
            "To ensure you have correctly backed up your seed phrase,\n"
            "please enter the following words from your seed:"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Verification inputs
        self.verification_inputs = []
        self.verification_positions = []
        
        for i in range(3):
            word_layout = QHBoxLayout()
            label = QLabel(f"Word #:")
            label.setMinimumWidth(80)
            word_input = QLineEdit()
            word_input.setPlaceholderText("Enter word")
            word_layout.addWidget(label)
            word_layout.addWidget(word_input)
            layout.addLayout(word_layout)
            self.verification_inputs.append((label, word_input))
        
        layout.addStretch()
        self.setLayout(layout)
    
    def initializePage(self):
        """Select 3 random words to verify"""
        # Select 3 random positions (1-25)
        self.verification_positions = random.sample(range(1, 26), 3)
        self.verification_positions.sort()
        
        # Update labels
        for i, (label, input_field) in enumerate(self.verification_inputs):
            pos = self.verification_positions[i]
            label.setText(f"Word #{pos}:")
            input_field.clear()
    
    def validatePage(self):
        """Verify the entered words"""
        seed_phrase = self.wizard().seed_phrase
        words = seed_phrase.split()
        
        for i, (label, input_field) in enumerate(self.verification_inputs):
            pos = self.verification_positions[i]
            expected_word = words[pos - 1].lower().strip()
            entered_word = input_field.text().lower().strip()
            
            if entered_word != expected_word:
                QMessageBox.warning(
                    self,
                    "Verification Failed",
                    f"Word #{pos} is incorrect.\n\n"
                    f"Please check your written seed phrase and try again."
                )
                return False
        
        QMessageBox.information(
            self,
            "Verification Successful",
            "✅ Seed phrase verified successfully!\n\n"
            "Your backup is correct."
        )
        
        return True


class WalletSummaryPage(QWizardPage):
    """Wallet summary and sync status page"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Wallet Created Successfully")
        self.setSubTitle("Your Monero wallet is ready to use!")
        
        layout = QVBoxLayout()
        
        # Success message
        success_label = QLabel(
            "✅ Your in-house Monero wallet has been created successfully!"
        )
        success_label.setStyleSheet("color: #5cb85c; font-size: 12pt; font-weight: bold;")
        layout.addWidget(success_label)
        
        # Wallet info group
        info_group = QGroupBox("Wallet Information")
        info_layout = QVBoxLayout()
        
        self.wallet_path_label = QLabel("Wallet Path: ")
        self.wallet_address_label = QLabel("Primary Address: Loading...")
        self.node_label = QLabel("Connected Node: ")
        
        info_layout.addWidget(self.wallet_path_label)
        info_layout.addWidget(self.wallet_address_label)
        info_layout.addWidget(self.node_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Sync status
        sync_group = QGroupBox("Sync Status")
        sync_layout = QVBoxLayout()
        
        self.sync_label = QLabel("Wallet will sync in the background after setup completes.")
        self.sync_label.setWordWrap(True)
        sync_layout.addWidget(self.sync_label)
        
        sync_group.setLayout(sync_layout)
        layout.addWidget(sync_group)
        
        # Important notes
        notes = QLabel(
            "\n📌 Important Notes:\n"
            "• Your wallet is now ready to receive payments\n"
            "• Keep your seed phrase safe - it's your only backup\n"
            "• The wallet will sync with the blockchain after setup\n"
            "• You can start adding products immediately"
        )
        notes.setWordWrap(True)
        layout.addWidget(notes)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def initializePage(self):
        """Display wallet information"""
        wallet_path = self.wizard().wallet_path
        node_config = self.wizard().node_config
        
        self.wallet_path_label.setText(f"Wallet Path: {wallet_path}")
        self.node_label.setText(f"Connected Node: {node_config.node_name}")
        
        # Try to get wallet address
        try:
            wallet = InHouseWallet(
                wallet_path=wallet_path,
                password=self.wizard().field("wallet_password"),
                daemon_address=node_config.address,
                daemon_port=node_config.port,
                use_ssl=node_config.use_ssl
            )
            address = wallet.get_address()
            if address:
                self.wallet_address_label.setText(f"Primary Address: {address[:20]}...{address[-20:]}")
            else:
                self.wallet_address_label.setText("Primary Address: Available after sync")
        except Exception as e:
            self.wallet_address_label.setText(f"Primary Address: Available after sync")


class CurrencyPage(QWizardPage):
    """Currency selection page"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Default Currency")
        self.setSubTitle("Choose your default pricing currency")
        
        layout = QVBoxLayout()
        
        label = QLabel("Select default currency for product pricing:")
        layout.addWidget(label)
        
        self.currency_combo = QComboBox()
        self.currency_combo.addItems(SUPPORTED_CURRENCIES)
        layout.addWidget(self.currency_combo)
        
        info = QLabel(
            "\nPrices will be shown in this currency and automatically "
            "converted to XMR at checkout time using real-time exchange rates."
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        
        layout.addStretch()
        self.setLayout(layout)
        
        self.registerField("currency", self.currency_combo, "currentText")


class SetupWizard(QWizard):
    """Main setup wizard with in-house wallet creation"""
    
    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        
        self.db_manager = db_manager
        self.seller_manager = SellerManager(db_manager)
        self.node_manager = NodeManager(db_manager)
        
        self.setWindowTitle("Signal Shop Bot - Setup Wizard")
        self.setWizardStyle(QWizard.ModernStyle)
        self.setMinimumSize(900, 750)
        
        # Store created wallet info
        self.wallet_path = None
        self.seed_phrase = None
        self.node_config = None
        
        # Track page IDs for custom navigation
        self.page_ids = {}
        
        # Add pages
        welcome_id = self.addPage(WelcomePage())
        self.page_ids['welcome'] = welcome_id
        
        pin_id = self.addPage(PINPage())
        self.page_ids['pin'] = pin_id
        
        signal_id = self.addPage(SignalPage())
        self.page_ids['signal'] = signal_id
        
        node_config_id = self.addPage(NodeConfigPage())
        self.page_ids['node_config'] = node_config_id
        
        custom_node_id = self.addPage(CustomNodePage())
        self.page_ids['custom_node'] = custom_node_id
        
        wallet_password_id = self.addPage(WalletPasswordPage())
        self.page_ids['wallet_password'] = wallet_password_id
        
        wallet_creation_id = self.addPage(WalletCreationPage())
        self.page_ids['wallet_creation'] = wallet_creation_id
        
        seed_phrase_id = self.addPage(SeedPhrasePage())
        self.page_ids['seed_phrase'] = seed_phrase_id
        
        seed_verification_id = self.addPage(SeedVerificationPage())
        self.page_ids['seed_verification'] = seed_verification_id
        
        wallet_summary_id = self.addPage(WalletSummaryPage())
        self.page_ids['wallet_summary'] = wallet_summary_id
        
        currency_id = self.addPage(CurrencyPage())
        self.page_ids['currency'] = currency_id
        
        # Connect finish button
        self.button(QWizard.FinishButton).clicked.connect(self.save_configuration)
    
    def save_configuration(self):
        """Save configuration to database"""
        try:
            # Get values
            pin = self.field("pin")
            signal_phone = self.field("signal_phone")
            currency = self.field("currency")
            
            if not self.wallet_path or not self.node_config:
                raise ValueError("Wallet or node configuration not found")
            
            # Save node configuration
            try:
                self.node_manager.add_node(self.node_config)
            except Exception as e:
                print(f"Note: Node may already exist: {e}")
            
            # Create seller with wallet_path only
            seller = Seller(
                signal_id=signal_phone,
                wallet_path=self.wallet_path,
                default_currency=currency
            )
            
            self.seller_manager.create_seller(seller, pin)
            
            QMessageBox.information(
                self,
                "Setup Complete",
                "✅ Your shop is now configured!\n\n"
                "Your in-house Monero wallet has been created and is ready to use.\n"
                "You can now start adding products to your shop.\n\n"
                f"Wallet Location: {self.wallet_path}\n"
                f"Connected Node: {self.node_config.node_name}\n\n"
                "⚠️ Remember: Keep your seed phrase safe!"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Setup Failed",
                f"Failed to save configuration:\n{e}\n\n"
                "Please try running the wizard again."
            )
