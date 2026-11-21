"""KI-Auftrag (Stufe A ohne lokale KI): Anleitung + Schema + Artikel-/Bausteinliste + Lastenheft in einen Text.

Der Text wird in eine beliebige KI (Chat) eingefügt; deren Antwort (YAML) prüft `projektmodell.bereit_machen`.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

from .modell import RegelFehler
from .projektmodell import ABSCHNITTE, SCHEMA

FELD_KATEGORIEN = ("sensor", "aktor")


def _anleitung(pfad: Path) -> str:
    text = pfad.read_text(encoding="utf-8")
    teil = text.split("## AUFTRAG AN DIE KI", 1)
    if len(teil) != 2:
        raise RegelFehler(f"{pfad.name}: Abschnitt „AUFTRAG AN DIE KI“ fehlt")
    return re.sub(r"<!--.*?-->", "", "## AUFTRAG AN DIE KI" + teil[1]).strip()


def _schema_kurz() -> str:
    z = []
    for name in ("projekt", "einspeisung", "feldgeraete", "motoren", "sicherheit"):
        _, liste, felder, text, _ = ABSCHNITTE[name]
        felder = [f for f in felder if not (name == "einspeisung" and f.name != "netz")
                  and not (name == "sicherheit" and f.name in ("freigabe", "ausgenommen"))]   # nur Elektrofachkraft
        z.append(f"{name}{' (Liste)' if liste else ''} – {text}:")
        z += [f"  {f.name}{' (Pflicht)' if f.pflicht else ''}: {f.text}" for f in felder]
    return "\n".join(z)


MAX_ZEICHEN = 60_000      # ANNAHME A23: übliche Chat-Eingaben fassen deutlich weniger als ein dickes Lastenheft-PDF


def _lese_roh(pfad: Path) -> str:
    endung = pfad.suffix.lower()
    if endung == ".pdf":
        import logging

        from pypdf import PdfReader
        from pypdf.errors import PdfReadError
        logging.getLogger("pypdf").setLevel(logging.ERROR)
        try:
            r = PdfReader(str(pfad))
            if r.is_encrypted:
                raise RegelFehler(f"{pfad.name}: PDF ist kennwortgeschützt – ohne Schutz speichern oder als Word-Datei")
            return "\n".join((s.extract_text() or "") for s in r.pages)
        except PdfReadError:
            raise RegelFehler(f"{pfad.name}: PDF ist beschädigt – neu speichern oder als Word-Datei verwenden") from None
    if endung == ".docx":
        import zipfile
        try:
            with zipfile.ZipFile(pfad) as z:
                xml = z.read("word/document.xml").decode("utf-8")
        except (zipfile.BadZipFile, KeyError):
            raise RegelFehler(f"{pfad.name}: keine gültige Word-Datei (.docx) – in Word als .docx speichern") from None
        xml = (xml.replace("</w:p>", "\n").replace("</w:tc>", " | ").replace("<w:tab/>", "\t")
               .replace("<w:br/>", "\n"))
        return html.unescape(re.sub(r"<[^>]+>", "", xml))
    if endung not in (".txt", ".md"):
        raise RegelFehler(f"{pfad.name}: Format „{pfad.suffix or 'ohne Endung'}“ wird nicht unterstützt – "
                          f"Lastenheft als .docx, .pdf oder .txt speichern")
    roh = pfad.read_bytes()
    for kodierung in ("utf-8-sig", "cp1252"):
        try:
            text = roh.decode(kodierung)
        except UnicodeDecodeError:
            continue
        if "\x00" not in text:
            return text
    raise RegelFehler(f"{pfad.name}: Text nicht lesbar – als .docx oder .txt (UTF-8) speichern")


def _lese_lastenheft(pfad: Path) -> str:
    if pfad.is_dir():
        raise RegelFehler(f"{pfad}: das ist ein Ordner – bitte die Lastenheft-Datei angeben")
    text = _lese_roh(pfad).strip()
    if len(text) < 50:
        raise RegelFehler(f"{pfad.name}: kein oder kaum lesbarer Text (leer oder eingescannt?) – "
                          f"Lastenheft als Word- oder Textdatei speichern")
    return text


def erzeuge_auftrag(lastenheft: str | Path, stamm: dict, anleitung: str | Path) -> str:
    art = stamm.get("artikel", {})
    zeilen = [f"| {k} | {d.get('bezeichnung', '')} | {d.get('signal') or '–'} |"
              for k, d in sorted(art.items()) if d.get("kategorie") in FELD_KATEGORIEN]
    bausteine = [f"| {k} | {t.get('beschreibung', '')} |" for k, t in sorted(stamm.get("typicals", {}).items())]
    teile = [
        _anleitung(Path(anleitung)),
        f"### Schema {SCHEMA} (Felder)\n{_schema_kurz()}",
        "### Artikelliste (nur diese verwenden)\n| Artikel | Bezeichnung | Signal |\n|---|---|---|\n" + "\n".join(zeilen),
        "### Bausteinliste (Feld `typical`)\n| Baustein | Beschreibung |\n|---|---|\n" + "\n".join(bausteine),
        "### LASTENHEFT\n" + _lese_lastenheft(Path(lastenheft)).strip(),
    ]
    return "\n\n".join(teile) + "\n"
