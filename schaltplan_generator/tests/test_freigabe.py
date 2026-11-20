import pytest
import yaml
from openpyxl import load_workbook

from slpgen.freigabe import S_EIGENER, S_FREIGABE, S_KEY, S_VORSCHLAG, uebernehme_freigaben
from slpgen.korpus import erzeuge_korpus
from slpgen.modell import RegelFehler
from slpgen.profil import lerne_ordner


@pytest.fixture
def gelernt(tmp_path):
    erzeuge_korpus(tmp_path / "k", anzahl=6, seed=2)
    pfad = tmp_path / "hausprofil" / "profil.yaml"
    lerne_ordner(tmp_path / "k", pfad)
    return pfad, pfad.with_name("profil_freigabe.xlsx")


def _setze(liste, eintraege: dict[str, tuple]):
    wb = load_workbook(liste)
    ws = wb["Freigabe"]
    for zeile in ws.iter_rows(min_row=2):
        if zeile[S_KEY].value in eintraege:
            zeile[S_FREIGABE].value, zeile[S_EIGENER].value = eintraege[zeile[S_KEY].value]
    wb.save(liste)


def _zeilen(liste):
    return {r[S_KEY]: r for r in load_workbook(liste)["Freigabe"].iter_rows(min_row=2, values_only=True)}


def _merkmale(pfad):
    return yaml.safe_load(pfad.read_text(encoding="utf-8"))["merkmale"]


def test_liste_enthaelt_nur_einzelwerte_beschreibung_zuerst(gelernt):
    _, liste = gelernt
    ws = load_workbook(liste)["Freigabe"]
    assert ws["A1"].value == "Beschreibung"
    from slpgen.profil import VORGABEN
    assert list(_zeilen(liste)) == ["feldklemmleiste", "sps_adressschreibweise", "haeufigste_ader_0_75", *VORGABEN]


def test_ja_nein_eigener_wert(gelernt):
    pfad, liste = gelernt
    _setze(liste, {"feldklemmleiste": ("ja", None), "sps_adressschreibweise": ("NEIN", None),
                   "haeufigste_ader_0_75": ("JA", "dbu 0.75")})
    e = uebernehme_freigaben(pfad, liste)
    assert len(e["freigegeben"]) == 2 and len(e["abgelehnt"]) == 1
    m = _merkmale(pfad)
    assert m["feldklemmleiste"]["status"] == "freigegeben"
    assert (m["haeufigste_ader_0_75"]["wert"], m["haeufigste_ader_0_75"]["quelle"]) == ("DBU 0,75", "manuell")
    assert pfad.with_suffix(".yaml.bak").exists()
    assert _zeilen(liste)["feldklemmleiste"][2] == "-X10"           # „Bisher freigegeben“ aktualisiert


def test_freigabe_und_ablehnung_ueberstehen_neues_lernen(gelernt, tmp_path):
    pfad, liste = gelernt
    _setze(liste, {"feldklemmleiste": ("JA", "-X99"), "sps_adressschreibweise": ("NEIN", None)})
    uebernehme_freigaben(pfad, liste)
    lerne_ordner(tmp_path / "k", pfad)
    m = _merkmale(pfad)
    assert (m["feldklemmleiste"]["wert"], m["feldklemmleiste"]["status"]) == ("-X99", "freigegeben")
    assert m["sps_adressschreibweise"]["status"] == "abgelehnt"
    z = _zeilen(liste)
    # neuer Lernvorschlag (-X10) weicht vom eigenen Wert ab -> steht zur Entscheidung, nicht vorbelegt
    assert z["feldklemmleiste"][S_VORSCHLAG] == "-X10" and z["feldklemmleiste"][S_FREIGABE] is None
    assert z["sps_adressschreibweise"][S_FREIGABE] == "NEIN"


def test_neuer_vorschlag_geht_nicht_ungesehen_verloren(gelernt, tmp_path):
    pfad, liste = gelernt
    _setze(liste, {"feldklemmleiste": ("JA", "-X99")})
    uebernehme_freigaben(pfad, liste)
    lerne_ordner(tmp_path / "k", pfad)                                 # erzeugt vorschlag_neu -X10
    uebernehme_freigaben(pfad, liste)                                  # Nutzer entscheidet nichts
    m = _merkmale(pfad)["feldklemmleiste"]
    assert m["wert"] == "-X99" and m["vorschlag_neu"]["wert"] == "-X10"
    _setze(liste, {"feldklemmleiste": ("JA", None)})                   # neuen Vorschlag annehmen
    uebernehme_freigaben(pfad, liste)
    m = _merkmale(pfad)["feldklemmleiste"]
    assert (m["wert"], m["status"]) == ("-X10", "freigegeben") and "vorschlag_neu" not in m and "quelle" not in m


