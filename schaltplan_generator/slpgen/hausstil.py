"""Ausgabe im Hausstil: eine Anlage je Funktion, Spalten 0–9, Seitenzählung je Anlage,
Querverweise `=Anlage/Seite.Spalte`, SPS-Kasten je Kanal, Aderkennzeichnung an Verbindungen.

Die Auslegung (Bilanz, Absicherung, SPS-Adressen, Motorabgänge) kommt unverändert aus
`regeln.plane()`; dieses Modul ordnet das Planmodell in Anlagen und zeichnet sie.
Hausparameter stehen in HAUSSTIL_STANDARD (neutral) und werden – soweit freigegeben – aus
dem lokalen Hausprofil überschrieben (`lade_hausstil`).
"""
from __future__ import annotations

import copy
import datetime as dt
import re
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

import yaml
from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfgen.canvas import Canvas

from .freigabe import pruefe_eigenen_wert
from .modell import SAMMELMELDUNG, Betriebsmittel, Planmodell, RegelFehler, eltern_bmk
from .zeichnen import (
    X0,
    X1,
    Y0,
    Y1,
    YL,
    YS,
    Blatt,
    hat_pruefbericht_fehler,
    potential_pfeil,
    s_deckblatt,
    stempel_nicht_fertigung,
    sym_klemme,
    sym_schliesser,
    sym_sicherung,
    tabelle,
)

HAUSSTIL_STANDARD = {
    "spalten": 10,                                   # Spaltenleiste 0..9
    "feldklemmleiste": "-X10",
    "zeichnungsnummer": "{projekt}-{anlage}-1-{art}-{rev}",
    "vorschrift": "",
    "ader": {"+24V": "DBU", "0V": "DBU/WH", "DI": "DBU", "DO": "DBU", "AI": "WH", "AO": "WH", "querschnitt": "0,75"},
    "feldkabel_typ": "LIYCY",
    "kennbuchstaben": {"netzteil": "T", "sps_karte": "K"},
    "feldkabel_adern": [2, 3, 4, 7, 12],
    "kartenanlagen": {"CPU": "SA0", "DI": "SA1", "DO": "SA2", "AI": "SA3", "AO": "SA4"},
    "infrastruktur": {"einspeisung": "EIN", "erzeugung": "NT24", "verteilung": "VT24"},
    "ader_ac": {"L": "BK", "N": "LBU", "PE": "GNYE", "querschnitt": "1,5"},
}
ZEILEN_JE_LISTENSEITE = 36
LEITER_Y = {"L1": 262, "L2": 256, "L3": 250, "N": 244, "PE": 238}   # Lage der Netzleiter auf Lastseiten


def lade_hausstil(profil_pfad: str | Path | None) -> dict:
    """Standard + freigegebene Werte aus dem Hausprofil (nur Status `freigegeben` zählt)."""
    stil: dict[str, Any] = copy.deepcopy(HAUSSTIL_STANDARD)
    stil["quelle"], stil["warnungen"] = {}, []
    if profil_pfad and Path(profil_pfad).exists():
        profil = yaml.safe_load(Path(profil_pfad).read_text(encoding="utf-8")) or {}
        merkmale = profil.get("merkmale", {})
        frei = {}
        for k, v in merkmale.items():
            if not (isinstance(v, dict) and v.get("status") == "freigegeben" and str(v.get("wert", "")).strip()):
                continue
            try:                                   # ältere Profile: Werte vor der Eingabeprüfung (M1) nachprüfen
                frei[k] = pruefe_eigenen_wert(k, str(v["wert"]))
            except RegelFehler as e:
                stil["warnungen"].append(f"Hausprofil: {v.get('beschreibung', k)} = „{v['wert']}“ ungültig ({e}) "
                                         f"– Standard verwendet, bitte in der Freigabeliste korrigieren")

        def herkunft(key: str) -> str:
            return f"{merkmale[key].get('beschreibung', key)} = {frei[key]} (Hausprofil, freigegeben)"
        if "spaltenraster" in frei:                     # M5d: gelernte Geometrie wirkt im Plan
            n, breite = re.match(r"(\d+) Spalten à ([\d,]+) mm", frei["spaltenraster"]).groups()  # type: ignore[union-attr]
            soll = (X1 - X0) / int(n)
            if int(n) != 10:                             # ANNAHME A45: Zeichner sind fest auf die Spalten 0…9 ausgelegt
                stil["warnungen"].append(f"Hausprofil: Spaltenraster {frei['spaltenraster']} wird noch nicht unterstützt "
                                         f"(nur 10 Spalten) – Plan mit 10 Spalten gezeichnet")
            else:
                stil["spalten"] = int(n)
                stil["quelle"]["spaltenraster"] = herkunft("spaltenraster")
                if abs(float(breite.replace(",", ".")) - soll) > 0.1 * soll:
                    stil["warnungen"].append(f"Hausprofil: Die Spaltenbreite {breite} mm wird nicht übernommen – der Plan "
                                             f"nutzt die Breite des A3-Rahmens ({soll:.1f} mm)".replace(".", ","))
        if "datumsformat" in frei:
            stil["datumsformat"] = frei["datumsformat"]
            stil["quelle"]["datumsformat"] = herkunft("datumsformat")
        if frei.get("feldklemmleiste", "").startswith("-X"):
            stil["feldklemmleiste"], stil["quelle"]["feldklemmleiste"] = frei["feldklemmleiste"], herkunft("feldklemmleiste")
        for key, wert in frei.items():
            if key.startswith("ader_"):
                pot = key[len("ader_"):]
                ziel = stil["ader_ac"] if pot in ("L", "N", "PE") else stil["ader"]
                if pot in ziel:
                    ziel[pot] = wert
                    stil["quelle"][key] = herkunft(key)
            elif key.startswith("kennbuchstabe_") and re.fullmatch(r"[A-Z]{1,3}", wert):
                stil["kennbuchstaben"][key[len("kennbuchstabe_"):]] = wert
                stil["quelle"][key] = herkunft(key)
    return stil


# --------------------------------------------------------------------------- #
# Anlagenmodell
# --------------------------------------------------------------------------- #
@dataclass
class Anlage:
    kennung: str                     # ohne "=", z. B. "B01", "VT24"
    titel: str
    art: str = "EFS"
    seiten: list[tuple[str, Callable]] = field(default_factory=list)   # (Seitentitel, Zeichner)


@dataclass
class Ort:
    anlage: str
    seite: int
    spalte: int


NACH_FELDMASS = "nach Feldmaß"


def datum_im_format(iso: object, fmt: str | None) -> str:
    """ISO-Datum (Planmodell) im Hausformat: TT.MM.JJJJ, TT.MM.JJ oder JJJJ-MM-TT (Standard: unverändert)."""
    if iso in (None, ""):
        return ""
    try:
        d = dt.date.fromisoformat(str(iso))
    except ValueError:
        return str(iso)
    return {"TT.MM.JJJJ": f"{d:%d.%m.%Y}", "TT.MM.JJ": f"{d:%d.%m.%y}"}.get(fmt or "", d.isoformat())


def _zahl(x: float) -> str:
    """Zahl im deutschen Format ohne überflüssige Nullen: 1.5 -> „1,5“, 25.0 -> „25“."""
    return f"{x:g}".replace(".", ",")


def _kuerze(text: str, n: int) -> str:
    return text if len(text) <= n else text[: n - 1] + "…"


