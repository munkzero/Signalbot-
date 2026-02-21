"""
Image optimization utility for fast Signal message delivery.
Aggressively resizes and compresses images to reduce upload time.
"""

import os


def optimize_image(image_path: str, max_width: int = 600, quality: int = 60, max_size_kb: int = 50) -> str:
    """
    Aggressively optimize images for fast Signal sending.

    Targets <50KB per image for fast send times. Iterates through lower
    quality levels until the file fits within max_size_kb.

    Args:
        image_path: Path to original image
        max_width: Maximum width in pixels (default 600)
        quality: Initial JPEG quality 1-100 (default 60 for speed)
        max_size_kb: Target maximum file size in KB (default 50)

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
                cached_size_kb = os.path.getsize(output_path) / 1024
                if cached_size_kb <= max_size_kb:
                    return output_path

        # Open and resize
        img = Image.open(image_path)

        if img.width > max_width:
            ratio = max_width / img.width
            new_dimensions = (max_width, int(img.height * ratio))
            img = img.resize(new_dimensions, Image.Resampling.LANCZOS)

        # Convert to RGB for JPEG output
        img = img.convert('RGB')

        # Try progressively lower quality until under max_size_kb
        quality_levels = sorted(set([quality, 50, 40, 30]), reverse=True)
        for q in quality_levels:
            img.save(output_path, 'JPEG', quality=q, optimize=True)
            size_kb = os.path.getsize(output_path) / 1024
            if size_kb <= max_size_kb:
                original_size = os.path.getsize(image_path) / 1024
                reduction = ((original_size - size_kb) / original_size) * 100
                print(
                    f"📉 Optimized: {os.path.basename(image_path)} "
                    f"{original_size:.0f}KB → {size_kb:.0f}KB ({reduction:.0f}% smaller, q={q})"
                )
                return output_path

        # If still too big, log warning and return best effort
        final_size_kb = os.path.getsize(output_path) / 1024
        original_size = os.path.getsize(image_path) / 1024
        print(
            f"⚠️ Image still large after optimization: "
            f"{os.path.basename(image_path)} {original_size:.0f}KB → {final_size_kb:.0f}KB"
        )
        return output_path

    except Exception as e:
        print(f"⚠️ Image optimization failed for {image_path}: {e}")
        return image_path  # Fallback to original
