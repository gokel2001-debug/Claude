"""M5c: Lernschleife – Korrektur -> Hausregel (Herkunft/Datum/Geltung) -> wirkt beim nächsten Plan -> Regressionstest."""
import copy
from pathlib import Path

import pytest
import yaml
from pypdf import PdfReader

from slpgen.cli import main
from slpgen.lernschleife import bestaetige, erfasse_korrektur, lade_regeln, pruefe_regressionen, wende_an
from slpgen.modell import RegelFehler

B = Path(__file__).resolve().parent.parent / "beispiele"
STAMM = yaml.safe_load((B / "geraetestamm.yaml").read_text(encoding="utf-8"))
BEISPIEL = yaml.safe_load((B / "projekt_beispiel.yaml").read_text(encoding="utf-8"))


def _projekt(tmp_path, daten=None):
    p = tmp_path / "p.yaml"
    p.write_text(yaml.safe_dump(daten or BEISPIEL, allow_unicode=True), encoding="utf-8")
    return p


def test_korrektur_wirkt_im_plan_und_steht_im_eigenen_nachweisabschnitt(tmp_path):
    profil = tmp_path / "hausprofil" / "profil.yaml"
    projekt = _projekt(tmp_path)
    main(["korrektur", str(projekt), "--art", "artikel_ersetzen", "--wenn", "OPT-REF-PNP", "--dann", "IND-M12-PNP",
          "--grund", "Hausstandard: induktiv", "--bearbeiter", "Planer A", "--profil", str(profil)])
    r = lade_regeln(profil.with_name("hausregeln.yaml"))[0][0]
    assert (r["id"], r["herkunft"], r["bearbeiter"], r["grund"]) == ("R1", "p.yaml", "Planer A", "Hausstandard: induktiv")
    main(["generieren", str(projekt), "--ausgabe", str(tmp_path / "aus"), "--profil", str(profil)])
    pm = yaml.safe_load((tmp_path / "aus" / "P-2026-001_Planmodell.json").read_text(encoding="utf-8"))
    assert "OPT-REF-PNP" not in {b["artikel"] for b in pm["betriebsmittel"]}
    text = "".join(s.extract_text() for s in PdfReader(str(tmp_path / "aus" / "P-2026-001_Stromlaufplan_Hausstil.pdf")).pages)
    assert "9 Angewendete Hausregeln" in text and "Hausregel R1 (Artikel ersetzen): B3 OPT-REF-PNP → IND-M12-PNP" in text
    assert "Hausregeln: 1 geladen aus" in text


def test_wirkungslose_und_verdeckte_regel_abgelehnt(tmp_path):
    pfad = tmp_path / "hausregeln.yaml"
    with pytest.raises(RegelFehler, match="DO-Aktoren"):
        erfasse_korrektur(pfad, "gruppe_setzen", "MV-24-4W", "Ventile", "x", "", BEISPIEL, STAMM)
    erfasse_korrektur(pfad, "artikel_ersetzen", "OPT-REF-PNP", "IND-M12-PNP", "x", "", BEISPIEL, STAMM)
    with pytest.raises(RegelFehler, match="kommt Artikel „OPT-REF-PNP“ nicht vor"):          # durch R1 ersetzt
        erfasse_korrektur(pfad, "gruppe_setzen", "OPT-REF-PNP", "X", "x", "", BEISPIEL, STAMM)
    with pytest.raises(RegelFehler, match="ändert nichts"):
        erfasse_korrektur(pfad, "gruppe_setzen", "IND-M12-PNP", "Sensorik", "x", "", BEISPIEL, STAMM)


def test_ersatzartikel_muss_passen_und_probelauf(tmp_path):
    with pytest.raises(RegelFehler, match="passt nicht"):
        erfasse_korrektur(tmp_path / "h.yaml", "artikel_ersetzen", "IND-M12-PNP", "NT-24-05", "x", "", BEISPIEL, STAMM)

    def scheitert(_):
        raise RegelFehler("Planung unmöglich")
    with pytest.raises(RegelFehler, match=r"nicht gespeichert.*Planung unmöglich"):
        erfasse_korrektur(tmp_path / "h.yaml", "gruppe_setzen", "IND-M12-PNP", "Neu", "x", "", BEISPIEL, STAMM,
                          probelauf=scheitert)
    assert not (tmp_path / "h.yaml").exists()


