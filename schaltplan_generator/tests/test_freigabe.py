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
    assert list(_zeilen(liste)) == ["feldklemmleiste", "sps_adressschreibweise", "haeufigste_ader_0_75"]


def test_ja_nein_eigener_wert(gelernt):
    pfad, liste = gelernt
    _setze(liste, {"feldklemmleiste": ("ja", None), "sps_adressschreibweise": ("NEIN", None),
                   "haeufigste_ader_0_75": ("JA", 1.5)})          # als Zahl eingegeben
    e = uebernehme_freigaben(pfad, liste)
    assert len(e["freigegeben"]) == 2 and len(e["abgelehnt"]) == 1 and e["offen"] == []
    m = _merkmale(pfad)
    assert m["feldklemmleiste"]["status"] == "freigegeben"
    assert (m["haeufigste_ader_0_75"]["wert"], m["haeufigste_ader_0_75"]["quelle"]) == ("1,5", "manuell")
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
