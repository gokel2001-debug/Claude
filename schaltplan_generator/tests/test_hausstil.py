from pathlib import Path

import pytest
import yaml
from pypdf import PdfReader

from slpgen import regeln
from slpgen.hausstil import erzeuge_hausstil_pdf, lade_hausstil

B = Path(__file__).resolve().parent.parent / "beispiele"
PROJEKT = yaml.safe_load((B / "projekt_beispiel.yaml").read_text(encoding="utf-8"))
STAMM = yaml.safe_load((B / "geraetestamm.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def plan(tmp_path_factory):
    pfad = tmp_path_factory.mktemp("hs") / "h.pdf"
    seiten = erzeuge_hausstil_pdf(regeln.plane(PROJEKT, STAMM), STAMM, str(pfad))
    texte = [s.extract_text() for s in PdfReader(str(pfad)).pages]
    return seiten, texte


def _seite(plan, anlage, nr=1):
    seiten, texte = plan
    return texte[seiten.index(next(s for s in seiten if s[0] == anlage and s[1] == nr))]


def test_anlagen_reihenfolge_und_seitenzaehlung(plan):
    seiten, _ = plan
    anlagen = list(dict.fromkeys(a for a, _, _ in seiten))
    assert anlagen[:5] == ["DBL", "INH", "AC230.01", "DC24.01", "DC24.02"]
    assert anlagen[-4:] == ["KAB", "KPL", "STL", "AUS"]
    assert [nr for a, nr, _ in seiten if a == "M01"] == [1, 2]      # Zählung je Anlage
    feld = [a for a in anlagen if a[0] in "BYP" and a[1:].isdigit()]
    assert len(feld) == len(PROJEKT["feldgeraete"])                    # eine Anlage je Feldgerät


def test_spalten_0_bis_9_und_schriftfeld(plan):
    t = _seite(plan, "B01")
    assert {str(i) for i in range(10)} <= {z.strip() for z in t.splitlines()}   # Spaltenleiste 0..9
    assert "= B01" in t and "& EFS" in t and "Seite 1" in t and "P-2026-001-B01-1-EFS-00" in t


def test_querverweise_in_beide_richtungen(plan):
    feld = _seite(plan, "B01")
    assert "=SA1/1.2" in feld                    # Feldgerät -> SPS-Karte
    assert "=DC24.02/1.3" in feld                # Feldgerät -> Absicherung (zweiter Abgang)
    assert "-X10:2" in feld                      # Klemme im SPS-Kasten
    karte = _seite(plan, "SA1")
    assert "=B01/1.4" in karte and "=M01/2.6" in karte     # Karte -> Feldgerät / Motorsteuerung


def test_freigegebenes_profil_wirkt_vorgeschlagenes_nicht(tmp_path):
    pfad = tmp_path / "profil.yaml"
    for status, erwartet in (("vorgeschlagen", "-X10"), ("freigegeben", "-X20")):
        pfad.write_text(yaml.safe_dump({"merkmale": {"feldklemmleiste": {"wert": "-X20", "status": status}}}),
                        encoding="utf-8")
        stil = lade_hausstil(pfad)
        assert stil["feldklemmleiste"] == erwartet
        if status == "freigegeben":
            erzeuge_hausstil_pdf(regeln.plane(PROJEKT, STAMM), STAMM, str(tmp_path / "h.pdf"), stil)
            text = "\n".join(s.extract_text() for s in PdfReader(str(tmp_path / "h.pdf")).pages)
            assert "-X20:2" in text and "Hausprofil (freigegeben)" in text
