from pathlib import Path  # für datei-pfade
from typing import Dict, List  # für typen

import pandas as pd  # für datentabellen
from PIL import Image   # zum bilder öffnen
from fpdf import FPDF   # für pdf-erzeugung

from core import LSBDetector  # holt unseren detektor aus core.py

def scan_directory(path: Path) -> List[Dict]:
    """Scan PNG und BMP dateien in nem ordner und sammelt werte."""
    results: List[Dict] = []
    # suche alle .png und .bmp dateien
    for file in list(path.glob("*.png")) + list(path.glob("*.bmp")):
        try:
            img = Image.open(file)  # lade bild
            det = LSBDetector(img)  # starte detektor
            msg = det.detect_message() or ""  # versuch nachricht zu lesen
            stats = det.analyze_bitplane()    # chek bit-ebenen
            # mittelwert der entropie
            ent_avg = sum(s["entropy"] for s in stats.values()) / 8
            # größter chi² wert
            chi2_max = max(s["chi2"] for s in stats.values())
            results.append({
                "file": file.name,       # dateiname
                "message": msg,          # gefundene nachricht
                "entropy_avg": ent_avg,  # durchschn.entropie
                "chi2_max": chi2_max,    # max chi-quadrat
            })
        except Exception:
            continue  # wenn fehler, dann ignoriern
    return results  # gib ergebnisse zurück

def export_to_csv(results: List[Dict], out_path: Path) -> None:
    """Schreib die ergebnisse in ne CSV datei."""
    df = pd.DataFrame(results)      # mach ne tabelle
    df.to_csv(out_path, index=False)  # speicher ohne index

def export_to_pdf(results: List[Dict], out_path: Path) -> None:
    """Erzeugt eienen einfachen PDF-report."""
    pdf = FPDF(orientation="L")  # querformat
    pdf.add_page()               # neue seite
    pdf.set_font("Courier", size=10)  # schriftart

    # header zeile
    headers = ["File", "Message", "Entropy", "Chi²"]
    col_widths = [60, 100, 30, 30]
    for h, w in zip(headers, col_widths):
        pdf.cell(w, 8, h, border=1)  # macht die kopf-zellen
    pdf.ln()  # neue zeile

    # jede zeile aus den results
    for r in results:
        pdf.cell(col_widths[0], 6, r["file"][:20], border=1)       # kurzt dateiname
        pdf.cell(col_widths[1], 6, r["message"][:40], border=1)    # message abkürzen
        pdf.cell(col_widths[2], 6, f"{r['entropy_avg']:.2f}", border=1)
        pdf.cell(col_widths[3], 6, f"{r['chi2_max']:.1f}", border=1)
        pdf.ln()  # nächste zeile

    pdf.output(str(out_path))  # speicher das pdf
