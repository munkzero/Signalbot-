"""
Main seller dashboard GUI
"""

import sys
import os
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QMessageBox, QLineEdit, QDialog,
    QDialogButtonBox, QFormLayout, QTextEdit, QListWidget,
    QSplitter, QFileDialog, QCheckBox, QDoubleSpinBox,
    QSpinBox, QComboBox, QScrollArea, QRadioButton,
    QButtonGroup, QGroupBox, QGridLayout, QListWidgetItem,
    QMenu, QAction, QApplication
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QCursor
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
    MONERO_CONFIRMATIONS_REQUIRED, COMMISSION_RATE
)
from ..core.signal_handler import SignalHandler
from ..utils.image_tools import image_processor


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
    
    def save_product(self):
        """Validate and save product"""
        # Validate required fields
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Product name is required")
            return
        
        price = self.price_input.value()
        if price <= 0:
            QMessageBox.warning(self, "Validation Error", "Price must be greater than 0")
            return
        
        # Create or update product
        if self.product:
            # Update existing
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
    
    def __init__(self, signal_handler: SignalHandler, parent=None):
        super().__init__(parent)
        self.signal_handler = signal_handler
        
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
                QMessageBox.information(self, "Success", "Message sent successfully!")
                self.accept()
            else:
                QMessageBox.warning(self, "Send Failed", "Failed to send message. Check Signal configuration.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to send message: {e}")


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
        button_layout.addWidget(refresh_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Orders table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Order ID", "Product", "Amount (XMR)", "Payment Status",
            "Order Status", "Date", "Actions"
        ])
        layout.addWidget(self.table)
        
        # Connect signals
        refresh_btn.clicked.connect(self.load_orders)
        
        self.setLayout(layout)
        self.load_orders()
    
    def load_orders(self):
        """Load orders into table"""
        orders = self.order_manager.list_orders(limit=100)
        
        self.table.setRowCount(len(orders))
        
        for row, order in enumerate(orders):
            self.table.setItem(row, 0, QTableWidgetItem(order.order_id))
            self.table.setItem(row, 1, QTableWidgetItem(order.product_name))
            self.table.setItem(row, 2, QTableWidgetItem(f"{order.price_xmr:.6f}"))
            self.table.setItem(row, 3, QTableWidgetItem(order.payment_status))
            self.table.setItem(row, 4, QTableWidgetItem(order.order_status))
            self.table.setItem(row, 5, QTableWidgetItem(
                order.created_at.strftime("%Y-%m-%d %H:%M") if order.created_at else "N/A"
            ))


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
    
    def __init__(self, signal_handler: SignalHandler, contact_manager, message_manager, seller_manager):
        super().__init__()
        self.signal_handler = signal_handler
        self.contact_manager = contact_manager
        self.message_manager = message_manager
        self.seller_manager = seller_manager
        self.conversations = {}  # Dict to store conversations
        self.conversations_cache = {}  # Cache for conversation data
        self.current_recipient = None
        self.my_signal_id = None
        
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
            
            for msg in messages:
                timestamp = msg.sent_at.strftime("%H:%M") if msg.sent_at else "??:??"
                sender_name = "You" if msg.is_outgoing else display_name
                text = msg.message_body or "[Attachment]"
                self.message_history.append(f"[{timestamp}] {sender_name}: {text}\n")
    
    def compose_message(self):
        """Open compose message dialog"""
        dialog = ComposeMessageDialog(self.signal_handler, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_conversations(force_refresh=True)
    
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
        QMessageBox.information(self, "Feature", "Product picker dialog would open here")
    
    def send_catalog(self):
        """Send full catalog to current recipient"""
        if not self.current_recipient:
            QMessageBox.warning(self, "No Recipient", "Please select a conversation first")
            return
        
        QMessageBox.information(self, "Feature", "Send catalog functionality to be implemented")
    
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
        unlink_btn = QPushButton("Unlink")
        unlink_btn.clicked.connect(self.unlink_signal)
        
        signal_buttons.addWidget(relink_btn)
        signal_buttons.addWidget(test_signal_btn)
        signal_buttons.addWidget(unlink_btn)
        signal_buttons.addStretch()
        signal_layout.addLayout(signal_buttons)
        
        signal_group.setLayout(signal_layout)
        layout.addWidget(signal_group)
        
        # Section 2: Wallet Configuration
        wallet_group = QGroupBox("Monero Wallet")
        wallet_layout = QVBoxLayout()
        
        if seller and seller.wallet_config:
            wallet_type = seller.wallet_config.get('type', 'Unknown')
            if wallet_type == 'view_only':
                address = seller.wallet_config.get('address', 'N/A')
                # Truncate address
                display_addr = address[:12] + "..." + address[-12:] if len(address) > 24 else address
                wallet_layout.addWidget(QLabel(f"Type: View-Only Wallet"))
                
                addr_layout = QHBoxLayout()
                addr_layout.addWidget(QLabel(f"Address: {display_addr}"))
                copy_btn = QPushButton("Copy")
                copy_btn.setMaximumWidth(80)
                addr_layout.addWidget(copy_btn)
                addr_layout.addStretch()
                wallet_layout.addLayout(addr_layout)
            elif wallet_type == 'rpc':
                rpc_host = seller.wallet_config.get('rpc_host', 'N/A')
                rpc_port = seller.wallet_config.get('rpc_port', 'N/A')
                wallet_layout.addWidget(QLabel(f"Type: RPC Wallet"))
                wallet_layout.addWidget(QLabel(f"RPC: {rpc_host}:{rpc_port}"))
        else:
            wallet_layout.addWidget(QLabel("Wallet not configured"))
        
        wallet_btn_layout = QHBoxLayout()
        test_conn_btn = QPushButton("Test Connection")
        edit_wallet_btn = QPushButton("Edit Wallet Settings")
        wallet_btn_layout.addWidget(test_conn_btn)
        wallet_btn_layout.addWidget(edit_wallet_btn)
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
        commission_layout.addWidget(QLabel("For every sale: 96% goes to you, 4% goes to the bot creator."))
        
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


class DashboardWindow(QMainWindow):
    """Main dashboard window"""
    
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
        
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        
        # Create tabs
        tabs = QTabWidget()
        
        # Add tabs
        tabs.addTab(ProductsTab(self.product_manager), "Products")
        tabs.addTab(OrdersTab(self.order_manager), "Orders")
        tabs.addTab(MessagesTab(self.signal_handler, self.contact_manager, self.message_manager, self.seller_manager), "Messages")
        tabs.addTab(SettingsTab(self.seller_manager, self.signal_handler), "Settings")
        
        self.setCentralWidget(tabs)
    
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
