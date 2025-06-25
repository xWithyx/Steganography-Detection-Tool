"""Command-line interface for the Steganography Detection Tool."""

import argparse
import logging
import sys
from pathlib import Path

try:
    from PIL import Image
    from stegdet.core import LSBDetector, bit_plane_view
    from stegdet.utils.file_utils import scan_directory, export_to_csv, export_to_pdf, validate_directory
except ImportError as e:
    module_name = str(e).split("'")[1] if "'" in str(e) else str(e)
    print(f"Error: Missing required dependency: {module_name}")
    print("Please install the required dependencies by running:")
    print("    pip install -r requirements.txt")
    sys.exit(1)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def analyze_single_image(image_path: Path, channel: str = 'blue', save_bit_planes: bool = False) -> None:
    """
    Analyze a single image for steganography.

    Args:
        image_path: Path to the image file
        channel: Color channel to analyze ('red', 'green', or 'blue')
        save_bit_planes: Whether to save bit plane visualizations
    """
    try:
        img = Image.open(image_path)
        print(f"Analyzing image: {image_path}")
        print(f"Image size: {img.size[0]}x{img.size[1]} pixels")

        # Detect LSB message
        detector = LSBDetector(img, channel=channel)
        message = detector.detect_message()

        if message:
            print("\nHidden message found:")
            print("-" * 40)
            print(message)
            print("-" * 40)
        else:
            print("\nNo obvious LSB message detected.")

        # Analyze bit planes
        stats = detector.analyze_bitplane()
        print("\nBit plane statistics:")
        print(f"{'Plane':>5} | {'Entropy':>10} | {'Chi²':>10}")
        print("-" * 30)
        for plane in range(8):
            print(f"{plane:>5} | {stats[plane]['entropy']:>10.4f} | {stats[plane]['chi2']:>10.2f}")

        # Save bit plane visualizations if requested
        if save_bit_planes:
            output_dir = image_path.parent / f"{image_path.stem}_bit_planes"
            output_dir.mkdir(exist_ok=True)

            for plane in range(8):
                plane_img = bit_plane_view(img, plane)
                output_path = output_dir / f"plane_{plane}.png"
                plane_img.save(output_path)

            print(f"\nBit plane visualizations saved to: {output_dir}")

    except Exception as e:
        logger.error(f"Error analyzing image {image_path}: {str(e)}")
        sys.exit(1)


def batch_analyze(directory: Path, output_format: str = 'csv') -> None:
    """
    Analyze all images in a directory.

    Args:
        directory: Path to the directory containing images
        output_format: Format for the output report ('csv', 'pdf', or 'both')
    """
    valid_dir = validate_directory(directory)
    if not valid_dir:
        logger.error(f"Invalid directory: {directory}")
        sys.exit(1)

    print(f"Scanning directory: {valid_dir}")
    results = scan_directory(valid_dir)

    if not results:
        print("No valid images found or no results to report.")
        return

    print(f"\nAnalyzed {len(results)} images:")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['file']}: ", end="")
        if result['message_found']:
            print("Message found!")
        else:
            print(f"No message (Entropy: {result['entropy_avg']:.2f}, Chi²: {result['chi2_max']:.2f})")

    # Export results
    if output_format in ('csv', 'both'):
        csv_path = valid_dir / "stegdet_report.csv"
        export_to_csv(results, csv_path)
        print(f"\nCSV report saved to: {csv_path}")

    if output_format in ('pdf', 'both'):
        pdf_path = valid_dir / "stegdet_report.pdf"
        export_to_pdf(results, pdf_path)
        print(f"\nPDF report saved to: {pdf_path}")


def main():
    """Main entry point for the command-line interface."""
    parser = argparse.ArgumentParser(description="Steganography Detection Tool")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Single image analysis command
    single_parser = subparsers.add_parser("analyze", help="Analyze a single image")
    single_parser.add_argument("image", type=str, help="Path to the image file")
    single_parser.add_argument("--channel", "-c", type=str, choices=["red", "green", "blue"], 
                              default="blue", help="Color channel to analyze")
    single_parser.add_argument("--save-bit-planes", "-b", action="store_true", 
                              help="Save bit plane visualizations")

    # Batch analysis command
    batch_parser = subparsers.add_parser("batch", help="Analyze all images in a directory")
    batch_parser.add_argument("directory", type=str, help="Path to the directory containing images")
    batch_parser.add_argument("--format", "-f", type=str, choices=["csv", "pdf", "both"], 
                             default="csv", help="Output format for the report")

    # Parse arguments
    args = parser.parse_args()

    if args.command == "analyze":
        analyze_single_image(Path(args.image), args.channel, args.save_bit_planes)
    elif args.command == "batch":
        batch_analyze(Path(args.directory), args.format)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
