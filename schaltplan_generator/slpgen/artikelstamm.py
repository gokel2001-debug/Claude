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


def _blaetter(pfad: Path) -> list[list[list[str]]]:
    """Alle Tabellenblätter (Excel) bzw. die Zeilen der CSV-Datei mit passendem Trennzeichen."""
    endung = pfad.suffix.lower()
    if endung in (".xlsx", ".xlsm"):
        try:
            wb = load_workbook(pfad, read_only=True, data_only=True)
        except Exception:
            raise RegelFehler(f"{pfad.name} ist keine lesbare Excel-Datei (.xlsx)") from None
        try:
            return [[["" if v is None else str(v).strip() for v in z] for z in ws.iter_rows(values_only=True)]
                    for ws in wb.worksheets]
        finally:
            wb.close()                                   # Datei unter Windows nicht gesperrt lassen
    if endung in (".csv", ".txt"):
        roh = pfad.read_bytes()
        if roh.startswith((b"\xff\xfe", b"\xfe\xff")):
            text = roh.decode("utf-16")                  # EPLAN „Unicode-Text“
        else:
            try:
                text = roh.decode("utf-8-sig")
            except UnicodeDecodeError:
                text = roh.decode("cp1252", errors="replace")
        # Trennzeichen: jenes, mit dem eine Kopfzeile erkannt wird (Dezimalkommas im Inhalt zählen nicht)
        return [[[f.strip() for f in z] for z in csv.reader(text.splitlines(), delimiter=t)] for t in (";", "\t", ",")]
    raise RegelFehler(f"{pfad.name}: Format {pfad.suffix} nicht unterstützt – als .xlsx oder .csv exportieren")


def _norm(kopf: str) -> str:
    return re.sub(r"[^a-z0-9äöü]", "", kopf.lower())


KOEPFE_NORM = {feld: {_norm(n) for n in namen} | ({"artnr", "artikelnr", "bestellnr", "matnr", "materialnummer"}
                                                  if feld == "artikelnummer" else set())
               for feld, namen in KOEPFE.items()}


def lese_export(pfad: str | Path) -> list[dict[str, str]]:
    """Export einlesen; Kopfzeile wird je Blatt in den ersten 10 Zeilen gesucht. -> Liste {artikelnummer, hersteller,
    bezeichnung}."""
    pfad = Path(pfad)
    erste = ""
    for zeilen in _blaetter(pfad):
        kopfzeile, spalten = -1, {}
        for i, kopf in enumerate(zeilen[:10]):
            klein = [_norm(k) for k in kopf]
            spalten = {feld: next((n for n, k in enumerate(klein) if k in namen), None) for feld, namen in KOEPFE_NORM.items()}
            if spalten["artikelnummer"] is not None and spalten["bezeichnung"] is not None:
                kopfzeile = i
                break
        if kopfzeile < 0:
            erste = erste or " | ".join(next((z for z in zeilen if any(z)), []))[:80]
            continue
        artikel, gesehen = [], set()
        for z in zeilen[kopfzeile + 1:]:
            def wert(feld: str, z: list[str] = z, sp: dict = spalten) -> str:
                n = sp[feld]
                return z[n] if n is not None and n < len(z) else ""
            nr = wert("artikelnummer")
            if not nr or nr in gesehen:
                continue
            gesehen.add(nr)
            artikel.append({"artikelnummer": nr, "hersteller": wert("hersteller"), "bezeichnung": wert("bezeichnung")})
        if artikel:
            return artikel
    raise RegelFehler(f"{pfad.name}: keine Spalten „Artikelnummer“ und „Bezeichnung“ gefunden (erste Zeile: „{erste}“) – "
                      f"Kopfzeile prüfen (erkannt werden z. B. Artikelnummer, Art.-Nr., Bestellnummer / Bezeichnung, "
                      f"Beschreibung)")


RE_KENNWERT = re.compile(r"(\d+(?:[.,]\d+)?)\s*(v|a|w|mm²|mm2|ma|kw|ka)\b")


