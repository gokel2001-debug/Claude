"""Projektmodell (Schicht A → B): Schema v1, Prüfung mit Lücken im Klartext, Ergänzung um Hausvorgaben.

Das Projektmodell ist die Eingabe des Planungskerns (`regeln.plane`). Es entsteht aus der
Excel-Vorlage, von Hand oder durch eine KI (siehe docs/KI_AUFBEREITUNG.md). Das Schema ist hier
als Daten hinterlegt; `docs/SCHEMA_PROJEKTMODELL.md` wird daraus erzeugt (`schema_markdown`).

Zwei Arten von Abschnitten:
  P = Projektangaben (kommen aus dem Lastenheft, Pflicht für die KI)
  H = Hausvorgaben (fehlen sie, werden sie aus `hausvorgaben.yaml` ergänzt)

Grundsatz: `bereit_machen` liefert entweder ein Modell, mit dem `regeln.plane` ohne Absturz läuft,
oder einen RegelFehler mit allen Lücken im Klartext.
"""
from __future__ import annotations

import copy
import datetime as dt
import difflib
import re
from dataclasses import dataclass
from typing import Any

from .modell import RegelFehler

SCHEMA = "projektmodell/1"
RE_BMK = re.compile(r"-?[A-Z]{1,3}\d{1,4}")
RE_ZAHL = re.compile(r"\s*([-+]?\d+(?:[.,]\d+)?)\s*(?:m|kW|A|V|W|%|mm²|mm2)?\s*")
RE_DATEINAME_VERBOTEN = re.compile(r'[<>:"/\\|?*]|\.\.')
FELD_KATEGORIEN = ("sensor", "aktor")
SIGNALARTEN = ("DI", "DO", "AI", "AO")
ADRESS_PLATZHALTER = {"byte": 0, "bit": 0, "wort": 0}


@dataclass(frozen=True)
class Feld:
    name: str
    typ: str                  # text|zahl|wahl:a|b|ja_nein | datum | bmk | artikel:<kat> | liste_artikel:<kat> | typical | tabelle
    pflicht: bool
    text: str
    beispiel: str = ""
    bereich: tuple[float, float] | None = None


