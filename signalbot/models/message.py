"""
Message model and management
"""

from typing import Optional, List, Dict
from datetime import datetime
from ..database.db import Message as MessageModel, DatabaseManager


class Message:
    """Message entity"""
    
    def __init__(
        self,
        id: Optional[int] = None,
        sender_signal_id: Optional[str] = None,
        recipient_signal_id: Optional[str] = None,
        message_body: Optional[str] = None,
        is_outgoing: bool = False,
        sent_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None
    ):
        self.id = id
        self.sender_signal_id = sender_signal_id
        self.recipient_signal_id = recipient_signal_id
        self.message_body = message_body
        self.is_outgoing = is_outgoing
        self.sent_at = sent_at
        self.created_at = created_at
    
    @classmethod
    def from_db_model(cls, db_message: MessageModel, db_manager: DatabaseManager) -> 'Message':
        """
        Create Message from database model
        
        Args:
            db_message: Database message model
            db_manager: Database manager for decryption
            
        Returns:
            Message instance
        """
        sender_signal_id = None
        if db_message.sender_signal_id and db_message.sender_signal_id_salt:
            try:
                sender_signal_id = db_manager.decrypt_field(
                    db_message.sender_signal_id,
                    db_message.sender_signal_id_salt
                )
            except Exception:
                sender_signal_id = None
        
        recipient_signal_id = None
        if db_message.recipient_signal_id and db_message.recipient_signal_id_salt:
            try:
                recipient_signal_id = db_manager.decrypt_field(
                    db_message.recipient_signal_id,
                    db_message.recipient_signal_id_salt
                )
            except Exception:
                recipient_signal_id = None
        
        return cls(
            id=db_message.id,
            sender_signal_id=sender_signal_id,
            recipient_signal_id=recipient_signal_id,
            message_body=db_message.message_body,
            is_outgoing=db_message.is_outgoing,
            sent_at=db_message.sent_at,
            created_at=db_message.created_at
        )
    
    def to_db_model(self, db_manager: DatabaseManager) -> MessageModel:
        """
        Convert to database model
        
        Args:
            db_manager: Database manager for encryption
            
        Returns:
            Database message model
        """
        # Encrypt sender Signal ID
        sender_enc = None
        sender_salt = None
        if self.sender_signal_id:
            sender_enc, sender_salt = db_manager.encrypt_field(self.sender_signal_id)
        
        # Encrypt recipient Signal ID
        recipient_enc = None
        recipient_salt = None
        if self.recipient_signal_id:
            recipient_enc, recipient_salt = db_manager.encrypt_field(self.recipient_signal_id)
        
        db_message = MessageModel(
            sender_signal_id=sender_enc,
            sender_signal_id_salt=sender_salt,
            recipient_signal_id=recipient_enc,
            recipient_signal_id_salt=recipient_salt,
            message_body=self.message_body,
            is_outgoing=self.is_outgoing,
            sent_at=self.sent_at or datetime.utcnow()
        )
        
        if self.id:
            db_message.id = self.id
        
        return db_message


class MessageManager:
    """Manages message operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def add_message(
        self,
        sender_signal_id: str,
        recipient_signal_id: str,
        message_body: Optional[str] = None,
        is_outgoing: bool = False
    ) -> Message:
        """
        Add message to database
        
        Args:
            sender_signal_id: Sender Signal ID
            recipient_signal_id: Recipient Signal ID
            message_body: Message text
            is_outgoing: Whether this is an outgoing message
            
        Returns:
            Created message
        """
        message = Message(
            sender_signal_id=sender_signal_id,
            recipient_signal_id=recipient_signal_id,
            message_body=message_body,
            is_outgoing=is_outgoing,
            sent_at=datetime.utcnow()
        )
        
        db_message = message.to_db_model(self.db)
        self.db.session.add(db_message)
        self.db.session.commit()
        
        message.id = db_message.id
        return message
    
    def get_conversation(self, contact_signal_id: str, my_signal_id: str) -> List[Message]:
        """
        Get conversation messages with a contact
        
        Args:
            contact_signal_id: Contact's Signal ID
            my_signal_id: My Signal ID
            
        Returns:
            List of messages ordered by time
        """
        db_messages = self.db.session.query(MessageModel).order_by(MessageModel.sent_at).all()
        
        # Decrypt and filter messages for this conversation
        conversation_messages = []
        for db_msg in db_messages:
            try:
                sender = self.db.decrypt_field(db_msg.sender_signal_id, db_msg.sender_signal_id_salt)
                recipient = self.db.decrypt_field(db_msg.recipient_signal_id, db_msg.recipient_signal_id_salt)
                
                # Check if this message is part of the conversation
                if (sender == my_signal_id and recipient == contact_signal_id) or \
                   (sender == contact_signal_id and recipient == my_signal_id):
                    conversation_messages.append(Message.from_db_model(db_msg, self.db))
            except Exception:
                continue
        
        return conversation_messages
    
    def get_all_conversations(self, my_signal_id: str) -> Dict[str, Dict]:
        """
        Get all conversations with message counts and last message
        
        Args:
            my_signal_id: My Signal ID
            
        Returns:
            Dict mapping contact Signal IDs to conversation data
        """
        db_messages = self.db.session.query(MessageModel).order_by(MessageModel.sent_at.desc()).all()
        
        conversations = {}
        
        for db_msg in db_messages:
            try:
                sender = self.db.decrypt_field(db_msg.sender_signal_id, db_msg.sender_signal_id_salt)
                recipient = self.db.decrypt_field(db_msg.recipient_signal_id, db_msg.recipient_signal_id_salt)
                
                # Determine the contact (the other party)
                contact_id = None
                if sender == my_signal_id:
                    contact_id = recipient
                elif recipient == my_signal_id:
                    contact_id = sender
                
                if contact_id and contact_id not in conversations:
                    conversations[contact_id] = {
                        'last_message': db_msg.message_body or '[Attachment]',
                        'last_timestamp': db_msg.sent_at,
                        'count': 0
                    }
                
                if contact_id:
                    conversations[contact_id]['count'] += 1
            except Exception:
                continue
        
        return conversations
    
    def delete_message(self, message_id: int) -> bool:
        """
        Delete a single message by ID
        
        Args:
            message_id: Database ID of message to delete
            
        Returns:
            True if message deleted successfully
        """
        try:
            db_message = self.db.session.query(MessageModel).filter_by(id=message_id).first()
            if db_message:
                self.db.session.delete(db_message)
                self.db.session.commit()
                return True
            return False
        except Exception as e:
            print(f"Error deleting message: {e}")
            return False
    
    def delete_conversation(self, contact_signal_id: str, my_signal_id: str) -> bool:
        """
        Delete all messages in a conversation
        
        Args:
            contact_signal_id: Contact's Signal ID
            my_signal_id: My Signal ID
            
        Returns:
            True if messages deleted
        """
        db_messages = self.db.session.query(MessageModel).all()
        
        deleted = False
        for db_msg in db_messages:
            try:
                sender = self.db.decrypt_field(db_msg.sender_signal_id, db_msg.sender_signal_id_salt)
                recipient = self.db.decrypt_field(db_msg.recipient_signal_id, db_msg.recipient_signal_id_salt)
                
                # Check if this message is part of the conversation
                if (sender == my_signal_id and recipient == contact_signal_id) or \
                   (sender == contact_signal_id and recipient == my_signal_id):
                    self.db.session.delete(db_msg)
                    deleted = True
            except Exception:
                continue
        
        if deleted:
            self.db.session.commit()
        
        return deleted
