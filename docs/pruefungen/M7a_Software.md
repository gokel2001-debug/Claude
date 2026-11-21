# Prüfung M7a – Software, 21.11.2026 (Commit 47b9875)

| Nr. | Schwere | Befund | Erledigung |
|---|---|---|---|
| 1 | hoch | Semikolon-Export mit Dezimalkommas als Komma-CSV gelesen | Trennzeichen über die erkannte Kopfzeile (; Tab ,); Test |
| 2 | hoch | Vorschlag mit abweichendem Kennwert (5 A ↔ 2,5 A, C16 ↔ B13) | kein Vorschlag bei abweichendem Wert gleicher Einheit; Warnung „Kennwerte weichen ab“ bei manueller Zuordnung im Nachweis; Test |
| 3 | mittel | Laufzeit 35 s bei 10.000 Hausartikeln | Merkmale einmal berechnet, Index-Vorfilter, Feinvergleich nur für 50 Kandidaten |
| 4 | mittel | Zeichensatz: Absturz bzw. UTF-16 nicht erkannt | UTF-16-BOM, Rückfall cp1252 mit Ersatzzeichen; Test |
| 5 | mittel | nur erstes Blatt, Kopf „Art.-Nr.“ nicht erkannt, Datei nicht geschlossen | alle Blätter; Köpfe vereinheitlicht (Satzzeichen egal); Meldung zeigt erste Zeile; `wb.close()` |
| 6 | gering | Hersteller-Mischung, Summenstückliste/Kabelliste nach Nummer | Hersteller nur aus Hausstamm; Rest → A48 |
