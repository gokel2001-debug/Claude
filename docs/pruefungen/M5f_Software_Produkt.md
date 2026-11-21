# Prüfung M5f – Lernschleife: programmgewählte Geräte, Klemmen, Kennbuchstaben-Bedingung (Commits b95b9c3, 0f35ee4, 72cdfff)

Prüfer: Software-Qualität, Produkt (Agenten, ändern keinen Code). Nacharbeit im Folgecommit.

| Nr. | Prüfer | Schwere | Befund (kurz) | Nacharbeit | Stand |
|---|---|---|---|---|---|
| S1 / P1 | beide | hoch | Klemmenersatz nur nach Kategorie: RK-PE → RK-2.5, Leistungsklemme kleiner möglich | Stamm: `querschnitt_mm2`, `pe`; Ersatz nur gleiche Rolle (PE bleibt PE) und Querschnitt ≥ Standard; Tests | behoben |
| P2 | Produkt | hoch | Regeln nur je Artikel; Hausregeln wie „ab 4 kW FU“, „Schütz eine Baugröße größer“ nicht abbildbar | neue Funktion, nicht Fehler dieses Pakets → Paket M5g | offen (M5g) |
| S2 | Software | mittel | Kennbuchstaben- und Artikelregel auf dasselbe Gerät → falscher „Kreis“ | feste Rangfolge: Artikelregel vor Sammelregel; Test | behoben |
| S3 | Software | mittel | „Programmauswahl …“ im Nachweis auch ohne tatsächlichen Ersatz | Meldung nur bei tatsächlichem Ersatz je Gerät, mit erfüllter Bedingung | behoben |
| S4 | Software | mittel | `auswahl_ersetzen` auch von Hand/KI im Projektmodell möglich, still | jeder Ersatz steht jetzt im Auslegungsnachweis; Auslegungsprüfung gilt immer | entschärft |
| P3 | Produkt | mittel | Bedingung nur Kennbuchstabe, kein Präfix/Signalart | → M5g | offen (M5g) |
| P4 | Produkt | mittel | Regressionsfall prüft Zuordnung, nicht Planergebnis | → M5g | offen (M5g) |
| P5 / S9 | beide | mittel/gering | Menü/Liste nannten keine Klemmen, RK-PE fehlte | Menütext und Liste ergänzt (mit Rolle) | behoben |
| P6 | Produkt | mittel | Wirkung im PDF nicht getestet | Test prüft Ersatzklemme im Hausstil-PDF (Stückliste) | behoben |
| S5, S6, S8, S10 | Software | gering | Absturz bei ungültigem Ersatzwert, wenn = dann irreführend, Präfix-Schreibweise/Ortspräfix, Dezimalpunkt | Klartext, früh abgewiesen, Präfix robust, Komma | behoben |
| S7, S11, S12, P7, P8 | beide | gering | DO-Geräte bei Kennbuchstaben-Regel (nur Hinweis), Standardklemmen doppelt in C als Rückfall für alte JSON, Test Menü↔CLI, Nachweis je Gerät mit Regel-ID, Kennzahl vermiedene Nacharbeit | → M5g | offen (M5g) |
