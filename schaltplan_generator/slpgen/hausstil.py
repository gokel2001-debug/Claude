"""Ausgabe im Hausstil: eine Anlage je Funktion, Spalten 0–9, Seitenzählung je Anlage,
Querverweise `=Anlage/Seite.Spalte`, SPS-Kasten je Kanal, Aderkennzeichnung an Verbindungen.

Die Auslegung (Bilanz, Absicherung, SPS-Adressen, Motorabgänge) kommt unverändert aus
`regeln.plane()`; dieses Modul ordnet das Planmodell in Anlagen und zeichnet sie.
Hausparameter stehen in HAUSSTIL_STANDARD (neutral) und werden – soweit freigegeben – aus
dem lokalen Hausprofil überschrieben (`lade_hausstil`).
"""
from __future__ import annotations

import copy
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import yaml
from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfgen.canvas import Canvas

from .modell import Planmodell
from .zeichnen import (X0, X1, Y0, Y1, YL, YS, Blatt, potential_pfeil, s_deckblatt, sym_klemme,
                       sym_schliesser, sym_sicherung, tabelle)

HAUSSTIL_STANDARD = {
    "spalten": 10,                                   # Spaltenleiste 0..9
    "feldklemmleiste": "-X10",
    "zeichnungsnummer": "{projekt}-{anlage}-1-{art}-{rev}",
    "vorschrift": "",
    "ader": {"+24V": "DBU", "0V": "DBU/WH", "DI": "DBU", "DO": "DBU", "AI": "WH", "querschnitt": "0,75"},
    "feldkabel_typ": "LIYCY",
    "feldkabel_adern": [2, 3, 4, 7, 12],
    "kartenanlagen": {"CPU": "SA0", "DI": "SA1", "DO": "SA2", "AI": "SA3"},
}
ZEILEN_JE_LISTENSEITE = 36


def lade_hausstil(profil_pfad: str | Path | None) -> dict:
    """Standard + freigegebene Werte aus dem Hausprofil (nur Status `freigegeben` zählt)."""
    stil = copy.deepcopy(HAUSSTIL_STANDARD)
    stil["quelle"] = {}
    if profil_pfad and Path(profil_pfad).exists():
        profil = yaml.safe_load(Path(profil_pfad).read_text(encoding="utf-8")) or {}
        m = profil.get("merkmale", {}).get("feldklemmleiste", {})
        if m.get("status") == "freigegeben" and str(m.get("wert", "")).startswith("-X"):
            stil["feldklemmleiste"], stil["quelle"]["feldklemmleiste"] = m["wert"], "Hausprofil (freigegeben)"
    return stil


# --------------------------------------------------------------------------- #
# Anlagenmodell
# --------------------------------------------------------------------------- #
@dataclass
class Anlage:
    kennung: str                     # ohne "=", z. B. "B01", "DC24.02"
    titel: str
    art: str = "EFS"
    seiten: list[tuple[str, Callable]] = field(default_factory=list)   # (Seitentitel, Zeichner)


@dataclass
class Ort:
    anlage: str
    seite: int
    spalte: int


