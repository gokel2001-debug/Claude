"""M2b: KI-Auftrag und Ende-zu-Ende Lastenheft → (externe KI) → projektmodell.yaml → PDF."""
import zipfile
from pathlib import Path

import pytest
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
    assert any("SPS-CPU" in x for x in ergaenzt) and roh["annahmen"]
    m = regeln.plane(modell, STAMM)
    assert {"-M1", "-M2", "-M3", "-Y1", "-B1", "-B2", "-P1"} <= {b.bmk for b in m.betriebsmittel}
    with pytest.raises(SystemExit, match="Sicherheitsfunktion nicht ausgelegt"):   # Not-Halt offen -> nicht für Fertigung
        main(["generieren", str(B / "projektmodell_ki_beispiel.yaml"), "--stamm", str(B / "geraetestamm.yaml"),
              "--vorgaben", str(B / "hausvorgaben.yaml"), "--ausgabe", str(tmp_path), "--profil", str(tmp_path / "x.yaml")])
    text = "".join(s.extract_text() for s in PdfReader(str(tmp_path / "P-2026-017_Stromlaufplan.pdf")).pages)
    assert "-M3" in text and "Leitungslänge Umwälzpumpe Heizkreis Süd 30 m" in text   # KI-Annahme im Nachweis


def test_motor_nicht_m1_zeichnet_richtige_schutzorgane(tmp_path):
    """Regression: Lastseite leitete -Q/-K aus der Motornummer ab (KeyError bei Motor M3 als einzigem)."""
    from slpgen import zeichnen
    d = yaml.safe_load((B / "projekt_beispiel.yaml").read_text(encoding="utf-8"))
    d["motoren"] = [dict(d["motoren"][0], bmk="M7")]
    m = regeln.plane(d, STAMM)
    zeichnen.erzeuge_pdf(m, str(tmp_path / "p.pdf"))
    texte = [x.extract_text() for x in PdfReader(str(tmp_path / "p.pdf")).pages]
    last = next(t for t in texte if "-M7" in t and "-Q2" in t)
    assert "-K1" in last


def test_cli_ki_auftrag(tmp_path, capsys):
    lh = tmp_path / "Lastenheft Halle.md"
    lh.write_text((B / "lastenheft_beispiel.md").read_text(encoding="utf-8"), encoding="utf-8")
    main(["ki-auftrag", str(lh)])
    ziel = tmp_path / "Lastenheft Halle_KI_Auftrag.txt"
    assert ziel.exists() and "### LASTENHEFT" in ziel.read_text(encoding="utf-8")
    assert "KI-Chat einfügen" in capsys.readouterr().out


def test_cli_ki_auftrag_docx_mit_tabelle_und_sonderzeichen(tmp_path):
    docx = tmp_path / "lh.docx"
    xml = ("<w:document><w:p><w:t>Pumpe &amp; Ventil, I &lt; 5 A, Gr&#246;&#223;e</w:t></w:p>"
           "<w:tbl><w:tr><w:tc><w:p><w:t>Pumpe Nord</w:t></w:p></w:tc><w:tc><w:p><w:t>25 m</w:t></w:p></w:tc></w:tr>"
           "</w:tbl><w:p><w:t>Weitere Angaben zum Projekt folgen hier im Text.</w:t></w:p></w:document>")
    with zipfile.ZipFile(docx, "w") as z:
        z.writestr("word/document.xml", xml)
    main(["ki-auftrag", str(docx)])
    t = (tmp_path / "lh_KI_Auftrag.txt").read_text(encoding="utf-8")
    assert "Pumpe & Ventil, I < 5 A, Größe" in t and "Pumpe Nord" in t and " | 25 m" in t


@pytest.mark.parametrize("name, inhalt, meldung", [
    ("fehlt.md", None, "nicht gefunden"),
    ("leer.txt", b"", "kaum lesbarer Text"),
    ("x.xlsx", b"PK\x03\x04", "nicht unterstützt"),
    ("x.rtf", b"{\\rtf1 Hallo}", "nicht unterstützt"),
    ("kaputt.pdf", b"kaputt", "beschädigt"),
    ("kaputt.docx", b"keine zip", "keine gültige Word-Datei"),
    ("binaer.txt", bytes(range(256)) * 4, "nicht lesbar"),
    ("ordner", "DIR", "Ordner"),
])
def test_ki_auftrag_fehlerhafte_lastenhefte_klartext(tmp_path, name, inhalt, meldung):
    f = tmp_path / name
    if inhalt == "DIR":
        f.mkdir()
    elif inhalt is not None:
        f.write_bytes(inhalt)
    with pytest.raises(SystemExit, match=meldung):
        main(["ki-auftrag", str(f)])


