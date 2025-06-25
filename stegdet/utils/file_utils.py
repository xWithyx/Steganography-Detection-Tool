"""File utility functions for the Steganography Detection Tool."""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from PIL import Image
from fpdf import FPDF

from stegdet.config import ALLOWED_EXTENSIONS, MAX_IMAGE_SIZE_MP
from stegdet.core import LSBDetector

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def is_valid_image(file_path: Path) -> bool:
    """
    Check if a file is a valid image for analysis.

    Args:
        file_path: Path to the image file

    Returns:
        bool: True if the file is valid, False otherwise
    """
    # Check file extension
    if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        return False

    # Check if file exists and is readable
    if not file_path.is_file():
        return False

    try:
        # Check image size to prevent memory issues
        with Image.open(file_path) as img:
            width, height = img.size
            megapixels = (width * height) / 1_000_000
            if megapixels > MAX_IMAGE_SIZE_MP:
                logger.warning(f"Image {file_path} exceeds maximum size limit ({megapixels:.1f}MP > {MAX_IMAGE_SIZE_MP}MP)")
                return False
            return True
    except Exception as e:
        logger.warning(f"Error opening image {file_path}: {str(e)}")
        return False


def validate_directory(directory: Path) -> Optional[Path]:
    """
    Validate that a directory exists and is accessible.

    Args:
        directory: Path to the directory

    Returns:
        Optional[Path]: Validated directory path or None if invalid
    """
    try:
        # Convert to absolute path to prevent directory traversal
        abs_path = directory.resolve()

        # Check if directory exists and is accessible
        if not abs_path.is_dir():
            logger.warning(f"Directory does not exist: {abs_path}")
            return None

        # Try to list contents to verify permissions
        list(abs_path.iterdir())
        return abs_path
    except (PermissionError, FileNotFoundError) as e:
        logger.warning(f"Cannot access directory {directory}: {str(e)}")
        return None


def scan_directory(path: Path) -> List[Dict]:
    """
    Scan a directory for image files and analyze them for steganography.

    Args:
        path: Directory path to scan

    Returns:
        List[Dict]: List of dictionaries containing analysis results for each file
    """
    results: List[Dict] = []

    # Validate directory
    valid_path = validate_directory(path)
    if not valid_path:
        return results

    # Find all valid image files
    image_files = []
    for ext in ALLOWED_EXTENSIONS:
        image_files.extend(list(valid_path.glob(f"*{ext}")))

    logger.info(f"Found {len(image_files)} image files in {valid_path}")

    # Define color channels to analyze
    channels = ["red", "green", "blue"]

    for file in image_files:
        try:
            # Validate image before processing
            if not is_valid_image(file):
                continue

            # Load the image
            img = Image.open(file)

            # Initialize result dictionary for this file
            file_result = {
                "file": file.name,
                "message_found": False,
                "message": "",
                "channel_with_message": "",
            }

            # Analyze each color channel
            for channel in channels:
                # Create detector for this channel
                detector = LSBDetector(img, channel=channel)

                # Try to detect hidden message
                msg = detector.detect_message() or ""

                # If message found, store it
                if msg and not file_result["message_found"]:
                    file_result["message_found"] = True
                    file_result["message"] = msg
                    file_result["channel_with_message"] = channel

                # Analyze bit planes
                stats = detector.analyze_bitplane()

                # Calculate average entropy across all bit planes
                entropy_avg = sum(s["entropy"] for s in stats.values()) / 8

                # Find maximum chi-square value
                chi2_max = max(s["chi2"] for s in stats.values())

                # Store channel-specific results
                file_result[f"{channel}_entropy_avg"] = entropy_avg
                file_result[f"{channel}_chi2_max"] = chi2_max

            # Calculate overall statistics
            file_result["entropy_avg"] = (
                file_result["red_entropy_avg"] + 
                file_result["green_entropy_avg"] + 
                file_result["blue_entropy_avg"]
            ) / 3

            file_result["chi2_max"] = max(
                file_result["red_chi2_max"],
                file_result["green_chi2_max"],
                file_result["blue_chi2_max"]
            )

            # Add to results
            results.append(file_result)

        except Exception as e:
            # Log the error instead of silently continuing
            logger.warning(f"Error processing {file}: {str(e)}")
            continue

    return results


def export_to_csv(results: List[Dict], out_path: Path) -> None:
    """
    Export analysis results to a CSV file.

    Args:
        results: List of dictionaries containing analysis results
        out_path: Path where the CSV file will be saved
    """
    df = pd.DataFrame(results)
    df.to_csv(out_path, index=False)


