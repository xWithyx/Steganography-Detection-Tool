"""Streamlit GUI for the Steganography Detection Tool."""

import os
import streamlit as st
from pathlib import Path

from PIL import Image

from stegdet.core import LSBDetector, bit_plane_view
from stegdet.utils.file_utils import (
    scan_directory, export_to_csv, export_to_pdf, 
    create_temp_file, close_fd, validate_directory
)
from stegdet.config import MAX_IMAGE_SIZE_MP


def setup_page():
    """Configure the Streamlit page settings."""
    st.set_page_config(
        page_title="Steganography Detector",
        page_icon="🔍",
        layout="wide"
    )
    st.title("Steganography Detection Tool")
    st.markdown(
        """
        This tool helps detect hidden messages in images using LSB steganography analysis.
        Upload an image or analyze a directory of images.
        """
    )


def initialize_session_state():
    """Initialize session state variables if they don't exist."""
    if "current_image" not in st.session_state:
        st.session_state.current_image = None
    if "analysis_results" not in st.session_state:
        st.session_state.analysis_results = None
    if "batch_results" not in st.session_state:
        st.session_state.batch_results = None
    if "message_found" not in st.session_state:
        st.session_state.message_found = False


def single_image_analysis():
    """Handle single image upload and analysis."""
    st.header("Single Image Analysis")

    uploaded = st.file_uploader("Upload an image", type=["png", "bmp"])

    # Clear session state if no image is uploaded
    if not uploaded and st.session_state.current_image is not None:
        st.session_state.current_image = None
        st.session_state.message_found = False
        return None

    if uploaded:
        try:
            # Load the image
            img = Image.open(uploaded)

            # Check image size
            width, height = img.size
            megapixels = (width * height) / 1_000_000
            if megapixels > MAX_IMAGE_SIZE_MP:
                st.warning(f"Image exceeds recommended size limit ({megapixels:.1f}MP > {MAX_IMAGE_SIZE_MP}MP). Analysis may be slow.")

            # Store in session state
            st.session_state.current_image = img

            # Display the image immediately after upload
            st.image(img, caption="Uploaded image", use_container_width=True)

            return img
        except Exception as e:
            st.error(f"Error loading image: {str(e)}")

    return None


def analyze_single_channel(img, channel):
    """Analyze a single color channel of an image for steganography."""
    # Create detector for this channel
    detector = LSBDetector(img, channel=channel)

    # Detect LSB message
    message = detector.detect_message()

    # Create a container for this channel's results
    with st.expander(f"{channel.upper()} Channel Analysis", expanded=True):
        # Display message if found
        if message:
            st.success(f"Hidden message found in {channel} channel!")

            # Calculate message size for display area
            msg_lines = message.count('\n') + 1
            height = max(150, min(500, msg_lines * 20))  # Adaptive height

            st.text_area(
                f"Extracted message from {channel} channel", 
                message, 
                height=height,
                key=f"extracted_message_{channel}"
            )

            # Add download button for large messages
            if len(message) > 500:
                st.download_button(
                    f"Download full message from {channel} channel",
                    message,
                    file_name=f"extracted_message_{channel}.txt",
                    key=f"download_message_{channel}"
                )
        else:
            st.warning(f"No obvious LSB message detected in {channel} channel.")

        # Bit-plane visualization
        st.subheader(f"Bit-plane view ({channel} channel)")

        # Create bit plane images for the specific channel
        planes = [bit_plane_view(img, i, channel=channel) for i in range(8)]

        # Display in two rows of 4 columns
        col1, col2, col3, col4 = st.columns(4)
        col5, col6, col7, col8 = st.columns(4)

        cols = [col1, col2, col3, col4, col5, col6, col7, col8]

        for i, plane_img in enumerate(planes):
            cols[i].image(
                plane_img, 
                caption=f"Bit plane {i}", 
                use_container_width=True
            )

        # Display statistics
        st.subheader(f"Statistical Analysis ({channel} channel)")
        stats = detector.analyze_bitplane()

        # Create a DataFrame for better display
        import pandas as pd
        stats_df = pd.DataFrame([
            {"Bit Plane": i, "Entropy": stats[i]["entropy"], "Chi²": stats[i]["chi2"]}
            for i in range(8)
        ])

        st.dataframe(
            stats_df, 
            use_container_width=True,
            key=f"stats_df_{channel}"
        )

    return message


