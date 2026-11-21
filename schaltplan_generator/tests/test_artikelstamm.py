"""M7a: eigener Artikelstamm (synthetischer Export) -> Zuordnung -> Stückliste/EPLAN mit eigenen Artikelnummern."""
from pathlib import Path

import pytest
import yaml
from openpyxl import Workbook, load_workbook

from slpgen.artikelstamm import lese_export, vorschlag
from slpgen.cli import main
from slpgen.modell import RegelFehler

B = Path(__file__).resolve().parent.parent / "beispiele"
STAMM = yaml.safe_load((B / "geraetestamm.yaml").read_text(encoding="utf-8"))
EXPORT = [["Export Artikelverwaltung"], [], ["Artikelnummer", "Hersteller", "Bezeichnung"],
          ["HN-1000", "Musterwerk", "Netzteil 24 V DC 5 A primär 230 V"],
          ["HN-2000", "Musterwerk", "Induktiver Sensor M12 PNP Schließer"],
          ["HN-3000", "Musterwerk", "Reihenklemme 2,5 mm² grau"],
          ["HN-1000", "Musterwerk", "doppelt"]]


def _export(tmp_path, endung="xlsx"):
    p = tmp_path / f"export.{endung}"
    if endung == "xlsx":
        wb = Workbook()
        for z in EXPORT:
            wb.active.append(z)
        wb.save(p)
    else:
        p.write_bytes("\n".join(";".join(z) for z in EXPORT).encode("cp1252"))
    return p


@pytest.mark.parametrize("endung", ["xlsx", "csv"])
def test_export_lesen(tmp_path, endung):
    a = lese_export(_export(tmp_path, endung))
    assert [x["artikelnummer"] for x in a] == ["HN-1000", "HN-2000", "HN-3000"] and a[2]["bezeichnung"].endswith("grau")


def test_vorschlag_nach_merkmalen(tmp_path):
    haus = lese_export(_export(tmp_path))
    assert vorschlag(STAMM["artikel"]["NT-24-05"], haus)["artikelnummer"] == "HN-1000"
    assert vorschlag(STAMM["artikel"]["IND-M12-PNP"], haus)["artikelnummer"] == "HN-2000"
    assert vorschlag(STAMM["artikel"]["SPS-CPU"], haus) is None


def test_zuordnung_wirkt_in_stueckliste_und_eplan(tmp_path):
    profil = tmp_path / "hausprofil" / "profil.yaml"
    main(["artikelstamm", str(_export(tmp_path)), "--profil", str(profil)])
    liste = profil.with_name("artikelzuordnung.xlsx")
    wb = load_workbook(liste)
    for z in wb.active.iter_rows(min_row=2):
        if z[0].value in ("NT-24-05", "IND-M12-PNP"):
            z[4].value = "JA"
        if z[0].value == "RK-2.5":
            z[4].value = "HN-3000"
    wb.save(liste)
    main(["artikelzuordnung", "--profil", str(profil)])
    main(["generieren", str(B / "projekt_beispiel.yaml"), "--ausgabe", str(tmp_path / "aus"), "--profil", str(profil)])
    csv_text = (tmp_path / "aus" / "P-2026-001_Stueckliste.csv").read_text(encoding="utf-8")
    assert "HN-1000;Musterwerk" in csv_text and "HN-2000" in csv_text and "IND-M12-PNP" not in csv_text
    from slpgen.eplan_adapter import aufbereiten
    from slpgen.modell import Planmodell
    pm = Planmodell.lade(tmp_path / "aus" / "P-2026-001_Planmodell.json")
    assert any(z["artikelnummer"] == "HN-2000" for z in aufbereiten(pm)["betriebsmittel"])


def test_fehler_klartext(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("Spalte1;Spalte2\na;b\n", encoding="utf-8")
    with pytest.raises(RegelFehler, match="keine Spalten"):
        lese_export(p)
    with pytest.raises(RegelFehler, match="nicht unterstützt"):
        lese_export(tmp_path / "x.pdf")
    profil = tmp_path / "hausprofil" / "profil.yaml"
    main(["artikelstamm", str(_export(tmp_path)), "--profil", str(profil)])
    wb = load_workbook(profil.with_name("artikelzuordnung.xlsx"))
    wb.active["E2"] = "GIBTSNICHT"
    wb.save(profil.with_name("artikelzuordnung.xlsx"))
    with pytest.raises(SystemExit, match="nichts übernommen"):
        main(["artikelzuordnung", "--profil", str(profil)])
