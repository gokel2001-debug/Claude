#!/bin/bash
# Lokale Prüfung vor jedem Commit (wie CI): Linter, Typen, Tests – bricht beim ersten Fehler ab
set -euo pipefail
cd "$(dirname "$0")"
ruff check slpgen tests
mypy slpgen
python3 -m pytest -q tests | tail -1
