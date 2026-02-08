"""
Image handling utilities
Handles image metadata removal, compression, and processing
"""

from PIL import Image
from PIL.ExifTags import TAGS
import os
from typing import Optional, Tuple
from ..config.settings import MAX_IMAGE_SIZE, ALLOWED_IMAGE_FORMATS, IMAGE_QUALITY, IMAGES_DIR


class ImageProcessor:
    """Handles image processing with privacy features"""
    
    def __init__(self):
        self.max_size = MAX_IMAGE_SIZE
        self.allowed_formats = ALLOWED_IMAGE_FORMATS
        self.quality = IMAGE_QUALITY
    
    def strip_metadata(self, image_path: str) -> str:
        """
        Strip all EXIF and metadata from image
        
        Args:
            image_path: Path to image file
            
        Returns:
            Path to cleaned image (overwrites original)
            
        Raises:
            ValueError: If image format not supported
        """
        try:
            # Open image
            img = Image.open(image_path)
            
            # Check format
            if img.format not in self.allowed_formats:
                raise ValueError(f"Unsupported image format: {img.format}")
            
            # Get image data without metadata
            data = list(img.getdata())
            image_without_exif = Image.new(img.mode, img.size)
            image_without_exif.putdata(data)
            
            # Save without metadata
            image_without_exif.save(image_path, format=img.format, quality=self.quality)
            
            return image_path
        except Exception as e:
            raise ValueError(f"Failed to process image: {e}")
    
    def compress_image(self, image_path: str, max_width: int = 1920, max_height: int = 1080) -> str:
        """
        Compress and resize image
        
        Args:
            image_path: Path to image file
            max_width: Maximum width
            max_height: Maximum height
            
        Returns:
            Path to compressed image
        """
        try:
            img = Image.open(image_path)
            
            # Calculate new size maintaining aspect ratio
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            # Save compressed image
            img.save(image_path, format=img.format, quality=self.quality, optimize=True)
            
            return image_path
        except Exception as e:
            raise ValueError(f"Failed to compress image: {e}")
    
    def process_product_image(self, source_path: str, product_id: int) -> str:
        """
        Process product image: strip metadata, compress, and save
        
        Args:
            source_path: Path to source image
            product_id: Product ID for filename
            
        Returns:
            Path to processed image (relative to IMAGES_DIR)
        """
        # Check file size
        file_size = os.path.getsize(source_path)
        if file_size > self.max_size:
            raise ValueError(f"Image too large: {file_size} bytes (max {self.max_size})")
        
        # Generate destination path
        ext = os.path.splitext(source_path)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png']:
            raise ValueError(f"Unsupported file extension: {ext}")
        
        dest_filename = f"product_{product_id}{ext}"
        dest_path = os.path.join(IMAGES_DIR, dest_filename)
        
        # Copy to destination
        if source_path != dest_path:
            import shutil
            shutil.copy2(source_path, dest_path)
        
        # Strip metadata
        self.strip_metadata(dest_path)
        
        # Compress
        self.compress_image(dest_path)
        
        return dest_filename
    
    def get_image_info(self, image_path: str) -> dict:
        """
        Get basic image information
        
        Args:
            image_path: Path to image
            
        Returns:
            Dictionary with image info
        """
        try:
            img = Image.open(image_path)
            return {
                'format': img.format,
                'mode': img.mode,
                'size': img.size,
                'width': img.width,
                'height': img.height
            }
        except Exception as e:
            return {'error': str(e)}
    
    def has_metadata(self, image_path: str) -> bool:
        """
        Check if image has EXIF metadata
        
        Args:
            image_path: Path to image
            
        Returns:
            True if metadata found, False otherwise
        """
        try:
            img = Image.open(image_path)
            exif = img.getexif()
            return len(exif) > 0
        except:
            return False
    
    def delete_image(self, image_filename: str):
        """
        Delete an image file
        
        Args:
            image_filename: Filename (relative to IMAGES_DIR)
        """
        image_path = os.path.join(IMAGES_DIR, image_filename)
        if os.path.exists(image_path):
            os.remove(image_path)


# Singleton instance
image_processor = ImageProcessor()
