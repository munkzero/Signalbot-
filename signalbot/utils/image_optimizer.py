"""
Image optimization utility for fast Signal message delivery.
Aggressively resizes and compresses images to reduce upload time.
"""

import os


def optimize_image(image_path: str, max_width: int = 600, quality: int = 60) -> str:
    """
    Aggressively optimize images for fast Signal sending.

    Args:
        image_path: Path to original image
        max_width: Maximum width in pixels (default 600)
        quality: JPEG quality 1-100 (default 60 for speed)

    Returns:
        Path to optimized image (or original if optimization fails)
    """
    try:
        from PIL import Image

        # Skip if already optimized
        if '.optimized.' in image_path:
            return image_path

        if not os.path.exists(image_path):
            print(f"⚠️ Image not found: {image_path}")
            return image_path

        # Generate optimized filename
        base, _ext = os.path.splitext(image_path)
        output_path = f"{base}.optimized.jpg"

        # Skip if cached and newer than source
        if os.path.exists(output_path):
            if os.path.getmtime(output_path) >= os.path.getmtime(image_path):
                return output_path

        # Open and resize
        img = Image.open(image_path)

        if img.width > max_width:
            ratio = max_width / img.width
            new_dimensions = (max_width, int(img.height * ratio))
            img = img.resize(new_dimensions, Image.Resampling.LANCZOS)

        # Save optimized version
        img.convert('RGB').save(output_path, 'JPEG', quality=quality, optimize=True)

        # Log size reduction
        original_size = os.path.getsize(image_path) / 1024
        new_size_kb = os.path.getsize(output_path) / 1024
        reduction = ((original_size - new_size_kb) / original_size) * 100
        print(
            f"📉 Optimized: {os.path.basename(image_path)} "
            f"{original_size:.0f}KB → {new_size_kb:.0f}KB ({reduction:.0f}% smaller)"
        )

        return output_path

    except Exception as e:
        print(f"⚠️ Image optimization failed for {image_path}: {e}")
        return image_path  # Fallback to original
