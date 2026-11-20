"""Projektmodell (Schicht A → B): Schema v1, Prüfung mit Lücken im Klartext, Ergänzung um Hausvorgaben.

Das Projektmodell ist die Eingabe des Planungskerns (`regeln.plane`). Es entsteht aus der
Excel-Vorlage, von Hand oder durch eine KI (siehe docs/KI_AUFBEREITUNG.md). Das Schema ist hier
als Daten hinterlegt; `docs/SCHEMA_PROJEKTMODELL.md` wird daraus erzeugt (`schema_markdown`).

Zwei Arten von Abschnitten:
  P = Projektangaben (kommen aus dem Lastenheft, Pflicht für die KI)
  H = Hausvorgaben (fehlen sie, werden sie aus `hausvorgaben.yaml` ergänzt)
"""
from __future__ import annotations

import copy
import difflib
import datetime as dt
import re
from dataclasses import dataclass
from typing import Any

SCHEMA = "projektmodell/1"
RE_BMK = re.compile(r"-?[A-Z]{1,3}\d{1,4}")


@dataclass(frozen=True)
class Feld:
    name: str
    typ: str                  # text | zahl | ja_nein | datum | bmk | artikel:<kategorie> | liste_artikel:<kategorie> | tabelle
    pflicht: bool
    text: str
    beispiel: str = ""
    bereich: tuple[float, float] | None = None