# Abschnitt -> (Art P/H, Liste?, Felder, Beschreibung, Klartextname eines Eintrags)
ABSCHNITTE: dict[str, tuple[str, bool, list[Feld], str, str]] = {
    "projekt": ("P", False, [
        Feld("nummer", "text", True, "Projekt-/Auftragsnummer (wird Dateiname)", "P-2026-001"),
        Feld("bezeichnung", "text", True, "Kurzbezeichnung der Anlage", "Steuerschrank Förderband"),
        Feld("kunde", "text", False, "Kunde (bleibt lokal, nie ins Repository)", "Musterkunde AG"),
        Feld("anlage", "text", False, "Anlagenkennzeichen (Funktionsaspekt IEC 81346), beginnt mit =", "=FB1"),
        Feld("ort", "text", False, "Ortskennzeichen (Schrank), beginnt mit +", "+SS1"),
        Feld("ersteller", "text", False, "Bearbeiter", "N.N."),
        Feld("datum", "datum", False, "Erstelldatum JJJJ-MM-TT", "2026-10-24"),
        Feld("revision", "text", False, "Revisionsstand", "\"00\""),
    ], "Kopfdaten für Deckblatt und Schriftfeld", "Projektdaten"),
    "einspeisung": ("P", False, [
        Feld("netz", "text", True, "Netzform und Spannung", "3/N/PE AC 400/230 V 50 Hz"),
        Feld("hauptschalter", "artikel:hauptschalter", False,
             "Hauptschalter (Artikel); fehlt er, gilt die Hausvorgabe", "HS-3P-40"),
    ], "Netzanschluss des Schranks", "Einspeisung"),
    "feldgeraete": ("P", True, [
        Feld("bmk", "bmk", True, "Betriebsmittelkennzeichen: Kennbuchstabe(n) + Nummer", "B1"),
        Feld("artikel", "artikel:feld", True, "Artikel aus dem Gerätestamm (Sensor/Aktor)", "IND-M12-PNP"),
        Feld("funktion", "text", True, "Funktionstext für Plan und SPS-Liste", "Endlage Band vorne"),
        Feld("gruppe", "text", False, "gemeinsamer 24-V-Abgang (DO-Aktoren: DO-Last)", "Sensorik"),
        Feld("typical", "typical", False, "Baustein aus der Bibliothek (mehrere Signale/Leistungsteil)", "pumpe_ec"),
        Feld("laenge_m", "zahl", False, "Leitungslänge zum Gerät in m (Pflicht bei Leistungsteil, sonst für Kabelliste)", "15",
             (0.1, 1000)),
    ], "Sensoren, Aktoren und Bausteine im Feld", "Feldgerät"),
    "motoren": ("P", True, [
        Feld("bmk", "bmk", True, "Betriebsmittelkennzeichen", "M1"),
        Feld("funktion", "text", False, "Funktionstext", "Bandantrieb"),
        Feld("p_kW", "zahl", True, "Bemessungsleistung in kW (Typenschild)", "0.75", (0.01, 500)),
        Feld("i_N_A", "zahl", True, "Bemessungsstrom in A (Typenschild)", "1.9", (0.01, 1000)),
        Feld("cos_phi", "zahl", False, "Leistungsfaktor (Typenschild), Standard 0,8", "0.78", (0.1, 1.0)),
        Feld("laenge_m", "zahl", True, "Leitungslänge Schrank–Motor in m", "12", (0.1, 1000)),
        Feld("anlauf", "wahl:direkt|fu", False, "direkt (Schütz, Standard) oder fu (Frequenzumrichter mit Freigabe, "
             "Sollwert 4–20 mA, Störmeldung)", "fu"),
    ], "Drehstrommotoren mit Direktstart oder Frequenzumrichter", "Motor"),
    "versorgung_24V": ("H", False, [
        Feld("netzteile", "liste_artikel:netzteil", True, "Netzteil-Kandidaten, das kleinste passende wird gewählt",
             "[NT-24-05, NT-24-10]"),
        Feld("gleichzeitigkeit", "zahl", False, "Gleichzeitigkeitsfaktor g", "1.0", (0.1, 1.0)),
        Feld("reserve", "zahl", False, "Reserve auf den Bedarf", "0.25", (0.0, 2.0)),
        Feld("absicherungsfaktor", "zahl", False, "I_Sicherung ≥ Faktor · I_Gruppe", "1.25", (1.0, 3.0)),
        Feld("verteilung", "text", False, "einzelsicherungen oder selektivmodul", "einzelsicherungen"),
        Feld("selektivmodul", "artikel:selektivmodul", False, "Selektivmodul bei verteilung = selektivmodul",
             "SEL-24-4K"),
    ], "24-V-Versorgung (Hausregeln)", "24-V-Versorgung"),
    "sps": ("H", False, [
        Feld("cpu", "artikel:sps_cpu", True, "SPS-CPU", "SPS-CPU"),
        Feld("module_kandidaten", "tabelle", True, "E/A-Karte je Signalart DI/DO/AI/AO", "{DI: SPS-DI16, ...}"),
        Feld("adressschema", "tabelle", True, "Adressformat je Signalart, Platzhalter {byte} {bit} {wort}",
             "{DI: \"%I{byte}.{bit}\", ...}"),
    ], "Steuerung (Hausvorgabe)", "SPS"),
    "leitungen": ("H", False, [
        Feld("freigegeben", "ja_nein", False, "Tabelle von Elektrofachkraft freigegeben", "false"),
        Feld("verlegeart", "text", False, "Verlegeart (Dokumentation)", "B2"),
        Feld("i_z_A", "tabelle", False, "Strombelastbarkeit I_z in A je Querschnitt mm²", "{1.5: 13.1}"),
        Feld("reduktionsfaktor", "zahl", False, "Reduktionsfaktor Häufung/Umgebung", "0.8", (0.1, 1.0)),
        Feld("kappa", "zahl", False, "Leitfähigkeit in m/(Ω·mm²)", "56", (30, 60)),
        Feld("du_max_prozent", "zahl", False, "zulässiger Spannungsfall in %", "3.0", (0.5, 10)),
        Feld("min_querschnitt_mm2", "zahl", False, "kleinster Querschnitt für Motor-/Leistungsleitungen in mm² (Hausregel)",
             "2.5", (0.5, 240)),
    ], "Leitungsauslegung (Hausregeln, Freigabe durch Elektrofachkraft)", "Leitungsauslegung"),
    "sicherheit": ("P", False, [
        Feld("not_halt", "ja_nein", False, "Not-Halt gefordert (wird nur als Platzhalter gezeichnet)", "true"),
        Feld("pl", "text", False, "geforderter Performance Level laut Risikobeurteilung (z. B. PL d)", "PL d"),
        Feld("funktionen", "text", False, "weitere Sicherheitsfunktionen in Klartext", "Schutztür Pumpenraum"),
        Feld("stoppkategorie", "text", False, "Stoppkategorie 0/1/2 nach EN 60204-1 laut Risikobeurteilung", "0"),
        Feld("freigabe", "text", False, "Freigabevermerk der Elektrofachkraft (Name, Datum) – erst dann entfällt "
             "„nicht für Fertigung“; die Auslegung selbst liegt außerhalb dieses Plans", "M. Muster, 2026-11-21"),
        Feld("ausgenommen", "text", False, "Feldgeräte (BMK, mit Komma), die trotz Sicherheitsbegriff an der Standard-SPS "
             "bleiben dürfen – nur mit Freigabevermerk wirksam", "S9"),
    ], "Sicherheitsfunktionen – nur Platzhalter, Auslegung und Freigabe durch Elektrofachkraft", "Sicherheit"),
}
PFLICHT_ABSCHNITTE = ("projekt", "einspeisung", "feldgeraete")
ZUSATZ = {"schema": "Schemaversion, immer „projektmodell/1“",
          "annahmen": "Liste: was die KI angenommen hat (erscheint im Auslegungsnachweis)",
          "offene_fragen": "Liste: was im Lastenheft fehlt oder unklar ist (erscheint im Auslegungsnachweis)"}
