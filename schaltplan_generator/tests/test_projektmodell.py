"""M2a: Schema Projektmodell v1 – Prüfung mit Lücken im Klartext, Hausvorgaben, CLI."""
import copy
from pathlib import Path

import pytest
import yaml

from slpgen import regeln
from slpgen.cli import main
from slpgen.excel_eingabe import lade_excel
from slpgen.modell import RegelFehler
from slpgen.projektmodell import bereit_machen, pruefe, schema_markdown

B = Path(__file__).resolve().parent.parent / "beispiele"
STAMM = yaml.safe_load((B / "geraetestamm.yaml").read_text(encoding="utf-8"))
BEISPIEL = yaml.safe_load((B / "projekt_beispiel.yaml").read_text(encoding="utf-8"))
VORGABEN = yaml.safe_load((B / "hausvorgaben.yaml").read_text(encoding="utf-8"))


def _nur_projektangaben():
    """So liefert die KI-Aufbereitung: nur P-Abschnitte, Hausvorgaben fehlen."""
    d = copy.deepcopy(BEISPIEL)
    for k in ("versorgung_24V", "sps", "leitungen"):
        d.pop(k)
    d["einspeisung"].pop("hauptschalter")
    return d


def test_beispiele_yaml_und_excel_ohne_luecke():
    assert pruefe(BEISPIEL, STAMM) == []
    assert pruefe(lade_excel(str(B / "Projekt_Vorlage.xlsx")), STAMM) == []


def _setze(d, pfad, wert):
    *weg, letzter = pfad
    ziel = d
    for k in weg:
        ziel = ziel[k]
    if wert is KeyError:
        del ziel[letzter]
    else:
        ziel[letzter] = wert


@pytest.mark.parametrize("pfad, wert, erwartet", [
    (("feldgeraete",), KeyError, "„feldgeraete“ fehlt"),
    (("projekt", "nummer"), KeyError, "Pflichtangabe „nummer“ fehlt"),
    (("feldgeraete", 0, "artikel"), "IND-M12-PNPX", "passend wären: IND-M12-PNP"),
    (("feldgeraete", 0, "bmk"), "B.1", "ungültig"),
    (("feldgeraete", 1, "bmk"), "-b1", "schon bei feldgeraete Nr. 1"),
    (("feldgeraete", 0, "farbe"), "rot", "unbekanntes Feld „farbe“"),
    (("feldgeraete", 0, "typical"), "gibtsnicht", "Baustein „gibtsnicht“"),
    (("motoren", 0, "i_N_A"), "viel", "keine Zahl"),
    (("motoren", 0, "cos_phi"), 1.5, "außerhalb"),
    (("einspeisung", "hauptschalter"), "NT-24-05", "erwartet hauptschalter"),
    (("versorgung_24V", "verteilung"), "zentral", "erlaubt: einzelsicherungen"),
    (("sps", "module_kandidaten"), {"DI": "SPS-DI16"}, "ohne Eintrag für DO, AI, AO"),
    (("leitungen", "freigegeben"), "ja", "true oder false"),
    (("projekt", "datum"), "24.10.2026", "kein Datum"),
    (("annahmen",), "alles klar", "Liste von Sätzen"),
    (("schema",), "projektmodell/2", "nicht unterstützt"),
    (("anlagen",), [], "Unbekannter Abschnitt „anlagen“"),
])
def test_jede_lueckenart_erkannt(pfad, wert, erwartet):
    d = copy.deepcopy(BEISPIEL)
    _setze(d, pfad, wert)
    assert any(erwartet in x for x in pruefe(d, STAMM)), pruefe(d, STAMM)


def test_alle_luecken_auf_einmal():
    d = _nur_projektangaben()
    d["feldgeraete"][0]["artikel"] = "XX"
    d["motoren"][0]["laenge_m"] = None
    with pytest.raises(RegelFehler) as e:
        bereit_machen(d, STAMM, None)
    text = str(e.value)
    for teil in ("„XX“", "„laenge_m“ fehlt", "„versorgung_24V“ fehlt", "„sps“ fehlt", "„hauptschalter“ fehlt"):
        assert teil in text
    assert "Projektmodell unvollständig (5 Punkte)" in text


def test_hausvorgaben_ergaenzen_und_plan_entsteht():
    d = _nur_projektangaben()
    d["motoren"][0]["p_kW"] = "0,75"                     # Komma wie im Lastenheft
    d["motoren"][0]["bmk"] = "m1"
    modell, ergaenzt = bereit_machen(d, STAMM, VORGABEN)
    assert "einspeisung.hauptschalter" in ergaenzt and "sps.cpu" in ergaenzt and "leitungen.i_z_A" in ergaenzt
    assert modell["motoren"][0]["p_kW"] == 0.75 and modell["motoren"][0]["bmk"] == "M1"
    assert "versorgung_24V" not in d                         # Eingabe bleibt unverändert
    m = regeln.plane(modell, STAMM)
    assert m.bilanz["netzteil"] == regeln.plane(copy.deepcopy(BEISPIEL), STAMM).bilanz["netzteil"]


def test_projektwert_geht_vor_hausvorgabe():
    d = copy.deepcopy(BEISPIEL)
    d["versorgung_24V"]["reserve"] = 0.5
    modell, ergaenzt = bereit_machen(d, STAMM, VORGABEN)
    assert modell["versorgung_24V"]["reserve"] == 0.5 and "versorgung_24V.reserve" not in ergaenzt


def test_schema_dokument_aktuell():
    doku = Path(__file__).resolve().parents[2] / "docs" / "SCHEMA_PROJEKTMODELL.md"
    assert doku.read_text(encoding="utf-8") == schema_markdown() + "\n", "python -m slpgen schema ausführen"


def test_cli_pruefen_klartext(tmp_path, capsys):
    kaputt = tmp_path / "ki.yaml"
    kaputt.write_text("projekt:\n  nummer: 1\n bezeichnung: x\n", encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        main(["pruefen", str(kaputt), "--stamm", str(B / "geraetestamm.yaml")])
    assert "Formatfehler in Zeile" in str(e.value) and "Traceback" not in str(e.value)
    gut = tmp_path / "gut.yaml"
    d = _nur_projektangaben()
    d["annahmen"] = ["Sensoren PNP angenommen"]
    gut.write_text(yaml.safe_dump(d, allow_unicode=True), encoding="utf-8")
    main(["pruefen", str(gut), "--stamm", str(B / "geraetestamm.yaml"), "--vorgaben", str(B / "hausvorgaben.yaml")])
    aus = capsys.readouterr().out
    assert "vollständig" in aus and "Sensoren PNP angenommen" in aus and "sps.cpu" in aus


def test_cli_generieren_mit_ki_modell(tmp_path):
    gut = tmp_path / "projektmodell.yaml"
    gut.write_text(yaml.safe_dump(_nur_projektangaben(), allow_unicode=True), encoding="utf-8")
    main(["generieren", str(gut), "--stamm", str(B / "geraetestamm.yaml"), "--vorgaben", str(B / "hausvorgaben.yaml"),
          "--ausgabe", str(tmp_path / "aus"), "--profil", str(tmp_path / "keins.yaml")])
    assert (tmp_path / "aus" / "P-2026-001_Stromlaufplan.pdf").exists()