# Abschnitt -> (Art P/H, Liste?, Felder, Beschreibung)
ABSCHNITTE: dict[str, tuple[str, bool, list[Feld], str]] = {
    "projekt": ("P", False, [
        Feld("nummer", "text", True, "Projekt-/Auftragsnummer", "P-2026-001"),
        Feld("bezeichnung", "text", True, "Kurzbezeichnung der Anlage", "Steuerschrank Förderband"),
        Feld("kunde", "text", False, "Kunde (bleibt lokal, nie ins Repository)", "Musterkunde AG"),
        Feld("anlage", "text", False, "Anlagenkennzeichen (Funktionsaspekt IEC 81346), beginnt mit =", "=FB1"),
        Feld("ort", "text", False, "Ortskennzeichen (Schrank), beginnt mit +", "+SS1"),
        Feld("ersteller", "text", False, "Bearbeiter", "N.N."),
        Feld("datum", "datum", False, "Erstelldatum JJJJ-MM-TT", "2026-10-24"),
        Feld("revision", "text", False, "Revisionsstand", "00"),
    ], "Kopfdaten für Deckblatt und Schriftfeld"),
    "einspeisung": ("P", False, [
        Feld("netz", "text", True, "Netzform und Spannung", "3/N/PE AC 400/230 V 50 Hz"),
        Feld("hauptschalter", "artikel:hauptschalter", False, "Hauptschalter (Artikel aus Gerätestamm)", "HS-3P-40"),
    ], "Netzanschluss des Schranks"),
    "feldgeraete": ("P", True, [
        Feld("bmk", "bmk", True, "Betriebsmittelkennzeichen: Kennbuchstabe(n) + Nummer", "B1"),
        Feld("artikel", "artikel:*", True, "Artikel aus dem Gerätestamm", "IND-M12-PNP"),
        Feld("funktion", "text", True, "Funktionstext für Plan und SPS-Liste", "Endlage Band vorne"),
        Feld("gruppe", "text", False, "gemeinsamer 24-V-Abgang (DO-Aktoren: DO-Last)", "Sensorik"),
        Feld("typical", "typical", False, "Baustein aus der Bibliothek (mehrere Signale/Leistungsteil)", "pumpe_ec"),
        Feld("laenge_m", "zahl", False, "Leitungslänge zum Gerät in m (Bausteine mit Leistungsteil)", "15",
             (0.1, 1000)),
    ], "Sensoren, Aktoren und Bausteine im Feld"),
    "motoren": ("P", True, [
        Feld("bmk", "bmk", True, "Betriebsmittelkennzeichen", "M1"),
        Feld("funktion", "text", False, "Funktionstext", "Bandantrieb"),
        Feld("p_kW", "zahl", True, "Bemessungsleistung in kW (Typenschild)", "0.75", (0.01, 500)),
        Feld("i_N_A", "zahl", True, "Bemessungsstrom in A (Typenschild)", "1.9", (0.01, 1000)),
        Feld("cos_phi", "zahl", False, "Leistungsfaktor (Typenschild), Standard 0,8", "0.78", (0.1, 1.0)),
        Feld("laenge_m", "zahl", True, "Leitungslänge Schrank–Motor in m", "12", (0.1, 1000)),
    ], "Drehstrommotoren mit Direktstart"),
    "versorgung_24V": ("H", False, [
        Feld("netzteile", "liste_artikel:netzteil", True, "Netzteil-Kandidaten, das kleinste passende wird gewählt",
             "[NT-24-05, NT-24-10]"),
        Feld("gleichzeitigkeit", "zahl", False, "Gleichzeitigkeitsfaktor g", "1.0", (0.1, 1.0)),
        Feld("reserve", "zahl", False, "Reserve auf den Bedarf", "0.25", (0.0, 2.0)),
        Feld("absicherungsfaktor", "zahl", False, "I_Sicherung ≥ Faktor · I_Gruppe", "1.25", (1.0, 3.0)),
        Feld("verteilung", "text", False, "einzelsicherungen oder selektivmodul", "einzelsicherungen"),
        Feld("selektivmodul", "artikel:selektivmodul", False, "Selektivmodul bei verteilung = selektivmodul",
             "SEL-24-4K"),
    ], "24-V-Versorgung (Hausregeln)"),
    "sps": ("H", False, [
        Feld("cpu", "artikel:sps_cpu", True, "SPS-CPU", "SPS-CPU"),
        Feld("module_kandidaten", "tabelle", True, "E/A-Karte je Signalart DI/DO/AI/AO", "{DI: SPS-DI16, ...}"),
        Feld("adressschema", "tabelle", True, "Adressformat je Signalart", "{DI: \"%I{byte}.{bit}\", ...}"),
    ], "Steuerung (Hausvorgabe)"),
    "leitungen": ("H", False, [
        Feld("freigegeben", "ja_nein", False, "Tabelle von Elektrofachkraft freigegeben", "false"),
        Feld("verlegeart", "text", False, "Verlegeart (Dokumentation)", "B2"),
        Feld("i_z_A", "tabelle", False, "Strombelastbarkeit I_z in A je Querschnitt mm²", "{1.5: 13.1}"),
        Feld("reduktionsfaktor", "zahl", False, "Reduktionsfaktor Häufung/Umgebung", "0.8", (0.1, 1.0)),
        Feld("kappa", "zahl", False, "Leitfähigkeit in m/(Ω·mm²)", "56", (30, 60)),
        Feld("du_max_prozent", "zahl", False, "zulässiger Spannungsfall in %", "3.0", (0.5, 10)),
    ], "Leitungsauslegung (Hausregeln, Freigabe durch Elektrofachkraft)"),
}
PFLICHT_ABSCHNITTE = ("projekt", "einspeisung", "feldgeraete")
ZUSATZ = {"schema": "Schemaversion, immer „projektmodell/1“",
          "annahmen": "Liste: was die KI angenommen hat (wird im Prüfbericht gezeigt)",
          "offene_fragen": "Liste: was im Lastenheft fehlt oder unklar ist"}
SIGNALARTEN = ("DI", "DO", "AI", "AO")


def _zahl(w: Any) -> float | None:
    if isinstance(w, bool):
        return None
    if isinstance(w, (int, float)):
        return float(w)
    try:
        return float(str(w).strip().replace(",", "."))
    except ValueError:
        return None


def _ort(abschnitt: str, i: int | None, eintrag: dict | None) -> str:
    if i is None:
        return f"Abschnitt „{abschnitt}“"
    bmk = f" ({eintrag.get('bmk')})" if isinstance(eintrag, dict) and eintrag.get("bmk") else ""
    return f"{abschnitt} Nr. {i + 1}{bmk}"


