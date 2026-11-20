"""M3a: Planungskern (B) und Ausgabe (C) sind über planmodell.json getrennt."""
import copy
import json
from pathlib import Path

import pytest
import yaml
from pypdf import PdfReader

from slpgen import regeln
from slpgen.cli import main
from slpgen.hausstil import erzeuge_hausstil_pdf, kennzeichne
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
    m.kennzeichen = kennzeichne(m)
    m.speichere(tmp_path / "pm.json")
    geladen = Planmodell.lade(tmp_path / "pm.json")
    assert geladen == m                                          # verlustfreie Rundreise, gleiche Typen
    for erzeuge, datei in ((erzeuge_pdf, "a.pdf"), (erzeuge_hausstil_pdf, "h.pdf")):
        erzeuge(m, str(tmp_path / ("mem_" + datei)))
        erzeuge(geladen, str(tmp_path / ("json_" + datei)))
        assert (tmp_path / ("mem_" + datei)).read_bytes() == (tmp_path / ("json_" + datei)).read_bytes()
    assert stueckliste_csv(m) == stueckliste_csv(geladen)


def test_pdf_und_eplan_zeigen_gleiche_kennzeichen(tmp_path):
    from slpgen.eplan_adapter import aufbereiten
    m = regeln.plane(_projekte()["beispiel"], STAMM)
    m.kennzeichen = kennzeichne(m)
    rk = {z["referenzkennzeichen"] for z in aufbereiten(m)["betriebsmittel"]}
    assert "=NT24+SS1-T1" in rk and "=FB1+SS1-G1" not in rk          # Netzteil wie im Hausstil-PDF
    erzeuge_hausstil_pdf(m, str(tmp_path / "h.pdf"))
    assert "-T1" in "".join(_texte(tmp_path / "h.pdf"))


def test_ausgabe_importiert_den_planungskern_nicht():
    import ast
    for modul in ("zeichnen", "hausstil", "eplan_adapter"):
        baum = ast.parse((Path(__file__).resolve().parent.parent / "slpgen" / f"{modul}.py").read_text(encoding="utf-8"))
        importe = {n.module for n in ast.walk(baum) if isinstance(n, ast.ImportFrom)} | \
            {a.name for n in ast.walk(baum) if isinstance(n, ast.Import) for a in n.names}
        assert not importe & {"regeln", "motor", "projektmodell"}, (modul, importe)


def test_geaendertes_hausprofil_nach_dem_planen_wird_erkannt(tmp_path):
    m = regeln.plane(_projekte()["beispiel"], STAMM)
    m.kennzeichen = kennzeichne(m)
    from slpgen.hausstil import lade_hausstil
    stil = lade_hausstil(None)
    stil["kennbuchstaben"]["netzteil"] = "G"
    with pytest.raises(RegelFehler, match="Hausprofil"):
        erzeuge_hausstil_pdf(m, str(tmp_path / "h.pdf"), stil)


def test_ausgabe_braucht_keinen_geraetestamm(tmp_path):
    """Planmodell trägt den Artikelauszug selbst; Zeichnen ohne Projekt und Gerätestamm."""
    m = regeln.plane(_projekte()["beispiel"], STAMM)
    assert {"IND-M12-PNP", "NT-24-05", "SPS-DI16", "MSS-6.3", "KAB-4G1.5", "HS-3P-40"} <= set(m.artikel)
    assert "KUNDE" not in m.artikel and "NT-24-20" not in m.artikel        # Beistellung / nicht gewählt
    (tmp_path / "pm").mkdir()
    m.speichere(tmp_path / "pm" / "P_Planmodell.json")
    main(["zeichnen", str(tmp_path / "pm" / "P_Planmodell.json"), "--profil", str(tmp_path / "x.yaml")])
    assert (tmp_path / "pm" / "P-2026-001_Stromlaufplan.pdf").exists()
    assert "IND-M12-PNP" in (tmp_path / "pm" / "P-2026-001_Stueckliste.csv").read_text(encoding="utf-8")


@pytest.mark.parametrize("inhalt, meldung", [
    ("{kaputt", "JSON beschädigt"),
    (json.dumps({"schema": "planmodell/0"}), "erwartet „planmodell/1“"),
    (json.dumps({"schema": SCHEMA_PLANMODELL, "fremd": 1, "projekt": {}}), "unbekannte Felder: fremd"),
    (json.dumps({"schema": SCHEMA_PLANMODELL, "projekt": {}, "kabel": [{"bmk": "-W1"}]}), "Pflichtfeld „von“ fehlt"),
    ("[1, 2]", "JSON-Objekt"),
    (json.dumps({"schema": SCHEMA_PLANMODELL, "projekt": None}), "keine „nummer“"),
    (json.dumps({"schema": SCHEMA_PLANMODELL, "projekt": {"nummer": "A"}, "seiten": [[1, "x", "feld"]]}),
     "Nr, Titel, Art, Index"),
    (json.dumps({"schema": SCHEMA_PLANMODELL, "projekt": {"nummer": "A"}, "artikel": []}), "„artikel“ muss ein Objekt"),
    (json.dumps({"schema": SCHEMA_PLANMODELL, "projekt": {"nummer": "A"}, "betriebsmittel": [
        {"bmk": "-B1", "artikel": "X", "bezeichnung": "b", "seite": "drei"}]}), "„seite“ = 'drei' hat falschen Typ"),
])
def test_fehlerhaftes_planmodell_klartext(tmp_path, inhalt, meldung):
    (tmp_path / "pm.json").write_text(inhalt, encoding="utf-8")
    with pytest.raises(RegelFehler, match=meldung):
        Planmodell.lade(tmp_path / "pm.json")


@pytest.mark.parametrize("name", ["beispiel", "ki_bausteine", "selektiv"])
def test_eplan_stub_gegen_schema(tmp_path, name):
    from slpgen.eplan_adapter import OHNE_ARTIKEL, PFLICHT_BETRIEBSMITTEL, aufbereiten, uebertrage
    m = regeln.plane(_projekte()[name], STAMM)
    m.speichere(tmp_path / "pm.json")
    d = aufbereiten(Planmodell.lade(tmp_path / "pm.json"))         # Adapter liest nur das Planmodell
    rk = [z["referenzkennzeichen"] for z in d["betriebsmittel"]]
    assert len(rk) == len(set(rk)) == len(m.betriebsmittel)
    for z in d["betriebsmittel"]:
        teil = z["kategorie"] in OHNE_ARTIKEL          # Teilsignal/Kanal/Meldung: Artikel trägt das Hauptgerät
        pflicht = [f for f in PFLICHT_BETRIEBSMITTEL if not (teil and f == "artikelnummer")]
        assert all(z[f] not in (None, "") for f in pflicht), z
        assert not teil or z["teil_von"], z
    assert all(z["referenzkennzeichen"].startswith(m.projekt.get("anlage", "") + m.projekt.get("ort", ""))
               for z in d["betriebsmittel"])
    assert len(d["sps"]) == len(m.sps_kanaele) and len(d["klemmen"]) == len(m.klemmen)
    with pytest.raises(RegelFehler, match="noch nicht verfügbar"):
        uebertrage(m, str(tmp_path / "x"))


def test_schema_planmodell_dokument_aktuell():
    from slpgen.modell import schema_planmodell_markdown
    doku = Path(__file__).resolve().parents[2] / "docs" / "SCHEMA_PLANMODELL.md"
    assert doku.read_text(encoding="utf-8") == schema_planmodell_markdown(), "python -m slpgen schema --planmodell"
