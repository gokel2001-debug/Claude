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


def main() -> None:
    bau = HIER / "build_exe"
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--console",
                    "--name", "slpgen", "--distpath", str(bau / "dist"), "--workpath", str(bau / "work"),
                    "--specpath", str(bau), str(HIER / "slpgen_exe.py")], check=True)
    if ZIEL.exists():
        shutil.rmtree(ZIEL)
    shutil.copytree(bau / "dist" / "slpgen", ZIEL / "programm")
    for name in MIT:
        quelle = HIER / name
        if quelle.is_dir():
            shutil.copytree(quelle, ZIEL / name, ignore=shutil.ignore_patterns("ergebnis", "__pycache__"))
        else:
            shutil.copy2(quelle, ZIEL / name)
    (ZIEL / "docs").mkdir()
    for name in DOKUMENTE:
        shutil.copy2(HIER.parent / "docs" / name, ZIEL / "docs" / name)
    verboten = [p for p in ZIEL.rglob("*") if p.name in ("hausprofil", "meine_projekte")]
    if verboten:
        raise SystemExit(f"Kundendaten-Ordner im Paket: {verboten}")
    print(f"Paket: {ZIEL}")


if __name__ == "__main__":
    main()