class Hausplan:
    """Planmodell -> Anlagen; hält Positionen für Querverweise."""

    def __init__(self, m: Planmodell, stil: dict):
        self.m, self.stil = m, stil
        self.anlagen: OrderedDict[str, Anlage] = OrderedDict()
        self.pos: dict[str, Ort] = {}            # Schlüssel: altes BMK oder "kanal:<geraet>" / "karte:<geraet>"
        self.lokal: dict[str, tuple[str, str]] = {}   # altes BMK -> (Anlage, lokales BMK)
        self._aufbauen()
        if m.kennzeichen and {k: list(v) for k, v in self.lokal.items()} != m.kennzeichen:
            raise RegelFehler("Kennzeichen im Planmodell passen nicht zum aktuellen Hausprofil (Profil seit dem "
                              "Planen geändert?) – Plan neu erzeugen")

    # ---- Verweise --------------------------------------------------------------
    def ref(self, ziel: Ort | None, von: str) -> str:
        if ziel is None:
            return ""
        return f"/{ziel.seite}.{ziel.spalte}" if ziel.anlage == von else f"={ziel.anlage}/{ziel.seite}.{ziel.spalte}"

    def voll(self, alt_bmk: str) -> str:
        alt_bmk = eltern_bmk(alt_bmk)
        a, lok = self.lokal.get(alt_bmk, ("", alt_bmk))
        return f"={a}{self.m.projekt.get('ort', '')}{lok}"

    # ---- Aufbau ----------------------------------------------------------------
    def _aufbauen(self):
        m, karten, infra = self.m, self.stil["kartenanlagen"], self.stil["infrastruktur"]
        self.EIN, self.NT, self.VT = infra["einspeisung"], infra["erzeugung"], infra["verteilung"]
        self._neu("DBL", "Deckblatt", "DBL").seiten.append(
            ("Deckblatt", lambda b, a: s_deckblatt(b, m, datum_im_format(m.projekt.get("datum"), self.stil.get("datumsformat")))))
        self._neu("INH", "Inhaltsverzeichnis", "INH")             # Seiten erst am Ende (hängt von allem ab)

        self._neu(self.EIN, "Einspeisung").seiten.append(("Einspeisung", self._s_einspeisung))
        self._lokal("-Q1", self.EIN, "-Q1", 1, 2)
        self._lokal("-F1", self.EIN, "-F1", 1, 5)
        self.pos["netz_aus"] = Ort(self.EIN, 1, 9)
        self._neu(self.NT, "24 V DC Erzeugung").seiten.append(("Erzeugung 24 V DC", self._s_erzeugung))
        kb = self.stil["kennbuchstaben"]
        self._lokal("-G1", self.NT, f"-{kb['netzteil']}1", 1, 4)
        self._neu(self.VT, "24 V DC Verteilung").seiten.append(("Potentialverteilung 24 V DC", self._s_verteilung))
        self.pos["24M"] = Ort(self.VT, 1, 0)
        module = [b for b in m.betriebsmittel if b.kategorie == "selektivmodul"]
        for j, sel in enumerate(module):                    # Selektivmodule: lokal -F1, -F2 …
            self._lokal(sel.bmk, self.VT, f"-F{j + 1}", 1, 1)
        sammel = any(k.geraet_bmk == SAMMELMELDUNG for k in m.sps_kanaele)
        n = len(m.absicherungen) + (1 if sammel else 0)
        if n > 9:
            raise RegelFehler(f"{n} Abgänge passen nicht auf die 24-V-Verteilseite (höchstens 9) – Gruppen zusammenlegen")
        schritt = 2 if n <= 4 else 1
        for i, a in enumerate(m.absicherungen):
            kanal = m.bm(a.bmk)
            lok = (f"{self.lokal[kanal.daten['modul']][1]}:K{kanal.daten['kanal']}" if kanal.kategorie == "selektivkanal"
                   else f"-F{i + 1}")
            self._lokal(a.bmk, self.VT, lok, 1, 1 + schritt * i)
        if sammel:                                          # Meldekontakte in der Spalte nach dem letzten Abgang
            self._lokal(SAMMELMELDUNG, self.VT, "Meldung", 1, 1 + schritt * len(m.absicherungen))
            self.pos[f"kanal:{SAMMELMELDUNG}"] = self.pos[SAMMELMELDUNG]

        # je Motor eine Anlage (Lastkreis + Steuerung); Zuordnung über die Daten, nicht über Nummern
        self.netzkette: list[str] = []                 # Anlagen an L1-L3/N/PE in Reihenfolge (Motoren, Netzgeräte)
        self.netzbedarf: dict[str, set[str]] = {}       # je Kettenglied benötigte Leiter
        for i, mot in enumerate([b for b in m.betriebsmittel if b.kategorie == "motor"], 1):
            kenn = self._kennung(mot.bmk, "M", i)
            an = self._neu(kenn, f"Motor {mot.bmk} {mot.funktion}".strip())
            an.seiten += [("Lastkreis", self._s_motor_last), ("Steuerung", self._s_motor_steuer)]
            self.netzkette.append(kenn)
            self.netzbedarf[kenn] = {"L1", "L2", "L3", "PE"}
            q, k, w = mot.daten["mss"], mot.daten["schuetz"], mot.daten["kabel"]
            self._lokal(mot.bmk, kenn, "-M1", 1, 4)
            self._lokal(w, kenn, "-W1", 1, 4)
            self._lokal(q, kenn, "-Q1", 2, 6)          # 24-V-Verbraucher: Hilfskontakt 13/14 (Steuerung)
            self._lokal(k, kenn, "-K1", 2, 2)          # 24-V-Verbraucher: Spule A1/A2 (Steuerung)
            self.pos[f"haupt:{q}"] = Ort(kenn, 1, 4)  # Leistungsteil im Lastkreis
            self.pos[f"haupt:{k}"] = Ort(kenn, 1, 4)
            self.pos[f"kanal:{k}"] = Ort(kenn, 2, 2)
            self.pos[f"kanal:{q}"] = Ort(kenn, 2, 6)
            self.pos[f"netz_ein:{kenn}"] = Ort(kenn, 1, 0)
            self.pos[f"netz_aus:{kenn}"] = Ort(kenn, 1, 9)

        # je Feldgerät eine Anlage
        for i, g in enumerate([b for b in m.betriebsmittel if b.kategorie in ("sensor", "aktor")], 1):
            buchst = "".join(c for c in g.bmk if c.isalpha()) or "F"
            kenn = self._kennung(g.bmk, buchst, i)
            an = self._neu(kenn, f"{g.funktion}".strip() or g.bezeichnung)
            an.seiten.append((g.funktion or g.bezeichnung, self._s_feld))
            self._lokal(g.bmk, kenn, f"-{buchst}1", 1, 4)
            kl = self._feldklemmen(g.bmk)
            for i, k in enumerate(kl):                              # SPS-Kasten über der Signalklemme
                if k.signal:
                    self.pos[f"kanal:{k.signal}"] = Ort(kenn, 1, self._feldspalte(i, len(kl)))
            for bt in [x for x in m.betriebsmittel
                       if x.kategorie in ("bauteil", "kabel") and x.daten.get("eltern") == g.bmk]:
                self._lokal(bt.bmk, kenn, bt.daten["lokal"], 1, 1)
            if g.daten.get("leistung"):                              # Netzgerät: zweite Seite Leistungsteil
                an.seiten.append(("Leistungsteil", self._s_leistung))
                self.netzkette.append(kenn)
                self.netzbedarf[kenn] = {g.daten["leistung"].get("aussenleiter", "L1"), "N", "PE"}
                self.pos[f"netz_ein:{kenn}"] = Ort(kenn, 2, 0)
                self.pos[f"netz_aus:{kenn}"] = Ort(kenn, 2, 9)
                le = g.daten["leistung"]
                self._lokal(le["mss"], kenn, "-Q1", 2, 3)
                self._lokal(le["kabel"], kenn, "-W2", 2, 3)
                self.pos[f"haupt:{le['mss']}"] = Ort(kenn, 2, 3)
                for t in g.daten.get("quellsignale", {}):            # Hilfskontakt-Meldung auf Seite 2
                    self.pos[f"kanal:{t}"] = Ort(kenn, 2, 6)

        # SPS-Karten je Signalart als Anlage
        cpu = self._neu(karten["CPU"], "SPS-Steuerung")
        cpu.seiten.append(("SPS-CPU", self._s_cpu))
        self._lokal("-A1", karten["CPU"], f"-{kb['sps_karte']}1", 1, 1)
        for sig, kenn, titel in (("DI", karten["DI"], "SPS Digitaleingänge"), ("DO", karten["DO"], "SPS Digitalausgänge"),
                                 ("AI", karten["AI"], "SPS Analogeingänge"), ("AO", karten["AO"], "SPS Analogausgänge")):
            mods = sorted({k.modul_bmk for k in m.sps_kanaele if k.art == sig})
            if not mods:
                continue
            an = self._neu(kenn, titel)
            for i, mod in enumerate(mods):
                an.seiten.append((f"{titel} Karte {i + 1}", self._s_karte(mod)))
                self._lokal(mod, kenn, f"-{kb['sps_karte']}{i + 1}", i + 1, 1)
                self.pos[f"modul:{mod}"] = Ort(kenn, i + 1, 1)
                for k in [k for k in m.sps_kanaele if k.modul_bmk == mod]:
                    self.pos[f"karte:{k.geraet_bmk}"] = Ort(kenn, i + 1, 0)      # Kanaltabelle: Kanal in Spalte 0

        for kenn, titel, art, zeichner, n in (
                ("KAB", "Kabelübersicht", "KAB", self._s_kabel, len(self._kabelzeilen())),
                ("KPL", "Klemmenplan", "KPL", self._s_klemmen, len(self._klemmenplan()[0])),
                ("STL", "Artikelstückliste", "STL", self._s_stueckliste, len(self._stl_zeilen())),
                ("SUM", "Summenstückliste", "STL", self._s_summe, len(self._summenzeilen())),
                ("AUS", "Auslegungsnachweis", "AUS", self._s_auslegung, len(self._auslegungszeilen()))):
            self._listenanlage(kenn, titel, art, zeichner, n)

        # Inhaltsverzeichnis zuletzt: seine Seitenzahl hängt von der Gesamtseitenzahl ab (inkl. eigener Seiten)
        n_inh = 1
        while -(-(sum(len(a.seiten) for a in self.anlagen.values()) + n_inh) // ZEILEN_JE_LISTENSEITE) > n_inh:
            n_inh += 1
        self.anlagen["INH"].seiten = [("Inhaltsverzeichnis", (lambda i: lambda b, a: self._s_inhalt(b, a, i))(i))  # noqa: B023 – i sofort gebunden
                                      for i in range(n_inh)]

    def _listenanlage(self, kenn, titel, art, zeichner, n):
        an = self._neu(kenn, titel, art)
        for i in range(max(1, -(-n // ZEILEN_JE_LISTENSEITE))):
            an.seiten.append((titel, (lambda i: lambda b, a: zeichner(b, a, i))(i)))  # noqa: B023 – i sofort gebunden

    def _feldklemmen(self, geraet: str):
        """Signalklemmen eines Feldgeräts (Leistungsklemmen L/N/PE liegen auf eigener Leiste)."""
        return [k for k in self.m.klemmen if k.ziel_aussen.startswith(geraet + ":") and k.leiste == "-X1"]

    @staticmethod
    def _feldspalte(index: int, anzahl: int) -> int:
        """Klemmen von links nach rechts: bis 5 Klemmen in Spalte 1, 3, 5, 7, 9, sonst 1, 2, … 9."""
        return 1 + 2 * index if anzahl <= 5 else 1 + index

    def _kennung(self, bmk: str, buchst: str, laufnr: int) -> str:
        ziffern = "".join(c for c in bmk if c.isdigit())
        return f"{buchst}{int(ziffern) if ziffern else laufnr:02d}"

    def _neu(self, kenn: str, titel: str, art: str = "EFS") -> Anlage:
        if kenn in self.anlagen:
            raise RegelFehler(f"Anlagenkennung ={kenn} wäre doppelt (z. B. Feldgeräte B1 und B01) – "
                              f"bitte Betriebsmittelkennzeichen eindeutig vergeben")
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
        b.text(X0 + 62, YS - 5, f"Datum {datum_im_format(p.get('datum', ''), self.stil.get('datumsformat'))}", 2)
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
    def _s_inhalt(self, b: Blatt, a: Anlage, idx: int = 0):
        zeilen = [(f"={an.kennung}", self.zeichnungsnummer(an), i + 1, f"{an.titel} – {t}"[:70])
                  for an in self.anlagen.values() for i, (t, _) in enumerate(an.seiten)]
        tabelle(b, ["Anlage", "Zeichnungsnummer", "Seite", "Seitenbeschreibung"],
                zeilen[idx * ZEILEN_JE_LISTENSEITE:(idx + 1) * ZEILEN_JE_LISTENSEITE], [35, 95, 20, 200])

    # ---- Einspeisung / 24 V ------------------------------------------------------
    def _s_einspeisung(self, b: Blatt, a: Anlage):
        q1, f1 = self.m.bm("-Q1"), self.m.bm("-F1")
        b.text(X0 + 8, 268, self.m.projekt.get("_netz", ""), 2.5)
        ac = self.stil["ader_ac"]
        erster = self.pos.get(f"netz_ein:{self.netzkette[0]}") if self.netzkette else None
        benoetigt = self._leiter_ab(0)
        for lt, y in LEITER_Y.items():
            b.linie(X0 + 8, y, X1 - 30, y)
            b.text(X0 + 2, y + 0.8, lt, 2.5)
            if erster and lt in benoetigt:
                potential_pfeil(b, X1 - 30, y, f"{lt} {self.ref(erster, a.kennung)}")
        b.rechteck(self.x(2) - 7, 247, 14, 18, strich=([1.5, 1], 0))
        b.text(self.x(2), 270, "-Q1", 3, True, "m")
        b.text(self.x(2), 231, q1.bezeichnung, 2, ausr="m")
        x = self.x(5)
        b.kreis(x, 262, 0.6, True)
        b.linie(x, 262, x, 215)
        yu = sym_sicherung(b, x, 215, "-F1", f1.bezeichnung)
        b.linie(x, yu, x, 170)
        b.text(x + 1, 185, f"{ac['L']} {ac['querschnitt']}", 1.9)
        b.linie(x, 170, X1 - 60, 170)
        potential_pfeil(b, X1 - 60, 170, f"L1a {self.ref(self.pos['-G1'], a.kennung)}")
        b.kreis(x + 10, 244, 0.6, True)
        b.linie(x + 10, 244, x + 10, 160)
        b.text(x + 11, 185, f"{ac['N']} {ac['querschnitt']}", 1.9)
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
        b.text(x - 17, 196, self.lokal["-G1"][1], 3.5, True, "r")
        ac = self.stil["ader_ac"]
        b.text(x - 4, 230, f"{ac['L']} {ac['querschnitt']}", 1.9)
        b.text(x + 6, 230, f"{ac['N']} {ac['querschnitt']}", 1.9)
        b.text(x - 17, 191, g1.bezeichnung[:34], 1.9, ausr="r")
        b.text(x - 17, 187, f"Artikel {g1.artikel}", 1.9, ausr="r")
        ad = self.stil["ader"]
        for dx, pot, y in ((-5, f"24L+ {ad['+24V']} 1,5", 120), (5, f"24M {ad['0V']} 1,5", 110)):
            b.linie(x + dx, 160, x + dx, y)
            b.linie(x + dx, y, X1 - 60, y)
            b.text(x + dx + 1, y + 1, pot, 1.9)
            potential_pfeil(b, X1 - 60, y, f"{pot.split()[0]} {self.ref(self.pos['24M'], a.kennung)}")
        b.text(X0 + 8, 90, f"Auslegung: Σ I = {bil['i_summe_A']} A → Bedarf {bil['i_bedarf_A']} A → "
                           f"{g1.artikel} ({bil['i_nenn_A']} A, Auslastung {bil['auslastung']:.0%})", 2.4)

    def _s_verteilung(self, b: Blatt, a: Anlage):
        ad = self.stil["ader"]
        potential_pfeil(b, X0 + 8, 255, f"24L+ {self.ref(self.pos['-G1'], a.kennung)}", False)
        potential_pfeil(b, X0 + 8, 90, f"24M {self.ref(self.pos['-G1'], a.kennung)}", False)
        b.linie(X0 + 8, 90, X1 - 30, 90)
        b.text(X0 + 40, 91, f"{ad['0V']} {ad['querschnitt']}", 1.9)
        for mod in [x for x in self.m.betriebsmittel if x.kategorie == "selektivmodul"]:
            kanaele = [self.pos[ab.bmk] for ab in self.m.absicherungen if ab.bmk.startswith(mod.bmk + ".")]
            if kanaele:
                xa, xe = self.x(kanaele[0].spalte) - 12, self.x(kanaele[-1].spalte) + 12
                b.rechteck(xa, 205, xe - xa, 28, strich=([3, 1], 0))
                b.text(xa, 235, f"{self.lokal[mod.bmk][1]}  {mod.bezeichnung}"[:70], 2.2, True)
                b.text(xa, 201, mod.artikel, 1.9)
        if f"kanal:{SAMMELMELDUNG}" in self.pos:           # Meldekontakte aller Module in Reihe, Ruhestrom
            xm = self.x(self.pos[SAMMELMELDUNG].spalte)
            sps = next((ab for ab in self.m.absicherungen if ab.gruppe == "SPS"), self.m.absicherungen[0])
            b.text(xm - 1, 266, f"24L+ {self.ref(self.pos.get(sps.bmk), a.kennung)}", 1.9, ausr="r")
            module = [x for x in self.m.betriebsmittel if x.kategorie == "selektivmodul"]
            y = 262
            for mod in module:
                b.linie(xm, y, xm, y - 4)
                sym_schliesser(b, xm, y - 4, 10)
                b.text(xm - 3, y - 10, f"{self.lokal[mod.bmk][1]} 13/14", 1.7, ausr="r")
                y -= 16
            b.linie(xm, y, xm, 200)
            b.text(xm + 1, y - 4, "geschlossen = in Ordnung", 1.6)
            self._sps_kasten(b, xm, 168, SAMMELMELDUNG, a.kennung, "0 = Störung", 34)
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
        alt = next(k for k, (an, lok) in self.lokal.items()
                   if an == a.kennung and self.m.bm(k).kategorie in ("sensor", "aktor"))
        g, ad, leiste = self.m.bm(alt), self.stil["ader"], self.stil["feldklemmleiste"]
        kl = self._feldklemmen(g.bmk)
        if len(kl) > 9:
            raise RegelFehler(f"{g.bmk}: mehr als 9 Feldklemmen passen nicht auf eine Seite")
        breit = 40 if len(kl) <= 5 else 34
        fa = self.pos.get(g.daten.get("absicherung", ""))
        y_k, y_dev = 170, 120
        kanal_von = {c.geraet_bmk: c for c in self.m.sps_kanaele}
        for i, k in enumerate(kl):
            x = self.x(self._feldspalte(i, len(kl)))
            if k.potential == "+24V":
                b.text(x - 1, 266, f"24L+ {self.ref(fa, a.kennung)}", 2, ausr="r")
                b.linie(x, 268, x, y_k + 1.1)
                farbe = ad["+24V"]
            elif k.potential == "0V":
                b.text(x - 1, 266, f"24M {self.ref(self.pos['24M'], a.kennung)}", 2, ausr="r")
                b.linie(x, 268, x, y_k + 1.1)
                farbe = ad["0V"]
            elif k.potential == "Kontakt":               # DO -> Koppelrelais-Spule, Kontakt 11/14 -> Feld
                kanal = kanal_von[k.signal]
                bauteil = k.ziel_innen.split(":")[0]
                lok = self.lokal.get(bauteil, ("", bauteil))[1]
                self._sps_kasten(b, x, 228, k.signal, a.kennung, f"{lok}:A1", breit)
                b.linie(x, 228, x, 222)
                b.linie(x, 222, x - 12, 222)
                b.linie(x - 12, 222, x - 12, 214)
                b.rechteck(x - 16, 208, 8, 6, 0.4)
                b.text(x - 17, 210, lok, 2.6, True, "r")
                b.text(x - 11, 215, "A1", 1.7)
                b.text(x - 11, 205.5, "A2", 1.7)
                b.linie(x - 12, 208, x - 12, 202)
                b.text(x - 12, 199, f"24M {self.ref(self.pos['24M'], a.kennung)}", 1.8, ausr="m")
                rueck = next((n for n, r in enumerate(kl, 1) if r.potential == "Kontakt-Rück"
                              and r.ziel_innen.split(":")[0] == bauteil), None)
                b.text(x + 1, 203, f"{leiste}:{rueck} (potentialfrei)" if rueck else f"24L+ {self.ref(fa, a.kennung)}",
                       1.8)
                b.linie(x, 201, x, 196)
                sym_schliesser(b, x, 196, 12)
                b.linie(x - 8, 211, x - 1.5, 190, 0.15, strich=([1, 1], 0))      # Wirkverbindung Spule-Kontakt
                b.text(x + 2, 194, "11", 1.7)
                b.text(x + 2, 185, "14", 1.7)
                b.linie(x, 184, x, y_k + 1.1)
                farbe = ad["+24V"]
            elif k.potential == "Kontakt-Rück":          # Kontaktwurzel 11 des Koppelrelais (potentialfrei)
                bauteil = k.ziel_innen.split(":")[0]
                lok = self.lokal.get(bauteil, ("", bauteil))[1]
                b.text(x - 1, 266, f"{lok}:11", 1.9, ausr="r")
                b.linie(x, 268, x, y_k + 1.1)
                farbe = ad["DO"]
            elif k.potential == "Bezug":                 # Rückleiter 4–20 mA auf den Kanal (M)
                modul, rest = k.ziel_innen.split(":", 1)
                karte = self.lokal.get(modul, ("", modul))
                b.text(x - 1, 266, f"={karte[0]}{karte[1]}:{rest} (M)", 1.9, ausr="r")
                b.linie(x, 268, x, y_k + 1.1)
                farbe = ad["AI"]
            else:
                kanal = kanal_von[k.signal]
                self._sps_kasten(b, x, 215, k.signal, a.kennung, f"{leiste}:{i + 1}", breit)
                b.linie(x, 215, x, y_k + 1.1)
                farbe = ad[kanal.art]
            b.text(x + 1, y_k + 12, farbe, 1.9)
            b.text(x + 1, y_k + 9, ad["querschnitt"], 1.9)
            sym_klemme(b, x, y_k, leiste, i + 1)
            b.linie(x, y_k - 1.1, x, y_dev)
            b.text(x + 0.8, y_dev + 1, k.ziel_aussen.split(":", 1)[1].split(" ")[0], 1.9)
        b.text(self.x(0) + 10, y_k - 0.8, leiste, 2.4, True, "r")
        xr = self.x(self._feldspalte(len(kl) - 1, len(kl))) if kl else self.x(6)
        b.linie(self.x(1) - 8, 150, xr + 8, 150, strich=([2, 1], 0))
        b.text(self.x(0) + 10, 151, f"-W1 {self.stil['feldkabel_typ']} {self._feldkabel_adern(g.bmk)}x0,75", 2.2, ausr="r")
        mss = (g.daten.get("leistung") or {}).get("mss")
        bauteile = [x for x in self.m.betriebsmittel if x.kategorie == "bauteil" and x.daten["eltern"] == g.bmk
                    and x.bmk != mss                                                # auf Seite Leistungsteil
                    and not any(k.ziel_innen.startswith(x.bmk + ":") for k in kl)]   # Relais schon gezeichnet
        for j, bt in enumerate(bauteile):                       # weitere Zusatzbauteile im Schrank
            b.rechteck(self.x(0) - 8, 200 - j * 12, 16, 8)
            b.text(self.x(0), 203 - j * 12, bt.daten["lokal"], 2.4, True, "m")
            b.text(self.x(0) - 8, 197 - j * 12, bt.funktion[:30], 1.7)
        b.rechteck(self.x(1) - 10, 60, xr - self.x(1) + 20, 60, strich=([4, 1, 1, 1], 0))
        b.text(self.x(1) - 8, 114, "Feld", 2.2)
        b.rechteck(self.x(1) - 8, y_dev - 30, xr - self.x(1) + 16, 30, 0.4)
        xm = (self.x(1) + xr) / 2
        b.text(xm, y_dev - 10, self.lokal[g.bmk][1], 4, True, "m")
        b.text(xm, y_dev - 16, g.bezeichnung[:70], 2.1, ausr="m")
        zusatz = f"Baustein {g.daten['typical']}   " if g.daten.get("typical") else ""
        strom = (f"I_N = {g.daten['leistung']['i_N_A']:g} A (230 V, siehe Seite 2)" if g.daten.get("leistung")
                 else f"I = {g.daten['i_A'] * 1000:.0f} mA")
        b.text(xm, y_dev - 21, f"{zusatz}{g.artikel}   {strom}", 2, ausr="m")

    def _leiter_ab(self, idx: int) -> list[str]:
        """Leiter, die Kettenglied idx oder ein späteres Glied braucht (in fester Reihenfolge)."""
        bedarf = set().union(*(self.netzbedarf[k] for k in self.netzkette[idx:])) if idx < len(self.netzkette) else set()
        return [lt for lt in LEITER_Y if lt in bedarf]

    def _kette(self, b: Blatt, a: Anlage):
        """Netzleiter auf einer Lastseite: hereinkommend links, weiterführend rechts (nur was später gebraucht wird)."""
        idx = self.netzkette.index(a.kennung)
        quelle, weiter = self._netz_nachbarn(a.kennung)
        weiterfuehren = self._leiter_ab(idx + 1)
        for lt in self._leiter_ab(idx):
            y = LEITER_Y[lt]
            potential_pfeil(b, X0 + 8, y, f"{lt} {self.ref(quelle, a.kennung)}", False)
            if lt in weiterfuehren:
                b.linie(X0 + 8, y, X1 - 30, y)
                potential_pfeil(b, X1 - 30, y, f"{lt} {self.ref(weiter, a.kennung)}")

    def _netz_nachbarn(self, kenn: str):
        idx = self.netzkette.index(kenn)
        quelle = self.pos["netz_aus"] if idx == 0 else self.pos[f"netz_aus:{self.netzkette[idx - 1]}"]
        weiter = self.pos[f"netz_ein:{self.netzkette[idx + 1]}"] if idx + 1 < len(self.netzkette) else None
        return quelle, weiter

    def _s_leistung(self, b: Blatt, a: Anlage):
        """Netzgerät 1~: L/N aus der Netzkette über Motorschutzschalter -Q1 auf Klemmen -X1, Leitung -W2."""
        alt = next(k for k, (an, lok) in self.lokal.items()
                   if an == a.kennung and self.m.bm(k).kategorie in ("sensor", "aktor"))
        g, ac, ad = self.m.bm(alt), self.stil["ader_ac"], self.stil["ader"]
        le = g.daten["leistung"]
        q, w = self.m.bm(le["mss"]), next(c for c in self.m.kabel if c.bmk == le["kabel"])
        x = self.x(3)
        self._kette(b, a)
        y_l = LEITER_Y[le.get("aussenleiter", "L1")]
        for d, (lt, y) in zip((-4, 4), (("L", y_l), ("N", LEITER_Y["N"]))):
            b.linie(X0 + 8, y, x + d, y)                       # Abgriff aus der Kette
            b.kreis(x + d, y, 0.6, True)
            b.linie(x + d, y, x + d, 222)
            b.rechteck(x + d - 1.2, 216, 2.4, 6)
            b.linie(x + d, 216, x + d, 131.1)
            b.text(x + d + 1, 160, ac["L"] if lt == "L" else ac["N"], 1.8)
            b.text(x + d + 1, 157, f"{w.querschnitt_mm2:g}".replace(".", ","), 1.8)
        b.linie(X0 + 8, LEITER_Y["PE"], x + 12, LEITER_Y["PE"])
        b.kreis(x + 12, 238, 0.6, True)
        b.linie(x + 12, 238, x + 12, 131.1)
        b.text(x + 13, 160, ac["PE"], 1.8)
        b.rechteck(x - 9, 210, 18, 18, strich=([1.5, 1], 0))
        b.text(x - 10, 222, "-Q1", 3, True, "r")
        b.text(x - 10, 218, f"Ir = {q.daten['i_r_A']:g} A".replace(".", ","), 2, ausr="r")
        b.text(x - 10, 214.5, f"13-14 {self.ref(Ort(a.kennung, 2, 6), a.kennung)}", 1.9, ausr="r")
        for d, (o, u) in zip((-4, 4), (("1", "2"), ("3", "4"))):          # Polnummern der benutzten Strompfade
            b.text(x + d + 1.4, 223, o, 1.6)
            b.text(x + d + 1.4, 213, u, 1.6)
        b.text(x - 9, 206.5, "1~: Strompfade nach Herstellerangabe", 1.6)
        for i, (d, pin) in enumerate(((-4, "L"), (4, "N"), (12, "PE")), 1):
            sym_klemme(b, x + d, 130, "-X1", i)
            b.linie(x + d, 128.9, x + d, 100)
            b.text(x + d + 0.8, 101, le["pins"].get(pin, pin), 1.8)
        b.text(x - 10, 129.2, "-X1", 2.4, True, "r")
        b.linie(x - 9, 112, x + 15, 118, 0.25)
        laenge = f" {w.laenge_m:g} m" if w.laenge_m else " (Länge lt. Feld)"
        b.text(x + 16, 119, f"-W2 {w.adern}G{w.querschnitt_mm2:g}{laenge}".replace(".", ","), 2.2)
        b.rechteck(x - 12, 75, 34, 25, 0.4)
        b.text(x + 5, 90, self.lokal[g.bmk][1], 3.5, True, "m")
        b.text(x + 5, 84, f"I_N = {le['i_N_A']:g} A", 2, ausr="m")
        # Meldung Hilfskontakt 13/14 des Motorschutzschalters
        xb = self.x(6)
        fa = self.pos.get(g.daten.get("absicherung", ""))
        b.text(xb - 1, 266, f"24L+ {self.ref(fa, a.kennung)}", 2, ausr="r")
        b.linie(xb, 268, xb, 205)
        sym_schliesser(b, xb, 205, 12)
        b.text(xb - 4, 199, "-Q1", 3, True, "r")
        b.text(xb - 4, 195.5, self.ref(self.pos[f"haupt:{le['mss']}"], a.kennung), 1.9, ausr="r")
        b.text(xb + 2, 203, "13", 1.9)
        b.text(xb + 2, 194, "14", 1.9)
        b.linie(xb, 193, xb, 172)
        b.text(xb + 1, 185, f"{ad['DI']} {ad['querschnitt']}", 1.9)
        for t in g.daten.get("quellsignale", {}):
            self._sps_kasten(b, xb, 140, t, a.kennung, "-Q1:14")
        b.linie(xb, 172, xb, 140 + 32)

    def _sps_kasten(self, b: Blatt, x: float, y: float, geraet: str, von: str, klemme: str, breit: float = 40):
        """SPS-Kasten im Hausstil: Kanal, Karte, Verweis, Adresse, Klemme, Funktionstext, Artikel."""
        k = next(c for c in self.m.sps_kanaele if c.geraet_bmk == geraet)
        karte_a, karte_bmk = self.lokal[k.modul_bmk]
        modul = self.m.bm(k.modul_bmk)
        h = breit / 2
        b.rechteck(x - h, y, breit, 32)
        zeilen = [(f"{k.art}{k.kanal}", 2.0, False), (f"={karte_a}{karte_bmk}", 2.6, True),
                  (self.ref(self.pos.get(f"karte:{geraet}"), von), 1.9, False), (k.adresse, 2.6, True),
                  (klemme, 1.9, False), (k.funktion[:34], 1.8, False)]
        for i, (t, g, fett) in enumerate(zeilen):
            b.text(x, y + 28 - i * 4.6, t, g, fett, "m")
            if i in (1, 3):
                b.linie(x - h, y + 26.3 - i * 4.6, x + h, y + 26.3 - i * 4.6, 0.15)
        b.text(x, y - 3, modul.artikel, 1.7, ausr="m")

    # ---- Motor ------------------------------------------------------------------
    def _motor(self, a: Anlage):
        alt_m = next(k for k, (an, lok) in self.lokal.items() if an == a.kennung and lok == "-M1")
        mot = self.m.bm(alt_m)
        kabel = next(c for c in self.m.kabel if c.bmk == mot.daten["kabel"])
        return mot, self.m.bm(mot.daten["mss"]), self.m.bm(mot.daten["schuetz"]), kabel

    def _s_motor_last(self, b: Blatt, a: Anlage):
        mot, q, k, w = self._motor(a)
        ac = self.stil["ader_ac"]
        x = self.x(4)
        self._kette(b, a)
        for d, (_lt, y) in zip((-6, 0, 6), (("L1", 262), ("L2", 256), ("L3", 250))):
            b.kreis(x + d, y, 0.6, True)
            b.linie(X0 + 8, y, x + d, y)
            b.linie(x + d, y, x + d, 222)
            b.rechteck(x + d - 1.2, 216, 2.4, 6)
            b.linie(x + d, 216, x + d, 190)
            sym_schliesser(b, x + d, 190, 12)
            b.linie(x + d, 178, x + d, 131.1)
        b.kreis(x + 12, 238, 0.6, True)
        b.linie(X0 + 8, 238, x + 12, 238)
        b.linie(x + 12, 238, x + 12, 131.1)
        b.rechteck(x - 10, 210, 20, 18, strich=([1.5, 1], 0))
        b.text(x - 11, 222, "-Q1", 3, True, "r")
        b.text(x - 11, 218, f"Ir = {q.daten['i_r_A']:g} A".replace(".", ","), 2, ausr="r")
        b.text(x - 11, 214.5, f"13-14 {self.ref(self.pos[f'kanal:{q.bmk}'], a.kennung)}", 1.9, ausr="r")
        b.text(x - 11, 186, "-K1", 3, True, "r")
        b.text(x - 11, 182.5, f"A1-A2 {self.ref(self.pos[f'kanal:{k.bmk}'], a.kennung)}", 1.9, ausr="r")
        b.linie(x - 6, 184, x + 6, 184, strich=([1, 1], 0))
        for i, d in enumerate((-6, 0, 6, 12), 1):
            sym_klemme(b, x + d, 130, "-X1", i)
            b.linie(x + d, 128.9, x + d, 100 if d < 12 else 90)
            b.text(x + d + 1, 160, ac["L"] if d < 12 else ac["PE"], 1.8)
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
        _mot, q, k, _w = self._motor(a)
        ad = self.stil["ader"]
        x = self.x(2)
        self._sps_kasten(b, x, 215, k.bmk, a.kennung, "-K1:A1")
        b.linie(x, 215, x, 156)
        b.text(x + 1, 190, f"{ad['DO']} {ad['querschnitt']}", 1.9)
        b.rechteck(x - 4, 150, 8, 6, 0.4)
        b.text(x - 6, 152, "-K1", 3, True, "r")
        b.linie(x, 150, x, 95)
        potential_pfeil(b, X1 - 30, 95, f"24M {self.ref(self.pos['24M'], a.kennung)}")
        b.text(x + 1, 120, f"{ad['0V']} {ad['querschnitt']}", 1.9)
        b.linie(x, 95, X1 - 30, 95)
        for i, kt in enumerate(("1-2", "3-4", "5-6")):
            b.text(x - 6, 88 - i * 3.5, f"{kt}  {self.ref(self.pos[f'haupt:{k.bmk}'], a.kennung)}", 1.9)
        xb = self.x(6)
        fa = self.pos.get(q.daten.get("absicherung", ""))
        b.text(xb - 1, 266, f"24L+ {self.ref(fa, a.kennung)}", 2, ausr="r")
        b.linie(xb, 268, xb, 205)
        sym_schliesser(b, xb, 205, 12)
        b.text(xb - 4, 199, "-Q1", 3, True, "r")
        b.text(xb - 4, 195.5, self.ref(self.pos[f"haupt:{q.bmk}"], a.kennung), 1.9, ausr="r")
        b.text(xb + 2, 203, "13", 1.9)
        b.text(xb + 2, 194, "14", 1.9)
        b.linie(xb, 193, xb, 172)
        self._sps_kasten(b, xb, 140, q.bmk, a.kennung, "-Q1:14")
        b.linie(xb, 172, xb, 140 + 32)

    # ---- SPS -------------------------------------------------------------------
    def _karten(self) -> list[Betriebsmittel]:
        """E/A-Karten in Steckplatzreihenfolge (Reihenfolge im Planmodell).  # ANNAHME A29"""
        return [b for b in self.m.betriebsmittel if b.kategorie in ("sps_di", "sps_do", "sps_ai", "sps_ao")]

    def _signalklemme(self, signal: str) -> str:
        """Feldklemme (Hausstil-Nummerierung je Anlage) des Signalleiters eines SPS-Kanals."""
        nr_je: dict[tuple[str, str], int] = {}
        for k in self.m.klemmen:
            geraet = k.ziel_aussen.split(":")[0]
            if geraet not in self.lokal or k.leiste != "-X1":
                continue
            kenn = self.lokal[geraet][0]
            leiste = self.stil["feldklemmleiste"]
            nr_je[(kenn, leiste)] = nr_je.get((kenn, leiste), 0) + 1
            if k.signal == signal:
                return f"={kenn}{leiste}:{nr_je[(kenn, leiste)]}"
        return ""

    def _s_cpu(self, b: Blatt, a: Anlage):
        cpu = self.m.bm("-A1")
        karten = self._karten()
        b.text(X0 + 6, 266, f"={a.kennung}{self.lokal['-A1'][1]}  {cpu.bezeichnung}  ({cpu.artikel})", 3, True)
        b.text(X0 + 6, 261, f"Steckplatz 0 · {len(karten)} E/A-Karten", 2.3)
        b.text(X0 + 6, 256.5, self._versorgung_karte("-A1", a.kennung), 2.3)
        zeilen = [("0", f"={a.kennung}{self.lokal['-A1'][1]}", "CPU", cpu.artikel, "–", "–", "–", "")]
        summe_b = summe_g = 0
        for slot, mod in enumerate(karten, 1):
            belegt = len([k for k in self.m.sps_kanaele if k.modul_bmk == mod.bmk])
            gesamt = int(self.m.artikel.get(mod.artikel, {}).get("kanaele", belegt))
            summe_b, summe_g = summe_b + belegt, summe_g + gesamt
            kenn, lok = self.lokal[mod.bmk]
            bereich = mod.daten.get("bytebereich")
            zeilen.append((str(slot), f"={kenn}{lok}", mod.kategorie[4:].upper(), mod.artikel, f"{belegt} / {gesamt}",
                           str(gesamt - belegt), f"{bereich[0]}–{bereich[1]}" if bereich else "",
                           self.ref(self.pos.get(f"modul:{mod.bmk}"), a.kennung)))
        zeilen.append(("Σ", "", "", "", f"{summe_b} / {summe_g}", str(summe_g - summe_b), "", ""))
        tabelle(b, ["Steckplatz", "Karte", "Art", "Artikel", "Kanäle belegt / gesamt", "Reserve", "Byte", "Verweis"],
                zeilen, [25, 40, 18, 45, 50, 25, 25, 30], y_start=248, fett={len(zeilen) - 1})

    def _versorgung_karte(self, modul_bmk: str, kennung: str) -> str:
        teile = []
        for ab in self.m.absicherungen:
            if modul_bmk in ab.verbraucher:
                art = "Lastspannung 2L+" if ab.gruppe == "DO-Last" else "Versorgung 1L+"
                teile.append(f"{art} {self.ref(self.pos.get(ab.bmk), kennung)}")
        teile.append(f"M {self.ref(self.pos.get('24M'), kennung)}")
        return " · ".join(teile)

    def _s_karte(self, modul_bmk: str):
        def zeichne(b: Blatt, a: Anlage):
            mod = self.m.bm(modul_bmk)
            kanaele = {k.kanal: k for k in self.m.sps_kanaele if k.modul_bmk == modul_bmk}
            adressen = mod.daten.get("adressen", [])
            gesamt = max(len(adressen), int(self.m.artikel.get(mod.artikel, {}).get("kanaele", 0)), len(kanaele))
            art = mod.kategorie[4:].upper()
            slot = next((i for i, x in enumerate(self._karten(), 1) if x.bmk == modul_bmk), "?")
            b.text(X0 + 6, 266, f"={a.kennung}{self.lokal[modul_bmk][1]}  {mod.bezeichnung}  ({mod.artikel})", 3, True)
            bereich = mod.daten.get("bytebereich")
            b.text(X0 + 6, 261, f"Steckplatz {slot} (Übersicht {self.ref(Ort(self.stil['kartenanlagen']['CPU'], 1, 0), a.kennung)})"
                   f" · Belegt {len(kanaele)} von {gesamt} Kanälen, Reserve {gesamt - len(kanaele)}"
                   + (f" · Byte {bereich[0]}–{bereich[1]}" if bereich else ""), 2.3)
            b.text(X0 + 6, 256.5, self._versorgung_karte(modul_bmk, a.kennung), 2.3)
            belegt, reserve = [], []
            for nr in range(gesamt):
                k = kanaele.get(nr)
                adr = adressen[nr] if nr < len(adressen) else ""
                if k is None:
                    reserve.append((f"{art}{nr}", adr, "", "", "", "Reserve"))
                    continue
                if k.anschluss:                                   # Kanal endet im Schrank (Relais, Hilfskontakt)
                    geraet, pin = k.anschluss.rsplit(":", 1)
                    zeile = (self.voll(geraet) + f":{pin}", "im Schrank")
                else:
                    zeile = (self.voll(k.geraet_bmk), self._signalklemme(k.geraet_bmk) or "–")
                belegt.append((f"{k.art}{k.kanal}", k.adresse, self.ref(self.pos.get(f"kanal:{k.geraet_bmk}"), a.kennung),
                               zeile[0], zeile[1], _kuerze(k.funktion, 70)))
            kopf = ["Kanal", "Adresse", "Verweis", "Gerät / Anschluss", "Klemme", "Funktionstext"]
            breiten = [22, 30, 30, 55, 40, 150]
            tabelle(b, kopf, belegt, breiten, y_start=248)
            if reserve:                                            # Reserve abgesetzt und grau
                y = 248 - 7 - len(belegt) * 5.5 - 2              # Abstand, damit die Trennlinie frei liegt
                b.c.setStrokeGray(0.6)
                b.linie(X0 + 4, y + 5, X1 - 4, y + 5)                # Trennlinie belegt | Reserve
                b.c.setFillGray(0.5)
                tabelle(b, [], reserve, breiten, y_start=y + 7)
                b.c.setFillGray(0)
                b.c.setStrokeGray(0)
        return zeichne

    # ---- Listen ------------------------------------------------------------------
    def _motoren(self) -> set[str]:
        return {self.lokal[b.bmk][0] for b in self.m.betriebsmittel if b.kategorie == "motor"}

    def _feldgeraete(self) -> list[str]:
        return [b.bmk for b in self.m.betriebsmittel if b.kategorie in ("sensor", "aktor")]

    def _feldlaenge(self, alt: str) -> str:
        """Länge der Feldleitung aus dem Projektmodell (laenge_m je Feldgerät), sonst „nach Feldmaß“ (A35)."""
        laenge = self.m.bm(alt).daten.get("laenge_m")
        return f"{_zahl(float(laenge))} m" if laenge else NACH_FELDMASS

    def _feldkabel_adern(self, alt: str) -> int:
        n = len([k for k in self.m.klemmen if k.ziel_aussen.startswith(alt + ":")])
        return next((x for x in self.stil["feldkabel_adern"] if x >= n), n)

    def _kabelzeilen(self):
        z = []
        for alt in self._feldgeraete():
            kenn, lok = self.lokal[alt]
            z.append((f"={kenn}-W1", f"{self.stil['feldkabel_typ']} {self._feldkabel_adern(alt)}x0,75",
                      f"={kenn}{self.stil['feldklemmleiste']}", f"={kenn}{lok}", self._feldlaenge(alt),
                      self.ref(Ort(kenn, 1, 4), "")))
        for w in self.m.kabel:
            kenn, lok = self.lokal[w.bmk]
            ziel = self.lokal.get(w.nach, (kenn, w.nach))[1]
            z.append((f"={kenn}{lok}", f"{w.adern}G{_zahl(w.querschnitt_mm2)} mm² ({w.artikel})",
                      f"={kenn}-X1", f"={kenn}{ziel}", f"{_zahl(w.laenge_m)} m",
                      self.ref(self.pos.get(w.bmk), "")))
        return z

    def _s_kabel(self, b: Blatt, a: Anlage, idx: int):
        tabelle(b, ["Kabelnummer", "Kabeltyp", "Quelle", "Ziel", "Länge", "Verweis"],
                self._kabelzeilen()[idx * ZEILEN_JE_LISTENSEITE:(idx + 1) * ZEILEN_JE_LISTENSEITE],
                [50, 90, 80, 80, 30, 30])

    POTENTIAL: ClassVar[dict[str, str]] = {"+24V": "24L+", "0V": "24M", "Signal": "Signal", "Kontakt": "Kontakt 14",
                                           "Kontakt-Rück": "Kontakt 11",
                 "Bezug": "M (Analog)"}
    SCHUETZ_ANSCHLUSS: ClassVar[dict[str, str]] = {"U": "2", "V": "4", "W": "6"}

    def _klemmenzeilen(self):
        z = []
        nr_je: dict[tuple[str, str], int] = {}
        for k in self.m.klemmen:
            geraet = k.ziel_aussen.split(":")[0]
            if geraet not in self.lokal:
                continue
            kenn, lok = self.lokal[geraet]
            motor = k.leiste != "-X1"                 # Motorklemmen (U/V/W/PE)
            leiste = "-X1" if motor else self.stil["feldklemmleiste"]
            nr_je[(kenn, leiste)] = nr_je.get((kenn, leiste), 0) + 1
            if motor:
                if k.potential in self.SCHUETZ_ANSCHLUSS:
                    ziel = f"-K1:{self.SCHUETZ_ANSCHLUSS[k.potential]}"
                elif k.potential in ("L", "N"):                     # Netzgerät über Motorschutzschalter
                    ziel = f"-Q1:{k.ziel_innen.split(':')[-1]}"
                else:
                    ziel = f"PE ={self.EIN}"
                seite = self.ref(Ort(kenn, 1, 4) if kenn in self._motoren() else Ort(kenn, 2, 3), "")
            else:
                eigene = [x.nr for x in self._feldklemmen(geraet)]
                seite = self.ref(Ort(kenn, 1, self._feldspalte(eigene.index(k.nr), len(eigene))), "")
                if k.potential == "0V":
                    ziel = f"24M {self.ref(self.pos['24M'], '')}"
                else:
                    ziel = k.ziel_innen
                    for alt, (an2, lok2) in self.lokal.items():
                        if ziel.startswith(alt + ":") or ziel == alt:
                            ziel = ziel.replace(alt, f"={an2}{lok2}", 1)
                            break
            z.append((f"={kenn}{leiste}:{nr_je[(kenn, leiste)]}", self.POTENTIAL.get(k.potential, k.potential),
                      ziel, f"{lok}:{k.ziel_aussen.split(':', 1)[1]}", seite))
        return z

    def _klemmenplan(self) -> tuple[list[tuple], set[int]]:
        """Klemmenplan je Leiste (sortiert nach Anlage/Leiste), seitenweise aufgefüllt: Leistenkopf nie allein am
        Seitenende, auf Folgeseiten als „(Fortsetzung)“ wiederholt. -> (Zeilen, Indizes der Kopfzeilen)."""
        je_leiste: dict[str, list] = {}
        for z in self._klemmenzeilen():
            je_leiste.setdefault(z[0].split(":")[0], []).append(z)
        zeilen: list[tuple] = []
        kopf: set[int] = set()
        n = ZEILEN_JE_LISTENSEITE
        for leiste in sorted(je_leiste):
            klemmen = je_leiste[leiste]
            if len(zeilen) % n == n - 1:                         # Kopf wäre letzte Zeile -> neue Seite
                zeilen.append(("", "", "", "", ""))
            kopf.add(len(zeilen))
            zeilen.append((f"Klemmleiste {leiste}", f"{len(klemmen)} Klemmen", "", "", ""))
            for z in klemmen:
                if len(zeilen) % n == 0:                         # Seitenwechsel mitten in der Leiste
                    kopf.add(len(zeilen))
                    zeilen.append((f"Klemmleiste {leiste} (Fortsetzung)", "", "", "", ""))
                zeilen.append(z)
        return zeilen, kopf

    def _s_klemmen(self, b: Blatt, a: Anlage, idx: int):
        zeilen, kopf = self._klemmenplan()
        von = idx * ZEILEN_JE_LISTENSEITE
        tabelle(b, ["Klemme", "Potential", "Ziel innen (Schrank)", "Ziel außen (Feld)", "Verweis"],
                zeilen[von:von + ZEILEN_JE_LISTENSEITE], [55, 30, 110, 80, 30],
                fett={i - von for i in kopf if von <= i < von + ZEILEN_JE_LISTENSEITE})

    def _stl_zeilen(self):
        ort = self.m.projekt.get("ort", "")
        artikel = self.m.artikel
        zeilen = []
        for bm in self.m.betriebsmittel:
            if bm.bmk not in self.lokal or bm.kategorie in ("selektivkanal", "meldung"):
                continue
            kenn, lok = self.lokal[bm.bmk]
            art = artikel.get(bm.artikel, {"hersteller": "", "bezeichnung": "Beistellung Kunde"})
            menge = ((f"{_zahl(bm.daten['laenge_m'])} m" if bm.daten.get("laenge_m") else NACH_FELDMASS)
                     if bm.kategorie == "kabel" else "1 Stk")
            zeilen.append((f"={kenn}", ort, lok, menge, art.get("hersteller", ""), art.get("artikelnummer") or bm.artikel,
                           _kuerze(art["bezeichnung"], 110)))
        klemmen: dict[tuple[str, str, str], int] = {}
        for k in self._klemmenzeilen():
            anlage, rest = k[0][1:].split("-", 1)
            leiste = "-" + rest.split(":")[0]
            key = "RK-PE" if k[1] == "PE" else ("RK-4" if leiste == "-X1" else "RK-2.5")
            klemmen[(anlage, leiste, key)] = klemmen.get((anlage, leiste, key), 0) + 1
        for (anlage, leiste, key), n in klemmen.items():
            a = artikel.get(key, {"hersteller": "", "bezeichnung": "Reihenklemme"})
            zeilen.append((f"={anlage}", ort, leiste, f"{n} Stk", a.get("hersteller", ""), key, _kuerze(a["bezeichnung"], 110)))
        for alt in self._feldgeraete():
            kenn = self.lokal[alt][0]
            typ = f"{self.stil['feldkabel_typ']} {self._feldkabel_adern(alt)}x0,75"
            zeilen.append((f"={kenn}", ort, "-W1", self._feldlaenge(alt), "–", typ, "Feldleitung geschirmt"))
        return [(i + 1, *z) for i, z in enumerate(zeilen)]

    def _s_stueckliste(self, b: Blatt, a: Anlage, idx: int):
        tabelle(b, ["Pos.", "=Anlage", "+Ort", "-BMK", "Menge", "Hersteller", "Artikel", "Benennung"],
                self._stl_zeilen()[idx * ZEILEN_JE_LISTENSEITE:(idx + 1) * ZEILEN_JE_LISTENSEITE],
                [14, 28, 20, 20, 18, 38, 38, 160])

    def _summenzeilen(self) -> list[tuple]:
        """Summenstückliste: je Artikel eine Zeile mit Gesamtmenge; Beistellungen am Ende („nicht bestellen“)."""
        summe: OrderedDict[str, list] = OrderedDict()
        for _, _, _, _lok, menge, hersteller, artikel, benennung in self._stl_zeilen():
            schluessel = f"{artikel}|{benennung}" if artikel == "KUNDE" else artikel
            e = summe.setdefault(schluessel, [0.0, 0, "", hersteller, benennung, artikel])
            if menge.endswith(" Stk"):
                e[0] += float(menge.split()[0])
                e[2] = "Stk"
            elif menge.endswith(" m"):
                e[0] += float(menge.split()[0].replace(",", "."))
                e[2] = "m"
            else:                                       # nach Feldmaß
                e[1] += 1
        kauf: list[tuple] = []
        beistellung: list[tuple] = []
        for menge, offen, einheit, hersteller, benennung, artikel in summe.values():
            text = f"{_zahl(menge)} {einheit}" if einheit else ""
            if offen:
                text = (text + " + " if text else "") + f"{offen} Stk {NACH_FELDMASS}"
            (beistellung if artikel == "KUNDE" else kauf).append((text, hersteller, artikel, benennung))
        zeilen = [(i, *z) for i, z in enumerate(kauf, 1)]
        if beistellung:
            zeilen.append(("", "Beistellung – nicht bestellen", "", "", ""))
            zeilen += [("", *z) for z in beistellung]
        return zeilen

    def _s_summe(self, b: Blatt, a: Anlage, idx: int):
        tabelle(b, ["Pos.", "Menge", "Hersteller", "Artikel", "Benennung"],
                self._summenzeilen()[idx * ZEILEN_JE_LISTENSEITE:(idx + 1) * ZEILEN_JE_LISTENSEITE],
                [14, 50, 40, 45, 200])

    def _auslegungszeilen(self) -> list[tuple]:
        """Auslegungsnachweis (mehrseitig), gegliedert: Abgänge, Bilanz, Hausvorgaben/-stil, Annahmen, offene Fragen,
        nicht geprüft / nicht freigegeben."""
        bil = self.m.bilanz
        z: list[tuple] = [("1 Abgänge 24 V DC", "", "", "", ""), ("Abgang", "Gruppe", "Σ I [A]", "Sicherung [A]", "")]
        z += [(f"={self.VT}{self.lokal[ab.bmk][1]}", ab.gruppe, _zahl(round(ab.i_gruppe_A, 3)), _zahl(ab.i_nenn_A), "")
              for ab in self.m.absicherungen]
        z += [("", ), ("2 Strombilanz", )]
        z += [(f"Summenstrom 24 V: Σ I = {_zahl(bil['i_summe_A'])} A; Bedarf mit Gleichzeitigkeit g = "
               f"{_zahl(bil['gleichzeitigkeit'])} und Reserve {_zahl(bil['reserve'])} = {_zahl(bil['i_bedarf_A'])} A",),
              (f"Netzteil {bil['netzteil']} ({_zahl(bil['i_nenn_A'])} A, Auslastung {bil['auslastung']:.0%})",)]
        if self.m.kabel:
            z.append((f"Motoren Σ I_N = {_zahl(bil['i_motoren_A'])} A; Strom je Außenleiter höchstens "
                      f"{_zahl(bil['i_400V_max_A'])} A",))
            from .konsistenz import _schutzorgan_je_kabel
            schutz = _schutzorgan_je_kabel(self.m)
            z += [("",), ("2a Leitungen Motor-/Leistungsabgänge (Quelle: Tabelle i_z_A der Hausvorgabe, nicht freigegeben)",),
                  ("Kabel", "Querschnitt", "I_B [A]", "I_n = I_r [A]", "I_z·f [A]", "ΔU [%]")]
            for kab in self.m.kabel:
                kenn, lok = self.lokal.get(kab.bmk, ("", kab.bmk))
                mss = schutz.get(kab.bmk)
                i_r = self.m.bm(mss).daten.get("i_r_A") if mss else None
                z.append((f"={kenn}{lok} ({_zahl(kab.laenge_m)} m)", f"{kab.adern}G{_zahl(kab.querschnitt_mm2)} mm²",
                          _zahl(kab.i_b_A), _zahl(float(i_r)) if i_r is not None else "–", _zahl(kab.i_z_A),
                          _zahl(round(kab.du_prozent, 2))))
        gruppen: dict[str, list[str]] = {"3 Hausvorgaben und Hausstil": [], "4 Annahmen": [], "5 Offene Fragen": [],
                                         "6 Nicht geprüft / nicht freigegeben": []}
        gruppen["3 Hausvorgaben und Hausstil"] += [f"Hausstil: {w}" for w in self.stil["quelle"].values()]
        gruppen["3 Hausvorgaben und Hausstil"] += [f"Achtung {w}" for w in self.stil.get("warnungen", [])]
        for w in self.m.warnungen:
            w = re.sub(r"\s*\((leitungen|versorgung_24V|sps)\.[\w.]+\)", "", w)        # keine internen Schlüssel
            if w.startswith("Annahme der Aufbereitung:"):
                gruppen["4 Annahmen"].append(w.split(":", 1)[1].strip())
            elif w.startswith("Offene Frage:"):
                gruppen["5 Offene Fragen"].append(w.split(":", 1)[1].strip())
            elif w.startswith(("Hausregel", "Regressionsfall", "Hausregeln bilden")):
                gruppen.setdefault("9 Angewendete Hausregeln (Lernschleife)", []).append(w)
            elif "nach Hausvorgabe" in w:
                gruppen["3 Hausvorgaben und Hausstil"].append(w)
            else:
                gruppen["6 Nicht geprüft / nicht freigegeben"].append(w)
        from .konsistenz import MINUTEN_JE, bericht_text, kennzahlen, pruefe_plan  # frisch am Planmodell geprüft
        gruppen["7 Prüfbericht (Konsistenz)"] = bericht_text(pruefe_plan(self.m))
        k = kennzahlen(self.m, sum(len(a.seiten) for a in self.anlagen.values()))
        gruppen["8 Kennzahlen (Zeitansatz je Element: " + ", ".join(f"{n} {_zahl(v)} min" for n, v in MINUTEN_JE.items())
                + " – Annahme A36)"] = [f"{n}: {_zahl(v)}" for n, v in k.items()]
        for titel, eintraege in gruppen.items():
            z.append(("",))
            if len(z) % ZEILEN_JE_LISTENSEITE == ZEILEN_JE_LISTENSEITE - 1:      # Überschrift nie allein am Seitenende
                z.append(("",))
            z += [(titel,)] + [(f"• {e}",) for e in (eintraege or ["keine"])]
        return z

    def _s_auslegung(self, b: Blatt, a: Anlage, idx: int):
        zeilen = self._auslegungszeilen()[idx * ZEILEN_JE_LISTENSEITE:(idx + 1) * ZEILEN_JE_LISTENSEITE]
        fett = {i for i, z in enumerate(zeilen) if z and re.match(r"\d\w? \w|Abgang$|Kabel$", str(z[0]))}
        tabelle(b, [], zeilen, [55, 40, 30, 35, 30, 30], y_start=YL - 5, fett=fett, linien=False)

def kennzeichne(m: Planmodell, stil: dict | None = None) -> dict[str, list[str]]:
    """Kennzeichen im Hausstil (Anlage je Funktion + lokales BMK) für das Planmodell festlegen.

    Läuft im Planungsablauf VOR dem Speichern von planmodell.json (siehe cli.generieren); die Ausgabe und der
    EPLAN-Adapter lesen danach nur noch `m.kennzeichen`.  # ANNAHME A27
    """
    m.kennzeichen = {}
    return {k: list(v) for k, v in Hausplan(m, stil or lade_hausstil(None)).lokal.items()}


def erzeuge_hausstil_pdf(m: Planmodell, pfad: str, stil: dict | None = None) -> list[tuple[str, int, str]]:
    stil = stil or lade_hausstil(None)
    hp = Hausplan(m, stil)
    folge = hp.seitenfolge()
    c = Canvas(pfad, pagesize=landscape(A3), invariant=1)
    c.setTitle(f"Stromlaufplan {m.projekt.get('nummer', '')}")
    b = Blatt(c)
    fehler = hat_pruefbericht_fehler(m)
    for i, (a, nr, titel, zeichner) in enumerate(folge):
        vorher = f"={folge[i - 1][0].kennung}/{folge[i - 1][1]}" if i else ""
        nachher = f"={folge[i + 1][0].kennung}/{folge[i + 1][1]}" if i + 1 < len(folge) else ""
        hp.rahmen(b, a, nr, titel, vorher, nachher)
        zeichner(b, a)
        if fehler:
            stempel_nicht_fertigung(b)
        c.showPage()
    c.save()
    return [(a.kennung, nr, t) for a, nr, t, _ in folge]
