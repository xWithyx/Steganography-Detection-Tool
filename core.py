import math  # holt Mathe-Funktionen
from typing import Dict, Optional  # für Typ-Hinweise
import numpy as np  # für Zahl-Arrays
from PIL import Image  # für Bild-Ladung und Umwandlung

class LSBDetector:
    # Das ist unser Detektor für LSB-Stego in einem Kanal

    @staticmethod
    def compute_entropy(bits: np.ndarray) -> float:
        # Berechnet wie "ungeordnet" die Bits sind (Shannon-Entropie)
        total = bits.size
        if total == 0:
            return 0.0  # nix da, also 0
        p1 = bits.sum() / total  # Anteil an 1en
        p0 = 1 - p1  # Rest sind 0en
        entropy = 0.0
        for p in (p0, p1):
            if p > 0:
                entropy -= p * math.log2(p)  # Formel
        return entropy  # gib Entropie zurück

    @staticmethod
    def chi_square(bits: np.ndarray) -> float:
        # Einfacher Chi² Test gegen 50/50 Verteilung
        total = bits.size
        if total == 0:
            return 0.0
        obs0 = (bits == 0).sum()  # beobachtete 0en
        obs1 = (bits == 1).sum()  # beobachtete 1en
        exp = total / 2  # erwartet gleichviele
        return (obs0 - exp) ** 2 / exp + (obs1 - exp) ** 2 / exp

    def analyze_bitplane(self) -> Dict[int, Dict[str, float]]:
        # Schaut sich alle 8 Bit-Ebenen im Graustufenbild an
        gray = np.array(self.image.convert("L"))
        stats: Dict[int, Dict[str, float]] = {}
        for plane in range(8):
            mask = 1 << plane  # Maske für das Bit
            bits = ((gray & mask) > 0).astype(np.uint8).flatten()
            stats[plane] = {
                "entropy": self.compute_entropy(bits),  # Entropie
                "chi2": self.chi_square(bits),         # Chi-Quadrat
            }
        return stats  # gib Stats pro Ebene zurück

    def __init__(self, image: Image.Image, channel: str = 'blue') -> None:
        # beim Start Bild laden und Pixel merken
        self.image = image.convert('RGB')
        self.pixels = np.array(self.image)
        idx_map = {'red': 0, 'green': 1, 'blue': 2}
        # Kanal auswählen (standard: blau)
        self.channel_idx = idx_map.get(channel.lower(), 2)

    def extract_lsb(self) -> np.ndarray:
        # liest die niederwertigsten Bits vom Kanal aus
        channel = self.pixels[:, :, self.channel_idx]
        return channel & 1

    def bits_to_int(self, bits: np.ndarray) -> int:
        # wandelt eine Liste von Bits in eine ganze Zahl um
        bit_str = ''.join(str(int(b)) for b in bits)
        return int(bit_str, 2)

    def detect_message(
        self,
        max_bytes: int = 1024,
        printable_ratio: float = 0.8
    ) -> Optional[str]:
        # versucht die Nachricht zu finden und zu lesen
        bits = self.extract_lsb().flatten()
        if bits.size < 32:
            return None  # zu wenig Bits

        length = self.bits_to_int(bits[:32])  # erste 32 Bits = Länge
        if length <= 0 or length > max_bytes:
            return None  # ungültige Länge

        total_bits = 32 + length * 8
        if bits.size < total_bits:
            return None  # nicht genug Daten

        msg_bits = bits[32:total_bits]  # hier stecken die echten Bits
        byte_arr = np.packbits(msg_bits)
        try:
            msg = byte_arr.tobytes().decode('utf-8', errors='ignore')
        except Exception:
            return None

        # prüfe ob genug druckbare Zeichen drin sind
        printable = sum(32 <= ord(c) <= 126 for c in msg)
        if printable / len(msg) < printable_ratio:
            return None  # zu wenig lesbarer Text

        return msg  # gib die gefundene Nachricht zurück

def bit_plane_view(image: Image.Image, plane: int) -> Image.Image:
    # zeigt nur ein Bit pro Pixel, damit man versteckte Muster sieht
    arr = np.array(image.convert('L'))
    mask = 1 << plane
    plane_data = (arr & mask) * 255
    return Image.fromarray(plane_data)
