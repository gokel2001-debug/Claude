"""M4c: Konsistenzprüfungen (Prüfbericht) – Testkorpus ohne Fehler, jede Fehlerart wird erkannt."""
import copy
from pathlib import Path

import pytest
import yaml

from slpgen import regeln
from slpgen.cli import main
from slpgen.konsistenz import FEHLER, HINWEIS, KENNZAHL, kennzahlen, pruefe_plan
from slpgen.modell import Klemme, SpsKanal
from slpgen.projektmodell import bereit_machen

B = Path(__file__).resolve().parent.parent / "beispiele"
STAMM = yaml.safe_load((B / "geraetestamm.yaml").read_text(encoding="utf-8"))
VORGABEN = yaml.safe_load((B / "hausvorgaben.yaml").read_text(encoding="utf-8"))
BEISPIEL = yaml.safe_load((B / "projekt_beispiel.yaml").read_text(encoding="utf-8"))


def _korpus():
    """Testkorpus: Beispiel, KI-Beispiel (alle Bausteine), Selektivmodul, ohne Motoren, viele Feldgeräte."""
    ki, _ = bereit_machen(yaml.safe_load((B / "projektmodell_ki_beispiel.yaml").read_text(encoding="utf-8")),
                          STAMM, VORGABEN)
    selektiv = copy.deepcopy(BEISPIEL)
    selektiv["versorgung_24V"].update(verteilung="selektivmodul", selektivmodul="SEL-24-4K")
    ohne_motoren = copy.deepcopy(BEISPIEL)
    ohne_motoren["motoren"] = []
    viele = copy.deepcopy(BEISPIEL)
    viele["feldgeraete"] += [{"bmk": f"B{20 + i}", "artikel": "IND-M12-PNP", "funktion": f"Sensor {i}",
                              "gruppe": "Sensorik"} for i in range(20)]
    return {"beispiel": BEISPIEL, "ki": ki, "selektiv": selektiv, "ohne_motoren": ohne_motoren, "viele": viele}


@pytest.mark.parametrize("name", list(_korpus()))
def test_testkorpus_ohne_fehler(name):
    m = regeln.plane(copy.deepcopy(_korpus()[name]), STAMM)
    befunde = pruefe_plan(m)
    assert not [b for b in befunde if b.art == FEHLER], befunde
    assert not [b for b in befunde if b.pruefung == "Text"]          # keine Wortdopplung mehr (M4a Elektro 8)


def _plan():
    return regeln.plane(copy.deepcopy(BEISPIEL), STAMM)


def _stoere_adresse(m):
    m.sps_kanaele[1].adresse = m.sps_kanaele[0].adresse


def _stoere_klemme(m):
    m.klemmen.append(Klemme("-X1", m.klemmen[0].nr, "Signal", "x", "-B1:4"))


def _stoere_verweis(m):
    m.sps_kanaele.append(SpsKanal("-A2", 15, "DI", "%I9.9", "-B99", "Phantom"))


def _stoere_bmk(m):
    m.betriebsmittel.append(copy.deepcopy(m.betriebsmittel[-1]))


def _stoere_sicherung(m):
    m.absicherungen[0].i_gruppe_A = m.absicherungen[0].i_nenn_A + 1


def _stoere_kanal(m):
    m.sps_kanaele[0].kanal = 99


@pytest.mark.parametrize("stoerung, pruefung", [
    (_stoere_adresse, "SPS"), (_stoere_klemme, "Klemmen"), (_stoere_verweis, "Verweis"), (_stoere_bmk, "Kennzeichen"),
    (_stoere_sicherung, "Absicherung"), (_stoere_kanal, "SPS"), (lambda m: setattr(m.kabel[0], "i_z_A", 0.5), "Leitungsschutz"),
    (lambda m: setattr(m.kabel[0], "du_prozent", 12.0), "Spannungsfall"),
    (lambda m: m.bm(m.bm("-M1").daten["mss"]).daten.update(i_r_A=40.0), "Motorschutz"),
    (lambda m: m.absicherungen.__setitem__(slice(None), [a for a in m.absicherungen if "-B1" not in a.verbraucher]),
     "Potential"),
    (lambda m: setattr(m.klemmen[1], "ziel_aussen", m.klemmen[0].ziel_aussen), "Klemmen"),
    (lambda m: setattr(m.klemmen[0], "nr", 0), "Klemmen")])
