"""KI-Auftrag (Stufe A ohne lokale KI): Anleitung + Schema + Artikel-/Bausteinliste + Lastenheft in einen Text.

Der Text wird in eine beliebige KI (Chat) eingefügt; deren Antwort (YAML) prüft `projektmodell.bereit_machen`.
"""
from __future__ import annotations

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
    for name in ("projekt", "einspeisung", "feldgeraete", "motoren"):
        _, liste, felder, text, _ = ABSCHNITTE[name]
        felder = [f for f in felder if not (name == "einspeisung" and f.name != "netz")]
        z.append(f"{name}{' (Liste)' if liste else ''} – {text}:")
        z += [f"  {f.name}{' (Pflicht)' if f.pflicht else ''}: {f.text}" for f in felder]
    return "\n".join(z)


def _lese_lastenheft(pfad: Path) -> str:
    if pfad.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        text = "\n".join((s.extract_text() or "") for s in PdfReader(str(pfad)).pages)
        if len(text.strip()) < 50:
            raise RegelFehler(f"{pfad.name}: kein lesbarer Text (eingescannt?) – Lastenheft als Text/Word speichern")
        return text
    if pfad.suffix.lower() == ".docx":
        import zipfile
        with zipfile.ZipFile(pfad) as z:
            xml = z.read("word/document.xml").decode("utf-8")
        return re.sub(r"<[^>]+>", "", xml.replace("</w:p>", "\n"))
    return pfad.read_text(encoding="utf-8")


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