def pruefe(daten: Any, stamm: dict) -> list[str]:
    """Alle Lücken und Fehler des Projektmodells als Klartext (leere Liste = gültig)."""
    if not isinstance(daten, dict):
        return ["Die Datei enthält kein Projektmodell (oberste Ebene muss aus Abschnitten wie „projekt:“ bestehen)"]
    art = stamm.get("artikel", {})
    typicals = stamm.get("typicals", {})
    l: list[str] = []
    if "schema" in daten and daten["schema"] != SCHEMA:
        l.append(f"schema: „{daten['schema']}“ wird nicht unterstützt – erwartet „{SCHEMA}“")
    for k in daten:
        if k not in ABSCHNITTE and k not in ZUSATZ:
            l.append(f"Unbekannter Abschnitt „{k}“ – erlaubt: {', '.join([*ABSCHNITTE, *ZUSATZ])} (Tippfehler?)")
    for k in ("annahmen", "offene_fragen"):
        if k in daten and not (isinstance(daten[k], list) and all(isinstance(x, str) for x in daten[k])):
            l.append(f"„{k}“ muss eine Liste von Sätzen sein (je Zeile „- …“)")
    for name in PFLICHT_ABSCHNITTE:
        if name not in daten or daten[name] in (None, [], {}):
            l.append(f"Abschnitt „{name}“ fehlt oder ist leer – {ABSCHNITTE[name][3]}")
    gesehen: dict[str, str] = {}
    for name, (_, liste, felder, _) in ABSCHNITTE.items():
        if name not in daten or daten[name] is None:
            continue
        wert = daten[name]
        if liste and not isinstance(wert, list):
            l.append(f"Abschnitt „{name}“ muss eine Liste sein (je Eintrag eine Zeile mit „- “)")
            continue
        if not liste and not isinstance(wert, dict):
            l.append(f"Abschnitt „{name}“ muss Einträge der Form „feld: wert“ enthalten")
            continue
        for i, e in (enumerate(wert) if liste else [(None, wert)]):
            ort = _ort(name, i, e)
            if not isinstance(e, dict):
                l.append(f"{ort}: Eintrag muss die Form „feld: wert“ haben")
                continue
            namen = {f.name for f in felder}
            for k in e:
                if k not in namen:
                    l.append(f"{ort}: unbekanntes Feld „{k}“ – erlaubt: {', '.join(sorted(namen))}")
            for f in felder:
                l.extend(_pruefe_feld(ort, f, e.get(f.name), art, typicals))
            if name in ("feldgeraete", "motoren") and isinstance(e.get("bmk"), str):
                kurz = e["bmk"].strip().lstrip("-").upper()
                if kurz in gesehen:
                    l.append(f"{ort}: Betriebsmittelkennzeichen {kurz} ist schon bei {gesehen[kurz]} vergeben")
                gesehen.setdefault(kurz, ort)
    l.extend(_pruefe_zusammenhang(daten, art, typicals))
    return l