class Hausplan:
    """Planmodell -> Anlagen; hält Positionen für Querverweise."""

    def __init__(self, m: Planmodell, stamm: dict, stil: dict):
        self.m, self.stamm, self.stil = m, stamm, stil
        self.anlagen: "OrderedDict[str, Anlage]" = OrderedDict()
        self.pos: dict[str, Ort] = {}            # Schlüssel: altes BMK oder "kanal:<geraet>" / "karte:<geraet>"
        self.lokal: dict[str, tuple[str, str]] = {}   # altes BMK -> (Anlage, lokales BMK)
        self._aufbauen()

    # ---- Verweise --------------------------------------------------------------
    def ref(self, ziel: Ort | None, von: str) -> str:
        if ziel is None:
            return ""
        return f"/{ziel.seite}.{ziel.spalte}" if ziel.anlage == von else f"={ziel.anlage}/{ziel.seite}.{ziel.spalte}"

    def voll(self, alt_bmk: str) -> str:
        a, lok = self.lokal.get(alt_bmk, ("", alt_bmk))
        return f"={a}{self.m.projekt.get('ort', '')}{lok}"

    # ---- Aufbau ----------------------------------------------------------------
    def _aufbauen(self):
        m, karten = self.m, self.stil["kartenanlagen"]
        self._neu("DBL", "Deckblatt", "DBL").seiten.append(("Deckblatt", lambda b, a: s_deckblatt(b, m)))
        self._neu("INH", "Inhaltsverzeichnis", "INH").seiten.append(("Inhaltsverzeichnis", self._s_inhalt))

        ein = self._neu("AC230.01", "Einspeisung")
        ein.seiten.append(("Einspeisung", self._s_einspeisung))
        self._lokal("-Q1", "AC230.01", "-Q1", 1, 2)
        self._lokal("-F1", "AC230.01", "-F1", 1, 5)
        self._neu("DC24.01", "24 V DC Erzeugung").seiten.append(("Erzeugung 24 V DC", self._s_erzeugung))
        self._lokal("-G1", "DC24.01", "-T1", 1, 4)
        vert = self._neu("DC24.02", "24 V DC Verteilung")
        vert.seiten.append(("Potentialverteilung 24 V DC", self._s_verteilung))
        for i, a in enumerate(m.absicherungen):
            self._lokal(a.bmk, "DC24.02", f"-F{i + 1}", 1, 1 + 2 * i)

        # je Motor eine Anlage (Last + Steuerung)
        for mot in [b for b in m.betriebsmittel if b.kategorie == "motor"]:
            nr = int(mot.bmk.lstrip("-M"))
            kenn = f"M{nr:02d}"
            an = self._neu(kenn, f"Motor {mot.bmk} {mot.funktion}".strip())
            an.seiten += [("Lastkreis", self._s_motor_last), ("Steuerung", self._s_motor_steuer)]
            self._lokal(mot.bmk, kenn, "-M1", 1, 4)
            self._lokal(f"-Q{nr + 1}", kenn, "-Q1", 1, 4)
            self._lokal(f"-K{nr}", kenn, "-K1", 1, 4)
            self._lokal(f"-W{nr}", kenn, "-W1", 1, 4)
            self.pos[f"kanal:-K{nr}"] = Ort(kenn, 2, 2)
            self.pos[f"kanal:-Q{nr + 1}"] = Ort(kenn, 2, 6)
            self.pos[f"spule:-K{nr}"] = Ort(kenn, 2, 2)

        # je Feldgerät eine Anlage
        for g in [b for b in m.betriebsmittel if b.kategorie in ("sensor", "aktor")]:
            buchst = "".join(c for c in g.bmk if c.isalpha())
            kenn = f"{buchst}{int(''.join(c for c in g.bmk if c.isdigit())):02d}"
            an = self._neu(kenn, f"{g.funktion}".strip() or g.bezeichnung)
            an.seiten.append((g.funktion or g.bezeichnung, self._s_feld))
            self._lokal(g.bmk, kenn, f"-{buchst}1", 1, 4)
            self.pos[f"kanal:{g.bmk}"] = Ort(kenn, 1, 4)

        # SPS-Karten je Signalart als Anlage
        cpu = self._neu(karten["CPU"], "SPS-Steuerung")
        cpu.seiten.append(("SPS-CPU", self._s_cpu))
        self._lokal("-A1", karten["CPU"], "-K1", 1, 1)
        for sig, kenn, titel in (("DI", karten["DI"], "SPS Digitaleingänge"), ("DO", karten["DO"], "SPS Digitalausgänge"),
                                 ("AI", karten["AI"], "SPS Analogeingänge")):
            mods = sorted({k.modul_bmk for k in m.sps_kanaele if k.art == sig})
            if not mods:
                continue
            an = self._neu(kenn, titel)
            for i, mod in enumerate(mods):
                an.seiten.append((f"{titel} Karte {i + 1}", self._s_karte(mod)))
                self._lokal(mod, kenn, f"-K{i + 1}", i + 1, 1)
                for k in [k for k in m.sps_kanaele if k.modul_bmk == mod]:
                    self.pos[f"karte:{k.geraet_bmk}"] = Ort(kenn, i + 1, 2)      # Kanalliste in Spalte 2

        for kenn, titel, art, zeichner, n in (
                ("KAB", "Kabelübersicht", "KAB", self._s_kabel, len(self._kabelzeilen())),
                ("KPL", "Klemmenplan", "KPL", self._s_klemmen, len(self._klemmenzeilen())),
                ("STL", "Artikelstückliste", "STL", self._s_stueckliste, len(self._stl_zeilen())),
                ("AUS", "Auslegungsnachweis", "AUS", self._s_auslegung, 1)):
            an = self._neu(kenn, titel, art)
            for i in range(max(1, -(-n // ZEILEN_JE_LISTENSEITE))):
                an.seiten.append((titel, (lambda z, i=i: lambda b, a: z(b, a, i))(zeichner)))

    def _neu(self, kenn: str, titel: str, art: str = "EFS") -> Anlage:
        self.anlagen[kenn] = Anlage(kenn, titel, art)
        return self.anlagen[kenn]

    def _lokal(self, alt: str, anlage: str, lok: str, seite: int, spalte: int):
        self.lokal[alt] = (anlage, lok)
        self.pos[alt] = Ort(anlage, seite, spalte)

    # ---- Seitenfolge -----------------------------------------------------------
    def seitenfolge(self) -> list[tuple[Anlage, int, str, Callable]]:
        return [(a, i + 1, t, z) for a in self.anlagen.values() for i, (t, z) in enumerate(a.seiten)]

    def zeichnungsnummer(self, a: Anlage) -> str:
        p = self.m.projekt
        return self.stil["zeichnungsnummer"].format(projekt=p.get("nummer", ""), anlage=a.kennung, art=a.art,
                                                    rev=p.get("revision", "00"))

    # ======================================================================== #
    # Zeichnen
    # ======================================================================== #
    def x(self, spalte: int) -> float:
        return X0 + (spalte + 0.5) * (X1 - X0) / self.stil["spalten"]

    def rahmen(self, b: Blatt, a: Anlage, nr: int, titel: str, vorher: str, nachher: str):
        n, p = self.stil["spalten"], self.m.projekt
        colw = (X1 - X0) / n
        b.rechteck(X0, Y0, X1 - X0, Y1 - Y0, 0.5)
        b.linie(X0, YL, X1, YL)
        for k in range(n):
            if k:
                b.linie(X0 + k * colw, YL, X0 + k * colw, Y1)
            b.text(X0 + (k + 0.5) * colw, YL + 2.2, k, 2.5, ausr="m")
        b.linie(X0, YS, X1, YS, 0.5)
        for xs in (60, 110, 170, 250, 330):
            b.linie(X0 + xs, Y0, X0 + xs, YS)
        b.text(X0 + 2, YS - 5, "Rev.  Änderung", 1.9)
        b.text(X0 + 2, YS - 11, f"{p.get('revision', '')}", 2.3)
        b.text(X0 + 62, YS - 5, f"Datum {p.get('datum', '')}", 2)
        b.text(X0 + 62, YS - 10, f"Bearb. {p.get('ersteller', '')}", 2)
        b.text(X0 + 62, YS - 15, "Gepr.", 2)
        b.text(X0 + 112, YS - 6, p.get("bezeichnung", ""), 2.3)
        b.text(X0 + 112, YS - 12, p.get("kunde", ""), 2)
        b.text(X0 + 172, YS - 7, a.titel[:40], 2.8, True)
        b.text(X0 + 172, YS - 14, titel[:40], 2.5)
        b.text(X0 + 172, YS - 21, "Stromlaufplan" if a.art == "EFS" else "", 2.2)
        b.text(X0 + 252, YS - 6, f"Projekt-Nr. {p.get('nummer', '')}", 2.2)
        b.text(X0 + 252, YS - 15, f"Zeichnung-Nr. {self.zeichnungsnummer(a)}", 2.3, True)
        b.text(X0 + 332, YS - 6, f"= {a.kennung}", 2.6, True)
        b.text(X0 + 332, YS - 12, f"{p.get('ort', '')}", 2.4)
        b.text(X0 + 332, YS - 18, f"& {a.art}", 2.4)
        b.text(X0 + 360, YS - 6, f"Seite {nr}", 2.4)
        b.text(X0 + 360, YS - 12, f"Seiten {len(a.seiten)}", 2.4)
        b.text(X0 + 360, YS - 18, self.stil.get("vorschrift", ""), 2)
        b.text(X0 + 2, Y0 + 2.5, "Erzeugt mit slpgen (Prototyp) – nicht freigegeben", 1.6)
        b.text(X0, Y0 - 4, vorher, 2)
        b.text(X1, Y0 - 4, nachher, 2, ausr="r")

    # ---- Inhalt ------------------------------------------------------------------
    def _s_inhalt(self, b: Blatt, a: Anlage):
        zeilen = [(f"={an.kennung}", self.zeichnungsnummer(an), i + 1, f"{an.titel} – {t}"[:70])
                  for an, i, t in [(an, i, t) for an in self.anlagen.values() for i, (t, _) in enumerate(an.seiten)]]
        tabelle(b, ["Anlage", "Zeichnungsnummer", "Seite", "Seitenbeschreibung"], zeilen[:ZEILEN_JE_LISTENSEITE],
                [35, 95, 20, 200])

    # ---- Einspeisung / 24 V ------------------------------------------------------
    def _s_einspeisung(self, b: Blatt, a: Anlage):
        q1, f1 = self.m.bm("-Q1"), self.m.bm("-F1")
        b.text(X0 + 8, 268, self.m.projekt.get("_netz", ""), 2.5)
        motoren = [k for k in self.anlagen if k.startswith("M") and k[1:].isdigit()]
        for i, (lt, y) in enumerate((("L1", 262), ("L2", 256), ("L3", 250), ("N", 244), ("PE", 238))):
            b.linie(X0 + 8, y, X1 - 40, y)
            b.text(X0 + 2, y + 0.8, lt, 2.5)
            if motoren and lt != "N":
                potential_pfeil(b, X1 - 40, y, f"{lt} {self.ref(Ort(motoren[0], 1, 1), a.kennung)}")
        b.rechteck(self.x(2) - 7, 247, 14, 18, strich=([1.5, 1], 0))
        b.text(self.x(2), 270, "-Q1", 3, True, "m")
        b.text(self.x(2), 231, q1.bezeichnung, 2, ausr="m")
        x = self.x(5)
        b.kreis(x, 262, 0.6, True)
        b.linie(x, 262, x, 215)
        yu = sym_sicherung(b, x, 215, "-F1", f1.bezeichnung)
        b.linie(x, yu, x, 170)
        b.text(x + 1, 185, "BK 1,5", 1.9)
        b.linie(x, 170, X1 - 60, 170)
        potential_pfeil(b, X1 - 60, 170, f"L1a {self.ref(self.pos['-G1'], a.kennung)}")
        b.kreis(x + 10, 244, 0.6, True)
        b.linie(x + 10, 244, x + 10, 160)
        b.linie(x + 10, 160, X1 - 60, 160)
        potential_pfeil(b, X1 - 60, 160, f"N {self.ref(self.pos['-G1'], a.kennung)}")

    def _s_erzeugung(self, b: Blatt, a: Anlage):
        g1, bil = self.m.bm("-G1"), self.m.bilanz
        potential_pfeil(b, X0 + 8, 255, f"L1a {self.ref(self.pos['-F1'], a.kennung)}", False)
        potential_pfeil(b, X0 + 8, 245, f"N {self.ref(self.pos['-F1'], a.kennung)}", False)
        x = self.x(4)
        b.linie(X0 + 8, 255, x - 5, 255)
        b.linie(x - 5, 255, x - 5, 200)
        b.linie(X0 + 8, 245, x + 5, 245)
        b.linie(x + 5, 245, x + 5, 200)
        b.rechteck(x - 15, 160, 30, 40, 0.4)
        b.linie(x - 15, 160, x + 15, 200, 0.2)
        b.text(x - 17, 196, "-T1", 3.5, True, "r")
        b.text(x - 17, 191, g1.bezeichnung[:34], 1.9, ausr="r")
        b.text(x - 17, 187, f"Artikel {g1.artikel}", 1.9, ausr="r")
        ad = self.stil["ader"]
        for dx, pot, y in ((-5, f"24L+ {ad['+24V']} 1,5", 120), (5, f"24M {ad['0V']} 1,5", 110)):
            b.linie(x + dx, 160, x + dx, y)
            b.linie(x + dx, y, X1 - 60, y)
            b.text(x + dx + 1, y + 1, pot, 1.9)
            potential_pfeil(b, X1 - 60, y, f"{pot.split()[0]} {self.ref(Ort('DC24.02', 1, 0), a.kennung)}")
        b.text(X0 + 8, 90, f"Auslegung: Σ I = {bil['i_summe_A']} A → Bedarf {bil['i_bedarf_A']} A → "
                           f"{g1.artikel} ({bil['i_nenn_A']} A, Auslastung {bil['auslastung']:.0%})", 2.4)

    def _s_verteilung(self, b: Blatt, a: Anlage):
        ad = self.stil["ader"]
        potential_pfeil(b, X0 + 8, 255, f"24L+ {self.ref(self.pos['-G1'], a.kennung)}", False)
        potential_pfeil(b, X0 + 8, 90, f"24M {self.ref(self.pos['-G1'], a.kennung)}", False)
        b.linie(X0 + 8, 90, X1 - 30, 90)
        b.text(X0 + 40, 91, f"{ad['0V']} {ad['querschnitt']}", 1.9)
        for i, ab in enumerate(self.m.absicherungen):
            o = self.pos[ab.bmk]
            x = self.x(o.spalte)
            b.linie(X0 + 8 if i == 0 else self.x(self.pos[self.m.absicherungen[i - 1].bmk].spalte), 255, x, 255)
            b.kreis(x, 255, 0.6, True)
            b.linie(x, 255, x, 225)
            yu = sym_sicherung(b, x, 225, self.lokal[ab.bmk][1], f"{ab.i_nenn_A:g} A")
            b.linie(x, yu, x, 180)
            b.text(x + 1, 195, f"{ad['+24V']} {ad['querschnitt']}", 1.9)
            b.text(x + 1.5, 176, f"24L+ {ab.gruppe}", 2.2, True)
            for j, v in enumerate([v for v in ab.verbraucher if v in self.pos][:10]):
                b.text(x + 1.5, 172 - j * 3.2, f"{self.lokal.get(v, ('', v))[1]} {self.ref(self.pos[v], a.kennung)}", 1.9)

    # ---- Feldgerät ----------------------------------------------------------------
    def _s_feld(self, b: Blatt, a: Anlage):
        alt = next(k for k, (an, _) in self.lokal.items() if an == a.kennung)
        g, ad, leiste = self.m.bm(alt), self.stil["ader"], self.stil["feldklemmleiste"]
        kl = [k for k in self.m.klemmen if k.ziel_aussen.startswith(g.bmk + ":")]
        spalte = {"+24V": 2, "Signal": 4, "0V": 6}
        fa = self.pos.get(g.daten.get("absicherung", ""))
        y_k, y_dev = 170, 120
        for i, k in enumerate(kl, 1):
            x = self.x(spalte[k.potential])
            if k.potential == "+24V":
                b.text(x - 1, 266, f"24L+ {self.ref(fa, a.kennung)}", 2, ausr="r")
                b.linie(x, 268, x, y_k + 1.1)
                farbe = ad["+24V"]
            elif k.potential == "0V":
                b.text(x - 1, 266, f"24M {self.ref(Ort('DC24.02', 1, 0), a.kennung)}", 2, ausr="r")
                b.linie(x, 268, x, y_k + 1.1)
                farbe = ad["0V"]
            else:
                self._sps_kasten(b, x, 215, g.bmk, a.kennung, f"{leiste}:{i}")
                b.linie(x, 215, x, y_k + 1.1)
                farbe = ad[g.daten["signal"]]
            b.text(x + 1, y_k + 12, f"{farbe}", 1.9)
            b.text(x + 1, y_k + 9, ad["querschnitt"], 1.9)
            sym_klemme(b, x, y_k, leiste, i)
            b.linie(x, y_k - 1.1, x, y_dev)
        b.text(self.x(1), y_k - 0.8, leiste, 2.4, True, "r")
        n = len(kl)
        adern = next((z for z in self.stil["feldkabel_adern"] if z >= n), n)
        b.linie(self.x(2) - 8, 150, self.x(6) + 8, 150, strich=([2, 1], 0))
        b.text(self.x(1), 151, f"-W1 {self.stil['feldkabel_typ']} {adern}x0,75", 2.2, ausr="r")
        b.rechteck(self.x(1) - 10, 60, self.x(7) - self.x(1) + 20, 60, strich=([4, 1, 1, 1], 0))
        b.text(self.x(1) - 8, 114, "Feld", 2.2)
        b.rechteck(self.x(2) - 8, y_dev - 30, self.x(6) - self.x(2) + 16, 30, 0.4)
        b.text(self.x(4), y_dev - 10, self.lokal[g.bmk][1], 4, True, "m")
        b.text(self.x(4), y_dev - 16, g.bezeichnung[:60], 2.1, ausr="m")
        b.text(self.x(4), y_dev - 21, f"{g.artikel}   I = {g.daten['i_A'] * 1000:.0f} mA", 2, ausr="m")
        for k, sp in zip(kl, (spalte[k.potential] for k in kl)):
            b.text(self.x(sp) + 0.8, y_dev - 4, k.ziel_aussen.split(":", 1)[1].split(" ")[0], 1.9)

    def _sps_kasten(self, b: Blatt, x: float, y: float, geraet: str, von: str, klemme: str):
        """SPS-Kasten im Hausstil: Kanal, Karte, Verweis, Adresse, Klemme, Funktionstext, Artikel."""
        k = next(c for c in self.m.sps_kanaele if c.geraet_bmk == geraet)
        karte_a, karte_bmk = self.lokal[k.modul_bmk]
        modul = self.m.bm(k.modul_bmk)
        b.rechteck(x - 20, y, 40, 32)
        zeilen = [(f"{k.art}{k.kanal}", 2.0, False), (f"={karte_a}{karte_bmk}", 2.6, True),
                  (self.ref(self.pos.get(f"karte:{geraet}"), von), 1.9, False), (k.adresse, 2.6, True),
                  (klemme, 1.9, False), (k.funktion[:34], 1.8, False)]
        for i, (t, g, fett) in enumerate(zeilen):
            b.text(x, y + 28 - i * 4.6, t, g, fett, "m")
            if i in (1, 3):
                b.linie(x - 20, y + 26.3 - i * 4.6, x + 20, y + 26.3 - i * 4.6, 0.15)
        b.text(x, y - 3, modul.artikel, 1.7, ausr="m")

    # ---- Motor ------------------------------------------------------------------
    def _motor(self, a: Anlage):
        alt_m = next(k for k, (an, lok) in self.lokal.items() if an == a.kennung and lok == "-M1")
        nr = int(alt_m.lstrip("-M"))
        return self.m.bm(alt_m), self.m.bm(f"-Q{nr + 1}"), self.m.bm(f"-K{nr}"), \
            next(c for c in self.m.kabel if c.nach == alt_m)

    def _s_motor_last(self, b: Blatt, a: Anlage):
        mot, q, k, w = self._motor(a)
        x = self.x(4)
        for d, (lt, y) in zip((-6, 0, 6), (("L1", 262), ("L2", 256), ("L3", 250))):
            potential_pfeil(b, X0 + 8, y, f"{lt} {self.ref(self.pos['-Q1'], a.kennung)}", False)
            b.linie(X0 + 8, y, x + d, y)
            b.linie(x + d, y, x + d, 222)
            b.rechteck(x + d - 1.2, 216, 2.4, 6)
            b.linie(x + d, 216, x + d, 190)
            sym_schliesser(b, x + d, 190, 12)
            b.linie(x + d, 178, x + d, 131.1)
        potential_pfeil(b, X0 + 8, 238, f"PE {self.ref(self.pos['-Q1'], a.kennung)}", False)
        b.linie(X0 + 8, 238, x + 12, 238)
        b.linie(x + 12, 238, x + 12, 131.1)
        b.rechteck(x - 10, 210, 20, 18, strich=([1.5, 1], 0))
        b.text(x - 11, 222, "-Q1", 3, True, "r")
        b.text(x - 11, 218, f"Ir = {q.daten['i_r_A']:g} A", 2, ausr="r")
        b.text(x - 11, 214.5, f"13-14 /2.6", 1.9, ausr="r")
        b.text(x - 11, 186, "-K1", 3, True, "r")
        b.text(x - 11, 182.5, "A1-A2 /2.2", 1.9, ausr="r")
        b.linie(x - 6, 184, x + 6, 184, strich=([1, 1], 0))
        for i, d in enumerate((-6, 0, 6, 12), 1):
            sym_klemme(b, x + d, 130, "-X1", i)
            b.linie(x + d, 128.9, x + d, 100 if d < 12 else 90)
            b.text(x + d + 1, 160, "BK" if d < 12 else "GNYE", 1.8)
            b.text(x + d + 1, 157, f"{w.querschnitt_mm2:g}".replace(".", ","), 1.8)
        b.text(x - 11, 129.2, "-X1", 2.4, True, "r")
        b.linie(x - 9, 112, x + 15, 118, 0.25)
        b.text(x + 16, 119, f"-W1 {w.adern}G{w.querschnitt_mm2:g} {w.laenge_m:g} m".replace(".", ","), 2.2)
        b.linie(x + 12, 90, x + 9.9, 90)
        b.kreis(x, 90, 10)
        b.text(x, 91, "M", 4, True, "m")
        b.text(x, 85.5, "3~", 2.6, ausr="m")
        b.text(x + 14, 84, "-M1", 3.5, True)
        b.text(x + 14, 80, f"P = {mot.daten['p_kW']:g} kW  I_N = {mot.daten['i_N_A']:g} A", 2)

    def _s_motor_steuer(self, b: Blatt, a: Anlage):
        mot, q, k, w = self._motor(a)
        ad = self.stil["ader"]
        x = self.x(2)
        self._sps_kasten(b, x, 215, k.bmk, a.kennung, "-K1:A1")
        b.linie(x, 215, x, 156)
        b.text(x + 1, 190, f"{ad['DO']} {ad['querschnitt']}", 1.9)
        b.rechteck(x - 4, 150, 8, 6, 0.4)
        b.text(x - 6, 152, "-K1", 3, True, "r")
        b.linie(x, 150, x, 95)
        potential_pfeil(b, X1 - 30, 95, f"24M {self.ref(Ort('DC24.02', 1, 0), a.kennung)}")
        b.linie(x, 95, X1 - 30, 95)
        for i, kt in enumerate(("1-2", "3-4", "5-6")):
            b.text(x - 6, 88 - i * 3.5, f"{kt}  /1.4", 1.9)
        xb = self.x(6)
        fa = self.pos.get(q.daten.get("absicherung", ""))
        b.text(xb - 1, 266, f"24L+ {self.ref(fa, a.kennung)}", 2, ausr="r")
        b.linie(xb, 268, xb, 205)
        sym_schliesser(b, xb, 205, 12)
        b.text(xb - 4, 199, "-Q1", 3, True, "r")
        b.text(xb - 4, 195.5, "/1.4", 1.9, ausr="r")
        b.text(xb + 2, 203, "13", 1.9)
        b.text(xb + 2, 194, "14", 1.9)
        b.linie(xb, 193, xb, 172)
        self._sps_kasten(b, xb, 140, q.bmk, a.kennung, "-Q1:14")
        b.linie(xb, 172, xb, 140 + 32)

    # ---- SPS -------------------------------------------------------------------
    def _s_cpu(self, b: Blatt, a: Anlage):
        cpu = self.m.bm("-A1")
        x = self.x(1)
        b.rechteck(x - 15, 120, 60, 140, 0.4)
        b.text(x, 252, "-K1", 3.5, True)
        b.text(x, 246, cpu.bezeichnung, 2.4)
        b.text(x, 241, cpu.artikel, 2)
        fa = self.pos.get(next((ab.bmk for ab in self.m.absicherungen if "-A1" in ab.verbraucher), ""))
        b.text(x, 200, f"Versorgung 24L+ {self.ref(fa, a.kennung)}", 2.2)

    def _s_karte(self, modul_bmk: str):
        def zeichne(b: Blatt, a: Anlage):
            mod = self.m.bm(modul_bmk)
            x = self.x(1)
            b.text(x - 10, 262, self.lokal[modul_bmk][1], 3.5, True)
            b.text(x - 10, 257, mod.bezeichnung, 2.3)
            b.text(x - 10, 253, mod.artikel, 1.9)
            b.rechteck(x - 12, 100, 45, 150, 0.4)
            for k in [k for k in self.m.sps_kanaele if k.modul_bmk == modul_bmk]:
                y = 240 - k.kanal * 8
                b.text(x + 18, y, k.adresse, 2.4, True, "r")
                b.text(x + 20, y, f"{k.art}{k.kanal}", 2)
                ziel = self.pos.get(f"kanal:{k.geraet_bmk}")
                b.text(x + 40, y, self.ref(ziel, a.kennung), 2.2)
                b.text(x + 75, y, f"{k.funktion}  {self.voll(k.geraet_bmk)}"[:80], 2.2)
        return zeichne

    # ---- Listen ------------------------------------------------------------------
    def _kabelzeilen(self):
        z = []
        for kenn, an in self.anlagen.items():
            alt = next((k for k, (a2, lok) in self.lokal.items() if a2 == kenn and lok[1:2] in ("B", "Y", "P")
                        and self.m.bm(k).kategorie in ("sensor", "aktor")), None)
            if alt:
                n = len([k for k in self.m.klemmen if k.ziel_aussen.startswith(alt + ":")])
                adern = next((x for x in self.stil["feldkabel_adern"] if x >= n), n)
                z.append((f"={kenn}-W1", f"{self.stil['feldkabel_typ']} {adern}x0,75 mm²",
                          f"={kenn}{self.stil['feldklemmleiste']}", f"={kenn}{self.lokal[alt][1]}"))
        for w in self.m.kabel:
            kenn = self.lokal[w.bmk][0]
            z.append((f"={kenn}-W1", f"{w.adern}G{w.querschnitt_mm2:g} mm² ({w.artikel})".replace(".", ","),
                      f"={kenn}-X1", f"={kenn}-M1"))
        return z

    def _s_kabel(self, b: Blatt, a: Anlage, idx: int):
        tabelle(b, ["Kabelnummer", "Kabeltyp", "Quelle", "Ziel"],
                self._kabelzeilen()[idx * ZEILEN_JE_LISTENSEITE:(idx + 1) * ZEILEN_JE_LISTENSEITE], [50, 90, 90, 90])

    def _klemmenzeilen(self):
        z = []
        nr_je = {}
        for k in self.m.klemmen:
            geraet = k.ziel_aussen.split(":")[0]
            if geraet not in self.lokal:
                continue
            kenn, lok = self.lokal[geraet]
            leiste = self.stil["feldklemmleiste"] if k.leiste == "-X1" else "-X1"
            nr_je[(kenn, leiste)] = nr_je.get((kenn, leiste), 0) + 1
            ziel_innen = k.ziel_innen
            for alt, (an2, lok2) in self.lokal.items():
                if ziel_innen.startswith(alt + ":") or ziel_innen == alt:
                    ziel_innen = ziel_innen.replace(alt, f"={an2}{lok2}", 1)
                    break
            z.append((f"={kenn}{leiste}:{nr_je[(kenn, leiste)]}", k.potential, ziel_innen,
                      f"{lok}:{k.ziel_aussen.split(':', 1)[1]}", f"={kenn}/1"))
        return z

    def _s_klemmen(self, b: Blatt, a: Anlage, idx: int):
        tabelle(b, ["Klemme", "Potential", "Ziel innen", "Ziel außen", "Seite"],
                self._klemmenzeilen()[idx * ZEILEN_JE_LISTENSEITE:(idx + 1) * ZEILEN_JE_LISTENSEITE],
                [55, 30, 110, 80, 30])

    def _stl_zeilen(self):
        ort = self.m.projekt.get("ort", "")
        zeilen = []
        for bm in self.m.betriebsmittel:
            if bm.bmk not in self.lokal:
                continue
            kenn, lok = self.lokal[bm.bmk]
            art = self.stamm["artikel"].get(bm.artikel, {"hersteller": "", "bezeichnung": "Beistellung Kunde"})
            zeilen.append((f"={kenn}", ort, lok, "1 Stk", art.get("hersteller", ""), bm.artikel,
                           art["bezeichnung"][:55]))
        return [(i + 1, *z) for i, z in enumerate(zeilen)]

    def _s_stueckliste(self, b: Blatt, a: Anlage, idx: int):
        tabelle(b, ["Pos.", "=Anlage", "+Ort", "-BMK", "Menge", "Hersteller", "Artikel", "Benennung"],
                self._stl_zeilen()[idx * ZEILEN_JE_LISTENSEITE:(idx + 1) * ZEILEN_JE_LISTENSEITE],
                [14, 28, 20, 20, 18, 38, 38, 160])

    def _s_auslegung(self, b: Blatt, a: Anlage, _idx: int):
        bil = self.m.bilanz
        zeilen = [(f"=DC24.02{self.lokal[ab.bmk][1]}", ab.gruppe, f"{ab.i_gruppe_A:.3f}", f"{ab.i_nenn_A:g}")
                  for ab in self.m.absicherungen]
        tabelle(b, ["Abgang", "Gruppe", "Σ I [A]", "Sicherung [A]"], zeilen, [50, 40, 30, 30])
        y = YL - 12 - 7 - len(zeilen) * 5.5 - 10
        texte = [f"Summenstrom 24 V: Σ I = {bil['i_summe_A']} A; Bedarf mit g und Reserve = {bil['i_bedarf_A']} A",
                 f"Netzteil {bil['netzteil']} ({bil['i_nenn_A']} A, Auslastung {bil['auslastung']:.0%})"]
        if self.m.kabel:
            texte.append(f"Motoren Σ I_N = {bil['i_motoren_A']} A; 400 V gesamt ≤ {bil['i_400V_max_A']} A")
        for q, w in self.stil["quelle"].items():
            texte.append(f"Hausstil: {q} = {self.stil[q]} aus {w}")
        for t in texte + ["Hinweise:"] + [f"• {w}" for w in self.m.warnungen or ["keine"]]:
            b.text(X0 + 6, y, t, 2.6)
            y -= 6


def erzeuge_hausstil_pdf(m: Planmodell, stamm: dict, pfad: str, stil: dict | None = None) -> list[tuple[str, int, str]]:
    stil = stil or lade_hausstil(None)
    hp = Hausplan(m, stamm, stil)
    folge = hp.seitenfolge()
    c = Canvas(pfad, pagesize=landscape(A3), invariant=1)
    c.setTitle(f"Stromlaufplan {m.projekt.get('nummer', '')}")
    b = Blatt(c)
    for i, (a, nr, titel, zeichner) in enumerate(folge):
        vorher = f"={folge[i - 1][0].kennung}/{folge[i - 1][1]}" if i else ""
        nachher = f"={folge[i + 1][0].kennung}/{folge[i + 1][1]}" if i + 1 < len(folge) else ""
        hp.rahmen(b, a, nr, titel, vorher, nachher)
        zeichner(b, a)
        c.showPage()
    c.save()
    return [(a.kennung, nr, t) for a, nr, t, _ in folge]
