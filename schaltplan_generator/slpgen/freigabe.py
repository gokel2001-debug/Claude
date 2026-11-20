"""Freigabe des gelernten Hausprofils über eine Excel-Liste (statt Programmdateien zu bearbeiten).

Ablauf: `lernen` schreibt neben profil.yaml die Liste profil_freigabe.xlsx. Der Nutzer trägt je
Zeile in „Freigabe“ JA oder NEIN ein, optional (nur mit JA) einen eigenen Wert, speichert und
ruft `freigabe` auf. Erst freigegebene Werte darf der Generator später verwenden.

Schutz gegen veraltete Listen: Die Spalte „Zur Freigabe“ muss noch zum Profil passen, sonst
wird abgebrochen (z. B. wenn nach dem Ausfüllen erneut gelernt wurde).
"""
from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path

import yaml
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils.exceptions import InvalidFileException
from openpyxl.worksheet.datavalidation import DataValidation

from .modell import RegelFehler

SPALTEN = ["Beschreibung", "Zur Freigabe", "Bisher freigegeben", "Belegt in", "Sicherheit",
           "Änderung über die Jahre", "Freigabe (JA/NEIN)", "Eigener Wert (nur mit JA)", "Merkmal (intern)"]
S_BESCHR, S_VORSCHLAG, S_BISHER, S_FREIGABE, S_EIGENER, S_KEY = 0, 1, 2, 6, 7, 8
JA, NEIN = "JA", "NEIN"
NEU_LERNEN = "Liste bitte neu erzeugen: Menüpunkt 6 (Hausprofil lernen) erneut ausführen"


def _offener_vorschlag(m: dict) -> dict | None:
    v = m.get("vorschlag_neu")
    return v if v and v.get("status") != "abgelehnt" else None


def _zur_freigabe(m: dict) -> str:
    """Wert, über den entschieden wird: offener neuer Lernvorschlag, sonst der aktuelle Wert."""
    return str((_offener_vorschlag(m) or {}).get("wert", m["wert"]))


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
        quelle = _offener_vorschlag(m) or m       # Belege/Trend gehören zum Wert, über den entschieden wird
        trend = "; ".join(f"ab {t['ab_jahr']}: {t['von']} -> {t['nach']} ({t['sicherheit']})"
                          for t in quelle.get("trend", []))
        bisher = m["wert"] if m.get("status") == "freigegeben" else ""
        if m.get("quelle") == "manuell" and not _offener_vorschlag(m):
            belegt, sicher = "eigener Wert", "–"
        else:
            belegt, sicher = quelle.get("belegt_in", ""), quelle.get("sicherheit", "")
        # nur vorbelegen, wenn es nichts Neues zu entscheiden gibt
        vorbelegt = "" if _offener_vorschlag(m) else {"freigegeben": JA, "abgelehnt": NEIN}.get(m.get("status"), "")
        ws.append([m["beschreibung"], _zur_freigabe(m), str(bisher), belegt, sicher, trend, vorbelegt, None, key])
    dv = DataValidation(type="list", formula1=f'"{JA},{NEIN}"', allow_blank=True,
                        showErrorMessage=True, errorTitle="Freigabe", error="Bitte JA oder NEIN wählen")
    ws.add_data_validation(dv)
    dv.add(f"G2:G{max(2, ws.max_row)}")
    for zeile in ws.iter_rows(min_row=2):
        zeile[S_EIGENER].number_format = "@"      # als Text: Excel macht aus „1,5“ sonst die Zahl 1.5
        zeile[S_KEY].font = Font(color="999999")
    for spalte, breite in zip("ABCDEFGHI", (52, 22, 20, 20, 12, 40, 18, 24, 22)):
        ws.column_dimensions[spalte].width = breite
    ws.freeze_panes = "A2"
    wb.save(pfad)


# Zulässige eigene Werte je Merkmalsart (Klartext-Hinweis bei Verstoß)
PRUEFUNG = [
    ("kennbuchstabe_", re.compile(r"[A-Z]{1,3}"), "Kennbuchstabe: 1–3 Großbuchstaben ohne Ziffer, z. B. T oder KF"),
    ("ader_", re.compile(r"[A-Z]{2,4}(/[A-Z]{2,4})?"),
     "Aderfarbe als Farbkürzel nach IEC 60757, z. B. DBU oder DBU/WH (Querschnitt nicht hier eintragen)"),
    ("feldklemmleiste", re.compile(r"-X[A-Z]?\d{1,3}"), "Klemmleiste wie -X10 oder -XD1"),
]


def pruefe_eigenen_wert(key: str, wert: str) -> str:
    """Eigenen Wert vereinheitlichen und prüfen; liefert den bereinigten Wert oder wirft RegelFehler (Hinweis)."""
    wert = wert.strip().upper()
    if key == "feldklemmleiste" and wert.startswith("X"):
        wert = "-" + wert
    for praefix, muster, hinweis in PRUEFUNG:
        if key.startswith(praefix) and not muster.fullmatch(wert):
            raise RegelFehler(hinweis)
    return wert


def _als_text(wert) -> str:
    if isinstance(wert, float):                  # trotzdem als Zahl eingegeben -> deutsches Komma
        return f"{wert:g}".replace(".", ",")
    return str(wert).strip()


