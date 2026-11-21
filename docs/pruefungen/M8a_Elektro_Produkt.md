# Prüfung M8a – Abweichungsliste Referenzplan ↔ Nachbau (Commit 0427cfd)

Prüfer: Elektro/Norm, Produkt (Agenten, ändern keinen Code). Nacharbeit im Folgecommit.

| Nr. | Prüfer | Schwere | Befund (kurz) | Nacharbeit | Stand |
|---|---|---|---|---|---|
| E1 | Elektro | kritisch | Zuordnung Adresse ↔ Gerät/Funktion fehlt (vertauschte Belegung = 0 Abweichungen) | Tabellenzeilen per Textkoordinaten; Bereich „SPS-Belegung“ (Adresse → Gerät/Klemme/Funktion), Test mit Tausch/Funktionstext | behoben |
| E2 | Elektro | kritisch | Artikel nur per Textsuche, anderer MSS am selben Gerät unerkannt | Bereich „Artikel je Gerät“ aus der Stückliste (beide Richtungen), Test Motor kleiner | behoben |
| P1 | Produkt | kritisch | echte EPLAN-Schreibweisen (BMK ohne Anlage, X1:3, %IX) nicht erkannt | Anlage je Seite aus häufigstem „=…“, Muster ohne Vorsatz, %IX/%IW/%I0.10; echte Erprobung = PC8 | teilweise (Erprobung PC8) |
| P2 / E4 | beide | kritisch/hoch | nichts erkannt = 100 % | „nicht auswertbar“ statt Quote; Test mit fremder Schreibweise | behoben |
| P3 | Produkt | hoch | Kennzahl misst Namen, nicht Gleichwertigkeit | umbenannt „Übereinstimmung der Kennzeichen“, Hinweis „kein Abnahmeurteil“; Zuordnungen E1/E2 ergänzt | behoben |
| P4 / E5 | beide | hoch/mittel | Bewertungen ohne Auszählung, kein Abnahmefeld | ZÄHLENWENN je Bewertung, Felder Urteil/Name/Datum/Programmstand/Stunden | behoben |
| P5 | Produkt | hoch | bewertete Liste wird überschrieben | neue Datei _2, _3 …; Test | behoben |
| P7 / P11 | Produkt | hoch/mittel | Zeitaufwand nicht erfasst; Nachbau-Regel „nur aus Lastenheft“ fehlt | PC8 ergänzt (Regel, Stunden, 3 Pläne) | behoben |
| E3 | Elektro | hoch | Querschnitte, Absicherung, Potentiale nicht verglichen | → M8b | offen (M8b) |
| P6 | Produkt | hoch | Bewertung „Fehler im Nachbau“ → Lernschleife | → M8b | offen (M8b) |
| E7 / P8 | beide | mittel | Ort verworfen | Ort bleibt im Kennzeichen | behoben |
| P9 | Produkt | mittel | %I0.10 als %I0.1 | mehrstellige Bitnummern | behoben |
| P10 | Produkt | mittel | Teilstring-Suche Artikel | ersetzt durch Artikel je Gerät | behoben |
| E6, E8, E9, E10 | Elektro | mittel/gering | Gruppierung nach Ursache, Muster aus Hausprofil, Mehrfachbelegung zählen, Negativtests | Negativtests ergänzt; Rest → M8b | teilweise |
