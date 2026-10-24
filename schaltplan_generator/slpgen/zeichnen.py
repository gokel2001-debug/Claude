"""PDF-Ausgabe (Variante B): Planmodell -> Stromlaufplan-PDF mit Listen.

Blattformat, Rahmen, Spaltenleiste und Schriftfeld sind in LAYOUT gekapselt,
damit sie an das Haus-Layout (aus der Bestandsanalyse) angepasst werden können.
Symbole sind vereinfachte Darstellungen in Anlehnung an IEC 60617; für den
Produktiveinsatz werden sie durch die Symbolbibliothek des Hauses ersetzt.
"""
from __future__ import annotations

from collections import Counter, OrderedDict
from typing import Callable

from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

from .modell import Planmodell
from .regeln import (ERSTE_FELDSEITE, SEITE_EINSPEISUNG, SEITE_SPS,
                     SEITE_VERTEILUNG, SPALTEN_JE_SEITE)

LAYOUT = {
    "rand_links": 20, "rand": 10, "spaltenleiste": 7, "schriftfeld": 30,
    "schrift": "Helvetica", "schrift_fett": "Helvetica-Bold",
}
W, H = (v / mm for v in landscape(A3))   # 420 x 297 mm
X0, X1 = LAYOUT["rand_links"], W - LAYOUT["rand"]
Y0, Y1 = LAYOUT["rand"], H - LAYOUT["rand"]
YS = Y0 + LAYOUT["schriftfeld"]           # Oberkante Schriftfeld
YL = Y1 - LAYOUT["spaltenleiste"]         # Unterkante Spaltenleiste
COLW = (X1 - X0) / SPALTEN_JE_SEITE


def sx(spalte: int) -> float:
    return X0 + (spalte - 0.5) * COLW


class Blatt:
    """Dünne Hülle um den Canvas mit mm-Koordinaten."""

    def __init__(self, c: Canvas):
        self.c = c

    def linie(self, x1, y1, x2, y2, breite=0.25, strich=None):
        c = self.c
        c.setLineWidth(breite)
        c.setDash(*(strich or ([], 0)))
        c.line(x1 * mm, y1 * mm, x2 * mm, y2 * mm)
        c.setDash([], 0)

    def rechteck(self, x, y, w, h, breite=0.3, strich=None):
        c = self.c
        c.setLineWidth(breite)
        c.setDash(*(strich or ([], 0)))
        c.rect(x * mm, y * mm, w * mm, h * mm)
        c.setDash([], 0)

    def kreis(self, x, y, r, fuellen=False):
        self.c.setLineWidth(0.25)
        self.c.circle(x * mm, y * mm, r * mm, stroke=1, fill=1 if fuellen else 0)

    def text(self, x, y, s, groesse=2.5, fett=False, ausr="l", drehen=0):
        c = self.c
        c.saveState()
        c.setFont(LAYOUT["schrift_fett" if fett else "schrift"], groesse / 0.3528)  # mm -> pt
        c.translate(x * mm, y * mm)
        if drehen:
            c.rotate(drehen)
        {"l": c.drawString, "m": c.drawCentredString, "r": c.drawRightString}[ausr](0, 0, str(s))
        c.restoreState()


# --------------------------------------------------------------------------- #
# Symbole (vereinfacht, in Anlehnung an IEC 60617)
# --------------------------------------------------------------------------- #
def sym_sicherung(b: Blatt, x, y_oben, bmk, text="", laenge=14):
    """Sicherung/Schutzorgan senkrecht; liefert y unten."""
    b.rechteck(x - 2, y_oben - laenge, 4, laenge)
    b.linie(x, y_oben, x, y_oben - laenge)
    b.text(x - 4, y_oben - laenge / 2 + 1, bmk, 2.5, True, "r")
    if text:
        b.text(x - 4, y_oben - laenge / 2 - 2.5, text, 2, ausr="r")
    return y_oben - laenge