def test_regressionstest_und_bestaetigen(tmp_path):
    pfad = tmp_path / "hausregeln.yaml"
    erfasse_korrektur(pfad, "gruppe_setzen", "IND-M12-PNP", "Endlagen", "A", "", BEISPIEL, STAMM)
    regeln, _ = lade_regeln(pfad)
    regeln.append({"id": "R2", "art": "artikel_ersetzen", "wenn": "IND-M12-PNP", "dann": "OPT-REF-PNP", "aktiv": True})
    befunde = pruefe_regressionen(regeln)
    assert befunde and "R1" in befunde[0] and "--bestaetigen" in befunde[0]
    from slpgen.lernschleife import speichere_regeln
    speichere_regeln(pfad, regeln)
    assert bestaetige(pfad) == 2 and not pruefe_regressionen(lade_regeln(pfad)[0])


def test_kette_und_kreis():
    kette = [{"id": "R1", "art": "artikel_ersetzen", "wenn": "OPT-REF-PNP", "dann": "IND-M12-PNP"},
             {"id": "R2", "art": "artikel_ersetzen", "wenn": "IND-M12-PNP", "dann": "ZAEHLER-PULS"}]
    neu, _ = wende_an(copy.deepcopy(BEISPIEL), list(reversed(kette)))      # Reihenfolge egal
    assert {fg["artikel"] for fg in neu["feldgeraete"] if fg["bmk"] in ("B1", "B3")} == {"ZAEHLER-PULS"}
    kreis = [*kette, {"id": "R3", "art": "artikel_ersetzen", "wenn": "ZAEHLER-PULS", "dann": "OPT-REF-PNP"}]
    with pytest.raises(RegelFehler, match="Kreis"):
        wende_an(copy.deepcopy(BEISPIEL), kreis)


def test_geltung_datum_projekt_und_aus():
    r = {"id": "R1", "art": "gruppe_setzen", "wenn": "IND-M12-PNP", "dann": "Neu", "gilt_ab": "2027-01-01"}
    assert not wende_an(copy.deepcopy(BEISPIEL), [r])[1]                    # Projekt 2026-10-24
    p = copy.deepcopy(BEISPIEL)
    p["projekt"]["datum"] = "2027-03-01"
    assert wende_an(p, [r])[1]
    nur = {**r, "gilt_ab": "", "nur_projekt": "ANDERES"}
    assert not wende_an(copy.deepcopy(BEISPIEL), [nur])[1]
    assert not wende_an(copy.deepcopy(BEISPIEL), [{**r, "gilt_ab": "", "aktiv": False}])[1]
    with pytest.raises(RegelFehler, match="JJJJ-MM-TT"):
        erfasse_korrektur("x.yaml", "gruppe_setzen", "IND-M12-PNP", "Neu", "x", "", BEISPIEL, STAMM, gilt_ab="01.01.2030")


def test_beschaedigte_datei_ueberspringen_statt_abbrechen(tmp_path):
    pfad = tmp_path / "hausprofil" / "hausregeln.yaml"
    pfad.parent.mkdir()
    pfad.write_text("regeln:\n  - a\n  - {id: R2, art: gruppe_setzen, wenn: IND-M12-PNP}\n"
                    "  - {id: R3, art: gruppe_setzen, wenn: IND-M12-PNP, dann: Neu, aktiv: nein}\n", encoding="utf-8")
    regeln, hinweise = lade_regeln(pfad)
    assert not regeln and len(hinweise) == 3
    pfad.write_text("regeln: null", encoding="utf-8")
    assert lade_regeln(pfad)[1]
    projekt = _projekt(tmp_path)
    main(["generieren", str(projekt), "--ausgabe", str(tmp_path / "aus"), "--profil", str(pfad.with_name("profil.yaml"))])
    assert (tmp_path / "aus" / "P-2026-001_Stromlaufplan.pdf").exists()


def test_cli_ein_aus_loeschen_und_ids(tmp_path, capsys):
    profil = tmp_path / "hausprofil" / "profil.yaml"
    pfad = profil.with_name("hausregeln.yaml")
    erfasse_korrektur(pfad, "gruppe_setzen", "IND-M12-PNP", "A", "x", "", BEISPIEL, STAMM)
    erfasse_korrektur(pfad, "gruppe_setzen", "PT-420-2L", "B", "x", "", BEISPIEL, STAMM)
    main(["hausregel", "loeschen", "R1", "--profil", str(profil)])
    assert erfasse_korrektur(pfad, "gruppe_setzen", "OPT-REF-PNP", "C", "x", "", BEISPIEL, STAMM)["id"] == "R3"
    main(["hausregel", "aus", "R2", "--profil", str(profil)])
    main(["hausregeln", "--profil", str(profil)])
    aus = capsys.readouterr().out
    assert "R2 [aus]" in aus and "R3 [aktiv]" in aus and "gilt immer" in aus
    with pytest.raises(SystemExit, match="gibt es nicht"):
        main(["hausregel", "ein", "R9", "--profil", str(profil)])


