# Prüfung M7c – Motorabgang mit Frequenzumrichter (Commit fbc542f)

Prüfer: Elektro/Norm, Software-Qualität (Agenten, ändern keinen Code). Nacharbeit in 0e8e18e und Folgecommit.

| Nr. | Prüfer | Schwere | Befund (kurz) | Nacharbeit | Stand |
|---|---|---|---|---|---|
| E1 | Elektro | hoch | STO fehlt, kein Netzschütz → Not-Halt-Wirkung offen | je FU rot gerahmter STO-Platzhalter (Hausstil) bzw. rote Zeile (Standard), FU löst Sicherheitsseite SIK und FEHLER bis Freigabevermerk aus (A49/A51) | behoben |
| E2 | Elektro | hoch | Motorleitung gegen MSS vor dem FU geprüft → falscher FEHLER bei I_ein < I_N | Schutzorgan der Motorleitung = FU (Stromgrenze I_aus); Test Grenzfall 3 kW/7 A | behoben |
| E3 | Elektro | mittel | Motorleitung nur nach I_N | Bemessung nach I_aus (konservativ), Warnung „I²t = I_N, Stromgrenze ≤ I_aus“ | behoben |
| E5 | Elektro | mittel | Anschlüsse L1–L3/U–W am FU nicht beschriftet | beschriftet (Hausstil) | behoben |
| E9 | Elektro | gering | RL1-Verweis fehlt im Lastkreis, Verweis auf MSS statt FU | ergänzt / auf FU gestellt | behoben |
| S1 | Software | mittel | eigener FU ohne Pflichtwert → Absturz | Klartext je fehlendem Wert; `vorsicherung_max_A` Pflicht | behoben |
| S3 | Software | mittel | Spalte „Anlauf“ nur mit exaktem Namen | Spalte beginnt mit „Anlauf“ genügt; Test | behoben |
| S4 | Software | mittel | Tests fehlen (Vorsicherung, Kabel, viele FU, Rundreise, EPLAN, Excel) | 3 Tests ergänzt | behoben |
| S8–S10, S12 | Software | gering | Verweis, Meldungstexte ohne Motor/Komma, -T in Doppelt-Meldung, Auswahlwerte im Schema | behoben | behoben |
| S2 | Software | mittel | Lernschleife erreicht programmgewählte Geräte (FU/Schütz/MSS) nicht | → Paket M5f | offen (M5f) |
| E4, E6, E7 | Elektro | mittel | PE am FU/Schirmauflage zeichnen; Standardstil Störrelais als Kontakt; Bezugspotentiale COM/AGND und geschirmte Sollwertleitung | → Paket M7d (FU-Nacharbeit) | offen (M7d) |
| E8, E10, E11, S5–S7, S11 | beide | gering | Ruhestrom-Störmeldung, Darstellung -T2.2 als -T2:AI1, max. Motorleitungslänge, Kennbuchstabe FU aus Hausprofil, EPLAN-Kennzeichen Teilsignale, Klemmenziele einheitlich, AO-Meldung | gesammelt in M7d | offen (M7d) |
| S13 | Software | gering | mypy `analyse.py:48` | lokal mit `vor_commit.sh` und in CI ohne Befund – nicht nachvollziehbar (andere mypy-Version beim Prüfer, nicht verifiziert) | geprüft |
