# ARBEITSVORRAT – Warteschlange für Autostarts und manuelle Läufe

Regel: Jeder Lauf (Autostart oder manuell) nimmt das **oberste offene** Paket, setzt es um
(Umsetzung → Tests → Commit/Push → Prüfer → Nacharbeit), hakt es hier ab und sorgt dafür, dass
**mindestens 5 offene Pakete** in der Liste stehen (nächste aus ZIEL.md Abschnitt 3 ableiten).
Reihenfolge der Meilensteine ist verbindlich (ZIEL.md). Ein Paket = in einem 5-h-Fenster machbar.

| Nr. | Paket | Fertig, wenn | Prüfer | Stand |
|---|---|---|---|---|
| M2a | Schema Projektmodell v1 (`docs/SCHEMA_PROJEKTMODELL.md`), Prüfung `slpgen/projektmodell.py` mit allen Lücken im Klartext, Befehl `pruefen`, `generieren` prüft vorher | Tests: gültiges Beispiel ohne Lücke, jede Lückenart erkannt | Software, Einsteiger | erledigt 20.11. (Prüfung: 7 hoch → behoben) |
| M2b | `docs/KI_AUFBEREITUNG.md` + Befehl `ki-auftrag` (Anleitung + Artikelliste aus Gerätestamm + Lastenheft in eine Textdatei), synthetisches Beispiel-Lastenheft, daraus „wie externe KI“ erzeugte YAML gültig | E2E-Test Lastenheft-Beispiel → YAML → PDF | Software, Einsteiger, Elektro | in Arbeit (Anleitung, Lastenheft, KI-Antwort, E2E-Test fertig; Befehl `ki-auftrag` fehlt) |
| M2c | start.bat: Menüpunkte „KI-Auftrag erstellen“, „KI-Antwort prüfen“; ANLEITUNG_EINSTEIGER; Excel-Eingabe läuft durch dieselbe Prüfung | Einsteiger-Prüfer ohne hoch-Befund | Einsteiger, UX | offen (inkl. A22 Zeilennummern) |
| M2d | CI: GitHub Actions (pytest, ruff, Abdeckung) + `pyproject.toml`; Linter-Befunde beheben | Workflow grün | Software | offen |
| M3a | Planungskern trennen: `plane()` → `planmodell.json` (versioniertes Schema), Ausgabe-Schicht liest nur noch das Planmodell (Laden aus JSON) | PDF aus geladenem `planmodell.json` identisch | Software | offen |
| M3b | Schema `docs/SCHEMA_PLANMODELL.md`, Rundreise-Test JSON ↔ Objekt, EPLAN-Stub-Test gegen Schema | Tests grün | Software | offen |
| M4a | P5b SPS-Übersicht im Hausformat (Kartenbelegung je Steckplatz) | Testkorpus ohne Fehler | Elektro, UX | offen |
| M4b | P6 Listen im Hausformat (Klemmenplan, Kabelliste, Stückliste als PDF-Seiten) | Testkorpus ohne Fehler | Elektro, UX, Produkt | offen |
| M4c | Konsistenzprüfungen (A15 Kanalwert vs. I_z, Querverweise, BMK, Klemmen) als Prüfbericht | Prüfbericht ohne Fehler am Testkorpus | Elektro, Software | offen |
