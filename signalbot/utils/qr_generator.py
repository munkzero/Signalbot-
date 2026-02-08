"""
QR Code generation utilities
"""

import qrcode
from io import BytesIO
from typing import Optional
import base64


class QRCodeGenerator:
    """Generates QR codes for Monero addresses and payment info"""
    
    def __init__(self):
        self.qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
    
    def generate_payment_qr(
        self,
        address: str,
        amount: Optional[float] = None,
        recipient_name: Optional[str] = None
    ) -> bytes:
        """
        Generate QR code for Monero payment
        
        Args:
            address: Monero address
            amount: Optional payment amount
            recipient_name: Optional recipient name
            
        Returns:
            PNG image data as bytes
        """
        # Build Monero URI
        # Format: monero:<address>?tx_amount=<amount>&recipient_name=<name>
        uri = f"monero:{address}"
        
        params = []
        if amount:
            params.append(f"tx_amount={amount}")
        if recipient_name:
            params.append(f"recipient_name={recipient_name}")
        
        if params:
            uri += "?" + "&".join(params)
        
        # Generate QR code
        self.qr.clear()
        self.qr.add_data(uri)
        self.qr.make(fit=True)
        
        img = self.qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def generate_simple_qr(self, data: str) -> bytes:
        """
        Generate simple QR code from data
        
        Args:
            data: Data to encode
            
        Returns:
            PNG image data as bytes
        """
        self.qr.clear()
        self.qr.add_data(data)
        self.qr.make(fit=True)
        
        img = self.qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def generate_qr_base64(self, data: str) -> str:
        """
        Generate QR code and return as base64 string
        
        Args:
            data: Data to encode
            
        Returns:
            Base64-encoded PNG image
        """
        qr_bytes = self.generate_simple_qr(data)
        return base64.b64encode(qr_bytes).decode('utf-8')


# Singleton instance
qr_generator = QRCodeGenerator()
