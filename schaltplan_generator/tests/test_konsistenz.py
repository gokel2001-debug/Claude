"""M4c: Konsistenzprüfungen (Prüfbericht) – Testkorpus ohne Fehler, jede Fehlerart wird erkannt."""
import copy
from pathlib import Path

import pytest
import yaml

from slpgen import regeln
from slpgen.cli import main
from slpgen.konsistenz import FEHLER, HINWEIS, KENNZAHL, kennzahlen, pruefe_plan
from slpgen.modell import Klemme, SpsKanal
from slpgen.projektmodell import bereit_machen

B = Path(__file__).resolve().parent.parent / "beispiele"
STAMM = yaml.safe_load((B / "geraetestamm.yaml").read_text(encoding="utf-8"))
VORGABEN = yaml.safe_load((B / "hausvorgaben.yaml").read_text(encoding="utf-8"))
BEISPIEL = yaml.safe_load((B / "projekt_beispiel.yaml").read_text(encoding="utf-8"))


def _korpus():
    """Testkorpus: Beispiel, KI-Beispiel (alle Bausteine), Selektivmodul, ohne Motoren, viele Feldgeräte."""
    ki, _ = bereit_machen(yaml.safe_load((B / "projektmodell_ki_beispiel.yaml").read_text(encoding="utf-8")),
                          STAMM, VORGABEN)
    selektiv = copy.deepcopy(BEISPIEL)
    selektiv["versorgung_24V"].update(verteilung="selektivmodul", selektivmodul="SEL-24-4K")
    ohne_motoren = copy.deepcopy(BEISPIEL)
    ohne_motoren["motoren"] = []
    viele = copy.deepcopy(BEISPIEL)
    viele["feldgeraete"] += [{"bmk": f"B{20 + i}", "artikel": "IND-M12-PNP", "funktion": f"Sensor {i}",
                              "gruppe": "Sensorik"} for i in range(20)]
    return {"beispiel": BEISPIEL, "ki": ki, "selektiv": selektiv, "ohne_motoren": ohne_motoren, "viele": viele}


@pytest.mark.parametrize("name", list(_korpus()))
def test_testkorpus_ohne_fehler(name):
    m = regeln.plane(copy.deepcopy(_korpus()[name]), STAMM)
    befunde = pruefe_plan(m)
    sicher = [b for b in befunde if b.pruefung == "Sicherheit"]
    assert bool(sicher) == (name == "ki")                    # KI-Beispiel fragt nach Not-Halt -> Platzhalter (A49)
    assert not [b for b in befunde if b.art == FEHLER and b.pruefung != "Sicherheit"], befunde
    assert not [b for b in befunde if b.pruefung == "Text"]          # keine Wortdopplung mehr (M4a Elektro 8)


def _plan():
    return regeln.plane(copy.deepcopy(BEISPIEL), STAMM)


def _stoere_adresse(m):
    m.sps_kanaele[1].adresse = m.sps_kanaele[0].adresse


def _stoere_klemme(m):
    m.klemmen.append(Klemme("-X1", m.klemmen[0].nr, "Signal", "x", "-B1:4"))


def _stoere_verweis(m):
    m.sps_kanaele.append(SpsKanal("-A2", 15, "DI", "%I9.9", "-B99", "Phantom"))


def _stoere_bmk(m):
    m.betriebsmittel.append(copy.deepcopy(m.betriebsmittel[-1]))


def _stoere_sicherung(m):
    m.absicherungen[0].i_gruppe_A = m.absicherungen[0].i_nenn_A + 1


def _stoere_kanal(m):
    m.sps_kanaele[0].kanal = 99


@pytest.mark.parametrize("stoerung, pruefung", [
    (_stoere_adresse, "SPS"), (_stoere_klemme, "Klemmen"), (_stoere_verweis, "Verweis"), (_stoere_bmk, "Kennzeichen"),
    (_stoere_sicherung, "Absicherung"), (_stoere_kanal, "SPS"), (lambda m: setattr(m.kabel[0], "i_z_A", 0.5), "Leitungsschutz"),
    (lambda m: setattr(m.kabel[0], "du_prozent", 12.0), "Spannungsfall"),
    (lambda m: m.bm(m.bm("-M1").daten["mss"]).daten.update(i_r_A=40.0), "Motorschutz"),
    (lambda m: m.absicherungen.__setitem__(slice(None), [a for a in m.absicherungen if "-B1" not in a.verbraucher]),
     "Potential"),
    (lambda m: setattr(m.klemmen[1], "ziel_aussen", m.klemmen[0].ziel_aussen), "Klemmen"),
    (lambda m: setattr(m.klemmen[0], "nr", 0), "Klemmen"),
    (lambda m: m.bilanz.update(i_bedarf_A=99.0), "Netzteil"),
    (lambda m: m.bm(next(k.geraet_bmk for k in m.sps_kanaele if k.art == "DO")).daten.update(i_A=2.0), "DO-Last")])
