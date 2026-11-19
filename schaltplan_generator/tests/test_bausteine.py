import copy
import re
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
ZAEHLER_AI = {"bmk": "P8", "artikel": "ZAEHLER-AI", "funktion": "Zähler Hauptleitung", "gruppe": "Sensorik",
              "typical": "zaehler_ai"}
STELL = {"bmk": "Y9", "artikel": "STELLANTRIEB-24", "funktion": "Stellantrieb Heizung", "gruppe": "Aktorik",
         "typical": "stellantrieb_ao"}


def _projekt(*geraete):
    p = copy.deepcopy(PROJEKT)
    p["feldgeraete"] += [copy.deepcopy(g) for g in geraete]
    return p


def _klemmen(m, bmk):
    return [(k.potential, k.ziel_aussen.split(":")[1]) for k in m.klemmen if k.ziel_aussen.startswith(bmk + ":")]


def test_zaehler_di_zwei_eingaenge_klemmen_und_widerstand():
    m = regeln.plane(_projekt(ZAEHLER), STAMM)
    kanaele = [k for k in m.sps_kanaele if k.geraet_bmk.startswith("-P7.")]
    assert [(k.art, k.funktion.split()[0]) for k in kanaele] == [("DI", "Zählimpuls"), ("DI", "Störung")]
    assert _klemmen(m, "-P7") == [("+24V", "24V"), ("Signal", "I1"), ("Signal", "I2"), ("0V", "GND")]
    r1 = m.bm("-P7-R1")
    assert r1.kategorie == "bauteil" and r1.artikel == "WID-2K2"
    assert not any("-P7-R1" in a.verbraucher for a in m.absicherungen)      # passiv: kein 24-V-Verbraucher


def test_zaehler_ai_vier_leiter_mit_rueckleiter():
    m = regeln.plane(_projekt(ZAEHLER_AI), STAMM)
    assert _klemmen(m, "-P8") == [("+24V", "24V"), ("Signal", "I1"), ("Signal", "AO+"), ("Bezug", "AO-"),
                                  ("0V", "GND")]
    ai = next(k for k in m.sps_kanaele if k.geraet_bmk == "-P8.2")
    bezug = next(k for k in m.klemmen if k.ziel_aussen == "-P8:AO-")
    assert ai.art == "AI" and bezug.ziel_innen == f"{ai.modul_bmk}:{ai.kanal}M"


def test_stellantrieb_koppelrelais_kontakt_speisung_und_bilanz():
    ohne = regeln.plane(_projekt(), STAMM)
    mit = regeln.plane(_projekt(STELL), STAMM)
    assert _klemmen(mit, "-Y9") == [("+24V", "24V"), ("Kontakt", "S/S"), ("Signal", "IN+"), ("Bezug", "IN-"),
                                    ("+24V", "COM"), ("Signal", "NO"), ("0V", "GND")]
    kontakt = next(k for k in mit.klemmen if k.ziel_aussen == "-Y9:S/S")
    assert kontakt.ziel_innen == "-Y9-K1:14"                         # DO geht über das Koppelrelais
    ao = next(k for k in mit.sps_kanaele if k.art == "AO")
    assert ao.adresse == "%QW0" and mit.bm(ao.modul_bmk).artikel == "SPS-AO4"
    g = mit.bilanz["gruppen"]
    assert g["DO-Last"] == pytest.approx(ohne.bilanz["gruppen"]["DO-Last"] + 0.009, abs=1e-3)   # nur Spule
    assert g["Aktorik"] == pytest.approx(0.150, abs=1e-3)                                       # Antrieb selbst


def test_fremdversorgter_baustein_ist_kein_verbraucher():
    stamm = copy.deepcopy(STAMM)
    stamm["typicals"]["zaehler_fremd"] = {"versorgung": {}, "signale": [{"art": "DI", "text": "Impuls", "pin": "I1"}]}
    m = regeln.plane(_projekt(dict(ZAEHLER, typical="zaehler_fremd")), stamm)
    assert not any("-P7" in a.verbraucher for a in m.absicherungen)
    assert _klemmen(m, "-P7") == [("Signal", "I1")]


@pytest.mark.parametrize("geraet, text", [
    (dict(ZAEHLER, typical="gibt_es_nicht"), "Baustein"),
    (dict(STELL, artikel="MV-24-4W"), "Anschlüsse"),                    # Pins passen nicht zum Artikel
    (dict(ZAEHLER, bmk="P7.1"), "ungültig"),
    (dict(ZAEHLER, bmk="B1"), "doppelt"),
])
def test_eingabefehler_klar_gemeldet(geraet, text):
    with pytest.raises(regeln.RegelFehler, match=text):
        regeln.plane(_projekt(geraet), STAMM)


