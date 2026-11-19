from pathlib import Path

import pytest

from slpgen.analyse import analysiere_pdf
from slpgen.korpus import WECHSELJAHR, erzeuge_korpus
from slpgen.struktur import lese_struktur


@pytest.fixture(scope="module")
def korpus(tmp_path_factory):
    ordner = tmp_path_factory.mktemp("korpus")
    return ordner, erzeuge_korpus(ordner, anzahl=6, seed=7)


def test_deterministisch(tmp_path, korpus):
    _, plaene = korpus
    zweiter = erzeuge_korpus(tmp_path, anzahl=6, seed=7)
    assert [(p.jahr, p.typicals) for p in plaene] == [(p.jahr, p.typicals) for p in zweiter]


def test_jahr_und_trend(korpus):
    ordner, plaene = korpus
    for p in plaene:
        assert analysiere_pdf(ordner / p.datei)["jahr"] == p.jahr
        assert p.feldleiste == ("-X20" if p.jahr < WECHSELJAHR else "-X10")
    assert {p.feldleiste for p in plaene} == {"-X20", "-X10"}       # Trend im Korpus enthalten


def test_struktur_findet_eingebaute_typicals(korpus):
    ordner, plaene = korpus
    for p in plaene:
        e = lese_struktur(ordner / p.datei)
        soll = sorted(sorted(v) for v in p.typicals.values() if len(v) > 1)
        assert sorted(e["typical_kandidaten"]) == soll
        assert e["leere_anlagen"] == ["789"]
        leiste = p.feldleiste.lstrip("-")
        assert all(leiste in e["anlagen"][a]["bmk"] for v in p.typicals.values() for a in v)


def test_nur_platzhalternamen(korpus):
    ordner, plaene = korpus
    from pypdf import PdfReader
    text = " ".join(s.extract_text() for s in PdfReader(str(ordner / plaene[0].datei)).pages)
    assert "Bearb. Muster" in text                                  # Platzhalter im Schriftfeld
    assert all(p.projekt.startswith("P1") and len(p.projekt) == 5 for p in plaene)
