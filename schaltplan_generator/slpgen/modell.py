"""Neutrales Planmodell.

Das Modell ist bewusst unabhängig vom Ausgabeweg: Variante B rendert es direkt
als PDF, Variante A überträgt dasselbe Modell (als JSON) per EPLAN-API in ein
EPLAN-Projekt.
"""
from __future__ import annotations

import json
from dataclasses import MISSING, asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

SCHEMA_PLANMODELL = "planmodell/1"

# Seitenaufbau des bisherigen Plans und feste Kennzeichen – Teil der Schnittstelle B -> C
SEITE_EINSPEISUNG = 3
SEITE_VERTEILUNG = 4
SEITE_SPS = 5
ERSTE_DYN_SEITE = 6            # ab hier Motor-Last-, Motor-Steuer- und Feldgeräteseiten
SPALTEN_JE_SEITE = 8
ZEILEN_JE_SEITE = 36           # Listen (Klemmen, Kabel, Stückliste)
SAMMELMELDUNG = "-F2.S"        # Sammelmeldung der Selektivmodule (gehört zum ersten Modul -F2)
SEITENARTEN = ("deckblatt", "inhalt", "einspeisung", "verteilung", "sps", "motor_last", "motor_steuer", "feld",
               "klemmen", "kabel", "stueckliste", "auslegung")


class RegelFehler(Exception):
    """Eingabe/Stamm erlauben keine regelkonforme Auslegung."""


@dataclass
class Betriebsmittel:
    bmk: str                      # z. B. "-G1" (ohne Anlage/Ort-Präfix)
    artikel: str                  # Schlüssel im Gerätestamm
    bezeichnung: str
    funktion: str = ""
    kategorie: str = ""
    seite: int | None = None      # Seite, auf der das Hauptsymbol steht
    spalte: int | None = None     # Strompfad/Spalte 1..8
    daten: dict[str, Any] = field(default_factory=dict)


@dataclass
class Klemme:
    leiste: str                   # z. B. "-X1"
    nr: int
    potential: str                # "+24V", "0V", "Signal"
    ziel_innen: str               # z. B. "-A2:3 (%I0.2)"
    ziel_aussen: str              # z. B. "-B3:4 (Q)"
    seite: int | None = None
    spalte: int | None = None
    signal: str = ""              # Schlüssel des SPS-Kanals (SpsKanal.geraet_bmk), nur bei Signalklemmen


def eltern_bmk(signal_schluessel: str) -> str:
    """Teilsignal "-B7.2" eines Bausteins -> Gerät "-B7"; einfache Geräte bleiben unverändert."""
    return signal_schluessel.rsplit(".", 1)[0] if "." in signal_schluessel else signal_schluessel


@dataclass
class SpsKanal:
    modul_bmk: str
    kanal: int
    art: str                      # DI, DO, AI
    adresse: str
    geraet_bmk: str
    funktion: str
    anschluss: str = ""           # direkt angeschlossenes Betriebsmittel im Schrank, z. B. "-M1-K1:A1"; leer = Feldklemme


@dataclass
class Absicherung:
    bmk: str
    artikel: str
    i_nenn_A: float
    gruppe: str
    i_gruppe_A: float
    verbraucher: list[str]


@dataclass
class Kabel:
    bmk: str                      # z. B. "-W1"
    artikel: str
    von: str
    nach: str
    adern: int
    querschnitt_mm2: float
    laenge_m: float
    i_b_A: float                  # Betriebsstrom (Einstellstrom Schutzorgan)
    i_z_A: float                  # Strombelastbarkeit inkl. Reduktionsfaktor
    du_prozent: float
    seite: int | None = None
    spalte: int | None = None


