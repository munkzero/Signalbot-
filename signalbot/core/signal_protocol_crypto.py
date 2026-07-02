"""
Signal Protocol Cryptography module
Handles key generation, encryption/decryption, session management
"""

import os
import json
import logging
from typing import Dict, Tuple, Optional
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class KeyManager:
    """
    Manages Signal Protocol keys
    - Identity key pair generation
    - Prekey generation
    - Session state management
    """
    
    def __init__(self):
        self.backend = default_backend()
    
    def generate_identity_keypair(self) -> Dict:
        """
        Generate identity key pair for Signal account
        
        Returns:
            Dict with:
            - private_key: Private key bytes
            - public_key: Public key bytes
            - registration_id: Registration ID (random)
        """
        try:
            # Generate ECDH key pair (Curve25519)
            private_key = ec.generate_private_key(
                ec.SECP256R1(),
                self.backend
            )
            public_key = private_key.public_key()
            
            # Serialize keys
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            # Generate registration ID (random 14-bit number)
            registration_id = int.from_bytes(os.urandom(2), 'big') & 0x3FFF
            
            return {
                'private_key': private_pem,
                'public_key': public_pem,
                'registration_id': registration_id
            }
        
        except Exception as e:
            logger.error(f"Failed to generate identity keypair: {e}")
            raise
    
    def generate_prekeys(self, count: int = 100, start_id: int = 0) -> list:
        """
        Generate prekey bundle for key exchange
        
        Args:
            count: Number of prekeys to generate
            start_id: Starting prekey ID
            
        Returns:
            List of prekey dicts
        """
        try:
            prekeys = []
            
            for i in range(count):
                private_key = ec.generate_private_key(
                    ec.SECP256R1(),
                    self.backend
                )
                public_key = private_key.public_key()
                
                prekey_dict = {
                    'id': start_id + i,
                    'private_key': private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption()
                    ),
                    'public_key': public_key.public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo
                    )
                }
                prekeys.append(prekey_dict)
            
            return prekeys
        
        except Exception as e:
            logger.error(f"Failed to generate prekeys: {e}")
            raise
    
    def generate_signed_prekey(self, 
                              identity_private_key: bytes,
                              prekey_id: int = 1) -> Dict:
        """
        Generate signed prekey (authenticated)
        
        Args:
            identity_private_key: Identity private key bytes
            prekey_id: ID for this signed prekey
            
        Returns:
            Dict with signed prekey info
        """
        try:
            # Generate new key for signed prekey
            private_key = ec.generate_private_key(
                ec.SECP256R1(),
                self.backend
            )
            public_key = private_key.public_key()
            
            # Sign with identity key
            # (In real implementation, this uses Signal's specific signature)
            identity_key = serialization.load_pem_private_key(
                identity_private_key,
                password=None,
                backend=self.backend
            )
            
            signature = identity_key.sign(
                public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ),
                ec.ECDSA(hashes.SHA256())
            )
            
            return {
                'id': prekey_id,
                'private_key': private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ),
                'public_key': public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ),
                'signature': signature
            }
        
        except Exception as e:
            logger.error(f"Failed to generate signed prekey: {e}")
            raise
    
    def generate_ephemeral_keys(self) -> Dict:
        """
        Generate ephemeral keys for device linking
        
        Returns:
            Dict with ephemeral key info
        """
        try:
            private_key = ec.generate_private_key(
                ec.SECP256R1(),
                self.backend
            )
            public_key = private_key.public_key()
            
            # Generate random verification code
            verification_code = os.urandom(32).hex()
            
            return {
                'private_key': private_key,
                'public_key': public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ),
                'verification_code': verification_code,
                'encrypted_name': self._encrypt_device_name("ShopBot")
            }
        
        except Exception as e:
            logger.error(f"Failed to generate ephemeral keys: {e}")
            raise
    
    def _encrypt_device_name(self, device_name: str) -> str:
        """Encrypt device name for linking"""
        # Simple encryption for device name
        name_bytes = device_name.encode('utf-8')
        key = os.urandom(32)
        iv = os.urandom(16)
        
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=self.backend
        )
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(name_bytes) + encryptor.finalize()
        
        return (key + iv + ciphertext).hex()


class MessageCrypto:
    """
    Encrypt and decrypt messages using Signal Protocol
    """
    
    def __init__(self):
        self.backend = default_backend()
    
    def encrypt_message(self, 
                       plaintext: str,
                       session_key: bytes) -> bytes:
        """
        Encrypt message using session key
        
        Args:
            plaintext: Message text
            session_key: Symmetric key for encryption
            
        Returns:
            Encrypted message bytes
        """
        try:
            message_bytes = plaintext.encode('utf-8')
            iv = os.urandom(16)
            
            cipher = Cipher(
                algorithms.AES(session_key),
                modes.GCM(iv),
                backend=self.backend
            )
            encryptor = cipher.encryptor()
            ciphertext = encryptor.update(message_bytes) + encryptor.finalize()
            tag = encryptor.tag
            
            # Return: IV + tag + ciphertext
            return iv + tag + ciphertext
        
        except Exception as e:
            logger.error(f"Failed to encrypt message: {e}")
            raise
    
    def decrypt_message(self,
                       ciphertext: bytes,
                       session_key: bytes) -> str:
        """
        Decrypt message using session key
        
        Args:
            ciphertext: Encrypted message bytes (IV + tag + ciphertext)
            session_key: Symmetric key for decryption
            
        Returns:
            Decrypted message text
        """
        try:
            iv = ciphertext[:16]
            tag = ciphertext[16:32]
            encrypted = ciphertext[32:]
            
            cipher = Cipher(
                algorithms.AES(session_key),
                modes.GCM(iv, tag),
                backend=self.backend
            )
            decryptor = cipher.decryptor()
            plaintext = decryptor.update(encrypted) + decryptor.finalize()
            
            return plaintext.decode('utf-8')
        
        except Exception as e:
            logger.error(f"Failed to decrypt message: {e}")
            raise
    
    def derive_session_key(self,
                          shared_secret: bytes,
                          salt: bytes = b'Signal') -> bytes:
        """
        Derive symmetric session key from shared secret
        
        Args:
            shared_secret: ECDH shared secret
            salt: Salt for key derivation
            
        Returns:
            Derived session key (32 bytes)
        """
        try:
            from cryptography.hazmat.primitives.kdf.hkdf import HKDF
            
            hkdf = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                info=b'Signal',
                backend=self.backend
            )
            
            return hkdf.derive(shared_secret)
        
        except Exception as e:
            logger.error(f"Failed to derive session key: {e}")
            raise