def _pruefe_feld(ort: str, f: Feld, w: Any, art: dict, typicals: dict) -> list[str]:
    if w is None or (isinstance(w, str) and not w.strip()):
        return [f"{ort}: Pflichtangabe „{f.name}“ fehlt – {f.text}, z. B. {f.beispiel}"] if f.pflicht else []
    typ, _, kat = f.typ.partition(":")
    if typ == "zahl":
        z = _zahl(w)
        if z is None:
            return [f"{ort}: „{f.name}“ = „{w}“ ist keine Zahl – {f.text}, z. B. {f.beispiel}"]
        if f.bereich and not f.bereich[0] <= z <= f.bereich[1]:
            return [f"{ort}: „{f.name}“ = {w} liegt außerhalb {f.bereich[0]:g}…{f.bereich[1]:g} – bitte prüfen"]
    elif typ == "ja_nein" and not isinstance(w, bool):
        return [f"{ort}: „{f.name}“ muss true oder false sein"]
    elif typ == "datum" and not isinstance(w, dt.date):
        try:
            dt.date.fromisoformat(str(w))
        except ValueError:
            return [f"{ort}: „{f.name}“ = „{w}“ ist kein Datum JJJJ-MM-TT"]
    elif typ == "bmk" and not (isinstance(w, str) and RE_BMK.fullmatch(w.strip().upper())):
        return [f"{ort}: Betriebsmittelkennzeichen „{w}“ ungültig – Kennbuchstabe(n) + Nummer, z. B. B7 oder KF12"]
    elif typ == "artikel":
        return _pruefe_artikel(ort, f.name, w, kat, art)
    elif typ == "liste_artikel":
        if not isinstance(w, list) or not w:
            return [f"{ort}: „{f.name}“ muss eine Liste von Artikeln sein, z. B. {f.beispiel}"]
        return [x for a in w for x in _pruefe_artikel(ort, f.name, a, kat, art)]
    elif typ == "typical" and w not in typicals:
        return [f"{ort}: Baustein „{w}“ gibt es nicht – vorhanden: {', '.join(sorted(typicals)) or 'keine'}"]
    elif typ == "tabelle" and not isinstance(w, dict):
        return [f"{ort}: „{f.name}“ muss eine Tabelle sein, z. B. {f.beispiel}"]
    elif typ == "text" and not isinstance(w, (str, int, float)):
        return [f"{ort}: „{f.name}“ muss ein Text sein"]
    return []


def _pruefe_artikel(ort: str, feld: str, w: Any, kat: str, art: dict) -> list[str]:
    if not isinstance(w, str) or w not in art:
        feld_kat = ("sensor", "aktor")
        passend = sorted(a for a, d in art.items() if d.get("kategorie") in (feld_kat if kat == "*" else (kat,)))
        aehnlich = difflib.get_close_matches(str(w), passend, n=3, cutoff=0.5)
        vorschlag = ", ".join(aehnlich or passend[:8]) + ("" if aehnlich or len(passend) <= 8 else " …")
        return [f"{ort}: Artikel „{w}“ ({feld}) gibt es nicht im Gerätestamm – passend wären: {vorschlag}"]
    if kat != "*" and art[w].get("kategorie") != kat:
        return [f"{ort}: Artikel „{w}“ ist ein(e) {art[w].get('kategorie')}, erwartet {kat}"]
    return []


def _pruefe_zusammenhang(daten: dict, art: dict, typicals: dict) -> list[str]:
    l = []
    for i, fg in enumerate(daten.get("feldgeraete") or []):
        if not isinstance(fg, dict) or fg.get("artikel") not in art:
            continue
        a = art[fg["artikel"]]
        if not fg.get("typical") and a.get("kategorie") in ("sensor", "aktor") and not a.get("signal"):
            l.append(f"{_ort('feldgeraete', i, fg)}: Artikel {fg['artikel']} hat kein Signal – Baustein (typical) angeben")
        tp = typicals.get(fg.get("typical"))
        if tp and tp.get("leistung") and fg.get("laenge_m") is None:
            l.append(f"{_ort('feldgeraete', i, fg)}: Baustein {fg['typical']} hat einen Leistungsteil – "
                     f"„laenge_m“ (Leitungslänge) fehlt")
    sps = daten.get("sps")
    if isinstance(sps, dict):
        for k in ("module_kandidaten", "adressschema"):
            if isinstance(sps.get(k), dict):
                fehlt = [s for s in SIGNALARTEN if s not in sps[k]]
                if fehlt:
                    l.append(f"Abschnitt „sps“: „{k}“ ohne Eintrag für {', '.join(fehlt)}")
    v24 = daten.get("versorgung_24V")
    if isinstance(v24, dict) and v24.get("verteilung", "einzelsicherungen") not in ("einzelsicherungen", "selektivmodul"):
        l.append(f"Abschnitt „versorgung_24V“: verteilung = „{v24['verteilung']}“ – erlaubt: einzelsicherungen, selektivmodul")
    if daten.get("motoren") and isinstance(daten.get("leitungen"), dict) and not daten["leitungen"].get("i_z_A"):
        l.append("Abschnitt „leitungen“: Motoren vorhanden, aber keine Strombelastbarkeitstabelle i_z_A")
    return l


