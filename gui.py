import streamlit as st  # holt streamlit, damit wir ne web-app machen
from PIL import Image    # zum Bilder öffnen
from pathlib import Path # für Dateipfade
import tempfile          # für temporäre dateien

from core import LSBDetector, bit_plane_view  # unser Detektor und Bitplane-Methode
from utils import export_to_csv, export_to_pdf, scan_directory  # fürs Batch & Reports

# richtet die seiteninfo oben an der App ein
st.set_page_config(page_title="Steganography Detector")
st.title("Steganography Detection Tool")  # zeigt den titel

# === Einzelbild-Modus ===
uploaded = st.file_uploader("Upload an image", type=["png", "bmp"])  # knopf zum Bild hochlade
if uploaded:
    img = Image.open(uploaded)  # Bild wird geladen

st.markdown("---")  # trennt mit ner Linie
st.header("Batch Analysis & Reports")  # Überschrift für Batch

# eingabefeld für Ordner-pfad
directory = st.text_input("Directory with PNG/BMP files", "")
# Knopf zum scannen drücken
if st.button("Scan Directory"):
    if directory:
        with st.spinner("Scanning..."):  # zeigt "Scanner ..." während es arbeitet
            results = scan_directory(Path(directory))  # Verzeichniss durchsuche
        st.success(f"Finished — {len(results)} files processed.")  # meldung wenn fertig
        st.dataframe(results)  # zeigt die Tabelle mit ergebnissen

        # === CSV Report zum rununterladen ===
        csv_fd, csv_path = tempfile.mkstemp(suffix=".csv")
        export_to_csv(results, Path(csv_path))  # schreibt CSV
        with open(csv_path, "rb") as f:
            st.download_button(
                "Download CSV Report", data=f, file_name="report.csv"
            )  # bereitstellt zum Download

        # === PDF Report zum runterladen ===
        pdf_fd, pdf_path = tempfile.mkstemp(suffix=".pdf")
        export_to_pdf(results, Path(pdf_path))  # schreibt PDF
        with open(pdf_path, "rb") as f:
            st.download_button(
                "Download PDF Report", data=f, file_name="report.pdf"
            )  # PDF zum runterladen
    else:
        st.error("Please specify a directory to scan.")  # Fehlermeldung wenn nix drinsteht

    # zeigt nochmal das originalbild an
    st.image(img, caption="Original image", use_container_width=True)

    # LSB-Nachricht erkennen
    detector = LSBDetector(img)
    message = detector.detect_message()

    if message:
        st.success("Hidden message found:")  # wenn was drin ist
        st.text_area("Message", message, height=150)  # zeigt die nachricht
    else:
        st.warning("No obvious LSB message detected.")  # warnung wenn nix gefunden

    # === Bit-plane Ansicht ===
    st.header("Bit-plane view")
    planes = [bit_plane_view(img, i) for i in range(8)]  # erstelle 8 bit-ebenen
    cols = st.columns(4)  # mach 4 spalten
    for i, plane_img in enumerate(planes):
        cols[i % 4].image(plane_img, caption=f"Bit plane {i}", use_container_width=True)
        # zeig jede ebene in ner spalte
