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
    assert any(b == "Artikel je Gerät" and m == "=Y01+SS1-Y1" and "Nachbau: VENTIL-NEU" in w for b, m, w in abw)
    assert any(b == "SPS-Adresse" for b, _, _ in abw)                                # Adressen verschieben sich
    _g, r, _n, q = erg["kennzahlen"]["BMK"]
    assert r > 0 and q < 1.0
    schreibe_liste(erg, tmp_path / "a.xlsx")
    wb = load_workbook(tmp_path / "a.xlsx")
    assert wb["Abweichungen"]["E2"].value == "offen" and wb["Zusammenfassung"]["A2"].value == "BMK"
    assert wb["Abweichungen"].data_validations.dataValidation                         # Bewertung per Auswahlliste


def test_merkmale_ohne_ort_und_cli(tmp_path, capsys):
    mk = merkmale("=M01+SS1-Q1 =M01-Q1 =B01-X10:2 %QW4 %IX0.3 %I0.10")
    assert mk["BMK"] >= {"=M01+SS1-Q1", "=M01-Q1"} and mk["SPS-Adresse"] == {"%Q4", "%I0.3", "%I0.10"}
    eplan = merkmale("Schriftfeld =PU1 Blatt 3  -Q1  -K12 X1:3 -F2")            # EPLAN: Anlage nur im Schriftfeld
    assert {"=PU1-Q1", "=PU1-K12", "=PU1-F2"} <= eplan["BMK"] and "=PU1-X1:3" in eplan["Klemme"]
    ref = _referenz(tmp_path)
    m = regeln.plane(copy.deepcopy(BEISPIEL), STAMM)
    m.speichere(tmp_path / "pm.json")
    main(["abweichungen", str(ref), str(tmp_path / "pm.json")])
    assert capsys.readouterr().out.count("Übereinstimmung 100,0%") == 5
    assert (tmp_path / "referenz_Abweichungen.xlsx").exists()
    main(["abweichungen", str(ref), str(tmp_path / "pm.json")])                     # bewertete Liste bleibt erhalten
    assert (tmp_path / "referenz_Abweichungen_2.xlsx").exists()
    leer = tmp_path / "leer.pdf"
    from reportlab.pdfgen.canvas import Canvas
    c = Canvas(str(leer))
    c.showPage()
    c.save()
    with pytest.raises(RegelFehler, match="kein Text"):
        vergleiche(leer, m)
    fremd = tmp_path / "fremd.pdf"                                                   # nichts erkennbar -> nicht 100 %
    c = Canvas(str(fremd))
    c.drawString(100, 700, "Ein Plan in fremder Schreibweise ohne erkennbare Kennzeichen")
    c.showPage()
    c.save()
    assert all(q is None for *_, q in vergleiche(fremd, m)["kennzahlen"].values())


@pytest.mark.parametrize("aenderung, bereich", [
    ("tausche_b1_b2", "SPS-Belegung"),       # Elektro M8a Versuch 1: vertauschte Belegung
    ("funktionstext", "SPS-Belegung"),       # Versuch 5
    ("motor_kleiner", "Artikel je Gerät"),   # Versuch 6: anderer Motorschutzschalter am selben Gerät
])
def test_zuordnungen_erkannt(tmp_path, aenderung, bereich):
    """Prüfung M8a Elektro 1/2: Namen gleich, Zuordnung anders -> Abweichung, Übereinstimmung < 100 %."""
    ref = _referenz(tmp_path)
    p = copy.deepcopy(BEISPIEL)
    fg = p["feldgeraete"]
    if aenderung == "tausche_b1_b2":
        fg[0]["funktion"], fg[1]["funktion"] = fg[1]["funktion"], fg[0]["funktion"]
    elif aenderung == "funktionstext":
        fg[0]["funktion"] = "Endlage Band ganz vorne"
    else:
        p["motoren"][3].update(p_kW=2.2, i_N_A=4.9)
    erg = vergleiche(ref, regeln.plane(p, STAMM))
    assert any(a["bereich"] == bereich and "≠" in a["abweichung"] for a in erg["abweichungen"])
    assert erg["kennzahlen"][bereich][3] < 1.0
