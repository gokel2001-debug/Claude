from collections import Counter

import pytest
import yaml

from slpgen.korpus import WECHSELJAHR, erzeuge_korpus
from slpgen.profil import ProfilFehler, _bloecke, _feldklemmleiste, _trend, lerne_ordner


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
    assert m["haeufigste_ader_0_75"]["wert"] == "DBU 0,75"
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


def test_ausreisser_ist_kein_sicherer_trend():
    # 2010-2023 je 3x A, 2024 1x B, 2025 2x A + 1x B  (Szenario aus der Prüfung)
    je_jahr = {j: Counter({"A": 3}) for j in range(2010, 2024)}
    je_jahr[2024] = Counter({"B": 1})
    je_jahr[2025] = Counter({"A": 2, "B": 1})
    bloecke = _bloecke(je_jahr)
    assert [b["wert"] for b in bloecke] == ["A", "B", "A"]
    assert all(t["sicherheit"] == "unsicher" for t in _trend(bloecke))   # B nur 1 Beleg
    assert bloecke[-1]["wert"] == "A"


def test_gleichstand_im_jahr_ist_unentschieden():
    bloecke = _bloecke({2024: Counter({"A": 3}), 2025: Counter({"A": 2, "B": 2}), 2026: Counter({"A": 2})})
    assert [b["wert"] for b in bloecke] == ["A"] and _trend(bloecke) == []


def test_feldklemmleiste_bevorzugt_klemmenbezuege():
    st = {"anlagen": {"F01": {"leer": False, "bmk": ["X1", "X20", "P1"], "klemmenbezuege": {"X20": 3}},
                      "F02": {"leer": False, "bmk": ["X1", "X20", "B1"], "klemmenbezuege": {"X20": 2}},
                      "AC1": {"leer": False, "bmk": ["X1"], "klemmenbezuege": {"X1": 9}}}}
    assert _feldklemmleiste(st) == "-X20"
    for a in st["anlagen"].values():
        a["klemmenbezuege"] = {}
    assert _feldklemmleiste(st) is None          # X1 und X20 gleich oft -> nicht raten


def test_unlesbare_pdfs_veraendern_profil_nicht(korpus, tmp_path):
    ordner, _ = korpus
    pfad = tmp_path / "hausprofil" / "profil.yaml"
    lerne_ordner(ordner, pfad)
    vorher = pfad.read_text(encoding="utf-8")
    kaputt = tmp_path / "kaputt"
    kaputt.mkdir()
    (kaputt / "a.pdf").write_bytes(b"kein pdf")
    with pytest.raises(ProfilFehler):
        lerne_ordner(kaputt, pfad)
    assert pfad.read_text(encoding="utf-8") == vorher


def test_beschaedigtes_profil_klare_meldung(korpus, tmp_path):
    ordner, _ = korpus
    pfad = tmp_path / "profil.yaml"
    pfad.write_text("merkmale: [unvollständig\n", encoding="utf-8")
    with pytest.raises(ProfilFehler, match="beschädigt"):
        lerne_ordner(ordner, pfad)


def test_sicherung_und_uebersicht(korpus, tmp_path):
    ordner, _ = korpus
    pfad = tmp_path / "profil.yaml"
    lerne_ordner(ordner, pfad)
    lerne_ordner(ordner, pfad)
    assert (tmp_path / "profil.yaml.bak").exists()
    text = (tmp_path / "profil_uebersicht.txt").read_text(encoding="utf-8")
    assert "Änderung ab 2025: -X20 -> -X10" in text and "Nur ansehen" in text
