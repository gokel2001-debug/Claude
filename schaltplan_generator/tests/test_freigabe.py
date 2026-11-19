import pytest
import yaml
from openpyxl import load_workbook

from slpgen.freigabe import uebernehme_freigaben
from slpgen.korpus import erzeuge_korpus
from slpgen.modell import RegelFehler
from slpgen.profil import lerne_ordner


@pytest.fixture
def gelernt(tmp_path):
    erzeuge_korpus(tmp_path / "k", anzahl=6, seed=2)
    pfad = tmp_path / "hausprofil" / "profil.yaml"
    lerne_ordner(tmp_path / "k", pfad)
    return pfad, pfad.with_name("profil_freigabe.xlsx")


def _setze(liste, eintraege: dict[str, tuple]):
    wb = load_workbook(liste)
    ws = wb["Freigabe"]
    for zeile in ws.iter_rows(min_row=2):
        if zeile[0].value in eintraege:
            zeile[6].value, zeile[7].value = eintraege[zeile[0].value]
    wb.save(liste)


def test_liste_enthaelt_nur_einzelwerte(gelernt):
    _, liste = gelernt
    keys = [r[0] for r in load_workbook(liste)["Freigabe"].iter_rows(min_row=2, values_only=True)]
    assert keys == ["feldklemmleiste", "sps_adressschreibweise", "haeufigste_ader_0_75"]


def test_ja_nein_eigener_wert(gelernt):
    pfad, liste = gelernt
    _setze(liste, {"feldklemmleiste": ("ja", None), "sps_adressschreibweise": ("NEIN", None),
                   "haeufigste_ader_0_75": ("JA", "DBU 1,0")})
    e = uebernehme_freigaben(pfad, liste)
    assert e == {"freigegeben": ["feldklemmleiste", "haeufigste_ader_0_75"],
                 "abgelehnt": ["sps_adressschreibweise"], "offen": []}
    m = yaml.safe_load(pfad.read_text(encoding="utf-8"))["merkmale"]
    assert m["feldklemmleiste"]["status"] == "freigegeben"
    assert (m["haeufigste_ader_0_75"]["wert"], m["haeufigste_ader_0_75"]["quelle"]) == ("DBU 1,0", "manuell")


def test_freigabe_und_ablehnung_ueberstehen_neues_lernen(gelernt, tmp_path):
    pfad, liste = gelernt
    _setze(liste, {"feldklemmleiste": ("JA", "-X99"), "sps_adressschreibweise": ("NEIN", None)})
    uebernehme_freigaben(pfad, liste)
    lerne_ordner(tmp_path / "k", pfad)
    m = yaml.safe_load(pfad.read_text(encoding="utf-8"))["merkmale"]
    assert (m["feldklemmleiste"]["wert"], m["feldklemmleiste"]["status"]) == ("-X99", "freigegeben")
    assert m["sps_adressschreibweise"]["status"] == "abgelehnt"
    vorbelegt = {r[0]: r[6] for r in load_workbook(liste)["Freigabe"].iter_rows(min_row=2, values_only=True)}
    assert vorbelegt["feldklemmleiste"] == "JA" and vorbelegt["sps_adressschreibweise"] == "NEIN"


def test_ungueltige_eingabe(gelernt):
    pfad, liste = gelernt
    _setze(liste, {"feldklemmleiste": ("vielleicht", None)})
    with pytest.raises(RegelFehler, match="Zeile 2"):
        uebernehme_freigaben(pfad, liste)


def test_ohne_profil(tmp_path, gelernt):
    _, liste = gelernt
    with pytest.raises(RegelFehler, match="zuerst"):
        uebernehme_freigaben(tmp_path / "fehlt.yaml", liste)