def sym_klemme(b: Blatt, x, y, leiste, nr):
    b.kreis(x, y, 1.1)
    b.text(x + 1.8, y - 0.8, f"{nr}", 2)
    return leiste


def sym_schliesser(b: Blatt, x, y_oben, laenge=10):
    b.linie(x, y_oben, x, y_oben - 3)
    b.linie(x, y_oben - 3, x - 3, y_oben - laenge + 3)
    b.linie(x, y_oben - laenge + 3, x, y_oben - laenge)


def potential_pfeil(b: Blatt, x, y, text, nach_rechts=True):
    d = 1 if nach_rechts else -1
    b.linie(x, y, x + d * 3, y)
    b.c.setLineWidth(0.25)
    p = b.c.beginPath()
    p.moveTo((x + d * 3) * mm, (y + 1) * mm)
    p.lineTo((x + d * 5) * mm, y * mm)
    p.lineTo((x + d * 3) * mm, (y - 1) * mm)
    p.close()
    b.c.drawPath(p, fill=1)
    b.text(x + d * 6, y - 0.8, text, 2.2, ausr="l" if nach_rechts else "r")


def verweis(seite: int | None, spalte: int | None) -> str:
    return f"/{seite}.{spalte}" if seite else ""


# --------------------------------------------------------------------------- #
# Rahmen und Schriftfeld
# --------------------------------------------------------------------------- #
def rahmen(b: Blatt, m: Planmodell, seite: int, gesamt: int, titel: str, spalten=True):
    b.rechteck(X0, Y0, X1 - X0, Y1 - Y0, 0.5)
    if spalten:
        b.linie(X0, YL, X1, YL)
        for k in range(SPALTEN_JE_SEITE):
            x = X0 + k * COLW
            if k:
                b.linie(x, YL, x, Y1)
            b.text(x + COLW / 2, YL + 2.2, k + 1, 2.5, ausr="m")
    # Schriftfeld
    p = m.projekt
    b.linie(X0, YS, X1, YS, 0.5)
    felder = [(0, 70), (70, 160), (160, 270), (270, 330), (330, X1 - X0)]
    for a, _ in felder[1:]:
        b.linie(X0 + a, Y0, X0 + a, YS)
    b.text(X0 + 3, YS - 6, "Erstellt:", 2)
    b.text(X0 + 3, YS - 11, f"{p.get('ersteller', '')}  {p.get('datum', '')}", 2.5)
    b.text(X0 + 3, YS - 18, f"Rev. {p.get('revision', '')}", 2.5)
    b.text(X0 + 3, Y0 + 3, "Erzeugt mit slpgen (Prototyp) – nicht freigegeben", 1.8)
    b.text(X0 + 73, YS - 6, "Projekt", 2)
    b.text(X0 + 73, YS - 12, p.get("nummer", ""), 3, True)
    b.text(X0 + 73, YS - 18, p.get("bezeichnung", ""), 2.5)
    b.text(X0 + 73, YS - 24, p.get("kunde", ""), 2.5)
    b.text(X0 + 163, YS - 6, "Seiteninhalt", 2)
    b.text(X0 + 163, YS - 16, titel, 4, True)
    b.text(X0 + 273, YS - 6, "Anlage / Ort", 2)
    b.text(X0 + 273, YS - 14, p.get("anlage", ""), 3.5, True)
    b.text(X0 + 273, YS - 22, p.get("ort", ""), 3.5, True)
    b.text(X0 + 333, YS - 6, "Blatt", 2)
    b.text(X0 + 333, YS - 16, f"{seite}", 6, True)
    b.text(X0 + 355, YS - 16, f"von {gesamt}", 3)


