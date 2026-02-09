"""
Contact model and management
"""

from typing import Optional, List
from datetime import datetime
from ..database.db import Contact as ContactModel, DatabaseManager


class Contact:
    """Contact entity"""
    
    def __init__(
        self,
        id: Optional[int] = None,
        signal_id: Optional[str] = None,
        name: Optional[str] = None,
        notes: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = id
        self.signal_id = signal_id
        self.name = name
        self.notes = notes
        self.created_at = created_at
        self.updated_at = updated_at
    
    @classmethod
    def from_db_model(cls, db_contact: ContactModel, db_manager: DatabaseManager) -> 'Contact':
        """
        Create Contact from database model
        
        Args:
            db_contact: Database contact model
            db_manager: Database manager for decryption
            
        Returns:
            Contact instance
        """
        signal_id = None
        if db_contact.signal_id and db_contact.signal_id_salt:
            try:
                signal_id = db_manager.decrypt_field(
                    db_contact.signal_id,
                    db_contact.signal_id_salt
                )
            except Exception:
                signal_id = None
        
        return cls(
            id=db_contact.id,
            signal_id=signal_id,
            name=db_contact.name,
            notes=db_contact.notes,
            created_at=db_contact.created_at,
            updated_at=db_contact.updated_at
        )
    
    def to_db_model(self, db_manager: DatabaseManager) -> ContactModel:
        """
        Convert to database model
        
        Args:
            db_manager: Database manager for encryption
            
        Returns:
            Database contact model
        """
        # Encrypt Signal ID
        signal_id_enc = None
        signal_id_salt = None
        if self.signal_id:
            signal_id_enc, signal_id_salt = db_manager.encrypt_field(self.signal_id)
        
        db_contact = ContactModel(
            signal_id=signal_id_enc,
            signal_id_salt=signal_id_salt,
            name=self.name,
            notes=self.notes
        )
        
        if self.id:
            db_contact.id = self.id
        
        return db_contact


class ContactManager:
    """Manages contact operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_contact(self, contact: Contact) -> Contact:
        """
        Create contact
        
        Args:
            contact: Contact to create
            
        Returns:
            Created contact with ID
        """
        db_contact = contact.to_db_model(self.db)
        self.db.session.add(db_contact)
        self.db.session.commit()
        
        contact.id = db_contact.id
        return contact
    
    def get_contact(self, contact_id: int) -> Optional[Contact]:
        """
        Get contact by ID
        
        Args:
            contact_id: Contact ID
            
        Returns:
            Contact or None
        """
        db_contact = self.db.session.query(ContactModel).filter_by(id=contact_id).first()
        if db_contact:
            return Contact.from_db_model(db_contact, self.db)
        return None
    
    def get_contact_by_signal_id(self, signal_id: str) -> Optional[Contact]:
        """
        Get contact by Signal ID
        
        Args:
            signal_id: Signal ID to search for
            
        Returns:
            Contact or None
        """
        # Get all contacts and decrypt to find match
        db_contacts = self.db.session.query(ContactModel).all()
        for db_contact in db_contacts:
            try:
                decrypted_id = self.db.decrypt_field(
                    db_contact.signal_id,
                    db_contact.signal_id_salt
                )
                if decrypted_id == signal_id:
                    return Contact.from_db_model(db_contact, self.db)
            except Exception:
                continue
        return None
    
    def get_or_create_contact(self, signal_id: str, name: Optional[str] = None) -> Contact:
        """
        Get existing contact or create new one
        
        Args:
            signal_id: Signal ID
            name: Optional name (defaults to Signal ID)
            
        Returns:
            Contact (existing or new)
        """
        contact = self.get_contact_by_signal_id(signal_id)
        if contact:
            return contact
        
        # Create new contact
        contact = Contact(
            signal_id=signal_id,
            name=name or signal_id
        )
        return self.create_contact(contact)
    
    def update_contact(self, contact: Contact) -> Contact:
        """
        Update contact
        
        Args:
            contact: Contact to update
            
        Returns:
            Updated contact
        """
        db_contact = self.db.session.query(ContactModel).filter_by(id=contact.id).first()
        if not db_contact:
            raise ValueError(f"Contact with ID {contact.id} not found")
        
        # Update fields
        if contact.signal_id:
            signal_id_enc, signal_id_salt = self.db.encrypt_field(contact.signal_id)
            db_contact.signal_id = signal_id_enc
            db_contact.signal_id_salt = signal_id_salt
        
        db_contact.name = contact.name
        db_contact.notes = contact.notes
        
        self.db.session.commit()
        return contact
    
    def list_contacts(self) -> List[Contact]:
        """
        List all contacts
        
        Returns:
            List of contacts
        """
        db_contacts = self.db.session.query(ContactModel).all()
        return [Contact.from_db_model(c, self.db) for c in db_contacts]
    
    def delete_contact(self, contact_id: int) -> bool:
        """
        Delete contact
        
        Args:
            contact_id: Contact ID
            
        Returns:
            True if deleted
        """
        db_contact = self.db.session.query(ContactModel).filter_by(id=contact_id).first()
        if db_contact:
            self.db.session.delete(db_contact)
            self.db.session.commit()
            return True
        return False
