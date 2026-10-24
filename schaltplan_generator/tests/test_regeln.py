import copy
import json
import math
from pathlib import Path

import pytest
import yaml

from slpgen import analyse, regeln
from slpgen.motor import spannungsfall_prozent
from slpgen.zeichnen import erzeuge_pdf

B = Path(__file__).resolve().parent.parent / "beispiele"
PROJEKT = yaml.safe_load((B / "projekt_beispiel.yaml").read_text(encoding="utf-8"))
STAMM = yaml.safe_load((B / "geraetestamm.yaml").read_text(encoding="utf-8"))
OHNE_MOTOREN = {k: v for k, v in PROJEKT.items() if k != "motoren"}


# ---- 24-V-Versorgung --------------------------------------------------------
def test_bilanz_handgerechnet():
    m = regeln.plane(OHNE_MOTOREN, STAMM)
    # SPS: 600+30+40+50 mA; Feld: 2*15 + 2*35 + 22 + 20 mA + 3 * 4,2 W / 24 V
    i_soll = 0.720 + 0.030 + 0.070 + 0.022 + 0.020 + 3 * 4.2 / 24
    assert m.bilanz["i_summe_A"] == pytest.approx(i_soll, abs=1e-3)
    assert m.bilanz["i_bedarf_A"] == pytest.approx(i_soll * 1.25, abs=1e-3)
    assert m.bilanz["netzteil"] == "NT-24-05"


def test_schuetzspulen_in_der_bilanz():
    m = regeln.plane(PROJEKT, STAMM)
    # 4 Schütze à 3,0 W an 24 V zusätzlich (DO-Last)
    assert m.bilanz["i_summe_A"] == pytest.approx(1.387 + 4 * 3.0 / 24, abs=1e-3)
    do = next(a for a in m.absicherungen if a.gruppe == "DO-Last")
    assert {"-K1", "-K2", "-K3", "-K4", "-Y1", "-P1", "-A3"} <= set(do.verbraucher)


def test_netzteil_waechst_mit_last():
    p = copy.deepcopy(OHNE_MOTOREN)
    p["feldgeraete"] += [{"bmk": f"Y{10 + i}", "artikel": "MV-24-4W", "funktion": "x"} for i in range(30)]
    m = regeln.plane(p, STAMM)
    assert m.bilanz["netzteil"] == "NT-24-10"   # 30*0.175 A + Rest > 5 A
    assert len([b for b in m.betriebsmittel if b.kategorie == "sps_do"]) == 3   # 34 DO / 16


def test_klemmen_lueckenlos_und_eindeutig():
    m = regeln.plane(PROJEKT, STAMM)
    for leiste, soll in (("-X1", 4 * 3 + 2 + 4 * 2), ("-X2", 4 * 4)):
        nr = [k.nr for k in m.klemmen if k.leiste == leiste]
        assert nr == list(range(1, soll + 1))


def test_fehlender_artikel():
    p = copy.deepcopy(PROJEKT)
    p["feldgeraete"][0]["artikel"] = "GIBT-ES-NICHT"
    with pytest.raises(regeln.RegelFehler):
        regeln.plane(p, STAMM)


# ---- Motorabgänge -------------------------------------------------------------
def test_spannungsfall_formel():
    # √3 · 4,9 A · 40 m · 0,82 / (56 · 1,5) / 400 V
    assert spannungsfall_prozent(4.9, 40, 0.82, 56, 1.5) == pytest.approx(
        math.sqrt(3) * 4.9 * 40 * 0.82 / (56 * 1.5) / 400 * 100)


def test_motorabgang_auswahl():
    m = regeln.plane(PROJEKT, STAMM)
    assert m.bm("-Q5").artikel == "MSS-16" and m.bm("-K4").artikel == "SCH-12"   # M4: 11,2 A
    assert m.bm("-Q2").artikel == "MSS-2.5" and m.bm("-K1").artikel == "SCH-09"  # M1: 1,9 A
    w4 = next(c for c in m.kabel if c.nach == "-M4")
    # 1,5 mm²: 13,1 A · 0,8 = 10,48 A < 11,2 A  -> 2,5 mm²: 17,4 · 0,8 = 13,92 A
    assert w4.querschnitt_mm2 == 2.5 and w4.i_z_A == pytest.approx(13.92)
    assert any("nicht freigegeben" in w for w in m.warnungen)


def test_kein_querschnitt_fuehrt_zu_regelfehler():
    p = copy.deepcopy(PROJEKT)
    p["motoren"][3]["laenge_m"] = 1000
    with pytest.raises(regeln.RegelFehler):
        regeln.plane(p, STAMM)


def test_seitenplan():
    m = regeln.plane(PROJEKT, STAMM)
    arten = [a for _, _, a, _ in m.seiten]
    assert arten[5:8] == ["motor_last", "motor_steuer", "feld"]
    assert arten[-4:] == ["klemmen", "kabel", "stueckliste", "auslegung"]
    k1 = m.bm("-K1")
    assert (k1.daten["steuer_seite"], k1.seite) == (7, 6)


# ---- PDF + Rundlauf-Vergleich -----------------------------------------------------
def test_pdf_und_vergleich(tmp_path):
    m = regeln.plane(PROJEKT, STAMM)
    erzeuge_pdf(m, STAMM, str(tmp_path / "t.pdf"))
    modell = json.loads(json.dumps(m.als_dict(), default=str))
    v = analyse.vergleiche(tmp_path / "t.pdf", modell)
    assert v["bmk_nur_modell"] == [] and v["bmk_abdeckung"] == 1.0
    assert v["artikel_fehlen_im_pdf"] == []