# --------------------------------------------------------------------------- #
# Seiteninhalte
# --------------------------------------------------------------------------- #
def s_deckblatt(b: Blatt, m: Planmodell):
    p = m.projekt
    xm = (X0 + X1) / 2
    b.text(xm, 220, "Stromlaufplan", 12, True, "m")
    b.text(xm, 200, p.get("bezeichnung", ""), 7, ausr="m")
    zeilen = [("Projektnummer", p.get("nummer")), ("Kunde", p.get("kunde")),
              ("Anlage (=)", p.get("anlage")), ("Ort (+)", p.get("ort")),
              ("Ersteller", p.get("ersteller")), ("Datum", p.get("datum")),
              ("Revision", p.get("revision"))]
    for i, (k, v) in enumerate(zeilen):
        b.text(xm - 60, 170 - i * 9, k, 4)
        b.text(xm + 5, 170 - i * 9, v, 4, True)


def s_inhalt(seiten):
    def f(b: Blatt, m: Planmodell):
        b.text(X0 + 10, YL - 15, "Seite", 3, True)
        b.text(X0 + 35, YL - 15, "Inhalt", 3, True)
        for i, (nr, titel, _) in enumerate(seiten):
            b.text(X0 + 10, YL - 25 - i * 7, nr, 3)
            b.text(X0 + 35, YL - 25 - i * 7, titel, 3)
    return f


def s_einspeisung(b: Blatt, m: Planmodell):
    leiter = [("L1", 262), ("L2", 256), ("L3", 250), ("N", 244), ("PE", 238)]
    netz = m.projekt.get("_netz", "")
    for name, y in leiter:
        b.text(X0 + 2, y + 0.8, name, 2.5)
        if name in ("L1", "L2", "L3"):
            xq = sx(2)
            b.linie(X0 + 8, y, xq - 5, y)
            b.linie(xq - 5, y, xq - 1.5, y + 2.5)       # Schaltkontakt
            b.linie(xq + 1.5, y, X1 - 12, y)
        else:
            b.linie(X0 + 8, y, X1 - 12, y)
        potential_pfeil(b, X1 - 12, y, "", True)
    b.text(X0 + 8, 268, netz, 2.5)
    q1 = m.bm("-Q1")
    b.rechteck(sx(2) - 7, 247, 14, 18, strich=([1.5, 1], 0))
    b.text(sx(2), 270, q1.bmk, 3, True, "m")
    b.text(sx(2), 230, q1.bezeichnung, 2, ausr="m")

    f1, g1 = m.bm("-F1"), m.bm("-G1")
    x = sx(5)
    b.kreis(x, 262, 0.6, True)
    b.linie(x, 262, x, 215)
    yu = sym_sicherung(b, x, 215, f1.bmk, f1.bezeichnung)
    b.linie(x, yu, x, 160)
    for xx, yy in ((x + 8, 244), (x + 16, 238)):
        b.kreis(xx, yy, 0.6, True)
        b.linie(xx, yy, xx, 160)
    # Netzteil
    gx0, gx1 = x - 5, sx(7) + 10
    b.rechteck(gx0, 120, gx1 - gx0, 40, 0.4)
    b.linie(gx0, 120, gx1, 160, 0.2)
    b.text(gx0 + 6, 150, "~", 6)
    b.text(gx1 - 10, 126, "=", 6)
    for xx, t in ((x, "L"), (x + 8, "N"), (x + 16, "PE")):
        b.text(xx + 0.8, 156, t, 2)
    b.text(gx1 + 2, 156, g1.bmk, 3.5, True)
    b.text(gx1 + 2, 151, g1.bezeichnung, 2)
    b.text(gx1 + 2, 147, f"Artikel {g1.artikel}", 2)
    for yy, t in ((140, "+24V"), (128, "0V")):
        b.linie(gx1, yy, X1 - 12, yy)
        b.text(gx1 + 1, yy + 0.8, t, 2)
        potential_pfeil(b, X1 - 12, yy, f"{t} {verweis(SEITE_VERTEILUNG, 1)}")
    bil = m.bilanz
    b.text(X0 + 5, 95, f"Auslegung: Σ I = {bil['i_summe_A']} A · g = {bil['gleichzeitigkeit']} · "
                       f"Reserve {bil['reserve']:.0%} → Bedarf {bil['i_bedarf_A']} A → {g1.artikel} "
                       f"({bil['i_nenn_A']} A, Auslastung {bil['auslastung']:.0%})", 2.5)