def kennwerte(text: str) -> dict[str, set[float]]:
    """Zahlen mit Einheit je Einheit, z. B. {"v": {24.0}, "a": {5.0}}."""
    k: dict[str, set[float]] = {}
    for z, e in RE_KENNWERT.findall(text.lower()):
        k.setdefault(e.replace("mm2", "mm²"), set()).add(float(z.replace(",", ".")))
    return k


def kennwert_abweichung(a: str, b: str) -> list[str]:
    """Einheiten, die in beiden Texten vorkommen, aber mit verschiedenen Werten (z. B. 5 A gegen 2,5 A)."""
    ka, kb = kennwerte(a), kennwerte(b)
    return [e for e in ka.keys() & kb.keys() if not ka[e] & kb[e]]


def _merkmale(text: str) -> set[str]:
    """Vergleichsmerkmale: Wörter und Zahlen mit Einheit („24 V“, „5 A“, „16“) – Groß/klein egal."""
    t = text.lower().replace(",", ".")
    zahlen = {f"{z}{e}" for z, e in re.findall(r"(\d+(?:\.\d+)?)\s*(v|a|w|mm²|mm2|ma|kw)?\b", t)}
    worte = set(re.findall(r"[a-zäöüß]{4,}", t))
    return zahlen | worte


class Vorschlaege:
    """Vorschläge für viele Programm-Artikel: Merkmale der Hausartikel einmal berechnen, über Index vorfiltern."""

    def __init__(self, haus: list[dict[str, str]]):
        self.haus = haus
        self.merk = [_merkmale(h["bezeichnung"]) for h in haus]
        self.index: dict[str, list[int]] = {}
        for i, m in enumerate(self.merk):
            for x in m:
                self.index.setdefault(x, []).append(i)

    def fuer(self, programm: dict[str, Any]) -> dict[str, str] | None:
        text = programm.get("bezeichnung", "")
        m = _merkmale(text)
        treffer: dict[int, int] = {}
        for x in m:
            for i in self.index.get(x, []):
                treffer[i] = treffer.get(i, 0) + 1
        kandidaten = sorted(treffer, key=lambda i: -treffer[i])[:50]
        best, wert = None, 0.0
        for i in kandidaten:
            h = self.haus[i]
            if kennwert_abweichung(text, h["bezeichnung"]):      # andere Bemessungswerte -> nie vorschlagen
                continue
            gemeinsam = len(m & self.merk[i]) / max(1, len(m | self.merk[i]))
            aehnlich = difflib.SequenceMatcher(None, text.lower(), h["bezeichnung"].lower()).ratio()
            punkte = 0.7 * gemeinsam + 0.3 * aehnlich
            if punkte > wert:
                best, wert = h, punkte
        return best if wert >= 0.35 else None                    # ANNAHME A47: Schwelle für einen Vorschlag


def vorschlag(programm: dict[str, Any], haus: list[dict[str, str]]) -> dict[str, str] | None:
    return Vorschlaege(haus).fuer(programm)


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
    vs = Vorschlaege(haus)
    for key, a in sorted(stamm.get("artikel", {}).items()):
        v = vs.fuer(a)
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
    ersetzt, hinweise = [], []
    for key, nr in zuordnung.items():
        if key in m.artikel and nr in haus:
            h = haus[nr]
            abw = kennwert_abweichung(m.artikel[key].get("bezeichnung", ""), h.get("bezeichnung", ""))
            if abw:
                hinweise.append(f"Eigener Artikelstamm: {key} → {nr} – Kennwerte weichen ab ({', '.join(sorted(abw))}); "
                                f"die Auslegung rechnet mit {key} – Zuordnung prüfen")
            m.artikel[key].update({"artikelnummer": nr, "hersteller": h.get("hersteller", ""),
                                   "bezeichnung": h.get("bezeichnung") or m.artikel[key]["bezeichnung"]})
            ersetzt.append(key)
    kopf = [f"Eigener Artikelstamm: {len(ersetzt)} Artikel zugeordnet ({', '.join(sorted(ersetzt))})"] if ersetzt else []
    return kopf + hinweise