TYP_KLARTEXT = {"text": "Text", "zahl": "Zahl (Punkt oder Komma, ohne Einheit)", "ja_nein": "ja / nein",
                "datum": "Datum JJJJ-MM-TT", "bmk": "Kennzeichen wie B1", "artikel": "Artikel aus Gerätestamm",
                "liste_artikel": "Liste von Artikeln", "typical": "Bausteinname", "tabelle": "Tabelle",
                "wahl": "Auswahl"}


def _zahl(w: Any) -> float | None:
    """Zahl aus 1.5 / „1,5“ / „15 m“; None, wenn keine Zahl (bool zählt nicht)."""
    if isinstance(w, bool):
        return None
    if isinstance(w, (int, float)):
        return float(w)
    mt = RE_ZAHL.fullmatch(str(w)) if isinstance(w, str) else None
    return float(mt.group(1).replace(",", ".")) if mt else None


def _ja_nein(w: Any) -> bool | None:
    if isinstance(w, bool):
        return w
    return {"ja": True, "nein": False, "true": True, "false": False}.get(str(w).strip().lower())


def _ort(abschnitt: str, i: int | None, eintrag: Any) -> str:
    klar = ABSCHNITTE[abschnitt][4]
    if i is None:
        return klar
    bmk = f" {eintrag.get('bmk')}" if isinstance(eintrag, dict) and eintrag.get("bmk") else ""
    zeile = f", Zeile {eintrag['_zeile']}" if isinstance(eintrag, dict) and eintrag.get("_zeile") else ""
    return f"{klar}{bmk} ({i + 1}. Eintrag{zeile})"