def s_verteilung(b: Blatt, m: Planmodell):
    yp, y0v = 255, 90
    potential_pfeil(b, X0 + 6, yp, f"+24V {verweis(SEITE_EINSPEISUNG, 8)}", False)
    potential_pfeil(b, X0 + 6, y0v, f"0V {verweis(SEITE_EINSPEISUNG, 8)}", False)
    b.linie(X0 + 6, yp, sx(len(m.absicherungen)), yp)
    b.linie(X0 + 6, y0v, X1 - 30, y0v)
    potential_pfeil(b, X1 - 30, y0v, "0V Feld")
    for a in m.absicherungen:
        f = m.bm(a.bmk)
        x = sx(f.spalte)
        b.kreis(x, yp, 0.6, True)
        b.linie(x, yp, x, 225)
        yu = sym_sicherung(b, x, 225, f.bmk, f"{a.i_nenn_A:g} A")
        b.linie(x, yu, x, 180)
        ziele = sorted({(m.bm(v).seite, m.bm(v).spalte) for v in a.verbraucher})
        b.text(x + 1.5, 182, f"+24V {a.gruppe}", 2.3, True)
        b.text(x + 1.5, 178, f"Σ {a.i_gruppe_A:.2f} A", 2)
        for i, (s, sp) in enumerate(ziele[:12]):
            b.text(x + 1.5, 174 - i * 3.2, verweis(s, sp), 2)


def s_sps(b: Blatt, m: Planmodell):
    module = [x for x in m.betriebsmittel if x.kategorie.startswith("sps_")]
    for mb in module:
        x = sx(mb.spalte)
        b.rechteck(x - 20, 120, 40, 140, 0.4)
        b.text(x, 262, mb.bmk, 3.5, True, "m")
        b.text(x, 254, mb.funktion, 2.5, ausr="m")
        b.text(x, 250, mb.artikel, 2, ausr="m")
        kan = [k for k in m.sps_kanaele if k.modul_bmk == mb.bmk]
        for i, k in enumerate(kan):
            g = m.bm(k.geraet_bmk)
            y = 242 - i * 7
            b.text(x - 18, y, f"{k.kanal}", 2.2)
            b.text(x - 14, y, k.adresse, 2.2, True)
            b.text(x - 1, y, f"{k.geraet_bmk} {verweis(g.seite, g.spalte)}", 2.2)
            b.text(x - 14, y - 2.8, k.funktion[:26], 1.8)
        if mb.kategorie == "sps_cpu":
            b.text(x, 200, "Versorgung 24 V", 2.2, ausr="m")
            fa = next(a.bmk for a in m.absicherungen if mb.bmk in a.verbraucher)
            b.text(x, 196, f"über {fa} {verweis(SEITE_VERTEILUNG, m.bm(fa).spalte)}", 2.2, ausr="m")


