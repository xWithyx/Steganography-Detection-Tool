# Steganography Detection Tool

A tool for detecting hidden messages in images using LSB (Least Significant Bit) steganography analysis.

## Features

- Analyze single images for hidden messages
- Batch process directories of images
- Visualize bit planes to reveal hidden patterns
- Generate CSV and PDF reports
- Command-line interface and Streamlit web interface
- Statistical analysis with entropy and chi-square tests

## Project Structure

```
stegdet/
├── __init__.py        # Package initialization
├── __main__.py        # CLI entry point
├── config.py          # Configuration settings
├── core.py            # Core detection algorithms
└── utils/             # Utility functions
    ├── __init__.py
    └── file_utils.py  # File operations and reporting
streamlit_app.py       # Streamlit web interface
```

## Requirements
- Python 3.7+
- NumPy
- Pillow (PIL)
- Pandas
- FPDF
- Streamlit

## Installation

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Web Interface

Run the Streamlit app:

```bash
streamlit run streamlit_app.py
```

This will open a web interface where you can:
- Upload and analyze individual images
- Scan directories of images
- View bit plane visualizations
- Generate and download reports

### Command Line Interface

The tool can be used from the command line:

```bash
# Analyze a single image
python -m stegdet analyze path/to/image.png --channel blue --save-bit-planes

# Batch analyze a directory
python -m stegdet batch path/to/directory --format both
```

#### CLI Commands:

- `analyze`: Analyze a single image
  - Arguments:
    - `image`: Path to the image file
    - `--channel, -c`: Color channel to analyze (red, green, blue)
    - `--save-bit-planes, -b`: Save bit plane visualizations

- `batch`: Analyze all images in a directory
  - Arguments:
    - `directory`: Path to the directory containing images
    - `--format, -f`: Output format for the report (csv, pdf, both)

## How It Works

The tool analyzes images for potential hidden messages using several techniques:

1. **LSB Extraction**: Extracts the least significant bit from each pixel in the selected color channel.
2. **Message Detection**: Attempts to decode the LSB data as a UTF-8 message.
3. **Statistical Analysis**: 
   - **Entropy**: Measures the randomness of the bit distribution.
   - **Chi-Square Test**: Tests against the expected 50/50 distribution.
4. **Bit Plane Visualization**: Creates visual representations of each bit plane to reveal patterns.

## Security Considerations

- The tool includes safeguards against processing excessively large images (>20MP by default).
- Directory paths are validated to prevent directory traversal attacks.
- Error handling is implemented to prevent crashes from malformed inputs.
