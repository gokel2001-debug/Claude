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


def texte_der_seite(seite: Any) -> tuple[list[tuple[float, float, str]], float, float]:
    """(x_mm, y_mm, text) aller Textstücke in Anzeige-Lage (Mediabox-Ursprung und /Rotate berücksichtigt)
    sowie (Breite, Höhe) des angezeigten Blatts in mm."""
    box = seite.mediabox
    x0, y0 = float(box.left), float(box.bottom)
    w, h = float(box.width), float(box.height)
    drehung = int(seite.get("/Rotate", 0) or 0) % 360
    roh: list[tuple[float, float, str]] = []

    def besucher(text: str, cm: list[float], tm: list[float], _font: Any, _groesse: Any) -> None:
        if text and text.strip():
            x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4] - x0
            y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5] - y0
            roh.append((x, y, text.strip()))

    seite.extract_text(visitor_text=besucher)
    # PDF /Rotate dreht im Uhrzeigersinn: Benutzerkoordinaten -> Anzeigekoordinaten
    umrechnen = {0: lambda x, y: (x, y), 90: lambda x, y: (y, w - x), 180: lambda x, y: (w - x, h - y),
                 270: lambda x, y: (h - y, x)}.get(drehung, lambda x, y: (x, y))
    breite, hoehe = (h, w) if drehung in (90, 270) else (w, h)
    stuecke = []
    for x, y, t in roh:
        xa, ya = umrechnen(x, y)
        stuecke.append((round(xa / PT_JE_MM, 1), round(ya / PT_JE_MM, 1), t))
    return stuecke, breite / PT_JE_MM, hoehe / PT_JE_MM


def spaltenraster(texte: list[tuple[float, float, str]], hoehe_mm: float) -> tuple[int, float] | None:
    """Spaltenleiste: fortlaufende Ziffern (ab 0 oder 1) in gleichem Abstand am oberen Rand -> (Anzahl, Breite in mm).

    Einzelne Störzahlen (z. B. eine Seitenzahl) werden übergangen; gesucht wird die längste passende Folge.
    """
    kandidaten = sorted((x, int(t)) for x, y, t in texte if y > hoehe_mm - BAND_OBEN_MM and re.fullmatch(r"\d{1,2}", t))
    beste: list[float] = []
    for i, (x_start, n_start) in enumerate(kandidaten):
        if n_start not in (0, 1):
            continue
        folge, erwartet = [x_start], n_start + 1
        for x, n in kandidaten[i + 1:]:
            if n == erwartet:
                folge.append(x)
                erwartet += 1
        if len(folge) > len(beste):
            beste = folge
    if len(beste) < 4:
        return None
    abstaende = [b - a for a, b in itertools.pairwise(beste)]
    breite = statistics.median(abstaende)
    if max(abstaende) - min(abstaende) > 0.05 * breite:          # ungleichmäßig -> keine Spaltenleiste
        return None
    return len(beste), round(breite * 2) / 2                      # auf 0,5 mm


def _begriff_in(begriff: str, text: str) -> bool:
    return re.search(rf"(?<![\w]){re.escape(begriff)}(?![\w])", text) is not None


def schriftfeld(texte: list[tuple[float, float, str]]) -> tuple[list[tuple[str, float]], str | None, int | None]:
    """-> (gefundene Feldbezeichnungen mit x-Lage, Datumsformat, Jahr) aus dem unteren Band.

    Das Datum wird dem Feld „Datum“ zugeordnet (im selben Textstück oder rechts daneben in derselben Zeile);
    Daten in Änderungs-/Revisionsfeldern zählen nicht.
    """
    unten = sorted((x, y, t) for x, y, t in texte if y < BAND_UNTEN_MM)
    felder: list[tuple[str, float]] = []
    for x, _, t in unten:
        for begriff in SCHRIFTFELD_BEGRIFFE:
            if _begriff_in(begriff, t) and begriff not in [f for f, _ in felder]:
                felder.append((begriff, x + 1.5 * t.index(begriff)))     # Lage im Textstück (≈ 1,5 mm je Zeichen)
    fmt, jahr = None, None
    datum_label = [(x, y, t) for x, y, t in unten if _begriff_in("Datum", t)]
    for x, y, t in datum_label:
        kandidaten = [t[t.index("Datum"):]] + [t2 for x2, y2, t2 in unten if abs(y2 - y) < 3 and 0 < x2 - x < 60
                                                 and not _begriff_in("Änderung", t2) and not _begriff_in("Rev.", t2)]
        for k in kandidaten:
            mt = RE_DATUM.search(k)
            if mt:
                fmt = "TT.MM.JJJJ" if mt.group(3) else "JJJJ-MM-TT"
                jahr = int(mt.group(3) or mt.group(4))
                return felder, fmt, jahr
    return felder, fmt, jahr


def lese_geometrie(pdf: Path) -> dict[str, Any]:
    """Häufigste Werte über alle Seiten eines Plans; Anteil = Sicherheit innerhalb des Plans."""
    r = PdfReader(str(pdf))
    raster: Counter[tuple[int, float]] = Counter()
    feld_x: dict[str, list[float]] = {}
    formate: Counter[str] = Counter()
    jahre: Counter[int] = Counter()
    mit_text = 0
    for seite in r.pages:
        texte, _breite, hoehe = texte_der_seite(seite)
        mit_text += bool(texte)
        sr = spaltenraster(texte, hoehe)
        if sr:
            raster[sr] += 1
        felder, fmt, jahr = schriftfeld(texte)
        for f, x in felder:
            feld_x.setdefault(f, []).append(x)
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

    # Feld zählt, wenn es auf mindestens der Hälfte der Seiten steht; Reihenfolge nach mittlerer x-Lage
    stabil = sorted((statistics.mean(xs), f) for f, xs in feld_x.items() if len(xs) >= n / 2)
    (sr, a_sr), (fmt, _a_fmt), (jahr, a_jahr) = (haeufigst(c) for c in (raster, formate, jahre))
    return {
        "spaltenraster": f"{sr[0]} Spalten à {sr[1]:g} mm".replace(".", ",") if sr else None, "anteil_raster": a_sr,
        "schriftfeld_felder": ", ".join(f for _, f in stabil) if stabil else None,
        "anteil_schriftfeld": round(min((len(feld_x[f]) for _, f in stabil), default=0) / n, 2),
        "datumsformat": fmt, "schriftfeld_jahr": jahr, "anteil_jahr": a_jahr,
        "hinweis": None if mit_text else "keine Textebene (gescannt?) – Geometrie nicht lesbar",
    }
