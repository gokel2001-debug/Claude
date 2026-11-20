"""Neutrales Planmodell.

Das Modell ist bewusst unabhängig vom Ausgabeweg: Variante B rendert es direkt
als PDF, Variante A überträgt dasselbe Modell (als JSON) per EPLAN-API in ein
EPLAN-Projekt.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

SCHEMA_PLANMODELL = "planmodell/1"


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
    def aus_dict(cls, d: dict[str, Any]) -> Planmodell:
        """Gegenstück zu `als_dict` (z. B. aus planmodell.json); prüft die Schemaversion."""
        if d.get("schema") != SCHEMA_PLANMODELL:
            raise RegelFehler(f"Planmodell hat Schema „{d.get('schema')}“, erwartet „{SCHEMA_PLANMODELL}“ – "
                              f"Plan mit dieser Programmversion neu erzeugen")
        unbekannt = set(d) - {f.name for f in fields(cls)} - {"schema"}
        if unbekannt:
            raise RegelFehler(f"Planmodell enthält unbekannte Felder: {', '.join(sorted(unbekannt))}")
        typen = {"betriebsmittel": Betriebsmittel, "klemmen": Klemme, "sps_kanaele": SpsKanal,
                 "absicherungen": Absicherung, "kabel": Kabel}
        werte: dict[str, Any] = {k: v for k, v in d.items() if k != "schema"}
        for k, typ in typen.items():
            werte[k] = [typ(**x) for x in d.get(k, [])]
        werte["seiten"] = [tuple(x) for x in d.get("seiten", [])]
        return cls(**werte)

    def speichere(self, pfad: str | Path) -> None:
        Path(pfad).write_text(json.dumps(self.als_dict(), indent=1, ensure_ascii=False, default=str), encoding="utf-8")

    @classmethod
    def lade(cls, pfad: str | Path) -> Planmodell:
        try:
            d = json.loads(Path(pfad).read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise RegelFehler(f"{Path(pfad).name} ist kein gültiges Planmodell (JSON beschädigt)") from None
        try:
            return cls.aus_dict(d)
        except TypeError as e:
            raise RegelFehler(f"{Path(pfad).name}: Planmodell unvollständig oder beschädigt ({e})") from None
