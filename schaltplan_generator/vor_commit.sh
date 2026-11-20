#!/bin/sh
# Lokale Prüfung vor jedem Commit (wie CI): Linter, Typen, Tests
cd "$(dirname "$0")" && ruff check slpgen tests && mypy slpgen && python3 -m pytest -q tests | tail -1
