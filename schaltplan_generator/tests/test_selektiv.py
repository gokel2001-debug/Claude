import copy
from pathlib import Path

import pytest
import yaml
from pypdf import PdfReader

from slpgen import regeln
from slpgen.excel_eingabe import lade_excel, schreibe_vorlage
from slpgen.hausstil import erzeuge_hausstil_pdf
from slpgen.zeichnen import erzeuge_pdf, stueckliste_zeilen

B = Path(__file__).resolve().parent.parent / "beispiele"
PROJEKT = yaml.safe_load((B / "projekt_beispiel.yaml").read_text(encoding="utf-8"))
STAMM = yaml.safe_load((B / "geraetestamm.yaml").read_text(encoding="utf-8"))


def _selektiv(p=PROJEKT):
    p = copy.deepcopy(p)
    p["versorgung_24V"].update(verteilung="selektivmodul", selektivmodul="SEL-24-4K")
    return p


def test_kanaele_nach_gruppenstrom_und_sammelmeldung():
    m = regeln.plane(_selektiv(), STAMM)
    werte = {a.gruppe: (a.bmk, a.i_nenn_A) for a in m.absicherungen}
    # I_Kanal = kleinster Einstellwert >= 1,25 · Σ I der Gruppe
    assert werte == {"SPS": ("-F2.1", 1), "Sensorik": ("-F2.2", 0.5), "DO-Last": ("-F2.3", 2)}
    assert [b.bmk for b in m.betriebsmittel if b.kategorie == "selektivmodul"] == ["-F2"]
    assert any(k.geraet_bmk == "-F2.S" and k.art == "DI" for k in m.sps_kanaele)
    assert m.bm("-B1").daten["absicherung"] == "-F2.2"


def test_mehr_gruppen_als_kanaele_ergibt_zweites_modul():
    p = _selektiv()
    for i, g in enumerate(p["feldgeraete"][:5]):
        g["gruppe"] = f"Gruppe{i}"
    m = regeln.plane(p, STAMM)
    assert [b.bmk for b in m.betriebsmittel if b.kategorie == "selektivmodul"] == ["-F2", "-F3"]


def test_zu_grosser_gruppenstrom_und_fehlender_artikel():
    p = _selektiv()
    p["feldgeraete"] += [{"bmk": f"Y{20 + i}", "artikel": "MV-24-4W", "funktion": "x"} for i in range(60)]
    with pytest.raises(regeln.RegelFehler, match="Gruppe teilen"):
        regeln.plane(p, STAMM)
    p = _selektiv()
    p["versorgung_24V"]["selektivmodul"] = ""
    with pytest.raises(regeln.RegelFehler, match="kein Artikel"):
        regeln.plane(p, STAMM)


def test_ausgaben_und_stueckliste(tmp_path):
    m = regeln.plane(_selektiv(), STAMM)
    assert [z for z in stueckliste_zeilen(m, STAMM) if z[2] == "SEL-24-4K"][0][1] == "1 Stk"   # Modul einmal
    seiten = erzeuge_hausstil_pdf(m, STAMM, str(tmp_path / "h.pdf"))
    texte = [s.extract_text() for s in PdfReader(str(tmp_path / "h.pdf")).pages]
    vt = texte[[a for a, _, _ in seiten].index("VT24")]
    assert "-F1:K2" in vt and "Sammelmeldung" in vt
    feld = texte[[a for a, _, _ in seiten].index("B01")]
    assert "=VT24/1.3" in feld                                       # Kanal K2 in Spalte 3
    erzeuge_pdf(m, STAMM, str(tmp_path / "alt.pdf"))


def test_excel_felder(tmp_path):
    schreibe_vorlage(_selektiv(), STAMM, tmp_path / "p.xlsx")
    v = lade_excel(tmp_path / "p.xlsx")["versorgung_24V"]
    assert (v["verteilung"], v["selektivmodul"]) == ("selektivmodul", "SEL-24-4K")
    schreibe_vorlage(PROJEKT, STAMM, tmp_path / "q.xlsx")
    assert "verteilung" not in lade_excel(tmp_path / "q.xlsx")["versorgung_24V"]
