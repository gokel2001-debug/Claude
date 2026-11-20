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
    (("feldgeraete",), KeyError, "„feldgeraete“ (Sensoren, Aktoren und Bausteine im Feld) fehlt"),
    (("projekt", "nummer"), KeyError, "(„nummer“) fehlt"),
    (("feldgeraete", 0, "artikel"), "IND-M12-PNPX", "passend wären: IND-M12-PNP"),
    (("feldgeraete", 0, "bmk"), "B.1", "ungültig"),
    (("feldgeraete", 1, "bmk"), "-b1", "schon bei Feldgerät B1 (1. Eintrag)"),
    (("feldgeraete", 0, "farbe"), "rot", "unbekanntes Feld „farbe“"),
    (("feldgeraete", 0, "typical"), "gibtsnicht", "Baustein „gibtsnicht“"),
    (("motoren", 0, "i_N_A"), "viel", "keine Zahl"),
    (("motoren", 0, "cos_phi"), 1.5, "außerhalb"),
    (("einspeisung", "hauptschalter"), "NT-24-05", "erwartet hauptschalter"),
    (("versorgung_24V", "verteilung"), "zentral", "erlaubt: einzelsicherungen"),
    (("sps", "module_kandidaten"), {"DI": "SPS-DI16"}, "ohne Eintrag für DO, AI, AO"),
    (("leitungen", "freigegeben"), "vielleicht", "ja oder nein"),
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
    for teil in ("Strombelastbarkeitstabelle", "„XX“", "(„laenge_m“) fehlt", "„versorgung_24V“", "„sps“", "(„hauptschalter“) fehlt"):
        assert teil in text
    assert "Projektmodell: 6 Punkte zu korrigieren" in text


def test_hausvorgaben_ergaenzen_und_plan_entsteht():
    d = _nur_projektangaben()
    d["motoren"][0]["p_kW"] = "0,75"                     # Komma wie im Lastenheft
    d["motoren"][0]["bmk"] = "m1"
    modell, ergaenzt = bereit_machen(d, STAMM, VORGABEN)
    text = "\n".join(ergaenzt)
    assert "Hauptschalter" in text and "HS-3P-40" in text and "SPS-CPU" in text and "1.5 13.1" in text
    assert modell["motoren"][0]["p_kW"] == 0.75 and modell["motoren"][0]["bmk"] == "M1"
    assert "versorgung_24V" not in d                         # Eingabe bleibt unverändert
    m = regeln.plane(modell, STAMM)
    assert m.bilanz["netzteil"] == regeln.plane(copy.deepcopy(BEISPIEL), STAMM).bilanz["netzteil"]


def test_projektwert_geht_vor_hausvorgabe():
    d = copy.deepcopy(BEISPIEL)
    d["versorgung_24V"]["reserve"] = 0.5
    modell, ergaenzt = bereit_machen(d, STAMM, VORGABEN)
    assert modell["versorgung_24V"]["reserve"] == 0.5 and not any("Reserve" in x for x in ergaenzt)


def test_schema_dokument_aktuell():
    doku = Path(__file__).resolve().parents[2] / "docs" / "SCHEMA_PROJEKTMODELL.md"
    assert doku.read_text(encoding="utf-8") == schema_markdown(), "python -m slpgen schema ausführen"


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
    assert "vollständig" in aus and "Sensoren PNP angenommen" in aus and "SPS-CPU" in aus


def test_cli_generieren_mit_ki_modell(tmp_path):
    gut = tmp_path / "projektmodell.yaml"
    gut.write_text(yaml.safe_dump(_nur_projektangaben(), allow_unicode=True), encoding="utf-8")
    main(["generieren", str(gut), "--stamm", str(B / "geraetestamm.yaml"), "--vorgaben", str(B / "hausvorgaben.yaml"),
          "--ausgabe", str(tmp_path / "aus"), "--profil", str(tmp_path / "keins.yaml")])
    assert (tmp_path / "aus" / "P-2026-001_Stromlaufplan.pdf").exists()


