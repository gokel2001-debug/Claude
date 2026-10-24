"""Neutrales Planmodell.

Das Modell ist bewusst unabhängig vom Ausgabeweg: Variante B rendert es direkt
als PDF, Variante A überträgt dasselbe Modell (als JSON) per EPLAN-API in ein
EPLAN-Projekt.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


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
class Planmodell:
    projekt: dict[str, Any]
    betriebsmittel: list[Betriebsmittel] = field(default_factory=list)
    klemmen: list[Klemme] = field(default_factory=list)
    sps_kanaele: list[SpsKanal] = field(default_factory=list)
    absicherungen: list[Absicherung] = field(default_factory=list)
    bilanz: dict[str, Any] = field(default_factory=dict)
    warnungen: list[str] = field(default_factory=list)

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
        return asdict(self)
