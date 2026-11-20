# Prüfung M5c – Software, 21.11.2026 (Commit 307c316)

| Nr. | Schwere | Befund | Erledigung |
|---|---|---|---|
| 1 | hoch | unpassender Ersatzartikel / Gruppe DO-Last speicherbar, danach jeder Plan blockiert | Regeln wirken vor `bereit_machen` (volle Prüfung); Ersatz nur gleiche Kategorie+Signal; DO-Gruppe abgelehnt; Probelauf (Prüfung+Planung) vor dem Speichern |
| 2 | hoch | beschädigte hausregeln.yaml → kein Plan mehr | Einträge geprüft, fehlerhafte übersprungen mit Hinweis im Nachweis; Plan entsteht; Test |
| 3 | hoch | kein Abschalten/Zurücknehmen; `aktiv: nein` galt als aktiv | Befehl `hausregel ein/aus/loeschen`; `aktiv` nur true/false |
| 4 | mittel | Reihenfolge/Ketten, kein Bestätigen | Anwendung bis Stillstand, Kreis erkannt; `hausregeln --bestaetigen` |
| 5 | mittel | gilt_ab als Text verglichen, Fall ohne Datum | Datum geprüft und als Datum verglichen; Projektdatum im Fall |
| 6 | mittel | Regression nur auf Feldgeräte-Ebene | offen → A43 |
| 7 | mittel | Korrektur gegen Rohprojekt | Korrektur gegen Projekt mit bisherigen Regeln; Motoren/Bausteine → A44 |
| 8 | gering | Tests fehlen, ID-Kollision, .gitignore | Tests ergänzt; ID = höchste + 1; `hausregeln*.yaml` in .gitignore |
