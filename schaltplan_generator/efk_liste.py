"""Freigabeliste für die Elektrofachkraft (Überwachung Ü-E6) aus docs/OFFENE_PUNKTE.md erzeugen.

Aufruf: python efk_liste.py  ->  docs/EFK_FREIGABE.xlsx (zum Ausdrucken: Querformat, eine Seite breit).
Je Annahme eine Zeile: Klartext-Frage, vorgeschlagener Wert, Quelle, Feld „freigegeben (Name, Datum)“.
"""
from __future__ import annotations

import re
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.page import PageMargins

DOCS = Path(__file__).resolve().parent.parent / "docs"
SPALTEN = [("Nr.", 6), ("Frage an die Elektrofachkraft", 38), ("Vorgeschlagener Wert (so arbeitet die Software jetzt)", 52),
           ("Quelle / Begründung", 34), ("Alternative", 28), ("freigegeben (Name, Datum)", 22), ("Anmerkung / anderer Wert", 28)]


def _klartext(t: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[`*]|~~", "", t)).strip()


def annahmen(md: str) -> list[list[str]]:
    zeilen = []
    for z in md.splitlines():
        if re.match(r"^\| A\d+ \|", z):
            zellen = [_klartext(c) for c in z.strip().strip("|").split(" | ")]
            if len(zellen) >= 6:
                nr, annahme, quelle, alternative, _betroffen, frage = zellen[:6]
                frage = frage if frage not in ("", "–", "-") else "Annahme so freigeben?"
                zeilen.append([nr, frage, annahme, quelle, alternative])
    return zeilen


def schreibe(ziel: Path) -> int:
    daten = annahmen((DOCS / "OFFENE_PUNKTE.md").read_text(encoding="utf-8"))
    wb = Workbook()
    ws = wb.active
    ws.title = "Freigabe EFK"
    ws.append(["Freigabeliste Annahmen der Software (Stromlaufplan-Generator) – bitte je Zeile prüfen und abzeichnen"])
    ws["A1"].font = Font(bold=True, size=12)
    ws.append([n for n, _ in SPALTEN])
    duenn = Side(style="thin", color="999999")
    for c in ws[2]:
        c.font, c.fill = Font(bold=True), PatternFill("solid", fgColor="DDDDDD")
    for d in daten:
        ws.append([*d, "", ""])
    for zeile in ws.iter_rows(min_row=2):
        for c in zeile:
            c.alignment = Alignment(wrap_text=True, vertical="top")
            c.border = Border(left=duenn, right=duenn, top=duenn, bottom=duenn)
    for i, (_, breite) in enumerate(SPALTEN):
        ws.column_dimensions[chr(65 + i)].width = breite
    ws.print_title_rows = "2:2"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_margins = PageMargins(left=0.4, right=0.4, top=0.5, bottom=0.5)
    ws.freeze_panes = "A3"
    wb.save(ziel)
    return len(daten)


if __name__ == "__main__":
    n = schreibe(DOCS / "EFK_FREIGABE.xlsx")
    print(f"{n} Annahmen -> {DOCS / 'EFK_FREIGABE.xlsx'}")
