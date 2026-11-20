# Prüfung M2c – UX/Design (pruefer-ux-design), 20.11.2026

| Nr. | Schwere | Befund | Erledigung |
|---|---|---|---|
| 1 | kritisch | Menü-Verteilung zerrissen (Punkt 5 → fehlende Marke, 6–9/0 unerreichbar, `:selbsttest` doppelt) – Ursache: Textersetzung traf `goto :selbsttest` statt der Marke | repariert; `tests/test_start_bat.py` prüft Marken, Ziele und Verteilung |
| 2 | hoch | Formatfehler/abgeschnittene Antwort → Sackgasse ohne Korrekturauftrag | Korrekturauftrag auch bei Formatfehlern |
| 3 | hoch | zwei widersprüchliche Anleitungen; Zwischenablage ohne Erfolgskontrolle | Menümodus: eine Anleitung; Meldung erst nach erfolgreichem Kopieren, sonst Datei im Editor |
| 4 | hoch | Ergebnis geht in ~45 Zeilen unter | Menümodus: Zählung + „FERTIG …“; Einzelheiten im Auslegungsnachweis |
| 5 | mittel | feste Namen `projektmodell.yaml`, Ausgabe im Programmordner | `<Lastenheft>_projektmodell.yaml`, Ausgabe `ausgabe` neben dem Lastenheft |
| 6 | mittel | Menüreihenfolge | nach Abläufen gruppiert, Nummern unverändert |
| 7 | gering | Begriffe uneinheitlich | „KI-Auftrag“, „KI-Antwort“, „Korrekturauftrag“ (Datei `_Korrekturauftrag.txt`); Rest → Glossar mit Browser-Oberfläche (A25) |
| 8 | gering | Meldungen als strukturierte Daten für Oberfläche | offen → A25 |