def export_to_pdf(results: List[Dict], out_path: Path) -> None:
    """
    Generate a PDF report from analysis results.

    Args:
        results: List of dictionaries containing analysis results
        out_path: Path where the PDF file will be saved
    """
    # Determine orientation based on content
    orientation = "L" if len(results) > 5 or any(len(r.get("message", "")) > 40 for r in results) else "P"

    # Initialize PDF with appropriate orientation
    pdf = FPDF(orientation=orientation)
    pdf.add_page()
    pdf.set_font("Courier", size=10)

    # Define table headers and column widths (adjusted based on orientation)
    if orientation == "L":  # Landscape
        headers = ["File", "Message Found", "Channel", "Message", "Entropy", "Chi²"]
        col_widths = [40, 25, 20, 120, 30, 30]
    else:  # Portrait
        headers = ["File", "Message Found", "Channel", "Message", "Entropy", "Chi²"]
        col_widths = [30, 25, 20, 50, 30, 30]

    # Create header row
    for header, width in zip(headers, col_widths):
        pdf.cell(width, 8, header, border=1)
    pdf.ln()

    # Add data rows
    for result in results:
        # Truncate long filenames and messages to fit in cells
        filename = result["file"]
        message = result.get("message", "")
        message_found = "Yes" if result.get("message_found", False) else "No"
        channel = result.get("channel_with_message", "-")

        # Adjust truncation based on orientation
        max_filename_len = 15 if orientation == "L" else 12
        max_message_len = 60 if orientation == "L" else 25

        if len(filename) > max_filename_len:
            filename = filename[:max_filename_len-3] + "..."

        if len(message) > max_message_len:
            message = message[:max_message_len-3] + "..."

        pdf.cell(col_widths[0], 6, filename, border=1)
        pdf.cell(col_widths[1], 6, message_found, border=1)
        pdf.cell(col_widths[2], 6, channel, border=1)
        pdf.cell(col_widths[3], 6, message, border=1)
        pdf.cell(col_widths[4], 6, f"{result.get('entropy_avg', 0):.2f}", border=1)
        pdf.cell(col_widths[5], 6, f"{result.get('chi2_max', 0):.1f}", border=1)
        pdf.ln()

    # Add a second page with channel-specific details
    pdf.add_page()
    pdf.set_font("Courier", size=10)
    pdf.cell(0, 10, "Channel-Specific Analysis", ln=True)
    pdf.ln(5)

    # Define headers for channel-specific details
    channel_headers = ["File", "Red Entropy", "Red Chi²", "Green Entropy", "Green Chi²", "Blue Entropy", "Blue Chi²"]
    channel_widths = [40, 25, 25, 25, 25, 25, 25] if orientation == "L" else [30, 25, 25, 25, 25, 25, 25]

    # Create header row for channel-specific details
    for header, width in zip(channel_headers, channel_widths):
        pdf.cell(width, 8, header, border=1)
    pdf.ln()

    # Add data rows for channel-specific details
    for result in results:
        filename = result["file"]
        if len(filename) > max_filename_len:
            filename = filename[:max_filename_len-3] + "..."

        pdf.cell(channel_widths[0], 6, filename, border=1)
        pdf.cell(channel_widths[1], 6, f"{result.get('red_entropy_avg', 0):.2f}", border=1)
        pdf.cell(channel_widths[2], 6, f"{result.get('red_chi2_max', 0):.1f}", border=1)
        pdf.cell(channel_widths[3], 6, f"{result.get('green_entropy_avg', 0):.2f}", border=1)
        pdf.cell(channel_widths[4], 6, f"{result.get('green_chi2_max', 0):.1f}", border=1)
        pdf.cell(channel_widths[5], 6, f"{result.get('blue_entropy_avg', 0):.2f}", border=1)
        pdf.cell(channel_widths[6], 6, f"{result.get('blue_chi2_max', 0):.1f}", border=1)
        pdf.ln()

    # Save the PDF
    pdf.output(str(out_path))


def create_temp_file(suffix: str) -> tuple:
    """
    Create a temporary file and return its file descriptor and path.

    Args:
        suffix: File extension for the temporary file

    Returns:
        tuple: (file_descriptor, file_path)
    """
    import tempfile
    fd, path = tempfile.mkstemp(suffix=suffix)
    return fd, Path(path)


def close_fd(fd: int) -> None:
    """
    Safely close a file descriptor.

    Args:
        fd: File descriptor to close
    """
    try:
        os.close(fd)
    except Exception as e:
        logger.warning(f"Error closing file descriptor: {str(e)}")