@dataclass
class Planmodell:
    projekt: dict[str, Any]
    betriebsmittel: list[Betriebsmittel] = field(default_factory=list)
    klemmen: list[Klemme] = field(default_factory=list)
    sps_kanaele: list[SpsKanal] = field(default_factory=list)
    absicherungen: list[Absicherung] = field(default_factory=list)
    kabel: list[Kabel] = field(default_factory=list)
    seiten: list[tuple[int, str, str, int]] = field(default_factory=list)  # Nr, Titel, Art, Index
    bilanz: dict[str, Any] = field(default_factory=dict)
    warnungen: list[str] = field(default_factory=list)
    artikel: dict[str, dict[str, Any]] = field(default_factory=dict)   # Auszug Gerätestamm: nur verwendete Artikel
    kennzeichen: dict[str, list[str]] = field(default_factory=dict)    # BMK -> [Anlage, lokales BMK] (Hausstil)

    def bm(self, bmk: str) -> Betriebsmittel:
        for b in self.betriebsmittel:
            if b.bmk == bmk:
                return b
        raise KeyError(bmk)

    def voll_bmk(self, bmk: str) -> str:
        """Vollständiges Referenzkennzeichen nach IEC 81346: =Anlage+Ort-BMK."""
        p = self.projekt
        return f"{p.get('anlage', '')}{p.get('ort', '')}{bmk}"

    def als_dict(self) -> dict[str, Any]:
        return {"schema": SCHEMA_PLANMODELL, **asdict(self)}

    @classmethod
    def aus_dict(cls, d: Any) -> Planmodell:
        """Gegenstück zu `als_dict` (z. B. aus planmodell.json); prüft Schemaversion, Aufbau und Typen."""
        if not isinstance(d, dict):
            raise RegelFehler("Planmodell muss ein JSON-Objekt sein")
        if d.get("schema") != SCHEMA_PLANMODELL:
            raise RegelFehler(f"Planmodell hat Schema „{d.get('schema')}“, erwartet „{SCHEMA_PLANMODELL}“ – "
                              f"Plan mit dieser Programmversion neu erzeugen")
        unbekannt = set(d) - {f.name for f in fields(cls)} - {"schema"}
        if unbekannt:
            raise RegelFehler(f"Planmodell enthält unbekannte Felder: {', '.join(sorted(unbekannt))}")
        fehler: list[str] = []
        if not isinstance(d.get("projekt"), dict) or not str(d["projekt"].get("nummer", "")).strip():
            fehler.append("„projekt“ fehlt oder hat keine „nummer“")
        for k in ("bilanz", "artikel", "kennzeichen"):
            if k in d and not isinstance(d[k], dict):
                fehler.append(f"„{k}“ muss ein Objekt sein")
        for name, art in d.get("artikel", {}).items() if isinstance(d.get("artikel"), dict) else []:
            if not isinstance(art, dict) or "kategorie" not in art or "bezeichnung" not in art:
                fehler.append(f"artikel „{name}“: „kategorie“ und „bezeichnung“ sind Pflicht")
        for i, z in enumerate(d.get("seiten", [])):
            if not (isinstance(z, list) and len(z) == 4 and isinstance(z[0], int) and z[2] in SEITENARTEN):
                fehler.append(f"seiten Nr. {i + 1}: erwartet [Nr, Titel, Art, Index] mit Art aus {', '.join(SEITENARTEN)}")
        typen = {"betriebsmittel": Betriebsmittel, "klemmen": Klemme, "sps_kanaele": SpsKanal,
                 "absicherungen": Absicherung, "kabel": Kabel}
        for k, typ in typen.items():
            liste = d.get(k, [])
            if not isinstance(liste, list):
                fehler.append(f"„{k}“ muss eine Liste sein")
                continue
            for i, x in enumerate(liste):
                fehler += [f"{k} Nr. {i + 1}: {t}" for t in _pruefe_eintrag(typ, x)]
        if fehler:
            raise RegelFehler("Planmodell beschädigt oder von Hand verändert – Plan neu erzeugen:\n"
                              + "\n".join(f"  • {x}" for x in fehler[:15]))
        werte: dict[str, Any] = {k: v for k, v in d.items() if k != "schema"}
        for k, typ in typen.items():
            werte[k] = [typ(**x) for x in d.get(k, [])]
        werte["seiten"] = [tuple(x) for x in d.get("seiten", [])]
        return cls(**werte)

    def speichere(self, pfad: str | Path) -> None:
        # ohne default=str: ein Wert, den JSON nicht kennt, fällt hier auf statt still zu Text zu werden
        Path(pfad).write_text(json.dumps(self.als_dict(), indent=1, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def lade(cls, pfad: str | Path) -> Planmodell:
        try:
            d = json.loads(Path(pfad).read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise RegelFehler(f"{Path(pfad).name} ist kein gültiges Planmodell (JSON beschädigt)") from None
        return cls.aus_dict(d)


def _pruefe_eintrag(typ: type, x: Any) -> list[str]:
    """Feldnamen und Grundtypen eines Listeneintrags gegen die Dataclass prüfen (Klartext)."""
    import typing
    if not isinstance(x, dict):
        return ["Eintrag muss ein Objekt sein"]
    hints = typing.get_type_hints(typ)
    namen = {f.name for f in fields(typ)}
    t = [f"unbekanntes Feld „{k}“" for k in x if k not in namen]
    for f in fields(typ):
        if f.name not in x:
            if f.default is MISSING and f.default_factory is MISSING:
                t.append(f"Pflichtfeld „{f.name}“ fehlt")
            continue
        w, h = x[f.name], str(hints[f.name]).replace("<class '", "").replace("'>", "")
        erlaubt: tuple[type, ...] = {"str": (str,), "int": (int,), "float": (int, float), "list": (list,),
                                     "dict": (dict,)}.get(h.split("[")[0].split(" ")[0], (object,))
        if w is None and "None" in h:
            continue
        if isinstance(w, bool) or not isinstance(w, erlaubt):
            t.append(f"„{f.name}“ = {w!r} hat falschen Typ (erwartet {h.replace('typing.', '')})")
    return t


# --------------------------------------------------------------------------- #
# Schema-Dokument (docs/SCHEMA_PLANMODELL.md wird hieraus erzeugt)
# --------------------------------------------------------------------------- #
TEILE = {
    "projekt": ("Objekt", "Kopfdaten aus dem Projektmodell (nummer, bezeichnung, anlage, ort, …; `_netz` = Netzform; "
                "`_klemmen` = Klemmenartikel je Rolle leistung/feld/pe; `_sicherheit` = Platzhalterseite Sicherheit: "
                "not_halt, pl, stoppkategorie, funktionen, freigabe, ausloeser, geraete, antriebe)"),
    "betriebsmittel": ("Liste Betriebsmittel", "alle Geräte, Bausteinteile, Kabel, Klemmleisten mit Lage im Plan"),
    "klemmen": ("Liste Klemme", "Klemmenbelegung innen/außen je Leiste"),
    "sps_kanaele": ("Liste SpsKanal", "SPS-Kanalzuordnung mit Adresse"),
    "absicherungen": ("Liste Absicherung", "24-V-Abgänge mit Gruppenstrom und Verbrauchern"),
    "kabel": ("Liste Kabel", "Leitungsauslegung (Querschnitt, I_z, ΔU)"),
    "seiten": ("Liste [Nr, Titel, Art, Index]", "Seitenfolge des bisherigen Plans"),
    "bilanz": ("Objekt", "24-V-Bilanz und Netzteilauswahl"),
    "warnungen": ("Liste Text", "Auslegungsnachweis: Annahmen, offene Fragen, nicht geprüfte Punkte"),
    "artikel": ("Objekt Artikel → Daten", "Auszug Gerätestamm, nur verwendete Artikel (Ausgabe braucht keinen Stamm)"),
    "kennzeichen": ("Objekt BMK → [Anlage, lokales BMK]", "Kennzeichen im Hausstil, im Planungsablauf vor dem Speichern "
                    "vergeben; PDF Hausstil und EPLAN-Adapter verwenden dieselben (A27)"),
}

# Inhalt der freien Objekte (Auszug der heute verwendeten Schlüssel; Erweiterung nur mit neuer Schemaversion)
DATEN_SCHLUESSEL = {
    "alle mit 24-V-Strom": "i_A (A), gruppe, absicherung (BMK des Abgangs)",
    "sensor/aktor": "signal (DI/DO/AI/AO/BAUSTEIN), sps (Kanal), adresse, anschluss (Pins), klemmen, typical, "
                    "versorgung, versorgt, teilsignale, quellsignale, leistung (Leistungsteil: mss, kabel, aussenleiter …)",
    "teilsignal/bauteil/kabel eines Bausteins": "eltern (BMK des Geräts), lokal (BMK im Baustein), i_r_A, laenge_m",
    "motor": "p_kW, i_N_A, cos_phi, mss, schuetz, kabel (BMK)",
    "motorschutz/schuetz": "i_r_A, signal, sps, adresse, funktion_sps, steuer_seite, steuer_spalte",
    "netzteil": "Artikeldaten des gewählten Netzteils (i_nenn_A, u_ein_V, u_aus_V, wirkungsgrad, vorsicherung_A)",
    "klemme (Leiste)": "anzahl",
    "selektivkanal/meldung": "modul, kanal",
}
ARTIKEL_PFLICHT = "kategorie, bezeichnung (Pflicht); hersteller, artikelnummer und technische Werte je Kategorie"
BILANZ_SCHLUESSEL = ("netzteil, i_nenn_A, i_summe_A, i_bedarf_A, gleichzeitigkeit, reserve, auslastung, gruppen, "
                     "i_motoren_A, i_netzgeraete_A, i_je_aussenleiter_A, i_400V_max_A, i_primaer_max_A")


def schema_planmodell_markdown() -> str:
    import typing
    z = [f"# Schema Planmodell (`{SCHEMA_PLANMODELL}`)", "",
         "Erzeugt aus `slpgen/modell.py` (`python -m slpgen schema --planmodell`) – nicht von Hand ändern.", "",
         "Das Planmodell ist das Ergebnis des Planungskerns (Schicht B) und die **einzige** Eingabe der Ausgabe "
         "(Schicht C: PDF bisher, PDF Hausstil, Stückliste, später EPLAN-Adapter). Datei: `<Projektnummer>_Planmodell.json`.",
         "", "| Feld | Art | Inhalt |", "|---|---|---|", "| `schema` | Text | immer „" + SCHEMA_PLANMODELL + "“ |"]
    z += [f"| `{k}` | {a} | {t} |" for k, (a, t) in TEILE.items()]
    z += ["", "Pflicht: `projekt.nummer` (wird Dateiname: Buchstaben, Ziffern, `. - _`). "
          f"Seitenarten: {', '.join(SEITENARTEN)}.", "", "## Freie Objekte", "",
          "| Objekt | Schlüssel |", "|---|---|", f"| `artikel.<Artikel>` | {ARTIKEL_PFLICHT} |",
          f"| `bilanz` | {BILANZ_SCHLUESSEL} |"]
    z += [f"| `betriebsmittel.daten` ({k}) | {v} |" for k, v in DATEN_SCHLUESSEL.items()]
    z += ["", "Verbindungen und Potentiale sind (noch) kein eigener Teil: sie ergeben sich aus `klemmen` "
          "(innen/außen, Potential) und `absicherungen` (Abgang → Verbraucher). Annahme A28."]
    for typ in (Betriebsmittel, Klemme, SpsKanal, Absicherung, Kabel):
        hints = typing.get_type_hints(typ)
        z += ["", f"## {typ.__name__}", "", "| Feld | Typ | Pflicht |", "|---|---|---|"]
        for f in fields(typ):
            pflicht = "ja" if f.default is MISSING and f.default_factory is MISSING else "–"
            h = hints[f.name]
            name = h.__name__ if isinstance(h, type) else str(h).replace("typing.", "")
            z.append(f"| `{f.name}` | `{name}` | {pflicht} |")
    return "\n".join(z) + "\n"
