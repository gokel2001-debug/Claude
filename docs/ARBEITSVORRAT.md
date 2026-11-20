# ARBEITSVORRAT – Warteschlange für Autostarts und manuelle Läufe

Regel: Jeder Lauf (Autostart oder manuell) nimmt das **oberste offene** Paket, setzt es um
(Umsetzung → Tests → Commit/Push → Prüfer → Nacharbeit), hakt es hier ab und sorgt dafür, dass
**mindestens 5 offene Pakete** in der Liste stehen (nächste aus ZIEL.md Abschnitt 3 ableiten).
Reihenfolge der Meilensteine ist verbindlich (ZIEL.md). Ein Paket = in einem 5-h-Fenster machbar.

| Nr. | Paket | Fertig, wenn | Prüfer | Stand |
|---|---|---|---|---|
| M2a | Schema Projektmodell v1 (`docs/SCHEMA_PROJEKTMODELL.md`), Prüfung `slpgen/projektmodell.py` mit allen Lücken im Klartext, Befehl `pruefen`, `generieren` prüft vorher | Tests: gültiges Beispiel ohne Lücke, jede Lückenart erkannt | Software, Einsteiger | erledigt 20.11. (Prüfung: 7 hoch → behoben) |
| M2b | `docs/KI_AUFBEREITUNG.md` + Befehl `ki-auftrag` (Anleitung + Artikelliste aus Gerätestamm + Lastenheft in eine Textdatei), synthetisches Beispiel-Lastenheft, daraus „wie externe KI“ erzeugte YAML gültig | E2E-Test Lastenheft-Beispiel → YAML → PDF | Software, Einsteiger, Elektro | erledigt 20.11. (Prüfung: 6 hoch → behoben; echte Rohantwort einer unabhängigen KI als Test) |
| M2c | start.bat: Menüpunkte „KI-Auftrag erstellen“, „KI-Antwort prüfen“; ANLEITUNG_EINSTEIGER; Excel-Eingabe läuft durch dieselbe Prüfung | Einsteiger-Prüfer ohne hoch-Befund | Einsteiger, UX | erledigt 20.11. (1 kritisch + 5 hoch → behoben, Nachprüfung start.bat) |
| M2d | CI: GitHub Actions (pytest, ruff, Abdeckung) + `pyproject.toml`; Linter-Befunde beheben | Workflow grün | Software | erledigt 20.11. (CI grün auf Ubuntu+Windows, Py 3.12/3.13; ruff ohne Befund; Abdeckung 95 %) |
| M3a | Planungskern trennen: `plane()` → `planmodell.json` (versioniertes Schema), Ausgabe-Schicht liest nur noch das Planmodell (Laden aus JSON) | PDF aus geladenem `planmodell.json` identisch | Software | erledigt 20.11. (byte-gleich; Prüfung: 1 hoch → behoben) |
| M3b | Schema `docs/SCHEMA_PLANMODELL.md`, Rundreise-Test JSON ↔ Objekt, EPLAN-Stub-Test gegen Schema | Tests grün | Software | erledigt 20.11. |
| M4a | P5b SPS-Übersicht im Hausformat (Kartenbelegung je Steckplatz) | Testkorpus ohne Fehler | Elektro, UX | erledigt 20.11. (Prüfung: 2 hoch → behoben; 4 offen als A31–A33) |
| M4b | P6 Listen im Hausformat (Klemmenplan, Kabelliste, Stückliste als PDF-Seiten; Zeilenlinien, einheitliche Spaltennamen, CPU-Seitenkopf – UX M4a) | Testkorpus ohne Fehler | Elektro, UX, Produkt | offen |
| M4c | Konsistenzprüfungen (A15 Kanalwert vs. I_z, Querverweise, BMK, Klemmen; 230-V-Geräte nicht in 24-V-Abgangslisten) als Prüfbericht | Prüfbericht ohne Fehler am Testkorpus | Elektro, Software | offen |
| M4d | Planungskern: 24-V-Abgangsliste ohne 230-V-Geräte, Projektordner-Konzept (alle Ein-/Ausgaben je Projekt) | Test + Einsteiger ohne hoch | Elektro, Einsteiger | offen |
| M4e | Strukturteil des Hausstils (Anlagen, Kennzeichen, Seitenpositionen) als eigenes Modul in Schicht B (A27) | Ausgabe enthält keine Zuordnungslogik mehr; Tests grün | Software | offen |
| M5a | P7 Geometrie/Schriftfeld lernen, Teil 1: Schriftfeldfelder (Datum, Revision, Ersteller) und Spaltenraster aus Vektor-PDFs des synthetischen Korpus auslesen, mit Sicherheitsangabe (A16) | Tests am Korpus; Profil enthält Schriftfeld-Merkmale mit Sicherheit | Software, Einsteiger | offen |
