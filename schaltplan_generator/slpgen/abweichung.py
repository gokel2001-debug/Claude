"""Abnahme (ZIEL M8): Abweichungsliste Referenzplan ↔ Nachbau.

Referenz = vorhandener Plan als Vektor-PDF (Hausstil). Nachbau = Planmodell des Programms; daraus wird das
Hausstil-PDF erzeugt und mit denselben Mustern ausgewertet wie die Referenz (symmetrischer Vergleich).
Verglichen werden (1) Mengen: Betriebsmittelkennzeichen, Klemmen, SPS-Adressen; (2) Zuordnungen aus Tabellenzeilen:
SPS-Belegung (Adresse -> Gerät/Klemme/Funktionstext) und Artikel je Gerät (Stückliste). Ergebnis: Excel-Liste mit
Bewertungsspalte für die Elektrofachkraft. Kein Abnahmeurteil über Verschaltung, Absicherung, Querschnitte (M8b).

# ANNAHME A54: Referenzpläne liegen als Vektor-PDF im Hausstil vor (Kennzeichen „=Anlage(+Ort)-BMK“ oder BMK ohne
# Vorsatz mit Anlage im Schriftfeld, Klemmen „Xn:Nr“, SPS-Adressen „%I/%IX/%IW…“, SPS-Kartentabelle und Stückliste
# als Tabellen mit Spalten wie im Hausstil); andere Schreibweisen ergeben „nicht auswertbar“ statt 100 %.
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
    "BMK": re.compile(r"=([A-Z0-9]+(?:\+[A-Z0-9]+)?)(-[A-Z]{1,3}\d+)(?![\d:.])"),
    "Klemme": re.compile(r"=([A-Z0-9]+(?:\+[A-Z0-9]+)?)(-X\w*:\d+)"),
    "SPS-Adresse": re.compile(r"%([IQ])[XBWD]?(\d+(?:\.\d+)?)"),     # %I0.1, %IX0.1, %QW4, %I0.10
}
# Kennzeichen ohne Anlagenvorsatz (EPLAN: Anlage steht nur im Schriftfeld der Seite)
OHNE_ANLAGE = {"BMK": re.compile(r"(?<![\w=+/.:-])(-[A-Z]{1,3}\d+)(?![\w:.])"),
               "Klemme": re.compile(r"(?<![\w=+/.:-])(-?X\d+:\d+)(?![\w.])")}
ANLAGE_SEITE = re.compile(r"=([A-Z0-9]{2,})(?![\w-])")
BEWERTUNGEN = ("Fehler im Nachbau", "Fehler im Referenzplan", "gleichwertig", "offen")
SPALTEN = ["Nr", "Bereich", "Merkmal", "Abweichung", "Bewertung", "Kommentar"]


def _zeilen(seite: Any, toleranz: float = 1.2) -> list[list[str]]:
    """Tabellenzeilen einer PDF-Seite: Textstücke nach Höhe gruppiert, von links nach rechts (pypdf liefert Zellen
    sonst einzeln). Rückgabe: Liste von Zellen je Zeile."""
    teile: list[tuple[int, float, str]] = []

    def sammle(text: str, cm: list[float], tm: list[float], _fd: Any, _fs: Any) -> None:
        if text.strip():
            x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
            y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
            teile.append((round(y / toleranz), x, text.strip()))

    seite.extract_text(visitor_text=sammle)
    reihen: dict[int, list[tuple[float, str]]] = {}
    for y, x, t in teile:
        reihen.setdefault(y, []).append((x, t))
    return [[t for _, t in sorted(r)] for _, r in sorted(reihen.items(), reverse=True)]


RE_ADRESSE_ZELLE = re.compile(r"^%[IQ][XBWD]?\d+(?:\.\d+)?$")
RE_VERWEIS = re.compile(r"^=?[A-Z0-9]*/\d+\.\d+$")              # Seitenverweise (=B01/1.3) dürfen abweichen
RE_MENGE = re.compile(r"^\d+(?:[.,]\d+)? ?(?:Stk|m)$")


def zuordnungen(zeilen: list[list[str]]) -> dict[str, dict[str, str]]:
    """Paare aus Tabellenzeilen: SPS-Belegung (Adresse -> Gerät/Klemme/Funktion) und Stückliste (Gerät -> Artikel)."""
    sps: dict[str, str] = {}
    artikel: dict[str, set[str]] = {}
    for z in zeilen:
        adressen = [c for c in z if RE_ADRESSE_ZELLE.match(c)]
        if len(adressen) == 1 and not any(c == "Reserve" for c in z):
            rest = [c for c in z if c not in adressen and not RE_VERWEIS.match(c) and not re.fullmatch(r"[DA][IO]\d+", c)]
            sps["%" + re.sub(r"^%([IQ])[XBWD]?", r"\1", adressen[0])] = " | ".join(rest)
        menge = next((i for i, c in enumerate(z) if RE_MENGE.match(c)), None)
        if menge is not None and menge >= 3 and len(z) > menge + 2:
            anl, ort, bmk = z[menge - 3], z[menge - 2], z[menge - 1]
            if anl.startswith("=") and bmk.startswith("-"):
                artikel.setdefault(f"{anl}{ort if ort.startswith('+') else ''}{bmk}", set()).add(z[menge + 2])
    return {"SPS-Belegung": sps, "Artikel je Gerät": {k: ", ".join(sorted(v)) for k, v in artikel.items()}}


def _seiten(pdf: Path) -> tuple[list[str], list[list[str]]]:
    """-> (Text je Seite, Tabellenzeilen aller Seiten)."""
    try:
        r = PdfReader(str(pdf))
    except Exception as e:                      # pypdf meldet beschädigte Dateien mit verschiedenen Fehlern
        raise RegelFehler(f"{pdf.name}: PDF nicht lesbar ({type(e).__name__}) – neu exportieren") from None
    seiten = [(s.extract_text() or "") for s in r.pages]
    if not "".join(seiten).strip():
        raise RegelFehler(f"{pdf.name}: kein Text im PDF (eingescannt?) – Referenzplan als Vektor-PDF exportieren")
    return seiten, [z for s in r.pages for z in _zeilen(s)]


def merkmale(text: str) -> dict[str, set[str]]:
    """Merkmale je Bereich (eine Seite oder ganzer Text). Kennzeichen mit Anlagenvorsatz wie gedruckt; Kennzeichen
    ohne Vorsatz bekommen die Anlage der Seite (häufigstes „=…“ auf der Seite, z. B. aus dem Schriftfeld)."""
    aus: dict[str, set[str]] = {b: set() for b in MUSTER}
    for bereich in ("BMK", "Klemme"):
        aus[bereich] = {f"={a}{k}" for a, k in MUSTER[bereich].findall(text)}
    aus["SPS-Adresse"] = {f"%{a}{n}" for a, n in MUSTER["SPS-Adresse"].findall(text)}
    anlagen = ANLAGE_SEITE.findall(text)
    if anlagen:
        anlage = max(set(anlagen), key=anlagen.count)
        for bereich, muster in OHNE_ANLAGE.items():
            aus[bereich] |= {f"={anlage}{k if k.startswith('-') else '-' + k}" for k in muster.findall(text)}
    return aus


def _alle(seiten: list[str]) -> dict[str, set[str]]:
    gesamt: dict[str, set[str]] = {b: set() for b in MUSTER}
    for s in seiten:
        for b, w in merkmale(s).items():
            gesamt[b] |= w
    return gesamt


def vergleiche(referenz: Path, m: Planmodell, stil: dict | None = None) -> dict[str, Any]:
    """-> {"abweichungen": [...], "kennzahlen": {Bereich: (gemeinsam, nur_ref, nur_nachbau, quote)}}."""
    from .hausstil import erzeuge_hausstil_pdf
    ref_seiten, ref_zeilen = _seiten(referenz)
    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / "nachbau.pdf"
        erzeuge_hausstil_pdf(m, str(pdf), stil)
        nach_seiten, nach_zeilen = _seiten(pdf)
    ref, nach = _alle(ref_seiten), _alle(nach_seiten)
    abw: list[dict[str, str]] = []
    kennzahlen: dict[str, tuple[int, int, int, float | None]] = {}
    for bereich in MUSTER:
        nur_ref, nur_nach, gemeinsam = ref[bereich] - nach[bereich], nach[bereich] - ref[bereich], ref[bereich] & nach[bereich]
        abw += [{"bereich": bereich, "merkmal": x, "abweichung": "nur im Referenzplan"} for x in sorted(nur_ref)]
        abw += [{"bereich": bereich, "merkmal": x, "abweichung": "nur im Nachbau"} for x in sorted(nur_nach)]
        alle = len(gemeinsam) + len(nur_ref) + len(nur_nach)
        # im Referenzplan nichts erkannt -> nicht auswertbar (Muster passen nicht), nie „100 %“
        kennzahlen[bereich] = (len(gemeinsam), len(nur_ref), len(nur_nach),
                               round(len(gemeinsam) / alle, 3) if ref[bereich] else None)
    # Zuordnungen (Paare) aus Tabellenzeilen: Belegung je Adresse, Artikel je Gerät
    z_ref, z_nach = zuordnungen(ref_zeilen), zuordnungen(nach_zeilen)
    for bereich in ("SPS-Belegung", "Artikel je Gerät"):
        r_, n_ = z_ref[bereich], z_nach[bereich]
        gleich = [k for k in r_ if k in n_ and r_[k] == n_[k]]
        anders = sorted(k for k in r_ if k in n_ and r_[k] != n_[k])
        abw += [{"bereich": bereich, "merkmal": k, "abweichung": f"Referenz: {r_[k]}  ≠  Nachbau: {n_[k]}"} for k in anders]
        abw += [{"bereich": bereich, "merkmal": k, "abweichung": f"nur im Referenzplan: {r_[k]}"} for k in sorted(set(r_) - set(n_))]
        abw += [{"bereich": bereich, "merkmal": k, "abweichung": f"nur im Nachbau: {n_[k]}"} for k in sorted(set(n_) - set(r_))]
        alle = len(set(r_) | set(n_))
        kennzahlen[bereich] = (len(gleich), len(anders) + len(set(r_) - set(n_)), len(set(n_) - set(r_)),
                               round(len(gleich) / alle, 3) if r_ else None)
    return {"referenz": referenz.name, "abweichungen": abw, "kennzahlen": kennzahlen}


def freier_name(pfad: Path) -> Path:
    """Vorhandene (evtl. schon bewertete) Liste nie überschreiben: _2, _3 … anhängen."""
    if not pfad.exists():
        return pfad
    i = 2
    while pfad.with_name(f"{pfad.stem}_{i}{pfad.suffix}").exists():
        i += 1
    return pfad.with_name(f"{pfad.stem}_{i}{pfad.suffix}")


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
    wz.append(["Bereich", "gemeinsam", "nur Referenz", "nur Nachbau", "Übereinstimmung der Kennzeichen"])
    for bereich, (g, r, n, q) in ergebnis["kennzahlen"].items():
        wz.append([bereich, g, r, n, q if q is not None else "nicht auswertbar – im Referenzplan nichts erkannt"])
        wz.cell(wz.max_row, 5).number_format = "0.0%"
    wz.append([])
    wz.append(["Bewertung", "Anzahl"])
    letzte = max(2, len(ergebnis["abweichungen"]) + 1)
    for b in BEWERTUNGEN:                          # zählt die Bewertungen der Elektrofachkraft mit (Excel-Formel)
        wz.append([b, f'=COUNTIF(Abweichungen!E2:E{letzte},"{b}")'])
    wz.append([])
    for feld in ("Abnahmeurteil (gleichwertig ja/nein)", "Elektrofachkraft (Name)", "Datum",
                 "Programmstand / Gerätestamm", "Stunden Nachbau + Nacharbeit", "Stunden Original (geschätzt)"):
        wz.append([feld, ""])
    wz.append([])
    wz.append([f"Referenz: {ergebnis['referenz']}. Die Übereinstimmung vergleicht nur Kennzeichen, Klemmen, Adressen und "
               f"Artikel als Listen – kein Abnahmeurteil (Verschaltung, Absicherung, Zuordnung Adresse↔Gerät nicht "
               f"verglichen, A54). Artikel nur Richtung Nachbau → Referenz."])
    for c in wz[1]:
        c.font, c.fill = Font(bold=True), PatternFill("solid", fgColor="DDDDDD")
    wz.column_dimensions["A"].width = 16
    wb.save(pfad)
