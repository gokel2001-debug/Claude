"""M2b: KI-Auftrag und Ende-zu-Ende Lastenheft → (externe KI) → projektmodell.yaml → PDF."""
from pathlib import Path

import yaml
from pypdf import PdfReader

from slpgen import regeln
from slpgen.cli import main
from slpgen.ki_auftrag import erzeuge_auftrag
from slpgen.projektmodell import bereit_machen

B = Path(__file__).resolve().parent.parent / "beispiele"
DOCS = Path(__file__).resolve().parents[2] / "docs"
STAMM = yaml.safe_load((B / "geraetestamm.yaml").read_text(encoding="utf-8"))


def test_auftrag_enthaelt_anleitung_listen_und_lastenheft():
    t = erzeuge_auftrag(B / "lastenheft_beispiel.md", STAMM, DOCS / "KI_AUFBEREITUNG.md")
    assert t.startswith("## AUFTRAG AN DIE KI") and "ANNAHME" not in t        # interne Markierung entfernt
    assert "| PUMPE-EC-230 |" in t and "| pumpe_ec |" in t and "| NT-24-05 |" not in t   # nur Feldgeräte
    assert t.rstrip().endswith("- Dokumentation nach Hausstandard, Revision 00.")


def test_ki_antwort_zum_beispiel_lastenheft_ergibt_plan(tmp_path):
    """Fertig-Kriterium M2: Beispiel-Lastenheft → gültige YAML (über externe KI) → PDF."""
    roh = yaml.safe_load((B / "projektmodell_ki_beispiel.yaml").read_text(encoding="utf-8"))
    modell, ergaenzt = bereit_machen(roh, STAMM, yaml.safe_load((B / "hausvorgaben.yaml").read_text(encoding="utf-8")))
    assert "sps.cpu" in ergaenzt and roh["annahmen"]
    m = regeln.plane(modell, STAMM)
    assert {"-M1", "-M2", "-M3", "-Y1", "-B1", "-B2", "-P1"} <= {b.bmk for b in m.betriebsmittel}
    main(["generieren", str(B / "projektmodell_ki_beispiel.yaml"), "--stamm", str(B / "geraetestamm.yaml"),
          "--vorgaben", str(B / "hausvorgaben.yaml"), "--ausgabe", str(tmp_path), "--profil", str(tmp_path / "x.yaml")])
    text = "".join(s.extract_text() for s in PdfReader(str(tmp_path / "P-2026-017_Stromlaufplan.pdf")).pages)
    assert "-M3" in text and "Leitungslänge Umwälzpumpe Heizkreis Süd 25 m" in text   # KI-Annahme im Nachweis


def test_motor_nicht_m1_zeichnet_richtige_schutzorgane(tmp_path):
    """Regression: Lastseite leitete -Q/-K aus der Motornummer ab (KeyError bei Motor M3 als einzigem)."""
    from slpgen import zeichnen
    d = yaml.safe_load((B / "projekt_beispiel.yaml").read_text(encoding="utf-8"))
    d["motoren"] = [dict(d["motoren"][0], bmk="M7")]
    m = regeln.plane(d, STAMM)
    zeichnen.erzeuge_pdf(m, STAMM, str(tmp_path / "p.pdf"))
    assert m.bm("-M7").daten["mss"] == "-Q2"