# ---- Robustheit (Prüfer-Befunde M2a): jede Störung -> RegelFehler im Klartext ODER plane() läuft --------
STOERUNGEN = [
    (("versorgung_24V",), None), (("sps",), None), (("leitungen",), None), (("motoren",), None),
    (("feldgeraete", 0, "artikel"), ["IND-M12-PNP"]), (("feldgeraete", 0, "typical"), ["x"]),
    (("feldgeraete", 0, "artikel"), "NT-24-05"),
    (("sps", "module_kandidaten", "DI"), "NT-24-05"), (("sps", "module_kandidaten", "DI"), "GIBTSNICHT"),
    (("sps", "adressschema", "DI"), "%I{byt}.{bit}"), (("sps", "adressschema", "DI"), 5),
    (("leitungen", "i_z_A"), {"1,5": 13.1, "2.50": "17,4"}), (("leitungen", "i_z_A"), {1.5: None}),
    (("leitungen", "freigegeben"), "ja"), (("projekt", "nummer"), "../../x"), (("projekt", "revision"), False),
    (("motoren", 0, "laenge_m"), "12 m"), (("einspeisung", "hauptschalter"), None),
    (("versorgung_24V", "verteilung"), "selektivmodul"), (("feldgeraete",), {"bmk": "B1"}),
]


@pytest.mark.parametrize("pfad, wert", STOERUNGEN)
def test_keine_stoerung_fuehrt_zum_absturz(pfad, wert):
    d = copy.deepcopy(BEISPIEL)
    _setze(d, pfad, wert)
    try:
        modell, _ = bereit_machen(d, STAMM, VORGABEN)
    except RegelFehler as e:
        assert "zu korrigieren" in str(e)
        return
    regeln.plane(modell, STAMM)


def test_listen_und_zahlen_vereinheitlicht():
    d = copy.deepcopy(BEISPIEL)
    d["leitungen"]["i_z_A"] = {"1,5": "13,1", "2.50": 17.4}
    d["leitungen"]["freigegeben"] = "nein"
    d["motoren"][0]["laenge_m"] = "12 m"
    modell, _ = bereit_machen(d, STAMM, VORGABEN)
    assert modell["leitungen"]["i_z_A"] == {1.5: 13.1, 2.5: 17.4} and modell["leitungen"]["freigegeben"] is False
    assert modell["motoren"][0]["laenge_m"] == 12.0
    regeln.plane(modell, STAMM)


@pytest.mark.parametrize("inhalt, erwartet", [
    ("Hier ist das Projektmodell:\n```yaml\nprojekt: {nummer: A}\n```\nViel Erfolg!", None),
    ("projekt:\n\tnummer: A\n", "Tabulator"),
    ("feldgeraete:\n  - {bmk: B1}\nfeldgeraete:\n  - {bmk: B2}\n", "doppelt"),
    ("projekt: {datum: 2026-13-01}\n", "Datum"),
])
def test_ki_antwort_einlesen(tmp_path, inhalt, erwartet):
    from slpgen.cli import lade_yaml
    f = tmp_path / "ki.yaml"
    f.write_text(inhalt, encoding="utf-8")
    if erwartet is None:
        assert lade_yaml(str(f)) == {"projekt": {"nummer": "A"}}
    else:
        with pytest.raises(RegelFehler, match=erwartet):
            lade_yaml(str(f))


def test_ansi_datei_wird_gelesen(tmp_path):
    from slpgen.cli import lade_yaml
    f = tmp_path / "ki.yaml"
    f.write_bytes("projekt: {bezeichnung: Förderband}\n".encode("cp1252"))
    assert lade_yaml(str(f))["projekt"]["bezeichnung"] == "Förderband"


def test_fehlende_vorgaben_und_unerwarteter_fehler_ohne_traceback(tmp_path, monkeypatch):
    gut = tmp_path / "gut.yaml"
    gut.write_text(yaml.safe_dump(_nur_projektangaben(), allow_unicode=True), encoding="utf-8")
    with pytest.raises(SystemExit, match="Hausvorgaben nicht gefunden"):
        main(["pruefen", str(gut), "--vorgaben", str(tmp_path / "fehlt.yaml")])
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("slpgen.projektmodell.bereit_machen", lambda *a: 1 / 0)
    with pytest.raises(SystemExit, match="Unerwarteter Programmfehler"):
        main(["pruefen", str(gut)])
    assert "ZeroDivisionError" in (tmp_path / "slpgen_fehler.log").read_text(encoding="utf-8")