def test_mindestquerschnitt_wirkt_auf_motorleitung_mit_vorschau(tmp_path, capsys):
    """M5e: neue Korrekturart Mindestquerschnitt (Produkt-Befund), Vorschau speichert nichts."""
    profil = tmp_path / "hausprofil" / "profil.yaml"
    projekt = _projekt(tmp_path)
    args = ["korrektur", str(projekt), "--art", "mindestquerschnitt", "--wenn", "motorleitung", "--dann", "2,5",
            "--grund", "Hausstandard Motorleitungen", "--profil", str(profil)]
    main([*args, "--vorschau"])
    assert "Vorschau" in capsys.readouterr().out and not profil.with_name("hausregeln.yaml").exists()
    main(args)
    main(["generieren", str(projekt), "--ausgabe", str(tmp_path / "aus"), "--profil", str(profil)])
    pm = yaml.safe_load((tmp_path / "aus" / "P-2026-001_Planmodell.json").read_text(encoding="utf-8"))
    assert pm["kabel"] and all(k["querschnitt_mm2"] >= 2.5 for k in pm["kabel"])
    regeln, _ = lade_regeln(profil.with_name("hausregeln.yaml"))
    assert regeln[0]["fall"]["erwartet"]["leitungen"]["min_querschnitt_mm2"] == 2.5 and not pruefe_regressionen(regeln)


def test_mindestquerschnitt_klartext(tmp_path):
    ohne_motoren = {**copy.deepcopy(BEISPIEL), "motoren": []}
    with pytest.raises(RegelFehler, match="keine Motor"):
        erfasse_korrektur(tmp_path / "h.yaml", "mindestquerschnitt", "motorleitung", "2,5", "x", "", ohne_motoren, STAMM)
    with pytest.raises(RegelFehler, match=r"z\. B\. 2,5"):
        erfasse_korrektur(tmp_path / "h.yaml", "mindestquerschnitt", "motor", "viel", "x", "", BEISPIEL, STAMM)


def test_einsteiger_hilfen(tmp_path, capsys):
    """M5e Einsteiger: Artikelliste, Groß-/Kleinschreibung, Hinweis auf neue Gruppe, klare Zahlmeldung."""
    projekt = _projekt(tmp_path)
    main(["artikelliste", str(projekt)])
    aus = capsys.readouterr().out
    assert "OPT-REF-PNP" in aus and "Sensorik" in aus
    r = erfasse_korrektur(tmp_path / "h.yaml", "artikel_ersetzen", "opt-ref-pnp", "ind-m12-pnp", "x", "", BEISPIEL, STAMM,
                          nur_vorschau=True)
    assert (r["wenn"], r["dann"]) == ("OPT-REF-PNP", "IND-M12-PNP") and not (tmp_path / "h.yaml").exists()
    r = erfasse_korrektur(tmp_path / "h.yaml", "gruppe_setzen", "IND-M12-PNP", "Sensorikk", "x", "", BEISPIEL, STAMM,
                          nur_vorschau=True)
    assert any("NEUE 24-V-Gruppe" in x for x in r["vorschau"])
    with pytest.raises(RegelFehler, match=r"0,5 bis 240"):
        erfasse_korrektur(tmp_path / "h.yaml", "mindestquerschnitt", "motorleitung", "0,3", "x", "", BEISPIEL, STAMM)


def test_mindestquerschnitt_robust_und_strengerer_wert_gilt():
    """Software-Befund M5e: leitungen leer/Komma ohne Absturz; Hausvorgabe 4 mm² schlägt Regel 2,5 mm²."""
    from slpgen.projektmodell import mit_hausvorgaben
    r = [{"id": "R1", "art": "mindestquerschnitt", "wenn": "motorleitung", "dann": "2.5"}]
    assert wende_an({"leitungen": None}, r)[0]["leitungen"]["min_querschnitt_mm2"] == 2.5
    assert wende_an({"leitungen": {"min_querschnitt_mm2": "4,0"}}, r)[0]["leitungen"]["min_querschnitt_mm2"] == "4,0"
    neu, _ = wende_an({"leitungen": {}}, r)
    zusammen, _ = mit_hausvorgaben(neu, {"leitungen": {"min_querschnitt_mm2": 4.0, "kappa": 56}})
    assert zusammen["leitungen"]["min_querschnitt_mm2"] == 4.0 and zusammen["leitungen"]["kappa"] == 56


