# Prüfung M4c – Elektro/Norm, 20.11.2026 (Commit 1c9d7a1)

| Nr. | Schwere | Befund | Erledigung |
|---|---|---|---|
| 1 | hoch | Leitungsschutz I_B ≤ I_n ≤ I_z bei Motor-/Leistungsabgängen nicht geprüft; I_n fehlt in 2a | Prüfung „Leitungsschutz“ (FEHLER) mit Quelle IEC 60364-4-43 433.1 (Abschnitt nicht online verifiziert); Spalte I_n = I_r in 2a; Spannungsfall gegen Hausvorgabe |
| 2 | hoch | MSS-Einstellwert gegen Bereich/I_N nicht geprüft | Prüfung „Motorschutz“: außerhalb Bereich = FEHLER, ≠ I_N = HINWEIS |
| 3 | mittel | Netzteil-Auslastung, DO-Kanalstrom nicht geprüft | offen → A37 |
| 4 | mittel | Doppelbelegung Anschlüsse, offene Potentiale fehlen | „Geräteanschluss auf mehreren Klemmen“ (FEHLER), „offenes Potential 24L+“ (FEHLER) |
| 5 | mittel | keine Quelle je Regel | Feld `quelle` je Befund, im Bericht ausgegeben |
| 6 | mittel | Kennzahl CLI ≠ PDF | eine Zählweise (Hausstil-Seiten, Feldleitungen mitgezählt, Kabel nicht doppelt); Bezeichnung „Zeichenaufwand (entfällt bei Übernahme ohne Nacharbeit)“ |
| 7 | gering | Hausstil-Kennzeichen nicht auf Eindeutigkeit geprüft; -X-Enden ungeprüft | geprüft (wenn `kennzeichen` vorhanden); Kabelenden gegen Klemmleisten |
| 8 | gering | PDF bei FEHLER ohne Stempel, Rückgabe 0 | Rückgabe ≠ 0 mit Klartext; Stempel auf Deckblatt → A37 |
