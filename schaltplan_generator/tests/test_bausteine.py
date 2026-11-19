import copy
from pathlib import Path

import pytest
import yaml
from pypdf import PdfReader

from slpgen import regeln
from slpgen.excel_eingabe import lade_excel, schreibe_vorlage
from slpgen.hausstil import erzeuge_hausstil_pdf
from slpgen.zeichnen import erzeuge_pdf

B = Path(__file__).resolve().parent.parent / "beispiele"
PROJEKT = yaml.safe_load((B / "projekt_beispiel.yaml").read_text(encoding="utf-8"))
STAMM = yaml.safe_load((B / "geraetestamm.yaml").read_text(encoding="utf-8"))
ZAEHLER = {"bmk": "P7", "artikel": "ZAEHLER-PULS", "funktion": "Zähler Kühlwasser", "gruppe": "Sensorik",
           "typical": "zaehler_di"}
STELL = {"bmk": "Y9", "artikel": "MV-24-4W", "funktion": "Stellventil", "gruppe": "Aktorik",
         "typical": "stellantrieb_ao"}


def _projekt(*geraete):
    p = copy.deepcopy(PROJEKT)
    p["feldgeraete"] += [copy.deepcopy(g) for g in geraete]
    return p


def test_zaehler_di_zwei_eingaenge_klemmen_und_widerstand():
    m = regeln.plane(_projekt(ZAEHLER), STAMM)
    kanaele = [k for k in m.sps_kanaele if k.geraet_bmk.startswith("-P7.")]
    assert [(k.art, k.funktion.split()[0]) for k in kanaele] == [("DI", "Zählimpuls"), ("DI", "Störung")]
    kl = [k for k in m.klemmen if k.ziel_aussen.startswith("-P7:")]
    assert [(k.potential, k.ziel_aussen) for k in kl] == [("+24V", "-P7:24V"), ("Signal", "-P7:I1"),
                                                          ("Signal", "-P7:I2"), ("0V", "-P7:GND")]
    assert [k.signal for k in kl] == ["", "-P7.1", "-P7.2", ""]
    r1 = m.bm("-P7-R1")
    assert r1.kategorie == "bauteil" and r1.artikel == "WID-2K2"


def test_stellantrieb_ao_modul_und_koppelrelais_in_bilanz():
    ohne = regeln.plane(_projekt(), STAMM)
    mit = regeln.plane(_projekt(STELL), STAMM)
    ao = [k for k in mit.sps_kanaele if k.art == "AO"]
    assert len(ao) == 1 and ao[0].adresse == "%QW0"
    assert mit.bm(ao[0].modul_bmk).artikel == "SPS-AO4"
    # Koppelrelais 9 mA + DO-Modul unverändert -> DO-Last steigt genau um 0,009 A
    assert mit.bilanz["gruppen"]["DO-Last"] == pytest.approx(ohne.bilanz["gruppen"]["DO-Last"] + 0.009, abs=1e-3)


def test_fehlende_bibliothek_oder_modul():
    with pytest.raises(regeln.RegelFehler, match="Baustein"):
        regeln.plane(_projekt(dict(ZAEHLER, typical="gibt_es_nicht")), STAMM)
    p = _projekt(STELL)
    del p["sps"]["module_kandidaten"]["AO"]
    with pytest.raises(regeln.RegelFehler, match="AO"):
        regeln.plane(p, STAMM)


def test_hausstil_zeigt_baustein_mit_allen_kanaelen(tmp_path):
    m = regeln.plane(_projekt(ZAEHLER, STELL), STAMM)
    seiten = erzeuge_hausstil_pdf(m, STAMM, str(tmp_path / "h.pdf"))
    texte = [s.extract_text() for s in PdfReader(str(tmp_path / "h.pdf")).pages]
    t = {a: texte[i] for i, (a, n, _) in enumerate(seiten) if n == 1}
    assert "SA4" in t and "=Y09/1.5" in t["SA4"]                    # AO-Karte verweist auf Signalklemme
    for adr in [k.adresse for k in m.sps_kanaele if k.geraet_bmk.startswith("-Y9.")]:
        assert adr in t["Y09"]
    assert "-R1" in t["P07"] and "-K1" in t["Y09"]
    stl = "\n".join(texte[i] for i, (a, _, _) in enumerate(seiten) if a == "STL")
    assert "WID-2K2" in stl and "KR-24DC" in stl
    erzeuge_pdf(m, STAMM, str(tmp_path / "alt.pdf"))                 # bisheriger Plan bricht nicht ab


def test_excel_baustein_spalte(tmp_path):
    p = _projekt(ZAEHLER, STELL)
    schreibe_vorlage(p, STAMM, tmp_path / "p.xlsx")
    geladen = lade_excel(tmp_path / "p.xlsx")
    assert [g.get("typical") for g in geladen["feldgeraete"]][-2:] == ["zaehler_di", "stellantrieb_ao"]
    assert geladen["sps"]["module_kandidaten"]["AO"] == "SPS-AO4"