def _leer(w: Any) -> bool:
    return w is None or w == [] or w == {} or (isinstance(w, str) and not w.strip())


def pruefe(daten: Any, stamm: dict) -> list[str]:
    """Alle Lücken und Fehler des Projektmodells als Klartext (leere Liste = gültig)."""
    if daten is None:
        return ["Die Datei ist leer"]
    if not isinstance(daten, dict):
        return ["Die Datei enthält kein Projektmodell (oberste Ebene muss aus Abschnitten wie „projekt:“ bestehen)"]
    art = stamm.get("artikel", {})
    typicals = stamm.get("typicals", {})
    luecken: list[str] = []
    if "schema" in daten and daten["schema"] != SCHEMA:
        luecken.append(f"schema: „{daten['schema']}“ wird nicht unterstützt – erwartet „{SCHEMA}“")
    for k in daten:
        if k not in ABSCHNITTE and k not in ZUSATZ and isinstance(daten[k], str) and " " in daten[k]:
            luecken.append(f"„{k}: {daten[k][:40]}…“ ist vermutlich ein Kommentar der KI – diese Zeile löschen")
        elif k not in ABSCHNITTE and k not in ZUSATZ:
            luecken.append(f"Unbekannter Abschnitt „{k}“ – erlaubt: {', '.join([*ABSCHNITTE, *ZUSATZ])} "
                     f"(Tippfehler oder falsch eingerückt?)")
    for k in ("annahmen", "offene_fragen"):
        if not _leer(daten.get(k)) and not (isinstance(daten[k], list) and all(isinstance(x, str) for x in daten[k])):
            luecken.append(f"„{k}“ muss eine Liste von Sätzen sein (je Zeile „- …“)")
    for name in PFLICHT_ABSCHNITTE:
        if _leer(daten.get(name)):
            luecken.append(f"Abschnitt „{name}“ ({ABSCHNITTE[name][3]}) fehlt oder ist leer")
    gesehen: dict[str, str] = {}
    for name, (_, liste, felder, _, _) in ABSCHNITTE.items():
        wert = daten.get(name)
        if _leer(wert):
            continue
        if liste and not isinstance(wert, list):
            luecken.append(f"Abschnitt „{name}“ muss eine Liste sein (je Eintrag eine Zeile mit „- “)")
            continue
        if not liste and not isinstance(wert, dict):
            luecken.append(f"Abschnitt „{name}“ muss Einträge der Form „feld: wert“ enthalten")
            continue
        for i, e in (enumerate(wert or []) if liste else [(None, wert)]):
            ort = _ort(name, i, e)
            if not isinstance(e, dict):
                luecken.append(f"{ort}: Eintrag muss die Form „feld: wert“ haben")
                continue
            namen = {f.name for f in felder}
            for k in e:
                if k not in namen and k != "_zeile":
                    luecken.append(f"{ort}: unbekanntes Feld „{k}“ – erlaubt: {', '.join(sorted(namen))}")
            for f in felder:
                luecken.extend(_pruefe_feld(ort, f, e.get(f.name), art, typicals))
            if name in ("feldgeraete", "motoren") and isinstance(e.get("bmk"), str):
                kurz = e["bmk"].strip().lstrip("-").upper()
                if kurz in gesehen:
                    luecken.append(f"{ort}: Kennzeichen {kurz} ist schon bei {gesehen[kurz]} vergeben")
                gesehen.setdefault(kurz, ort)
    luecken.extend(_pruefe_zusammenhang(daten, art, typicals))
    return luecken


