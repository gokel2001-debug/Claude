"""Eigener Artikelstamm (M7a): Export (Excel/CSV, z. B. aus EPLAN) einlesen, Programm-Artikel zuordnen,
in Stückliste/EPLAN-Daten die eigenen Hersteller und Artikelnummern verwenden.

Ablauf:
  1. `artikelstamm <datei>`  -> hausprofil/artikelstamm.yaml (Hausartikel) + hausprofil/artikelzuordnung.xlsx
     (je Programm-Artikel ein Vorschlag aus dem Hausstamm, Spalte „Hausartikel (JA = Vorschlag)“)
  2. Liste ausfüllen, `artikelzuordnung` -> Zuordnung in artikelstamm.yaml
  3. Beim Erzeugen ersetzt `wende_zuordnung_an` im Planmodell Hersteller/Artikelnummer/Bezeichnung (Stückliste, EPLAN).
Technische Werte (Strom, Kanäle …) bleiben aus dem Gerätestamm – der Export liefert sie nicht.
Alles bleibt lokal in `hausprofil/` (vertraulich).
"""
from __future__ import annotations

import csv
import difflib
import re
from pathlib import Path
from typing import Any

import yaml
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font

from .modell import Planmodell, RegelFehler

# Spaltenköpfe, die als Artikelnummer/Hersteller/Bezeichnung erkannt werden   # ANNAHME A47: übliche Exportköpfe
KOEPFE = {"artikelnummer": ("artikelnummer", "artikel-nr", "artikelnr", "bestellnummer", "part number", "teilenummer",
                            "artikel"),
          "hersteller": ("hersteller", "manufacturer", "lieferant"),
          "bezeichnung": ("bezeichnung", "benennung", "beschreibung", "description", "bezeichnung 1", "text")}
LISTE = ["Programm-Artikel", "Bezeichnung im Programm", "Vorschlag Hausartikel", "Bezeichnung Hausartikel",
         "Hausartikel (JA = Vorschlag, oder Nummer eintragen)"]


def _zeilen(pfad: Path) -> list[list[str]]:
    endung = pfad.suffix.lower()
    if endung in (".xlsx", ".xlsm"):
        try:
            ws = load_workbook(pfad, read_only=True, data_only=True).worksheets[0]
        except Exception:
            raise RegelFehler(f"{pfad.name} ist keine lesbare Excel-Datei (.xlsx)") from None
        return [["" if v is None else str(v).strip() for v in z] for z in ws.iter_rows(values_only=True)]
    if endung in (".csv", ".txt"):
        roh = pfad.read_bytes()
        for kodierung in ("utf-8-sig", "cp1252"):
            try:
                text = roh.decode(kodierung)
                break
            except UnicodeDecodeError:
                continue
        trenner = ";" if text.count(";") >= text.count(",") else ","
        return [[f.strip() for f in z] for z in csv.reader(text.splitlines(), delimiter=trenner)]
    raise RegelFehler(f"{pfad.name}: Format {pfad.suffix} nicht unterstützt – als .xlsx oder .csv exportieren")


def lese_export(pfad: str | Path) -> list[dict[str, str]]:
    """Export einlesen; Kopfzeile wird in den ersten 10 Zeilen gesucht. -> Liste {artikelnummer, hersteller, bezeichnung}."""
    zeilen = _zeilen(Path(pfad))
    kopfzeile = -1
    for i, kopf in enumerate(zeilen[:10]):
        klein = [k.lower() for k in kopf]
        spalten = {feld: next((n for n, k in enumerate(klein) if k in namen), None) for feld, namen in KOEPFE.items()}
        if spalten["artikelnummer"] is not None and spalten["bezeichnung"] is not None:
            kopfzeile = i
            break
    else:
        raise RegelFehler(f"{Path(pfad).name}: keine Spalten „Artikelnummer“ und „Bezeichnung“ gefunden – Kopfzeile prüfen "
                          f"(erkannt werden z. B. {', '.join(KOEPFE['artikelnummer'][:3])} / "
                          f"{', '.join(KOEPFE['bezeichnung'][:3])})")
    artikel, gesehen = [], set()
    for z in zeilen[kopfzeile + 1:]:
        def wert(feld: str, z: list[str] = z) -> str:
            n = spalten[feld]
            return z[n] if n is not None and n < len(z) else ""
        nr = wert("artikelnummer")
        if not nr or nr in gesehen:
            continue
        gesehen.add(nr)
        artikel.append({"artikelnummer": nr, "hersteller": wert("hersteller"), "bezeichnung": wert("bezeichnung")})
    if not artikel:
        raise RegelFehler(f"{Path(pfad).name}: keine Artikelzeilen gefunden")
    return artikel


def _merkmale(text: str) -> set[str]:
    """Vergleichsmerkmale: Wörter und Zahlen mit Einheit („24 V“, „5 A“, „16“) – Groß/klein egal."""
    t = text.lower().replace(",", ".")
    zahlen = {f"{z}{e}" for z, e in re.findall(r"(\d+(?:\.\d+)?)\s*(v|a|w|mm²|mm2|ma|kw)?\b", t)}
    worte = {w for w in re.findall(r"[a-zäöüß]{4,}", t)}
    return zahlen | worte


