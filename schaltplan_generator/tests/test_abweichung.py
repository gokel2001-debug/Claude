"""M8a: Abweichungsliste Referenzplan ↔ Nachbau – bekannte Abweichungen werden gefunden (synthetisch)."""
import copy
from pathlib import Path

import pytest
import yaml
from openpyxl import load_workbook

from slpgen import regeln
from slpgen.abweichung import merkmale, schreibe_liste, vergleiche
from slpgen.cli import main
from slpgen.hausstil import erzeuge_hausstil_pdf
from slpgen.modell import RegelFehler

B = Path(__file__).resolve().parent.parent / "beispiele"
STAMM = yaml.safe_load((B / "geraetestamm.yaml").read_text(encoding="utf-8"))
BEISPIEL = yaml.safe_load((B / "projekt_beispiel.yaml").read_text(encoding="utf-8"))


def _referenz(tmp_path):
    ref = tmp_path / "referenz.pdf"
    erzeuge_hausstil_pdf(regeln.plane(copy.deepcopy(BEISPIEL), STAMM), str(ref))
    return ref


def test_gleicher_plan_ohne_abweichung(tmp_path):
    erg = vergleiche(_referenz(tmp_path), regeln.plane(copy.deepcopy(BEISPIEL), STAMM))
    assert erg["abweichungen"] == [] and all(q == 1.0 for *_, q in erg["kennzahlen"].values())


def test_bekannte_abweichungen_gefunden(tmp_path):
    ref = _referenz(tmp_path)
    p = copy.deepcopy(BEISPIEL)
    p["feldgeraete"] = [g for g in p["feldgeraete"] if g["bmk"] != "B5"]           # Gerät fehlt im Nachbau
    y1 = next(g for g in p["feldgeraete"] if g["bmk"] == "Y1")
    stamm = copy.deepcopy(STAMM)
    stamm["artikel"]["VENTIL-NEU"] = {**stamm["artikel"][y1["artikel"]], "bezeichnung": "Ventil neu"}
    y1["artikel"] = "VENTIL-NEU"                                                     # anderer Artikel
    erg = vergleiche(ref, regeln.plane(p, stamm))
    abw = {(a["bereich"], a["merkmal"], a["abweichung"]) for a in erg["abweichungen"]}
    assert ("BMK", "=B05-B1", "nur im Referenzplan") in abw
    assert any(b == "Klemme" and m.startswith("=B05-") and w == "nur im Referenzplan" for b, m, w in abw)
    assert ("Artikel", "VENTIL-NEU", "Artikel des Nachbaus fehlt im Referenzplan") in abw
    assert any(b == "SPS-Adresse" for b, _, _ in abw)                                # Adressen verschieben sich
    _g, r, _n, q = erg["kennzahlen"]["BMK"]
    assert r > 0 and q < 1.0
    schreibe_liste(erg, tmp_path / "a.xlsx")
    wb = load_workbook(tmp_path / "a.xlsx")
    assert wb["Abweichungen"]["E2"].value == "offen" and wb["Zusammenfassung"]["A2"].value == "BMK"
    assert wb["Abweichungen"].data_validations.dataValidation                         # Bewertung per Auswahlliste


def test_merkmale_ohne_ort_und_cli(tmp_path, capsys):
    assert merkmale("=M01+SS1-Q1 =M01-Q1 =B01-X10:2 %QW4 %I0.3")["BMK"] == {"=M01-Q1"}
    ref = _referenz(tmp_path)
    m = regeln.plane(copy.deepcopy(BEISPIEL), STAMM)
    m.speichere(tmp_path / "pm.json")
    main(["abweichungen", str(ref), str(tmp_path / "pm.json")])
    assert capsys.readouterr().out.count("Übereinstimmung 100,0%") == 4
    assert (tmp_path / "referenz_Abweichungen.xlsx").exists()
    leer = tmp_path / "leer.pdf"
    from reportlab.pdfgen.canvas import Canvas
    c = Canvas(str(leer))
    c.showPage()
    c.save()
    with pytest.raises(RegelFehler, match="kein Text"):
        vergleiche(leer, m)
