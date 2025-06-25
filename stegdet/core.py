"""Core functionality for steganography detection."""

import math
from typing import Dict, Optional

import numpy as np
from PIL import Image

from stegdet.config import DEFAULT_CHANNEL


class LSBDetector:
    """Detector for LSB (Least Significant Bit) steganography in image channels."""

    @staticmethod
    def compute_entropy(bits: np.ndarray) -> float:
        """
        Calculate Shannon entropy of bit distribution.

        Args:
            bits: Array of bits (0s and 1s)

        Returns:
            float: Entropy value between 0.0 and 1.0
        """
        total = bits.size
        if total == 0:
            return 0.0

        # Vectorized implementation using NumPy
        counts = np.bincount(bits, minlength=2)
        probs = counts / counts.sum()
        # Only calculate log for non-zero probabilities
        entropy = -np.sum(probs[probs > 0] * np.log2(probs[probs > 0]))

        return entropy

    @staticmethod
    def chi_square(bits: np.ndarray) -> float:
        """
        Perform chi-square test against expected 50/50 distribution.

        Args:
            bits: Array of bits (0s and 1s)

        Returns:
            float: Chi-square statistic value
        """
        total = bits.size
        if total == 0:
            return 0.0

        obs0 = (bits == 0).sum()  # Observed 0s
        obs1 = (bits == 1).sum()  # Observed 1s
        exp = total / 2  # Expected equal distribution

        return (obs0 - exp) ** 2 / exp + (obs1 - exp) ** 2 / exp

    def analyze_bitplane(self) -> Dict[int, Dict[str, float]]:
        """
        Analyze all 8 bit planes in the specified color channel.

        Returns:
            Dict[int, Dict[str, float]]: Dictionary with statistics for each bit plane
                                         containing entropy and chi-square values
        """
        # Use the channel data from the pixels array
        channel_data = self.pixels[:, :, self.channel_idx]
        stats: Dict[int, Dict[str, float]] = {}

        for plane in range(8):
            # Extract bits from the specified plane
            bits = ((channel_data >> plane) & 1).astype(np.uint8).flatten()
            stats[plane] = {
                "entropy": self.compute_entropy(bits),
                "chi2": self.chi_square(bits),
            }

        return stats

    def __init__(self, image: Image.Image, channel: str = DEFAULT_CHANNEL) -> None:
        """
        Initialize the LSB detector with an image and channel.

        Args:
            image: PIL Image object to analyze
            channel: Color channel to analyze ('red', 'green', or 'blue')
        """
        self.image = image.convert('RGB')
        self.pixels = np.array(self.image)

        idx_map = {'red': 0, 'green': 1, 'blue': 2}
        self.channel_idx = idx_map.get(channel.lower(), 2)  # Default to blue

    def extract_lsb(self) -> np.ndarray:
        """
        Extract the least significant bits from the selected color channel.

        Returns:
            np.ndarray: Array of LSB values (0s and 1s)
        """
        channel = self.pixels[:, :, self.channel_idx]
        return channel & 1

    def bits_to_int(self, bits: np.ndarray) -> int:
        """
        Convert an array of bits to an integer.

        Args:
            bits: Array of bits (0s and 1s)

        Returns:
            int: Integer value represented by the bits
        """
        # More efficient implementation using NumPy's packbits
        return int.from_bytes(np.packbits(bits), byteorder="big")

    def detect_message(
        self,
        max_bytes: int = 1024,
        printable_ratio: float = 0.8
    ) -> Optional[str]:
        """
        Attempt to detect and extract a hidden message from the image.

        Args:
            max_bytes: Maximum message size in bytes to consider valid
            printable_ratio: Minimum ratio of printable characters required
                            for a message to be considered valid

        Returns:
            Optional[str]: Detected message or None if no valid message found
        """
        bits = self.extract_lsb().flatten()
        if bits.size < 32:
            return None  # Not enough bits

        # First 32 bits represent the message length
        length = self.bits_to_int(bits[:32])
        if length <= 0 or length > max_bytes:
            return None  # Invalid length

        total_bits = 32 + length * 8
        if bits.size < total_bits:
            return None  # Not enough data

        # Extract the actual message bits
        msg_bits = bits[32:total_bits]
        byte_arr = np.packbits(msg_bits)

        try:
            msg = byte_arr.tobytes().decode('utf-8', errors='ignore')
        except Exception:
            return None

        # Check if enough printable characters are present
        if not msg:
            return None  # Empty message

        printable = sum(32 <= ord(c) <= 126 for c in msg)
        if printable / len(msg) < printable_ratio:
            return None  # Not enough readable text

        return msg


def bit_plane_view(image: Image.Image, plane: int, channel: str = DEFAULT_CHANNEL) -> Image.Image:
    """
    Create a visualization of a specific bit plane to reveal hidden patterns.

    Args:
        image: PIL Image object to analyze
        plane: Bit plane to visualize (0-7, where 0 is LSB)
        channel: Color channel to analyze ('red', 'green', or 'blue')

    Returns:
        Image.Image: Visualization of the specified bit plane
    """
    # Convert to RGB and extract the specified channel
    rgb_image = image.convert('RGB')
    arr = np.array(rgb_image)

    # Map channel name to index
    idx_map = {'red': 0, 'green': 1, 'blue': 2}
    channel_idx = idx_map.get(channel.lower(), 2)  # Default to blue

    # Extract the specified channel
    channel_data = arr[:, :, channel_idx]

    # Extract the bit plane
    plane_data = ((channel_data >> plane) & 1) * 255
    return Image.fromarray(plane_data.astype(np.uint8))
