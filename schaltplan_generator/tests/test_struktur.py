from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfgen.canvas import Canvas

from slpgen.struktur import lese_struktur

# Synthetischer Plan: zwei gleich aufgebaute Anlagen (Typical), eine abweichende, eine leere
SEITEN = {
    "ZA01": ["-X20 1 2 3", "-W1 LIYCY 7x0,75", "DBU 0,75", "DBU/WH 0,75", "E0.1 Zählimpuls Zähler ZA01",
             "E0.2 Drahtbruch Zähler ZA01", "-P1 Wasserzähler 24V DC Puls GND"],
    "ZA02": ["-X20 1 2 3", "-W1 LIYCY 7x0,75", "DBU 0,75", "DBU/WH 0,75", "E0.3 Zählimpuls Zähler ZA02",
             "E0.4 Drahtbruch Zähler ZA02", "-P1 Wasserzähler 24V DC Puls GND"],
    "PU01": ["-Q1 Motorschutzschalter", "-K1 Koppelrelais", "AW256 Stellsignal 4-20mA", "A1.0 Freigabe",
             "BK 2,5", "OG 1,5", "-X10 1 2 3 4 5 6"],
    "RES1": [],
}


def test_struktur_synthetisch(tmp_path):
    pdf = tmp_path / "s.pdf"
    c = Canvas(str(pdf), pagesize=landscape(A3))
    for anlage, zeilen in SEITEN.items():
        for i, z in enumerate(zeilen):
            c.drawString(50, 700 - 20 * i, z)
        c.drawString(800, 30, f"P0001-{anlage}-0-EFS-00")
        c.showPage()
    c.drawString(800, 30, "P0001-KPL-0--00")
    c.showPage()
    c.save()
    e = lese_struktur(pdf)
    assert e["seiten_je_dokumentart"] == {"EFS": 4, "-": 1}
    assert e["typical_kandidaten"] == [["ZA01", "ZA02"]]
    assert e["leere_anlagen"] == ["RES1"]
    assert e["anlagen"]["PU01"]["sps_adressen"] == ["A1.0", "AW256"]
    assert e["anlagen"]["ZA01"]["bmk"] == ["P1", "W1", "X20"]
    assert e["aderkennzeichnung_gesamt"]["DBU 0,75"] == 2