def test_auswahl_ersetzen_programmgewaehlte_geraete(tmp_path, capsys):
    """M5f (Prüfung M7c S2): Hausregel für Geräte, die das Programm selbst wählt (Schütz/MSS/FU)."""
    profil = tmp_path / "hausprofil" / "profil.yaml"
    projekt = _projekt(tmp_path)
    main(["artikelliste", str(projekt)])
    assert "Vom Programm gewählt" in capsys.readouterr().out
    main(["korrektur", str(projekt), "--art", "auswahl_ersetzen", "--wenn", "sch-09", "--dann", "SCH-12",
          "--grund", "Hausstandard 12-A-Schütz", "--profil", str(profil)])
    main(["generieren", str(projekt), "--ausgabe", str(tmp_path / "aus"), "--profil", str(profil)])
    pm = yaml.safe_load((tmp_path / "aus" / "P-2026-001_Planmodell.json").read_text(encoding="utf-8"))
    schuetze = {b["bmk"]: b["artikel"] for b in pm["betriebsmittel"] if b["kategorie"] == "schuetz"}
    assert "SCH-09" not in schuetze.values() and schuetze["-K1"] == "SCH-12"
    assert any("Programmauswahl SCH-09 → SCH-12" in w for w in pm["warnungen"])
    regeln, _ = lade_regeln(profil.with_name("hausregeln.yaml"))
    assert regeln[0]["fall"]["erwartet"] == {"auswahl_ersetzen": {"SCH-09": "SCH-12"}} and not pruefe_regressionen(regeln)
    # Kette: SCH-12 -> SCH-18 verändert den alten Fall -> Regressionstest meldet es
    main(["korrektur", str(projekt), "--art", "auswahl_ersetzen", "--wenn", "SCH-12", "--dann", "SCH-18",
          "--profil", str(profil)])
    regeln, _ = lade_regeln(profil.with_name("hausregeln.yaml"))
    assert wende_an(BEISPIEL, regeln)[0]["auswahl_ersetzen"]["SCH-09"] == "SCH-18"
    assert pruefe_regressionen(regeln)


def test_auswahl_ersetzen_klartext(tmp_path):
    h = tmp_path / "h.yaml"

    def nie(_p):
        return set()

    with pytest.raises(RegelFehler, match="wählt das Programm nicht selbst"):
        erfasse_korrektur(h, "auswahl_ersetzen", "IND-M12-PNP", "OPT-REF-PNP", "x", "", BEISPIEL, STAMM)
    with pytest.raises(RegelFehler, match="derselben Art"):
        erfasse_korrektur(h, "auswahl_ersetzen", "SCH-09", "MSS-4", "x", "", BEISPIEL, STAMM)
    with pytest.raises(RegelFehler, match="vom Programm nicht gewählt"):
        erfasse_korrektur(h, "auswahl_ersetzen", "FU-1.5", "FU-3.0", "x", "", BEISPIEL, STAMM, planartikel=nie)

    def probelauf(p):
        from slpgen import regeln
        from slpgen.projektmodell import bereit_machen
        regeln.plane(bereit_machen(p, STAMM, yaml.safe_load((B / "hausvorgaben.yaml").read_text(encoding="utf-8")))[0],
                     STAMM)

    with pytest.raises(RegelFehler, match=r"nicht gespeichert.*MSS-4 erfüllt nicht Einstellbereich"):
        erfasse_korrektur(h, "auswahl_ersetzen", "MSS-2.5", "MSS-4", "x", "", BEISPIEL, STAMM, probelauf=probelauf)
    assert not h.exists()


def test_auswahl_ersetzen_kreis():
    regeln = [{"id": "R1", "art": "auswahl_ersetzen", "wenn": "SCH-09", "dann": "SCH-12"},
              {"id": "R2", "art": "auswahl_ersetzen", "wenn": "SCH-12", "dann": "SCH-09"}]
    with pytest.raises(RegelFehler, match="Kreis"):
        wende_an(BEISPIEL, regeln)
