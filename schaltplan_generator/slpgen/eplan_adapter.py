"""EPLAN-Adapter (Schicht C, Variante A) – STUB.

Liest ausschließlich das Planmodell (planmodell.json) und bereitet die Daten so auf, wie ein späterer
Import in EPLAN sie braucht: je Betriebsmittel ein vollständiges Referenzkennzeichen (=Anlage+Ort-BMK),
Artikelnummer, Funktionstext und Lage im Plan; dazu Klemmen, Kabel und SPS-Kanäle.

Die eigentliche Übertragung fehlt bewusst: ohne API-Lizenz ist kein Importweg bestätigt.
ANNAHME A26: Ein späterer Import über Makros/XML oder eine Beschriftungs-/Importliste ist möglich – ungeprüft
(siehe eplan_skripte/Test_Beschriftung.cs und PC_AUFGABEN).
"""
from __future__ import annotations

from typing import Any

from .modell import Planmodell, RegelFehler, eltern_bmk

PFLICHT_BETRIEBSMITTEL = ("referenzkennzeichen", "artikelnummer", "bezeichnung", "kategorie")
OHNE_ARTIKEL = ("teilsignal", "selektivkanal", "meldung")      # Teile eines anderen Betriebsmittels


def aufbereiten(m: Planmodell) -> dict[str, Any]:
    """Planmodell -> neutrale Importdaten (Listen von Zeilen). Wirft RegelFehler bei Widersprüchen."""
    zeilen, gesehen = [], set()
    for b in m.betriebsmittel:
        rk = m.voll_bmk(b.bmk)
        if rk in gesehen:
            raise RegelFehler(f"EPLAN-Export: Referenzkennzeichen {rk} doppelt")
        gesehen.add(rk)
        art = m.artikel.get(b.artikel, {})
        eltern = b.daten.get("eltern") or (eltern_bmk(b.bmk) if b.kategorie in OHNE_ARTIKEL else "")
        zeilen.append({"referenzkennzeichen": rk, "artikelnummer": art.get("artikelnummer", b.artikel),
                       "hersteller": art.get("hersteller", ""), "bezeichnung": b.bezeichnung,
                       "funktionstext": b.funktion, "kategorie": b.kategorie,
                       "seite": b.seite, "spalte": b.spalte, "teil_von": m.voll_bmk(eltern) if eltern else ""})
    return {
        "projekt": {k: v for k, v in m.projekt.items() if not k.startswith("_")},
        "betriebsmittel": zeilen,
        "klemmen": [{"leiste": m.voll_bmk(k.leiste), "nr": k.nr, "potential": k.potential,
                     "innen": k.ziel_innen, "aussen": k.ziel_aussen} for k in m.klemmen],
        "kabel": [{"referenzkennzeichen": m.voll_bmk(c.bmk), "von": c.von, "nach": c.nach, "adern": c.adern,
                   "querschnitt_mm2": c.querschnitt_mm2, "laenge_m": c.laenge_m} for c in m.kabel],
        "sps": [{"modul": m.voll_bmk(s.modul_bmk), "kanal": s.kanal, "art": s.art, "adresse": s.adresse,
                 "geraet": m.voll_bmk(s.geraet_bmk), "funktion": s.funktion} for s in m.sps_kanaele],
    }


def uebertrage(m: Planmodell, ziel: str) -> None:
    """Übertragung nach EPLAN – noch nicht verfügbar (kein bestätigter Importweg)."""
    aufbereiten(m)                       # Daten sind vorbereitet und geprüft
    raise RegelFehler("EPLAN-Übertragung ist noch nicht verfügbar (Importweg ungeprüft, Annahme A26). "
                      "Bitte das PDF (Hausstil) und die Stückliste verwenden.")