def vorschlag(programm: dict[str, Any], haus: list[dict[str, str]]) -> dict[str, str] | None:
    """Ähnlichster Hausartikel zur Bezeichnung des Programm-Artikels (Merkmale + Textähnlichkeit), sonst None."""
    m = _merkmale(programm.get("bezeichnung", ""))
    best, wert = None, 0.0
    for h in haus:
        hm = _merkmale(h["bezeichnung"])
        gemeinsam = len(m & hm) / max(1, len(m | hm))
        aehnlich = difflib.SequenceMatcher(None, programm.get("bezeichnung", "").lower(), h["bezeichnung"].lower()).ratio()
        punkte = 0.7 * gemeinsam + 0.3 * aehnlich
        if punkte > wert:
            best, wert = h, punkte
    return best if wert >= 0.35 else None                       # ANNAHME A47: Schwelle für einen Vorschlag


def importiere(export: str | Path, stamm: dict[str, Any], ordner: str | Path) -> tuple[Path, Path, int]:
    """Export -> artikelstamm.yaml + artikelzuordnung.xlsx im Ordner hausprofil. -> (yaml, xlsx, Anzahl Vorschläge)."""
    haus = lese_export(export)
    ordner = Path(ordner)
    ordner.mkdir(parents=True, exist_ok=True)
    yml = ordner / "artikelstamm.yaml"
    alt = lade(yml)
    yml.write_text("# Eigener Artikelstamm – VERTRAULICH, nur lokal\n" + yaml.safe_dump(
        {"artikel": haus, "zuordnung": alt.get("zuordnung", {})}, allow_unicode=True, sort_keys=False), encoding="utf-8")
    wb = Workbook()
    ws = wb.active
    ws.title = "Zuordnung"
    ws.append(LISTE)
    for c in ws[1]:
        c.font = Font(bold=True)
    n = 0
    for key, a in sorted(stamm.get("artikel", {}).items()):
        v = vorschlag(a, haus)
        n += bool(v)
        bisher = alt.get("zuordnung", {}).get(key, "")
        ws.append([key, a.get("bezeichnung", ""), v["artikelnummer"] if v else "", v["bezeichnung"] if v else "", bisher])
    for spalte, breite in zip("ABCDE", (18, 50, 22, 50, 34), strict=True):
        ws.column_dimensions[spalte].width = breite
    xlsx = ordner / "artikelzuordnung.xlsx"
    wb.save(xlsx)
    return yml, xlsx, n


def lade(pfad: str | Path) -> dict[str, Any]:
    p = Path(pfad)
    if not p.is_file():
        return {}
    try:
        d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        raise RegelFehler(f"{p.name} ist beschädigt – Artikelstamm neu importieren") from None
    return d if isinstance(d, dict) else {}


def uebernehme_zuordnung(ordner: str | Path) -> dict[str, str]:
    """artikelzuordnung.xlsx -> Zuordnung Programm-Artikel -> Hausartikelnummer (JA = Vorschlag)."""
    ordner = Path(ordner)
    yml, xlsx = ordner / "artikelstamm.yaml", ordner / "artikelzuordnung.xlsx"
    daten = lade(yml)
    if not daten.get("artikel"):
        raise RegelFehler("Noch kein Artikelstamm importiert – zuerst Artikelstamm einlesen")
    nummern = {a["artikelnummer"] for a in daten["artikel"]}
    try:
        ws = load_workbook(xlsx).worksheets[0]
    except FileNotFoundError:
        raise RegelFehler(f"{xlsx.name} fehlt – zuerst Artikelstamm einlesen") from None
    zuordnung, fehler = {}, []
    for nr, z in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        key, vorschlag_nr, eintrag = z[0], z[2], str(z[4] or "").strip()
        if not key or not eintrag:
            continue
        ziel = str(vorschlag_nr or "") if eintrag.upper() == "JA" else eintrag
        if ziel not in nummern:
            fehler.append(f"Zeile {nr} ({key}): „{eintrag}“ – Artikelnummer nicht im eigenen Artikelstamm")
            continue
        zuordnung[str(key)] = ziel
    if fehler:
        raise RegelFehler("Es wurde nichts übernommen:\n" + "\n".join(f"  • {f}" for f in fehler))
    daten["zuordnung"] = zuordnung
    yml.write_text("# Eigener Artikelstamm – VERTRAULICH, nur lokal\n" + yaml.safe_dump(daten, allow_unicode=True,
                                                                                       sort_keys=False), encoding="utf-8")
    return zuordnung


def wende_zuordnung_an(m: Planmodell, pfad: str | Path) -> list[str]:
    """Hausartikel (Hersteller, Artikelnummer, Bezeichnung) in den Artikelauszug des Planmodells übernehmen."""
    daten = lade(pfad)
    zuordnung = daten.get("zuordnung") or {}
    haus = {a["artikelnummer"]: a for a in daten.get("artikel") or [] if isinstance(a, dict)}
    ersetzt = []
    for key, nr in zuordnung.items():
        if key in m.artikel and nr in haus:
            h = haus[nr]
            m.artikel[key].update({"artikelnummer": nr, "hersteller": h.get("hersteller") or m.artikel[key].get("hersteller", ""),
                                   "bezeichnung": h.get("bezeichnung") or m.artikel[key]["bezeichnung"]})
            ersetzt.append(key)
    return [f"Eigener Artikelstamm: {len(ersetzt)} Artikel zugeordnet ({', '.join(sorted(ersetzt))})"] if ersetzt else []