def mit_hausvorgaben(daten: dict, vorgaben: dict) -> tuple[dict, list[str]]:
    """Fehlende H-Abschnitte bzw. -Felder aus den Hausvorgaben ergänzen. -> (Modell, Liste der Ergänzungen)."""
    neu, ergaenzt = copy.deepcopy(daten), []
    for name, (artk, liste, felder, _) in ABSCHNITTE.items():
        quelle = vorgaben.get(name)
        if artk == "H" or name == "einspeisung":          # ANNAHME A19: Hauptschalter als Hausvorgabe
            if not isinstance(quelle, dict):
                continue
            ziel = neu.setdefault(name, {})
            if not isinstance(ziel, dict):
                continue
            for f in felder:
                if f.name in quelle and f.name not in ziel:
                    ziel[f.name] = copy.deepcopy(quelle[f.name])
                    ergaenzt.append(f"{name}.{f.name}")
    return neu, ergaenzt


def schema_markdown() -> str:
    z = [f"# Schema Projektmodell (`{SCHEMA}`)", "",
         "Erzeugt aus `slpgen/projektmodell.py` (`python -m slpgen schema`) – nicht von Hand ändern.", "",
         "Datei: `projektmodell.yaml` (UTF-8). Abschnittsart **P** = Projektangaben aus dem Lastenheft, "
         "**H** = Hausvorgabe (fehlt sie, wird sie aus `hausvorgaben.yaml` ergänzt).", "",
         f"Pflichtabschnitte: {', '.join(PFLICHT_ABSCHNITTE)}.", "",
         "| Zusatzfeld | Bedeutung |", "|---|---|", *[f"| `{k}` | {v} |" for k, v in ZUSATZ.items()], ""]
    for name, (artk, liste, felder, text) in ABSCHNITTE.items():
        z += [f"## `{name}` ({artk}{', Liste' if liste else ''}) – {text}", "",
              "| Feld | Typ | Pflicht | Bedeutung | Beispiel |", "|---|---|---|---|---|"]
        for f in felder:
            ber = f" ({f.bereich[0]:g}…{f.bereich[1]:g})" if f.bereich else ""
            z.append(f"| `{f.name}` | {f.typ}{ber} | {'ja' if f.pflicht else '–'} | {f.text} | `{f.beispiel}` |")
        z.append("")
    return "\n".join(z)


def bereit_machen(daten: Any, stamm: dict, vorgaben: dict | None = None) -> tuple[dict, list[str]]:
    """Hausvorgaben ergänzen, prüfen, Zahlen vereinheitlichen. Wirft RegelFehler mit ALLEN Lücken.

    -> (Projektmodell für `regeln.plane`, Liste der aus den Hausvorgaben ergänzten Felder)
    """
    from .modell import RegelFehler
    ergaenzt: list[str] = []
    if isinstance(daten, dict) and vorgaben:
        daten, ergaenzt = mit_hausvorgaben(daten, vorgaben)
    luecken = pruefe(daten, stamm)
    if isinstance(daten, dict):
        for name in ("versorgung_24V", "sps"):
            if name not in daten:
                luecken.append(f"Abschnitt „{name}“ fehlt und keine Hausvorgaben gefunden – {ABSCHNITTE[name][3]}")
        if isinstance(daten.get("einspeisung"), dict) and not daten["einspeisung"].get("hauptschalter"):
            luecken.append("Abschnitt „einspeisung“: „hauptschalter“ fehlt und keine Hausvorgabe gefunden")
    if luecken:
        raise RegelFehler(f"Projektmodell unvollständig ({len(luecken)} Punkte):\n"
                          + "\n".join(f"  • {x}" for x in luecken))
    for name, (_, liste, felder, _) in ABSCHNITTE.items():
        for e in (daten.get(name) or []) if liste else [daten.get(name) or {}]:
            for f in felder:
                if f.typ == "zahl" and e.get(f.name) is not None:
                    e[f.name] = _zahl(e[f.name])
                elif f.typ == "bmk" and e.get(f.name) is not None:
                    e[f.name] = str(e[f.name]).strip().upper()
    return daten, ergaenzt
