"""Lernschleife (M5c, ZIEL 4c): Korrektur erfassen -> Hausregel mit Herkunft/Datum/Geltung -> wirkt beim nächsten
Plan -> Regressionstest.

Hausregeln liegen lokal in `hausprofil/hausregeln.yaml` (vertraulich, nie im Repository). Sie ändern das
Projektmodell VOR dessen Prüfung und Planung (Schicht A -> B) und stehen im Auslegungsnachweis unter
„Angewendete Hausregeln“. Zu jeder Regel wird der Fall gespeichert, an dem sie erfasst wurde (betroffene
Feldgeräte vorher/nachher, Projektdatum); `pruefe_regressionen` spielt alle Fälle erneut durch.

Regelarten (Grundgerüst, erweiterbar):
  artikel_ersetzen  Feldgerät mit Artikel `wenn` bekommt `dann` (gleiche Kategorie und gleiches Signal)
  gruppe_setzen     Feldgeräte mit Artikel `wenn` bekommen die 24-V-Gruppe `dann` (nicht für DO-Aktoren)
  mindestquerschnitt  wenn = „motorleitung“: Motor-/Leistungsleitungen mindestens `dann` mm² (leitungen.min_querschnitt_mm2)
Geltung: immer, ab Projektdatum (`gilt_ab`) und/oder nur für ein Projekt (`nur_projekt`).
"""
from __future__ import annotations

import copy
import datetime as dt
import os
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from .modell import RegelFehler

ARTEN = {"artikel_ersetzen": "Artikel ersetzen", "gruppe_setzen": "24-V-Gruppe setzen",
         "mindestquerschnitt": "Mindestquerschnitt Motor-/Leistungsleitung",
         "auswahl_ersetzen": "vom Programm gewähltes Gerät ersetzen (FU/Schütz/Motorschutzschalter/Klemme)"}
AUSWAHL_KATEGORIEN = ("fu", "schuetz", "motorschutz", "klemme")      # Geräte, die die Planung selbst aus dem Stamm wählt
ZIEL_MINDESTQUERSCHNITT = "motorleitung"
PFLICHT = ("id", "art", "wenn", "dann")
MAX_DURCHLAEUFE = 10                 # Regelketten A→B→C; mehr Durchläufe = Kreis


def lade_regeln(pfad: str | Path) -> tuple[list[dict[str, Any]], list[str]]:
    """-> (gültige Regeln, Klartext-Hinweise zu fehlerhaften Einträgen). Fehlerhafte Regeln werden übersprungen."""
    p = Path(pfad)
    if not p.is_file():
        return [], []
    try:
        daten = yaml.safe_load(p.read_text(encoding="utf-8"))
    except (yaml.YAMLError, UnicodeDecodeError):
        return [], [f"Hausregeln: {p.name} ist beschädigt und wird nicht verwendet – Sicherung {p.name}.bak zurückkopieren"]
    roh = daten.get("regeln") if isinstance(daten, dict) else None
    if not isinstance(roh, list):
        return [], [f"Hausregeln: {p.name} hat kein gültiges Format („regeln:“ mit Liste) – nicht verwendet"]
    regeln, hinweise = [], []
    for i, r in enumerate(roh, 1):
        fehlt = [k for k in PFLICHT if not isinstance(r, dict) or not isinstance(r.get(k), str) or not r.get(k)]
        zahl_ok = True
        if not fehlt and isinstance(r, dict) and r.get("art") == "mindestquerschnitt":
            try:
                zahl_ok = mm2(r["dann"]) > 0
            except RegelFehler:
                zahl_ok = False
        if fehlt or r["art"] not in ARTEN or not isinstance(r.get("aktiv", True), bool) or not zahl_ok:
            grund = f"fehlt/ungültig: {', '.join(fehlt)}" if fehlt else "Art oder „aktiv“ (true/false) ungültig"
            hinweise.append(f"Hausregeln: Eintrag {i} übersprungen ({grund})")
            continue
        regeln.append(r)
    return regeln, hinweise


