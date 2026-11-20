# Prüfung M4c – Software, 20.11.2026 (Commit 1c9d7a1)

Klemmenplan-Umbruch nachgestellt (80 Klemmen, Grenzfälle) – korrekt.

| Nr. | Schwere | Befund | Erledigung |
|---|---|---|---|
| 1 | hoch | `zeichnen` zeigte alten Bericht („keine Befunde“) bei geändertem Modell | Bericht bei jeder Ausgabe frisch berechnet (`_ausgabe`, Nachweis); Test über `zeichnen` |
| 2 | hoch | offene Potentiale, Leitungsschutz/ΔU, Quelle je Regel fehlen | ergänzt (siehe Elektro 1, 2, 4, 5); Störungstests |
| 3 | mittel | Bericht als Text in `warnungen` | nicht mehr in `warnungen`; Nachweis berechnet selbst |
| 4 | mittel | Kennzahlen widersprüchlich, Kabel doppelt | eine Zählquelle; Kategorie kabel nicht als Betriebsmittel; Feldleitungen gezählt |
| 5 | mittel | mypy-Fehler | `konsistenz.py` ohne Befund; Rest des Pakets → M2e (mypy für alle Module) |
| 6 | mittel | Absturz bei handbearbeitetem JSON | jede Prüfung abgesichert → Befund „Daten“ |
| 7 | gering | Fortsetzungszweig ungetestet; nur any(); nr < 1 | Test mit 80 Klemmen; Störungstests ohne fremde Fehlalarme; nr < 1 = FEHLER |
| 8 | gering | Rückgabe 0 bei FEHLER, englisches Zahlenformat, Überschrift am Seitenende | Rückgabe ≠ 0; `_zahl` im CLI; Überschrift nie allein am Seitenende |