def test_jede_fehlerart_wird_erkannt(stoerung, pruefung):
    m = _plan()
    stoerung(m)
    fehler = {b.pruefung for b in pruefe_plan(m) if b.art == FEHLER}
    assert pruefung in fehler and fehler <= {pruefung, "Klemmen", "Verweis", "Potential", "Leitungsschutz"}  # nichts Fremdes


def test_hinweise_luecke_und_textdopplung():
    m = _plan()
    m.klemmen = [k for k in m.klemmen if not (k.leiste == "-X1" and k.nr == 2)]
    m.sps_kanaele[0].funktion = "Endlage Endlage vorne"
    arten = {(b.art, b.pruefung) for b in pruefe_plan(m)}
    assert (HINWEIS, "Klemmen") in arten and (HINWEIS, "Text") in arten


def test_kennzahlen_und_cli(tmp_path, capsys):
    m = _plan()
    k = kennzahlen(m, 40)
    assert k["Seite"] == 40 and k["Klemme"] == len(m.klemmen) and k[KENNZAHL] > 0
    assert k["Kabel"] == len(m.kabel) + len([b for b in m.betriebsmittel if b.kategorie in ("sensor", "aktor")])
    m.speichere(tmp_path / "pm.json")
    main(["pruefbericht", str(tmp_path / "pm.json")])
    aus = capsys.readouterr().out
    assert "Prüfbericht: keine Befunde" in aus and "Kennzahlen:" in aus
    _stoere_adresse(m)
    m.speichere(tmp_path / "pm.json")
    with pytest.raises(SystemExit, match="FEHLER"):
        main(["pruefbericht", str(tmp_path / "pm.json")])


def test_nachweis_enthaelt_pruefbericht_motorleitungen_und_kennzahlen(tmp_path):
    from pypdf import PdfReader
    main(["generieren", str(B / "projekt_beispiel.yaml"), "--ausgabe", str(tmp_path), "--profil", str(tmp_path / "x.yaml")])
    text = "".join(p.extract_text() for p in PdfReader(str(tmp_path / "P-2026-001_Stromlaufplan_Hausstil.pdf")).pages)
    assert "7 Prüfbericht (Konsistenz)" in text and "2a Leitungen Motor" in text and "8 Kennzahlen" in text


def test_ungueltige_werte_ergeben_befund_statt_absturz():
    m = _plan()
    next(b for b in m.betriebsmittel if b.kategorie == "sps_di").daten["bytebereich"] = [0]
    assert any(b.pruefung == "Daten" and b.art == FEHLER for b in pruefe_plan(m))


def test_zeichnen_prueft_frisch(tmp_path):
    """Software-Befund M4c: geändertes planmodell.json -> zeichnen meldet FEHLER, Nachweis zeigt ihn."""
    from pypdf import PdfReader
    main(["generieren", str(B / "projekt_beispiel.yaml"), "--ausgabe", str(tmp_path), "--profil", str(tmp_path / "x.yaml")])
    pm = tmp_path / "P-2026-001_Planmodell.json"
    from slpgen.modell import Planmodell
    m = Planmodell.lade(pm)
    _stoere_adresse(m)
    m.speichere(pm)
    with pytest.raises(SystemExit, match="FEHLER"):
        main(["zeichnen", str(pm), "--profil", str(tmp_path / "x.yaml")])
    text = "".join(p.extract_text() for p in PdfReader(str(tmp_path / "P-2026-001_Stromlaufplan_Hausstil.pdf")).pages)
    assert "FEHLER (SPS)" in text
