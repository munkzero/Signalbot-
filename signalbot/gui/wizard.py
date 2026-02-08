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
        
        # QR code display
        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.qr_label)
        
        # Phone number input (alternative)
        phone_label = QLabel("\nOr enter your Signal phone number:")
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("+1234567890")
        
        layout.addWidget(phone_label)
        layout.addWidget(self.phone_input)
        layout.addStretch()
        
        self.setLayout(layout)
        
        self.registerField("signal_phone", self.phone_input)
    
    def generate_qr(self):
        """Generate QR code for linking"""
        try:
            # In actual implementation, would use signal-cli to generate link
            # For now, show placeholder
            link_data = "tsdevice:/?uuid=placeholder&pub_key=placeholder"
            qr_data = qr_generator.generate_simple_qr(link_data)
            
            pixmap = QPixmap()
            pixmap.loadFromData(qr_data)
            self.qr_label.setPixmap(pixmap.scaled(300, 300, Qt.KeepAspectRatio))
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to generate QR code: {e}")


class WalletPage(QWizardPage):
    """Monero wallet configuration page"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Configure Monero Wallet")
        self.setSubTitle("Choose how to connect your Monero wallet")
        
        layout = QVBoxLayout()
        
        # Wallet type selection
        type_label = QLabel("Select wallet type:")
        layout.addWidget(type_label)
        
        self.type_group = QButtonGroup()
        self.rpc_radio = QRadioButton("RPC Wallet (remote)")
        self.file_radio = QRadioButton("Wallet File (local)")
        self.rpc_radio.setChecked(True)
        
        self.type_group.addButton(self.rpc_radio, 1)
        self.type_group.addButton(self.file_radio, 2)
        
        layout.addWidget(self.rpc_radio)
        layout.addWidget(self.file_radio)
        
        # RPC configuration
        self.rpc_host = QLineEdit()
        self.rpc_host.setPlaceholderText("127.0.0.1")
        
        self.rpc_port = QLineEdit()
        self.rpc_port.setPlaceholderText("18083")
        
        self.rpc_user = QLineEdit()
        self.rpc_user.setPlaceholderText("(optional)")
        
        self.rpc_password = QLineEdit()
        self.rpc_password.setEchoMode(QLineEdit.Password)
        self.rpc_password.setPlaceholderText("(optional)")
        
        rpc_layout = QVBoxLayout()
        rpc_layout.addWidget(QLabel("RPC Host:"))
        rpc_layout.addWidget(self.rpc_host)
        rpc_layout.addWidget(QLabel("RPC Port:"))
        rpc_layout.addWidget(self.rpc_port)
        rpc_layout.addWidget(QLabel("RPC Username:"))
        rpc_layout.addWidget(self.rpc_user)
        rpc_layout.addWidget(QLabel("RPC Password:"))
        rpc_layout.addWidget(self.rpc_password)
        
        layout.addLayout(rpc_layout)
        
        # Test connection button
        self.test_btn = QPushButton("Test Connection")
        self.test_btn.clicked.connect(self.test_connection)
        layout.addWidget(self.test_btn)
        
        layout.addStretch()
        self.setLayout(layout)
        
        self.registerField("wallet_type", self.rpc_radio)
        self.registerField("rpc_host", self.rpc_host)
        self.registerField("rpc_port", self.rpc_port)
    
    def test_connection(self):
        """Test wallet connection"""
        try:
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
        self.setMinimumSize(600, 500)
        
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
            
            # Create wallet config
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
                wallet_type='rpc',
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
