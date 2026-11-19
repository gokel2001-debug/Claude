"""Freigabe des gelernten Hausprofils über eine Excel-Liste (statt Programmdateien zu bearbeiten).

Ablauf: `lernen` schreibt neben profil.yaml die Liste profil_freigabe.xlsx. Der Nutzer trägt je
Merkmal in Spalte „Freigabe“ JA oder NEIN ein, optional einen eigenen Wert, speichert und ruft
`freigabe` auf. Erst freigegebene Werte darf der Generator später verwenden.
"""
from __future__ import annotations

from pathlib import Path

import yaml
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from .modell import RegelFehler

SPALTEN = ["Merkmal", "Beschreibung", "Gelernter Wert", "Belegt in", "Sicherheit", "Änderung über die Jahre",
           "Freigabe (JA/NEIN)", "Eigener Wert (optional)", "Status bisher"]
FREIGABE_JA, FREIGABE_NEIN = "JA", "NEIN"


def schreibe_freigabeliste(profil: dict, pfad: str | Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Freigabe"
    ws.append(SPALTEN)
    for c in ws[1]:
        c.font, c.fill = Font(bold=True), PatternFill("solid", fgColor="DDDDDD")
    for key, m in profil["merkmale"].items():
        if "wert" not in m:                       # Häufigkeits-Merkmale: nur Information, keine Freigabe
            continue
        trend = "; ".join(f"ab {t['ab_jahr']}: {t['von']} -> {t['nach']} ({t['sicherheit']})"
                          for t in m.get("trend", []))
        vorbelegt = {"freigegeben": FREIGABE_JA, "abgelehnt": FREIGABE_NEIN}.get(m.get("status"), "")
        ws.append([key, m["beschreibung"], m["wert"], m.get("belegt_in", ""), m.get("sicherheit", ""),
                   trend, vorbelegt, "", m.get("status", "")])
    dv = DataValidation(type="list", formula1=f'"{FREIGABE_JA},{FREIGABE_NEIN}"', allow_blank=True,
                        showErrorMessage=True, errorTitle="Freigabe", error="Bitte JA oder NEIN wählen")
    ws.add_data_validation(dv)
    dv.add(f"G2:G{max(2, ws.max_row)}")
    for spalte, breite in zip("ABCDEFGHI", (24, 52, 22, 20, 12, 40, 18, 22, 16)):
        ws.column_dimensions[spalte].width = breite
    ws.freeze_panes = "A2"
    wb.save(pfad)


def uebernehme_freigaben(profil_pfad: str | Path, liste_pfad: str | Path) -> dict[str, list[str]]:
    """Excel-Entscheidungen ins Profil übernehmen. Liefert {freigegeben, abgelehnt, offen}."""
    profil_pfad = Path(profil_pfad)
    try:
        profil = yaml.safe_load(profil_pfad.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise RegelFehler(f"Kein Profil gefunden ({profil_pfad}) – zuerst „Hausprofil lernen“ ausführen") from None
    ws = load_workbook(liste_pfad, data_only=True)["Freigabe"]
    kopf = [c.value for c in ws[1]]
    if kopf[:len(SPALTEN)] != SPALTEN:
        raise RegelFehler(f"{Path(liste_pfad).name}: Spaltenköpfe wurden verändert – Liste bitte neu erzeugen")
    ergebnis: dict[str, list[str]] = {"freigegeben": [], "abgelehnt": [], "offen": []}
    for nr, zeile in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        key, entscheidung, eigener = zeile[0], zeile[6], zeile[7]
        if not key:
            continue
        m = profil["merkmale"].get(key)
        if m is None:
            raise RegelFehler(f"Zeile {nr}: Merkmal „{key}“ gibt es im Profil nicht – Liste bitte neu erzeugen")
        entscheidung = str(entscheidung or "").strip().upper()
        if entscheidung == FREIGABE_JA:
            if eigener not in (None, ""):
                m["wert"], m["quelle"] = str(eigener).strip(), "manuell"
            m["status"] = "freigegeben"
            m.pop("vorschlag_neu", None)
            ergebnis["freigegeben"].append(key)
        elif entscheidung == FREIGABE_NEIN:
            m["status"] = "abgelehnt"
            ergebnis["abgelehnt"].append(key)
        elif entscheidung:
            raise RegelFehler(f"Zeile {nr}: „{zeile[6]}“ – bitte JA, NEIN oder leer eintragen")
        else:
            ergebnis["offen"].append(key)
    profil_pfad.write_text("# Hausprofil – VERTRAULICH, nur lokal. Status je Merkmal: vorgeschlagen -> freigegeben\n"
                           + yaml.safe_dump(profil, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return ergebnis
