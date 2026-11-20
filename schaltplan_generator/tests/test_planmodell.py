"""M3a: Planungskern (B) und Ausgabe (C) sind über planmodell.json getrennt."""
import copy
import json
from pathlib import Path

import pytest
import yaml
from pypdf import PdfReader

from slpgen import regeln
from slpgen.cli import main
from slpgen.hausstil import erzeuge_hausstil_pdf
from slpgen.modell import SCHEMA_PLANMODELL, Planmodell, RegelFehler
from slpgen.projektmodell import bereit_machen
from slpgen.zeichnen import erzeuge_pdf, stueckliste_csv

B = Path(__file__).resolve().parent.parent / "beispiele"
STAMM = yaml.safe_load((B / "geraetestamm.yaml").read_text(encoding="utf-8"))
VORGABEN = yaml.safe_load((B / "hausvorgaben.yaml").read_text(encoding="utf-8"))


def _projekte():
    beispiel = yaml.safe_load((B / "projekt_beispiel.yaml").read_text(encoding="utf-8"))
    ki, _ = bereit_machen(yaml.safe_load((B / "projektmodell_ki_beispiel.yaml").read_text(encoding="utf-8")),
                          STAMM, VORGABEN)
    selektiv = copy.deepcopy(beispiel)
    selektiv["versorgung_24V"].update(verteilung="selektivmodul", selektivmodul="SEL-24-4K")
    return {"beispiel": beispiel, "ki_bausteine": ki, "selektiv": selektiv}


def _texte(pfad):
    return [s.extract_text() for s in PdfReader(str(pfad)).pages]


@pytest.mark.parametrize("name", ["beispiel", "ki_bausteine", "selektiv"])
def test_pdf_aus_geladenem_planmodell_identisch(tmp_path, name):
    m = regeln.plane(_projekte()[name], STAMM)
    m.speichere(tmp_path / "pm.json")
    geladen = Planmodell.lade(tmp_path / "pm.json")
    def norm(x):
        return json.loads(json.dumps(x.als_dict(), default=str))
    assert norm(geladen) == norm(m) and geladen.seiten == m.seiten          # verlustfreie Rundreise
    for erzeuge, datei in ((erzeuge_pdf, "a.pdf"), (erzeuge_hausstil_pdf, "h.pdf")):
        erzeuge(m, str(tmp_path / ("mem_" + datei)))
        erzeuge(geladen, str(tmp_path / ("json_" + datei)))
        assert _texte(tmp_path / ("mem_" + datei)) == _texte(tmp_path / ("json_" + datei))
    assert stueckliste_csv(m) == stueckliste_csv(geladen)


def test_ausgabe_braucht_keinen_geraetestamm(tmp_path):
    """Planmodell trägt den Artikelauszug selbst; Zeichnen ohne Projekt und Gerätestamm."""
    m = regeln.plane(_projekte()["beispiel"], STAMM)
    assert set(m.artikel) == {b.artikel for b in m.betriebsmittel} & set(STAMM["artikel"]) | \
        {a.artikel for a in m.absicherungen} | {k.artikel for k in m.kabel}
    (tmp_path / "pm").mkdir()
    m.speichere(tmp_path / "pm" / "P_Planmodell.json")
    main(["zeichnen", str(tmp_path / "pm" / "P_Planmodell.json"), "--profil", str(tmp_path / "x.yaml")])
    assert (tmp_path / "pm" / "P-2026-001_Stromlaufplan.pdf").exists()
    assert "IND-M12-PNP" in (tmp_path / "pm" / "P-2026-001_Stueckliste.csv").read_text(encoding="utf-8")


@pytest.mark.parametrize("inhalt, meldung", [
    ("{kaputt", "JSON beschädigt"),
    (json.dumps({"schema": "planmodell/0"}), "erwartet „planmodell/1“"),
    (json.dumps({"schema": SCHEMA_PLANMODELL, "fremd": 1, "projekt": {}}), "unbekannte Felder: fremd"),
    (json.dumps({"schema": SCHEMA_PLANMODELL, "projekt": {}, "kabel": [{"bmk": "-W1"}]}), "unvollständig"),
])
def test_fehlerhaftes_planmodell_klartext(tmp_path, inhalt, meldung):
    (tmp_path / "pm.json").write_text(inhalt, encoding="utf-8")
    with pytest.raises(RegelFehler, match=meldung):
        Planmodell.lade(tmp_path / "pm.json")
