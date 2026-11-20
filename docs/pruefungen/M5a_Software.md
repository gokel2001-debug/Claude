# Prüfung M5a – Software, 20.11.2026 (Commit 2338f76)

| Nr. | Schwere | Befund | Erledigung |
|---|---|---|---|
| 1 | hoch | Planjahr = erstes Datum links im unteren Band (auch Änderungsdatum), stets „eindeutig“ | Datum nur am Feld „Datum“ (gleiches Textstück oder rechts daneben, ohne Änderung/Rev.); Schriftfeld-Jahr nur bei Anteil ≥ 80 % der Seiten, sonst altes Verfahren; Test |
| 2 | mittel | Raster bricht bei 1..8, Störzahl, zusammengefasster Leiste | Folge ab 0 oder 1, längste fortlaufende Folge, Störzahlen übergangen; Tests. Zusammengefasste Leiste („0 1 2 …“ in einem Stück) → A39 |
| 3 | mittel | `vor_commit.sh` meldete fehlgeschlagene Tests nicht | bash mit `set -euo pipefail` |
| 4 | mittel | /Rotate und Mediabox-Versatz nicht beachtet | Umrechnung in Anzeige-Lage (0/90/180/270), Versatz abgezogen; Test Rotate 90 |
| 5 | mittel | Geometriefehler verwirft ganzen Plan | eigener try-Block, Hinweis im Klartext |
| 6 | gering | PDF dreimal gelesen (Laufzeit) | offen → A40 |
| 7 | gering | Teilstring-Treffer, Stimmen je Tupel, kein Hinweis bei fehlender Textebene | Wortgrenzen; Felder einzeln gezählt (≥ halbe Seitenzahl), Reihenfolge nach mittlerer Lage; Hinweis „keine Textebene“ |
| 8 | gering | Tests bestätigen nur den eigenen Generator | Negativ-/Sonderfälle als Tests (Änderungsdatum, 1..8 + Störzahl, Rotate 90, Wortgrenzen, leere Seite) |