def test_fehlendes_ao_modul():
    p = _projekt(STELL)
    del p["sps"]["module_kandidaten"]["AO"]
    with pytest.raises(regeln.RegelFehler, match="AO"):
        regeln.plane(p, STAMM)


def test_hausstil_zeigt_bausteine(tmp_path):
    m = regeln.plane(_projekt(ZAEHLER, ZAEHLER_AI, STELL), STAMM)
    seiten = erzeuge_hausstil_pdf(m, STAMM, str(tmp_path / "h.pdf"))
    texte = [s.extract_text() for s in PdfReader(str(tmp_path / "h.pdf")).pages]
    t = {a: texte[i] for i, (a, n, _) in enumerate(seiten) if n == 1}
    assert "=Y09/1.3" in t["SA4"]                                     # 7 Klemmen -> Spalten 1..7, AO auf Spalte 3
    for adr in [k.adresse for k in m.sps_kanaele if k.geraet_bmk.startswith("-Y9.")]:
        assert adr in t["Y09"]
    assert "-K1:A1" in t["Y09"] and re.search(r"\b11\b", t["Y09"]) and re.search(r"\b14\b", t["Y09"])
    assert "-R1" in t["P07"] and "(M)" in t["P08"]
    stl = "\n".join(texte[i] for i, (a, _, _) in enumerate(seiten) if a == "STL")
    assert "WID-2K2" in stl and "KR-24DC" in stl
    erzeuge_pdf(m, STAMM, str(tmp_path / "alt.pdf"))                 # bisheriger Plan bricht nicht ab


def test_excel_baustein_spalte(tmp_path):
    p = _projekt(ZAEHLER, STELL)
    schreibe_vorlage(p, STAMM, tmp_path / "p.xlsx")
    geladen = lade_excel(tmp_path / "p.xlsx")
    assert [g.get("typical") for g in geladen["feldgeraete"]][-2:] == ["zaehler_di", "stellantrieb_ao"]
    assert geladen["sps"]["module_kandidaten"]["AO"] == "SPS-AO4"


PUMPE = {"bmk": "M9", "artikel": "PUMPE-EC-230", "funktion": "Umwälzpumpe Heizkreis", "gruppe": "Aktorik",
         "typical": "pumpe_ec", "laenge_m": 25}


def test_pumpe_leistungsteil_und_meldungen(tmp_path):
    m = regeln.plane(_projekt(PUMPE), STAMM)
    assert m.bm("-M9-Q1").artikel == "MSS-1.6"                              # 1,19 A im Bereich 1–1,6 A
    w = next(c for c in m.kabel if c.bmk == "-M9-W2")
    # 1~: ΔU = 2 · I · l · cos φ / (κ · A) / 230 V
    assert w.querschnitt_mm2 == 1.5 and w.du_prozent == pytest.approx(2 * 1.19 * 25 * 0.95 / (56 * 1.5) / 230 * 100, abs=0.01)
    assert [(k.potential, k.ziel_aussen.split(":")[1]) for k in m.klemmen if k.leiste == "-X2" and "-M9" in k.ziel_aussen] \
        == [("L", "L"), ("N", "N"), ("PE", "PE")]
    assert ("Kontakt-Rück", "GND") in _klemmen(m, "-M9")                     # Start/Stopp potentialfrei
    msmeldung = next(k for k in m.sps_kanaele if k.funktion.startswith("Störung Motorschutz"))
    assert not any(k.signal == msmeldung.geraet_bmk for k in m.klemmen)      # Hilfskontakt: keine Feldklemme
    assert m.bilanz["i_netzgeraete_A"] == pytest.approx(1.19)
    seiten = erzeuge_hausstil_pdf(m, STAMM, str(tmp_path / "h.pdf"))
    assert [(a, n) for a, n, _ in seiten if a == "M09"] == [("M09", 1), ("M09", 2)]
    texte = [s.extract_text() for s in PdfReader(str(tmp_path / "h.pdf")).pages]
    seite2 = texte[seiten.index(("M09", 2, "Leistungsteil"))]
    assert "-Q1" in seite2 and msmeldung.adresse in seite2 and "L1 =M04/1.9" in seite2   # Netzkette nach Motor 4
    erzeuge_pdf(m, STAMM, str(tmp_path / "alt.pdf"))


def test_pumpe_ohne_laenge_warnt():
    m = regeln.plane(_projekt(dict(PUMPE, laenge_m=None)), STAMM)
    assert any("Spannungsfall nicht geprüft" in w for w in m.warnungen)