def _lade_profil(pfad: Path) -> dict:
    try:
        profil = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise RegelFehler(f"Kein Profil gefunden ({pfad}) – zuerst Menüpunkt 6 (Hausprofil lernen)") from None
    except yaml.YAMLError:
        raise RegelFehler(f"{pfad} ist beschädigt – bitte löschen und Menüpunkt 6 erneut ausführen") from None
    if not isinstance(profil, dict) or "merkmale" not in profil:
        raise RegelFehler(f"{pfad} hat kein gültiges Profilformat – bitte löschen und Menüpunkt 6 erneut ausführen")
    return profil


def _lade_liste(pfad: Path):
    try:
        return load_workbook(pfad, data_only=True)["Freigabe"]
    except FileNotFoundError:
        raise RegelFehler(f"Freigabeliste fehlt ({pfad}) – {NEU_LERNEN}") from None
    except KeyError:
        raise RegelFehler(f"{pfad.name}: Blatt „Freigabe“ fehlt (umbenannt?) – {NEU_LERNEN}") from None
    except (InvalidFileException, zipfile.BadZipFile, OSError):
        raise RegelFehler(f"{pfad.name} ist keine gültige .xlsx-Datei (als .xls gespeichert?) – {NEU_LERNEN}") from None


def uebernehme_freigaben(profil_pfad: str | Path, liste_pfad: str | Path) -> dict[str, list[str]]:
    """Excel-Entscheidungen ins Profil übernehmen. Liefert Beschreibungen je {freigegeben, abgelehnt, offen}."""
    profil_pfad, liste_pfad = Path(profil_pfad), Path(liste_pfad)
    profil = _lade_profil(profil_pfad)
    ws = _lade_liste(liste_pfad)
    if [c.value for c in ws[1]][:len(SPALTEN)] != SPALTEN:
        raise RegelFehler(f"{liste_pfad.name}: Spaltenköpfe wurden verändert – {NEU_LERNEN}")

    entscheidungen = []
    for nr, z in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        key = z[S_KEY]
        if not key:
            continue
        m = profil["merkmale"].get(key)
        if m is None or "wert" not in m:
            raise RegelFehler(f"Zeile {nr}: Merkmal gibt es im Profil nicht – {NEU_LERNEN}")
        if _als_text(z[S_VORSCHLAG]) != _zur_freigabe(m):
            raise RegelFehler(f"Zeile {nr} ({m['beschreibung']}): Liste ist veraltet, das Profil wurde inzwischen "
                              f"neu gelernt – {NEU_LERNEN}")
        wahl = str(z[S_FREIGABE] or "").strip().upper()
        eigener = None if z[S_EIGENER] is None or not _als_text(z[S_EIGENER]) else _als_text(z[S_EIGENER])
        if eigener is not None:
            try:
                eigener = pruefe_eigenen_wert(key, eigener)
            except RegelFehler as e:
                raise RegelFehler(f"Zeile {nr} ({m['beschreibung']}): eigener Wert „{z[S_EIGENER]}“ ungültig – {e}") from None
        if wahl not in ("", JA, NEIN):
            raise RegelFehler(f"Zeile {nr}: „{z[S_FREIGABE]}“ – bitte JA, NEIN oder leer eintragen")
        if eigener is not None and wahl != JA:
            raise RegelFehler(f"Zeile {nr} ({m['beschreibung']}): eigener Wert nur zusammen mit JA möglich")
        entscheidungen.append((m, wahl, eigener))

    ergebnis: dict[str, list[str]] = {"freigegeben": [], "abgelehnt": [], "offen": []}
    for m, wahl, eigener in entscheidungen:      # erst alles prüfen, dann ändern
        if wahl == JA:
            neu = _offener_vorschlag(m)
            m.pop("vorschlag_neu", None)
            if eigener is not None:
                m["wert"], m["quelle"] = eigener, "manuell"
            elif neu:
                m.update({k: v for k, v in neu.items() if k != "status"})
                m.pop("quelle", None)
            m["status"] = "freigegeben"
            ergebnis["freigegeben"].append(m["beschreibung"])
        elif wahl == NEIN:
            if _offener_vorschlag(m):
                m["vorschlag_neu"]["status"] = "abgelehnt"     # neuer Vorschlag abgelehnt, alte Freigabe bleibt
            else:
                m["status"] = "abgelehnt"
            ergebnis["abgelehnt"].append(m["beschreibung"])
        else:
            ergebnis["offen"].append(m["beschreibung"])

    shutil.copyfile(profil_pfad, profil_pfad.with_suffix(".yaml.bak"))
    profil_pfad.write_text("# Hausprofil – VERTRAULICH, nur lokal. Status je Merkmal: vorgeschlagen -> freigegeben\n"
                           + yaml.safe_dump(profil, allow_unicode=True, sort_keys=False), encoding="utf-8")
    try:
        schreibe_freigabeliste(profil, liste_pfad)                 # Spalte „Bisher freigegeben“ aktualisieren
    except PermissionError:
        ergebnis["hinweis"] = ["Excel-Liste ist noch geöffnet – Änderungen sind übernommen, Liste nicht aktualisiert"]
    return ergebnis
