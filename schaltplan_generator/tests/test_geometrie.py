"""M5a: Spaltenraster und Schriftfeld aus Vektor-PDFs lernen (synthetischer Korpus, keine Kundendaten)."""

import pytest
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

from slpgen.analyse import analysiere_pdf
from slpgen.geometrie import lese_geometrie, spaltenraster
from slpgen.korpus import erzeuge_korpus
from slpgen.profil import lerne


@pytest.fixture(scope="module")
def korpus(tmp_path_factory):
    ordner = tmp_path_factory.mktemp("k")
    return ordner, erzeuge_korpus(ordner, anzahl=6, seed=3)


def test_geometrie_je_plan(korpus):
    ordner, plaene = korpus
    for p in plaene:
        g = lese_geometrie(ordner / p.datei)
        assert g["spaltenraster"] == "10 Spalten à 39 mm" and g["anteil_raster"] == 1.0
        assert g["schriftfeld_felder"].startswith("Datum, Bearb., Rev.") and g["datumsformat"] == "TT.MM.JJJJ"
        assert g["schriftfeld_jahr"] == p.jahr


def test_profil_lernt_geometrie_mit_sicherheit(korpus):
    ordner, plaene = korpus
    m = lerne(sorted(ordner.glob("*.pdf")))["merkmale"]
    assert m["spaltenraster"]["wert"] == "10 Spalten à 39 mm" and m["spaltenraster"]["sicherheit"] == "hoch"
    assert m["datumsformat"]["wert"] == "TT.MM.JJJJ"
    assert m["schriftfeld_felder"]["belegt_in"] == f"{len(plaene)} von {len(plaene)} Plänen"


def test_jahr_aus_schriftfeld_statt_haeufigstem_datum(tmp_path):
    """A16: Revisionsdaten im Text dürfen das Planjahr nicht verfälschen."""
    pfad = tmp_path / "p.pdf"
    c = Canvas(str(pfad), pagesize=landscape(A3))
    for _ in range(2):
        for i in range(10):
            c.drawString((40 + 39 * i) * mm, 282 * mm, str(i))
        c.drawString(60 * mm, 150 * mm, "Änderung 01.02.2019  Prüfung 03.04.2019  Muster 05.06.2019")
        c.drawString(25 * mm, 18 * mm, "Datum 12.03.2023   Bearb. Muster   Rev. 00")
        c.showPage()
    c.save()
    assert analysiere_pdf(pfad)["jahr"] == 2019                       # häufigstes Datum im Text: falsch
    assert lese_geometrie(pfad)["schriftfeld_jahr"] == 2023            # Schriftfeld: richtig


def test_kein_raster_bei_ungleichmaessigen_ziffern():
    texte = [(10 + x, 290.0, str(i)) for i, x in enumerate((0, 39, 78, 130, 160))]
    assert spaltenraster(texte, 297) is None
    assert spaltenraster([(10.0, 290.0, "0"), (49.0, 290.0, "1")], 297) is None          # zu wenige Ziffern


def _seite(pfad, zeichne, groesse=None, drehen=0):
    c = Canvas(str(pfad), pagesize=groesse or landscape(A3))
    zeichne(c)
    c.showPage()
    c.save()
    if drehen:
        from pypdf import PdfReader, PdfWriter
        r, w = PdfReader(str(pfad)), PdfWriter()
        for s in r.pages:
            s.rotate(drehen)
            w.add_page(s)
        with open(pfad, "wb") as f:
            w.write(f)


def test_aenderungsdatum_links_zaehlt_nicht(tmp_path):
    """Software-Befund M5a 1: Änderungsdatum links im Schriftfeld darf nicht Planjahr werden."""
    def z(c):
        c.drawString(5 * mm, 30 * mm, "Änderung 01.02.2025")
        c.drawString(60 * mm, 18 * mm, "Datum")
        c.drawString(75 * mm, 18 * mm, "12.03.2023")
    _seite(tmp_path / "p.pdf", z)
    assert lese_geometrie(tmp_path / "p.pdf")["schriftfeld_jahr"] == 2023


def test_raster_ab_1_und_mit_stoerzahl(tmp_path):
    def z(c):
        for i in range(1, 9):
            c.drawString((40 + 45 * i) * mm, 282 * mm, str(i))
        c.drawString(400 * mm, 286 * mm, "12")                       # Seitenzahl im oberen Band
    _seite(tmp_path / "p.pdf", z)
    assert lese_geometrie(tmp_path / "p.pdf")["spaltenraster"] == "8 Spalten à 45 mm"


def test_gedrehte_seite(tmp_path):
    """Hochformat-Mediabox mit /Rotate 90: Anzeige im Querformat, Spaltenleiste oben."""
    def z(c):                                                       # Inhalt so gezeichnet, dass er gedreht stimmt
        c.translate(297 * mm, 0)
        c.rotate(90)
        for i in range(10):
            c.drawString((40 + 39 * i) * mm, 282 * mm, str(i))
    _seite(tmp_path / "p.pdf", z, groesse=A3, drehen=90)
    assert lese_geometrie(tmp_path / "p.pdf")["spaltenraster"] == "10 Spalten à 39 mm"


def test_wortgrenzen_und_leere_seite(tmp_path):
    def z(c):
        c.drawString(25 * mm, 18 * mm, "Seitenanzahl 3   Normalbetrieb")
    _seite(tmp_path / "p.pdf", z)
    assert lese_geometrie(tmp_path / "p.pdf")["schriftfeld_felder"] is None
    _seite(tmp_path / "leer.pdf", lambda c: None)
    assert "keine Textebene" in lese_geometrie(tmp_path / "leer.pdf")["hinweis"]
