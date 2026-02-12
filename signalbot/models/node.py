"""
Monero node model and management
"""

from typing import Optional, List
from ..database.db import MoneroNode as NodeModel, DatabaseManager


class MoneroNodeConfig:
    """Monero node configuration"""
    
    def __init__(
        self,
        id: Optional[int] = None,
        address: str = "",
        port: int = 18081,
        use_ssl: bool = False,
        username: Optional[str] = None,
        password: Optional[str] = None,
        node_name: Optional[str] = None,
        is_default: bool = False
    ):
        self.id = id
        self.address = address
        self.port = port
        self.use_ssl = use_ssl
        self.username = username
        self.password = password
        self.node_name = node_name or f"{address}:{port}"
        self.is_default = is_default
    
    @classmethod
    def from_db_model(cls, db_node: NodeModel, db_manager: DatabaseManager) -> 'MoneroNodeConfig':
        """
        Create MoneroNodeConfig from database model
        
        Args:
            db_node: Database node model
            db_manager: Database manager for decryption
            
        Returns:
            MoneroNodeConfig instance
        """
        username = None
        if db_node.username and db_node.username_salt:
            try:
                username = db_manager.decrypt_field(
                    db_node.username,
                    db_node.username_salt
                )
            except:
                username = None
        
        password = None
        if db_node.password and db_node.password_salt:
            try:
                password = db_manager.decrypt_field(
                    db_node.password,
                    db_node.password_salt
                )
            except:
                password = None
        
        return cls(
            id=db_node.id,
            address=db_node.address,
            port=db_node.port,
            use_ssl=db_node.use_ssl,
            username=username,
            password=password,
            node_name=db_node.node_name,
            is_default=db_node.is_default
        )
    
    def to_db_model(self, db_manager: DatabaseManager) -> NodeModel:
        """
        Convert to database model
        
        Args:
            db_manager: Database manager for encryption
            
        Returns:
            Database node model
        """
        # Encrypt credentials
        username_enc = None
        username_salt = None
        if self.username:
            username_enc, username_salt = db_manager.encrypt_field(self.username)
        
        password_enc = None
        password_salt = None
        if self.password:
            password_enc, password_salt = db_manager.encrypt_field(self.password)
        
        db_node = NodeModel(
            address=self.address,
            port=self.port,
            use_ssl=self.use_ssl,
            username=username_enc,
            username_salt=username_salt,
            password=password_enc,
            password_salt=password_salt,
            node_name=self.node_name,
            is_default=self.is_default
        )
        
        if self.id:
            db_node.id = self.id
        
        return db_node


class NodeManager:
    """Manages Monero node operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def add_node(self, node: MoneroNodeConfig) -> MoneroNodeConfig:
        """
        Add a new node
        
        Args:
            node: Node configuration to add
            
        Returns:
            Created node with ID
        """
        # If this is set as default, unset other defaults
        if node.is_default:
            self.db.session.query(NodeModel).update({'is_default': False})
        
        db_node = node.to_db_model(self.db)
        self.db.session.add(db_node)
        self.db.session.commit()
        
        node.id = db_node.id
        return node
    
    def get_node(self, node_id: int) -> Optional[MoneroNodeConfig]:
        """
        Get node by ID
        
        Args:
            node_id: Node ID
            
        Returns:
            Node configuration or None
        """
        db_node = self.db.session.query(NodeModel).filter_by(id=node_id).first()
        if db_node:
            return MoneroNodeConfig.from_db_model(db_node, self.db)
        return None
    
    def get_default_node(self) -> Optional[MoneroNodeConfig]:
        """
        Get the default node
        
        Returns:
            Default node configuration or None
        """
        db_node = self.db.session.query(NodeModel).filter_by(is_default=True).first()
        if db_node:
            return MoneroNodeConfig.from_db_model(db_node, self.db)
        return None
    
    def list_nodes(self) -> List[MoneroNodeConfig]:
        """
        List all nodes
        
        Returns:
            List of node configurations
        """
        db_nodes = self.db.session.query(NodeModel).all()
        return [MoneroNodeConfig.from_db_model(node, self.db) for node in db_nodes]
    
    def update_node(self, node: MoneroNodeConfig) -> MoneroNodeConfig:
        """
        Update a node
        
        Args:
            node: Node configuration to update
            
        Returns:
            Updated node
        """
        db_node = self.db.session.query(NodeModel).filter_by(id=node.id).first()
        if not db_node:
            raise ValueError(f"Node with ID {node.id} not found")
        
        # If this is set as default, unset other defaults
        if node.is_default and not db_node.is_default:
            self.db.session.query(NodeModel).update({'is_default': False})
        
        db_node.address = node.address
        db_node.port = node.port
        db_node.use_ssl = node.use_ssl
        db_node.node_name = node.node_name
        db_node.is_default = node.is_default
        
        # Update credentials if provided
        if node.username:
            username_enc, username_salt = self.db.encrypt_field(node.username)
            db_node.username = username_enc
            db_node.username_salt = username_salt
        
        if node.password:
            password_enc, password_salt = self.db.encrypt_field(node.password)
            db_node.password = password_enc
            db_node.password_salt = password_salt
        
        self.db.session.commit()
        return node
    
    def delete_node(self, node_id: int):
        """
        Delete a node
        
        Args:
            node_id: Node ID to delete
        """
        db_node = self.db.session.query(NodeModel).filter_by(id=node_id).first()
        if db_node:
            self.db.session.delete(db_node)
            self.db.session.commit()
    
    def set_default_node(self, node_id: int):
        """
        Set a node as default
        
        Args:
            node_id: Node ID to set as default
        """
        # Unset all defaults
        self.db.session.query(NodeModel).update({'is_default': False})
        
        # Set the specified node as default
        db_node = self.db.session.query(NodeModel).filter_by(id=node_id).first()
        if db_node:
            db_node.is_default = True
            self.db.session.commit()
