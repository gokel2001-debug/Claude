"""start.bat: Menü-Verteilung und Sprungmarken (Regression M2c – zerrissenes Menü)."""
import re
from pathlib import Path

BAT = Path(__file__).resolve().parent.parent / "start.bat"
ZEILEN = BAT.read_bytes().decode("utf-8").split("\r\n")


def test_crlf_und_keine_einzelnen_lf():
    roh = BAT.read_bytes()
    assert roh.count(b"\n") == roh.count(b"\r\n")


def test_jede_sprungmarke_einmal_und_jedes_ziel_vorhanden():
    marken = [z[1:].strip().lower() for z in ZEILEN if re.match(r"^:\w", z)]
    assert len(marken) == len(set(marken)), "Sprungmarke doppelt"
    ziele = {m.lower() for z in ZEILEN for m in re.findall(r"goto :(\w+)", z, re.IGNORECASE)}
    assert ziele - {"eof"} <= set(marken), ziele - set(marken)


def test_menue_verteilung_vollstaendig_und_zusammenhaengend():
    punkte = re.findall(r"^echo\s+(\w)\s{2}", "\n".join(ZEILEN), re.MULTILINE)
    i = next(n for n, z in enumerate(ZEILEN) if z.startswith('set /p "W='))
    verteilung = []
    for z in ZEILEN[i + 1:]:
        if z.startswith("if defined W"):
            continue
        mt = re.match(r'if (?:/i )?"%W%"=="(\w)" goto :(\w+)$', z)
        if not mt:
            assert z == "goto :menue", f"nach der Verteilung erwartet 'goto :menue', gefunden: {z!r}"
            break
        verteilung.append(mt.group(1))
    assert sorted(verteilung) == sorted(punkte)
