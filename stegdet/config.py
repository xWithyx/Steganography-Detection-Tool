"""Configuration settings for the Steganography Detection Tool."""

# Allowed file extensions for image analysis
ALLOWED_EXTENSIONS = [".png", ".bmp"]

# Maximum image size in megapixels to prevent memory issues
MAX_IMAGE_SIZE_MP = 20  # 20 megapixels

# Default settings for message detection
DEFAULT_MAX_MESSAGE_BYTES = 1024
DEFAULT_PRINTABLE_RATIO = 0.8

# Default color channel for LSB analysis
DEFAULT_CHANNEL = "blue"