import re
from pathlib import Path

import pytest
from pypdf import PdfReader

from slpgen.analyse import analysiere_pdf
from slpgen.korpus import WECHSELJAHR, erzeuge_korpus
from slpgen.struktur import lese_struktur


@pytest.fixture(scope="module")
def korpus(tmp_path_factory):
    ordner = tmp_path_factory.mktemp("korpus")
    return ordner, erzeuge_korpus(ordner, anzahl=6, seed=7)


def _text(pdf: Path) -> str:
    return "\n".join(s.extract_text() for s in PdfReader(str(pdf)).pages)


def test_bytegleich_reproduzierbar_und_seed_wirkt(tmp_path, korpus):
    ordner, plaene = korpus
    wiederholt = erzeuge_korpus(tmp_path / "a", anzahl=6, seed=7)
    assert all((ordner / p.datei).read_bytes() == (tmp_path / "a" / q.datei).read_bytes()
               for p, q in zip(plaene, wiederholt))
    anderer = erzeuge_korpus(tmp_path / "b", anzahl=6, seed=8)
    assert [p.datum for p in anderer] != [p.datum for p in plaene]


def test_jahr_und_trend_aus_dem_pdf(korpus):
    ordner, plaene = korpus
    for p in plaene:
        assert analysiere_pdf(ordner / p.datei)["jahr"] == p.jahr
        bmk = set().union(*(a["bmk"] for a in lese_struktur(ordner / p.datei)["anlagen"].values()))
        erwartet, anders = ("X20", "X10") if p.jahr < WECHSELJAHR else ("X10", "X20")
        assert erwartet in bmk and anders not in bmk
    assert {p.feldleiste for p in plaene} == {"-X20", "-X10"}


def test_struktur_findet_eingebaute_typicals(korpus):
    ordner, plaene = korpus
    for p in plaene:
        e = lese_struktur(ordner / p.datei)
        soll = sorted(sorted(v) for v in p.typicals.values() if len(v) > 1)
        assert sorted(e["typical_kandidaten"]) == soll
        assert e["leere_anlagen"] == ["RES"]
        if "pumpe" in p.typicals:
            assert {"Q1", "K1", "M1"} <= set(e["anlagen"]["PU01"]["bmk"])


def _belegte_bytes(adresse: str) -> set[tuple[str, int]]:
    """E2.0 -> {("E", 2)}; EW256 -> {("E", 256), ("E", 257)} (Wort = 2 Byte)."""
    m = re.fullmatch(r"([EA])(W?)(\d+)(?:\.\d)?", adresse)
    bereich, wort, nr = m.group(1), m.group(2), int(m.group(3))
    return {(bereich, nr), (bereich, nr + 1)} if wort else {(bereich, nr)}


def test_keine_doppelt_belegten_sps_adressen(korpus):
    ordner, plaene = korpus
    for p in plaene:
        anlagen = lese_struktur(ordner / p.datei)["anlagen"]
        bits = [a for an in anlagen.values() for a in an["sps_adressen"] if "W" not in a]
        assert len(bits) == len(set(bits)), p.datei
        worte = [a for an in anlagen.values() for a in an["sps_adressen"] if "W" in a]
        bit_bytes = set().union(*(_belegte_bytes(a) for a in bits)) if bits else set()
        for w in worte:
            assert not (_belegte_bytes(w) & bit_bytes), (p.datei, w)


def test_nur_platzhalternamen(korpus):
    ordner, plaene = korpus
    for p in plaene:
        text = _text(ordner / p.datei)
        assert "Bearb. Muster" in text
        assert not re.search(r"\b(GmbH|AG|KG|e\.K\.)\b", text)            # keine Firmennamen
        assert re.fullmatch(r"P1\d{3}", p.projekt)


@pytest.mark.parametrize("anzahl, jahre", [(1, (2021, 2026)), (5, (2026, 2030)), (5, (2021, 2024))])
def test_ungueltige_parameter(tmp_path, anzahl, jahre):
    with pytest.raises(ValueError):
        erzeuge_korpus(tmp_path, anzahl=anzahl, jahre=jahre)