def s_feld(seite: int):
    def f(b: Blatt, m: Planmodell):
        geraete = [g for g in m.betriebsmittel if g.seite == seite and g.kategorie in ("sensor", "aktor")]
        y0v, y_k, y_dev = 272, 200, 150
        b.linie(X0 + 6, y0v, X1 - 6, y0v)
        potential_pfeil(b, X0 + 6, y0v, f"0V {verweis(SEITE_VERTEILUNG, 1)}", False)
        lane = {"+24V": -12, "Signal": 0, "0V": 12}
        for g in geraete:
            x = sx(g.spalte)
            kl = [k for k in m.klemmen if k.ziel_aussen.startswith(g.bmk + ":")]
            for k in kl:
                xl = x + lane[k.potential]
                if k.potential == "+24V":
                    fa = m.bm(g.daten["absicherung"])
                    b.text(xl - 1, 266, f"{fa.bmk}:2", 2, ausr="r", drehen=0)
                    b.text(xl - 1, 263, verweis(fa.seite, fa.spalte), 2, ausr="r")
                    b.linie(xl, 268, xl, y_k + 1.1)
                elif k.potential == "0V":
                    b.kreis(xl, y0v, 0.6, True)
                    b.linie(xl, y0v, xl, y_k + 1.1)
                else:
                    kanal = next(c for c in m.sps_kanaele if c.geraet_bmk == g.bmk)
                    b.rechteck(xl - 7, 238, 14, 14)
                    b.text(xl, 247, kanal.modul_bmk, 2.3, True, "m")
                    b.text(xl, 243.5, f"Kanal {kanal.kanal}", 1.9, ausr="m")
                    b.text(xl, 240, kanal.adresse, 2, ausr="m")
                    b.text(xl, 253, verweis(SEITE_SPS, m.bm(kanal.modul_bmk).spalte), 1.9, ausr="m")
                    b.linie(xl, 238, xl, y_k + 1.1)
                sym_klemme(b, xl, y_k, k.leiste, k.nr)
                b.linie(xl, y_k - 1.1, xl, y_dev)
                b.text(xl + 0.8, y_dev + 1, k.ziel_aussen.split(":", 1)[1].split(" ")[0], 1.9)
            b.text(x - 20, y_k + 4, "-X1", 2.2, True)
            b.rechteck(x - 20, y_dev - 35, 40, 35, 0.4)
            b.text(x, y_dev - 9, g.bmk, 4, True, "m")
            b.text(x, y_dev - 15, g.funktion[:28], 2.2, ausr="m")
            b.text(x, y_dev - 20, g.artikel, 2, ausr="m")
            if g.kategorie == "aktor":
                b.rechteck(x - 4, y_dev - 32, 8, 6)       # Spule/Last
            b.text(x - 20, y_dev - 40, m.voll_bmk(g.bmk), 2, True)
            text = g.bezeichnung
            b.text(x - 20, y_dev - 44, text[:34], 1.9)
            b.text(x - 20, y_dev - 47, text[34:68], 1.9)
            b.text(x - 20, y_dev - 51, f"I = {g.daten['i_A'] * 1000:.0f} mA", 1.9)
    return f


def tabelle(b: Blatt, kopf, zeilen, breiten, y_start=None, groesse=2.5):
    y = y_start or YL - 12
    x = X0 + 6
    for t, w in zip(kopf, breiten):
        b.text(x, y, t, groesse, True)
        x += w
    b.linie(X0 + 4, y - 2, X1 - 4, y - 2)
    for i, z in enumerate(zeilen):
        x = X0 + 6
        yy = y - 7 - i * 5.5
        for t, w in zip(z, breiten):
            b.text(x, yy, t, groesse)
            x += w


def s_klemmen(b: Blatt, m: Planmodell):
    zeilen = [(f"{k.leiste}:{k.nr}", k.potential, k.ziel_innen, k.ziel_aussen, verweis(k.seite, k.spalte))
              for k in m.klemmen]
    tabelle(b, ["Klemme", "Potential", "Ziel innen (Schrank)", "Ziel außen (Feld)", "Seite"],
            zeilen, [30, 30, 90, 80, 30])


def s_stueckliste(b: Blatt, m: Planmodell, stamm: dict):
    gruppen: "OrderedDict[str, list[str]]" = OrderedDict()
    for x in m.betriebsmittel:
        gruppen.setdefault(x.artikel, []).append(x.bmk)
    zeilen = []
    for pos, (art, bmks) in enumerate(gruppen.items(), 1):
        a = stamm["artikel"][art]
        menge = len(bmks)
        if a["kategorie"] == "klemme":
            menge = m.bm(bmks[0]).daten.get("anzahl", menge)
        zeilen.append((pos, menge, art, a.get("hersteller", ""), a["bezeichnung"][:60],
                       ", ".join(bmks)[:40]))
    tabelle(b, ["Pos.", "Menge", "Artikel", "Hersteller", "Bezeichnung", "BMK"],
            zeilen, [15, 15, 35, 40, 150, 100])