def _pruefe_feld(ort: str, f: Feld, w: Any, art: dict, typicals: dict) -> list[str]:
    was = f"{f.text} („{f.name}“)"
    if _leer(w):
        return [f"{ort}: {was} fehlt – bitte eintragen, z. B. {f.beispiel}"] if f.pflicht else []
    typ, _, kat = f.typ.partition(":")
    if typ == "zahl":
        z = _zahl(w)
        if z is None:
            return [f"{ort}: {was} = „{w}“ ist keine Zahl – bitte nur die Zahl eintragen, z. B. {f.beispiel}"]
        if f.bereich and not f.bereich[0] <= z <= f.bereich[1]:
            return [f"{ort}: {was} = {w} liegt außerhalb {f.bereich[0]:g}…{f.bereich[1]:g} – bitte prüfen"]
    elif typ == "wahl" and str(w).strip().lower() not in kat.split("|"):
        return [f"{ort}: {was} = „{w}“ – erlaubt: {', '.join(kat.split('|'))}"]
    elif typ == "ja_nein" and _ja_nein(w) is None:
        return [f"{ort}: {was} muss ja oder nein sein"]
    elif typ == "datum" and not isinstance(w, dt.date):
        try:
            dt.date.fromisoformat(str(w))
        except ValueError:
            return [f"{ort}: {was} = „{w}“ ist kein Datum in der Form JJJJ-MM-TT"]
    elif typ == "bmk" and not (isinstance(w, str) and RE_BMK.fullmatch(w.strip().upper())):
        return [f"{ort}: Kennzeichen „{w}“ ungültig – Kennbuchstabe(n) + Nummer ohne Punkt, z. B. B7 oder KF12"]
    elif typ == "artikel":
        return _pruefe_artikel(ort, was, w, kat, art)
    elif typ == "liste_artikel":
        if not isinstance(w, list):
            return [f"{ort}: {was} muss eine Liste von Artikeln sein, z. B. {f.beispiel}"]
        return [x for a in w for x in _pruefe_artikel(ort, was, a, kat, art)]
    elif typ == "typical" and (not isinstance(w, str) or w not in typicals):
        return [f"{ort}: Baustein „{w}“ gibt es nicht – vorhanden: {', '.join(sorted(typicals)) or 'keine'}"]
    elif typ == "tabelle" and not isinstance(w, dict):
        return [f"{ort}: {was} muss eine Tabelle sein, z. B. {f.beispiel}"]
    elif typ == "text":
        if isinstance(w, bool):
            return [f"{ort}: {was} = {w} wurde als ja/nein gelesen – Text bitte in Anführungszeichen setzen"]
        if not isinstance(w, (str, int, float, dt.date)):
            return [f"{ort}: {was} muss ein einzelner Text sein"]
        if f.name == "nummer" and RE_DATEINAME_VERBOTEN.search(str(w)):
            return [f"{ort}: {was} „{w}“ enthält Zeichen, die in Dateinamen nicht erlaubt sind (< > : \" / \\ | ? * ..)"]
    return []


def _pruefe_artikel(ort: str, was: str, w: Any, kat: str, art: dict) -> list[str]:
    erlaubt = FELD_KATEGORIEN if kat == "feld" else (kat,)
    if not isinstance(w, str) or w not in art:
        passend = sorted(a for a, d in art.items() if d.get("kategorie") in erlaubt)
        aehnlich = difflib.get_close_matches(str(w), passend, n=3, cutoff=0.5)
        vorschlag = ", ".join(aehnlich or passend[:8]) + ("" if aehnlich or len(passend) <= 8 else " …")
        return [f"{ort}: {was}: Artikel „{w}“ gibt es nicht im Gerätestamm – passend wären: {vorschlag}"]
    if art[w].get("kategorie") not in erlaubt:
        return [f"{ort}: {was}: Artikel „{w}“ ist ein(e) {art[w].get('kategorie')}, erwartet {' oder '.join(erlaubt)}"]
    return []