def speichere_regeln(pfad: str | Path, regeln: list[dict[str, Any]]) -> None:
    p = Path(pfad)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        p.with_name(p.name + ".bak").write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
    p.write_text("# Hausregeln aus Korrekturen – VERTRAULICH, nur lokal\n"
                 + yaml.safe_dump({"regeln": regeln}, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _datum(text: Any) -> dt.date | None:
    try:
        return dt.date.fromisoformat(str(text)) if text else None
    except ValueError:
        return None


BEDINGUNG_KB = "kennbuchstabe:"       # Eigenschaftsbedingung: alle Feldgeräte mit diesem Kennbuchstaben (IEC 81346-2)


def kennbuchstaben(bmk: Any) -> str:
    return re.match(r"[A-Z]*", str(bmk or "").strip().rsplit("-", 1)[-1].upper()).group(0)  # type: ignore[union-attr]


def _trifft(fg: dict[str, Any], wenn: str) -> bool:
    if wenn.lower().startswith(BEDINGUNG_KB):
        return kennbuchstaben(fg.get("bmk")) == wenn[len(BEDINGUNG_KB):].strip().upper()
    return fg.get("artikel") == wenn


def _gilt(regel: dict[str, Any], projekt: dict[str, Any]) -> bool:
    kopf = projekt.get("projekt") or {}
    if regel.get("nur_projekt") and str(kopf.get("nummer", "")) != str(regel["nur_projekt"]):
        return False
    ab, stichtag = _datum(regel.get("gilt_ab")), _datum(kopf.get("datum"))
    return not ab or not stichtag or stichtag >= ab


def wende_an(projekt: dict[str, Any], regeln: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    """Regeln (auch als Kette A→B→C) auf die Feldgeräte anwenden. -> (geändertes Modell, Klartext je Änderung)."""
    neu = copy.deepcopy(projekt)
    meldungen: list[str] = []
    aktiv = [r for r in regeln if r.get("aktiv", True) is True and _gilt(r, neu)]
    for _ in range(MAX_DURCHLAEUFE):
        geaendert = False
        for r in aktiv:
            if r["art"] == "mindestquerschnitt":
                if not isinstance(neu.get("leitungen"), dict):
                    neu["leitungen"] = {}
                ltg = neu["leitungen"]
                if mm2(ltg.get("min_querschnitt_mm2")) < mm2(r["dann"]):
                    ltg["min_querschnitt_mm2"] = mm2(r["dann"])
                    geaendert = True
                    meldungen.append(f"Hausregel {r['id']} ({ARTEN[r['art']]}): Motor-/Leistungsleitungen mindestens "
                                     f"{mm2(r['dann']):g} mm² – {r.get('bearbeiter', '?')}, {r.get('datum', '?')}, "
                                     f"Herkunft {r.get('herkunft', '?')}".replace(".", ","))
                continue
            if r["art"] == "auswahl_ersetzen":
                if not isinstance(neu.get("auswahl_ersetzen"), dict):
                    neu["auswahl_ersetzen"] = {}
                aus = neu["auswahl_ersetzen"]
                ziele = [k for k, v in aus.items() if v == r["wenn"]]            # Kette A→B, B→C ergibt A→C
                if r["wenn"] not in aus:                                     # eigener Eintrag nur einmal
                    ziele.append(r["wenn"])
                for k in ziele:                 # Meldung je Gerät erst bei tatsächlichem Ersatz (motor.ersatz)
                    aus[k] = r["dann"]
                    geaendert = True
                continue
            feld = "artikel" if r["art"] == "artikel_ersetzen" else "gruppe"
            for fg in neu.get("feldgeraete") or []:
                if not isinstance(fg, dict) or not _trifft(fg, r["wenn"]) or fg.get(feld) == r["dann"]:
                    continue
                if r["wenn"].lower().startswith(BEDINGUNG_KB) and any(   # Artikelregel geht der Sammelregel vor
                        x["art"] == r["art"] and x["wenn"] == fg.get("artikel") for x in aktiv):
                    continue
                fg[feld] = r["dann"]
                geaendert = True
                meldungen.append(f"Hausregel {r['id']} ({ARTEN[r['art']]}): {fg.get('bmk')} {r['wenn']} → {r['dann']} "
                                 f"– {r.get('bearbeiter', '?')}, {r.get('datum', '?')}, Herkunft {r.get('herkunft', '?')}")
        if not geaendert:
            return neu, meldungen
    raise RegelFehler("Hausregeln bilden einen Kreis (z. B. A → B → A) – eine der Regeln abschalten (Befehl hausregel aus)")


def mm2(wert: Any) -> float:
    """Querschnitt aus 2.5 / „2,5“ / None (0); ungültig -> RegelFehler im Klartext."""
    if wert in (None, ""):
        return 0.0
    try:
        return float(str(wert).replace(",", "."))
    except ValueError:
        raise RegelFehler(f"Mindestquerschnitt „{wert}“ ist keine Zahl – z. B. 2,5") from None


def _naechste_id(regeln: list[dict[str, Any]]) -> str:
    nummern = [int(r["id"][1:]) for r in regeln if str(r.get("id", "")).startswith("R") and r["id"][1:].isdigit()]
    return f"R{max(nummern, default=0) + 1}"


def erfasse_korrektur(pfad: str | Path, art: str, wenn: str, dann: str, herkunft: str, grund: str,
                      projekt: dict[str, Any], stamm: dict[str, Any], gilt_ab: str | None = None,
                      nur_projekt: str | None = None, bearbeiter: str | None = None,
                      probelauf: Callable[[dict[str, Any]], Any] | None = None,
                      nur_vorschau: bool = False,
                      planartikel: Callable[[dict[str, Any]], set[str]] | None = None) -> dict[str, Any]:
    """Korrektur als Hausregel speichern, samt Regressionsfall. Speichert nur, wenn die Regel wirkt und der
    Probelauf (Prüfung + Planung mit allen Regeln) gelingt."""
    if art not in ARTEN:
        raise RegelFehler(f"Regelart „{art}“ unbekannt – möglich: {', '.join(ARTEN)}")
    artikel = stamm.get("artikel", {})
    gross = {k.upper(): k for k in artikel}                     # Groß-/Kleinschreibung egal
    wenn = gross.get(str(wenn).strip().upper(), str(wenn).strip())
    bedingung = wenn.lower().startswith(BEDINGUNG_KB)
    if bedingung:
        if art != "gruppe_setzen":
            raise RegelFehler("Bedingung „kennbuchstabe:…“ gibt es nur für „24-V-Gruppe setzen“ – Artikel nur einzeln ersetzen")
        kb = wenn[len(BEDINGUNG_KB):].strip().upper()
        if not re.fullmatch(r"[A-Z]{1,3}", kb):
            raise RegelFehler(f"Kennbuchstabe „{kb}“ ungültig – 1 bis 3 Buchstaben, z. B. kennbuchstabe:B")
        wenn = BEDINGUNG_KB + kb
    if art in ("artikel_ersetzen", "auswahl_ersetzen"):
        dann = gross.get(str(dann).strip().upper(), str(dann).strip())
    if art == "mindestquerschnitt":
        try:
            if wenn != ZIEL_MINDESTQUERSCHNITT or not 0.5 <= float(str(dann).replace(",", ".")) <= 240:
                raise ValueError
        except ValueError:
            raise RegelFehler("Bitte eine Zahl in mm² eingeben (0,5 bis 240), z. B. 2,5") from None
        dann = f"{float(str(dann).replace(',', '.')):g}"
        if not (projekt.get("motoren") or [fg for fg in projekt.get("feldgeraete") or []
                                          if isinstance(fg, dict) and fg.get("typical")]):
            raise RegelFehler("Im Projekt gibt es keine Motor-/Leistungsleitung – Korrektur würde nichts ändern")
    elif not bedingung and wenn not in artikel:
        raise RegelFehler(f"Artikel „{wenn}“ gibt es nicht im Gerätestamm")
    if art == "auswahl_ersetzen":
        if wenn == dann:
            raise RegelFehler("Ersatz ist derselbe Artikel – Korrektur würde nichts ändern")
        kat = artikel[wenn].get("kategorie")
        if kat not in AUSWAHL_KATEGORIEN:
            raise RegelFehler(f"„{wenn}“ ({kat}) wählt das Programm nicht selbst – für Feldgeräte „Artikel ersetzen“ "
                              f"verwenden; hier nur Frequenzumrichter, Schütz, Motorschutzschalter, Klemme")
        if dann not in artikel or artikel[dann].get("kategorie") != kat:
            raise RegelFehler(f"Ersatz „{dann}“ muss ein Artikel derselben Art ({kat}) aus dem Gerätestamm sein")
    if art == "artikel_ersetzen":
        if dann not in artikel:
            raise RegelFehler(f"Ersatzartikel „{dann}“ gibt es nicht im Gerätestamm")
        a, b = artikel[wenn], artikel[dann]
        if (a.get("kategorie"), a.get("signal")) != (b.get("kategorie"), b.get("signal")):
            raise RegelFehler(f"Ersatzartikel „{dann}“ passt nicht: {b.get('kategorie')}/{b.get('signal')} statt "
                              f"{a.get('kategorie')}/{a.get('signal')} – nur gleichartige Geräte ersetzen")
    if art == "gruppe_setzen" and (dann == "DO-Last" or (not bedingung and artikel[wenn].get("signal") == "DO")):
        raise RegelFehler("DO-Aktoren laufen immer über die Lastspannung der DO-Karte (Gruppe DO-Last) – "
                          "diese Zuordnung ist nicht per Hausregel änderbar")
    if gilt_ab and _datum(gilt_ab) is None:
        raise RegelFehler(f"Datum „{gilt_ab}“ ungültig – bitte JJJJ-MM-TT, z. B. 2027-01-01")
    regeln, hinweise = lade_regeln(pfad)
    if hinweise:
        raise RegelFehler("Hausregel-Datei fehlerhaft – erst reparieren: " + "; ".join(hinweise))
    widerspruch = [r for r in regeln if r.get("aktiv", True) and r["art"] == art and r["wenn"] == wenn and r["dann"] != dann]
    if widerspruch:
        raise RegelFehler(f"Widerspruch zu Hausregel {widerspruch[0]['id']} ({wenn} → {widerspruch[0]['dann']}) – "
                          f"alte Regel erst abschalten: hausregel aus {widerspruch[0]['id']}")
    mit_bisherigen, _ = wende_an(projekt, regeln)                 # Korrektur bezieht sich auf den erzeugten Plan
    if art == "mindestquerschnitt":
        alt_min = (mit_bisherigen.get("leitungen") or {}).get("min_querschnitt_mm2") \
            if isinstance(mit_bisherigen.get("leitungen"), dict) else None
        ausschnitt: dict[str, Any] = {"leitungen": {"min_querschnitt_mm2": alt_min}}
        betroffen: list[Any] = [ausschnitt]
    elif art == "auswahl_ersetzen":
        vorher = mit_bisherigen.get("auswahl_ersetzen")
        ausschnitt = {"auswahl_ersetzen": copy.deepcopy(vorher) if isinstance(vorher, dict) else {}}
        betroffen = [wenn] if planartikel is None or wenn in planartikel(mit_bisherigen) else []
    else:
        betroffen = [fg for fg in mit_bisherigen.get("feldgeraete") or [] if isinstance(fg, dict) and _trifft(fg, wenn)]
        ausschnitt = {"feldgeraete": copy.deepcopy(betroffen)}
    if not betroffen:
        raise RegelFehler(f"Im Plan kommt Artikel „{wenn}“ nicht vor (ggf. schon durch eine Hausregel ersetzt"
                          f"{'' if art != 'auswahl_ersetzen' else ' oder vom Programm nicht gewählt'}) – "
                          f"Korrektur würde nichts ändern")
    kopf = projekt.get("projekt") or {}
    regel: dict[str, Any] = {
        "id": _naechste_id(regeln), "art": art, "wenn": wenn, "dann": dann, "aktiv": True,
        "herkunft": herkunft, "bearbeiter": bearbeiter or os.environ.get("USERNAME") or os.environ.get("USER") or "unbekannt",
        "grund": grund, "datum": dt.date.today().isoformat(), "gilt_ab": gilt_ab or "", "nur_projekt": nur_projekt or "",
        "fall": {"projekt": {"nummer": kopf.get("nummer", ""), "datum": str(kopf.get("datum", ""))},
                 "eingabe": copy.deepcopy(ausschnitt), "erwartet": None}}
    fall = {"projekt": regel["fall"]["projekt"], **copy.deepcopy(ausschnitt)}
    ohne, _ = wende_an(fall, regeln)
    mit, mit_meldungen = wende_an(fall, [*regeln, regel])
    if _teil(mit, ausschnitt) == _teil(ohne, ausschnitt):
        raise RegelFehler("Die neue Regel ändert nichts (Geltung passt nicht zum Projekt oder eine andere Regel "
                          "verdeckt sie)")
    if probelauf:
        try:
            probelauf(wende_an(projekt, [*regeln, regel])[0])
        except RegelFehler as e:
            raise RegelFehler(f"Korrektur nicht gespeichert – mit ihr wäre der Plan nicht erzeugbar: {e}") from None
    regel["fall"]["erwartet"] = _teil(mit, ausschnitt)
    regel["vorschau"] = [x for x in mit_meldungen if x.startswith(f"Hausregel {regel['id']} ")]
    if art == "gruppe_setzen" and bedingung:
        regel["vorschau"].append("Hinweis: DO-Aktoren bleiben immer in der Gruppe DO-Last (Lastspannung der DO-Karte)")
    if art == "gruppe_setzen":
        gruppen = {fg.get("gruppe") for fg in mit_bisherigen.get("feldgeraete") or [] if isinstance(fg, dict)}
        if dann not in gruppen:
            regel["vorschau"].append(f"Hinweis: „{dann}“ ist eine NEUE 24-V-Gruppe (eigener Abgang) – bisher: "
                                     f"{', '.join(sorted(str(g) for g in gruppen if g))}")
    if not nur_vorschau:
        speichere_regeln(pfad, [*regeln, {k: v for k, v in regel.items() if k != "vorschau"}])
    return regel


def _teil(modell: dict[str, Any], ausschnitt: dict[str, Any]) -> dict[str, Any]:
    """Nur die Teile des Modells, die der Regressionsfall enthält (Feldgeräte bzw. Mindestquerschnitt)."""
    teil: dict[str, Any] = {}
    for k in ausschnitt:
        if k == "leitungen":
            roh = modell.get("leitungen")
            ltg: dict[str, Any] = roh if isinstance(roh, dict) else {}
            teil[k] = {"min_querschnitt_mm2": ltg.get("min_querschnitt_mm2")}
        else:
            teil[k] = modell.get(k)
    return teil


def _fall(r: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """-> (Modell zum Durchspielen, Ausschnitt). Alte Fälle (Liste von Feldgeräten) bleiben lesbar."""
    eingabe = r["fall"].get("eingabe", [])
    ausschnitt = {"feldgeraete": eingabe} if isinstance(eingabe, list) else dict(eingabe)
    return {"projekt": r["fall"].get("projekt", {}), **copy.deepcopy(ausschnitt)}, ausschnitt


def schalte(pfad: str | Path, regel_id: str, aktion: str) -> dict[str, Any]:
    """Regel ein-/ausschalten oder löschen (aktion: ein | aus | loeschen)."""
    regeln, hinweise = lade_regeln(pfad)
    if hinweise:
        raise RegelFehler("Hausregel-Datei fehlerhaft – erst reparieren: " + "; ".join(hinweise))
    treffer = [r for r in regeln if r["id"] == regel_id]
    if not treffer:
        raise RegelFehler(f"Hausregel {regel_id} gibt es nicht – vorhanden: {', '.join(r['id'] for r in regeln) or 'keine'}")
    if aktion == "loeschen":
        regeln = [r for r in regeln if r["id"] != regel_id]
    else:
        treffer[0]["aktiv"] = aktion == "ein"
    speichere_regeln(pfad, regeln)
    return treffer[0]


def pruefe_regressionen(regeln: list[dict[str, Any]]) -> list[str]:
    """Jeden gespeicherten Fall (mit seinem Projektdatum) mit ALLEN aktiven Regeln erneut durchspielen."""
    befunde = []
    for r in regeln:
        if r.get("aktiv", True) is not True or not isinstance(r.get("fall"), dict):
            continue
        fall, ausschnitt = _fall(r)
        try:
            ist, _ = wende_an(fall, regeln)
        except RegelFehler as e:
            befunde.append(str(e))
            continue
        erwartet = r["fall"].get("erwartet")
        if isinstance(erwartet, list):                         # alter Fall: nur Feldgeräte
            erwartet = {"feldgeraete": erwartet}
        if _teil(ist, ausschnitt) != erwartet:
            befunde.append(f"Regressionsfall zu {r['id']} ({r['wenn']} → {r['dann']}) liefert jetzt ein anderes Ergebnis – "
                           f"eine spätere Regel verändert ihn (gewollt? dann: hausregeln --bestaetigen)")
    return befunde


def bestaetige(pfad: str | Path) -> int:
    """Aktuelles Ergebnis aller Fälle als neues Soll übernehmen (nach bewusster Regeländerung)."""
    regeln, _ = lade_regeln(pfad)
    for r in regeln:
        if isinstance(r.get("fall"), dict):
            fall, ausschnitt = _fall(r)
            r["fall"]["erwartet"] = _teil(wende_an(fall, regeln)[0], ausschnitt)
    speichere_regeln(pfad, regeln)
    return len(regeln)
