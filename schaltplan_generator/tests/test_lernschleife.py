"""M5c: Lernschleife – Korrektur -> Hausregel (Herkunft/Datum/Geltung) -> wirkt beim nächsten Plan -> Regressionstest."""
import copy
from pathlib import Path

import pytest
import yaml
from pypdf import PdfReader

from slpgen.cli import main
from slpgen.lernschleife import erfasse_korrektur, lade_regeln, pruefe_regressionen, wende_an
from slpgen.modell import RegelFehler

B = Path(__file__).resolve().parent.parent / "beispiele"
STAMM = yaml.safe_load((B / "geraetestamm.yaml").read_text(encoding="utf-8"))
BEISPIEL = yaml.safe_load((B / "projekt_beispiel.yaml").read_text(encoding="utf-8"))


def test_korrektur_wirkt_beim_naechsten_plan_und_steht_im_nachweis(tmp_path):
    profil = tmp_path / "hausprofil" / "profil.yaml"
    projekt = tmp_path / "p.yaml"
    projekt.write_text(yaml.safe_dump(BEISPIEL, allow_unicode=True), encoding="utf-8")
    main(["korrektur", str(projekt), "--art", "artikel_ersetzen", "--wenn", "OPT-REF-PNP", "--dann", "IND-M12-PNP",
          "--grund", "Hausstandard: induktiv statt optisch", "--profil", str(profil)])
    r = lade_regeln(profil.with_name("hausregeln.yaml"))[0]
    assert (r["id"], r["herkunft"], r["grund"]) == ("R1", "p.yaml", "Hausstandard: induktiv statt optisch") and r["datum"]
    main(["generieren", str(projekt), "--ausgabe", str(tmp_path / "aus"), "--profil", str(profil)])
    pm = yaml.safe_load((tmp_path / "aus" / "P-2026-001_Planmodell.json").read_text(encoding="utf-8"))
    assert "OPT-REF-PNP" not in {b["artikel"] for b in pm["betriebsmittel"]}
    text = "".join(s.extract_text() for s in PdfReader(str(tmp_path / "aus" / "P-2026-001_Stromlaufplan_Hausstil.pdf")).pages)
    assert "Hausregel R1 (Artikel ersetzen): B3 OPT-REF-PNP → IND-M12-PNP" in text


def test_regressionstest_erkennt_spaetere_widersprechende_regel(tmp_path):
    pfad = tmp_path / "hausregeln.yaml"
    erfasse_korrektur(pfad, "gruppe_setzen", "MV-24-4W", "DO-Last", "Projekt A", "", BEISPIEL, STAMM)
    erfasse_korrektur(pfad, "artikel_ersetzen", "MV-24-4W", "LMP-24-GN", "Projekt B", "", BEISPIEL, STAMM)
    befunde = pruefe_regressionen(lade_regeln(pfad))
    assert befunde and "R1" in befunde[0]                       # R2 verändert den Fall von R1


def test_geltung_ab_datum_und_inaktiv():
    regeln = [{"id": "R1", "art": "gruppe_setzen", "wenn": "IND-M12-PNP", "dann": "Neu", "gilt_ab": "2027-01-01",
               "aktiv": True}, {"id": "R2", "art": "gruppe_setzen", "wenn": "OPT-REF-PNP", "dann": "X", "aktiv": False}]
    neu, meldungen = wende_an(copy.deepcopy(BEISPIEL), regeln)
    assert not meldungen and neu == BEISPIEL                    # Projekt von 2026, R2 inaktiv
    spaeter = copy.deepcopy(BEISPIEL)
    spaeter["projekt"]["datum"] = "2027-03-01"
    neu, meldungen = wende_an(spaeter, regeln)
    assert len(meldungen) == 2 and {fg["gruppe"] for fg in neu["feldgeraete"] if fg["artikel"] == "IND-M12-PNP"} == {"Neu"}


@pytest.mark.parametrize("art, wenn, dann, meldung", [
    ("loeschen", "MV-24-4W", "x", "unbekannt"), ("artikel_ersetzen", "GIBTSNICHT", "MV-24-4W", "gibt es nicht"),
    ("artikel_ersetzen", "MV-24-4W", "GIBTSNICHT", "Ersatzartikel"), ("gruppe_setzen", "ZAEHLER-PULS", "X", "nicht vor")])
def test_korrektur_klartextfehler(tmp_path, art, wenn, dann, meldung):
    with pytest.raises(RegelFehler, match=meldung):
        erfasse_korrektur(tmp_path / "h.yaml", art, wenn, dann, "x", "", BEISPIEL, STAMM)


def test_widerspruch_wird_abgelehnt_und_cli_hausregeln(tmp_path, capsys):
    pfad = tmp_path / "hausprofil" / "hausregeln.yaml"
    erfasse_korrektur(pfad, "gruppe_setzen", "IND-M12-PNP", "A", "x", "", BEISPIEL, STAMM)
    with pytest.raises(RegelFehler, match="Widerspruch zu Hausregel R1"):
        erfasse_korrektur(pfad, "gruppe_setzen", "IND-M12-PNP", "B", "x", "", BEISPIEL, STAMM)
    main(["hausregeln", "--profil", str(tmp_path / "hausprofil" / "profil.yaml")])
    aus = capsys.readouterr().out
    assert "R1 [aktiv] 24-V-Gruppe setzen: IND-M12-PNP → A" in aus and "1 Fälle unverändert" in aus
