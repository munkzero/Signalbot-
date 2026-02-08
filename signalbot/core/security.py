"""
Security Module for Signal Shop Bot
Handles encryption, decryption, and anti-tamper protection
"""

import os
import hashlib
import hmac
from typing import Optional, Tuple
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, padding as sym_padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import secrets


class SecurityManager:
    """Manages encryption, decryption, and security operations"""
    
    def __init__(self):
        self.backend = default_backend()
        
    def generate_key(self, password: str, salt: bytes) -> bytes:
        """
        Generate encryption key from password using PBKDF2
        
        Args:
            password: User password/PIN
            salt: Salt for key derivation
            
        Returns:
            32-byte encryption key
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=self.backend
        )
        return kdf.derive(password.encode())
    
    def encrypt_data(self, data: bytes, key: bytes) -> bytes:
        """
        Encrypt data using AES-256-CBC
        
        Args:
            data: Data to encrypt
            key: 32-byte encryption key
            
        Returns:
            Encrypted data with IV prepended
        """
        # Generate random IV
        iv = os.urandom(16)
        
        # Pad data to block size
        padder = sym_padding.PKCS7(128).padder()
        padded_data = padder.update(data) + padder.finalize()
        
        # Encrypt
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=self.backend
        )
        encryptor = cipher.encryptor()
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
        
        # Return IV + encrypted data
        return iv + encrypted_data
    
    def decrypt_data(self, encrypted_data: bytes, key: bytes) -> bytes:
        """
        Decrypt data using AES-256-CBC
        
        Args:
            encrypted_data: Data to decrypt (with IV prepended)
            key: 32-byte encryption key
            
        Returns:
            Decrypted data
        """
        # Extract IV and encrypted data
        iv = encrypted_data[:16]
        ciphertext = encrypted_data[16:]
        
        # Decrypt
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=self.backend
        )
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()
        
        # Unpad
        unpadder = sym_padding.PKCS7(128).unpadder()
        data = unpadder.update(padded_data) + unpadder.finalize()
        
        return data
    
    def encrypt_string(self, plaintext: str, password: str, salt: Optional[bytes] = None) -> Tuple[str, str]:
        """
        Encrypt a string using password-based encryption
        
        Args:
            plaintext: String to encrypt
            password: Password for encryption
            salt: Optional salt (generated if not provided)
            
        Returns:
            Tuple of (encrypted_base64, salt_base64)
        """
        if salt is None:
            salt = os.urandom(32)
        
        key = self.generate_key(password, salt)
        encrypted = self.encrypt_data(plaintext.encode(), key)
        
        return (
            base64.b64encode(encrypted).decode('utf-8'),
            base64.b64encode(salt).decode('utf-8')
        )
    
    def decrypt_string(self, encrypted_base64: str, password: str, salt_base64: str) -> str:
        """
        Decrypt a string using password-based encryption
        
        Args:
            encrypted_base64: Base64-encoded encrypted data
            password: Password for decryption
            salt_base64: Base64-encoded salt
            
        Returns:
            Decrypted string
        """
        encrypted = base64.b64decode(encrypted_base64)
        salt = base64.b64decode(salt_base64)
        
        key = self.generate_key(password, salt)
        decrypted = self.decrypt_data(encrypted, key)
        
        return decrypted.decode('utf-8')
    
    def hash_pin(self, pin: str, salt: Optional[bytes] = None) -> Tuple[str, str]:
        """
        Hash a PIN for secure storage
        
        Args:
            pin: PIN to hash
            salt: Optional salt (generated if not provided)
            
        Returns:
            Tuple of (hash_base64, salt_base64)
        """
        if salt is None:
            salt = os.urandom(32)
        
        # Use PBKDF2 for PIN hashing
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=self.backend
        )
        hash_value = kdf.derive(pin.encode())
        
        return (
            base64.b64encode(hash_value).decode('utf-8'),
            base64.b64encode(salt).decode('utf-8')
        )
    
    def verify_pin(self, pin: str, hash_base64: str, salt_base64: str) -> bool:
        """
        Verify a PIN against stored hash
        
        Args:
            pin: PIN to verify
            hash_base64: Stored hash (base64)
            salt_base64: Stored salt (base64)
            
        Returns:
            True if PIN matches, False otherwise
        """
        salt = base64.b64decode(salt_base64)
        stored_hash = base64.b64decode(hash_base64)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=self.backend
        )
        
        try:
            kdf.verify(pin.encode(), stored_hash)
            return True
        except:
            return False
    
    def generate_checksum(self, data: bytes) -> str:
        """
        Generate SHA-256 checksum for data integrity verification
        
        Args:
            data: Data to checksum
            
        Returns:
            Hex-encoded checksum
        """
        return hashlib.sha256(data).hexdigest()
    
    def verify_checksum(self, data: bytes, checksum: str) -> bool:
        """
        Verify data integrity using checksum
        
        Args:
            data: Data to verify
            checksum: Expected checksum
            
        Returns:
            True if checksum matches, False otherwise
        """
        return self.generate_checksum(data) == checksum
    
    def generate_hmac(self, data: bytes, key: bytes) -> str:
        """
        Generate HMAC for data authentication
        
        Args:
            data: Data to authenticate
            key: HMAC key
            
        Returns:
            Hex-encoded HMAC
        """
        h = hmac.new(key, data, hashlib.sha256)
        return h.hexdigest()
    
    def verify_hmac(self, data: bytes, signature: str, key: bytes) -> bool:
        """
        Verify HMAC signature
        
        Args:
            data: Data to verify
            signature: Expected HMAC signature
            key: HMAC key
            
        Returns:
            True if signature is valid, False otherwise
        """
        expected = self.generate_hmac(data, key)
        return hmac.compare_digest(expected, signature)


# Singleton instance
security_manager = SecurityManager()
