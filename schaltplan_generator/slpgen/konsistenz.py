"""Konsistenzprüfungen am Planmodell (Schicht B) -> Prüfbericht.

Jede Prüfung liefert Befunde der Art FEHLER (Plan widersprüchlich, darf so nicht in die Fertigung) oder
HINWEIS (auffällig, bitte ansehen). Der Prüfbericht steht im Auslegungsnachweis und ist über
`python -m slpgen pruefbericht <planmodell.json>` abrufbar.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from .modell import SAMMELMELDUNG, Planmodell, eltern_bmk

FEHLER, HINWEIS = "FEHLER", "HINWEIS"


@dataclass(frozen=True)
class Befund:
    art: str          # FEHLER | HINWEIS
    pruefung: str     # kurzer Name der Prüfung
    text: str


def pruefe_plan(m: Planmodell) -> list[Befund]:
    b: list[Befund] = []
    for f in (_bmk_eindeutig, _verweise, _klemmen, _sps, _absicherungen, _texte):
        b.extend(f(m))
    return b


def _bmk_eindeutig(m: Planmodell) -> list[Befund]:
    doppelt = [k for k, n in Counter(x.bmk for x in m.betriebsmittel).items() if n > 1]
    return [Befund(FEHLER, "Kennzeichen", f"Betriebsmittelkennzeichen {k} ist mehrfach vergeben") for k in doppelt]


def _bekannt(m: Planmodell) -> set[str]:
    return {x.bmk for x in m.betriebsmittel} | {"PE-Schiene", SAMMELMELDUNG}


def _verweise(m: Planmodell) -> list[Befund]:
    """Jeder Verweis (Klemme, Kanal, Abgang, Kabel) zeigt auf ein vorhandenes Betriebsmittel."""
    bekannt = _bekannt(m)
    teile = {x.bmk for x in m.betriebsmittel} | {t for x in m.betriebsmittel for t in x.daten.get("teilsignale", [])}
    b = []
    for k in m.sps_kanaele:
        if k.geraet_bmk not in teile and eltern_bmk(k.geraet_bmk) not in bekannt:
            b.append(Befund(FEHLER, "Verweis", f"SPS-Kanal {k.adresse}: Gerät {k.geraet_bmk} gibt es nicht"))
        if k.anschluss and k.anschluss.rsplit(":", 1)[0] not in bekannt:
            b.append(Befund(FEHLER, "Verweis", f"SPS-Kanal {k.adresse}: Anschluss {k.anschluss} gibt es nicht"))
    for a in m.absicherungen:
        for v in a.verbraucher:
            if v not in bekannt:
                b.append(Befund(FEHLER, "Verweis", f"Abgang {a.bmk}: Verbraucher {v} gibt es nicht"))
    for c in m.kabel:
        for ende in (c.von, c.nach):
            if ende.split(":")[0] not in bekannt and not ende.startswith("-X"):
                b.append(Befund(FEHLER, "Verweis", f"Kabel {c.bmk}: Ende {ende} gibt es nicht"))
    for k in m.klemmen:
        geraet = k.ziel_aussen.split(":")[0]
        if geraet not in bekannt:
            b.append(Befund(FEHLER, "Verweis", f"Klemme {k.leiste}:{k.nr}: Feldgerät {geraet} gibt es nicht"))
    return b


def _klemmen(m: Planmodell) -> list[Befund]:
    """Klemmennummern je Leiste eindeutig und lückenlos ab 1."""
    b = []
    je_leiste: dict[str, list[int]] = {}
    for k in m.klemmen:
        je_leiste.setdefault(k.leiste, []).append(k.nr)
    for leiste, nrn in je_leiste.items():
        doppelt = sorted(n for n, c in Counter(nrn).items() if c > 1)
        if doppelt:
            b.append(Befund(FEHLER, "Klemmen", f"Leiste {leiste}: Klemme {', '.join(map(str, doppelt))} doppelt belegt"))
        luecken = sorted(set(range(1, max(nrn) + 1)) - set(nrn))
        if luecken:
            b.append(Befund(HINWEIS, "Klemmen", f"Leiste {leiste}: Lücke bei Klemme {', '.join(map(str, luecken[:10]))}"))
    return b


def _sps(m: Planmodell) -> list[Befund]:
    """Adressen und Kanäle eindeutig, Bytebereiche der Karten überschneidungsfrei, Kanal innerhalb der Karte."""
    b = []
    for adr, n in Counter(k.adresse for k in m.sps_kanaele).items():
        if n > 1:
            b.append(Befund(FEHLER, "SPS", f"Adresse {adr} ist {n}-mal vergeben"))
    for (mod, kanal), n in Counter((k.modul_bmk, k.kanal) for k in m.sps_kanaele).items():
        if n > 1:
            b.append(Befund(FEHLER, "SPS", f"Karte {mod} Kanal {kanal} ist {n}-mal belegt"))
    karten = {x.bmk: x for x in m.betriebsmittel if x.kategorie in ("sps_di", "sps_do", "sps_ai", "sps_ao")}
    for k in m.sps_kanaele:
        mod = karten.get(k.modul_bmk)
        if mod is None:
            b.append(Befund(FEHLER, "SPS", f"Kanal {k.adresse}: Karte {k.modul_bmk} gibt es nicht"))
            continue
        gesamt = int(m.artikel.get(mod.artikel, {}).get("kanaele", 0))
        if gesamt and k.kanal >= gesamt:
            b.append(Befund(FEHLER, "SPS", f"Kanal {k.kanal} auf {k.modul_bmk} – Karte hat nur {gesamt} Kanäle"))
    for bereich in (("sps_di", "sps_ai"), ("sps_do", "sps_ao")):
        belegt: Counter[int] = Counter()
        for x in karten.values():
            if x.kategorie in bereich and x.daten.get("bytebereich"):
                von, bis = x.daten["bytebereich"]
                belegt.update(range(von, bis + 1))
        doppelt = sorted(n for n, c in belegt.items() if c > 1)
        if doppelt:
            b.append(Befund(FEHLER, "SPS", f"Adressbereiche überschneiden sich (Byte {doppelt[0]}…{doppelt[-1]})"))
    return b


def _absicherungen(m: Planmodell) -> list[Befund]:
    """24-V-Abgänge: Gruppenstrom ≤ Sicherung; kein Verbraucher ohne 24-V-Strom und ohne Kontaktspeisung."""
    b = []
    bm = {x.bmk: x for x in m.betriebsmittel}

    def ohne_grund(v: str) -> bool:
        """0 A ist nur erklärt bei Kontaktspeisung (Hilfskontakt Motorschutz, Meldekontakte eines Bausteins)."""
        x = bm.get(v)
        return (x is not None and float(x.daten.get("i_A", 0) or 0) == 0 and x.kategorie not in ("motorschutz", "meldung")
                and not x.daten.get("versorgt"))

    for a in m.absicherungen:
        if a.i_gruppe_A > a.i_nenn_A:
            b.append(Befund(FEHLER, "Absicherung", f"Abgang {a.bmk}: Gruppenstrom {a.i_gruppe_A} A > Sicherung {a.i_nenn_A} A"))
        ohne = [v for v in a.verbraucher if ohne_grund(v)]
        if ohne:
            b.append(Befund(HINWEIS, "Absicherung", f"Abgang {a.bmk}: {', '.join(ohne)} ohne 24-V-Strom in der Verbraucherliste "
                                                    f"(fremdversorgt oder 230 V?)"))
    return b


def _texte(m: Planmodell) -> list[Befund]:
    """Funktionstexte ohne Wortdopplung („Durchfluss Durchfluss“)."""
    b = []
    for k in m.sps_kanaele:
        mt = re.search(r"\b(\w{3,})\s+\1\b", k.funktion, re.I)
        if mt:
            b.append(Befund(HINWEIS, "Text", f"Kanal {k.adresse}: Wort doppelt im Funktionstext „{k.funktion}“"))
    return b


def bericht_text(befunde: list[Befund]) -> list[str]:
    if not befunde:
        return ["Prüfbericht: keine Befunde"]
    n_f = sum(1 for x in befunde if x.art == FEHLER)
    kopf = f"Prüfbericht: {n_f} Fehler, {len(befunde) - n_f} Hinweise"
    return [kopf] + [f"{x.art} ({x.pruefung}): {x.text}" for x in sorted(befunde, key=lambda x: x.art != FEHLER)]


# Zeitansatz für die Kennzahl „Zeichenaufwand“ – ANNAHME A36: Erfahrungswerte fehlen; Werte sind Platzhalter,
# bis Stundensätze aus dem Hausprofil bzw. aus der Abnahme M8 vorliegen.
MINUTEN_JE = {"Seite": 20.0, "Betriebsmittel": 3.0, "Klemme": 1.0, "SPS-Kanal": 2.0, "Kabel": 2.0}


def kennzahlen(m: Planmodell, seiten_hausstil: int | None = None) -> dict[str, float]:
    mengen = {"Seite": float(seiten_hausstil if seiten_hausstil is not None else len(m.seiten)),
              "Betriebsmittel": float(len([b for b in m.betriebsmittel if b.kategorie not in ("teilsignal",)])),
              "Klemme": float(len(m.klemmen)), "SPS-Kanal": float(len(m.sps_kanaele)), "Kabel": float(len(m.kabel))}
    mengen["Stunden (Zeichenaufwand, Annahme A36)"] = round(sum(mengen[k] * MINUTEN_JE[k] for k in MINUTEN_JE) / 60, 1)
    return mengen
