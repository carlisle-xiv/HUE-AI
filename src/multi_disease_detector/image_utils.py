"""
Image processing utilities for Multi Disease Detector.
Handles validation, encoding, resizing, and metadata extraction for medical images.
"""

import base64
import io
import logging
from typing import Dict, Any, Tuple, Optional
from PIL import Image

# Configure logging
logger = logging.getLogger(__name__)

# Configuration
MAX_IMAGE_SIZE_MB = 20
MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024
SUPPORTED_FORMATS = {'JPEG', 'PNG', 'WEBP', 'JPG'}
MAX_DIMENSION = 4096  # Max width or height for API transmission


class ImageValidationError(Exception):
    """Raised when image validation fails"""
    pass


def validate_image(image_bytes: bytes, filename: Optional[str] = None) -> Dict[str, Any]:
    """
    Validate image format, size, and dimensions.
    
    Args:
        image_bytes: Raw image bytes
        filename: Optional filename for better error messages
        
    Returns:
        Dict with validation results and metadata
        
    Raises:
        ImageValidationError: If validation fails
    """
    try:
        # Check file size
        size_mb = len(image_bytes) / (1024 * 1024)
        if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
            raise ImageValidationError(
                f"Image size ({size_mb:.2f}MB) exceeds maximum allowed size ({MAX_IMAGE_SIZE_MB}MB)"
            )
        
        # Try to open image with PIL
        try:
            image = Image.open(io.BytesIO(image_bytes))
        except Exception as e:
            raise ImageValidationError(f"Invalid image file: {str(e)}")
        
        # Check format
        format_name = image.format
        if format_name not in SUPPORTED_FORMATS:
            raise ImageValidationError(
                f"Unsupported image format: {format_name}. "
                f"Supported formats: {', '.join(SUPPORTED_FORMATS)}"
            )
        
        # Get dimensions
        width, height = image.size
        
        # Log validation success
        logger.info(
            f"Image validation successful: {format_name}, "
            f"{width}x{height}, {size_mb:.2f}MB"
        )
        
        return {
            "valid": True,
            "format": format_name,
            "width": width,
            "height": height,
            "size_bytes": len(image_bytes),
            "size_mb": round(size_mb, 2),
            "filename": filename
        }
        
    except ImageValidationError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during image validation: {str(e)}")
        raise ImageValidationError(f"Image validation failed: {str(e)}")


def resize_if_needed(image_bytes: bytes, max_dimension: int = MAX_DIMENSION) -> Tuple[bytes, bool]:
    """
    Resize image if dimensions exceed maximum, maintaining aspect ratio.
    
    Args:
        image_bytes: Raw image bytes
        max_dimension: Maximum width or height
        
    Returns:
        Tuple of (resized_image_bytes, was_resized)
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        width, height = image.size
        
        # Check if resizing is needed
        if width <= max_dimension and height <= max_dimension:
            return image_bytes, False
        
        # Calculate new dimensions maintaining aspect ratio
        if width > height:
            new_width = max_dimension
            new_height = int(height * (max_dimension / width))
        else:
            new_height = max_dimension
            new_width = int(width * (max_dimension / height))
        
        # Resize image
        resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Save to bytes
        output = io.BytesIO()
        format_name = image.format or 'JPEG'
        resized_image.save(output, format=format_name, quality=95)
        resized_bytes = output.getvalue()
        
        logger.info(
            f"Image resized: {width}x{height} → {new_width}x{new_height}, "
            f"{len(image_bytes)/(1024*1024):.2f}MB → {len(resized_bytes)/(1024*1024):.2f}MB"
        )
        
        return resized_bytes, True
        
    except Exception as e:
        logger.error(f"Error resizing image: {str(e)}")
        # Return original if resizing fails
        return image_bytes, False


def encode_image_to_base64(image_bytes: bytes) -> str:
    """
    Encode image bytes to base64 string for API transmission.
    
    Args:
        image_bytes: Raw image bytes
        
    Returns:
        Base64-encoded string
    """
    try:
        base64_string = base64.b64encode(image_bytes).decode('utf-8')
        logger.debug(f"Image encoded to base64: {len(base64_string)} characters")
        return base64_string
    except Exception as e:
        logger.error(f"Error encoding image to base64: {str(e)}")
        raise


def get_image_metadata(image_bytes: bytes) -> Dict[str, Any]:
    """
    Extract metadata from image (format, dimensions, EXIF if available).
    
    Args:
        image_bytes: Raw image bytes
        
    Returns:
        Dict with image metadata
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        
        metadata = {
            "format": image.format,
            "mode": image.mode,
            "width": image.size[0],
            "height": image.size[1],
            "size_bytes": len(image_bytes)
        }
        
        # Try to extract EXIF data (if available)
        try:
            exif_data = image._getexif()
            if exif_data:
                # Only include relevant EXIF tags (avoid sensitive data)
                metadata["has_exif"] = True
        except:
            metadata["has_exif"] = False
        
        return metadata
        
    except Exception as e:
        logger.error(f"Error extracting image metadata: {str(e)}")
        return {}


def prepare_image_for_api(image_bytes: bytes, filename: Optional[str] = None) -> Dict[str, Any]:
    """
    Complete image preparation pipeline: validate, resize if needed, and encode.
    
    Args:
        image_bytes: Raw image bytes
        filename: Optional filename
        
    Returns:
        Dict with prepared image data and metadata
        
    Raises:
        ImageValidationError: If validation fails
    """
    # Step 1: Validate
    validation_result = validate_image(image_bytes, filename)
    
    # Step 2: Resize if needed
    processed_bytes, was_resized = resize_if_needed(image_bytes)
    
    # Step 3: Encode
    base64_string = encode_image_to_base64(processed_bytes)
    
    # Step 4: Get metadata
    metadata = get_image_metadata(processed_bytes)
    
    return {
        "base64": base64_string,
        "metadata": metadata,
        "validation": validation_result,
        "was_resized": was_resized,
        "original_size_mb": validation_result["size_mb"],
        "processed_size_mb": round(len(processed_bytes) / (1024 * 1024), 2)
    }

