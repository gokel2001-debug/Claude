"""Geometrie und Schriftfeld aus Vektor-PDFs lernen (M5a, P7 Teil 1).

Liest je Seite die Textpositionen (pypdf, Millimeter ab linker unterer Blattecke) und leitet ab:
  * Spaltenraster: Ziffern 0…n-1 in der Spaltenleiste am oberen Rand -> Spaltenzahl und Spaltenbreite
  * Schriftfeld: bekannte Feldbezeichnungen im unteren Band, von links nach rechts
  * Datum im Schriftfeld: Format (TT.MM.JJJJ / JJJJ-MM-TT) und Jahr – genauer als „häufigstes Datum im Text“ (A16)
Je Plan wird der häufigste Wert über alle Seiten genommen; die Sicherheit über viele Pläne bildet das Hausprofil.
"""
from __future__ import annotations

import itertools
import re
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

from pypdf import PdfReader

PT_JE_MM = 72 / 25.4
BAND_OBEN_MM = 25       # Spaltenleiste: oberste 25 mm
BAND_UNTEN_MM = 40      # Schriftfeld: unterste 40 mm   # ANNAHME A39: Lage von Spaltenleiste/Schriftfeld
SCHRIFTFELD_BEGRIFFE = ("Datum", "Bearb.", "Gepr.", "Rev.", "Änderung", "Zeichnung-Nr.", "Projekt-Nr.", "Seite", "Norm")
RE_DATUM = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.((?:19|20)\d{2})\b|\b((?:19|20)\d{2})-(\d{2})-(\d{2})\b")


def texte_der_seite(seite: Any) -> list[tuple[float, float, str]]:
    """(x_mm, y_mm, text) aller Textstücke einer PDF-Seite."""
    stuecke: list[tuple[float, float, str]] = []

    def besucher(text, cm, tm, _font, _groesse):
        if text and text.strip():
            x = (tm[4] * cm[0] + tm[5] * cm[2] + cm[4]) / PT_JE_MM
            y = (tm[4] * cm[1] + tm[5] * cm[3] + cm[5]) / PT_JE_MM
            stuecke.append((round(x, 1), round(y, 1), text.strip()))

    seite.extract_text(visitor_text=besucher)
    return stuecke


def spaltenraster(texte: list[tuple[float, float, str]], hoehe_mm: float) -> tuple[int, float] | None:
    """Spaltenleiste: Ziffern 0,1,2,… am oberen Rand in gleichem Abstand -> (Anzahl, Breite in mm)."""
    ziffern = sorted((x, int(t)) for x, y, t in texte if y > hoehe_mm - BAND_OBEN_MM and re.fullmatch(r"\d{1,2}", t))
    folge = [x for x, _ in ziffern]
    nummern = [n for _, n in ziffern]
    if len(nummern) < 4 or nummern != list(range(len(nummern))):
        return None
    abstaende = [b - a for a, b in itertools.pairwise(folge)]
    breite = statistics.median(abstaende)
    if max(abstaende) - min(abstaende) > 0.05 * breite:          # ungleichmäßig -> keine Spaltenleiste
        return None
    return len(nummern), round(breite * 2) / 2                    # auf 0,5 mm


def schriftfeld(texte: list[tuple[float, float, str]]) -> tuple[list[str], str | None, int | None]:
    """-> (Feldbezeichnungen von links nach rechts, Datumsformat, Jahr) aus dem unteren Band."""
    unten = sorted((x, t) for x, y, t in texte if y < BAND_UNTEN_MM)
    felder: list[str] = []
    for _, t in unten:
        for begriff in SCHRIFTFELD_BEGRIFFE:
            if begriff in t and begriff not in felder:
                felder.append(begriff)
    fmt, jahr = None, None
    for _, t in unten:
        mt = RE_DATUM.search(t)
        if mt:
            fmt = "TT.MM.JJJJ" if mt.group(3) else "JJJJ-MM-TT"
            jahr = int(mt.group(3) or mt.group(4))
            break
    return felder, fmt, jahr


def lese_geometrie(pdf: Path) -> dict[str, Any]:
    """Häufigste Werte über alle Seiten eines Plans; Anteil = Sicherheit innerhalb des Plans."""
    r = PdfReader(str(pdf))
    raster: Counter[tuple[int, float]] = Counter()
    felder: Counter[tuple[str, ...]] = Counter()
    formate: Counter[str] = Counter()
    jahre: Counter[int] = Counter()
    for seite in r.pages:
        hoehe = float(seite.mediabox.height) / PT_JE_MM
        texte = texte_der_seite(seite)
        sr = spaltenraster(texte, hoehe)
        if sr:
            raster[sr] += 1
        f, fmt, jahr = schriftfeld(texte)
        if f:
            felder[tuple(f)] += 1
        if fmt:
            formate[fmt] += 1
        if jahr:
            jahre[jahr] += 1
    n = max(1, len(r.pages))

    def haeufigst(c: Counter) -> tuple[Any, float]:
        if not c:
            return None, 0.0
        wert, anzahl = c.most_common(1)[0]
        return wert, round(anzahl / n, 2)

    (sr, a_sr), (fe, a_fe), (fmt, _a_fmt), (jahr, a_jahr) = (haeufigst(c) for c in (raster, felder, formate, jahre))
    return {
        "spaltenraster": f"{sr[0]} Spalten à {sr[1]:g} mm".replace(".", ",") if sr else None, "anteil_raster": a_sr,
        "schriftfeld_felder": ", ".join(fe) if fe else None, "anteil_schriftfeld": a_fe,
        "datumsformat": fmt, "schriftfeld_jahr": jahr, "anteil_jahr": a_jahr,
    }