def test_ki_auftrag_verschluesseltes_pdf_und_ansi(tmp_path):
    from pypdf import PdfWriter
    w = PdfWriter()
    w.add_blank_page(100, 100)
    w.encrypt("geheim")
    with open(tmp_path / "zu.pdf", "wb") as f:
        w.write(f)
    with pytest.raises(SystemExit, match="kennwortgeschützt"):
        main(["ki-auftrag", str(tmp_path / "zu.pdf")])
    (tmp_path / "ansi.txt").write_bytes(("Förderband mit Pumpe, Länge 25 m, Steuerung über SPS. " * 2).encode("cp1252"))
    main(["ki-auftrag", str(tmp_path / "ansi.txt")])
    assert "Förderband" in (tmp_path / "ansi_KI_Auftrag.txt").read_text(encoding="utf-8")


def test_rohe_chat_antwort_pruefen_und_korrekturauftrag(tmp_path, capsys):
    """Antwort wie aus dem Chat kopiert (Einleitung, Codeblock, Komma, Schlusssatz) über die Kommandozeile."""
    yaml_text = (B / "projektmodell_ki_beispiel.yaml").read_text(encoding="utf-8").replace("p_kW: 1.1", "p_kW: 1,1")
    roh = tmp_path / "projektmodell.yaml"
    roh.write_text("Gern, hier ist das Projektmodell:\n```yaml\n" + yaml_text + "```\nViel Erfolg!\n", encoding="utf-8")
    main(["pruefen", str(roh)])
    assert "vollständig" in capsys.readouterr().out
    roh.write_text(yaml_text.replace("laenge_m: 18", "laenge_m: ") + "Hinweis: Bitte Leitungslängen prüfen.\n",
                   encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        main(["pruefen", str(roh)])
    assert "Kommentar der KI" in str(e.value) and "Korrekturauftrag" in str(e.value)
    korr = (tmp_path / "projektmodell_Korrekturauftrag.txt").read_text(encoding="utf-8")
    assert "Leitungslänge Schrank–Motor" in korr and "YAML-Block" in korr


def test_echte_ki_rohantwort_ergibt_plan(tmp_path, capsys):
    """M2-Fertigkriterium: Rohantwort einer unabhängigen KI auf den erzeugten Auftrag -> pruefen -> generieren."""
    roh = B / "ki_antwort_roh_2026-11-20.txt"
    main(["pruefen", str(roh)])
    aus = capsys.readouterr().out
    assert "vollständig" in aus and "10 offene Fragen" in aus
    with pytest.raises(SystemExit, match="Sicherheitsfunktion nicht ausgelegt"):
        main(["generieren", str(roh), "--ausgabe", str(tmp_path), "--profil", str(tmp_path / "x.yaml")])
    text = "".join(s.extract_text() for s in PdfReader(str(tmp_path / "P-2026-017_Stromlaufplan.pdf")).pages)
    assert "-M3" in text and "Offene Frage: Reparatur-/Trennschalter" in text


def test_menue_modus_nennt_menuepunkte(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr("slpgen.cli.MENUE", True)
    lh = tmp_path / "lh.md"
    lh.write_text((B / "lastenheft_beispiel.md").read_text(encoding="utf-8"), encoding="utf-8")
    main(["ki-auftrag", str(lh)])
    aus = capsys.readouterr().out
    assert "_projektmodell.yaml" in aus and "Punkt 9" in aus and "python -m" not in aus
    kaputt = tmp_path / "projektmodell.yaml"
    kaputt.write_text("projekt: {nummer: A}\n", encoding="utf-8")
    with pytest.raises(SystemExit, match=r"wieder Punkt 9"):
        main(["pruefen", str(kaputt)])
