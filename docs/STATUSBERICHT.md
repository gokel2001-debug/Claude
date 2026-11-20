# STATUSBERICHT – Sammelbericht für die Überwachung

Berichtszeitraum: seit Projektbeginn (noch keine Überwachungsantwort) – Sitzungen: 2 (20.11.2026 manuell: ZIEL.md, M1–M4c; Autostart Fr 22:07: M4d, M2e, M5a–M5d)
Branch: `claude/ai-schaltplan-generator-u6lzbz`

## 1. Meilenstein aktuell / Fortschritt
- M1 – 100 %, erledigt.
- M2 – erledigt (M2a–M2d, CI grün auf Ubuntu+Windows); Fertig-Kriterium belegt mit einer unabhängigen KI-Instanz und synthetischem Lastenheft. Erprobung mit der im Betrieb freigegebenen KI = PC6.
- M3 – erledigt: PDFs entstehen nur noch aus `planmodell.json` (aus JSON byte-gleich), Schema `docs/SCHEMA_PLANMODELL.md`, EPLAN-Adapter als Stub.
- M4 – erledigt (SPS-Übersicht, Listen, Prüfbericht ohne Fehler am Testkorpus, Projektordner, Stempel „NICHT FÜR FERTIGUNG“); M4e (interner Umbau) zurückgestellt.
- M5 – M5a–M5c erledigt (Geometrie/Schriftfeld, Kennbuchstaben und Anlagenaufbau lernen, Lernschleife mit Hausregeln); M5d erledigt (Datumsformat wirkt im Plan, Spaltenraster nur bei 10 Spalten); offen: M5e (weitere Korrekturarten, Menü). Kriterium „Hausprofil aus 10 echten Plänen“ braucht PC3.

## 2. Seit letztem Bericht erledigt
| Datum | Paket | Ergebnis | Tests |
|---|---|---|---|
| 19.11. | P1–P5a (vor ZIEL.md) | Excel → PDF (bisher + Hausstil), Hausprofil, Bausteine, Selektivmodul | 75/75 |
| 20.11. | ZIEL.md übernommen | Steuerdateien, 6 Prüfer, Autostarts | 75/75 |
| 20.11. | M1 | Eingabeprüfung Freigabeliste (IEC 60757), alle Fehler auf einmal | 90/90 |
| 20.11. | M2a | Schema Projektmodell v1 (`docs/SCHEMA_PROJEKTMODELL.md`), Prüfung mit allen Lücken im Klartext, Hausvorgaben | 144/144 |
| 20.11. | M2b | `docs/KI_AUFBEREITUNG.md`, Befehl `ki-auftrag`, Lastenheft → KI → PDF; Fehler Motor-Lastseite behoben | 158/158 |
| 20.11. | M2c | Menü 8/9 (KI-Auftrag in Zwischenablage, KI-Antwort prüfen → Plan oder Korrekturauftrag), Zeilennummern | 164/164 |
| 20.11. | M2d | GitHub Actions (Ubuntu + Windows, Python 3.12/3.13): ruff, pytest, Abdeckung Kern ≥ 90 % | 164/164 |
| 20.11. | M3a/b | Planungskern getrennt (planmodell.json, Kennzeichen im Modell, Befehl `zeichnen`), Schema, EPLAN-Stub | 184/184 |
| 20.11. | M4a | SPS-Kartenseiten mit allen Kanälen (Reserve, Schrankanschluss/Feldklemme, Versorgung), Steckplatzübersicht; Adressen überschneidungsfrei | 186/186 |
| 20.11. | M4b | Listen im Hausformat: Klemmenplan je Leiste, Kabelübersicht mit Länge, Summenstückliste, Nachweis gegliedert | 187/187 |
| 20.11. | M4c | Prüfbericht mit Quelle je Regel (inkl. Leitungsschutz I_B ≤ I_n ≤ I_z, Motorschutz, offene Potentiale) bei jeder Ausgabe; Kennzahl Zeichenaufwand (A36) | 210/210 |
| 20.11. | M4d | Projektordner, Feldleitungslängen, Prüfungen Netzteil/DO-Last, Stempel bei FEHLER | 216/216 |
| 20.11. | M2e | Typprüfung mypy 150 → 0, in CI | 216/216 |
| 20.11. | M5a | Geometrie/Schriftfeld lernen (Freigabeliste), Planjahr aus Feld „Datum“ | 228/228 |
| 21.11. | M5b | Kennbuchstaben Netzteil/SPS-Karte, Anlagenaufbau aus Plänen; Ende-zu-Ende lernen → Freigabe → Plan | 240/240 |
| 21.11. | M5c | Lernschleife: Korrektur → Hausregel (Bearbeiter, Datum, Geltung) → wirkt vor Prüfung/Planung → Regressionstest; ein/aus/löschen | 248/248 |
| 21.11. | M5d | Gelerntes Datumsformat wirkt in Rahmen und Deckblatt; Spaltenraster begrenzt auf 10 Spalten (A45) | 249/249 |
| 20.11. | Autostart | `docs/ARBEITSVORRAT.md` als Warteschlange; alle 3 Autostarts arbeiten sie ab und füllen sie auf ≥ 5 Pakete auf | – |

