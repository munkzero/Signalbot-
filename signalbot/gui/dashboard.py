"""
Main seller dashboard GUI
"""

import sys
import os
import time
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QMessageBox, QLineEdit, QDialog,
    QDialogButtonBox, QFormLayout, QTextEdit, QListWidget,
    QSplitter, QFileDialog, QCheckBox, QDoubleSpinBox,
    QSpinBox, QComboBox, QScrollArea, QRadioButton,
    QButtonGroup, QGroupBox, QGridLayout, QListWidgetItem,
    QMenu, QAction, QApplication, QProgressDialog, QProgressBar,
    QFrame, QInputDialog
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QPixmap, QCursor, QColor, QIcon
from datetime import datetime
from typing import Optional

from ..database.db import DatabaseManager
from ..models.seller import SellerManager
from ..models.product import ProductManager, Product
from ..models.order import OrderManager, Order
from ..models.contact import ContactManager
from ..models.message import MessageManager
from ..config.settings import (
    WINDOW_TITLE, WINDOW_WIDTH, WINDOW_HEIGHT,
    SUPPORTED_CURRENCIES, MAX_IMAGE_SIZE, IMAGES_DIR,
    ORDER_EXPIRATION_MINUTES, LOW_STOCK_THRESHOLD,
    MONERO_CONFIRMATIONS_REQUIRED, COMMISSION_RATE,
    MESSAGE_SEND_DELAY_SECONDS
)
from ..core.signal_handler import SignalHandler
from ..utils.image_tools import image_processor
from ..core.monero_wallet import InHouseWallet
from ..models.node import NodeManager, MoneroNodeConfig


# Common image directories to search for product images
COMMON_IMAGE_SEARCH_DIRS = [
    'data/products/images',
    'data/images',
    'data/product_images',
    'images',
    '.',
]


class PINDialog(QDialog):
    """Dialog for PIN entry"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enter PIN")
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        label = QLabel("Enter your PIN to access the dashboard:")
        self.pin_input = QLineEdit()
        self.pin_input.setEchoMode(QLineEdit.Password)
        self.pin_input.setMaxLength(20)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        layout.addWidget(label)
        layout.addWidget(self.pin_input)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def get_pin(self):
        return self.pin_input.text()


class WalletPasswordDialog(QDialog):
    """Dialog for wallet password entry"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enter Wallet Password")
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        label = QLabel("Enter your wallet password:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        layout.addWidget(label)
        layout.addWidget(self.password_input)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def get_password(self):
        password = self.password_input.text()
        self.password_input.clear()
        return password



class AddProductDialog(QDialog):
    """Dialog for adding/editing products"""
    
    def __init__(self, product_manager: ProductManager, product: Optional[Product] = None, parent=None):
        super().__init__(parent)
        self.product_manager = product_manager
        self.product = product
        self.image_path = product.image_path if product else None
        
        self.setWindowTitle("Edit Product" if product else "Add Product")
        self.setModal(True)
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        
        # Product Name
        self.name_input = QLineEdit()
        if product:
            self.name_input.setText(product.name)
        form_layout.addRow("Product Name*:", self.name_input)
        
        # Product ID
        self.product_id_input = QLineEdit()
        self.product_id_input.setPlaceholderText("#1, SKU-001, LAP-123, etc.")
        if product and product.product_id:
            self.product_id_input.setText(product.product_id)
        else:
            # Auto-suggest next ID for new products
            next_id = self._get_next_product_id()
            self.product_id_input.setText(f"#{next_id}")
        form_layout.addRow("Product ID*:", self.product_id_input)
        
        # Description
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(100)
        if product:
            self.description_input.setPlainText(product.description)
        form_layout.addRow("Description:", self.description_input)
        
        # Price
        price_layout = QHBoxLayout()
        self.price_input = QDoubleSpinBox()
        self.price_input.setRange(0.01, 999999.99)
        self.price_input.setDecimals(2)
        self.price_input.setSingleStep(1.0)
        if product:
            self.price_input.setValue(product.price)
        
        self.currency_combo = QComboBox()
        self.currency_combo.addItems(SUPPORTED_CURRENCIES)
        if product:
            index = self.currency_combo.findText(product.currency)
            if index >= 0:
                self.currency_combo.setCurrentIndex(index)
        
        price_layout.addWidget(self.price_input)
        price_layout.addWidget(self.currency_combo)
        form_layout.addRow("Price*:", price_layout)
        
        # Stock
        self.stock_input = QSpinBox()
        self.stock_input.setRange(0, 999999)
        if product:
            self.stock_input.setValue(product.stock)
        form_layout.addRow("Stock Quantity*:", self.stock_input)
        
        # Category
        self.category_input = QLineEdit()
        if product:
            self.category_input.setText(product.category or "")
        form_layout.addRow("Category:", self.category_input)
        
        # Active checkbox
        self.active_checkbox = QCheckBox("Active")
        self.active_checkbox.setChecked(product.active if product else True)
        form_layout.addRow("Status:", self.active_checkbox)
        
        layout.addLayout(form_layout)
        
        # Image section
        image_group = QGroupBox("Product Image")
        image_layout = QVBoxLayout()
        
        self.image_label = QLabel("No image selected")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumHeight(150)
        self.image_label.setStyleSheet("border: 1px solid #ccc; background: #f5f5f5;")
        
        if product and product.image_path:
            self._load_image_preview(os.path.join(IMAGES_DIR, product.image_path))
        
        image_layout.addWidget(self.image_label)
        
        browse_btn = QPushButton("Browse Image...")
        browse_btn.clicked.connect(self.browse_image)
        image_layout.addWidget(browse_btn)
        
        image_group.setLayout(image_layout)
        layout.addWidget(image_group)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.save_product)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def browse_image(self):
        """Open file dialog to select image"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Product Image",
            "",
            "Image Files (*.png *.jpg *.jpeg)"
        )
        
        if file_path:
            # Validate file size
            file_size = os.path.getsize(file_path)
            if file_size > MAX_IMAGE_SIZE:
                QMessageBox.warning(
                    self,
                    "File Too Large",
                    f"Image is too large ({file_size / (1024*1024):.1f} MB). Maximum size is {MAX_IMAGE_SIZE / (1024*1024):.0f} MB."
                )
                return
            
            self.image_path = file_path
            self._load_image_preview(file_path)
    
    def _load_image_preview(self, path: str):
        """Load and display image preview"""
        try:
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(200, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled_pixmap)
                self.image_label.setText("")
            else:
                self.image_label.setText("Failed to load image")
        except Exception as e:
            self.image_label.setText(f"Error: {str(e)}")
    
    def _get_next_product_id(self):
        """Auto-suggest next available numeric ID"""
        products = self.product_manager.list_products(active_only=False)
        numeric_ids = []
        for p in products:
            if p.product_id:
                try:
                    # Extract number from IDs like "#1", "#2", etc.
                    if p.product_id.startswith('#'):
                        num = int(p.product_id[1:])
                        numeric_ids.append(num)
                except (ValueError, AttributeError):
                    pass
        
        if numeric_ids:
            return max(numeric_ids) + 1
        return 1
    
    def _is_duplicate_id(self, product_id: str) -> bool:
        """Check if product ID already exists"""
        # Skip check if editing and ID hasn't changed
        if self.product and self.product.product_id == product_id:
            return False
        
        existing = self.product_manager.get_product_by_product_id(product_id)
        return existing is not None
    
    def save_product(self):
        """Validate and save product"""
        # Validate required fields
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Product name is required")
            return
        
        product_id = self.product_id_input.text().strip()
        if not product_id:
            QMessageBox.warning(self, "Validation Error", "Product ID is required")
            return
        
        # Check for duplicate ID
        if self._is_duplicate_id(product_id):
            QMessageBox.warning(
                self, 
                "Duplicate ID", 
                f"Product ID '{product_id}' already exists. Choose another."
            )
            return
        
        price = self.price_input.value()
        if price <= 0:
            QMessageBox.warning(self, "Validation Error", "Price must be greater than 0")
            return
        
        # Create or update product
        if self.product:
            # Update existing
            self.product.product_id = product_id
            self.product.name = name
            self.product.description = self.description_input.toPlainText().strip()
            self.product.price = price
            self.product.currency = self.currency_combo.currentText()
            self.product.stock = self.stock_input.value()
            self.product.category = self.category_input.text().strip() or None
            self.product.active = self.active_checkbox.isChecked()
            
            # Process image if changed
            if self.image_path and not self.image_path.startswith(str(IMAGES_DIR)):
                try:
                    processed_image = image_processor.process_product_image(
                        self.image_path,
                        self.product.id
                    )
                    self.product.image_path = processed_image
                except Exception as e:
                    QMessageBox.warning(self, "Image Error", f"Failed to process image: {e}")
                    return
            
            try:
                self.product_manager.update_product(self.product)
                QMessageBox.information(self, "Success", "Product updated successfully!")
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update product: {e}")
        else:
            # Create new
            new_product = Product(
                product_id=product_id,
                name=name,
                description=self.description_input.toPlainText().strip(),
                price=price,
                currency=self.currency_combo.currentText(),
                stock=self.stock_input.value(),
                category=self.category_input.text().strip() or None,
                active=self.active_checkbox.isChecked()
            )
            
            try:
                # Save to get ID first
                created_product = self.product_manager.create_product(new_product)
                
                # Process image if provided
                if self.image_path:
                    try:
                        processed_image = image_processor.process_product_image(
                            self.image_path,
                            created_product.id
                        )
                        created_product.image_path = processed_image
                        self.product_manager.update_product(created_product)
                    except Exception as e:
                        QMessageBox.warning(self, "Image Warning", f"Product saved but image processing failed: {e}")
                
                QMessageBox.information(self, "Success", "Product added successfully!")
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create product: {e}")


class ComposeMessageDialog(QDialog):
    """Dialog for composing new messages"""
    
    def __init__(self, signal_handler: SignalHandler, message_manager=None, contact_manager=None, my_signal_id=None, parent=None):
        super().__init__(parent)
        self.signal_handler = signal_handler
        self.message_manager = message_manager
        self.contact_manager = contact_manager
        self.my_signal_id = my_signal_id
        
        self.setWindowTitle("Compose Message")
        self.setModal(True)
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout()
        
        # Recipient type selection
        type_group = QGroupBox("Recipient Type")
        type_layout = QVBoxLayout()
        
        self.type_group = QButtonGroup()
        self.contact_radio = QRadioButton("Contact (Phone/Username)")
        self.group_radio = QRadioButton("Group")
        self.contact_radio.setChecked(True)
        
        self.type_group.addButton(self.contact_radio, 1)
        self.type_group.addButton(self.group_radio, 2)
        
        type_layout.addWidget(self.contact_radio)
        type_layout.addWidget(self.group_radio)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        # Contact input
        self.contact_input = QLineEdit()
        self.contact_input.setPlaceholderText("Phone number (+1234567890) or username (user.123)")
        layout.addWidget(QLabel("Contact:"))
        layout.addWidget(self.contact_input)
        
        # Group selection
        self.group_combo = QComboBox()
        self.group_combo.setEnabled(False)
        layout.addWidget(QLabel("Group:"))
        layout.addWidget(self.group_combo)
        
        # Load groups
        self._load_groups()
        
        # Connect radio buttons
        self.contact_radio.toggled.connect(self._toggle_recipient_type)
        
        # Message text
        layout.addWidget(QLabel("Message:"))
        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("Type your message here...")
        layout.addWidget(self.message_input)
        
        # Quick actions
        quick_layout = QHBoxLayout()
        attach_btn = QPushButton("Attach Image")
        attach_btn.clicked.connect(self.attach_image)
        quick_layout.addWidget(attach_btn)
        quick_layout.addStretch()
        layout.addLayout(quick_layout)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.send_message)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
        
        self.attachment_path = None
    
    def _load_groups(self):
        """Load available groups"""
        try:
            groups = self.signal_handler.list_groups()
            for group in groups:
                self.group_combo.addItem(group.get('name', 'Unknown'), group.get('id'))
        except Exception as e:
            print(f"Failed to load groups: {e}")
    
    def _toggle_recipient_type(self, checked):
        """Toggle between contact and group input"""
        if checked:
            self.contact_input.setEnabled(True)
            self.group_combo.setEnabled(False)
        else:
            self.contact_input.setEnabled(False)
            self.group_combo.setEnabled(True)
    
    def attach_image(self):
        """Select image to attach"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            "",
            "Image Files (*.png *.jpg *.jpeg)"
        )
        
        if file_path:
            self.attachment_path = file_path
            QMessageBox.information(self, "Image Selected", f"Image attached: {os.path.basename(file_path)}")
    
    def send_message(self):
        """Send the message"""
        message = self.message_input.toPlainText().strip()
        if not message:
            QMessageBox.warning(self, "Validation Error", "Message cannot be empty")
            return
        
        # Get recipient
        if self.contact_radio.isChecked():
            recipient = self.contact_input.text().strip()
            if not recipient:
                QMessageBox.warning(self, "Validation Error", "Please enter a contact")
                return
        else:
            if self.group_combo.currentIndex() < 0:
                QMessageBox.warning(self, "Validation Error", "Please select a group")
                return
            recipient = self.group_combo.currentData()
        
        # Send message
        try:
            attachments = [self.attachment_path] if self.attachment_path else None
            success = self.signal_handler.send_message(recipient, message, attachments)
            
            if success:
                # Save outgoing message to database
                if self.my_signal_id and self.message_manager:
                    try:
                        self.message_manager.add_message(
                            sender_signal_id=self.my_signal_id,
                            recipient_signal_id=recipient,
                            message_body=message,
                            is_outgoing=True
                        )
                        
                        # Create or update contact
                        if self.contact_manager:
                            self.contact_manager.get_or_create_contact(
                                signal_id=recipient,
                                name=recipient  # Default to signal_id as name
                            )
                    except Exception as e:
                        print(f"Error saving message to database: {e}")
                
                QMessageBox.information(self, "Success", "Message sent successfully!")
                self.accept()
            else:
                QMessageBox.warning(self, "Send Failed", "Failed to send message. Check Signal configuration.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to send message: {e}")


class ProductPickerDialog(QDialog):
    """Dialog for selecting products to send to buyer"""
    
    def __init__(self, product_manager, parent=None):
        super().__init__(parent)
        self.product_manager = product_manager
        self.selected_products = []
        
        self.setWindowTitle("Select Products to Send")
        self.setModal(True)
        self.setMinimumSize(700, 500)
        
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel("Select one or more products to send to the buyer:")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Product list
        self.product_list = QTableWidget()
        self.product_list.setColumnCount(6)
        self.product_list.setHorizontalHeaderLabels([
            "Select", "Name", "Price", "Currency", "Stock", "Category"
        ])
        self.product_list.horizontalHeader().setStretchLastSection(True)
        self.product_list.setSelectionMode(QTableWidget.NoSelection)
        
        # Load products
        self._load_products()
        
        layout.addWidget(self.product_list)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def _load_products(self):
        """Load products into table"""
        products = self.product_manager.list_products()
        active_products = [p for p in products if p.active and p.stock > 0]
        
        self.product_list.setRowCount(len(active_products))
        
        for row, product in enumerate(active_products):
            # Checkbox
            checkbox = QCheckBox()
            checkbox.setProperty("product_id", product.id)
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            self.product_list.setCellWidget(row, 0, checkbox_widget)
            
            # Product details
            self.product_list.setItem(row, 1, QTableWidgetItem(product.name))
            self.product_list.setItem(row, 2, QTableWidgetItem(f"{product.price:.2f}"))
            self.product_list.setItem(row, 3, QTableWidgetItem(product.currency))
            self.product_list.setItem(row, 4, QTableWidgetItem(str(product.stock)))
            self.product_list.setItem(row, 5, QTableWidgetItem(product.category or "N/A"))
    
    def get_selected_products(self):
        """Get list of selected products"""
        selected = []
        products = self.product_manager.list_products()
        
        for row in range(self.product_list.rowCount()):
            checkbox_widget = self.product_list.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    product_id = checkbox.property("product_id")
                    # Find product by ID
                    for product in products:
                        if product.id == product_id:
                            selected.append(product)
                            break
        
        return selected


