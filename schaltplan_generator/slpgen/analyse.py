"""Bestandsanalyse (Lernbasis) und Datenblatt-Auswertung.

Stufe 1 (hier umgesetzt, ohne KI): deterministische Auswertung der Text-Ebene
vorhandener Stromlaufplan-PDFs – Datum, Blattformat, erzeugende Software,
verwendete Kennbuchstaben (BMK) – und deren Entwicklung über die Jahre.
Funktioniert nur bei Vektor-PDFs (z. B. aus EPLAN exportiert); gescannte
Pläne brauchen vorher OCR bzw. ein Vision-Modell.

Stufe 2 (optional): Datenblatt-Extraktion über ein lokales LLM (Ollama), das
einen Vorschlag für einen Gerätestamm-Eintrag liefert. Der Vorschlag ist
immer vom Menschen zu prüfen.
"""
from __future__ import annotations

import json
import re
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

from pypdf import PdfReader

RE_DATUM = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.((?:19|20)\d{2})\b|\b((?:19|20)\d{2})-(\d{2})-(\d{2})\b")
# BMK-Produktaspekt: "-K12", "-2F3" usw.; Präfix '-' vor Kennbuchstaben (IEC 81346)
RE_BMK = re.compile(r"(?<![\w/.-])-(\d{0,3})([A-Z]{1,3})(\d{1,4})\b")
RE_ANLAGE = re.compile(r"(?<![\w])=[A-Z0-9]{1,8}")
RE_ORT = re.compile(r"(?<![\w])\+[A-Z0-9]{1,8}")

FORMATE = {"A4": (210, 297), "A3": (297, 420), "A2": (420, 594)}


def blattformat(breite_pt: float, hoehe_pt: float) -> str:
    a, b = sorted((breite_pt * 0.3528, hoehe_pt * 0.3528))
    for name, (x, y) in FORMATE.items():
        if abs(a - x) < 5 and abs(b - y) < 5:
            return name
    return f"{a:.0f}x{b:.0f}mm"


def analysiere_pdf(pfad: Path) -> dict:
    r = PdfReader(str(pfad))
    text = "\n".join((s.extract_text() or "") for s in r.pages)
    jahre = Counter()
    for mt in RE_DATUM.finditer(text):
        jahr = mt.group(3) or mt.group(4)
        jahre[int(jahr)] += 1
    kenn = Counter(mt.group(2) for mt in RE_BMK.finditer(text))
    meta = r.metadata or {}
    box = r.pages[0].mediabox if r.pages else None
    return {
        "datei": pfad.name,
        "seiten": len(r.pages),
        "format": blattformat(float(box.width), float(box.height)) if box else "?",
        "erzeuger": str(meta.get("/Creator", "") or meta.get("/Producer", "")),
        # Plan-Jahr: das häufigste Jahr im Text (Schriftfeld wiederholt sich je Seite) [Annahme]
        "jahr": jahre.most_common(1)[0][0] if jahre else None,
        "textanteil": len(text.strip()) > 50 * max(1, len(r.pages)),
        "kennbuchstaben": dict(kenn),
        "anlage_kennz": len(RE_ANLAGE.findall(text)),
        "ort_kennz": len(RE_ORT.findall(text)),
    }


def analysiere_bestand(ordner: Path, ziel: Path) -> dict:
    ziel.mkdir(parents=True, exist_ok=True)
    ergebnisse = []
    for p in sorted(ordner.rglob("*.pdf")):
        try:
            ergebnisse.append(analysiere_pdf(p))
        except Exception as e:  # defekte/verschlüsselte PDFs nicht abbrechen lassen
            ergebnisse.append({"datei": p.name, "fehler": str(e)})
    (ziel / "plaene.json").write_text(json.dumps(ergebnisse, indent=2, ensure_ascii=False), encoding="utf-8")

    # Entwicklung der Kennbuchstaben je Jahr (Anteil an allen BMK des Jahres)
    je_jahr: dict[int, Counter] = defaultdict(Counter)
    for e in ergebnisse:
        if e.get("jahr"):
            je_jahr[e["jahr"]].update(e["kennbuchstaben"])
    codes = sorted({c for z in je_jahr.values() for c in z})
    zeilen = ["jahr;" + ";".join(codes)]
    for jahr in sorted(je_jahr):
        summe = sum(je_jahr[jahr].values()) or 1
        zeilen.append(f"{jahr};" + ";".join(f"{je_jahr[jahr][c] / summe:.3f}" for c in codes))
    (ziel / "kennbuchstaben_je_jahr.csv").write_text("\n".join(zeilen) + "\n", encoding="utf-8")

    ohne_text = [e["datei"] for e in ergebnisse if e.get("textanteil") is False]
    zus = {
        "anzahl": len(ergebnisse),
        "fehler": sum(1 for e in ergebnisse if "fehler" in e),
        "ohne_textebene_ocr_noetig": ohne_text,
        "formate": Counter(e.get("format") for e in ergebnisse if "format" in e),
        "erzeuger": Counter(e.get("erzeuger") for e in ergebnisse if "erzeuger" in e),
        "jahre": dict(sorted(Counter(e.get("jahr") for e in ergebnisse if e.get("jahr")).items())),
    }
    (ziel / "zusammenfassung.json").write_text(json.dumps(zus, indent=2, ensure_ascii=False), encoding="utf-8")
    return zus


