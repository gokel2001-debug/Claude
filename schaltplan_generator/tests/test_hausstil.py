import re
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
    assert anlagen[:5] == ["DBL", "INH", "EIN", "NT24", "VT24"]
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
    assert "=VT24/1.3" in feld                # Feldgerät -> Absicherung (zweiter Abgang)
    assert "-X10:2" in feld                      # Klemme im SPS-Kasten
    karte = _seite(plan, "SA1")
    assert "=B01/1.3" in karte and "=M01/2.6" in karte     # Karte -> Feldgerät (Signalklemme) / Motorsteuerung


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
            assert "-X20:2" in text and "feldklemmleiste = -X20 (Hausprofil, freigegeben)" in text


def _plan_mit(**aenderungen):
    import copy
    p = copy.deepcopy(PROJEKT)
    p.update(aenderungen)
    return p


def test_motornummern_beliebig_und_potentialkette(tmp_path):
    p = _plan_mit(motoren=[dict(PROJEKT["motoren"][0], bmk="M10"), dict(PROJEKT["motoren"][1], bmk="M2")])
    seiten = erzeuge_hausstil_pdf(regeln.plane(p, STAMM), STAMM, str(tmp_path / "h.pdf"))
    texte = [s.extract_text() for s in PdfReader(str(tmp_path / "h.pdf")).pages]
    t = {(a, n): texte[i] for i, (a, n, _) in enumerate(seiten)}
    assert ("M10", 1) in t and ("M02", 2) in t
    assert "L1 =M10/1.0" in t[("EIN", 1)]                         # Einspeisung -> erster Motor
    assert "L1 =M02/1.0" in t[("M10", 1)] and "L1 =EIN/1.9" in t[("M10", 1)]
    assert "L1 =M10/1.9" in t[("M02", 1)]                         # Rückverweis auf Vorgänger
    vt = t[("VT24", 1)]
    assert "-Q1 =M10/2.6" in vt and "-K1 =M10/2.2" in vt          # 24-V-Verbraucher auf der Steuerungsseite
    steuer = t[("M10", 2)]
    assert re.search(r"1-2\s+/1\.4", steuer)                         # Kontaktspiegel -> Hauptkontakte


def test_doppelte_kennung_klare_meldung(tmp_path):
    p = _plan_mit(feldgeraete=PROJEKT["feldgeraete"] + [dict(PROJEKT["feldgeraete"][0], bmk="B01")])
    with pytest.raises(regeln.RegelFehler, match="doppelt"):
        erzeuge_hausstil_pdf(regeln.plane(p, STAMM), STAMM, str(tmp_path / "h.pdf"))


def test_viele_seiten_inhalt_mehrseitig_und_jedes_feldgeraet_in_kabelliste(tmp_path):
    extra = [{"bmk": f"S{i}", "artikel": "IND-M12-PNP", "funktion": f"Taster {i}", "gruppe": "Sensorik"}
             for i in range(1, 31)]
    p = _plan_mit(feldgeraete=PROJEKT["feldgeraete"] + extra)
    seiten = erzeuge_hausstil_pdf(regeln.plane(p, STAMM), STAMM, str(tmp_path / "h.pdf"))
    texte = [s.extract_text() for s in PdfReader(str(tmp_path / "h.pdf")).pages]
    inh = "\n".join(texte[i] for i, (a, _, _) in enumerate(seiten) if a == "INH")
    assert len([s for s in seiten if s[0] == "INH"]) >= 2 and "=AUS" in inh
    kab = "\n".join(texte[i] for i, (a, _, _) in enumerate(seiten) if a == "KAB")
    assert "=S30-W1" in kab


def test_stueckliste_mit_klemmen_feldkabeln_und_laengen(plan):
    seiten, texte = plan
    stl = "\n".join(texte[i] for i, (a, _, _) in enumerate(seiten) if a == "STL")
    assert "=B01" in stl and "RK-2.5" in stl and "RK-4" in stl and "Länge lt. Feld" in stl
    assert "12 m" in stl                                           # Motorleitung mit Länge


def test_klemmenplan_potentiale_wie_im_stromlaufplan(plan):
    seiten, texte = plan
    kpl = "\n".join(texte[i] for i, (a, _, _) in enumerate(seiten) if a == "KPL")
    assert "24L+" in kpl and "24M =VT24/1.0" in kpl and "-K1:2" in kpl and "+24V" not in kpl