def s_auslegung(b: Blatt, m: Planmodell):
    bil = m.bilanz
    zeilen = [(a.bmk, a.gruppe, f"{a.i_gruppe_A:.3f}", f"{a.i_nenn_A:g}", ", ".join(a.verbraucher)[:80])
              for a in m.absicherungen]
    tabelle(b, ["Abgang", "Gruppe", "Σ I [A]", "Sicherung [A]", "Verbraucher"], zeilen,
            [25, 30, 25, 30, 200])
    y = YL - 12 - 7 - len(zeilen) * 5.5 - 10
    for t in [
        f"Summenstrom Σ I = {bil['i_summe_A']} A",
        f"Bedarf = Σ I · g · (1 + Reserve) = {bil['i_summe_A']} · {bil['gleichzeitigkeit']} · "
        f"(1 + {bil['reserve']}) = {bil['i_bedarf_A']} A",
        f"Gewählt: {bil['netzteil']} mit I_N = {bil['i_nenn_A']} A (Auslastung {bil['auslastung']:.0%})",
        f"Primärstrom max. ≈ U·I_N / (η·U_ein) = {bil['i_primaer_max_A']} A",
    ]:
        b.text(X0 + 6, y, t, 2.8)
        y -= 6
    y -= 4
    b.text(X0 + 6, y, "Hinweise / Warnungen:", 2.8, True)
    for w in m.warnungen or ["keine"]:
        y -= 6
        b.text(X0 + 10, y, "• " + w, 2.6)


# --------------------------------------------------------------------------- #
def erzeuge_pdf(m: Planmodell, stamm: dict, pfad: str) -> list[tuple[int, str]]:
    feldseiten = range(ERSTE_FELDSEITE, m.projekt["letzte_feldseite"] + 1)
    inhalt: list[tuple[str, Callable]] = [
        ("Deckblatt", s_deckblatt),
        ("Inhaltsverzeichnis", None),
        ("Einspeisung / Netzteil 24 V", s_einspeisung),
        ("Verteilung 24 V DC", s_verteilung),
        ("SPS-Übersicht", s_sps),
        *[(f"Feldgeräte {i + 1}", s_feld(s)) for i, s in enumerate(feldseiten)],
        ("Klemmenplan -X1", s_klemmen),
        ("Stückliste", lambda b, mm_: s_stueckliste(b, mm_, stamm)),
        ("Auslegung 24 V", s_auslegung),
    ]
    seiten = [(i + 1, t, f) for i, (t, f) in enumerate(inhalt)]
    assert seiten[SEITE_EINSPEISUNG - 1][1].startswith("Einspeisung")
    seiten[1] = (2, "Inhaltsverzeichnis", s_inhalt(seiten))

    c = Canvas(pfad, pagesize=landscape(A3))
    c.setTitle(f"Stromlaufplan {m.projekt.get('nummer', '')}")
    b = Blatt(c)
    for nr, titel, f in seiten:
        rahmen(b, m, nr, len(seiten), titel, spalten=nr > 2)
        f(b, m)
        c.showPage()
    c.save()
    return [(nr, t) for nr, t, _ in seiten]


def stueckliste_csv(m: Planmodell, stamm: dict) -> str:
    z = Counter(x.artikel for x in m.betriebsmittel)
    zeilen = ["Artikel;Menge;Hersteller;Bezeichnung"]
    for art, n in z.items():
        a = stamm["artikel"][art]
        if a["kategorie"] == "klemme":
            n = next(x for x in m.betriebsmittel if x.artikel == art).daten.get("anzahl", n)
        zeilen.append(f"{art};{n};{a.get('hersteller', '')};{a['bezeichnung']}")
    return "\n".join(zeilen) + "\n"
