# Prüfung M7b – Sicherheitskreis als Platzhalter (Commit d71c91e)

Prüfer: Elektro/Norm, Software-Qualität (Agenten, ändern keinen Code). Nacharbeit im Folgecommit.

| Nr. | Prüfer | Schwere | Befund (kurz) | Nacharbeit | Stand |
|---|---|---|---|---|---|
| E1 | Elektro | kritisch | Feldgerät „Not-Halt Taster“ wird still an Standard-SPS-DI verdrahtet | Feldgeräte (Funktion/Artikel) nach Sicherheitsbegriffen durchsucht → Platzhalterseite + FEHLER je Gerät | behoben |
| E2 | Elektro | hoch | Platzhalterseite nur im Hausstil-PDF; Standard-PDF/Stückliste ohne Kennzeichnung | durch E4: FEHLER → Stempel „NICHT FÜR FERTIGUNG“ auf allen Seiten beider PDFs und Kopfzeile der Stückliste (geprüft: 32/32 und 14/14 Seiten) | behoben |
| E3 / S1 | beide | hoch | Suchmuster zu eng (Not-Aus, Not Halt, Schutztür, Lichtgitter, ISO 13849 …); nur offene Fragen durchsucht | `regeln.SICHERHEIT_MUSTER` erweitert, auf Annahmen, offene Fragen, Feldgeräte, Motorfunktion angewandt; 15 Positiv-/Negativfälle | behoben |
| E4 | Elektro | hoch | Nur HINWEIS → Plan gilt als fertig | FEHLER ohne Freigabevermerk `sicherheit.freigabe`; mit Vermerk HINWEIS | behoben |
| E5 / S3 | beide | mittel | `not_halt` ohne Angabe = „ja“ (Programm legt fest) | dreistufig ja/nein/nicht angegeben | behoben |
| S4 | Software | mittel | `bool("nein")` = True in `plane` | `projektmodell._ja_nein` | behoben |
| S5 | Software | mittel | Excel kann Sicherheit nicht auslösen | Blatt „Sicherheit“ in Vorlage und Einlesen, Test | behoben |
| E6 | Elektro | mittel | „Not-Halt: nein“ liest sich wie geprüft | Text „nein (laut Lastenheft) – Begründung aus Risikobeurteilung nachweisen“ | behoben |
| E7 | Elektro | mittel | Pflichtangaben fehlen (PL_r, Stoppkategorie, Antriebe, Orte, Freigabe) | Zeilen auf der Platzhalterseite, Feld `stoppkategorie`, Antriebe nur aufgezählt | behoben |
| E8 | Elektro | mittel | Quelle nur ZIEL.md | Normquelle EN 60204-1 / EN ISO 13849-1 + A49 (Abschnitte vor Freigabe prüfen) | behoben |
| S2 / E10 | beide | mittel/gering | Fehlalarme „Fossil“, „Pl. 3“ | `\bSIL`, `PL` nicht vor Punkt; Tests | behoben |
| S7 | Software | gering | `_sicherheit` nicht im Schema-Dokument, Typ ungeprüft | Schema ergänzt; unlesbarer Wert → Klartext-FEHLER statt Absturz im Prüfbericht | teilweise (Zeichner nimmt weiter Objekt an) |
| E9 | Elektro | gering | Dokumentart „Stromlaufplan“ auf Platzhalterseite | Dokumentart „Platzhalter“ (Art PLH) | behoben |
| S8 | Software | gering | lange Texte laufen über den Rahmen | auf 150 Zeichen gekürzt | behoben |
| S6 | Software | gering | Seite auch bei `not_halt: nein` | bewusst so (konservativ), in A49 dokumentiert | offen (Annahme) |
| E11 / S9 | beide | gering | Tests zu dünn | 3 neue Tests (Suchmuster, Feldgerät+Freigabe, Excel+JSON-Rundreise) | behoben |

Folge für Anwender: Auf dem KI-Weg fragt die KI immer nach Not-Halt → Plan entsteht, ist aber „NICHT FÜR FERTIGUNG“,
bis die Elektrofachkraft den Freigabevermerk einträgt (beabsichtigt, ZIEL.md „Pflicht zur Freigabe“).