def analyze_image(img):
    """Analyze an image for steganography and display results for all channels."""
    if img is None:
        return

    with st.spinner("Analyzing all color channels..."):
        # Check all three color channels
        channels = ["red", "green", "blue"]

        # Store if any message was found
        any_message_found = False

        # Analyze each channel
        for ch in channels:
            message = analyze_single_channel(img, ch)
            if message:
                any_message_found = True

        # Store message status in session state
        st.session_state.message_found = any_message_found


def batch_analysis():
    """Handle batch analysis of multiple images in a directory."""
    st.header("Batch Analysis & Reports")

    # Directory input field
    directory = st.text_input("Directory with PNG/BMP files", "")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Scan Directory"):
            if not directory:
                st.error("Please specify a directory to scan.")
                return None

            # Validate directory
            valid_dir = validate_directory(Path(directory))
            if not valid_dir:
                st.error(f"Invalid directory: {directory}")
                return None

            # Scan the directory
            with st.spinner("Scanning..."):
                results = scan_directory(valid_dir)

            if not results:
                st.warning("No valid images found or no results to report.")
                return None

            # Store results in session state
            st.session_state.batch_results = results

            st.success(f"Finished — {len(results)} files processed.")

            # Display results
            display_batch_results(results)

            return results

    # If results exist in session state, display them
    if st.session_state.batch_results:
        with col2:
            if st.button("Clear Results"):
                st.session_state.batch_results = None
                st.rerun()

        display_batch_results(st.session_state.batch_results)

    return None


def display_batch_results(results):
    """Display batch analysis results and export options."""
    # Create a DataFrame for display
    import pandas as pd
    df = pd.DataFrame(results)

    # Create a more informative "Message Found" column
    def format_message_found(row):
        if row["message_found"]:
            return f"Yes ({row['channel_with_message']} channel)"
        return "No"

    # Apply the formatting function
    df["Message Found"] = df.apply(format_message_found, axis=1)

    # Create a basic view with essential information
    basic_view = df[["file", "Message Found", "entropy_avg", "chi2_max"]]
    st.dataframe(basic_view, use_container_width=True)

    # Option to show detailed channel-specific results
    if st.checkbox("Show channel-specific details"):
        # Create a detailed view with channel-specific information
        detailed_columns = [
            "file", "Message Found", 
            "red_entropy_avg", "green_entropy_avg", "blue_entropy_avg",
            "red_chi2_max", "green_chi2_max", "blue_chi2_max"
        ]
        st.dataframe(df[detailed_columns], use_container_width=True)

    # Export options
    st.subheader("Export Options")
    col1, col2 = st.columns(2)

    with col1:
        # Generate and offer CSV report
        csv_fd, csv_path = create_temp_file(".csv")
        export_to_csv(results, csv_path)
        with open(csv_path, "rb") as f:
            st.download_button(
                "Download CSV Report", 
                data=f, 
                file_name="stegdet_report.csv"
            )
        # Close the file descriptor
        close_fd(csv_fd)

    with col2:
        # Generate and offer PDF report
        pdf_fd, pdf_path = create_temp_file(".pdf")
        export_to_pdf(results, pdf_path)
        with open(pdf_path, "rb") as f:
            st.download_button(
                "Download PDF Report", 
                data=f, 
                file_name="stegdet_report.pdf"
            )
        # Close the file descriptor
        close_fd(pdf_fd)


def main():
    """Main application flow."""
    setup_page()
    initialize_session_state()

    # Create tabs for single image and batch analysis
    tab1, tab2 = st.tabs(["Single Image Analysis", "Batch Analysis"])

    with tab1:
        img = single_image_analysis()
        # Only proceed if we have an image (either newly uploaded or from session state)
        if img is not None or st.session_state.current_image is not None:
            # Use the current image from session state if available
            image_to_analyze = img if img is not None else st.session_state.current_image

            # Add analyze button
            analyze_button = st.button("Analyze Image")

            # Only analyze if button is clicked
            if analyze_button:
                analyze_image(image_to_analyze)
            # If analysis was already done and a message was found, show it
            elif st.session_state.message_found and st.session_state.current_image is not None:
                analyze_image(image_to_analyze)

    with tab2:
        batch_analysis()


if __name__ == "__main__":
    main()