def _pruefe_zusammenhang(daten: dict, art: dict, typicals: dict) -> list[str]:
    luecken = []
    braucht_leitungen = not _leer(daten.get("motoren"))
    for i, fg in enumerate(daten.get("feldgeraete") or [] if isinstance(daten.get("feldgeraete"), list) else []):
        if not isinstance(fg, dict) or not isinstance(fg.get("artikel"), str) or fg["artikel"] not in art:
            continue
        a = art[fg["artikel"]]
        tname = fg.get("typical") if isinstance(fg.get("typical"), str) else None
        if not tname and a.get("kategorie") in FELD_KATEGORIEN and not a.get("signal"):
            luecken.append(f"{_ort('feldgeraete', i, fg)}: Artikel {fg['artikel']} hat kein Signal – Baustein (typical) angeben")
        tp = typicals.get(tname) if tname else None
        if tp and tp.get("leistung"):
            braucht_leitungen = True
            if _leer(fg.get("laenge_m")):
                luecken.append(f"{_ort('feldgeraete', i, fg)}: Baustein {tname} hat einen Leistungsteil – "
                         f"Leitungslänge in m („laenge_m“) fehlt")
    sps = daten.get("sps")
    if isinstance(sps, dict):
        luecken.extend(_pruefe_sps(sps, art))
    v24 = daten.get("versorgung_24V")
    if isinstance(v24, dict) and v24.get("verteilung", "einzelsicherungen") not in ("einzelsicherungen", "selektivmodul"):
        luecken.append(f"24-V-Versorgung: verteilung = „{v24['verteilung']}“ – erlaubt: einzelsicherungen, selektivmodul")
    if isinstance(v24, dict) and v24.get("verteilung") == "selektivmodul" and _leer(v24.get("selektivmodul")):
        luecken.append("24-V-Versorgung: verteilung = selektivmodul, aber kein Artikel bei „selektivmodul“")
    ltg = daten.get("leitungen")
    if isinstance(ltg, dict) and isinstance(ltg.get("i_z_A"), dict):
        for q, iz in ltg["i_z_A"].items():
            if not (_zahl(q) or 0) > 0 or not (_zahl(iz) or 0) > 0:
                luecken.append(f"Leitungsauslegung: Strombelastbarkeit „{q}: {iz}“ ungültig – Querschnitt mm²: Strom A, "
                         f"z. B. 1.5: 13.1")
    if braucht_leitungen and not (isinstance(ltg, dict) and ltg.get("i_z_A")):
        luecken.append("Leitungsauslegung: Motoren/Pumpen vorhanden, aber keine Strombelastbarkeitstabelle („i_z_A“)")
    return luecken


def _pruefe_sps(sps: dict, art: dict) -> list[str]:
    luecken = []
    mk, ad = sps.get("module_kandidaten"), sps.get("adressschema")
    for k, tab in (("module_kandidaten", mk), ("adressschema", ad)):
        if isinstance(tab, dict):
            fehlt = [s for s in SIGNALARTEN if s not in tab]
            if fehlt:
                luecken.append(f"SPS: „{k}“ ohne Eintrag für {', '.join(fehlt)}")
    if isinstance(mk, dict):
        for s, a in mk.items():
            kat = f"sps_{str(s).lower()}"
            if not isinstance(a, str) or a not in art:
                luecken.append(f"SPS: E/A-Karte {s} „{a}“ gibt es nicht im Gerätestamm")
            elif art[a].get("kategorie") != kat or not art[a].get("kanaele"):
                luecken.append(f"SPS: E/A-Karte {s} „{a}“ ist ein(e) {art[a].get('kategorie')}, erwartet {kat} mit Kanalzahl")
    if isinstance(ad, dict):
        for s, muster in ad.items():
            try:
                ok = isinstance(muster, str) and bool(muster.format(**ADRESS_PLATZHALTER))
            except (KeyError, ValueError, IndexError, AttributeError):
                ok = False
            if not ok:
                luecken.append(f"SPS: Adressformat {s} „{muster}“ ungültig – erlaubt sind Text und die Platzhalter "
                         f"{{byte}}, {{bit}}, {{wort}}, z. B. %I{{byte}}.{{bit}}")
    return luecken


