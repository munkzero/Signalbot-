"""
Signal API module - REST API calls to Signal servers
Handles registration, verification, and device linking
"""

import requests
import json
import logging
from typing import Dict, Tuple, Optional
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

# Signal server endpoints
SIGNAL_API_BASE = "https://api.signal.org"
SIGNAL_CAPTCHA_BASE = "https://signalcaptchas.org"


class SignalAPI:
    """
    Direct Signal server API communication
    Replaces signal-cli subprocess calls
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Signal-ShopBot/1.0',
            'Content-Type': 'application/json'
        })
    
    def request_registration(self, phone_number: str) -> str:
        """
        Request registration for phone number
        Returns captcha URL that user must open in browser
        
        Args:
            phone_number: Phone number like +64123456789
            
        Returns:
            Captcha URL string
        """
        try:
            # Step 1: Request code from Signal
            response = self.session.post(
                f"{SIGNAL_API_BASE}/v1/accounts/code/{phone_number}",
                json={"captcha": None},  # Will get captcha challenge
                timeout=10
            )
            
            if response.status_code == 402:
                # Captcha required
                data = response.json()
                captcha_token = data.get('captchaToken')
                
                # Generate captcha URL
                captcha_url = self._generate_captcha_url(captcha_token)
                return captcha_url
            
            elif response.status_code == 200:
                # No captcha needed (unlikely but possible)
                logger.info("✓ Registration started without captcha")
                return None
            
            else:
                raise RuntimeError(f"Registration request failed: {response.status_code} {response.text}")
        
        except Exception as e:
            logger.error(f"Failed to request registration: {e}")
            raise
    
    def _generate_captcha_url(self, captcha_token: str) -> str:
        """Generate captcha URL for user to visit"""
        params = {
            'token': captcha_token
        }
        captcha_url = f"{SIGNAL_CAPTCHA_BASE}/registration/generate.html?{urlencode(params)}"
        return captcha_url
    
    def verify_captcha(self, phone_number: str, captcha_token: str) -> bool:
        """
        Verify captcha token and request SMS code
        
        Args:
            phone_number: Phone number like +64123456789
            captcha_token: Token from captcha solve (from browser)
            
        Returns:
            True if SMS was sent successfully
        """
        try:
            response = self.session.post(
                f"{SIGNAL_API_BASE}/v1/accounts/code/{phone_number}",
                json={"captcha": captcha_token},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"✓ SMS code sent to {phone_number}")
                return True
            else:
                error = response.json().get('message', response.text)
                raise RuntimeError(f"Captcha verification failed: {error}")
        
        except Exception as e:
            logger.error(f"Failed to verify captcha: {e}")
            raise
    
    def verify_sms(self, phone_number: str, sms_code: str) -> Dict:
        """
        Verify SMS code and complete registration
        Returns registration credentials (access token, etc)
        
        Args:
            phone_number: Phone number like +64123456789
            sms_code: 6-digit code from SMS
            
        Returns:
            Registration response dict with credentials
        """
        try:
            response = self.session.put(
                f"{SIGNAL_API_BASE}/v1/accounts/code/{phone_number}",
                json={"code": sms_code},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"✓ {phone_number} successfully registered!")
                return response.json()
            else:
                error = response.json().get('message', response.text)
                raise RuntimeError(f"SMS verification failed: {error}")
        
        except Exception as e:
            logger.error(f"Failed to verify SMS: {e}")
            raise
    
    def request_linking(self) -> Tuple[str, str]:
        """
        Request device linking
        Returns (linking_uri, device_id)
        
        Returns:
            Tuple of (linking_uri for QR code, device_id)
        """
        try:
            # Generate ephemeral key pair for linking
            from signalbot.core.signal_protocol_crypto import KeyManager
            key_manager = KeyManager()
            ephemeral_keys = key_manager.generate_ephemeral_keys()
            
            # Request linking from Signal servers
            response = self.session.post(
                f"{SIGNAL_API_BASE}/v1/devices/link",
                json={
                    "verificationCode": ephemeral_keys['verification_code'],
                    "encryptedDeviceName": ephemeral_keys['encrypted_name']
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                # Construct linking URI
                linking_uri = self._construct_linking_uri(
                    data.get('uuid'),
                    ephemeral_keys['public_key']
                )
                return linking_uri, data.get('uuid')
            else:
                raise RuntimeError(f"Linking request failed: {response.status_code}")
        
        except Exception as e:
            logger.error(f"Failed to request linking: {e}")
            raise
    
    def _construct_linking_uri(self, uuid: str, public_key: str) -> str:
        """Construct tsdevice:// URI for QR code"""
        # Format: tsdevice://...
        linking_uri = f"tsdevice://?uuid={uuid}&publicKey={public_key}"
        return linking_uri
    
    def send_message(self, 
                    recipient: str, 
                    message: str,
                    encrypted_payload: bytes,
                    auth_token: str) -> bool:
        """
        Send encrypted message to recipient
        
        Args:
            recipient: Recipient phone number
            message: Message text
            encrypted_payload: Encrypted message bytes
            auth_token: Authentication token from registration
            
        Returns:
            True if sent successfully
        """
        try:
            headers = {'Authorization': f'Bearer {auth_token}'}
            
            response = self.session.post(
                f"{SIGNAL_API_BASE}/v1/messages/{recipient}",
                data=encrypted_payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                logger.debug(f"✓ Message sent to {recipient}")
                return True
            else:
                logger.warning(f"Message send returned: {response.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    def get_messages(self, auth_token: str) -> list:
        """
        Fetch pending messages from Signal servers
        
        Args:
            auth_token: Authentication token
            
        Returns:
            List of encrypted messages
        """
        try:
            headers = {'Authorization': f'Bearer {auth_token}'}
            
            response = self.session.get(
                f"{SIGNAL_API_BASE}/v1/messages",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                messages = response.json().get('messages', [])
                return messages
            else:
                logger.warning(f"Failed to fetch messages: {response.status_code}")
                return []
        
        except Exception as e:
            logger.error(f"Failed to get messages: {e}")
            return []
    
    def get_prekeys(self, recipient: str, auth_token: str) -> Dict:
        """
        Get recipient's prekey bundle for key exchange
        
        Args:
            recipient: Recipient phone number
            auth_token: Auth token
            
        Returns:
            Prekey bundle dict
        """
        try:
            headers = {'Authorization': f'Bearer {auth_token}'}
            
            response = self.session.get(
                f"{SIGNAL_API_BASE}/v2/keys/{recipient}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise RuntimeError(f"Failed to get prekeys: {response.status_code}")
        
        except Exception as e:
            logger.error(f"Failed to get prekeys: {e}")
            raise
    
    def upload_keys(self, 
                   identity_key: str,
                   prekeys: list,
                   signed_prekey: str,
                   auth_token: str) -> bool:
        """
        Upload public keys to Signal servers
        
        Args:
            identity_key: Public identity key
            prekeys: List of prekeys
            signed_prekey: Signed prekey
            auth_token: Auth token
            
        Returns:
            True if successful
        """
        try:
            headers = {'Authorization': f'Bearer {auth_token}'}
            
            payload = {
                'identityKey': identity_key,
                'prekeys': prekeys,
                'signedPreKey': signed_prekey
            }
            
            response = self.session.post(
                f"{SIGNAL_API_BASE}/v2/keys",
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                logger.info("✓ Keys uploaded to Signal servers")
                return True
            else:
                logger.error(f"Failed to upload keys: {response.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"Failed to upload keys: {e}")
            return False
