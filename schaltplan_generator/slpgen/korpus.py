"""Synthetischer Testkorpus im Hausstil – Stromlaufplan-PDFs ohne Kunden- oder Firmendaten.

Zweck: Lern- und Auswertefunktionen (struktur, analysieren, später „lernen“) reproduzierbar
testen, ohne echte Pläne ins Repository zu legen. Aufbau und Konventionen sind dem
ausgewerteten Hausstandard nachempfunden (Anlage je Funktion, Spalten 0–9, Zeichnungsnummer
im Schriftfeld, SPS-Adressen E/EW, Aderkennzeichnung Farbe + Querschnitt), alle Namen sind neutral.

Eingebauter Trend (bekannte Sollwerte für Tests): Feldklemmleiste bis WECHSELJAHR-1 „-X20“,
ab WECHSELJAHR „-X10“.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path

from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

WECHSELJAHR = 2025
SPALTEN = 10                       # Spaltenleiste 0..9


@dataclass
class KorpusPlan:
    datei: str
    projekt: str
    jahr: int
    feldleiste: str
    anlagen: list[str]
    typicals: dict[str, list[str]] = field(default_factory=dict)   # Typical-Name -> Anlagen


def _rahmen(c: Canvas, projekt: str, anlage: str, art: str, titel: str, datum: str):
    w, h = landscape(A3)
    c.setLineWidth(0.5)
    c.rect(20 * mm, 10 * mm, w - 30 * mm, h - 20 * mm)
    spw = (w - 30 * mm) / SPALTEN
    c.setFont("Helvetica", 7)
    for i in range(SPALTEN):
        c.drawCentredString(20 * mm + (i + 0.5) * spw, h - 15 * mm, str(i))
    y = 18 * mm
    c.setFont("Helvetica", 7)
    c.drawString(25 * mm, y, f"Datum {datum}   Bearb. Muster   Rev. 00")
    c.drawString(120 * mm, y, titel)
    c.drawString(220 * mm, y, f"Zeichnung-Nr. {projekt}-{anlage}-0-{art}-00")
    c.drawString(330 * mm, y, f"= {anlage}   + S01   & {art}   Seite 1")


def _verbindung(c: Canvas, x: float, y1: float, y2: float, farbe: str, qs: str):
    c.line(x * mm, y1 * mm, x * mm, y2 * mm)
    c.setFont("Helvetica", 5)
    c.drawString((x + 1) * mm, ((y1 + y2) / 2) * mm, farbe)
    c.drawString((x + 1) * mm, ((y1 + y2) / 2 - 2.5) * mm, qs)


def _sps_kasten(c: Canvas, x: float, y: float, karte: str, adresse: str, klemme: str, text: str):
    c.rect((x - 18) * mm, y * mm, 36 * mm, 18 * mm)
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(x * mm, (y + 13) * mm, karte)
    c.drawCentredString(x * mm, (y + 8) * mm, adresse)
    c.setFont("Helvetica", 5)
    c.drawCentredString(x * mm, (y + 4) * mm, klemme)
    c.drawCentredString(x * mm, (y + 1) * mm, text[:40])


def _seite_zaehler_di(c, anlage, leiste, n_kanal):
    """Typical Zähler DI: Zählimpuls + Drahtbruchmeldung, geschirmte Feldleitung."""
    _sps_kasten(c, 80, 190, "=810-K1", f"E{n_kanal // 8}.{n_kanal % 8}", f"{leiste}:2",
                f"Betriebsmeldung Zähler {anlage} Zählimpuls")
    _sps_kasten(c, 160, 190, "=810-K1", f"E{(n_kanal + 1) // 8}.{(n_kanal + 1) % 8}", f"{leiste}:3",
                f"Störmeldung Zähler {anlage} Drahtbruch")
    for i, (x, farbe) in enumerate(((50, "DBU"), (80, "DBU"), (160, "DBU"), (200, "DBU/WH")), 1):
        _verbindung(c, x, 170, 130, farbe, "0,75")
        c.circle(x * mm, 128 * mm, 1.2 * mm)
        c.drawString((x + 2) * mm, 127 * mm, str(i))
    c.setFont("Helvetica", 7)
    c.drawString(30 * mm, 127 * mm, leiste)
    c.drawString(30 * mm, 112 * mm, "-W1 LIYCY 7x0,75")
    c.drawString(30 * mm, 80 * mm, "-P1 Zähler 24V DC Puls GND")
    c.drawString(120 * mm, 100 * mm, "Widerstand 2,2KΩ im Leerstecker")


def _seite_messstelle_ai(c, anlage, leiste, n_wort):
    """Typical Messstelle AI: 2-Leiter 4–20 mA."""
    _sps_kasten(c, 120, 190, "=830-K1", f"EW{n_wort}", f"{leiste}:2", f"Messwert 4I20 {anlage}")
    for i, (x, farbe) in enumerate(((90, "DBU"), (120, "WH")), 1):
        _verbindung(c, x, 170, 130, farbe, "0,75")
        c.circle(x * mm, 128 * mm, 1.2 * mm)
        c.drawString((x + 2) * mm, 127 * mm, str(i))
    c.setFont("Helvetica", 7)
    c.drawString(30 * mm, 127 * mm, leiste)
    c.drawString(30 * mm, 112 * mm, "-W1 JE-Y(ST)Y 2x2x0,8")
    c.drawString(30 * mm, 80 * mm, "-BT1 Messumformer 4-20mA")


def _seite_pumpe(c, anlage, leiste):
    """Typical Pumpe: Motorschutzschalter, Freigabe über Koppelrelais, Stellsignal, Meldungen."""
    _sps_kasten(c, 200, 200, "=840-K1", "AW256", f"{leiste}:5", f"Stellsignal 4I20 {anlage}")
    _sps_kasten(c, 260, 200, "=820-K1", "A1.0", "-K1:A1", f"Freigabe {anlage}")
    _sps_kasten(c, 320, 200, "=810-K1", "E4.0", f"{leiste}:7", f"Betrieb {anlage}")
    for x, farbe, qs in ((60, "BK", "2,5"), (70, "BK", "2,5"), (80, "BK", "2,5"), (200, "WH", "0,75"),
                         (320, "DBU", "0,75")):
        _verbindung(c, x, 180, 130, farbe, qs)
    c.setFont("Helvetica", 7)
    c.drawString(40 * mm, 160 * mm, "-Q1 Motorschutzschalter 13/14")
    c.drawString(250 * mm, 160 * mm, "-K1 Koppelrelais 24V DC")
    c.drawString(30 * mm, 127 * mm, leiste)
    c.drawString(30 * mm, 112 * mm, "-W1 ÖLFLEX 3G1,5")
    c.drawString(30 * mm, 80 * mm, "-M1 Pumpe 230V")


def _seite_einspeisung(c):
    for x, farbe in ((60, "BK"), (75, "LBU"), (90, "GNYE")):
        _verbindung(c, x, 220, 120, farbe, "1,5")
    c.setFont("Helvetica", 7)
    c.drawString(40 * mm, 200 * mm, "-F1 LS B10")
    c.drawString(40 * mm, 110 * mm, "-X1   -W1 NYY-J 3x2,5")


def _seite_24v(c):
    for x, farbe in ((100, "DBU"), (120, "DBU/WH")):
        _verbindung(c, x, 220, 120, farbe, "1,5")
    c.setFont("Helvetica", 7)
    c.drawString(80 * mm, 200 * mm, "-T1 Netzteil 24V/4A")
    c.drawString(80 * mm, 110 * mm, "-XDC")


def erzeuge_korpus(ordner: str | Path, anzahl: int = 10, seed: int = 1,
                   jahre: tuple[int, int] = (2021, 2026)) -> list[KorpusPlan]:
    """Erzeugt `anzahl` Pläne; Jahre gleichmäßig über den Bereich verteilt. Deterministisch über `seed`."""
    rnd = random.Random(seed)
    ordner = Path(ordner)
    ordner.mkdir(parents=True, exist_ok=True)
    plaene = []
    for i in range(anzahl):
        jahr = jahre[0] + round(i * (jahre[1] - jahre[0]) / max(1, anzahl - 1))
        projekt = f"P{1000 + i}"
        datum = f"{rnd.randint(1, 28):02d}.{rnd.randint(1, 12):02d}.{jahr}"
        leiste = "-X20" if jahr < WECHSELJAHR else "-X10"
        n_di, n_ai = rnd.randint(2, 6), rnd.randint(1, 3)
        mit_pumpe = rnd.random() < 0.6
        seiten = [("AC230.01", "Einspeisung 230V", _seite_einspeisung),
                  ("DC24.01", "24V DC Erzeugung", _seite_24v)]
        typ = {"zaehler_di": [], "messstelle_ai": [], "pumpe": []}
        for k in range(n_di):
            a = f"ZD{k + 1:02d}"
            typ["zaehler_di"].append(a)
            seiten.append((a, f"Zähler {a}", lambda c, a=a, k=k: _seite_zaehler_di(c, a, leiste, 2 * k + 1)))
        for k in range(n_ai):
            a = f"MA{k + 1:02d}"
            typ["messstelle_ai"].append(a)
            seiten.append((a, f"Messstelle {a}", lambda c, a=a, k=k: _seite_messstelle_ai(c, a, leiste, 4 + 2 * k)))
        if mit_pumpe:
            typ["pumpe"].append("PU01")
            seiten.append(("PU01", "Pumpe PU01", lambda c: _seite_pumpe(c, "PU01", leiste)))
        seiten.append(("789", "Reserve", lambda c: None))

        datei = f"{projekt}_{jahr}.pdf"
        c = Canvas(str(ordner / datei), pagesize=landscape(A3))
        c.setCreator("slpgen korpus")
        for anlage, titel, zeichne in seiten:
            _rahmen(c, projekt, anlage, "EFS", titel, datum)
            zeichne(c)
            c.showPage()
        _rahmen(c, projekt, "KPL", "", "Klemmenplan", datum)
        c.showPage()
        c.save()
        plaene.append(KorpusPlan(datei, projekt, jahr, leiste, [s[0] for s in seiten],
                                 {k: v for k, v in typ.items() if v}))
    return plaene
