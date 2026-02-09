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
    QButtonGroup, QGroupBox, QGridLayout, QListWidgetItem
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QPixmap
from datetime import datetime
from typing import Optional

from ..database.db import DatabaseManager
from ..models.seller import SellerManager
from ..models.product import ProductManager, Product
from ..models.order import OrderManager, Order
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


class MessagesTab(QWidget):
    """Messaging tab with conversation list and chat window"""
    
    def __init__(self, signal_handler: SignalHandler):
        super().__init__()
        self.signal_handler = signal_handler
        self.conversations = {}  # Dict to store conversations
        self.current_recipient = None
        
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
        
        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.send_message)
        
        message_input_layout.addWidget(self.message_input)
        message_input_layout.addWidget(send_btn)
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
    
    def load_conversations(self):
        """Load conversation list"""
        # In a real implementation, this would load from a database
        # For now, show placeholder
        self.conversations_list.clear()
        
        # Example conversations (in real app, load from database/history)
        sample_conversations = []
        
        if not sample_conversations:
            item = QListWidgetItem("No conversations yet")
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
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
        """Load selected conversation"""
        if not item or not item.flags() & Qt.ItemIsSelectable:
            return
        
        recipient = item.data(Qt.UserRole)
        if recipient:
            self.current_recipient = recipient
            self.chat_header.setText(f"Chat with {recipient}")
            
            # Load message history (placeholder)
            self.message_history.clear()
            messages = self.conversations.get(recipient, [])
            
            for msg in messages:
                timestamp = msg.get('timestamp', '')
                sender = msg.get('sender', '')
                text = msg.get('text', '')
                self.message_history.append(f"[{timestamp}] {sender}: {text}\n")
    
    def compose_message(self):
        """Open compose message dialog"""
        dialog = ComposeMessageDialog(self.signal_handler, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_conversations()
    
    def send_message(self):
        """Send message to current recipient"""
        if not self.current_recipient:
            QMessageBox.warning(self, "No Recipient", "Please select a conversation first")
            return
        
        message = self.message_input.text().strip()
        if not message and not self.attachment_path:
            return
        
        try:
            attachments = [self.attachment_path] if self.attachment_path else None
            success = self.signal_handler.send_message(
                self.current_recipient,
                message,
                attachments
            )
            
            if success:
                # Add to message history
                timestamp = datetime.now().strftime("%H:%M")
                self.message_history.append(f"[{timestamp}] You: {message}\n")
                self.message_input.clear()
                self.attachment_path = None
            else:
                QMessageBox.warning(self, "Send Failed", "Failed to send message")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to send message: {e}")
    
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
        
        # Add to conversations
        if sender not in self.conversations:
            self.conversations[sender] = []
            # Add to list
            item = QListWidgetItem(sender)
            item.setData(Qt.UserRole, sender)
            self.conversations_list.addItem(item)
        
        self.conversations[sender].append(message)
        
        # Update current conversation if it's the active one
        if self.current_recipient == sender:
            self.message_history.append(f"[{timestamp}] {sender}: {text}\n")


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
        phone_number = seller.signal_id if seller else "Not configured"
        
        phone_label = QLabel(f"Linked Phone: {phone_number}")
        signal_layout.addWidget(phone_label)
        
        signal_btn_layout = QHBoxLayout()
        relink_btn = QPushButton("Re-link Account")
        unlink_btn = QPushButton("Unlink Account")
        signal_btn_layout.addWidget(relink_btn)
        signal_btn_layout.addWidget(unlink_btn)
        signal_btn_layout.addStretch()
        signal_layout.addLayout(signal_btn_layout)
        
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


class DashboardWindow(QMainWindow):
    """Main dashboard window"""
    
    def __init__(self, db_manager: DatabaseManager, signal_handler: Optional[SignalHandler] = None):
        super().__init__()
        
        self.db_manager = db_manager
        self.seller_manager = SellerManager(db_manager)
        self.product_manager = ProductManager(db_manager)
        self.order_manager = OrderManager(db_manager)
        
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
        tabs.addTab(MessagesTab(self.signal_handler), "Messages")
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