def test_jede_fehlerart_wird_erkannt(stoerung, pruefung):
    m = _plan()
    stoerung(m)
    fehler = {b.pruefung for b in pruefe_plan(m) if b.art == FEHLER}
    assert pruefung in fehler and fehler <= {pruefung, "Klemmen", "Verweis", "Potential", "Leitungsschutz"}  # nichts Fremdes


def test_hinweise_luecke_und_textdopplung():
    m = _plan()
    m.klemmen = [k for k in m.klemmen if not (k.leiste == "-X1" and k.nr == 2)]
    m.sps_kanaele[0].funktion = "Endlage Endlage vorne"
    arten = {(b.art, b.pruefung) for b in pruefe_plan(m)}
    assert (HINWEIS, "Klemmen") in arten and (HINWEIS, "Text") in arten


def test_kennzahlen_und_cli(tmp_path, capsys):
    m = _plan()
    k = kennzahlen(m, 40)
    assert k["Seite"] == 40 and k["Klemme"] == len(m.klemmen) and k[KENNZAHL] > 0
    assert k["Kabel"] == len(m.kabel) + len([b for b in m.betriebsmittel if b.kategorie in ("sensor", "aktor")])
    m.speichere(tmp_path / "pm.json")
    main(["pruefbericht", str(tmp_path / "pm.json")])
    aus = capsys.readouterr().out
    assert "Prüfbericht: keine Befunde" in aus and "Kennzahlen:" in aus
    _stoere_adresse(m)
    m.speichere(tmp_path / "pm.json")
    with pytest.raises(SystemExit, match="FEHLER"):
        main(["pruefbericht", str(tmp_path / "pm.json")])


def test_nachweis_enthaelt_pruefbericht_motorleitungen_und_kennzahlen(tmp_path):
    from pypdf import PdfReader
    main(["generieren", str(B / "projekt_beispiel.yaml"), "--ausgabe", str(tmp_path), "--profil", str(tmp_path / "x.yaml")])
    text = "".join(p.extract_text() for p in PdfReader(str(tmp_path / "P-2026-001_Stromlaufplan_Hausstil.pdf")).pages)
    assert "7 Prüfbericht (Konsistenz)" in text and "2a Leitungen Motor" in text and "8 Kennzahlen" in text


def test_ungueltige_werte_ergeben_befund_statt_absturz():
    m = _plan()
    next(b for b in m.betriebsmittel if b.kategorie == "sps_di").daten["bytebereich"] = [0]
    assert any(b.pruefung == "Daten" and b.art == FEHLER for b in pruefe_plan(m))


def test_zeichnen_prueft_frisch(tmp_path):
    """Software-Befund M4c: geändertes planmodell.json -> zeichnen meldet FEHLER, Nachweis zeigt ihn."""
    from pypdf import PdfReader
    main(["generieren", str(B / "projekt_beispiel.yaml"), "--ausgabe", str(tmp_path), "--profil", str(tmp_path / "x.yaml")])
    pm = tmp_path / "P-2026-001_Planmodell.json"
    from slpgen.modell import Planmodell
    m = Planmodell.lade(pm)
    _stoere_adresse(m)
    m.speichere(pm)
    with pytest.raises(SystemExit, match="FEHLER"):
        main(["zeichnen", str(pm), "--profil", str(tmp_path / "x.yaml")])
    text = "".join(p.extract_text() for p in PdfReader(str(tmp_path / "P-2026-001_Stromlaufplan_Hausstil.pdf")).pages)
    assert "FEHLER (SPS)" in text


