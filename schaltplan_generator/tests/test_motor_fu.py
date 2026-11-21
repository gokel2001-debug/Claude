"""M7c: Motorabgang mit Frequenzumrichter (A51) – Auslegung, SPS-Signale, Zeichnung in beiden Stilen."""
import copy
from pathlib import Path

import pytest
import yaml
from pypdf import PdfReader

from slpgen import regeln, zeichnen
from slpgen.excel_eingabe import lade_excel, schreibe_vorlage
from slpgen.hausstil import erzeuge_hausstil_pdf
from slpgen.konsistenz import FEHLER, pruefe_plan
from slpgen.modell import RegelFehler
from slpgen.projektmodell import bereit_machen

B = Path(__file__).resolve().parent.parent / "beispiele"
STAMM = yaml.safe_load((B / "geraetestamm.yaml").read_text(encoding="utf-8"))
BEISPIEL = yaml.safe_load((B / "projekt_beispiel.yaml").read_text(encoding="utf-8"))
VORGABEN = yaml.safe_load((B / "hausvorgaben.yaml").read_text(encoding="utf-8"))


def _fu_projekt():
    p = copy.deepcopy(BEISPIEL)
    p["motoren"][1]["anlauf"] = "fu"            # M2: 1,5 kW, I_N 3,5 A
    return p


def test_fu_auslegung_und_signale():
    m = regeln.plane(_fu_projekt(), STAMM)
    fu = m.bm("-T2")
    assert fu.kategorie == "fu" and fu.artikel == "FU-1.5"                         # kleinster mit I_aus ≥ I_N, P ≥ P_N
    mot = m.bm("-M2")
    assert mot.daten["fu"] == "-T2" and mot.daten["i_netz_A"] == 3.7
    assert m.bm(mot.daten["mss"]).daten["i_r_A"] == 3.7                            # MSS auf Netzeingangsstrom (A51)
    w = next(c for c in m.kabel if c.nach == "-M2")
    assert STAMM["artikel"][w.artikel]["geschirmt"] is True
    direkt = next(c for c in m.kabel if c.nach == "-M1")
    assert not STAMM["artikel"][direkt.artikel].get("geschirmt")                 # Direktstart bleibt ungeschirmt
    kan = {k.geraet_bmk: (k.art, k.anschluss) for k in m.sps_kanaele if k.geraet_bmk.startswith("-T2")}
    assert kan == {"-T2": ("DO", "-T2:DI1"), "-T2.2": ("AO", "-T2:AI1"), "-T2.3": ("DI", "-T2:RL1")}
    assert not any(b.bmk == "-K2" for b in m.betriebsmittel)                       # kein Schütz beim FU
    ohne = regeln.plane(copy.deepcopy(BEISPIEL), STAMM)
    assert m.bilanz["i_motoren_A"] == pytest.approx(ohne.bilanz["i_motoren_A"] - 3.5 + 3.7)
    fehler = [b for b in pruefe_plan(m) if b.art == FEHLER]
    assert [b.pruefung for b in fehler] == ["Sicherheit"]          # STO nur Platzhalter -> Freigabe nötig (Elektro M7c 1)
    assert any("STO" in t for t in m.projekt["_sicherheit"]["ausloeser"])
    assert w.i_b_A == 4.1 and w.i_z_A >= 4.1                       # Motorleitung nach I_aus des FU (Elektro M7c 2/3)
    assert not [b for b in pruefe_plan(m) if b.pruefung == "Leitungsschutz" and b.art == FEHLER]
    assert any("Frequenzumrichter FU-1.5" in w for w in m.warnungen)


def test_fu_in_beiden_pdfs(tmp_path):
    m = regeln.plane(_fu_projekt(), STAMM)
    zeichnen.erzeuge_pdf(m, str(tmp_path / "a.pdf"))
    text = "".join(p.extract_text() for p in PdfReader(str(tmp_path / "a.pdf")).pages)
    assert "-T2" in text and "geschirmt" in text and "Sollwert Drehzahl -M2" in text
    seiten = erzeuge_hausstil_pdf(m, str(tmp_path / "h.pdf"))
    i = [(a, t) for a, _, t in seiten].index(("M02", "Lastkreis"))
    r = PdfReader(str(tmp_path / "h.pdf"))
    last, steuer = r.pages[i].extract_text(), r.pages[i + 1].extract_text()
    assert "-T1" in last and "I_aus = 4,1 A" in last and "geschirmt" in last and "RL1" in last
    assert "STO – PLATZHALTER" in steuer
    assert "%QW" in steuer and "RL1" in steuer and "DI1" in steuer and "AI1" in steuer