class SignalRelinkDialog(QDialog):
    """Dialog for re-linking Signal account"""
    
    def __init__(self, signal_handler: SignalHandler, parent=None):
        super().__init__(parent)
        self.signal_handler = signal_handler
        self.setWindowTitle("Re-link Signal Account")
        self.setModal(True)
        self.setMinimumSize(800, 700)
        
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel(
            "Re-link your Signal account:\n"
            "1. Click 'Generate QR Code' below\n"
            "2. Open Signal on your phone\n"
            "3. Go to Settings → Linked Devices\n"
            "4. Tap 'Link New Device'\n"
            "5. Scan the QR code shown below\n\n"
            "Note: This will unlink your current device and link a new one."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Generate QR button
        self.generate_btn = QPushButton("Generate QR Code")
        self.generate_btn.clicked.connect(self.generate_qr)
        layout.addWidget(self.generate_btn)
        
        # QR code display (scrollable)
        scroll_area = QScrollArea()
        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setMinimumSize(450, 450)
        scroll_area.setWidget(self.qr_label)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        # Action buttons
        button_layout = QHBoxLayout()
        self.save_qr_btn = QPushButton("Save QR as Image")
        self.save_qr_btn.clicked.connect(self.save_qr_image)
        self.save_qr_btn.setEnabled(False)
        
        self.copy_link_btn = QPushButton("Copy Link")
        self.copy_link_btn.clicked.connect(self.copy_link_text)
        self.copy_link_btn.setEnabled(False)
        
        button_layout.addWidget(self.save_qr_btn)
        button_layout.addWidget(self.copy_link_btn)
        layout.addLayout(button_layout)
        
        # Link text display
        link_label = QLabel("Or copy link text:")
        self.link_text = QTextEdit()
        self.link_text.setReadOnly(True)
        self.link_text.setMaximumHeight(80)
        layout.addWidget(link_label)
        layout.addWidget(self.link_text)
        
        # Timer label for expiration
        self.timer_label = QLabel("")
        self.timer_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.timer_label)
        
        # Phone number input (alternative)
        phone_label = QLabel("\nOr enter new Signal phone number:")
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("+15555550123")
        layout.addWidget(phone_label)
        layout.addWidget(self.phone_input)
        
        # Dialog buttons
        dialog_buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        dialog_buttons.accepted.connect(self.accept)
        dialog_buttons.rejected.connect(self.reject)
        layout.addWidget(dialog_buttons)
        
        self.setLayout(layout)
        self.link_uri = None
        self.expiration_timer = None
    
    def generate_qr(self):
        """Generate QR code for linking"""
        try:
            # Generate link using signal-cli
            self.link_uri = self.signal_handler.link_device()
            
            # Generate QR code
            from ..utils.qr_generator import qr_generator
            qr_data = qr_generator.generate_simple_qr(self.link_uri)
            
            # Display QR code (larger size)
            pixmap = QPixmap()
            pixmap.loadFromData(qr_data)
            self.qr_label.setPixmap(pixmap.scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            
            # Show link text
            self.link_text.setPlainText(self.link_uri)
            
            # Enable buttons
            self.save_qr_btn.setEnabled(True)
            self.copy_link_btn.setEnabled(True)
            
            # Start expiration countdown (5 minutes)
            self.start_expiration_timer()
            
            QMessageBox.information(
                self,
                "QR Code Generated",
                "Scan the QR code with Signal on your phone within 5 minutes."
            )
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to generate QR code: {e}"
            )
    
    def save_qr_image(self):
        """Save QR code as image file"""
        # Try Desktop first, fall back to home directory
        desktop_path = os.path.expanduser("~/Desktop")
        if os.path.exists(desktop_path):
            save_path = os.path.join(desktop_path, "signal_relink_qr.png")
        else:
            save_path = os.path.expanduser("~/signal_relink_qr.png")
            
        if self.qr_label.pixmap():
            try:
                self.qr_label.pixmap().save(save_path)
                QMessageBox.information(
                    self,
                    "Saved",
                    f"QR code saved to:\n{save_path}"
                )
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Failed to save QR code: {e}"
                )
    
    def copy_link_text(self):
        """Copy link text to clipboard"""
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText(self.link_uri)
        QMessageBox.information(
            self,
            "Copied",
            "Link copied to clipboard!"
        )
    
    def start_expiration_timer(self):
        """Start countdown timer for QR expiration"""
        self.remaining_seconds = 300  # 5 minutes
        self.expiration_timer = QTimer()
        self.expiration_timer.timeout.connect(self.update_timer)
        self.expiration_timer.start(1000)  # Update every second
    
    def update_timer(self):
        """Update expiration timer display"""
        self.remaining_seconds -= 1
        minutes = self.remaining_seconds // 60
        seconds = self.remaining_seconds % 60
        self.timer_label.setText(f"⏰ QR code expires in: {minutes}:{seconds:02d}")
        
        if self.remaining_seconds <= 0:
            self.expiration_timer.stop()
            self.timer_label.setText("❌ QR code expired - click Generate QR Code again")
            self.save_qr_btn.setEnabled(False)
            self.copy_link_btn.setEnabled(False)
    
    def get_new_phone(self):
        """Get the new phone number if entered manually"""
        return self.phone_input.text() if self.phone_input.text() else None


class EditWalletDialog(QDialog):
    """Dialog for editing Monero wallet configuration"""
    
    def __init__(self, seller_manager, current_seller, parent=None):
        super().__init__(parent)
        self.seller_manager = seller_manager
        self.seller = current_seller
        self.wallet_config = current_seller.wallet_config.copy() if current_seller.wallet_config else {}
        
        self.setWindowTitle("Edit Wallet Settings")
        self.setModal(True)
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout()
        
        # Warning
        warning = QLabel(
            "⚠️ Changing wallet settings may affect payment processing.\n"
            "Make sure the new configuration is correct before saving."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("color: orange; font-weight: bold;")
        layout.addWidget(warning)
        
        # Wallet type
        type_group = QGroupBox("Wallet Type")
        type_layout = QVBoxLayout()
        
        self.type_group = QButtonGroup()
        self.view_only_radio = QRadioButton("View-Only Wallet (Simple)")
        self.rpc_radio = QRadioButton("RPC Wallet (Advanced)")
        
        # Set current type
        wallet_type = self.wallet_config.get('type', 'view_only')
        if wallet_type == 'view_only':
            self.view_only_radio.setChecked(True)
        else:
            self.rpc_radio.setChecked(True)
        
        self.type_group.addButton(self.view_only_radio, 1)
        self.type_group.addButton(self.rpc_radio, 2)
        
        type_layout.addWidget(self.view_only_radio)
        type_layout.addWidget(self.rpc_radio)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        # Stack for different wallet types
        from PyQt5.QtWidgets import QStackedWidget
        self.config_stack = QStackedWidget()
        
        # View-only config
        view_only_widget = QWidget()
        view_only_layout = QFormLayout()
        
        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("45WQHqFEXu...")
        current_address = self.wallet_config.get('address', '')
        self.address_input.setText(current_address)
        view_only_layout.addRow("XMR Address*:", self.address_input)
        
        view_only_widget.setLayout(view_only_layout)
        self.config_stack.addWidget(view_only_widget)
        
        # RPC config
        rpc_widget = QWidget()
        rpc_layout = QFormLayout()
        
        self.rpc_host_input = QLineEdit()
        self.rpc_host_input.setPlaceholderText("127.0.0.1")
        self.rpc_host_input.setText(self.wallet_config.get('rpc_host', '127.0.0.1'))
        rpc_layout.addRow("RPC Host*:", self.rpc_host_input)
        
        self.rpc_port_input = QLineEdit()
        self.rpc_port_input.setPlaceholderText("18083")
        self.rpc_port_input.setText(str(self.wallet_config.get('rpc_port', 18083)))
        rpc_layout.addRow("RPC Port*:", self.rpc_port_input)
        
        self.rpc_user_input = QLineEdit()
        self.rpc_user_input.setText(self.wallet_config.get('rpc_username', ''))
        rpc_layout.addRow("Username:", self.rpc_user_input)
        
        self.rpc_pass_input = QLineEdit()
        self.rpc_pass_input.setEchoMode(QLineEdit.Password)
        self.rpc_pass_input.setText(self.wallet_config.get('rpc_password', ''))
        rpc_layout.addRow("Password:", self.rpc_pass_input)
        
        rpc_widget.setLayout(rpc_layout)
        self.config_stack.addWidget(rpc_widget)
        
        # Connect radio buttons to stack
        self.view_only_radio.toggled.connect(lambda checked: self.config_stack.setCurrentIndex(0 if checked else 1))
        
        # Set initial stack
        self.config_stack.setCurrentIndex(0 if wallet_type == 'view_only' else 1)
        
        layout.addWidget(self.config_stack)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.save_wallet)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def save_wallet(self):
        """Validate and save wallet configuration"""
        # Determine wallet type
        if self.view_only_radio.isChecked():
            # View-only wallet
            address = self.address_input.text().strip()
            
            if not address:
                QMessageBox.warning(self, "Validation Error", "XMR address is required")
                return
            
            if len(address) < 90:  # Basic validation
                QMessageBox.warning(self, "Validation Error", "Invalid XMR address length")
                return
            
            new_config = {
                'type': 'view_only',
                'address': address
            }
        else:
            # RPC wallet
            host = self.rpc_host_input.text().strip()
            port = self.rpc_port_input.text().strip()
            
            if not host or not port:
                QMessageBox.warning(self, "Validation Error", "RPC host and port are required")
                return
            
            try:
                port_int = int(port)
            except ValueError:
                QMessageBox.warning(self, "Validation Error", "Port must be a number")
                return
            
            new_config = {
                'type': 'rpc',
                'rpc_host': host,
                'rpc_port': port_int,
                'rpc_username': self.rpc_user_input.text().strip(),
                'rpc_password': self.rpc_pass_input.text().strip()
            }
        
        # Update seller
        try:
            self.seller.wallet_config = new_config
            self.seller_manager.update_seller(self.seller)
            QMessageBox.information(self, "Success", "Wallet settings updated successfully")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save wallet settings: {e}")


class ContactDialog(QDialog):
    """Dialog for adding/editing contacts"""
    
    def __init__(self, contact_manager, contact=None, parent=None):
        super().__init__(parent)
        self.contact_manager = contact_manager
        self.contact = contact
        
        self.setWindowTitle("Edit Contact" if contact else "Add Contact")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        
        # Name
        self.name_input = QLineEdit()
        if contact:
            self.name_input.setText(contact.name or "")
        form_layout.addRow("Name*:", self.name_input)
        
        # Signal ID
        self.signal_id_input = QLineEdit()
        self.signal_id_input.setPlaceholderText("+1234567890 or username.123")
        if contact:
            self.signal_id_input.setText(contact.signal_id or "")
            self.signal_id_input.setEnabled(False)  # Don't allow editing Signal ID
        form_layout.addRow("Signal ID*:", self.signal_id_input)
        
        # Notes
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(100)
        if contact:
            self.notes_input.setPlainText(contact.notes or "")
        form_layout.addRow("Notes:", self.notes_input)
        
        layout.addLayout(form_layout)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.save_contact)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def save_contact(self):
        """Validate and save contact"""
        name = self.name_input.text().strip()
        signal_id = self.signal_id_input.text().strip()
        notes = self.notes_input.toPlainText().strip()
        
        if not name:
            QMessageBox.warning(self, "Validation Error", "Name is required")
            return
        
        if not signal_id:
            QMessageBox.warning(self, "Validation Error", "Signal ID is required")
            return
        
        try:
            if self.contact:
                # Update existing contact
                self.contact.name = name
                self.contact.notes = notes
                self.contact_manager.update_contact(self.contact)
            else:
                # Create new contact
                from ..models.contact import Contact
                contact = Contact(
                    signal_id=signal_id,
                    name=name,
                    notes=notes
                )
                self.contact_manager.create_contact(contact)
            
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save contact: {e}")


class ContactPickerDialog(QDialog):
    """Dialog for selecting a contact to message"""
    
    def __init__(self, contact_manager, parent=None):
        super().__init__(parent)
        self.contact_manager = contact_manager
        self.selected_contact = None
        
        self.setWindowTitle("Select Contact")
        self.setModal(True)
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout()
        
        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search contacts...")
        self.search_input.textChanged.connect(self.filter_contacts)
        layout.addWidget(self.search_input)
        
        # Contact list
        self.contact_list = QListWidget()
        self.contact_list.itemDoubleClicked.connect(self.select_contact)
        layout.addWidget(self.contact_list)
        
        # Load contacts
        self._load_contacts()
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def _load_contacts(self):
        """Load contacts into list"""
        self.contact_list.clear()
        contacts = self.contact_manager.list_contacts()
        
        for contact in contacts:
            item = QListWidgetItem(f"{contact.name} ({contact.signal_id})")
            item.setData(Qt.UserRole, contact)
            self.contact_list.addItem(item)
    
    def filter_contacts(self, text):
        """Filter contacts based on search text"""
        search_text = text.lower()
        for i in range(self.contact_list.count()):
            item = self.contact_list.item(i)
            if search_text in item.text().lower():
                item.setHidden(False)
            else:
                item.setHidden(True)
    
    def select_contact(self, item):
        """Select contact on double-click"""
        self.selected_contact = item.data(Qt.UserRole)
        self.accept()
    
    def get_selected_contact(self):
        """Get selected contact"""
        if self.selected_contact:
            return self.selected_contact
        
        # Get from current selection
        current_item = self.contact_list.currentItem()
        if current_item:
            return current_item.data(Qt.UserRole)
        
        return None


