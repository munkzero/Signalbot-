"""
Product model and management
"""

from typing import Optional, List
from datetime import datetime
from ..database.db import Product as ProductModel, DatabaseManager
from ..core.security import security_manager


class Product:
    """Product entity with encryption support"""
    
    def __init__(
        self,
        id: Optional[int] = None,
        name: str = "",
        description: str = "",
        price: float = 0.0,
        currency: str = "USD",
        stock: int = 0,
        category: Optional[str] = None,
        image_path: Optional[str] = None,
        active: bool = True
    ):
        self.id = id
        self.name = name
        self.description = description
        self.price = price
        self.currency = currency
        self.stock = stock
        self.category = category
        self.image_path = image_path
        self.active = active
    
    @classmethod
    def from_db_model(cls, db_product: ProductModel, db_manager: DatabaseManager) -> 'Product':
        """
        Create Product from database model
        
        Args:
            db_product: Database product model
            db_manager: Database manager for decryption
            
        Returns:
            Product instance
        """
        image_path = None
        if db_product.image_path and db_product.image_path_salt:
            try:
                image_path = db_manager.decrypt_field(
                    db_product.image_path,
                    db_product.image_path_salt
                )
            except:
                image_path = None
        
        return cls(
            id=db_product.id,
            name=db_product.name,
            description=db_product.description or "",
            price=db_product.price,
            currency=db_product.currency,
            stock=db_product.stock,
            category=db_product.category,
            image_path=image_path,
            active=db_product.active
        )
    
    def to_db_model(self, db_manager: DatabaseManager) -> ProductModel:
        """
        Convert to database model
        
        Args:
            db_manager: Database manager for encryption
            
        Returns:
            Database product model
        """
        image_path_enc = None
        image_path_salt = None
        
        if self.image_path:
            image_path_enc, image_path_salt = db_manager.encrypt_field(self.image_path)
        
        db_product = ProductModel(
            name=self.name,
            description=self.description,
            price=self.price,
            currency=self.currency,
            stock=self.stock,
            category=self.category,
            image_path=image_path_enc,
            image_path_salt=image_path_salt,
            active=self.active
        )
        
        if self.id:
            db_product.id = self.id
        
        return db_product


class ProductManager:
    """Manages product operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_product(self, product: Product) -> Product:
        """
        Create a new product
        
        Args:
            product: Product to create
            
        Returns:
            Created product with ID
        """
        db_product = product.to_db_model(self.db)
        self.db.session.add(db_product)
        self.db.session.commit()
        
        product.id = db_product.id
        return product
    
    def update_product(self, product: Product) -> Product:
        """
        Update existing product
        
        Args:
            product: Product to update
            
        Returns:
            Updated product
        """
        db_product = self.db.session.query(ProductModel).filter_by(id=product.id).first()
        if not db_product:
            raise ValueError(f"Product with ID {product.id} not found")
        
        db_product.name = product.name
        db_product.description = product.description
        db_product.price = product.price
        db_product.currency = product.currency
        db_product.stock = product.stock
        db_product.category = product.category
        db_product.active = product.active
        
        if product.image_path:
            image_path_enc, image_path_salt = self.db.encrypt_field(product.image_path)
            db_product.image_path = image_path_enc
            db_product.image_path_salt = image_path_salt
        
        self.db.session.commit()
        return product
    
    def delete_product(self, product_id: int):
        """
        Delete a product
        
        Args:
            product_id: ID of product to delete
        """
        db_product = self.db.session.query(ProductModel).filter_by(id=product_id).first()
        if db_product:
            self.db.session.delete(db_product)
            self.db.session.commit()
    
    def get_product(self, product_id: int) -> Optional[Product]:
        """
        Get product by ID
        
        Args:
            product_id: Product ID
            
        Returns:
            Product or None if not found
        """
        db_product = self.db.session.query(ProductModel).filter_by(id=product_id).first()
        if db_product:
            return Product.from_db_model(db_product, self.db)
        return None
    
    def list_products(
        self,
        category: Optional[str] = None,
        active_only: bool = True,
        search: Optional[str] = None
    ) -> List[Product]:
        """
        List products with filtering
        
        Args:
            category: Filter by category
            active_only: Only show active products
            search: Search term for name/description
            
        Returns:
            List of products
        """
        query = self.db.session.query(ProductModel)
        
        if active_only:
            query = query.filter_by(active=True)
        
        if category:
            query = query.filter_by(category=category)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (ProductModel.name.like(search_term)) |
                (ProductModel.description.like(search_term))
            )
        
        db_products = query.all()
        return [Product.from_db_model(p, self.db) for p in db_products]
    
    def update_stock(self, product_id: int, quantity_change: int) -> Product:
        """
        Update product stock
        
        Args:
            product_id: Product ID
            quantity_change: Amount to add/subtract from stock
            
        Returns:
            Updated product
        """
        db_product = self.db.session.query(ProductModel).filter_by(id=product_id).first()
        if not db_product:
            raise ValueError(f"Product with ID {product_id} not found")
        
        db_product.stock += quantity_change
        
        # Deactivate if out of stock
        if db_product.stock <= 0:
            db_product.active = False
        
        self.db.session.commit()
        return Product.from_db_model(db_product, self.db)
    
    def get_low_stock_products(self, threshold: int = 5) -> List[Product]:
        """
        Get products with low stock
        
        Args:
            threshold: Stock threshold
            
        Returns:
            List of products with stock <= threshold
        """
        db_products = self.db.session.query(ProductModel).filter(
            ProductModel.stock <= threshold,
            ProductModel.active == True
        ).all()
        
        return [Product.from_db_model(p, self.db) for p in db_products]
