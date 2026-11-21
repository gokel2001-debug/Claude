"""Windows-Programmpaket bauen (ZIEL M9): PyInstaller-Ordner + start.bat + Beispiele + Anleitungen.

Aufruf (in CI auf windows-latest): python paket_bauen.py  -> dist/Stromlaufplan-Generator/
Keine Kundendaten: hausprofil/ und meine_projekte/ werden nie mitgepackt.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
ZIEL = HIER / "dist" / "Stromlaufplan-Generator"
MIT = ["start.bat", "ANLEITUNG_EINSTEIGER.md", "README.md", "beispiele"]
DOKUMENTE = ["KI_AUFBEREITUNG.md", "SCHEMA_PROJEKTMODELL.md"]


def _beispiele_aus_git() -> list[str]:
    """Nur von git erfasste Beispieldateien – ungetrackte (eigene/vertrauliche) Dateien kommen nie ins Paket."""
    aus = subprocess.run(["git", "ls-files", "beispiele"], cwd=HIER, capture_output=True, text=True, check=True).stdout
    return [z for z in aus.splitlines() if z and not z.startswith("beispiele/ergebnis/")]


def main() -> None:
    bau = HIER / "build_exe"
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--console",
                    "--name", "slpgen", "--distpath", str(bau / "dist"), "--workpath", str(bau / "work"),
                    "--specpath", str(bau), str(HIER / "slpgen_exe.py")], check=True)
    if ZIEL.exists():
        shutil.rmtree(ZIEL)
    shutil.copytree(bau / "dist" / "slpgen", ZIEL / "programm")
    for name in MIT:
        if name == "beispiele":
            for datei in _beispiele_aus_git():
                (ZIEL / datei).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(HIER / datei, ZIEL / datei)
        else:
            shutil.copy2(HIER / name, ZIEL / name)
    (ZIEL / "docs").mkdir()
    for name in DOKUMENTE:
        shutil.copy2(HIER.parent / "docs" / name, ZIEL / "docs" / name)
    verboten = [p for p in ZIEL.rglob("*") if p.name in ("hausprofil", "meine_projekte", "ausgabe", "slpgen_fehler.log")
                or "VERTRAULICH" in p.name.upper() or p.name.startswith(("hausregeln", "profil"))]
    if verboten:
        raise SystemExit(f"Kundendaten-Ordner im Paket: {verboten}")
    print(f"Paket: {ZIEL}")


if __name__ == "__main__":
    main()