def test_abgelehnter_neuer_vorschlag_kommt_nicht_wieder(gelernt, tmp_path):
    pfad, liste = gelernt
    _setze(liste, {"feldklemmleiste": ("JA", "-X99")})
    uebernehme_freigaben(pfad, liste)
    lerne_ordner(tmp_path / "k", pfad)
    _setze(liste, {"feldklemmleiste": ("NEIN", None)})
    uebernehme_freigaben(pfad, liste)
    lerne_ordner(tmp_path / "k", pfad)
    z = _zeilen(liste)["feldklemmleiste"]
    assert z[S_VORSCHLAG] == "-X99" and z[S_FREIGABE] == "JA"
    assert _merkmale(pfad)["feldklemmleiste"]["status"] == "freigegeben"


def test_veraltete_liste_wird_erkannt(gelernt):
    pfad, liste = gelernt
    profil = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    profil["merkmale"]["feldklemmleiste"]["wert"] = "-X77"         # wie nach neuem Lernlauf mit anderem Ergebnis
    pfad.write_text(yaml.safe_dump(profil, allow_unicode=True), encoding="utf-8")
    _setze(liste, {"feldklemmleiste": ("JA", None)})                 # Nutzer bestätigt noch den alten Wert -X10
    vorher = pfad.read_text(encoding="utf-8")
    with pytest.raises(RegelFehler, match="veraltet"):
        uebernehme_freigaben(pfad, liste)
    assert pfad.read_text(encoding="utf-8") == vorher


@pytest.mark.parametrize("wahl, eigener, text", [("vielleicht", None, "Zeile 2"), ("NEIN", "-X5", "nur zusammen mit JA")])
def test_ungueltige_eingaben(gelernt, wahl, eigener, text):
    pfad, liste = gelernt
    _setze(liste, {"feldklemmleiste": (wahl, eigener)})
    with pytest.raises(RegelFehler, match=text):
        uebernehme_freigaben(pfad, liste)


def test_fehlerfaelle_klartext(gelernt, tmp_path):
    pfad, liste = gelernt
    with pytest.raises(RegelFehler, match="zuerst"):
        uebernehme_freigaben(tmp_path / "fehlt.yaml", liste)
    kaputt = tmp_path / "kaputt.xlsx"
    kaputt.write_bytes(b"keine excel-datei")
    with pytest.raises(RegelFehler, match="keine gültige"):
        uebernehme_freigaben(pfad, kaputt)
    wb = load_workbook(liste)
    wb["Freigabe"].title = "Tabelle1"
    wb.save(liste)
    with pytest.raises(RegelFehler, match="Blatt"):
        uebernehme_freigaben(pfad, liste)


def test_vorgaben_freigeben_wirken_im_hausstil(gelernt, tmp_path):
    import copy
    from pathlib import Path

    from pypdf import PdfReader

    from slpgen import regeln
    from slpgen.hausstil import erzeuge_hausstil_pdf, lade_hausstil
    B = Path(__file__).resolve().parent.parent / "beispiele"
    stamm = yaml.safe_load((B / "geraetestamm.yaml").read_text(encoding="utf-8"))
    projekt = yaml.safe_load((B / "projekt_beispiel.yaml").read_text(encoding="utf-8"))
    pfad, liste = gelernt
    _setze(liste, {"ader_0V": ("JA", "BU/WH"), "kennbuchstabe_netzteil": ("JA", "G"), "ader_AI": ("NEIN", None)})
    uebernehme_freigaben(pfad, liste)
    stil = lade_hausstil(pfad)
    assert stil["ader"]["0V"] == "BU/WH" and stil["kennbuchstaben"]["netzteil"] == "G" and stil["ader"]["AI"] == "WH"
    m = regeln.plane(copy.deepcopy(projekt), stamm)
    seiten = erzeuge_hausstil_pdf(m, str(tmp_path / "h.pdf"), stil)
    texte = [x.extract_text() for x in PdfReader(str(tmp_path / "h.pdf")).pages]
    nt = texte[[a for a, _, _ in seiten].index("NT24")]
    assert "-G1" in nt and "BU/WH" in nt


@pytest.mark.parametrize("key, wert, hinweis", [
    ("kennbuchstabe_netzteil", "T1", "Großbuchstaben"),
    ("kennbuchstabe_sps_karte", "K-", "Großbuchstaben"),
    ("ader_DI", 1.5, "Farbkürzel"),                 # Querschnitt in falsche Spalte
    ("ader_0V", "DBU/", "Farbkürzel"),
    ("ader_DI", "XYZ", "Farbkürzel"),
    ("ader_L", "RT", "deutsches Kürzel"),
    ("haeufigste_ader_0_75", "DBU", "Querschnitt"),
    ("sps_adressschreibweise", "Siemens", "IEC oder deutsch"),
    ("feldklemmleiste", "X", "Klemmleiste"),
])
def test_ungueltige_eigene_werte_klar_abgelehnt(gelernt, key, wert, hinweis):
    pfad, liste = gelernt
    vorher = pfad.read_text(encoding="utf-8")
    _setze(liste, {key: ("JA", wert)})
    with pytest.raises(RegelFehler, match=f"Zeile \\d+ .*ungültig – .*{hinweis}"):
        uebernehme_freigaben(pfad, liste)
    assert pfad.read_text(encoding="utf-8") == vorher             # nichts übernommen