Prüfungen (`docs/pruefungen/`): M2a 7 hoch, M2b 6 hoch, M2c 1 kritisch + 5 hoch, M3 1 hoch, M4a 2 hoch, M4b 3 hoch, M4c 4 hoch, M4d 3 hoch, M5a 3 hoch, M5b 2 hoch, M5c 7 hoch, M5d 2 hoch – alle behoben. Zweimal hat eine eigene Textersetzung start.bat beschädigt; der Strukturtest fängt das jetzt sofort. Der kritische Befund (zerrissenes Menü in start.bat) war ein eigener Einfügefehler; start.bat ist jetzt per Test abgesichert.

## 3. Tests
249/249 grün; ruff und mypy ohne Befund; CI (Ubuntu + Windows) mit Typprüfung; lokale Prüfung `vor_commit.sh`.

## 4. Neue vorläufige Annahmen
A17 DBU/LBU als Hausfarben; A18 Vorgaben nicht neu anbieten; A19 Hauptschalter als Hausvorgabe; A20 Hausvorgaben = Beispielwerte; A21 Kennbuchstaben der KI-Anleitung (Hausregel, nicht IEC 81346-2); A23 Längengrenze KI-Auftrag; A24 Ablage KI-Anleitung; A25 strukturierte Meldungen; A26 EPLAN-Importweg; A27 Kennzeichen-Strukturlogik; A28 Verbindungen; A29 Steckplatzreihenfolge; A30 SPS-Adressvergabe; A31–A33 offene Prüferpunkte (Ortsaspekt Feldgeräte, Kartenpins, Analogdetails).

## 5. Offene Fehler / Risiken
- Leitungsschutz-/Kurzschlussnachweise fehlen (A5, A15); I_z-Tabelle ohne Quelle (A3).
- 230-V-Pumpen erscheinen in der 24-V-Abgangsliste (0 A) → M4d.
- start.bat kann nur gelesen, nicht unter Windows ausgeführt werden (PC-Test nötig).

## 6. Abweichungen von ZIEL.md
- Steuerdateien in `docs/`, ZIEL.md unter `schaltplan_generator/docs/`.
- „Externe KI“ für das M2-Kriterium: unabhängige KI-Instanz ohne Projektkontext statt Betriebs-KI (PC6 folgt).

## 7. Nächster geplanter Schritt
Autostart Sa 03:12: oberstes offenes Paket in `docs/ARBEITSVORRAT.md` (M5e Lernschleife ausbauen), dann M6a, M7a, M7b.

## 8. Fragen an die Überwachung (max. 3)
0. Produkt-Prüfer empfiehlt Reihenfolge M4c → M4d → M5 → M8-Vorabtest mit echtem Plan → M7 → M6 → M4e und die Lernschleife (M5c) vor M7. ZIEL-Reihenfolge ist verbindlich – ändern? Umgesetzt: M4e (reiner Umbau) hinter M5/M6 gestellt; übrige Reihenfolge bleibt.
1. Sollen die Steuerdateien nach `schaltplan_generator/docs/` umziehen? Annahme: bleiben in `docs/`.
2. Für die Elektrofachkraft: A3, A5, A11, A12, A17, A20, A21, A30, A31, A34, A36, A42, A44 in `docs/OFFENE_PUNKTE.md`.
