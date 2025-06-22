# Steganography Detection Tool

This project provides a simple Python utility to detect messages hidden with
least-significant-bit (LSB) steganography in PNG and BMP images.
A basic Streamlit GUI is included for easy use.

The tool can also perform batch analysis on directories and export
results as CSV or PDF reports.

## Requirements
- Python 3.10+
- Packages listed in `requirements.txt`

## Usage
Install dependencies and run the Streamlit app:

```bash
pip install -r requirements.txt
streamlit run gui.py
```

Upload an image via the interface. If a hidden ASCII message is found, it will
be displayed. The app also shows the bit-plane views of the uploaded image to
aid manual inspection. Use the directory input to scan all PNG/BMP files in a
folder and download the generated reports.
