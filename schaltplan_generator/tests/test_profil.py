import pytest
import yaml

from slpgen.korpus import WECHSELJAHR, erzeuge_korpus
from slpgen.profil import lerne_ordner


@pytest.fixture(scope="module")
def korpus(tmp_path_factory):
    ordner = tmp_path_factory.mktemp("k")
    return ordner, erzeuge_korpus(ordner, anzahl=10, seed=3)


def test_trend_der_feldklemmleiste_wird_gelernt(korpus, tmp_path):
    ordner, plaene = korpus
    m = lerne_ordner(ordner, tmp_path / "p.yaml")["merkmale"]["feldklemmleiste"]
    assert m["wert"] == "-X10" and m["status"] == "vorgeschlagen" and m["sicherheit"] == "hoch"
    (t,) = m["trend"]
    vorher = sum(p.jahr < WECHSELJAHR for p in plaene)
    assert (t["ab_jahr"], t["von"], t["nach"], t["belege_vorher"], t["belege_nachher"]) == \
        (WECHSELJAHR, "-X20", "-X10", vorher, len(plaene) - vorher)
    assert sorted(m["belege"]["-X10"]) == sorted(p.datei for p in plaene if p.jahr >= WECHSELJAHR)


def test_weitere_merkmale(korpus, tmp_path):
    ordner, _ = korpus
    m = lerne_ordner(ordner, tmp_path / "p.yaml")["merkmale"]
    assert m["sps_adressschreibweise"]["wert"] == "deutsch (E/A/EW/AW)"
    assert m["signalader_0_75"]["wert"] == "DBU 0,75"
    assert m["leitungstypen"]["haeufigkeit"]["LIYCY"] == 10


def test_wenige_plaene_sind_unsicher(tmp_path):
    erzeuge_korpus(tmp_path / "k", anzahl=2, seed=1)
    m = lerne_ordner(tmp_path / "k", tmp_path / "p.yaml")["merkmale"]["feldklemmleiste"]
    assert m["sicherheit"] == "unsicher"
    assert all(t["sicherheit"] == "unsicher" for t in m["trend"])


def test_freigegebene_werte_bleiben_erhalten(korpus, tmp_path):
    ordner, _ = korpus
    pfad = tmp_path / "p.yaml"
    lerne_ordner(ordner, pfad)
    profil = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    profil["merkmale"]["feldklemmleiste"].update(wert="-X30", status="freigegeben")   # Mensch entscheidet
    pfad.write_text(yaml.safe_dump(profil, allow_unicode=True), encoding="utf-8")
    m = lerne_ordner(ordner, pfad)["merkmale"]["feldklemmleiste"]
    assert (m["wert"], m["status"]) == ("-X30", "freigegeben")
    assert m["vorschlag_neu"]["wert"] == "-X10"
    assert "vorschlag_neu" not in m["vorschlag_neu"]


def test_leerer_ordner(tmp_path):
    with pytest.raises(FileNotFoundError):
        lerne_ordner(tmp_path, tmp_path / "p.yaml")