class ContactsTab(QWidget):
    """Contacts management tab"""
    
    def __init__(self, contact_manager, message_manager, signal_handler):
        super().__init__()
        self.contact_manager = contact_manager
        self.message_manager = message_manager
        self.signal_handler = signal_handler
        
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        header = QLabel("Contacts")
        header.setFont(QFont("Arial", 16, QFont.Bold))
        header_layout.addWidget(header)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Buttons and search
        controls_layout = QHBoxLayout()
        add_btn = QPushButton("Add Contact")
        refresh_btn = QPushButton("Refresh")
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search contacts...")
        self.search_input.textChanged.connect(self.filter_contacts)
        
        controls_layout.addWidget(add_btn)
        controls_layout.addWidget(refresh_btn)
        controls_layout.addWidget(QLabel("Search:"))
        controls_layout.addWidget(self.search_input)
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Contacts table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Name", "Signal ID", "Last Message", "Actions"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.doubleClicked.connect(self.open_chat)
        layout.addWidget(self.table)
        
        # Connect signals
        add_btn.clicked.connect(self.add_contact)
        refresh_btn.clicked.connect(self.load_contacts)
        
        self.setLayout(layout)
        self.load_contacts()
    
    def load_contacts(self):
        """Load contacts into table"""
        self.table.setRowCount(0)
        contacts = self.contact_manager.list_contacts()
        
        # Get seller's Signal ID for conversation lookup
        seller_id = None
        try:
            from ..models.seller import SellerManager
            # Note: This would need seller_manager passed in, or get from parent
            # For now, we'll skip last message lookup
        except:
            pass
        
        self.table.setRowCount(len(contacts))
        
        for row, contact in enumerate(contacts):
            # Name
            self.table.setItem(row, 0, QTableWidgetItem(contact.name or ""))
            
            # Signal ID
            self.table.setItem(row, 1, QTableWidgetItem(contact.signal_id or ""))
            
            # Last message (placeholder for now)
            self.table.setItem(row, 2, QTableWidgetItem("--"))
            
            # Actions button
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            message_btn = QPushButton("Message")
            message_btn.clicked.connect(lambda checked, c=contact: self.message_contact(c))
            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda checked, c=contact: self.edit_contact(c))
            delete_btn = QPushButton("Delete")
            delete_btn.clicked.connect(lambda checked, c=contact: self.delete_contact(c))
            
            actions_layout.addWidget(message_btn)
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
            
            self.table.setCellWidget(row, 3, actions_widget)
        
        self.table.resizeColumnsToContents()
    
    def filter_contacts(self, text):
        """Filter contacts based on search text"""
        search_text = text.lower()
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            signal_id_item = self.table.item(row, 1)
            
            match = False
            if name_item and search_text in name_item.text().lower():
                match = True
            if signal_id_item and search_text in signal_id_item.text().lower():
                match = True
            
            self.table.setRowHidden(row, not match)
    
    def add_contact(self):
        """Open dialog to add new contact"""
        dialog = ContactDialog(self.contact_manager, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_contacts()
    
    def edit_contact(self, contact):
        """Open dialog to edit contact"""
        dialog = ContactDialog(self.contact_manager, contact, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_contacts()
    
    def delete_contact(self, contact):
        """Delete a contact"""
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{contact.name}'?\nThis will not delete message history.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.contact_manager.delete_contact(contact.id):
                QMessageBox.information(self, "Success", "Contact deleted")
                self.load_contacts()
            else:
                QMessageBox.warning(self, "Error", "Failed to delete contact")
    
    def message_contact(self, contact):
        """Open message dialog for contact"""
        # Emit signal to switch to Messages tab and start conversation
        # For now, show a message box
        QMessageBox.information(
            self,
            "Message Contact",
            f"This will open a chat with {contact.name} in the Messages tab.\n\n"
            "Feature partially implemented - please use Messages tab to start conversation."
        )
    
    def open_chat(self, index):
        """Open chat on double-click"""
        row = index.row()
        name_item = self.table.item(row, 0)
        if name_item:
            # Get contact by name (not ideal, but works for now)
            name = name_item.text()
            contacts = self.contact_manager.list_contacts()
            for contact in contacts:
                if contact.name == name:
                    self.message_contact(contact)
                    break
    
    def show_context_menu(self, position):
        """Show context menu for contact table"""
        item = self.table.itemAt(position)
        if not item:
            return
        
        row = item.row()
        name_item = self.table.item(row, 0)
        if not name_item:
            return
        
        # Get contact
        name = name_item.text()
        contacts = self.contact_manager.list_contacts()
        contact = None
        for c in contacts:
            if c.name == name:
                contact = c
                break
        
        if not contact:
            return
        
        menu = QMenu(self)
        message_action = QAction("💬 Message", self)
        message_action.triggered.connect(lambda: self.message_contact(contact))
        edit_action = QAction("✏️ Edit", self)
        edit_action.triggered.connect(lambda: self.edit_contact(contact))
        delete_action = QAction("🗑️ Delete", self)
        delete_action.triggered.connect(lambda: self.delete_contact(contact))
        
        menu.addAction(message_action)
        menu.addAction(edit_action)
        menu.addSeparator()
        menu.addAction(delete_action)
        
        menu.exec_(self.table.mapToGlobal(position))


class RefreshBalanceWorker(QThread):
    """Worker thread for refreshing wallet balance"""
    finished = pyqtSignal(tuple)
    error = pyqtSignal(str)
    
    def __init__(self, wallet):
        super().__init__()
        self.wallet = wallet
    
    def run(self):
        try:
            balance = self.wallet.get_balance()
            self.finished.emit(balance)
        except Exception as e:
            self.error.emit(str(e))


class RefreshTransfersWorker(QThread):
    """Worker thread for refreshing transactions"""
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, wallet):
        super().__init__()
        self.wallet = wallet
    
    def run(self):
        try:
            transfers = self.wallet.get_transfers()
            self.finished.emit(transfers)
        except Exception as e:
            self.error.emit(str(e))


class SendFundsWorker(QThread):
    """Worker thread for sending funds"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, wallet, address, amount, priority):
        super().__init__()
        self.wallet = wallet
        self.address = address
        self.amount = amount
        self.priority = priority
    
    def run(self):
        try:
            result = self.wallet.send(self.address, self.amount, self.priority)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class BackupWalletWorker(QThread):
    """Worker thread for backing up wallet"""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, wallet):
        super().__init__()
        self.wallet = wallet
    
    def run(self):
        try:
            backup_path = self.wallet.backup_wallet()
            self.finished.emit(backup_path)
        except Exception as e:
            self.error.emit(str(e))


class SendFundsDialog(QDialog):
    """Dialog for sending Monero funds"""
    
    def __init__(self, wallet, parent=None):
        super().__init__(parent)
        self.wallet = wallet
        self.setWindowTitle("Send Funds")
        self.setModal(True)
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        
        # Address
        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("Monero address (starts with 4...)")
        form_layout.addRow("Recipient Address*:", self.address_input)
        
        # Amount
        self.amount_input = QDoubleSpinBox()
        self.amount_input.setDecimals(12)
        self.amount_input.setMaximum(1000000.0)
        self.amount_input.setMinimum(0.000000000001)
        self.amount_input.setSingleStep(0.1)
        form_layout.addRow("Amount (XMR)*:", self.amount_input)
        
        # Priority
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Low", "Medium", "High", "Urgent"])
        self.priority_combo.setCurrentIndex(1)  # Default to Medium
        form_layout.addRow("Priority:", self.priority_combo)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def validate_and_accept(self):
        """Validate inputs before accepting"""
        address = self.address_input.text().strip()
        amount = self.amount_input.value()
        
        if not address:
            QMessageBox.warning(self, "Validation Error", "Please enter a recipient address")
            return
        
        if len(address) < 95:
            QMessageBox.warning(self, "Validation Error", "Invalid Monero address (too short)")
            return
        
        if amount <= 0:
            QMessageBox.warning(self, "Validation Error", "Amount must be greater than zero")
            return
        
        # Confirm transaction
        reply = QMessageBox.question(
            self,
            "Confirm Send",
            f"Send {amount:.12f} XMR to:\n{address[:20]}...{address[-20:]}?\n\nThis action cannot be undone!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.accept()
    
    def get_data(self):
        """Get form data"""
        return {
            'address': self.address_input.text().strip(),
            'amount': self.amount_input.value(),
            'priority': self.priority_combo.currentIndex()
        }


class ReceiveDialog(QDialog):
    """Dialog for receiving Monero (shows QR code)"""
    
    def __init__(self, address, parent=None):
        super().__init__(parent)
        self.address = address
        self.setWindowTitle("Receive Funds")
        self.setModal(True)
        self.setMinimumWidth(450)
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Share this address to receive XMR:")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)
        
        # Address display
        address_layout = QHBoxLayout()
        self.address_label = QLineEdit(address)
        self.address_label.setReadOnly(True)
        self.address_label.setFont(QFont("Courier", 9))
        
        copy_btn = QPushButton("Copy")
        copy_btn.clicked.connect(self.copy_address)
        
        address_layout.addWidget(self.address_label)
        address_layout.addWidget(copy_btn)
        layout.addLayout(address_layout)
        
        # QR Code placeholder
        qr_label = QLabel("QR Code Generation:\nInstall qrcode library for QR display")
        qr_label.setAlignment(Qt.AlignCenter)
        qr_label.setMinimumHeight(250)
        qr_label.setStyleSheet("border: 1px solid #ccc; background: #f9f9f9; padding: 20px;")
        
        try:
            import qrcode
            from io import BytesIO
            
            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(address)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to QPixmap
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            pixmap = QPixmap()
            pixmap.loadFromData(buffer.read())
            qr_label.setPixmap(pixmap.scaled(300, 300, Qt.KeepAspectRatio))
        except ImportError:
            pass
        
        layout.addWidget(qr_label)
        
        # Warning
        warning = QLabel("⚠️ Only send Monero (XMR) to this address!")
        warning.setStyleSheet("color: #ff6600; font-weight: bold;")
        warning.setAlignment(Qt.AlignCenter)
        layout.addWidget(warning)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
    
    def copy_address(self):
        """Copy address to clipboard"""
        QApplication.clipboard().setText(self.address)
        QMessageBox.information(self, "Copied", "Address copied to clipboard!")


class BackupDialog(QDialog):
    """Dialog showing backup status"""
    
    def __init__(self, backup_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Wallet Backup")
        self.setModal(True)
        self.setMinimumWidth(450)
        
        layout = QVBoxLayout()
        
        # Success message
        success_label = QLabel("✅ Wallet backed up successfully!")
        success_label.setFont(QFont("Arial", 14, QFont.Bold))
        success_label.setStyleSheet("color: green;")
        layout.addWidget(success_label)
        
        # Backup path
        path_label = QLabel(f"Backup saved to:\n{backup_path}")
        path_label.setWordWrap(True)
        layout.addWidget(path_label)
        
        # Warning
        warning = QLabel(
            "⚠️ IMPORTANT:\n"
            "• Keep this backup file secure\n"
            "• Store it in multiple safe locations\n"
            "• Never share your wallet files with anyone\n"
            "• Keep your seed phrase backed up separately"
        )
        warning.setStyleSheet("color: #ff6600; margin-top: 20px;")
        layout.addWidget(warning)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)


class WalletTab(QWidget):
    """Monero wallet management tab"""
    
    def __init__(self, wallet: Optional[InHouseWallet] = None, db_manager=None, seller_manager=None):
        super().__init__()
        self.wallet = wallet
        self.db_manager = db_manager
        self.seller_manager = seller_manager
        self.subaddresses = []
        self.transfers = []
        self.last_refresh = None
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.auto_refresh)
        self.refresh_timer.start(30000)  # 30 seconds
        
        self.init_ui()
        
        # Initial load
        if self.wallet:
            self.refresh_all()
    
    def init_ui(self):
        """Initialize UI components"""
        main_layout = QVBoxLayout()
        
        # Sync Status Bar (very top)
        self.sync_status_bar = self.create_sync_status_bar()
        main_layout.addWidget(self.sync_status_bar)
        
        # Balance Display Section
        self.balance_section = self.create_balance_section()
        main_layout.addWidget(self.balance_section)
        
        # Middle section: Address Management + Quick Actions
        middle_layout = QHBoxLayout()
        
        # Address Management Section (left)
        self.address_section = self.create_address_section()
        middle_layout.addWidget(self.address_section, 1)
        
        # Quick Actions Section (right)
        self.actions_section = self.create_actions_section()
        middle_layout.addWidget(self.actions_section, 1)
        
        main_layout.addLayout(middle_layout)
        
        # Transaction History Section (bottom)
        self.history_section = self.create_history_section()
        main_layout.addWidget(self.history_section, 2)
        
        self.setLayout(main_layout)
    
    def create_sync_status_bar(self):
        """Create sync status bar"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        frame.setMaximumHeight(50)
        
        layout = QHBoxLayout()
        
        # Connection indicator
        self.connection_indicator = QLabel("●")
        self.connection_indicator.setStyleSheet("color: red; font-size: 20px;")
        layout.addWidget(self.connection_indicator)
        
        self.connection_status = QLabel("Disconnected")
        layout.addWidget(self.connection_status)
        
        layout.addStretch()
        
        # Block height
        self.block_height_label = QLabel("Block: 0 / 0")
        layout.addWidget(self.block_height_label)
        
        # Progress bar
        self.sync_progress = QProgressBar()
        self.sync_progress.setMaximumWidth(200)
        self.sync_progress.setValue(0)
        layout.addWidget(self.sync_progress)
        
        # Last sync
        self.last_sync_label = QLabel("Last sync: Never")
        layout.addWidget(self.last_sync_label)
        
        frame.setLayout(layout)
        return frame
    
    def create_balance_section(self):
        """Create balance display section"""
        group = QGroupBox("Wallet Balance")
        group.setFont(QFont("Arial", 12, QFont.Bold))
        
        layout = QGridLayout()
        
        # Total balance
        layout.addWidget(QLabel("Total Balance:"), 0, 0)
        self.total_balance_label = QLabel("0.000000000000 XMR")
        self.total_balance_label.setFont(QFont("Courier", 14, QFont.Bold))
        layout.addWidget(self.total_balance_label, 0, 1)
        
        # Unlocked balance
        layout.addWidget(QLabel("Unlocked:"), 1, 0)
        self.unlocked_balance_label = QLabel("0.000000000000 XMR")
        self.unlocked_balance_label.setFont(QFont("Courier", 12))
        self.unlocked_balance_label.setStyleSheet("color: green;")
        layout.addWidget(self.unlocked_balance_label, 1, 1)
        
        # Locked balance
        layout.addWidget(QLabel("Locked/Pending:"), 2, 0)
        self.locked_balance_label = QLabel("0.000000000000 XMR")
        self.locked_balance_label.setFont(QFont("Courier", 12))
        self.locked_balance_label.setStyleSheet("color: #ff9900;")
        layout.addWidget(self.locked_balance_label, 2, 1)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh Balance")
        refresh_btn.clicked.connect(self.refresh_balance)
        layout.addWidget(refresh_btn, 0, 2, 3, 1)
        
        # Last updated
        self.balance_updated_label = QLabel("Last updated: Never")
        self.balance_updated_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(self.balance_updated_label, 3, 0, 1, 3)
        
        group.setLayout(layout)
        return group
    
    def create_address_section(self):
        """Create address management section"""
        group = QGroupBox("Address Management")
        group.setFont(QFont("Arial", 11, QFont.Bold))
        
        layout = QVBoxLayout()
        
        # Primary address
        primary_layout = QHBoxLayout()
        primary_layout.addWidget(QLabel("Primary Address:"))
        
        self.primary_address_label = QLineEdit()
        self.primary_address_label.setReadOnly(True)
        self.primary_address_label.setFont(QFont("Courier", 8))
        self.primary_address_label.setText("Not connected")
        primary_layout.addWidget(self.primary_address_label)
        
        copy_primary_btn = QPushButton("Copy")
        copy_primary_btn.clicked.connect(lambda: self.copy_address(self.primary_address_label.text()))
        primary_layout.addWidget(copy_primary_btn)
        
        layout.addLayout(primary_layout)
        
        # Generate subaddress button
        gen_subaddr_btn = QPushButton("+ Generate Subaddress")
        gen_subaddr_btn.clicked.connect(self.generate_subaddress)
        layout.addWidget(gen_subaddr_btn)
        
        # Subaddresses list
        layout.addWidget(QLabel("Subaddresses:"))
        self.subaddress_list = QListWidget()
        self.subaddress_list.setMaximumHeight(150)
        self.subaddress_list.itemDoubleClicked.connect(self.show_receive_dialog)
        layout.addWidget(self.subaddress_list)
        
        group.setLayout(layout)
        return group
    
    def create_actions_section(self):
        """Create quick actions section"""
        group = QGroupBox("Quick Actions")
        group.setFont(QFont("Arial", 11, QFont.Bold))
        
        layout = QVBoxLayout()
        
        # Send Funds
        send_btn = QPushButton("💸 Send Funds")
        send_btn.setMinimumHeight(40)
        send_btn.setStyleSheet("font-size: 12px; font-weight: bold;")
        send_btn.clicked.connect(self.send_funds)
        layout.addWidget(send_btn)
        
        # Receive
        receive_btn = QPushButton("📥 Receive (Show QR)")
        receive_btn.setMinimumHeight(40)
        receive_btn.setStyleSheet("font-size: 12px; font-weight: bold;")
        receive_btn.clicked.connect(lambda: self.show_receive_dialog())
        layout.addWidget(receive_btn)
        
        # Backup Wallet
        backup_btn = QPushButton("💾 Backup Wallet")
        backup_btn.setMinimumHeight(40)
        backup_btn.clicked.connect(self.backup_wallet)
        layout.addWidget(backup_btn)
        
        # Export Transactions
        export_btn = QPushButton("📊 Export Transactions")
        export_btn.setMinimumHeight(40)
        export_btn.clicked.connect(self.export_transactions)
        layout.addWidget(export_btn)
        
        layout.addStretch()
        
        group.setLayout(layout)
        return group
    
    def create_history_section(self):
        """Create transaction history section"""
        group = QGroupBox("Transaction History")
        group.setFont(QFont("Arial", 11, QFont.Bold))
        
        layout = QVBoxLayout()
        
        # Transactions table
        self.transactions_table = QTableWidget()
        self.transactions_table.setColumnCount(5)
        self.transactions_table.setHorizontalHeaderLabels([
            "Type", "Amount (XMR)", "Address", "Confirmations", "Date"
        ])
        self.transactions_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.transactions_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.transactions_table)
        
        # View All button
        view_all_btn = QPushButton("View All Transactions")
        view_all_btn.clicked.connect(self.view_all_transactions)
        layout.addWidget(view_all_btn)
        
        group.setLayout(layout)
        return group
    
    def refresh_all(self):
        """Refresh all wallet data"""
        print(f"🔧 DEBUG: WalletTab.refresh_all() called")
        print(f"   Wallet instance: {self.wallet}")
        
        if not self.wallet:
            print("⚠ DEBUG: Wallet is None, skipping refresh")
            return
        
        print("✓ DEBUG: Refreshing balance...")
        self.refresh_balance()
        print("✓ DEBUG: Refreshing addresses...")
        self.refresh_addresses()
        print("✓ DEBUG: Refreshing transactions...")
        self.refresh_transactions()
        print("✓ DEBUG: Refresh complete")
    
    def refresh_balance(self):
        """Refresh wallet balance"""
        if not self.wallet:
            self.show_not_connected()
            return
        
        # Use worker thread
        self.balance_worker = RefreshBalanceWorker(self.wallet)
        self.balance_worker.finished.connect(self.on_balance_refreshed)
        self.balance_worker.error.connect(self.on_balance_error)
        self.balance_worker.start()
    
    def on_balance_refreshed(self, balance):
        """Handle balance refresh completion"""
        total, unlocked, locked = balance
        
        self.total_balance_label.setText(f"{total:.12f} XMR")
        self.unlocked_balance_label.setText(f"{unlocked:.12f} XMR")
        self.locked_balance_label.setText(f"{locked:.12f} XMR")
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.balance_updated_label.setText(f"Last updated: {now}")
        self.last_refresh = now
        
        # Update sync status
        self.connection_indicator.setStyleSheet("color: green; font-size: 20px;")
        self.connection_status.setText("Connected")
    
    def on_balance_error(self, error_msg):
        """Handle balance refresh error"""
        QMessageBox.warning(self, "Error", f"Failed to refresh balance:\n{error_msg}")
        self.connection_indicator.setStyleSheet("color: red; font-size: 20px;")
        self.connection_status.setText("Error")
    
    def refresh_addresses(self):
        """Refresh wallet addresses"""
        if not self.wallet:
            return
        
        try:
            # Get primary address
            primary = self.wallet.get_address()
            self.primary_address_label.setText(primary)
            
            # Note: Getting subaddresses would require additional wallet methods
            # For now, we'll keep the current list
        except Exception as e:
            print(f"Error refreshing addresses: {e}")
    
    def refresh_transactions(self):
        """Refresh transaction history"""
        if not self.wallet:
            return
        
        # Use worker thread
        self.transfers_worker = RefreshTransfersWorker(self.wallet)
        self.transfers_worker.finished.connect(self.on_transfers_refreshed)
        self.transfers_worker.error.connect(self.on_transfers_error)
        self.transfers_worker.start()
    
    def on_transfers_refreshed(self, transfers):
        """Handle transfers refresh completion"""
        self.transfers = transfers
        
        # Update table (show last 20)
        display_transfers = transfers[-20:] if len(transfers) > 20 else transfers
        self.transactions_table.setRowCount(len(display_transfers))
        
        for row, tx in enumerate(display_transfers):
            # Type
            tx_type = tx.get('type', 'in').upper()
            type_item = QTableWidgetItem(tx_type)
            if tx_type == 'IN':
                type_item.setForeground(QColor('green'))
            else:
                type_item.setForeground(QColor('red'))
            self.transactions_table.setItem(row, 0, type_item)
            
            # Amount
            amount = tx.get('amount', 0) / 1e12  # Convert from atomic units
            amount_item = QTableWidgetItem(f"{amount:.12f}")
            self.transactions_table.setItem(row, 1, amount_item)
            
            # Address
            address = tx.get('address', 'N/A')
            addr_display = f"{address[:20]}..." if len(address) > 20 else address
            self.transactions_table.setItem(row, 2, QTableWidgetItem(addr_display))
            
            # Confirmations
            confirmations = tx.get('confirmations', 0)
            self.transactions_table.setItem(row, 3, QTableWidgetItem(str(confirmations)))
            
            # Date
            timestamp = tx.get('timestamp', 0)
            if timestamp:
                date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")
            else:
                date_str = "N/A"
            self.transactions_table.setItem(row, 4, QTableWidgetItem(date_str))
        
        self.transactions_table.resizeColumnsToContents()
    
    def on_transfers_error(self, error_msg):
        """Handle transfers refresh error"""
        print(f"Error refreshing transfers: {error_msg}")
    
    def auto_refresh(self):
        """Auto-refresh wallet data"""
        if self.wallet:
            self.refresh_all()
    
    def generate_subaddress(self):
        """Generate new subaddress"""
        if not self.wallet:
            self.show_not_connected()
            return
        
        label, ok = QInputDialog.getText(self, "Generate Subaddress", "Enter label (optional):")
        
        if ok:
            try:
                subaddr = self.wallet.create_subaddress(label if label else None)
                address = subaddr.get('address', '')
                
                # Add to list
                item = QListWidgetItem(f"{label or 'Unlabeled'}: {address[:30]}...")
                item.setData(Qt.UserRole, address)
                self.subaddress_list.addItem(item)
                
                QMessageBox.information(
                    self,
                    "Success",
                    f"Subaddress generated:\n{address}\n\nClick to view QR code."
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to generate subaddress:\n{e}")
    
    def copy_address(self, address):
        """Copy address to clipboard"""
        if address and address != "Not connected":
            QApplication.clipboard().setText(address)
            QMessageBox.information(self, "Copied", "Address copied to clipboard!")
    
    def show_receive_dialog(self, item=None):
        """Show receive dialog with QR code"""
        if not self.wallet:
            self.show_not_connected()
            return
        
        if item:
            address = item.data(Qt.UserRole)
        else:
            address = self.primary_address_label.text()
        
        if address and address != "Not connected":
            dialog = ReceiveDialog(address, self)
            dialog.exec_()
    
    def send_funds(self):
        """Open send funds dialog with PIN verification"""
        if not self.wallet:
            self.show_not_connected()
            return
        
        dialog = SendFundsDialog(self.wallet, self)
        if dialog.exec_() != QDialog.Accepted:
            return
        
        data = dialog.get_data()
        
        # Step 1: Request PIN for authorization
        if self.seller_manager and self.db_manager:
            pin_dialog = PINDialog(self)
            pin_dialog.setWindowTitle("Enter PIN to Authorize Transaction")
            
            if pin_dialog.exec_() != QDialog.Accepted:
                return
            
            entered_pin = pin_dialog.get_pin()
            
            # Step 2: Verify PIN
            from ..database.db import Seller
            seller = self.db_manager.session.query(Seller).first()
            if not seller:
                QMessageBox.critical(self, "Error", "Seller data not found")
                return
            
            from ..core.security import security_manager
            if not security_manager.verify_pin(entered_pin, seller.pin_hash, seller.pin_salt):
                QMessageBox.critical(self, "Access Denied", "Incorrect PIN")
                return
        
        # Step 3: Show progress and execute transaction
        progress = QProgressDialog("Sending transaction...", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        
        # Use worker thread
        self.send_worker = SendFundsWorker(
            self.wallet,
            data['address'],
            data['amount'],
            data['priority']
        )
        self.send_worker.finished.connect(lambda result: self.on_send_complete(result, progress))
        self.send_worker.error.connect(lambda error: self.on_send_error(error, progress))
        self.send_worker.start()
    
    def on_send_complete(self, result, progress):
        """Handle send completion"""
        progress.close()
        
        tx_hash = result.get('tx_hash', 'N/A')
        amount = result.get('amount', 0)
        fee = result.get('fee', 0)
        
        QMessageBox.information(
            self,
            "Transaction Sent",
            f"Transaction sent successfully!\n\n"
            f"Amount: {amount:.12f} XMR\n"
            f"Fee: {fee:.12f} XMR\n"
            f"TX Hash: {tx_hash[:32]}..."
        )
        
        # Refresh balance and transactions
        self.refresh_all()
    
    def on_send_error(self, error_msg, progress):
        """Handle send error"""
        progress.close()
        QMessageBox.critical(self, "Send Failed", f"Failed to send transaction:\n{error_msg}")
    
    def backup_wallet(self):
        """Backup wallet"""
        if not self.wallet:
            self.show_not_connected()
            return
        
        reply = QMessageBox.question(
            self,
            "Backup Wallet",
            "Create encrypted backup of wallet?\n\nBackup will be saved to the backup directory.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            # Show progress
            progress = QProgressDialog("Creating backup...", None, 0, 0, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            
            # Use worker thread
            self.backup_worker = BackupWalletWorker(self.wallet)
            self.backup_worker.finished.connect(lambda path: self.on_backup_complete(path, progress))
            self.backup_worker.error.connect(lambda error: self.on_backup_error(error, progress))
            self.backup_worker.start()
    
    def on_backup_complete(self, backup_path, progress):
        """Handle backup completion"""
        progress.close()
        
        dialog = BackupDialog(backup_path, self)
        dialog.exec_()
    
    def on_backup_error(self, error_msg, progress):
        """Handle backup error"""
        progress.close()
        QMessageBox.critical(self, "Backup Failed", f"Failed to backup wallet:\n{error_msg}")
    
    def export_transactions(self):
        """Export transactions to CSV"""
        if not self.wallet or not self.transfers:
            QMessageBox.warning(self, "No Data", "No transactions to export")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Transactions",
            f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                import csv
                
                with open(file_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Type', 'Amount (XMR)', 'Address', 'Confirmations', 'Date', 'TX Hash'])
                    
                    for tx in self.transfers:
                        tx_type = tx.get('type', 'in').upper()
                        amount = tx.get('amount', 0) / 1e12
                        address = tx.get('address', 'N/A')
                        confirmations = tx.get('confirmations', 0)
                        timestamp = tx.get('timestamp', 0)
                        date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M") if timestamp else "N/A"
                        tx_hash = tx.get('txid', 'N/A')
                        
                        writer.writerow([tx_type, f"{amount:.12f}", address, confirmations, date_str, tx_hash])
                
                QMessageBox.information(self, "Success", f"Transactions exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Failed to export transactions:\n{e}")
    
    def view_all_transactions(self):
        """View all transactions (open full table)"""
        if not self.transfers:
            QMessageBox.information(self, "No Transactions", "No transactions to display")
            return
        
        # Reload table with all transactions
        self.transactions_table.setRowCount(len(self.transfers))
        
        for row, tx in enumerate(self.transfers):
            # Type
            tx_type = tx.get('type', 'in').upper()
            type_item = QTableWidgetItem(tx_type)
            if tx_type == 'IN':
                type_item.setForeground(QColor('green'))
            else:
                type_item.setForeground(QColor('red'))
            self.transactions_table.setItem(row, 0, type_item)
            
            # Amount
            amount = tx.get('amount', 0) / 1e12
            amount_item = QTableWidgetItem(f"{amount:.12f}")
            self.transactions_table.setItem(row, 1, amount_item)
            
            # Address
            address = tx.get('address', 'N/A')
            addr_display = f"{address[:20]}..." if len(address) > 20 else address
            self.transactions_table.setItem(row, 2, QTableWidgetItem(addr_display))
            
            # Confirmations
            confirmations = tx.get('confirmations', 0)
            self.transactions_table.setItem(row, 3, QTableWidgetItem(str(confirmations)))
            
            # Date
            timestamp = tx.get('timestamp', 0)
            if timestamp:
                date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")
            else:
                date_str = "N/A"
            self.transactions_table.setItem(row, 4, QTableWidgetItem(date_str))
        
        self.transactions_table.resizeColumnsToContents()
        QMessageBox.information(self, "All Transactions", f"Displaying all {len(self.transfers)} transactions")
    
    def show_not_connected(self):
        """Show wallet not connected message"""
        QMessageBox.warning(
            self,
            "Wallet Not Connected",
            "Wallet is not connected. Please configure your wallet in Settings."
        )


class ProductsTab(QWidget):
    """Products management tab"""
    
    def __init__(self, product_manager: ProductManager):
        super().__init__()
        self.product_manager = product_manager
        
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("Product Catalog")
        header.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(header)
        
        # Buttons
        button_layout = QHBoxLayout()
        add_btn = QPushButton("Add Product")
        refresh_btn = QPushButton("Refresh")
        edit_btn = QPushButton("Edit Product")
        delete_btn = QPushButton("Delete Product")
        
        button_layout.addWidget(add_btn)
        button_layout.addWidget(edit_btn)
        button_layout.addWidget(delete_btn)
        button_layout.addWidget(refresh_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Products table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Name", "Price", "Stock", "Category", "Status"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.doubleClicked.connect(self.edit_product)
        layout.addWidget(self.table)
        
        # Connect signals
        add_btn.clicked.connect(self.add_product)
        edit_btn.clicked.connect(self.edit_product)
        delete_btn.clicked.connect(self.delete_product)
        refresh_btn.clicked.connect(self.load_products)
        
        self.setLayout(layout)
        self.load_products()
    
    def add_product(self):
        """Open dialog to add new product"""
        dialog = AddProductDialog(self.product_manager, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_products()
            # Invalidate product cache
            if hasattr(self, 'buyer_handler') and self.buyer_handler:
                self.buyer_handler.product_cache.invalidate()
    
    def edit_product(self):
        """Open dialog to edit selected product"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a product to edit")
            return
        
        row = selected_rows[0].row()
        product_id = int(self.table.item(row, 0).text())
        
        product = self.product_manager.get_product(product_id)
        if product:
            dialog = AddProductDialog(self.product_manager, product, parent=self)
            if dialog.exec_() == QDialog.Accepted:
                self.load_products()
                # Invalidate product cache
                if hasattr(self, 'buyer_handler') and self.buyer_handler:
                    self.buyer_handler.product_cache.invalidate()
    
    def delete_product(self):
        """Delete selected product"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a product to delete")
            return
        
        row = selected_rows[0].row()
        product_id = int(self.table.item(row, 0).text())
        product_name = self.table.item(row, 1).text()
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{product_name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.product_manager.delete_product(product_id)
                QMessageBox.information(self, "Success", "Product deleted successfully")
                self.load_products()
                # Invalidate product cache
                if hasattr(self, 'buyer_handler') and self.buyer_handler:
                    self.buyer_handler.product_cache.invalidate()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete product: {e}")
    
    def load_products(self):
        """Load products into table"""
        products = self.product_manager.list_products(active_only=False)
        
        self.table.setRowCount(len(products))
        
        for row, product in enumerate(products):
            self.table.setItem(row, 0, QTableWidgetItem(str(product.id)))
            self.table.setItem(row, 1, QTableWidgetItem(product.name))
            self.table.setItem(row, 2, QTableWidgetItem(
                f"{product.currency} {product.price:.2f}"
            ))
            self.table.setItem(row, 3, QTableWidgetItem(str(product.stock)))
            self.table.setItem(row, 4, QTableWidgetItem(product.category or "N/A"))
            self.table.setItem(row, 5, QTableWidgetItem(
                "Active" if product.active else "Inactive"
            ))


class OrdersTab(QWidget):
    """Orders management tab"""
    
    # Display constants
    TXID_TRUNCATE_LENGTH = 20  # Minimum length before truncating transaction IDs
    
    def __init__(self, order_manager: OrderManager):
        super().__init__()
        self.order_manager = order_manager
        
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("Orders")
        header.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(header)
        
        # Buttons
        button_layout = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        delete_old_btn = QPushButton("🗑️ Delete Old Orders")
        delete_old_btn.clicked.connect(self.delete_old_orders)
        button_layout.addWidget(refresh_btn)
        button_layout.addWidget(delete_old_btn)
        button_layout.addStretch()
        
        # Auto-refresh status label
        self.auto_refresh_label = QLabel("⟳ Auto-refresh: 30s")
        self.auto_refresh_label.setStyleSheet("color: gray; font-size: 10px;")
        button_layout.addWidget(self.auto_refresh_label)
        
        layout.addLayout(button_layout)
        
        # Orders table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Order ID", "Product", "Amount (XMR)", "Paid (XMR)", 
            "Payment Status", "TX ID", "Order Status", "Date", "Actions"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setColumnWidth(0, 150)  # Order ID
        self.table.setColumnWidth(1, 180)  # Product
        self.table.setColumnWidth(2, 100)  # Amount
        self.table.setColumnWidth(3, 100)  # Paid
        self.table.setColumnWidth(4, 120)  # Payment Status
        self.table.setColumnWidth(5, 120)  # TX ID
        self.table.setColumnWidth(6, 100)  # Order Status
        self.table.setColumnWidth(7, 140)  # Date
        layout.addWidget(self.table)
        
        # Connect signals
        refresh_btn.clicked.connect(self.load_orders)
        
        # Setup auto-refresh timer (every 30 seconds)
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_orders)
        self.refresh_timer.start(30000)  # 30 seconds
        
        self.setLayout(layout)
        self.load_orders()
    
    def load_orders(self):
        """Load orders into table with enhanced payment status display"""
        orders = self.order_manager.list_orders(limit=100)
        
        self.table.setRowCount(len(orders))
        
        for row, order in enumerate(orders):
            # Order ID
            self.table.setItem(row, 0, QTableWidgetItem(order.order_id))
            
            # Product
            self.table.setItem(row, 1, QTableWidgetItem(order.product_name))
            
            # Amount (XMR)
            self.table.setItem(row, 2, QTableWidgetItem(f"{order.price_xmr:.6f}"))
            
            # Paid Amount (XMR)
            paid_item = QTableWidgetItem(f"{order.amount_paid:.6f}" if order.amount_paid > 0 else "-")
            if order.amount_paid > 0 and order.amount_paid < order.price_xmr:
                paid_item.setForeground(QColor(255, 165, 0))  # Orange for partial
            elif order.amount_paid >= order.price_xmr:
                paid_item.setForeground(QColor(0, 200, 0))  # Green for complete
            self.table.setItem(row, 3, paid_item)
            
            # Payment Status with visual indicators
            status_map = {
                'pending': '⏳ Pending',
                'unconfirmed': '💰 Unconfirmed',
                'partial': '⚠️ Partial',
                'paid': '✅ Confirmed',
                'expired': '❌ Expired'
            }
            status_text = status_map.get(order.payment_status, order.payment_status)
            status_item = QTableWidgetItem(status_text)
            
            # Color code by status
            if order.payment_status == 'paid':
                status_item.setForeground(QColor(0, 200, 0))  # Green
            elif order.payment_status == 'unconfirmed':
                status_item.setForeground(QColor(0, 150, 255))  # Blue
            elif order.payment_status == 'partial':
                status_item.setForeground(QColor(255, 165, 0))  # Orange
            elif order.payment_status == 'expired':
                status_item.setForeground(QColor(200, 0, 0))  # Red
            
            self.table.setItem(row, 4, status_item)
            
            # Transaction ID (shortened)
            if order.payment_txid:
                # Only shorten if longer than threshold to avoid overlap
                if len(order.payment_txid) > self.TXID_TRUNCATE_LENGTH:
                    txid_short = f"{order.payment_txid[:8]}...{order.payment_txid[-8:]}"
                else:
                    txid_short = order.payment_txid
                txid_item = QTableWidgetItem(txid_short)
                txid_item.setToolTip(order.payment_txid)  # Full TX ID on hover
                self.table.setItem(row, 5, txid_item)
            else:
                self.table.setItem(row, 5, QTableWidgetItem("-"))
            
            # Order Status
            self.table.setItem(row, 6, QTableWidgetItem(order.order_status))
            
            # Date
            date_str = order.created_at.strftime("%Y-%m-%d %H:%M") if order.created_at else "N/A"
            self.table.setItem(row, 7, QTableWidgetItem(date_str))
    
    def delete_old_orders(self):
        """Open dialog to delete old orders"""
        dialog = DeleteOldOrdersDialog(self.order_manager, self)
        if dialog.exec_() == QDialog.Accepted:
            deleted_count = dialog.deleted_count
            QMessageBox.information(
                self,
                "Success",
                f"Deleted {deleted_count} old order(s)"
            )
            self.load_orders()


class DeleteOldOrdersDialog(QDialog):
    """Dialog for configuring which orders to delete"""
    
    def __init__(self, order_manager, parent=None):
        super().__init__(parent)
        self.order_manager = order_manager
        self.deleted_count = 0
        
        self.setWindowTitle("Delete Old Orders")
        self.setModal(True)
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel(
            "Select criteria for orders to delete.\n"
            "This action cannot be undone!"
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("font-weight: bold; color: red;")
        layout.addWidget(instructions)
        
        # Criteria checkboxes
        criteria_group = QGroupBox("Delete Criteria")
        criteria_layout = QVBoxLayout()
        
        self.expired_checkbox = QCheckBox("Expired orders (never paid)")
        self.expired_checkbox.setChecked(True)
        criteria_layout.addWidget(self.expired_checkbox)
        
        self.delivered_checkbox = QCheckBox("Delivered orders")
        criteria_layout.addWidget(self.delivered_checkbox)
        
        self.cancelled_checkbox = QCheckBox("Cancelled orders")
        criteria_layout.addWidget(self.cancelled_checkbox)
        
        criteria_group.setLayout(criteria_layout)
        layout.addWidget(criteria_group)
        
        # Age filter
        age_group = QGroupBox("Age Filter (Optional)")
        age_layout = QHBoxLayout()
        
        self.age_checkbox = QCheckBox("Delete orders older than")
        self.age_spinbox = QSpinBox()
        self.age_spinbox.setRange(1, 365)
        self.age_spinbox.setValue(30)
        self.age_spinbox.setSuffix(" days")
        self.age_spinbox.setEnabled(False)
        
        self.age_checkbox.toggled.connect(self.age_spinbox.setEnabled)
        
        age_layout.addWidget(self.age_checkbox)
        age_layout.addWidget(self.age_spinbox)
        age_layout.addStretch()
        
        age_group.setLayout(age_layout)
        layout.addWidget(age_group)
        
        # Preview
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout()
        
        self.preview_label = QLabel("Click 'Preview' to see how many orders will be deleted")
        preview_layout.addWidget(self.preview_label)
        
        preview_btn = QPushButton("Preview")
        preview_btn.clicked.connect(self.preview_deletion)
        preview_layout.addWidget(preview_btn)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.confirm_and_delete)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def get_criteria(self):
        """Get deletion criteria from dialog"""
        criteria = {
            'statuses': [],
            'older_than_days': None
        }
        
        if self.expired_checkbox.isChecked():
            criteria['statuses'].append('expired')
        
        if self.delivered_checkbox.isChecked():
            criteria['statuses'].append('delivered')
        
        if self.cancelled_checkbox.isChecked():
            criteria['statuses'].append('cancelled')
        
        if self.age_checkbox.isChecked():
            criteria['older_than_days'] = self.age_spinbox.value()
        
        return criteria
    
    def preview_deletion(self):
        """Preview how many orders will be deleted"""
        criteria = self.get_criteria()
        
        if not criteria['statuses']:
            self.preview_label.setText("⚠️ No status criteria selected. No orders will be deleted.")
            return
        
        count = self.order_manager.count_orders_matching(criteria)
        self.preview_label.setText(f"📊 {count} order(s) will be deleted")
    
    def confirm_and_delete(self):
        """Confirm and delete matching orders"""
        criteria = self.get_criteria()
        
        if not criteria['statuses']:
            QMessageBox.warning(
                self,
                "No Criteria",
                "Please select at least one status criteria"
            )
            return
        
        # Get count
        count = self.order_manager.count_orders_matching(criteria)
        
        if count == 0:
            QMessageBox.information(
                self,
                "No Orders",
                "No orders match the selected criteria"
            )
            return
        
        # Confirmation
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete {count} order(s)?\n\n"
            "This action cannot be undone!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.deleted_count = self.order_manager.delete_orders(criteria)
            self.accept()


class MessageSendThread(QThread):
    """Thread for sending messages without blocking UI"""
    finished = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, signal_handler, recipient, message, attachments=None):
        super().__init__()
        self.signal_handler = signal_handler
        self.recipient = recipient
        self.message = message
        self.attachments = attachments
    
    def run(self):
        """Send message in background"""
        try:
            success = self.signal_handler.send_message(
                self.recipient,
                self.message,
                self.attachments
            )
            if success:
                self.finished.emit(True, "Message sent successfully")
            else:
                self.finished.emit(False, "Failed to send message")
        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}")


class MessagesTab(QWidget):
    """Messaging tab with conversation list and chat window"""
    
    def __init__(self, signal_handler: SignalHandler, contact_manager, message_manager, seller_manager, product_manager=None):
        super().__init__()
        self.signal_handler = signal_handler
        self.contact_manager = contact_manager
        self.message_manager = message_manager
        self.seller_manager = seller_manager
        self.product_manager = product_manager
        self.conversations = {}  # Dict to store conversations
        self.conversations_cache = {}  # Cache for conversation data
        self.current_recipient = None
        self.my_signal_id = None
        self.current_messages = []  # Store message objects for current conversation
        
        # Get seller's Signal ID
        seller = self.seller_manager.get_seller(1)
        if seller:
            self.my_signal_id = seller.signal_id
        
        layout = QVBoxLayout()
        
        # Header with compose button
        header_layout = QHBoxLayout()
        header = QLabel("Messages")
        header.setFont(QFont("Arial", 16, QFont.Bold))
        header_layout.addWidget(header)
        
        compose_btn = QPushButton("Compose Message")
        compose_btn.clicked.connect(self.compose_message)
        header_layout.addWidget(compose_btn)
        
        message_contact_btn = QPushButton("Message Contact")
        message_contact_btn.clicked.connect(self.message_from_contacts)
        header_layout.addWidget(message_contact_btn)
        
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Main splitter for conversations and chat
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel: Conversations list
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search conversations...")
        self.search_input.textChanged.connect(self.filter_conversations)
        left_layout.addWidget(self.search_input)
        
        # Conversations list
        self.conversations_list = QListWidget()
        self.conversations_list.itemClicked.connect(self.load_conversation)
        self.conversations_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.conversations_list.customContextMenuRequested.connect(self.show_conversation_context_menu)
        left_layout.addWidget(self.conversations_list)
        
        left_panel.setLayout(left_layout)
        splitter.addWidget(left_panel)
        
        # Right panel: Chat window
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Chat header
        self.chat_header = QLabel("Select a conversation")
        self.chat_header.setFont(QFont("Arial", 12, QFont.Bold))
        self.chat_header.setStyleSheet("padding: 10px; background: #f0f0f0;")
        right_layout.addWidget(self.chat_header)
        
        # Message history
        self.message_history = QTextEdit()
        self.message_history.setReadOnly(True)
        self.message_history.setContextMenuPolicy(Qt.CustomContextMenu)
        self.message_history.customContextMenuRequested.connect(self.show_message_context_menu)
        right_layout.addWidget(self.message_history)
        
        # Quick actions
        quick_layout = QHBoxLayout()
        send_product_btn = QPushButton("Send Product")
        send_catalog_btn = QPushButton("Send Catalog")
        attach_image_btn = QPushButton("Attach Image")
        
        send_product_btn.clicked.connect(self.send_product)
        send_catalog_btn.clicked.connect(self.send_catalog)
        attach_image_btn.clicked.connect(self.attach_image)
        
        quick_layout.addWidget(send_product_btn)
        quick_layout.addWidget(send_catalog_btn)
        quick_layout.addWidget(attach_image_btn)
        quick_layout.addStretch()
        right_layout.addLayout(quick_layout)
        
        # Message input
        message_input_layout = QHBoxLayout()
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type a message...")
        self.message_input.returnPressed.connect(self.send_message)
        
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send_message)
        
        message_input_layout.addWidget(self.message_input)
        message_input_layout.addWidget(self.send_btn)
        right_layout.addLayout(message_input_layout)
        
        right_panel.setLayout(right_layout)
        splitter.addWidget(right_panel)
        
        # Set splitter sizes
        splitter.setSizes([300, 700])
        
        layout.addWidget(splitter)
        self.setLayout(layout)
        
        # Register message callback
        self.signal_handler.register_message_callback(self.handle_incoming_message)
        
        # Start listening for messages
        self.signal_handler.start_listening()
        
        # Load initial conversations
        self.load_conversations()
        
        self.attachment_path = None
        self.send_thread = None  # Thread for async message sending
    
    @staticmethod
    def _format_product_id(product_id: Optional[str]) -> str:
        """
        Format product ID consistently
        
        Args:
            product_id: Product ID to format
            
        Returns:
            Formatted product ID string
        """
        if not product_id:
            return "N/A"
        
        # Add # prefix if not already present
        if not product_id.startswith('#'):
            return f"#{product_id}"
        
        return product_id
    
    def _resolve_image_path(self, image_path: str) -> Optional[str]:
        """
        Resolve image path by checking multiple common locations.
        Handles both relative and absolute paths.
        
        Args:
            image_path: Image path from database (may be relative)
            
        Returns:
            Absolute path if file found, None otherwise
        """
        if not image_path:
            return None
        
        # If already absolute and exists, return it
        if os.path.isabs(image_path):
            if os.path.exists(image_path) and os.path.isfile(image_path):
                return image_path
            return None
        
        # Relative path - search common directories
        base_dir = os.getcwd()
        
        for search_dir in COMMON_IMAGE_SEARCH_DIRS:
            full_path = os.path.join(base_dir, search_dir, image_path)
            if os.path.exists(full_path) and os.path.isfile(full_path):
                return full_path
        
        return None
    
    def _optimize_image_for_signal(self, image_path: str, max_size_kb: int = 800) -> str:
        """
        Optimize image for Signal sending - compress and resize if needed.
        
        Args:
            image_path: Path to original image
            max_size_kb: Maximum file size in KB (default 800KB)
            
        Returns:
            Path to optimized image (or original if already optimal)
        """
        try:
            from PIL import Image
            import tempfile
            
            # Check current size
            file_size_kb = os.path.getsize(image_path) / 1024
            file_ext = os.path.splitext(image_path)[1].lower()
            
            print(f"  📊 Original: {file_size_kb:.1f}KB, Format: {file_ext}")
            
            # If already small and JPG, use as-is
            if file_size_kb <= max_size_kb and file_ext in ['.jpg', '.jpeg']:
                print(f"  ✓ Image already optimized")
                return image_path
            
            # Open and optimize
            img = Image.open(image_path)
            
            # Convert RGBA to RGB if needed (for PNG with transparency)
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            # Resize if too large (max 1920px on longest side)
            max_dimension = 1920
            if img.width > max_dimension or img.height > max_dimension:
                ratio = max_dimension / max(img.width, img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                print(f"  📐 Resized to: {new_size[0]}x{new_size[1]}")
            
            # Save as optimized JPG
            optimized_path = os.path.join(
                tempfile.gettempdir(),
                f"signal_opt_{os.path.basename(image_path).rsplit('.', 1)[0]}.jpg"
            )
            
            # Start with quality 85, reduce if still too large
            quality = 85
            while quality >= 60:
                img.save(optimized_path, 'JPEG', quality=quality, optimize=True)
                new_size_kb = os.path.getsize(optimized_path) / 1024
                
                if new_size_kb <= max_size_kb or quality == 60:
                    print(f"  📉 Optimized: {file_size_kb:.1f}KB → {new_size_kb:.1f}KB (quality={quality})")
                    return optimized_path
                
                quality -= 5
            
            return optimized_path
            
        except ImportError:
            print(f"  ⚠️  PIL/Pillow not installed - cannot optimize images")
            print(f"     Install with: pip install Pillow")
            return image_path
        except Exception as e:
            print(f"  ⚠️  Image optimization failed: {e}")
            print(f"     Using original image")
            return image_path
    
    @staticmethod
    def _format_message_display(msg, display_name: str) -> str:
        """
        Format a message for display in the message history
        
        Args:
            msg: Message object
            display_name: Display name for the other party
            
        Returns:
            Formatted message string
        """
        timestamp = msg.sent_at.strftime("%H:%M") if msg.sent_at else "??:??"
        sender_name = "You" if msg.is_outgoing else display_name
        text = msg.message_body or "[Attachment]"
        return f"[{timestamp}] {sender_name}: {text}\n"
    
    def load_conversations(self, force_refresh=False):
        """Load conversation list from database with caching"""
        self.conversations_list.clear()
        
        if not self.my_signal_id:
            item = QListWidgetItem("No Signal ID configured")
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
            self.conversations_list.addItem(item)
            return
        
        # Get all conversations from database (use cache if available)
        if force_refresh or not self.conversations_cache:
            self.conversations_cache = self.message_manager.get_all_conversations(self.my_signal_id)
        
        conversations = self.conversations_cache
        
        if not conversations:
            item = QListWidgetItem("No conversations yet")
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
            self.conversations_list.addItem(item)
        else:
            for contact_id, conv_data in conversations.items():
                # Try to get contact name
                contact = self.contact_manager.get_contact_by_signal_id(contact_id)
                display_name = contact.name if contact else contact_id
                
                last_msg = conv_data['last_message'][:30] if conv_data['last_message'] else ''
                item = QListWidgetItem(f"{display_name} - {last_msg}...")
                item.setData(Qt.UserRole, contact_id)
                self.conversations_list.addItem(item)
    
    def filter_conversations(self, text):
        """Filter conversations based on search text"""
        search_text = text.lower()
        for i in range(self.conversations_list.count()):
            item = self.conversations_list.item(i)
            if search_text in item.text().lower():
                item.setHidden(False)
            else:
                item.setHidden(True)
    
    def load_conversation(self, item):
        """Load selected conversation from database"""
        if not item or not item.flags() & Qt.ItemIsSelectable:
            return
        
        recipient = item.data(Qt.UserRole)
        if recipient and self.my_signal_id:
            self.current_recipient = recipient
            
            # Try to get contact name
            contact = self.contact_manager.get_contact_by_signal_id(recipient)
            display_name = contact.name if contact else recipient
            self.chat_header.setText(f"Chat with {display_name}")
            
            # Load message history from database
            self.message_history.clear()
            messages = self.message_manager.get_conversation(recipient, self.my_signal_id)
            
            # Store messages for deletion feature
            self.current_messages = messages
            
            for msg in messages:
                self.message_history.append(self._format_message_display(msg, display_name))
    
    def compose_message(self):
        """Open compose message dialog"""
        dialog = ComposeMessageDialog(
            self.signal_handler,
            message_manager=self.message_manager,
            contact_manager=self.contact_manager,
            my_signal_id=self.my_signal_id,
            parent=self
        )
        if dialog.exec_() == QDialog.Accepted:
            self.load_conversations(force_refresh=True)
    
    def message_from_contacts(self):
        """Open contact picker and start conversation"""
        dialog = ContactPickerDialog(self.contact_manager, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            contact = dialog.get_selected_contact()
            if contact:
                # Set current recipient and load conversation
                self.current_recipient = contact.signal_id
                self.chat_header.setText(f"Chat with {contact.name}")
                
                # Load message history
                self.message_history.clear()
                messages = self.message_manager.get_conversation(contact.signal_id, self.my_signal_id)
                
                # Store messages for deletion feature
                self.current_messages = messages
                
                for msg in messages:
                    self.message_history.append(self._format_message_display(msg, contact.name))
                
                # Focus on message input
                self.message_input.setFocus()
    
    def send_message(self):
        """Send message to current recipient using background thread"""
        if not self.current_recipient:
            QMessageBox.warning(self, "No Recipient", "Please select a conversation first")
            return
        
        message = self.message_input.text().strip()
        if not message and not self.attachment_path:
            return
        
        # Disable send button and show loading state
        self.send_btn.setEnabled(False)
        self.send_btn.setText("Sending...")
        
        # Store message text for later use
        message_text = message
        
        # Create and start send thread
        attachments = [self.attachment_path] if self.attachment_path else None
        self.send_thread = MessageSendThread(
            self.signal_handler,
            self.current_recipient,
            message,
            attachments
        )
        self.send_thread.finished.connect(lambda success, msg: self.on_message_sent(success, msg, message_text))
        self.send_thread.start()
    
    def on_message_sent(self, success, status_message, message_text):
        """Handle message send completion"""
        # Re-enable send button
        self.send_btn.setEnabled(True)
        self.send_btn.setText("Send")
        
        if success:
            # Add to message history immediately (UI update)
            timestamp = datetime.now().strftime("%H:%M")
            self.message_history.append(f"[{timestamp}] You: {message_text}\n")
            self.message_input.clear()
            self.attachment_path = None
            
            # Save to database in background (non-blocking)
            if self.my_signal_id:
                QTimer.singleShot(0, lambda: self._save_message_to_db(message_text))
        else:
            QMessageBox.warning(self, "Send Failed", status_message)
        
        # Clean up thread
        if self.send_thread:
            self.send_thread.finished.disconnect()
            self.send_thread.deleteLater()
            self.send_thread = None
    
    def _save_message_to_db(self, message_text):
        """Save message to database asynchronously"""
        try:
            self.message_manager.add_message(
                sender_signal_id=self.my_signal_id,
                recipient_signal_id=self.current_recipient,
                message_body=message_text,
                is_outgoing=True
            )
            # Ensure contact exists
            self.contact_manager.get_or_create_contact(self.current_recipient)
            # Refresh conversations list
            self.load_conversations(force_refresh=True)
        except Exception as e:
            print(f"Error saving message to database: {e}")
            # Show warning to user if database save fails
            QMessageBox.warning(
                self, 
                "Database Error", 
                "Message was sent but could not be saved to history."
            )
    
    def send_product(self):
        """Open product picker and send product info"""
        if not self.current_recipient:
            QMessageBox.warning(self, "No Recipient", "Please select a conversation first")
            return
        
        if not self.product_manager:
            QMessageBox.warning(self, "Error", "Product manager not available")
            return
        
        dialog = ProductPickerDialog(self.product_manager, self)
        if dialog.exec_() == QDialog.Accepted:
            products = dialog.get_selected_products()
            
            if not products:
                QMessageBox.warning(self, "No Selection", "Please select at least one product")
                return
            
            # Send each selected product
            sent_count = 0
            for product in products:
                # Format product message with ID
                product_id_str = self._format_product_id(product.product_id)
                message = f"""━━━━━━━━━━━━━━━━━
{product_id_str} - {product.name}
━━━━━━━━━━━━━━━━━
{product.description}

💰 Price: {product.price} {product.currency}
📊 Stock: {product.stock} available
🏷️ Category: {product.category or 'N/A'}
"""
                
                # CRITICAL: Attach product image
                attachments = []
                if product.image_path and os.path.exists(product.image_path):
                    attachments.append(product.image_path)
                else:
                    QMessageBox.warning(
                        self, 
                        "No Image", 
                        f"Product '{product.name}' has no image. Sending text only."
                    )
                
                # Send via Signal
                try:
                    success = self.signal_handler.send_message(
                        recipient=self.current_recipient,
                        message=message,
                        attachments=attachments if attachments else None
                    )
                    
                    if success:
                        sent_count += 1
                        
                        # Save to message history
                        if self.my_signal_id:
                            try:
                                self.message_manager.add_message(
                                    sender_signal_id=self.my_signal_id,
                                    recipient_signal_id=self.current_recipient,
                                    message_body=message,
                                    is_outgoing=True
                                )
                                
                                # Update UI
                                timestamp = datetime.now().strftime("%H:%M")
                                self.message_history.append(f"[{timestamp}] You: {message}\n")
                            except Exception as e:
                                print(f"Error saving product message: {e}")
                except Exception as e:
                    print(f"Error sending product {product.name}: {e}")
            
            if sent_count > 0:
                QMessageBox.information(self, "Success", f"Sent {sent_count} product(s)")
                self.load_conversations(force_refresh=True)
            else:
                QMessageBox.warning(self, "Failed", "Failed to send products")
    
    def send_catalog(self):
        """Send product catalog to current recipient with robust error handling"""
        if not self.current_recipient:
            QMessageBox.warning(self, "No Recipient", "Please select a conversation first.")
            return
        
        if not self.product_manager:
            QMessageBox.warning(self, "Error", "Product manager not available")
            return
        
        # Get all active products
        products = self.product_manager.list_products(active_only=True)
        
        if not products:
            QMessageBox.information(self, "No Products", "No active products to send.")
            return
        
        total_products = len(products)
        
        # Send catalog header
        header = f"🛍️ PRODUCT CATALOG ({total_products} items)\n"
        try:
            self.signal_handler.send_message(
                recipient=self.current_recipient,
                message=header
            )
        except Exception as e:
            print(f"Failed to send catalog header: {e}")
        
        sent_count = 0
        failed_count = 0
        missing_images = []
        
        # Progress dialog
        progress = QProgressDialog(
            f"Sending catalog...",
            "Cancel",
            0,
            total_products,
            self
        )
        progress.setWindowModality(Qt.WindowModal)
        progress.setWindowTitle("Sending Catalog")
        
        # Send each product
        for index, product in enumerate(products, 1):
            # Update progress
            progress.setValue(index - 1)
            progress.setLabelText(f"Sending product {index}/{total_products}: {product.name}")
            
            # Check if user cancelled
            if progress.wasCanceled():
                QMessageBox.information(
                    self,
                    "Cancelled",
                    f"Catalog sending cancelled. Sent {sent_count}/{total_products} products."
                )
                return
            
            product_id_str = self._format_product_id(product.product_id)
            message = f"""━━━━━━━━━━━━━━━━━
{product_id_str} - {product.name}
━━━━━━━━━━━━━━━━━
{product.description}

💰 Price: {product.price} {product.currency}
📊 Stock: {product.stock} available
🏷️ Category: {product.category or 'N/A'}
"""
            
            # Resolve and optimize image
            attachments = []
            if product.image_path:
                resolved_path = self._resolve_image_path(product.image_path)
                
                if resolved_path:
                    # Optimize image before sending
                    optimized_path = self._optimize_image_for_signal(resolved_path)
                    attachments.append(optimized_path)
                else:
                    missing_images.append(product.name)
            
            # Send with exponential backoff retry logic
            max_retries = 5
            success = False
            
            for attempt in range(1, max_retries + 1):
                try:
                    result = self.signal_handler.send_message(
                        recipient=self.current_recipient,
                        message=message.strip(),
                        attachments=attachments if attachments else None
                    )
                    
                    if result:
                        sent_count += 1
                        success = True
                        
                        # Save to message history
                        if self.my_signal_id:
                            try:
                                self.message_manager.add_message(
                                    sender_signal_id=self.my_signal_id,
                                    recipient_signal_id=self.current_recipient,
                                    message_body=message.strip(),
                                    is_outgoing=True
                                )
                            except Exception as e:
                                print(f"Failed to save message to history: {e}")
                        
                        break  # Exit retry loop
                        
                    else:
                        print(f"Attempt {attempt} for {product.name} failed")
                        if attempt < max_retries:
                            # Exponential backoff: 3s, 6s, 12s, 24s, 48s (capped at 60s)
                            retry_delay = min(3 * (2 ** (attempt - 1)), 60)
                            time.sleep(retry_delay)
                            
                except Exception as e:
                    print(f"Error on attempt {attempt} for {product.name}: {e}")
                    
                    if attempt < max_retries:
                        # Exponential backoff: 3s, 6s, 12s, 24s, 48s (capped at 60s)
                        retry_delay = min(3 * (2 ** (attempt - 1)), 60)
                        time.sleep(retry_delay)
            
            if not success:
                # Try one final time without image (text-only fallback)
                if attachments:
                    print(f"  📝 Attempting text-only fallback (no image) for {product.name}...")
                    try:
                        result = self.signal_handler.send_message(
                            recipient=self.current_recipient,
                            message=message.strip(),
                            attachments=None  # No image
                        )
                        if result:
                            print(f"  ✅ Text-only version sent successfully for {product.name}")
                            sent_count += 1
                            success = True
                            
                            # Save to message history
                            if self.my_signal_id:
                                try:
                                    self.message_manager.add_message(
                                        sender_signal_id=self.my_signal_id,
                                        recipient_signal_id=self.current_recipient,
                                        message_body=message.strip(),
                                        is_outgoing=True
                                    )
                                except Exception as e:
                                    print(f"Failed to save message to history: {e}")
                        else:
                            print(f"  ✗ Text-only fallback also failed for {product.name}")
                            failed_count += 1
                    except Exception as e:
                        print(f"  ✗ Text-only fallback error for {product.name}: {e}")
                        failed_count += 1
                else:
                    failed_count += 1
                    
                if not success:
                    print(f"Product {product.name} failed after {max_retries} attempts")
            
            # Delay between products (already correct at 2.5s)
            if index < total_products:
                time.sleep(2.5)
        
        progress.setValue(total_products)
        
        # Show results
        result_msg = f"Catalog Send Complete\n\n"
        result_msg += f"✅ Successfully sent: {sent_count}/{total_products} products\n"
        
        if failed_count > 0:
            result_msg += f"❌ Failed: {failed_count} products\n"
        
        if missing_images:
            result_msg += f"\n⚠ Images not found for:\n"
            result_msg += "\n".join(f"  • {name}" for name in missing_images)
        
        if sent_count == total_products:
            QMessageBox.information(self, "Success", result_msg)
        elif sent_count > 0:
            QMessageBox.warning(self, "Partial Success", result_msg)
        else:
            QMessageBox.critical(self, "Failed", result_msg)
        
        self.load_conversations(force_refresh=True)
    
    def attach_image(self):
        """Attach image to message"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            "",
            "Image Files (*.png *.jpg *.jpeg)"
        )
        
        if file_path:
            self.attachment_path = file_path
            QMessageBox.information(self, "Image Attached", f"Image: {os.path.basename(file_path)}")
    
    def handle_incoming_message(self, message):
        """Handle incoming message from Signal"""
        sender = message.get('sender', '')
        text = message.get('text', '')
        timestamp = datetime.fromtimestamp(message.get('timestamp', 0) / 1000).strftime("%H:%M")
        
        # Save to database
        if self.my_signal_id and sender:
            self.message_manager.add_message(
                sender_signal_id=sender,
                recipient_signal_id=self.my_signal_id,
                message_body=text,
                is_outgoing=False
            )
            # Ensure contact exists
            self.contact_manager.get_or_create_contact(sender)
        
        # Add to conversations
        if sender not in self.conversations:
            self.conversations[sender] = []
            # Reload conversations to show new one
            self.load_conversations(force_refresh=True)
        
        self.conversations[sender].append(message)
        
        # Update current conversation if it's the active one
        if self.current_recipient == sender:
            self.message_history.append(f"[{timestamp}] {sender}: {text}\n")
    
    def show_conversation_context_menu(self, position):
        """Show context menu for conversation list"""
        item = self.conversations_list.itemAt(position)
        if not item or not (item.flags() & Qt.ItemIsSelectable):
            return
        
        contact_id = item.data(Qt.UserRole)
        if not contact_id:
            return
        
        menu = QMenu(self)
        delete_action = QAction("🗑️ Delete Conversation", self)
        delete_action.triggered.connect(lambda: self.delete_conversation(contact_id))
        menu.addAction(delete_action)
        
        menu.exec_(self.conversations_list.mapToGlobal(position))
    
    def delete_conversation(self, contact_id):
        """Delete a conversation"""
        reply = QMessageBox.question(
            self,
            "Delete Conversation",
            f"Are you sure you want to delete this conversation?\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.message_manager.delete_conversation(contact_id, self.my_signal_id):
                # Clear chat if this was the active conversation
                if self.current_recipient == contact_id:
                    self.current_recipient = None
                    self.chat_header.setText("Select a conversation")
                    self.message_history.clear()
                
                # Reload conversations
                self.load_conversations(force_refresh=True)
                QMessageBox.information(self, "Success", "Conversation deleted")
            else:
                QMessageBox.warning(self, "Error", "Failed to delete conversation")
    
    def show_message_context_menu(self, position):
        """Show context menu for message history"""
        menu = QMenu(self)
        
        copy_action = QAction("Copy", self)
        copy_action.triggered.connect(self.copy_selected_text)
        menu.addAction(copy_action)
        
        if self.current_recipient:
            menu.addSeparator()
            
            # Add delete individual message option
            cursor = self.message_history.textCursor()
            if cursor.hasSelection() or cursor.block().text():
                delete_msg_action = QAction("Delete This Message", self)
                delete_msg_action.triggered.connect(self.delete_selected_message)
                menu.addAction(delete_msg_action)
            
            menu.addSeparator()
            clear_action = QAction("Clear All Messages", self)
            clear_action.triggered.connect(self.clear_all_messages)
            menu.addAction(clear_action)
        
        menu.exec_(self.message_history.mapToGlobal(position))
    
    def copy_selected_text(self):
        """Copy selected text to clipboard"""
        cursor = self.message_history.textCursor()
        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            QApplication.clipboard().setText(selected_text)
    
    def delete_selected_message(self):
        """Delete individual message at cursor position"""
        if not self.current_recipient or not self.current_messages:
            return
        
        # Get cursor position and block text
        text_cursor = self.message_history.textCursor()
        text_cursor.select(text_cursor.BlockUnderCursor)
        block_text = text_cursor.selectedText().strip()
        
        if not block_text:
            QMessageBox.warning(self, "No Message", "No message selected")
            return
        
        # Find matching message in current_messages
        # Get contact name for formatting
        contact = self.contact_manager.get_contact_by_signal_id(self.current_recipient)
        display_name = contact.name if contact else self.current_recipient
        
        message_to_delete = None
        for msg in self.current_messages:
            # Use helper method to format message text
            expected_text = self._format_message_display(msg, display_name).strip()
            
            if expected_text in block_text:
                message_to_delete = msg
                break
                break
        
        if not message_to_delete:
            QMessageBox.warning(self, "Error", "Could not identify message")
            return
        
        # Only allow deleting outgoing messages (seller's messages)
        if not message_to_delete.is_outgoing:
            QMessageBox.warning(
                self, 
                "Cannot Delete", 
                "You can only delete messages you sent, not received messages."
            )
            return
        
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Delete Message",
            "Are you sure you want to delete this message?\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.message_manager.delete_message(message_to_delete.id):
                # Reload conversation to show updated message list
                self.load_conversation_refresh()
                QMessageBox.information(self, "Success", "Message deleted")
            else:
                QMessageBox.warning(self, "Error", "Failed to delete message")
    
    def load_conversation_refresh(self):
        """Reload current conversation without changing selection"""
        if not self.current_recipient or not self.my_signal_id:
            return
        
        # Get contact name
        contact = self.contact_manager.get_contact_by_signal_id(self.current_recipient)
        display_name = contact.name if contact else self.current_recipient
        
        # Reload message history from database
        self.message_history.clear()
        messages = self.message_manager.get_conversation(self.current_recipient, self.my_signal_id)
        
        # Store messages for deletion feature
        self.current_messages = messages
        
        for msg in messages:
            self.message_history.append(self._format_message_display(msg, display_name))
        
        # Refresh conversation list
        self.load_conversations(force_refresh=True)
    
    def clear_all_messages(self):
        """Clear all messages in current conversation"""
        if not self.current_recipient:
            return
        
        reply = QMessageBox.question(
            self,
            "Clear All Messages",
            "Are you sure you want to clear all messages in this conversation?\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.message_manager.delete_conversation(self.current_recipient, self.my_signal_id):
                self.message_history.clear()
                self.load_conversations(force_refresh=True)
                QMessageBox.information(self, "Success", "All messages cleared")
            else:
                QMessageBox.warning(self, "Error", "Failed to clear messages")


class SettingsTab(QWidget):
    """Settings tab with configuration options"""
    
    def __init__(self, seller_manager: SellerManager, signal_handler: SignalHandler):
        super().__init__()
        self.seller_manager = seller_manager
        self.signal_handler = signal_handler
        
        # Main layout with scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("Settings")
        header.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(header)
        
        # Section 1: Signal Account Info
        signal_group = QGroupBox("Signal Account")
        signal_layout = QVBoxLayout()
        
        seller = self.seller_manager.get_seller(1)
        
        # Display current number
        current_number_layout = QHBoxLayout()
        current_number_layout.addWidget(QLabel("Current Number:"))
        self.phone_label = QLabel(seller.signal_id if seller and seller.signal_id else "Not linked")
        current_number_layout.addWidget(self.phone_label)
        current_number_layout.addStretch()
        signal_layout.addLayout(current_number_layout)
        
        # Status indicator
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("Status:"))
        if seller and seller.signal_id:
            self.status_label = QLabel("✅ Linked")
        else:
            self.status_label = QLabel("❌ Not Linked")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        signal_layout.addLayout(status_layout)
        
        # Buttons
        signal_buttons = QHBoxLayout()
        relink_btn = QPushButton("Change Number / Re-link")
        relink_btn.clicked.connect(self.relink_signal)
        test_signal_btn = QPushButton("Test Connection")
        test_signal_btn.clicked.connect(self.test_signal_connection)
        test_message_btn = QPushButton("Test Message Receiving")
        test_message_btn.clicked.connect(self.test_message_receiving)
        unlink_btn = QPushButton("Unlink")
        unlink_btn.clicked.connect(self.unlink_signal)
        
        signal_buttons.addWidget(relink_btn)
        signal_buttons.addWidget(test_signal_btn)
        signal_buttons.addWidget(test_message_btn)
        signal_buttons.addWidget(unlink_btn)
        signal_buttons.addStretch()
        signal_layout.addLayout(signal_buttons)
        
        signal_group.setLayout(signal_layout)
        layout.addWidget(signal_group)
        
        # Section 2: Wallet Configuration
        wallet_group = QGroupBox("Monero Wallet")
        wallet_layout = QVBoxLayout()
        
        # Display wallet path
        if seller and seller.wallet_path:
            wallet_path_display = seller.wallet_path
            if len(wallet_path_display) > 50:
                wallet_path_display = "..." + wallet_path_display[-50:]
            wallet_layout.addWidget(QLabel(f"Wallet Path: {wallet_path_display}"))
        else:
            wallet_layout.addWidget(QLabel("Wallet Path: Not configured"))
        
        # Display current default node
        node_manager = NodeManager(self.seller_manager.db)
        default_node = node_manager.get_default_node()
        if default_node:
            protocol = "https" if default_node.use_ssl else "http"
            node_display = f"{default_node.node_name} ({protocol}://{default_node.address}:{default_node.port})"
            wallet_layout.addWidget(QLabel(f"Default Node: {node_display}"))
        else:
            wallet_layout.addWidget(QLabel("Default Node: Not configured"))
        
        wallet_btn_layout = QHBoxLayout()
        wallet_settings_btn = QPushButton("Wallet Settings")
        wallet_settings_btn.clicked.connect(self.open_wallet_settings)
        wallet_btn_layout.addWidget(wallet_settings_btn)
        
        # New Wallet Button (with warning styling)
        new_wallet_btn = QPushButton("Create New Wallet")
        new_wallet_btn.setStyleSheet("background-color: #ff6b6b; color: white; font-weight: bold;")
        new_wallet_btn.clicked.connect(self.create_new_wallet)
        wallet_btn_layout.addWidget(new_wallet_btn)
        
        wallet_btn_layout.addStretch()
        wallet_layout.addLayout(wallet_btn_layout)
        
        wallet_group.setLayout(wallet_layout)
        layout.addWidget(wallet_group)
        
        # Section 3: Shop Settings
        shop_group = QGroupBox("Shop Settings")
        shop_layout = QFormLayout()
        
        currency_combo = QComboBox()
        currency_combo.addItems(SUPPORTED_CURRENCIES)
        if seller:
            index = currency_combo.findText(seller.default_currency)
            if index >= 0:
                currency_combo.setCurrentIndex(index)
        shop_layout.addRow("Default Currency:", currency_combo)
        
        expiration_spin = QSpinBox()
        expiration_spin.setRange(5, 1440)
        expiration_spin.setValue(ORDER_EXPIRATION_MINUTES)
        expiration_spin.setSuffix(" minutes")
        shop_layout.addRow("Order Expiration:", expiration_spin)
        
        stock_threshold_spin = QSpinBox()
        stock_threshold_spin.setRange(0, 100)
        stock_threshold_spin.setValue(LOW_STOCK_THRESHOLD)
        shop_layout.addRow("Low Stock Threshold:", stock_threshold_spin)
        
        confirmations_spin = QSpinBox()
        confirmations_spin.setRange(1, 20)
        confirmations_spin.setValue(MONERO_CONFIRMATIONS_REQUIRED)
        shop_layout.addRow("Payment Confirmations:", confirmations_spin)
        
        shop_group.setLayout(shop_layout)
        layout.addWidget(shop_group)
        
        # Section 4: Commission Info
        commission_group = QGroupBox("Commission Information (Read-Only)")
        commission_layout = QVBoxLayout()
        
        commission_layout.addWidget(QLabel(f"Commission Rate: {COMMISSION_RATE * 100:.0f}% on all sales"))
        commission_layout.addWidget(QLabel("Commission is automatically calculated and deducted from each sale."))
        commission_layout.addWidget(QLabel("For every sale: 93% goes to you, 7% goes to the bot creator."))
        
        commission_group.setLayout(commission_layout)
        layout.addWidget(commission_group)
        
        # Save button
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)
        
        layout.addStretch()
        scroll_content.setLayout(layout)
        scroll.setWidget(scroll_content)
        
        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)
        
        # Store widgets for saving
        self.currency_combo = currency_combo
        self.expiration_spin = expiration_spin
        self.stock_threshold_spin = stock_threshold_spin
        self.confirmations_spin = confirmations_spin
    
    def save_settings(self):
        """Save settings changes"""
        try:
            seller = self.seller_manager.get_seller(1)
            if seller:
                seller.default_currency = self.currency_combo.currentText()
                self.seller_manager.update_seller(seller)
                QMessageBox.information(self, "Success", "Settings saved successfully!")
            else:
                QMessageBox.warning(self, "Error", "Seller not found")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")
    
    def relink_signal(self):
        """Open re-link dialog"""
        dialog = SignalRelinkDialog(self.signal_handler, self)
        if dialog.exec_() == QDialog.Accepted:
            new_phone = dialog.get_new_phone()
            if new_phone:
                # Update database with new phone
                seller = self.seller_manager.get_seller(1)
                seller.signal_id = new_phone
                self.seller_manager.update_seller(seller)
                self.phone_label.setText(new_phone)
                self.status_label.setText("✅ Linked")
                QMessageBox.information(
                    self,
                    "Success",
                    "Signal account re-linked successfully!"
                )

    def test_signal_connection(self):
        """Test Signal connection"""
        try:
            # Try sending a test message to self
            if not self.signal_handler.phone_number:
                QMessageBox.warning(
                    self, 
                    "Not Configured", 
                    "Signal not configured. Please link an account first."
                )
                return
                
            result = self.signal_handler.send_message(
                self.signal_handler.phone_number,
                "Signal connection test"
            )
            if result:
                QMessageBox.information(self, "Success", "Signal connection is working!")
            else:
                QMessageBox.warning(
                    self, 
                    "Failed", 
                    "Signal connection test failed.\n\n"
                    "Please check your Signal configuration:\n"
                    "- Ensure signal-cli is installed and configured\n"
                    "- Verify your account is properly linked\n"
                    "- Try re-linking your account"
                )
        except Exception as e:
            QMessageBox.warning(
                self, 
                "Error", 
                f"Connection test failed: {e}\n\n"
                "Please verify signal-cli is installed and your account is linked."
            )
    
    def test_message_receiving(self):
        """Test if message receiving is working"""
        if not self.signal_handler:
            QMessageBox.warning(self, "Error", "Signal handler not initialized")
            return
        
        # Check if listener is running
        is_running = self.signal_handler.is_listening()
        
        if not is_running:
            reply = QMessageBox.question(
                self,
                "Listener Not Running",
                "Message listener is not running. Start it now?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.signal_handler.start_listening()
                QMessageBox.information(
                    self,
                    "Started",
                    "✅ Message listener started.\n\n"
                    "Send a test message to your Signal account from another device to verify it's working."
                )
        else:
            QMessageBox.information(
                self,
                "Listener Active",
                "✅ Message listener is running.\n\n"
                "Send a test message from another device to verify it's working.\n"
                "Incoming messages will appear in the Messages tab."
            )

    def unlink_signal(self):
        """Unlink Signal account"""
        reply = QMessageBox.question(
            self,
            "Confirm Unlink",
            "Are you sure you want to unlink your Signal account?\n"
            "You will need to re-link to send/receive messages.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            # Clear Signal data
            seller = self.seller_manager.get_seller(1)
            seller.signal_id = None
            self.seller_manager.update_seller(seller)
            self.phone_label.setText("Not linked")
            self.status_label.setText("❌ Not Linked")
            QMessageBox.information(self, "Unlinked", "Signal account unlinked")
    
    def open_wallet_settings(self):
        """Open comprehensive wallet settings dialog"""
        seller = self.seller_manager.get_seller(1)
        if not seller:
            QMessageBox.warning(self, "Error", "Seller not found")
            return
        
        dialog = WalletSettingsDialog(self.seller_manager, seller, self, dashboard=self)
        if dialog.exec_() == QDialog.Accepted:
            QMessageBox.information(
                self,
                "Settings Updated",
                "Wallet settings updated successfully."
            )
    
    def show_status(self, message: str):
        """Show status message (helper method for wallet creation)"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(message)
    
    def create_new_wallet(self):
        """Create new wallet with confirmation dialogs"""
        # Step 1: Warning confirmation
        warning = QMessageBox()
        warning.setIcon(QMessageBox.Warning)
        warning.setWindowTitle("Create New Wallet - WARNING")
        warning.setText("Creating a new wallet will:")
        warning.setInformativeText(
            "• Generate a NEW seed phrase\n"
            "• Create NEW wallet files\n"
            "• Your CURRENT wallet will be backed up\n"
            "• You will LOSE ACCESS to current wallet unless you have the seed\n\n"
            "Have you backed up your current wallet seed phrase?"
        )
        warning.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        warning.setDefaultButton(QMessageBox.Cancel)
        
        if warning.exec_() != QMessageBox.Yes:
            return
        
        # Step 2: Final confirmation
        confirm = QMessageBox()
        confirm.setIcon(QMessageBox.Question)
        confirm.setWindowTitle("Final Confirmation")
        confirm.setText("Are you absolutely sure?")
        confirm.setInformativeText("This action will backup and replace your wallet.")
        confirm.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        confirm.setDefaultButton(QMessageBox.No)
        
        if confirm.exec_() != QMessageBox.Yes:
            return
        
        # Step 3: Show backup creation
        try:
            from pathlib import Path
            from datetime import datetime
            import shutil
            
            self.show_status("Creating wallet backup...")
            # Backup existing wallet
            backup_name = f"wallet_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            wallet_dir = Path("data/wallet")
            backup_dir = wallet_dir / "backups" / backup_name
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy all wallet files
            for file in wallet_dir.glob("shop_wallet*"):
                shutil.copy2(file, backup_dir / file.name)
            
            self.show_status(f"Backup created: {backup_name}")
            
            # Step 4: Create new wallet
            self.show_status("Creating new wallet...")
            from ..core.wallet_setup import WalletSetupManager
            
            setup = WalletSetupManager(
                wallet_path=str(wallet_dir / "shop_wallet"),
                daemon_address="",
                daemon_port=0,
                password=""  # Empty password (matches existing setup)
            )
            
            # Create wallet and get seed phrase using RPC method
            success, seed, address = setup.create_wallet_with_seed()
            
            if not success:
                QMessageBox.critical(self, "Error", "Failed to create wallet")
                return
            
            if not seed:
                QMessageBox.critical(
                    self,
                    "Error",
                    "Wallet created but failed to retrieve seed phrase.\n"
                    "This is a critical error. Please check logs."
                )
                return
            
            # Step 5: Show seed phrase with save options
            self.show_new_wallet_seed(seed, address, backup_name)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create wallet: {e}")
            self.show_status("Wallet creation failed")
    
    def show_new_wallet_seed(self, seed: str, address: str, backup_name: str):
        """Show seed phrase with save options"""
        from datetime import datetime
        
        dialog = QDialog(self)
        dialog.setWindowTitle("New Wallet Created - SAVE YOUR SEED!")
        dialog.setModal(True)
        dialog.setMinimumWidth(700)
        
        layout = QVBoxLayout()
        
        # Warning header
        warning = QLabel("⚠️ CRITICAL: Save this seed phrase immediately!")
        warning.setStyleSheet("background-color: #ff6b6b; color: white; padding: 10px; font-weight: bold; font-size: 14px;")
        layout.addWidget(warning)
        
        # Seed phrase display
        seed_label = QLabel("Your 25-word seed phrase:")
        layout.addWidget(seed_label)
        
        seed_text = QTextEdit()
        seed_text.setPlainText(seed)
        seed_text.setReadOnly(True)
        seed_text.setStyleSheet("background-color: #f0f0f0; font-family: monospace; font-size: 12px;")
        seed_text.setMinimumHeight(100)
        layout.addWidget(seed_text)
        
        # Address display
        addr_label = QLabel("Wallet Address:")
        layout.addWidget(addr_label)
        
        addr_text = QLineEdit(address)
        addr_text.setReadOnly(True)
        layout.addWidget(addr_text)
        
        # Backup info
        backup_info = QLabel(f"Previous wallet backed up to: {backup_name}")
        backup_info.setStyleSheet("color: green;")
        layout.addWidget(backup_info)
        
        # Save buttons
        button_layout = QHBoxLayout()
        
        copy_btn = QPushButton("📋 Copy Seed to Clipboard")
        copy_btn.clicked.connect(lambda: self.copy_seed_to_clipboard(seed))
        
        save_btn = QPushButton("💾 Save to File")
        save_btn.clicked.connect(lambda: self.save_seed_to_file(seed, address))
        
        button_layout.addWidget(copy_btn)
        button_layout.addWidget(save_btn)
        layout.addLayout(button_layout)
        
        # Confirmation checkbox
        confirm_check = QCheckBox("I have saved my seed phrase in a safe place")
        layout.addWidget(confirm_check)
        
        # Close button (disabled until confirmed)
        close_btn = QPushButton("Close")
        close_btn.setEnabled(False)
        confirm_check.stateChanged.connect(lambda: close_btn.setEnabled(confirm_check.isChecked()))
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.exec_()
        
        # Restart wallet RPC with new wallet
        QMessageBox.information(self, "Restart Required", "Please restart the bot to use the new wallet.")
    
    def save_seed_to_file(self, seed: str, address: str):
        """Save seed phrase to file"""
        from datetime import datetime
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Seed Phrase",
            f"wallet_seed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt)"
        )
        
        if filename:
            with open(filename, 'w') as f:
                f.write(f"Wallet Seed Phrase\n")
                f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"\nAddress: {address}\n")
                f.write(f"\nSeed Phrase (25 words):\n")
                f.write(f"{seed}\n")
                f.write(f"\n⚠️ KEEP THIS FILE SECURE! Anyone with this seed can access your funds.\n")
            
            QMessageBox.information(self, "Saved", f"Seed phrase saved to:\n{filename}")
    
    def copy_seed_to_clipboard(self, seed_phrase: str):
        """Copy seed phrase to clipboard with auto-clear for security"""
        clipboard = QApplication.clipboard()
        clipboard.setText(seed_phrase)
        
        QMessageBox.information(
            self,
            "Copied",
            "Seed phrase copied to clipboard!\n\n"
            "⚠️ Paste it somewhere safe immediately.\n"
            "The clipboard will be cleared in 60 seconds for security."
        )
        
        # Clear clipboard after 60 seconds for security
        QTimer.singleShot(60000, lambda: clipboard.clear())



# Worker threads for async operations
class TestNodeWorker(QThread):
    """Worker thread for testing node connections"""
    finished = pyqtSignal(bool, str, float)  # success, message, response_time
    
    def __init__(self, node_config: MoneroNodeConfig):
        super().__init__()
        self.node_config = node_config
    
    def run(self):
        """Test node connection"""
        import time
        start_time = time.time()
        
        try:
            protocol = "https" if self.node_config.use_ssl else "http"
            url = f"{protocol}://{self.node_config.address}:{self.node_config.port}/json_rpc"
            
            payload = {
                "jsonrpc": "2.0",
                "id": "0",
                "method": "get_info"
            }
            
            auth = None
            if self.node_config.username and self.node_config.password:
                auth = (self.node_config.username, self.node_config.password)
            
            import requests
            response = requests.post(url, json=payload, auth=auth, timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if 'result' in data:
                    self.finished.emit(True, "Connection successful", response_time)
                else:
                    self.finished.emit(False, "Invalid response from node", response_time)
            else:
                self.finished.emit(False, f"HTTP {response.status_code}", response_time)
        except requests.exceptions.Timeout:
            response_time = time.time() - start_time
            self.finished.emit(False, "Connection timeout", response_time)
        except requests.exceptions.ConnectionError:
            response_time = time.time() - start_time
            self.finished.emit(False, "Connection refused", response_time)
        except Exception as e:
            response_time = time.time() - start_time
            self.finished.emit(False, str(e), response_time)


class ReconnectWalletWorker(QThread):
    """Worker thread for reconnecting wallet"""
    finished = pyqtSignal(bool, str)  # success, message
    progress = pyqtSignal(str)  # progress message
    
    def __init__(self, wallet: InHouseWallet, node_config: MoneroNodeConfig):
        super().__init__()
        self.wallet = wallet
        self.node_config = node_config
    
    def run(self):
        """Reconnect wallet to node"""
        try:
            self.progress.emit("Disconnecting from current node...")
            if self.wallet.wallet:
                self.wallet.disconnect()
            
            self.progress.emit("Connecting to new node...")
            self.wallet.daemon_address = self.node_config.address
            self.wallet.daemon_port = self.node_config.port
            self.wallet.use_ssl = self.node_config.use_ssl
            
            self.wallet.connect()
            
            # Note: refresh() is not needed. Wallet syncs automatically when connected.
            # The JSONRPCWallet automatically syncs on the next RPC call (e.g., get_balance()).
            # The JSONRPCWallet object does not have a refresh() method.
            
            self.finished.emit(True, "Wallet reconnected successfully")
        except Exception as e:
            self.finished.emit(False, f"Failed to reconnect: {str(e)}")


class RescanBlockchainWorker(QThread):
    """Worker thread for rescanning blockchain"""
    finished = pyqtSignal(bool, str)  # success, message
    progress = pyqtSignal(str)  # progress message
    
    def __init__(self, wallet: InHouseWallet, height: Optional[int] = None):
        super().__init__()
        self.wallet = wallet
        self.height = height
    
    def run(self):
        """Rescan blockchain"""
        try:
            if self.height:
                self.progress.emit(f"Rescanning from block {self.height}...")
            else:
                self.progress.emit("Rescanning blockchain...")
            
            self.wallet.rescan_blockchain(self.height)
            
            self.finished.emit(True, "Blockchain rescan completed")
        except Exception as e:
            self.finished.emit(False, f"Rescan failed: {str(e)}")


class WalletSettingsDialog(QDialog):
    """Comprehensive wallet settings dialog with tabs"""
    
    def __init__(self, seller_manager, seller, parent=None, dashboard=None):
        super().__init__(parent)
        self.seller_manager = seller_manager
        self.seller = seller
        self.dashboard = dashboard  # Reference to main dashboard
        self.node_manager = NodeManager(seller_manager.db)
        
        self.setWindowTitle("Wallet Settings")
        self.setModal(True)
        self.setMinimumSize(700, 500)
        
        layout = QVBoxLayout()
        
        # Create tab widget
        self.tabs = QTabWidget()
        
        # Tab 1: Connect & Sync
        self.connect_tab = self._create_connect_tab()
        self.tabs.addTab(self.connect_tab, "Connect && Sync")
        
        # Tab 2: Manage Nodes
        self.nodes_tab = self._create_nodes_tab()
        self.tabs.addTab(self.nodes_tab, "Manage Nodes")
        
        layout.addWidget(self.tabs)
        
        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _request_wallet_password(self):
        """Request wallet password from user"""
        password_dialog = WalletPasswordDialog(self)
        if password_dialog.exec_() != QDialog.Accepted:
            return None
        
        password = password_dialog.get_password()
        if not password:
            QMessageBox.warning(self, "Error", "Password is required")
            return None
        
        return password
    
    def _create_connect_tab(self):
        """Create Connect & Sync tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Reconnect section
        reconnect_group = QGroupBox("Reconnect to Node")
        reconnect_layout = QVBoxLayout()
        
        reconnect_info = QLabel("Reconnect the wallet to the current default node")
        reconnect_info.setWordWrap(True)
        reconnect_layout.addWidget(reconnect_info)
        
        reconnect_btn = QPushButton("Reconnect Now")
        reconnect_btn.clicked.connect(self.reconnect_wallet)
        reconnect_layout.addWidget(reconnect_btn)
        
        reconnect_group.setLayout(reconnect_layout)
        layout.addWidget(reconnect_group)
        
        # Rescan section
        rescan_group = QGroupBox("Rescan Blockchain")
        rescan_layout = QVBoxLayout()
        
        rescan_info = QLabel(
            "Rescan the blockchain to find missing transactions.\n"
            "Leave block height empty for full rescan (may take time)."
        )
        rescan_info.setWordWrap(True)
        rescan_layout.addWidget(rescan_info)
        
        height_layout = QHBoxLayout()
        height_layout.addWidget(QLabel("Block Height (optional):"))
        self.height_input = QLineEdit()
        self.height_input.setPlaceholderText("e.g., 2500000")
        height_layout.addWidget(self.height_input)
        height_layout.addStretch()
        rescan_layout.addLayout(height_layout)
        
        rescan_btn = QPushButton("Start Rescan")
        rescan_btn.clicked.connect(self.rescan_blockchain)
        rescan_layout.addWidget(rescan_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        rescan_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        rescan_layout.addWidget(self.progress_label)
        
        rescan_group.setLayout(rescan_layout)
        layout.addWidget(rescan_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_nodes_tab(self):
        """Create Manage Nodes tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Saved Nodes"))
        header_layout.addStretch()
        add_btn = QPushButton("Add New Node")
        add_btn.clicked.connect(self.add_node)
        header_layout.addWidget(add_btn)
        layout.addLayout(header_layout)
        
        # Nodes table
        self.nodes_table = QTableWidget()
        self.nodes_table.setColumnCount(6)
        self.nodes_table.setHorizontalHeaderLabels([
            "Name", "Address", "Port", "SSL", "Default", "Actions"
        ])
        self.nodes_table.horizontalHeader().setStretchLastSection(False)
        self.nodes_table.setColumnWidth(0, 150)
        self.nodes_table.setColumnWidth(1, 200)
        self.nodes_table.setColumnWidth(2, 60)
        self.nodes_table.setColumnWidth(3, 50)
        self.nodes_table.setColumnWidth(4, 60)
        self.nodes_table.setColumnWidth(5, 150)
        
        layout.addWidget(self.nodes_table)
        
        self.refresh_nodes_table()
        
        widget.setLayout(layout)
        return widget
    
    def refresh_nodes_table(self):
        """Refresh the nodes table"""
        nodes = self.node_manager.list_nodes()
        self.nodes_table.setRowCount(len(nodes))
        
        for row, node in enumerate(nodes):
            # Name
            self.nodes_table.setItem(row, 0, QTableWidgetItem(node.node_name))
            
            # Address
            self.nodes_table.setItem(row, 1, QTableWidgetItem(node.address))
            
            # Port
            self.nodes_table.setItem(row, 2, QTableWidgetItem(str(node.port)))
            
            # SSL
            ssl_text = "✓" if node.use_ssl else ""
            ssl_item = QTableWidgetItem(ssl_text)
            ssl_item.setTextAlignment(Qt.AlignCenter)
            self.nodes_table.setItem(row, 3, ssl_item)
            
            # Default
            default_text = "●" if node.is_default else ""
            default_item = QTableWidgetItem(default_text)
            default_item.setTextAlignment(Qt.AlignCenter)
            self.nodes_table.setItem(row, 4, default_item)
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout()
            actions_layout.setContentsMargins(4, 2, 4, 2)
            
            if not node.is_default:
                set_default_btn = QPushButton("Set Default")
                set_default_btn.clicked.connect(lambda checked, n=node: self.set_default_node(n))
                actions_layout.addWidget(set_default_btn)
            
            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda checked, n=node: self.edit_node(n))
            actions_layout.addWidget(edit_btn)
            
            delete_btn = QPushButton("Delete")
            delete_btn.clicked.connect(lambda checked, n=node: self.delete_node(n))
            if node.is_default:
                delete_btn.setEnabled(False)
                delete_btn.setToolTip("Cannot delete default node. Set another as default first.")
            actions_layout.addWidget(delete_btn)
            
            actions_widget.setLayout(actions_layout)
            self.nodes_table.setCellWidget(row, 5, actions_widget)
    
    def reconnect_wallet(self):
        """Reconnect wallet to current node"""
        default_node = self.node_manager.get_default_node()
        if not default_node:
            QMessageBox.warning(self, "Error", "No default node configured")
            return
        
        if not self.seller.wallet_path:
            QMessageBox.warning(self, "Error", "Wallet not configured")
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm Reconnect",
            f"Reconnect wallet to {default_node.node_name}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Request wallet password
            password = self._request_wallet_password()
            if not password:
                return
            
            self.progress_bar.setVisible(True)
            self.progress_label.setVisible(True)
            self.progress_label.setText("Reconnecting...")
            
            # Create wallet instance with password
            wallet = InHouseWallet(
                self.seller.wallet_path,
                password,
                default_node.address,
                default_node.port,
                default_node.use_ssl
            )
            
            self.reconnect_worker = ReconnectWalletWorker(wallet, default_node)
            self.reconnect_worker.progress.connect(self.progress_label.setText)
            self.reconnect_worker.finished.connect(self.on_reconnect_finished)
            self.reconnect_worker.start()
    
    def on_reconnect_finished(self, success, message):
        """Handle reconnect completion"""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        
        if success:
            # Update dashboard's wallet instance
            if self.dashboard and hasattr(self, 'reconnect_worker'):
                print("✓ DEBUG: Updating dashboard wallet reference")
                self.dashboard.wallet = self.reconnect_worker.wallet
                
                # Refresh WalletTab to show new connection
                if hasattr(self.dashboard, 'wallet_tab'):
                    print("✓ DEBUG: Refreshing WalletTab")
                    self.dashboard.wallet_tab.wallet = self.reconnect_worker.wallet
                    self.dashboard.wallet_tab.refresh_all()
            
            QMessageBox.information(self, "Success", message + "\n\nWallet reconnected successfully!")
        else:
            QMessageBox.warning(self, "Error", message)
    
    def rescan_blockchain(self):
        """Rescan blockchain"""
        if not self.seller.wallet_path:
            QMessageBox.warning(self, "Error", "Wallet not configured")
            return
        
        height_text = self.height_input.text().strip()
        height = None
        if height_text:
            try:
                height = int(height_text)
                if height < 0:
                    QMessageBox.warning(self, "Error", "Block height must be positive")
                    return
            except ValueError:
                QMessageBox.warning(self, "Error", "Invalid block height")
                return
        
        reply = QMessageBox.question(
            self,
            "Confirm Rescan",
            "Rescanning may take time depending on blockchain size.\n"
            "Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Request wallet password
            password = self._request_wallet_password()
            if not password:
                return
            
            self.progress_bar.setVisible(True)
            self.progress_label.setVisible(True)
            self.progress_label.setText("Starting rescan...")
            
            # Get default node
            default_node = self.node_manager.get_default_node()
            if not default_node:
                QMessageBox.warning(self, "Error", "No default node configured")
                self.progress_bar.setVisible(False)
                self.progress_label.setVisible(False)
                return
            
            # Create wallet instance with password
            wallet = InHouseWallet(
                self.seller.wallet_path,
                password,
                default_node.address,
                default_node.port,
                default_node.use_ssl
            )
            
            self.rescan_worker = RescanBlockchainWorker(wallet, height)
            self.rescan_worker.progress.connect(self.progress_label.setText)
            self.rescan_worker.finished.connect(self.on_rescan_finished)
            self.rescan_worker.start()
    
    def on_rescan_finished(self, success, message):
        """Handle rescan completion"""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        
        if success:
            # Update dashboard's wallet instance after rescan
            if self.dashboard and hasattr(self, 'rescan_worker'):
                print("✓ DEBUG: Updating dashboard wallet reference after rescan")
                self.dashboard.wallet = self.rescan_worker.wallet
                
                # Refresh WalletTab
                if hasattr(self.dashboard, 'wallet_tab'):
                    print("✓ DEBUG: Refreshing WalletTab after rescan")
                    self.dashboard.wallet_tab.wallet = self.rescan_worker.wallet
                    self.dashboard.wallet_tab.refresh_all()
            
            QMessageBox.information(self, "Success", message + "\n\nWallet rescanned successfully!")
        else:
            QMessageBox.warning(self, "Error", message)
    
    def add_node(self):
        """Open add node dialog"""
        dialog = AddNodeDialog(self.node_manager, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_nodes_table()
    
    def edit_node(self, node: MoneroNodeConfig):
        """Open edit node dialog"""
        dialog = EditNodeDialog(self.node_manager, node, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_nodes_table()
    
    def delete_node(self, node: MoneroNodeConfig):
        """Delete a node"""
        if node.is_default:
            QMessageBox.warning(
                self,
                "Cannot Delete",
                "Cannot delete the default node.\n"
                "Please set another node as default first."
            )
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete node '{node.node_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.node_manager.delete_node(node.id)
                self.refresh_nodes_table()
                QMessageBox.information(self, "Success", "Node deleted")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to delete node: {e}")
    
    def set_default_node(self, node: MoneroNodeConfig):
        """Set a node as default"""
        try:
            self.node_manager.set_default_node(node.id)
            self.refresh_nodes_table()
            QMessageBox.information(
                self,
                "Success",
                f"'{node.node_name}' is now the default node"
            )
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to set default: {e}")


class AddNodeDialog(QDialog):
    """Dialog for adding a new node"""
    
    def __init__(self, node_manager: NodeManager, parent=None):
        super().__init__(parent)
        self.node_manager = node_manager
        self.test_worker = None
        
        self.setWindowTitle("Add New Node")
        self.setModal(True)
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout()
        
        # Form
        form = QFormLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("My Node")
        form.addRow("Node Name:", self.name_input)
        
        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("node.example.com")
        form.addRow("Node Address*:", self.address_input)
        
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(18081)
        form.addRow("Node Port*:", self.port_input)
        
        self.ssl_checkbox = QCheckBox("Use SSL (https)")
        form.addRow("", self.ssl_checkbox)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Optional")
        form.addRow("Username:", self.username_input)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Optional")
        form.addRow("Password:", self.password_input)
        
        self.default_checkbox = QCheckBox("Set as default node")
        form.addRow("", self.default_checkbox)
        
        layout.addLayout(form)
        
        # Test connection section
        test_group = QGroupBox("Test Connection")
        test_layout = QVBoxLayout()
        
        test_btn_layout = QHBoxLayout()
        self.test_btn = QPushButton("Test Connection")
        self.test_btn.clicked.connect(self.test_connection)
        test_btn_layout.addWidget(self.test_btn)
        test_btn_layout.addStretch()
        test_layout.addLayout(test_btn_layout)
        
        self.test_result = QLabel("")
        self.test_result.setWordWrap(True)
        test_layout.addWidget(self.test_result)
        
        test_group.setLayout(test_layout)
        layout.addWidget(test_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_node)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def test_connection(self):
        """Test node connection"""
        address = self.address_input.text().strip()
        if not address:
            QMessageBox.warning(self, "Error", "Node address is required")
            return
        
        # Create temporary node config
        node = MoneroNodeConfig(
            address=address,
            port=self.port_input.value(),
            use_ssl=self.ssl_checkbox.isChecked(),
            username=self.username_input.text().strip() or None,
            password=self.password_input.text().strip() or None
        )
        
        self.test_btn.setEnabled(False)
        self.test_result.setText("Testing connection...")
        self.test_result.setStyleSheet("color: blue;")
        
        self.test_worker = TestNodeWorker(node)
        self.test_worker.finished.connect(self.on_test_finished)
        self.test_worker.start()
    
    def on_test_finished(self, success, message, response_time):
        """Handle test completion"""
        self.test_btn.setEnabled(True)
        
        if success:
            self.test_result.setText(
                f"✅ {message}\n"
                f"Response time: {response_time:.2f}s"
            )
            self.test_result.setStyleSheet("color: green;")
        else:
            self.test_result.setText(f"❌ Connection failed: {message}")
            self.test_result.setStyleSheet("color: red;")
    
    def save_node(self):
        """Validate and save node"""
        address = self.address_input.text().strip()
        if not address:
            QMessageBox.warning(self, "Error", "Node address is required")
            return
        
        name = self.name_input.text().strip()
        if not name:
            name = f"{address}:{self.port_input.value()}"
        
        try:
            node = MoneroNodeConfig(
                address=address,
                port=self.port_input.value(),
                use_ssl=self.ssl_checkbox.isChecked(),
                username=self.username_input.text().strip() or None,
                password=self.password_input.text().strip() or None,
                node_name=name,
                is_default=self.default_checkbox.isChecked()
            )
            
            self.node_manager.add_node(node)
            QMessageBox.information(self, "Success", "Node added successfully")
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to add node: {e}")


class EditNodeDialog(QDialog):
    """Dialog for editing an existing node"""
    
    def __init__(self, node_manager: NodeManager, node: MoneroNodeConfig, parent=None):
        super().__init__(parent)
        self.node_manager = node_manager
        self.node = node
        self.test_worker = None
        
        self.setWindowTitle("Edit Node")
        self.setModal(True)
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout()
        
        # Form
        form = QFormLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setText(node.node_name)
        form.addRow("Node Name:", self.name_input)
        
        self.address_input = QLineEdit()
        self.address_input.setText(node.address)
        form.addRow("Node Address*:", self.address_input)
        
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(node.port)
        form.addRow("Node Port*:", self.port_input)
        
        self.ssl_checkbox = QCheckBox("Use SSL (https)")
        self.ssl_checkbox.setChecked(node.use_ssl)
        form.addRow("", self.ssl_checkbox)
        
        self.username_input = QLineEdit()
        if node.username:
            self.username_input.setText(node.username)
        self.username_input.setPlaceholderText("Optional")
        form.addRow("Username:", self.username_input)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        if node.password:
            self.password_input.setText(node.password)
        self.password_input.setPlaceholderText("Optional")
        form.addRow("Password:", self.password_input)
        
        self.default_checkbox = QCheckBox("Set as default node")
        self.default_checkbox.setChecked(node.is_default)
        if node.is_default:
            self.default_checkbox.setEnabled(False)
            self.default_checkbox.setToolTip("Already the default node")
        form.addRow("", self.default_checkbox)
        
        layout.addLayout(form)
        
        # Test connection section
        test_group = QGroupBox("Test Connection")
        test_layout = QVBoxLayout()
        
        test_btn_layout = QHBoxLayout()
        self.test_btn = QPushButton("Test Connection")
        self.test_btn.clicked.connect(self.test_connection)
        test_btn_layout.addWidget(self.test_btn)
        test_btn_layout.addStretch()
        test_layout.addLayout(test_btn_layout)
        
        self.test_result = QLabel("")
        self.test_result.setWordWrap(True)
        test_layout.addWidget(self.test_result)
        
        test_group.setLayout(test_layout)
        layout.addWidget(test_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_node)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def test_connection(self):
        """Test node connection"""
        address = self.address_input.text().strip()
        if not address:
            QMessageBox.warning(self, "Error", "Node address is required")
            return
        
        # Create temporary node config
        node = MoneroNodeConfig(
            address=address,
            port=self.port_input.value(),
            use_ssl=self.ssl_checkbox.isChecked(),
            username=self.username_input.text().strip() or None,
            password=self.password_input.text().strip() or None
        )
        
        self.test_btn.setEnabled(False)
        self.test_result.setText("Testing connection...")
        self.test_result.setStyleSheet("color: blue;")
        
        self.test_worker = TestNodeWorker(node)
        self.test_worker.finished.connect(self.on_test_finished)
        self.test_worker.start()
    
    def on_test_finished(self, success, message, response_time):
        """Handle test completion"""
        self.test_btn.setEnabled(True)
        
        if success:
            self.test_result.setText(
                f"✅ {message}\n"
                f"Response time: {response_time:.2f}s"
            )
            self.test_result.setStyleSheet("color: green;")
        else:
            self.test_result.setText(f"❌ Connection failed: {message}")
            self.test_result.setStyleSheet("color: red;")
    
    def save_node(self):
        """Validate and save node"""
        address = self.address_input.text().strip()
        if not address:
            QMessageBox.warning(self, "Error", "Node address is required")
            return
        
        name = self.name_input.text().strip()
        if not name:
            name = f"{address}:{self.port_input.value()}"
        
        try:
            # Update node fields
            self.node.node_name = name
            self.node.address = address
            self.node.port = self.port_input.value()
            self.node.use_ssl = self.ssl_checkbox.isChecked()
            self.node.username = self.username_input.text().strip() or None
            self.node.password = self.password_input.text().strip() or None
            self.node.is_default = self.default_checkbox.isChecked()
            
            self.node_manager.update_node(self.node)
            QMessageBox.information(self, "Success", "Node updated successfully")
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to update node: {e}")


class DashboardWindow(QMainWindow):
    """Main dashboard window"""
    
    # Delay (in milliseconds) before showing deferred dialogs to allow dashboard to fully load
    # 500ms provides enough time for the window to render and become responsive
    # while still being quick enough that users notice the dialog immediately
    DIALOG_DEFER_DELAY_MS = 500
    
    def __init__(self, db_manager: DatabaseManager, signal_handler: Optional[SignalHandler] = None):
        super().__init__()
        
        self.db_manager = db_manager
        self.seller_manager = SellerManager(db_manager)
        self.product_manager = ProductManager(db_manager)
        self.order_manager = OrderManager(db_manager)
        self.contact_manager = ContactManager(db_manager)
        self.message_manager = MessageManager(db_manager)
        
        # Initialize SignalHandler if not provided
        if signal_handler is None:
            seller = self.seller_manager.get_seller(1)
            phone_number = seller.signal_id if seller else None
            self.signal_handler = SignalHandler(phone_number)
        else:
            self.signal_handler = signal_handler
        
        # Initialize buyer handler for automatic order processing
        from ..core.buyer_handler import BuyerHandler
        seller = self.seller_manager.get_seller(1)
        seller_signal_id = seller.signal_id if seller else None
        if seller_signal_id:
            self.signal_handler.buyer_handler = BuyerHandler(
                self.product_manager,
                self.order_manager,
                self.signal_handler,
                seller_signal_id
            )
            # Store reference for cache invalidation
            self.buyer_handler = self.signal_handler.buyer_handler
        else:
            self.buyer_handler = None
        
        # CRITICAL FIX: Auto-start listening for incoming messages
        if seller_signal_id:
            print("DEBUG: Dashboard initializing - starting message listener")
            self.signal_handler.start_listening()
        
        # Initialize payment monitoring if wallet is configured
        self.payment_processor = None
        self.wallet = None  # Store wallet reference for WalletTab
        self.node_monitor = None  # Node health monitor
        
        if seller and seller.wallet_path:
            try:
                from ..core.payments import PaymentProcessor
                from ..core.commission import CommissionManager
                from ..core.monero_wallet import InHouseWallet
                from ..models.node import NodeManager
                from ..core.node_monitor import NodeHealthMonitor
                from ..core.wallet_setup import test_node_connectivity
                
                # Get available nodes and test connectivity
                node_manager = NodeManager(self.db_manager)
                all_nodes = node_manager.list_nodes()
                
                # Test node connectivity
                print("🔍 Testing Monero node connectivity...")
                node_tuples = [(node.address, node.port) for node in all_nodes if node.address]
                working_nodes = test_node_connectivity(node_tuples) if node_tuples else []
                
                # Get default node or first working node
                default_node = node_manager.get_default_node()
                if not default_node and working_nodes:
                    # Use first working node - create simple object with required attributes
                    from collections import namedtuple
                    NodeConfig = namedtuple('NodeConfig', ['address', 'port', 'use_ssl'])
                    default_node_addr, default_node_port = working_nodes[0]
                    print(f"ℹ️  Using first working node: {default_node_addr}:{default_node_port}")
                    default_node = NodeConfig(default_node_addr, default_node_port, False)
                
                if default_node:
                    # Check if wallet exists and determine if it uses empty password
                    # For this bot, wallets are created with empty password by default
                    from pathlib import Path
                    wallet_path = Path(seller.wallet_path)
                    wallet_exists = (wallet_path.parent / f"{wallet_path.name}.keys").exists()
                    
                    # Default password for this bot is empty string
                    password = ""
                    needs_password_prompt = False
                    
                    if wallet_exists:
                        # Wallet exists - auto-unlock with empty password (standard for this bot)
                        print("ℹ️  Wallet found - attempting auto-unlock with empty password...")
                    else:
                        # Wallet doesn't exist yet - will be created with empty password
                        print("ℹ️  No wallet found - will create with empty password...")
                    
                    # Always try with empty password first (standard for this bot)
                    try:
                        print(f"🔧 DEBUG: Attempting to initialize wallet...")
                        print(f"   Wallet path: {seller.wallet_path}")
                        print(f"   Node: {default_node.address}:{default_node.port}")
                        print(f"   SSL: {default_node.use_ssl}")
                        print(f"   Password: <empty string>")
                        
                        # Initialize in-house wallet with empty password
                        self.wallet = InHouseWallet(
                            seller.wallet_path,
                            password,  # Empty string
                            default_node.address,
                            default_node.port,
                            default_node.use_ssl
                        )
                        
                        print(f"✓ DEBUG: Wallet instance created")
                        
                        # Auto-setup wallet (create if missing, start RPC)
                        print(f"🔧 DEBUG: Running wallet auto-setup...")
                        setup_success, seed_phrase = self.wallet.auto_setup_wallet(create_if_missing=True)
                        
                        if setup_success:
                            print("✓ Wallet auto-setup completed")
                            
                            # If new wallet created, show seed phrase
                            if seed_phrase:
                                QTimer.singleShot(self.DIALOG_DEFER_DELAY_MS, 
                                    lambda: self._show_seed_phrase_dialog(seed_phrase))
                            
                            # Connect to node
                            print(f"🔧 DEBUG: Attempting to connect to node...")
                            connection_result = self.wallet.connect()
                            print(f"🔧 DEBUG: Connection result: {connection_result}")
                            
                            if connection_result:
                                print("✓ Wallet connected successfully")
                                
                                # Start node health monitor
                                self.node_monitor = NodeHealthMonitor(self.wallet.setup_manager)
                                if len(working_nodes) > 1:
                                    # Use other working nodes as backups (exclude current default)
                                    backup_nodes = [
                                        (addr, port) for addr, port in working_nodes 
                                        if addr != default_node.address or port != default_node.port
                                    ]
                                    self.node_monitor.set_backup_nodes(backup_nodes)
                                self.node_monitor.start()
                                print("✓ Node health monitor started")
                            else:
                                print("⚠ Wallet initialized but connection failed")
                                # Defer warning dialog until after dashboard loads
                                QTimer.singleShot(self.DIALOG_DEFER_DELAY_MS, lambda: self._show_connection_warning())
                                self.wallet = None
                        else:
                            print("⚠ Wallet auto-setup failed")
                            QTimer.singleShot(self.DIALOG_DEFER_DELAY_MS, 
                                lambda: self._show_setup_failed_dialog())
                            self.wallet = None
                                
                    except Exception as e:
                        print(f"❌ ERROR: Failed to initialize wallet: {e}")
                        import traceback
                        traceback.print_exc()  # Print full stack trace
                        
                        # Defer error dialog until after dashboard loads
                        error_msg = str(e)
                        QTimer.singleShot(self.DIALOG_DEFER_DELAY_MS, lambda: self._show_initialization_error(error_msg))
                        self.wallet = None
                    
            except Exception as e:
                print(f"WARNING: Failed to initialize wallet: {e}")
        
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        
        # Create tabs
        tabs = QTabWidget()
        
        # Add tabs
        tabs.addTab(WalletTab(self.wallet, self.db_manager, self.seller_manager), "💰 Wallet")
        tabs.addTab(ProductsTab(self.product_manager), "Products")
        tabs.addTab(OrdersTab(self.order_manager), "Orders")
        tabs.addTab(MessagesTab(self.signal_handler, self.contact_manager, self.message_manager, self.seller_manager, self.product_manager), "Messages")
        tabs.addTab(ContactsTab(self.contact_manager, self.message_manager, self.signal_handler), "Contacts")
        tabs.addTab(SettingsTab(self.seller_manager, self.signal_handler), "Settings")
        
        self.setCentralWidget(tabs)
        
        print("✓ DEBUG: Dashboard initialization completed successfully")
    
    def _show_connection_warning(self):
        """Show connection warning after dashboard is loaded"""
        print("🔧 DEBUG: Showing deferred connection warning")
        QMessageBox.warning(
            self,
            "Wallet Connection Failed",
            "Wallet was initialized but failed to connect to the node.\n\n"
            "Possible reasons:\n"
            "• Node is down or unreachable\n"
            "• Network/firewall blocking connection\n"
            "• Incorrect node settings\n\n"
            "You can:\n"
            "1. Go to Settings → Wallet Settings → Manage Nodes\n"
            "2. Try a different public node\n"
            "3. Click 'Reconnect Now' after changing nodes",
            QMessageBox.Ok
        )
    
    def _show_seed_phrase_dialog(self, seed_phrase: str):
        """Show seed phrase dialog for newly created wallet"""
        from PyQt5.QtWidgets import QTextEdit, QVBoxLayout, QLabel, QPushButton, QDialog
        
        dialog = QDialog(self)
        dialog.setWindowTitle("⚠️ SAVE YOUR SEED PHRASE!")
        dialog.setMinimumWidth(600)
        
        layout = QVBoxLayout()
        
        # Warning label
        warning = QLabel(
            "Write down these 25 words and store them safely!\n"
            "This is the ONLY way to recover your wallet if you lose access.\n\n"
            "DO NOT share this with anyone!"
        )
        warning.setStyleSheet("color: red; font-weight: bold; font-size: 12px;")
        layout.addWidget(warning)
        
        # Seed phrase text
        seed_text = QTextEdit()
        seed_text.setPlainText(seed_phrase)
        seed_text.setReadOnly(True)
        seed_text.setStyleSheet("font-family: monospace; font-size: 11px;")
        layout.addWidget(seed_text)
        
        # Confirm button
        confirm_btn = QPushButton("I Have Saved My Seed Phrase")
        confirm_btn.clicked.connect(dialog.accept)
        layout.addWidget(confirm_btn)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def _show_setup_failed_dialog(self):
        """Show wallet setup failure dialog"""
        QMessageBox.critical(
            self,
            "Wallet Setup Failed",
            "Failed to setup wallet and start RPC.\n\n"
            "Possible issues:\n"
            "• Wallet file is missing or corrupted\n"
            "• monero-wallet-rpc is not installed\n"
            "• Node is unreachable\n\n"
            "Please check the logs for more details.",
            QMessageBox.Ok
        )
    
    def _show_initialization_error(self, error_msg):
        """Show initialization error after dashboard is loaded"""
        print("🔧 DEBUG: Showing deferred initialization error")
        QMessageBox.critical(
            self,
            "Wallet Initialization Error",
            f"Failed to initialize wallet:\n\n{error_msg}\n\n"
            "You can try again from:\n"
            "Settings → Wallet Settings → Connect & Sync → Reconnect Now",
            QMessageBox.Ok
        )
    
    @staticmethod
    def verify_pin(db_manager: DatabaseManager) -> bool:
        """
        Verify PIN before showing dashboard
        
        Args:
            db_manager: Database manager
            
        Returns:
            True if PIN verified
        """
        seller_manager = SellerManager(db_manager)
        
        dialog = PINDialog()
        if dialog.exec_() == QDialog.Accepted:
            pin = dialog.get_pin()
            if seller_manager.verify_pin(1, pin):
                return True
            else:
                QMessageBox.warning(None, "Invalid PIN", "Incorrect PIN")
                return False
        return False
