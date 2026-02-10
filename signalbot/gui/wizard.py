"""
Setup Wizard for Signal Shop Bot
Guides seller through initial configuration
"""

import sys
from typing import Optional, Dict
from PyQt5.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QRadioButton, QButtonGroup,
    QTextEdit, QMessageBox, QComboBox, QFileDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QFont

from ..core.security import security_manager
from ..core.signal_handler import SignalHandler
from ..core.monero_wallet import MoneroWallet, MoneroWalletFactory
from ..utils.qr_generator import qr_generator
from ..models.seller import Seller, SellerManager
from ..database.db import DatabaseManager
from ..config.settings import SUPPORTED_CURRENCIES


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
            "This bot charges a 4% commission on all sales.\n"
            "For every sale, 96% goes to you and 4% goes to the bot creator.\n"
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
        from PyQt5.QtWidgets import QApplication
        link = self.link_text.toPlainText()
        if link:
            QApplication.clipboard().setText(link)
            QMessageBox.information(self, "Copied", "Link copied to clipboard!")


class WalletPage(QWizardPage):
    """Monero wallet configuration page"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Configure Monero Wallet")
        self.setSubTitle("Choose how to connect your Monero wallet")
        
        layout = QVBoxLayout()
        
        # Wallet mode selection
        mode_label = QLabel("Select wallet setup mode:")
        mode_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(mode_label)
        
        self.mode_group = QButtonGroup()
        self.simple_radio = QRadioButton("Simple Setup (Recommended) - View-Only Wallet")
        self.advanced_radio = QRadioButton("Advanced Setup - RPC Wallet Connection")
        self.simple_radio.setChecked(True)
        
        self.mode_group.addButton(self.simple_radio, 1)
        self.mode_group.addButton(self.advanced_radio, 2)
        
        layout.addWidget(self.simple_radio)
        layout.addWidget(self.advanced_radio)
        
        # Simple mode section
        self.simple_group = QGroupBox("Simple Setup - View Only Wallet")
        simple_layout = QVBoxLayout()
        
        info_label = QLabel(
            "Just enter your Monero wallet address below.\n"
            "This is the easiest option and works for most users.\n\n"
            "⚠️ Note: You'll receive payment notifications, but won't be able to\n"
            "send transactions from this app (send from your main wallet instead)."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-size: 9pt;")
        simple_layout.addWidget(info_label)
        
        self.wallet_address = QLineEdit()
        self.wallet_address.setPlaceholderText("45WQHqFEXu...")
        simple_layout.addWidget(QLabel("Your Monero Wallet Address*:"))
        simple_layout.addWidget(self.wallet_address)
        
        note_label = QLabel(
            "That's it! No private keys needed for simple mode.\n"
            "The app will monitor incoming payments to this address."
        )
        note_label.setWordWrap(True)
        note_label.setStyleSheet("color: green; font-size: 9pt; font-style: italic;")
        simple_layout.addWidget(note_label)
        
        self.simple_group.setLayout(simple_layout)
        layout.addWidget(self.simple_group)
        
        # Advanced mode section (RPC configuration)
        self.advanced_group = QGroupBox("Advanced Setup")
        advanced_layout = QVBoxLayout()
        
        adv_info_label = QLabel(
            "Connect to an existing monero-wallet-rpc instance.\n"
            "Ensure your wallet-RPC is running before testing connection."
        )
        adv_info_label.setWordWrap(True)
        adv_info_label.setStyleSheet("color: #666; font-size: 9pt;")
        advanced_layout.addWidget(adv_info_label)
        
        self.rpc_host = QLineEdit()
        self.rpc_host.setPlaceholderText("127.0.0.1")
        advanced_layout.addWidget(QLabel("RPC Host:"))
        advanced_layout.addWidget(self.rpc_host)
        
        self.rpc_port = QLineEdit()
        self.rpc_port.setPlaceholderText("18083")
        advanced_layout.addWidget(QLabel("RPC Port:"))
        advanced_layout.addWidget(self.rpc_port)
        
        self.rpc_user = QLineEdit()
        self.rpc_user.setPlaceholderText("(optional)")
        advanced_layout.addWidget(QLabel("RPC Username:"))
        advanced_layout.addWidget(self.rpc_user)
        
        self.rpc_password = QLineEdit()
        self.rpc_password.setEchoMode(QLineEdit.Password)
        self.rpc_password.setPlaceholderText("(optional)")
        advanced_layout.addWidget(QLabel("RPC Password:"))
        advanced_layout.addWidget(self.rpc_password)
        
        self.advanced_group.setLayout(advanced_layout)
        self.advanced_group.setVisible(False)
        layout.addWidget(self.advanced_group)
        
        # Test connection button
        self.test_btn = QPushButton("Test Connection")
        self.test_btn.clicked.connect(self.test_connection)
        layout.addWidget(self.test_btn)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # Connect mode switching
        self.simple_radio.toggled.connect(self._toggle_mode)
        
        # Register fields
        self.registerField("wallet_mode", self.simple_radio)
        self.registerField("wallet_address", self.wallet_address)
        self.registerField("rpc_host", self.rpc_host)
        self.registerField("rpc_port", self.rpc_port)
    
    def _toggle_mode(self, checked):
        """Toggle between simple and advanced mode"""
        if checked:
            self.simple_group.setVisible(True)
            self.advanced_group.setVisible(False)
        else:
            self.simple_group.setVisible(False)
            self.advanced_group.setVisible(True)
    
    def test_connection(self):
        """Test wallet connection"""
        try:
            if self.simple_radio.isChecked():
                # Validate simple mode inputs
                address = self.wallet_address.text().strip()
                
                if not address:
                    QMessageBox.warning(self, "Validation Error", "Please enter your wallet address")
                    return
                
                # Basic address validation (Monero addresses are 95 or 106 characters)
                if len(address) < 90:
                    QMessageBox.warning(self, "Invalid Address", "Please enter a valid Monero wallet address")
                    return
                
                QMessageBox.information(
                    self, 
                    "Valid Address", 
                    "Wallet address format looks good!\n\n"
                    "In Simple Mode, the app will monitor incoming payments\n"
                    "to this address. You can send payments from your main wallet."
                )
            else:
                # Test RPC connection
                wallet = MoneroWallet(
                    wallet_type='rpc',
                    rpc_host=self.rpc_host.text() or '127.0.0.1',
                    rpc_port=int(self.rpc_port.text() or '18083'),
                    rpc_user=self.rpc_user.text() or None,
                    rpc_password=self.rpc_password.text() or None
                )
                
                if wallet.test_connection():
                    QMessageBox.information(self, "Success", "Wallet connection successful!")
                else:
                    QMessageBox.warning(self, "Failed", "Could not connect to wallet")
                    
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Connection failed: {e}")


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
    """Main setup wizard"""
    
    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        
        self.db_manager = db_manager
        self.seller_manager = SellerManager(db_manager)
        
        self.setWindowTitle("Signal Shop Bot - Setup Wizard")
        self.setWizardStyle(QWizard.ModernStyle)
        self.setMinimumSize(800, 700)
        
        # Add pages
        self.addPage(WelcomePage())
        self.addPage(PINPage())
        self.addPage(SignalPage())
        self.addPage(WalletPage())
        self.addPage(CurrencyPage())
        
        # Connect finish button
        self.button(QWizard.FinishButton).clicked.connect(self.save_configuration)
    
    def save_configuration(self):
        """Save configuration to database"""
        try:
            # Get values
            pin = self.field("pin")
            signal_phone = self.field("signal_phone")
            currency = self.field("currency")
            
            # Get wallet configuration based on mode
            is_simple_mode = self.field("wallet_mode")
            
            if is_simple_mode:
                # Simple mode: view-only wallet
                wallet_address = self.field("wallet_address")
                view_key = self.field("view_key")
                auto_start = self.field("auto_start_rpc")
                
                wallet_config = {
                    'type': 'view_only',
                    'address': wallet_address,
                    'view_key': view_key,
                    'auto_start_rpc': auto_start
                }
            else:
                # Advanced mode: RPC wallet
                wallet_config = {
                    'type': 'rpc',
                    'rpc_host': self.field("rpc_host") or '127.0.0.1',
                    'rpc_port': int(self.field("rpc_port") or 18083),
                    'rpc_user': None,  # Would get from form
                    'rpc_password': None  # Would get from form
                }
            
            # Create seller
            seller = Seller(
                signal_id=signal_phone,
                wallet_type='view_only' if is_simple_mode else 'rpc',
                wallet_config=wallet_config,
                default_currency=currency
            )
            
            self.seller_manager.create_seller(seller, pin)
            
            QMessageBox.information(
                self,
                "Setup Complete",
                "Your shop is now configured! You can now start adding products."
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Setup Failed",
                f"Failed to save configuration: {e}"
            )