def test_fu_grenzfall_i_ein_kleiner_i_n():
    """Elektro M7c 2: I_ein < I_N darf keinen falschen Leitungsschutz-FEHLER geben (Schutz der Motorleitung = FU)."""
    p = copy.deepcopy(BEISPIEL)
    p["motoren"][2].update(anlauf="fu", p_kW=3.0, i_N_A=7.0)
    befunde = pruefe_plan(regeln.plane(p, STAMM))
    assert not [b for b in befunde if b.pruefung == "Leitungsschutz" and b.art == FEHLER], befunde


def test_fu_fehlerfaelle():
    p = _fu_projekt()
    p["motoren"][1]["p_kW"] = 30
    with pytest.raises(RegelFehler, match="kein Frequenzumrichter"):
        regeln.plane(p, STAMM)
    p = _fu_projekt()
    p["motoren"][1]["anlauf"] = "stern-dreieck"
    with pytest.raises(RegelFehler, match="erlaubt: direkt, fu"):
        bereit_machen(p, STAMM, VORGABEN)


def test_fu_ueber_excel(tmp_path):
    schreibe_vorlage(_fu_projekt(), STAMM, tmp_path / "p.xlsx")
    d = lade_excel(tmp_path / "p.xlsx")
    assert [mo.get("anlauf") for mo in d["motoren"]] == ["direkt", "fu", "direkt", "direkt"]


def test_fu_stammwerte_und_vorsicherung():
    """Software M7c 1/4: eigener FU ohne Pflichtwert -> Klartext; MSS über zulässiger Vorsicherung -> Fehler."""
    stamm = copy.deepcopy(STAMM)
    del stamm["artikel"]["FU-1.5"]["i_ein_A"]
    with pytest.raises(RegelFehler, match=r"FU-1.5.*Netzeingangsstrom \(i_ein_A\) fehlt"):
        regeln.plane(_fu_projekt(), stamm)
    stamm = copy.deepcopy(STAMM)
    stamm["artikel"]["FU-1.5"]["vorsicherung_max_A"] = 2
    with pytest.raises(RegelFehler, match="zulässigen Vorsicherung"):
        regeln.plane(_fu_projekt(), stamm)
    stamm = copy.deepcopy(STAMM)
    for k in [k for k, d in stamm["artikel"].items() if d.get("geschirmt")]:
        del stamm["artikel"][k]
    with pytest.raises(RegelFehler, match=r"-M2: kein Kabel 4 x 1,5 mm² geschirmt"):
        regeln.plane(_fu_projekt(), stamm)


def test_fu_viele_motoren_rundreise_eplan(tmp_path):
    """Software M7c 4: mehrere FU über Seitenwechsel, planmodell.json-Rundreise, EPLAN-Aufbereitung."""
    from slpgen import eplan_adapter
    from slpgen.modell import Planmodell
    p = copy.deepcopy(BEISPIEL)
    p["motoren"] = [dict(p["motoren"][1], bmk=f"M{i}", anlauf="fu" if i % 2 else "direkt") for i in range(1, 7)]
    m = regeln.plane(p, STAMM)
    assert len([b for b in m.betriebsmittel if b.kategorie == "fu"]) == 3
    m.speichere(tmp_path / "pm.json")
    m2 = Planmodell.lade(tmp_path / "pm.json")
    assert m2.als_dict() == m.als_dict()
    zeichnen.erzeuge_pdf(m2, str(tmp_path / "a.pdf"))
    erzeuge_hausstil_pdf(m2, str(tmp_path / "h.pdf"))
    assert eplan_adapter.aufbereiten(m2)


def test_fu_excel_spalte_von_hand(tmp_path):
    """Software M7c 3: alte Vorlage, Spalte „Anlauf“ von Hand ergänzt -> wird erkannt."""
    from openpyxl import load_workbook
    schreibe_vorlage(copy.deepcopy(BEISPIEL), STAMM, tmp_path / "p.xlsx")
    wb = load_workbook(tmp_path / "p.xlsx")
    ws = wb["Motoren"]
    ws.cell(1, 7).value = "Anlauf"
    ws.cell(3, 7).value = "FU"
    wb.save(tmp_path / "p.xlsx")
    assert [mo.get("anlauf") for mo in lade_excel(tmp_path / "p.xlsx")["motoren"]][:2] == ["direkt", "fu"]