def _kurz(w: Any) -> str:
    if isinstance(w, bool):
        return "ja" if w else "nein"
    if isinstance(w, dict):
        t = ", ".join(f"{k} {v}" for k, v in w.items())
    elif isinstance(w, list):
        t = ", ".join(map(str, w))
    else:
        t = str(w)
    return t if len(t) <= 60 else t[:57] + "…"


def mit_hausvorgaben(daten: dict, vorgaben: dict) -> tuple[dict, list[str]]:
    """Fehlende H-Abschnitte bzw. -Felder aus den Hausvorgaben ergänzen.

    -> (Modell, Klartext je ergänztem Abschnitt, z. B. „Einspeisung (Hausvorgabe): Hauptschalter … = HS-3P-40“)
    """
    neu, ergaenzt = copy.deepcopy(daten), []
    for name, (artk, _, felder, _, klar) in ABSCHNITTE.items():
        quelle = vorgaben.get(name)
        if not (artk == "H" or name == "einspeisung") or not isinstance(quelle, dict):  # ANNAHME A19
            continue
        if neu.get(name) is None:
            neu[name] = {}
        ziel = neu[name]
        if not isinstance(ziel, dict):
            continue
        teile = []
        if name == "leitungen" and not _leer(ziel.get("min_querschnitt_mm2")) and not _leer(quelle.get("min_querschnitt_mm2")):
            # Mindestwert aus Hausregel und Hausvorgabe: der strengere gilt
            ziel["min_querschnitt_mm2"] = max(_zahl(ziel["min_querschnitt_mm2"]) or 0, _zahl(quelle["min_querschnitt_mm2"]) or 0)
        for f in felder:
            if f.name in quelle and _leer(ziel.get(f.name)):
                ziel[f.name] = copy.deepcopy(quelle[f.name])
                if f.typ.startswith(("artikel", "liste_artikel")):      # nur das Wesentliche nennen
                    teile.append(_kurz(quelle[f.name]))
                elif f.name == "i_z_A":
                    frei = "freigegeben" if _ja_nein(ziel.get("freigegeben", quelle.get("freigegeben"))) \
                        else "noch nicht von Elektrofachkraft freigegeben"
                    teile.append(f"Strombelastbarkeitstabelle ({frei})")
        if any(_leer((daten.get(name) or {}).get(f.name)) and f.name in quelle for f in felder) and isinstance(
                daten.get(name) or {}, dict):
            ergaenzt.append(f"{klar} nach Hausvorgabe" + (f": {', '.join(teile)}" if teile else ""))
    return neu, ergaenzt


def bereit_machen(daten: Any, stamm: dict, vorgaben: dict | None = None) -> tuple[dict, list[str]]:
    """Hausvorgaben ergänzen, prüfen, Werte vereinheitlichen. Wirft RegelFehler mit ALLEN Lücken.

    -> (Projektmodell für `regeln.plane`, Klartext-Liste der aus den Hausvorgaben ergänzten Werte)
    """
    ergaenzt: list[str] = []
    if isinstance(daten, dict) and vorgaben:
        daten, ergaenzt = mit_hausvorgaben(daten, vorgaben)
    luecken = pruefe(daten, stamm)
    if isinstance(daten, dict):
        for name in ("versorgung_24V", "sps"):
            if _leer(daten.get(name)):
                luecken.append(f"Abschnitt „{name}“ ({ABSCHNITTE[name][3]}) fehlt und es gibt keine Hausvorgabe dafür")
        if isinstance(daten.get("einspeisung"), dict) and _leer(daten["einspeisung"].get("hauptschalter")):
            luecken.append("Einspeisung: Hauptschalter („hauptschalter“) fehlt und es gibt keine Hausvorgabe dafür")
    if luecken:
        n = len(luecken)
        raise RegelFehler(f"Projektmodell: {n} Punkt{'' if n == 1 else 'e'} zu korrigieren:\n"
                          + "\n".join(f"  • {x}" for x in luecken))
    for name, (_, liste, felder, _, _) in ABSCHNITTE.items():
        if daten.get(name) is None:
            daten[name] = [] if liste else {}
        for e in daten[name] if liste else [daten[name]]:
            for f in felder:
                if e.get(f.name) is None:
                    continue
                if f.typ == "zahl":
                    e[f.name] = _zahl(e[f.name])
                elif f.typ == "ja_nein":
                    e[f.name] = _ja_nein(e[f.name])
                elif f.typ == "bmk":
                    e[f.name] = str(e[f.name]).strip().upper()
            e.pop("_zeile", None)
    ltg = daten["leitungen"]
    if isinstance(ltg.get("i_z_A"), dict):
        ltg["i_z_A"] = {_zahl(q): _zahl(iz) for q, iz in ltg["i_z_A"].items()}
    if not daten.get("leitungen"):
        del daten["leitungen"]
    return daten, ergaenzt


