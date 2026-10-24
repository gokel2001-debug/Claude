import copy
from pathlib import Path

import pytest
import yaml

from slpgen import regeln
from slpgen.zeichnen import erzeuge_pdf

B = Path(__file__).resolve().parent.parent / "beispiele"
PROJEKT = yaml.safe_load((B / "projekt_beispiel.yaml").read_text(encoding="utf-8"))
STAMM = yaml.safe_load((B / "geraetestamm.yaml").read_text(encoding="utf-8"))


def test_bilanz_handgerechnet():
    m = regeln.plane(PROJEKT, STAMM)
    # SPS: 600+30+40+50 mA; Feld: 2*15 + 2*35 + 22 + 20 mA + 3 * 4,2 W / 24 V
    i_soll = 0.720 + 0.030 + 0.070 + 0.022 + 0.020 + 3 * 4.2 / 24
    assert m.bilanz["i_summe_A"] == pytest.approx(i_soll, abs=1e-3)
    assert m.bilanz["i_bedarf_A"] == pytest.approx(i_soll * 1.25, abs=1e-3)
    assert m.bilanz["netzteil"] == "NT-24-05"


def test_netzteil_waechst_mit_last():
    p = copy.deepcopy(PROJEKT)
    p["feldgeraete"] += [{"bmk": f"Y{10 + i}", "artikel": "MV-24-4W", "funktion": "x"} for i in range(30)]
    m = regeln.plane(p, STAMM)
    assert m.bilanz["netzteil"] == "NT-24-10"   # 30*0.175 A + Rest > 5 A
    assert len([b for b in m.betriebsmittel if b.kategorie == "sps_do"]) == 3   # 34 DO / 16


def test_do_aktoren_am_abgang_der_do_module():
    m = regeln.plane(PROJEKT, STAMM)
    do = next(a for a in m.absicherungen if a.gruppe == "DO-Last")
    assert {"-A3", "-Y1", "-Y2", "-Y3", "-P1"} <= set(do.verbraucher)


def test_klemmen_lueckenlos_und_eindeutig():
    m = regeln.plane(PROJEKT, STAMM)
    nr = [k.nr for k in m.klemmen]
    assert nr == list(range(1, len(nr) + 1))
    assert len(nr) == 4 * 3 + 2 + 4 * 2   # 4 DI 3-Leiter, 1 AI 2-Leiter, 4 DO


def test_fehlender_artikel():
    p = copy.deepcopy(PROJEKT)
    p["feldgeraete"][0]["artikel"] = "GIBT-ES-NICHT"
    with pytest.raises(regeln.RegelFehler):
        regeln.plane(p, STAMM)


def test_pdf_wird_erzeugt(tmp_path):
    m = regeln.plane(PROJEKT, STAMM)
    seiten = erzeuge_pdf(m, STAMM, str(tmp_path / "t.pdf"))
    assert (tmp_path / "t.pdf").stat().st_size > 5000
    assert [t for _, t in seiten][-3:] == ["Klemmenplan -X1", "Stückliste", "Auslegung 24 V"]
