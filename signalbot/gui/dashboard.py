"""
Main seller dashboard GUI
"""

import sys
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QMessageBox, QLineEdit, QDialog,
    QDialogButtonBox, QFormLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from ..database.db import DatabaseManager
from ..models.seller import SellerManager
from ..models.product import ProductManager, Product
from ..models.order import OrderManager, Order
from ..config.settings import WINDOW_TITLE, WINDOW_WIDTH, WINDOW_HEIGHT


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
        
        button_layout.addWidget(add_btn)
        button_layout.addWidget(refresh_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Products table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Name", "Price", "Stock", "Category", "Status"
        ])
        layout.addWidget(self.table)
        
        # Connect signals
        refresh_btn.clicked.connect(self.load_products)
        
        self.setLayout(layout)
        self.load_products()
    
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


class DashboardWindow(QMainWindow):
    """Main dashboard window"""
    
    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        
        self.db_manager = db_manager
        self.seller_manager = SellerManager(db_manager)
        self.product_manager = ProductManager(db_manager)
        self.order_manager = OrderManager(db_manager)
        
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        
        # Create tabs
        tabs = QTabWidget()
        
        # Add tabs
        tabs.addTab(ProductsTab(self.product_manager), "Products")
        tabs.addTab(OrdersTab(self.order_manager), "Orders")
        tabs.addTab(QWidget(), "Settings")
        
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