def test_stempel_und_projektordner(tmp_path):
    """M4d: bei FEHLER roter Vermerk auf jeder Seite; ohne --ausgabe landen Ergebnisse im Projektordner."""
    from pypdf import PdfReader

    from slpgen.hausstil import erzeuge_hausstil_pdf
    from slpgen.zeichnen import erzeuge_pdf
    projekt = tmp_path / "Kunde_A" / "projekt.yaml"
    projekt.parent.mkdir()
    projekt.write_text((B / "projekt_beispiel.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    main(["generieren", str(projekt), "--profil", str(tmp_path / "x.yaml")])
    pdf = tmp_path / "Kunde_A" / "ausgabe" / "P-2026-001_Stromlaufplan_Hausstil.pdf"
    assert pdf.exists() and "NICHT FÜR FERTIGUNG" not in PdfReader(str(pdf)).pages[0].extract_text()
    m = _plan()
    _stoere_adresse(m)
    erzeuge_pdf(m, str(tmp_path / "a.pdf"))
    erzeuge_hausstil_pdf(m, str(tmp_path / "h.pdf"))
    for f in ("a.pdf", "h.pdf"):
        assert all("NICHT FÜR FERTIGUNG" in p.extract_text() for p in PdfReader(str(tmp_path / f)).pages)


def test_feldleitungslaenge_aus_projektmodell():
    from slpgen.hausstil import Hausplan, lade_hausstil
    p = copy.deepcopy(BEISPIEL)
    p["feldgeraete"][0]["laenge_m"] = 17
    hp = Hausplan(regeln.plane(p, STAMM), lade_hausstil(None))
    kab = {z[0]: z[4] for z in hp._kabelzeilen()}
    assert kab["=B01-W1"] == "17 m" and kab["=B02-W1"] == "nach Feldmaß"
    assert any(z[4] == "17 m" and z[3] == "-W1" for z in hp._stl_zeilen())


def test_netzteil_zu_klein_klartext():
    p = copy.deepcopy(BEISPIEL)
    p["versorgung_24V"]["netzteile"] = ["NT-24-05"]
    p["feldgeraete"] += [{"bmk": f"Y{20 + i}", "artikel": "MV-24-4W", "funktion": f"Ventil {i}", "gruppe": "DO-Last"}
                         for i in range(25)]
    with pytest.raises(Exception, match=r"größte.*NT-24-05.*größeres Netzteil ergänzen") as e:
        regeln.plane(p, STAMM)
    assert "[" not in str(e.value)                                   # keine Python-Listenschreibweise


def test_stempel_im_rand_und_csv(tmp_path):
    from slpgen.zeichnen import stueckliste_csv
    m = _plan()
    assert not stueckliste_csv(m).startswith("NICHT")
    _stoere_adresse(m)
    assert stueckliste_csv(m).startswith("NICHT FÜR FERTIGUNG")


def test_sicherheit_nur_als_platzhalter(tmp_path):
    """M7b: Not-Halt/PL -> rot gerahmte Platzhalterseite, Hinweis im Prüfbericht, keine Sicherheitsschaltung."""
    from pypdf import PdfReader

    from slpgen.hausstil import erzeuge_hausstil_pdf
    p = copy.deepcopy(BEISPIEL)
    p["sicherheit"] = {"not_halt": True, "pl": "PL d", "funktionen": "Schutztür"}
    m = regeln.plane(p, STAMM)
    assert [b.art for b in pruefe_plan(m) if b.pruefung == "Sicherheit"] == [FEHLER]   # ohne Freigabevermerk gesperrt
    seiten = erzeuge_hausstil_pdf(m, str(tmp_path / "h.pdf"))
    i = [a for a, _, _ in seiten].index("SIK")
    text = PdfReader(str(tmp_path / "h.pdf")).pages[i].extract_text()
    assert "PLATZHALTER" in text and "PL d" in text and "Schutztür" in text
    ohne = regeln.plane(copy.deepcopy(BEISPIEL), STAMM)
    assert "_sicherheit" not in ohne.projekt                                   # ohne Anforderung keine Seite
    frage = copy.deepcopy(BEISPIEL)
    frage["offene_fragen"] = ["Not-Halt: welcher PL?"]
    assert regeln.plane(frage, STAMM).projekt["_sicherheit"]["pl"] == ""        # aus offener Frage abgeleitet


@pytest.mark.parametrize("text, treffer", [
    ("Not-Halt gefordert?", True), ("NOT-AUS am Schrank", True), ("Not Halt vor Ort", True), ("Schutztür Pumpenraum", True),
    ("Lichtgitter am Einlauf", True), ("Sicherheitsrelais vorhanden?", True), ("Kategorie 3 nach ISO 13849", True),
    ("welcher PL d?", True), ("SIL 2 gefordert", True), ("Emergency stop", True),
    ("Welcher PL ist gefordert?", True), ("Zuhaltung Schutztür", True),
    ("Silo Füllstand", False), ("Ventil auf", False), ("Fossil", False), ("PLZ Baustelle", False), ("Pl. 3 prüfen", False),
    ("PLC Kommunikation", False), ("SPS PLC", False), ("Notausgang Leuchte", False), ("Sicherheitsbeleuchtung", False),
    ("Wendeschütz verriegelt", False), ("Kategorie 3 Überspannung", False),
])
def test_sicherheit_suchmuster(text, treffer):
    """Prüfer M7b Elektro 3 / Software 1+2: Auslöser vollständig, keine Fehlalarme bei üblichen Wörtern."""
    assert bool(regeln.SICHERHEIT_MUSTER.search(text)) == treffer


def test_sicherheit_feldgeraet_und_freigabe(tmp_path):
    """Prüfer M7b Elektro 1/4/5: Not-Halt-Taster als Feldgerät -> FEHLER je Gerät; Freigabevermerk hebt die Sperre auf."""
    p = copy.deepcopy(BEISPIEL)
    p["feldgeraete"].append({"bmk": "S9", "artikel": "IND-M12-PNP", "funktion": "Not-Halt Taster Schrank", "gruppe": "Sensorik"})
    m = regeln.plane(p, STAMM)
    si = m.projekt["_sicherheit"]
    assert si["geraete"] == ["-S9"] and si["not_halt"] is None                  # nichts selbst festgelegt
    fehler = [b.text for b in pruefe_plan(m) if b.pruefung == "Sicherheit" and b.art == FEHLER]
    assert len(fehler) == 2 and "-S9" in fehler[1]
    p["sicherheit"] = {"freigabe": "M. Muster, 2026-11-21"}
    befunde = [b for b in pruefe_plan(regeln.plane(p, STAMM)) if b.pruefung == "Sicherheit"]
    assert [b.art for b in befunde] == [HINWEIS, FEHLER] and "M. Muster" in befunde[0].text   # Gerät bleibt FEHLER (N3)
    p["sicherheit"]["ausgenommen"] = "S9"
    assert [b.art for b in pruefe_plan(regeln.plane(p, STAMM)) if b.pruefung == "Sicherheit"] == [HINWEIS, HINWEIS]
    for unsinn in ("NEIN", "offen", "-", "Muster"):                         # N2: nur „Name, Datum“
        p["sicherheit"]["freigabe"] = unsinn
        assert FEHLER in [b.art for b in pruefe_plan(regeln.plane(p, STAMM)) if b.pruefung == "Sicherheit"][:1]
    p["sicherheit"]["freigabe"] = "M. Muster, 21.11.2026"
    p["offene_fragen"] = ["Not-Halt?"]                                     # N1: KI-Antwort darf nicht freigeben
    erste = next(b for b in pruefe_plan(regeln.plane(p, STAMM)) if b.pruefung == "Sicherheit")
    assert erste.art == FEHLER and "KI-Antwort" in erste.text


def test_sicherheit_excel_und_rundreise(tmp_path):
    """Prüfer M7b Software 5/7: Excel-Blatt Sicherheit; _sicherheit übersteht planmodell.json."""
    from slpgen.excel_eingabe import lade_excel, schreibe_vorlage
    from slpgen.modell import Planmodell
    p = copy.deepcopy(BEISPIEL)
    p["sicherheit"] = {"not_halt": True, "pl": "PL d"}
    schreibe_vorlage(p, STAMM, tmp_path / "p.xlsx")
    assert lade_excel(tmp_path / "p.xlsx")["sicherheit"] == {"not_halt": "ja", "pl": "PL d"}
    leer = copy.deepcopy(BEISPIEL)
    schreibe_vorlage(leer, STAMM, tmp_path / "leer.xlsx")
    assert "sicherheit" not in lade_excel(tmp_path / "leer.xlsx")
    m = regeln.plane(p, STAMM)
    m.speichere(tmp_path / "pm.json")
    assert Planmodell.lade(tmp_path / "pm.json").projekt["_sicherheit"] == m.projekt["_sicherheit"]