def schema_markdown() -> str:
    z = [f"# Schema Projektmodell (`{SCHEMA}`)", "",
         "Erzeugt aus `slpgen/projektmodell.py` (`python -m slpgen schema`) – nicht von Hand ändern.", "",
         "## Kurz für Anwender", "",
         ("Das Projektmodell beschreibt, **was** gebaut wird: Projektdaten, Einspeisung, Feldgeräte und Motoren. "
         "Es entsteht aus der Excel-Vorlage oder aus der Antwort einer KI (Anleitung `docs/KI_AUFBEREITUNG.md`). "
         "Die Software prüft die Datei und meldet jede Lücke im Klartext."), "",
         "- **P** = Angaben aus dem Lastenheft (muss die KI liefern).",
         ("- **H** = Hausvorgabe: fehlt der Abschnitt, ergänzt die Software ihn aus `beispiele/hausvorgaben.yaml` "
         "und nennt das im Auslegungsnachweis."),
         ("- Zahlen mit Punkt oder Komma, ohne Einheit (`0.75` oder `0,75`). Texte mit `=`, `+`, `:` oder führender "
         "Null in Anführungszeichen (`\"=FB1\"`, `\"00\"`)."),
         ("- Artikel und Bausteine nur aus dem Gerätestamm (`beispiele/geraetestamm.yaml`); "
         "der KI-Auftrag enthält die Liste."), "",
         "Kleinstes gültiges Beispiel (Rest aus Hausvorgaben):", "",
         "```yaml", f"schema: {SCHEMA}", "projekt: {nummer: P-2026-001, bezeichnung: Förderband}",
         "einspeisung: {netz: \"3/N/PE AC 400/230 V 50 Hz\"}", "feldgeraete:",
         "  - {bmk: B1, artikel: IND-M12-PNP, funktion: \"Endlage vorne\", gruppe: Sensorik}", "```", "",
         f"Pflichtabschnitte: {', '.join(PFLICHT_ABSCHNITTE)}.", "",
         "| Zusatzfeld | Bedeutung |", "|---|---|", *[f"| `{k}` | {v} |" for k, v in ZUSATZ.items()], "",
         "## Felder"]
    for name, (artk, liste, felder, text, _) in ABSCHNITTE.items():
        z += ["", f"### `{name}` ({artk}{', Liste' if liste else ''}) – {text}", "",
              "| Feld | Art | Pflicht | Bedeutung | Beispiel |", "|---|---|---|---|---|"]
        for f in felder:
            ber = f" ({f.bereich[0]:g}…{f.bereich[1]:g})" if f.bereich else ""
            typ = TYP_KLARTEXT[f.typ.partition(":")[0]]
            if f.typ.startswith("wahl:"):
                typ += ": " + " / ".join(f.typ.partition(":")[2].split("|"))
            z.append(f"| `{f.name}` | {typ}{ber} | {'ja' if f.pflicht else '–'} | {f.text} | `{f.beispiel}` |")
    return "\n".join(z) + "\n"
