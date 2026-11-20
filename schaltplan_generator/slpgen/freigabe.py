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
           "Änderung über die Jahre", "Freigabe (JA/NEIN)", "Eigener Wert (nur mit JA)", "Merkmal (intern)",
           "Erlaubte Form / Beispiel"]
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
        ws.append([m["beschreibung"], _zur_freigabe(m), str(bisher), belegt, sicher, trend, vorbelegt, None, key, erlaubte_form(key)])
    dv = DataValidation(type="list", formula1=f'"{JA},{NEIN}"', allow_blank=True,
                        showErrorMessage=True, errorTitle="Freigabe", error="Bitte JA oder NEIN wählen")
    ws.add_data_validation(dv)
    dv.add(f"G2:G{max(2, ws.max_row)}")
    for zeile in ws.iter_rows(min_row=2):
        zeile[S_EIGENER].number_format = "@"      # als Text: Excel macht aus „1,5“ sonst die Zahl 1.5
        zeile[S_KEY].font = Font(color="999999")
    for spalte, breite in zip("ABCDEFGHIJ", (52, 22, 20, 20, 12, 40, 18, 24, 22, 60)):
        ws.column_dimensions[spalte].width = breite
    ws.freeze_panes = "A2"
    wb.save(pfad)


# Farbkürzel nach IEC 60757:1983 (GNYE = Schutzleiter grün-gelb)
FARBEN_IEC60757 = {"BK", "BN", "RD", "OG", "YE", "GN", "BU", "VT", "GY", "WH", "PK", "GD", "TQ", "SR", "GNYE"}
HAUS_FARBEN = {"DBU", "LBU"}            # ANNAHME A17: dunkel-/hellblau als Hausregel (im Bestand üblich)
ADRESS_SCHREIBWEISEN = {"iec": "IEC (%I/%Q/%IW)", "deutsch": "deutsch (E/A/EW/AW)"}
DEUTSCHE_FARBEN = {"SW", "BR", "RT", "OR", "GE", "BL", "VI", "GR", "WS", "RS", "GNGE"}

# Erlaubte Form je Merkmal – steht auch als Spalte „Erlaubte Form / Beispiel“ in der Excel-Liste
FORM = {
    "kennbuchstabe_": "1–3 Großbuchstaben ohne Ziffer, z. B. T oder KF",
    "ader_": "Farbkürzel nach IEC 60757, z. B. DBU oder DBU/WH (Querschnitt nicht hier eintragen)",
    "feldklemmleiste": "Klemmleiste wie -X10 oder -XD1",
    "haeufigste_ader_0_75": "Farbkürzel und Querschnitt, z. B. DBU 0,75",
    "sps_adressschreibweise": "IEC oder deutsch",
    "spaltenraster": "Anzahl und Breite, z. B. 10 Spalten à 39 mm",
    "schriftfeld_felder": "Feldnamen mit Komma, z. B. Datum, Bearb., Rev. (auch Felder, die das Programm nicht kennt)",
    "datumsformat": "TT.MM.JJJJ, TT.MM.JJ oder JJJJ-MM-TT",
}


def erlaubte_form(key: str) -> str:
    return next((f for p, f in FORM.items() if key.startswith(p)), "")


def _farbe(text: str) -> str:
    """„gn/ye“ -> „GNYE“, „DBU/WH“ bleibt; wirft RegelFehler bei unbekanntem Kürzel."""
    teile = text.replace("GN/YE", "GNYE").split("/")
    for t in teile:
        if t in DEUTSCHE_FARBEN and t not in FARBEN_IEC60757:
            raise RegelFehler(f"„{t}“ ist ein deutsches Kürzel – bitte IEC 60757 verwenden, z. B. RD statt RT")
        if t not in FARBEN_IEC60757 | HAUS_FARBEN:
            raise RegelFehler(FORM["ader_"])
    if len(teile) > 2:
        raise RegelFehler(FORM["ader_"])
    return "/".join(teile)


def pruefe_eigenen_wert(key: str, wert: str) -> str:
    """Eigenen Wert vereinheitlichen und prüfen; liefert den bereinigten Wert oder wirft RegelFehler (Hinweis)."""
    wert = " ".join(wert.split())
    if key.startswith("kennbuchstabe_"):
        wert = wert.upper()
        if not re.fullmatch(r"[A-Z]{1,3}", wert):
            raise RegelFehler(FORM["kennbuchstabe_"])
    elif key.startswith("ader_"):
        wert = _farbe(wert.upper())
    elif key == "feldklemmleiste":
        wert = wert.upper()
        wert = "-" + wert if wert.startswith("X") else wert
        if not re.fullmatch(r"-X[A-Z]?\d{1,3}", wert):
            raise RegelFehler(FORM["feldklemmleiste"])
    elif key == "haeufigste_ader_0_75":
        mt = re.fullmatch(r"(\S+) 0[,.]75", wert.upper())
        if not mt:
            raise RegelFehler(FORM["haeufigste_ader_0_75"])
        wert = f"{_farbe(mt.group(1))} 0,75"
    elif key == "spaltenraster":
        mt = re.fullmatch(r"(\d{1,2})\s*(?:spalten)?\s*(?:à|a|x|zu|je)?\s*(\d{2,3}(?:[.,]\d)?)\s*(?:mm)?", wert.lower())
        if not mt or not 4 <= int(mt.group(1)) <= 20:
            raise RegelFehler(FORM["spaltenraster"])
        wert = f"{int(mt.group(1))} Spalten à {mt.group(2).replace('.', ',')} mm"
    elif key == "datumsformat":
        erlaubt = {"TT.MM.JJJJ", "JJJJ-MM-TT", "TT.MM.JJ"}
        if wert.upper() not in erlaubt:
            raise RegelFehler(FORM["datumsformat"])
        wert = wert.upper()
    elif key == "schriftfeld_felder":
        teile = [t.strip() for t in wert.split(",") if t.strip()]
        if not teile or not all(re.fullmatch(r"[A-Za-zÄÖÜäöüß][\w.\- ]{0,24}", t) for t in teile):
            raise RegelFehler(FORM["schriftfeld_felder"])
        wert = ", ".join(teile)
    elif key == "sps_adressschreibweise":
        treffer = [v for k, v in ADRESS_SCHREIBWEISEN.items() if wert.lower().startswith(k)]
        if not treffer:
            raise RegelFehler(FORM["sps_adressschreibweise"])
        wert = treffer[0]
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

    entscheidungen, fehler = [], []
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
        roh = "" if z[S_EIGENER] is None else _als_text(z[S_EIGENER])
        eigener = roh or None
        if wahl not in ("", JA, NEIN):
            fehler.append(f"Zeile {nr}: „{z[S_FREIGABE]}“ – bitte JA, NEIN oder leer eintragen")
            continue
        if eigener is not None and wahl != JA:
            fehler.append(f"Zeile {nr} ({m['beschreibung']}): eigener Wert nur zusammen mit JA möglich")
            continue
        if eigener is not None:
            try:
                eigener = pruefe_eigenen_wert(key, eigener)
            except RegelFehler as e:
                fehler.append(f"Zeile {nr} ({m['beschreibung']}): eigener Wert „{roh}“ ungültig – {e}")
                continue
        entscheidungen.append((m, wahl, eigener))
    if fehler:
        raise RegelFehler("Es wurde nichts übernommen. Bitte in der Liste korrigieren, speichern und "
                          "Menüpunkt 7 erneut ausführen:\n" + "\n".join(f"  • {f}" for f in fehler))

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