def test_gueltige_werte_vereinheitlicht_und_leer_ist_kein_wert(gelernt):
    pfad, liste = gelernt
    _setze(liste, {"kennbuchstabe_netzteil": ("JA", "g"), "feldklemmleiste": ("JA", "x12"),
                   "ader_DO": ("JA", "   ")})
    uebernehme_freigaben(pfad, liste)
    m = _merkmale(pfad)
    assert m["kennbuchstabe_netzteil"]["wert"] == "G" and m["feldklemmleiste"]["wert"] == "-X12"
    assert (m["ader_DO"]["wert"], m["ader_DO"].get("quelle")) == ("DBU", None)   # Leerzeichen = Vorgabe bestätigt


def test_eigener_vorgabewert_bleibt_nach_neuem_lernen(gelernt, tmp_path):
    pfad, liste = gelernt
    _setze(liste, {"ader_0V": ("JA", "BU/WH"), "ader_AI": ("NEIN", None)})
    uebernehme_freigaben(pfad, liste)
    lerne_ordner(tmp_path / "k", pfad)
    m = _merkmale(pfad)
    assert (m["ader_0V"]["wert"], m["ader_0V"]["status"]) == ("BU/WH", "freigegeben")
    assert "vorschlag_neu" not in m["ader_0V"] and m["ader_AI"]["status"] == "abgelehnt"
    z = _zeilen(liste)["ader_0V"]
    assert z[S_VORSCHLAG] == "BU/WH" and z[S_FREIGABE] == "JA"      # kein erneutes Angebot der Vorgabe
    e = uebernehme_freigaben(pfad, liste)                            # „JA“ überschreibt nichts
    assert _merkmale(pfad)["ader_0V"]["wert"] == "BU/WH" and "Aderfarbe 0 V (24M)" in e["freigegeben"]


def test_offene_punkte_genau_die_unentschiedenen(gelernt):
    from slpgen.profil import VORGABEN
    pfad, liste = gelernt
    _setze(liste, {"feldklemmleiste": ("JA", None)})
    e = uebernehme_freigaben(pfad, liste)
    erwartet = {_merkmale(pfad)[k]["beschreibung"] for k in ["sps_adressschreibweise", "haeufigste_ader_0_75", *VORGABEN]}
    assert set(e["offen"]) == erwartet


def test_alle_fehler_auf_einmal_und_rohwert_lesbar(gelernt):
    pfad, liste = gelernt
    vorher = pfad.read_text(encoding="utf-8")
    _setze(liste, {"ader_DI": ("JA", 1.5), "kennbuchstabe_netzteil": ("NEIN", "X1"), "feldklemmleiste": ("JA", "Q")})
    with pytest.raises(RegelFehler) as e:
        uebernehme_freigaben(pfad, liste)
    text = str(e.value)
    assert "nichts übernommen" in text and text.count("• Zeile") == 3
    assert "„1,5“" in text and "nur zusammen mit JA" in text            # Wahl vor Wert geprüft
    assert pfad.read_text(encoding="utf-8") == vorher


def test_farben_und_schreibweise_vereinheitlicht(gelernt):
    pfad, liste = gelernt
    _setze(liste, {"ader_PE": ("JA", "gn/ye"), "sps_adressschreibweise": ("JA", "iec"), "ader_N": ("JA", " lbu ")})
    uebernehme_freigaben(pfad, liste)
    m = _merkmale(pfad)
    assert (m["ader_PE"]["wert"], m["sps_adressschreibweise"]["wert"], m["ader_N"]["wert"]) == \
        ("GNYE", "IEC (%I/%Q/%IW)", "LBU")
    assert _zeilen(liste)["ader_PE"][-1].startswith("Farbkürzel")         # Spalte „Erlaubte Form / Beispiel“


def test_altes_profil_mit_ungueltigem_wert_warnt(gelernt):
    from slpgen.hausstil import lade_hausstil
    pfad, _ = gelernt
    profil = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    profil["merkmale"]["ader_DI"].update(wert="1,5", status="freigegeben")   # vor M1 ungeprüft gespeichert
    pfad.write_text(yaml.safe_dump(profil, allow_unicode=True), encoding="utf-8")
    stil = lade_hausstil(pfad)
    assert stil["ader"]["DI"] == "DBU" and "ungültig" in stil["warnungen"][0]
