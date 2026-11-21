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


def test_exe_paket_ohne_python():
    """M9a: liegt programm\\slpgen.exe vor, nutzt start.bat die Exe und überspringt die Python-Einrichtung."""
    zeilen = (Path(__file__).resolve().parent.parent / "start.bat").read_bytes().decode().split("\r\n")
    i = next(i for i, z in enumerate(zeilen) if z.startswith('if exist "programm\\slpgen.exe"'))
    assert "goto :bereit_exe" in zeilen[i] and i < zeilen.index("rem ---- Python suchen: bevorzugt Versionen, fuer die alle "
                                                                  "Bibliotheken fertig vorliegen ----")
    assert zeilen[zeilen.index(":bereit_exe") - 2] == ":bereit"


def test_programmordner_als_exe(monkeypatch, tmp_path):
    """M9a: im PyInstaller-Paket ist der Programmordner der Ordner über programm\\ (dort liegen start.bat, hausprofil)."""
    import importlib
    import sys

    import slpgen.cli as cli
    (tmp_path / "programm").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "KI_AUFBEREITUNG.md").write_text("x", encoding="utf-8")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "programm" / "slpgen.exe"))
    try:
        neu = importlib.reload(cli)
        assert neu.PROG == tmp_path.resolve() and neu.DOCS == tmp_path.resolve() / "docs"
        assert neu.PROFIL == str(tmp_path.resolve() / "hausprofil" / "profil.yaml")
    finally:
        monkeypatch.undo()
        importlib.reload(cli)
