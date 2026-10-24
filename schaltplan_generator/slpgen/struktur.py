"""Strukturauslese aus Vektor-PDFs (aus E-CAD exportiert) – Lernen ohne E-CAD-Zugriff.

Je Seite wird über die Zeichnungsnummer im Schriftfeld die Anlage (=Funktion) und die
Dokumentart (&EFS, &KPL …) bestimmt. Je Anlage werden Merkmale gesammelt:
Betriebsmittelkennzeichen, SPS-Adressen, Aderkennzeichnungen (Farbe + Querschnitt),
Leitungstypen. Anlagen mit sehr ähnlichem, normalisiertem Inhalt werden zu
Typical-Kandidaten gruppiert (z. B. zehnmal derselbe Zähleranschluss).

Alle Muster sind Parameter, damit das Hausschema nicht im Code steht.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path

from pypdf import PdfReader

MUSTER = {
    # Projekt-Anlage-Nr-Dokumentart-Revision, z. B. "P0001-WZ01-0-EFS-00"
    "zeichnungsnummer": r"(?P<projekt>[A-Z0-9_]+)-(?P<anlage>[A-Za-z0-9.]+)-(?P<nr>\d)-(?P<art>[A-Z]*)-(?P<rev>\d{2})",
    "bmk": r"(?<![\w/.-])-(\d{0,3}[A-Z]{1,4}\d{0,4})\b",
    # Siemens-Mnemonik deutsch (E/A/EW/AW) und IEC (%I/%Q/%IW/%QW)
    "sps_adresse": r"\b(?:[EA]\d{1,4}\.[0-7]|[EA]W\d{1,5})\b|%(?:[IQ]\d{1,4}\.[0-7]|[IQ]W\d{1,5})",
    "ader": r"\b(GNYE|BK|BN|BU|GY|OG|RD|WH|YE|GN|VT|PK|DBU/WH|DBU|LBU)\s*\n?\s*(0,75|0,5|1,5|2,5|(?:4|6|10|16)(?=\s*mm))",
    "leitungstyp": r"\b(LIYCY|LiYCY|NYY-J|NYM-J|ÖLFLEX[^\n]{0,20}|J-Y\(ST\)Y|JE-Y\(ST\)Y|Cat ?\d|Patchkabel)",
}
SEITENARTEN_PLAN = {"EFS"}          # Dokumentarten mit Stromlaufplan-Inhalt


def _normalisiert(text: str, anlage: str) -> set[str]:
    """Token-Menge ohne Anlagennamen und Ziffern -> vergleichbar zwischen Anlagen."""
    t = text.replace(anlage, "§")
    t = re.sub(r"\d+", "#", t)
    return {w for w in re.split(r"[\s|/,;:()]+", t) if len(w) > 1}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / max(1, len(a | b))


def lese_struktur(pdf: Path, muster: dict | None = None, schwelle: float = 0.75) -> dict:
    mu = {k: re.compile(v) for k, v in {**MUSTER, **(muster or {})}.items()}
    r = PdfReader(str(pdf))
    seiten_je_art: Counter = Counter()
    anlagen: dict[str, dict] = defaultdict(lambda: {"seiten": [], "text": ""})
    ohne_nr = []
    for i, s in enumerate(r.pages, 1):
        text = s.extract_text() or ""
        m = mu["zeichnungsnummer"].search(text)
        if not m:
            ohne_nr.append(i)
            continue
        art = m.group("art") or "-"
        seiten_je_art[art] += 1
        if art in SEITENARTEN_PLAN:
            a = anlagen[m.group("anlage")]
            a["seiten"].append(i)
            a["text"] += "\n" + text

    ergebnis_anlagen = {}
    for name, a in anlagen.items():
        t = a["text"]
        sps = mu["sps_adresse"].findall(t)
        ergebnis_anlagen[name] = {
            "seiten": a["seiten"],
            "bmk": sorted(set(mu["bmk"].findall(t))),
            "sps_adressen": sorted(set(sps)),
            "adern": dict(Counter(f"{f} {q}" for f, q in mu["ader"].findall(t))),
            "leitungstypen": sorted(set(mu["leitungstyp"].findall(t))),
        }
        # ohne Betriebsmittel und SPS-Adressen: nur Schriftfeld -> leere/Reserve-Anlage
        ergebnis_anlagen[name]["leer"] = not (ergebnis_anlagen[name]["bmk"] or sps)

    # Typical-Kandidaten: einfache Gruppierung über Jaccard-Ähnlichkeit (single linkage)
    namen = [n for n in anlagen if not ergebnis_anlagen[n]["leer"]]
    tok = {n: _normalisiert(anlagen[n]["text"], n) for n in namen}
    gruppe = {n: n for n in namen}

    def wurzel(n):
        while gruppe[n] != n:
            n = gruppe[n]
        return n

    for i, a in enumerate(namen):
        for b in namen[i + 1:]:
            if jaccard(tok[a], tok[b]) >= schwelle:
                gruppe[wurzel(b)] = wurzel(a)
    aehnlichste = sorted(((round(jaccard(tok[a], tok[b]), 2), a, b) for i, a in enumerate(namen)
                          for b in namen[i + 1:]), reverse=True)[:15]
    typicals: dict[str, list[str]] = defaultdict(list)
    for n in namen:
        typicals[wurzel(n)].append(n)

    adern = Counter()
    for e in ergebnis_anlagen.values():
        adern.update(e["adern"])
    return {
        "datei": pdf.name,
        "seiten": len(r.pages),
        "seiten_je_dokumentart": dict(seiten_je_art),
        "seiten_ohne_zeichnungsnummer": ohne_nr,
        "anlagen": ergebnis_anlagen,
        "typical_kandidaten": [sorted(v) for v in typicals.values() if len(v) > 1],
        "aehnlichste_paare": aehnlichste,
        "leere_anlagen": sorted(n for n, e in ergebnis_anlagen.items() if e["leer"]),
        "aderkennzeichnung_gesamt": dict(adern.most_common()),
    }
