"""Abnahme (ZIEL M8): Abweichungsliste Referenzplan ↔ Nachbau.

Referenz = vorhandener Plan als Vektor-PDF (Hausstil). Nachbau = Planmodell des Programms; daraus wird das
Hausstil-PDF erzeugt und mit denselben Mustern ausgewertet wie die Referenz (symmetrischer Vergleich).
Verglichen werden Betriebsmittelkennzeichen (ohne Ortsangabe), Klemmen, SPS-Adressen und – nur in Richtung
Nachbau → Referenz – Artikelnummern. Ergebnis: Excel-Liste mit Bewertungsspalte für die Elektrofachkraft.

# ANNAHME A54: Referenzpläne liegen als Vektor-PDF mit Kennzeichen „=Anlage(+Ort)-BMK“, Klemmen „=Anlage-Xn:Nr“
# und SPS-Adressen „%I/%Q…“ vor (Hausstil wie Korpus); Artikel des Referenzplans sind ohne Stücklistenleser nicht
# vollständig aufzählbar, daher nur „Artikel des Nachbaus fehlt im Referenzplan“.
"""
from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
from pypdf import PdfReader

from .modell import Planmodell, RegelFehler

MUSTER = {
    "BMK": re.compile(r"=([A-Z0-9]+)(?:\+[A-Z0-9]+)?(-[A-Z]{1,3}\d+)(?![\d:.])"),
    "Klemme": re.compile(r"=([A-Z0-9]+)(?:\+[A-Z0-9]+)?(-X\w*:\d+)"),
    "SPS-Adresse": re.compile(r"(%[IQ][WB]?\d+(?:\.\d)?)"),
}
BEWERTUNGEN = ("Fehler im Nachbau", "Fehler im Referenzplan", "gleichwertig", "offen")
SPALTEN = ["Nr", "Bereich", "Merkmal", "Abweichung", "Bewertung", "Kommentar"]


def _text(pdf: Path) -> str:
    try:
        r = PdfReader(str(pdf))
    except Exception as e:                      # pypdf meldet beschädigte Dateien mit verschiedenen Fehlern
        raise RegelFehler(f"{pdf.name}: PDF nicht lesbar ({type(e).__name__}) – neu exportieren") from None
    text = "\n".join((s.extract_text() or "") for s in r.pages)
    if not text.strip():
        raise RegelFehler(f"{pdf.name}: kein Text im PDF (eingescannt?) – Referenzplan als Vektor-PDF exportieren")
    return text


def merkmale(text: str) -> dict[str, set[str]]:
    """Merkmale je Bereich; Kennzeichen ohne Ortsangabe (+…), weil Ort in Kopf und Schriftfeld steht."""
    aus: dict[str, set[str]] = {}
    for bereich, muster in MUSTER.items():
        aus[bereich] = {f"={t[0]}{t[1]}" if isinstance(t, tuple) else t for t in muster.findall(text)}
    return aus


def vergleiche(referenz: Path, m: Planmodell, stil: dict | None = None) -> dict[str, Any]:
    """-> {"abweichungen": [...], "kennzahlen": {Bereich: (gemeinsam, nur_ref, nur_nachbau, quote)}}."""
    from .hausstil import erzeuge_hausstil_pdf
    ref_text = _text(referenz)
    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / "nachbau.pdf"
        erzeuge_hausstil_pdf(m, str(pdf), stil)
        nach_text = _text(pdf)
    ref, nach = merkmale(ref_text), merkmale(nach_text)
    abw: list[dict[str, str]] = []
    kennzahlen: dict[str, tuple[int, int, int, float]] = {}
    for bereich in MUSTER:
        nur_ref, nur_nach, gemeinsam = ref[bereich] - nach[bereich], nach[bereich] - ref[bereich], ref[bereich] & nach[bereich]
        abw += [{"bereich": bereich, "merkmal": x, "abweichung": "nur im Referenzplan"} for x in sorted(nur_ref)]
        abw += [{"bereich": bereich, "merkmal": x, "abweichung": "nur im Nachbau"} for x in sorted(nur_nach)]
        alle = len(gemeinsam) + len(nur_ref) + len(nur_nach)
        kennzahlen[bereich] = (len(gemeinsam), len(nur_ref), len(nur_nach), round(len(gemeinsam) / alle, 3) if alle else 1.0)
    nummern = sorted({str(m.artikel.get(b.artikel, {}).get("artikelnummer") or b.artikel)
                      for b in m.betriebsmittel if b.artikel and b.artikel in m.artikel})
    fehlen = [n for n in nummern if n not in ref_text]
    abw += [{"bereich": "Artikel", "merkmal": n, "abweichung": "Artikel des Nachbaus fehlt im Referenzplan"} for n in fehlen]
    kennzahlen["Artikel"] = (len(nummern) - len(fehlen), 0, len(fehlen),
                             round((len(nummern) - len(fehlen)) / len(nummern), 3) if nummern else 1.0)
    return {"referenz": referenz.name, "abweichungen": abw, "kennzahlen": kennzahlen}


def schreibe_liste(ergebnis: dict[str, Any], pfad: str | Path) -> None:
    """Excel: Blatt „Abweichungen“ (Bewertung per Auswahlliste) und Blatt „Zusammenfassung“ (Übereinstimmung je Bereich)."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Abweichungen"
    ws.append(SPALTEN)
    for i, a in enumerate(ergebnis["abweichungen"], 1):
        ws.append([i, a["bereich"], a["merkmal"], a["abweichung"], "offen", ""])
    for c in ws[1]:
        c.font, c.fill = Font(bold=True), PatternFill("solid", fgColor="DDDDDD")
    dv = DataValidation(type="list", formula1='"' + ",".join(BEWERTUNGEN) + '"', allow_blank=False,
                        showErrorMessage=True, errorTitle="Bewertung", error="Bitte aus der Liste wählen")
    ws.add_data_validation(dv)
    dv.add(f"E2:E{max(2, len(ergebnis['abweichungen']) + 1)}")
    for spalte, breite in zip("ABCDEF", (6, 14, 28, 40, 24, 50)):
        ws.column_dimensions[spalte].width = breite
    wz = wb.create_sheet("Zusammenfassung")
    wz.append(["Bereich", "gemeinsam", "nur Referenz", "nur Nachbau", "Übereinstimmung"])
    for bereich, (g, r, n, q) in ergebnis["kennzahlen"].items():
        wz.append([bereich, g, r, n, q])
        wz.cell(wz.max_row, 5).number_format = "0.0%"
    wz.append([])
    wz.append([f"Referenz: {ergebnis['referenz']}. Artikel nur Richtung Nachbau → Referenz geprüft (A54). "
               f"Bewertung je Zeile durch Elektrofachkraft; „offen“ = noch nicht bewertet."])
    for c in wz[1]:
        c.font, c.fill = Font(bold=True), PatternFill("solid", fgColor="DDDDDD")
    wz.column_dimensions["A"].width = 16
    wb.save(pfad)