# --------------------------------------------------------------------------- #
# Datenblatt -> Vorschlag Gerätestamm
# --------------------------------------------------------------------------- #
RE_SPANNUNG = re.compile(r"(\d{1,3}(?:[.,]\d+)?)\s*V\s*(DC|AC|=|~)", re.I)
RE_STROM = re.compile(r"(\d{1,4}(?:[.,]\d+)?)\s*(mA|A)\b")
RE_LEISTUNG = re.compile(r"(\d{1,4}(?:[.,]\d+)?)\s*W\b")

PROMPT = """Extrahiere aus dem folgenden Datenblatt-Text die Werte für einen Gerätestamm-Eintrag.
Antworte NUR mit JSON mit den Schlüsseln: hersteller, bezeichnung, artikelnummer, kategorie
(netzteil|sensor|aktor|schutz|sonstiges), u_V, i_mA, p_W, signal (DI|DO|AI|AO|null),
anschluss (Liste der Pin-Bezeichnungen). Unbekannte Werte = null. Erfinde nichts.

TEXT:
{text}"""


def datenblatt_vorschlag(pdf: Path, ollama_url: str | None = None, modell: str = "qwen2.5:7b") -> dict:
    text = "\n".join((s.extract_text() or "") for s in PdfReader(str(pdf)).pages)
    roh = {
        "spannungen": sorted({f"{a} V {b.upper()}" for a, b in RE_SPANNUNG.findall(text)})[:10],
        "stroeme": sorted({f"{a} {b}" for a, b in RE_STROM.findall(text)})[:10],
        "leistungen": sorted({f"{a} W" for a in RE_LEISTUNG.findall(text)})[:10],
    }
    erg = {"quelle": pdf.name, "regex_kandidaten": roh, "llm": None, "status": "PRUEFEN"}
    if ollama_url:
        body = json.dumps({"model": modell, "prompt": PROMPT.format(text=text[:12000]),
                           "format": "json", "stream": False}).encode()
        req = urllib.request.Request(ollama_url.rstrip("/") + "/api/generate", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as resp:
            erg["llm"] = json.loads(json.loads(resp.read())["response"])
    return erg


# --------------------------------------------------------------------------- #
# Vergleich Original-PDF <-> Planmodell (Erprobung Variante B)
# --------------------------------------------------------------------------- #
def vergleiche(pdf: Path, modell: dict) -> dict:
    """Welche BMK und Artikel des Planmodells finden sich im PDF wieder – und umgekehrt?"""
    text = "\n".join((s.extract_text() or "") for s in PdfReader(str(pdf)).pages)
    im_pdf = {f"-{mt.group(1)}{mt.group(2)}{mt.group(3)}" for mt in RE_BMK.finditer(text)}
    im_modell = {b["bmk"] for b in modell["betriebsmittel"]}
    artikel = sorted({b["artikel"] for b in modell["betriebsmittel"]})
    return {
        "pdf": pdf.name,
        "bmk_gemeinsam": len(im_modell & im_pdf),
        "bmk_nur_modell": sorted(im_modell - im_pdf),
        "bmk_nur_pdf": sorted(im_pdf - im_modell),
        "bmk_abdeckung": round(len(im_modell & im_pdf) / max(1, len(im_modell)), 3),
        "artikel_fehlen_im_pdf": [a for a in artikel if a not in text],
    }
