# STATUSBERICHT – Sammelbericht für die Überwachung

Berichtszeitraum: seit Projektbeginn (noch keine Überwachungsantwort) – Sitzungen: 4 (20.11. manuell: ZIEL.md, M1–M4c; Autostart Fr 22:07: M4d, M2e, M5a–M5d; Autostart Sa 03:12: M5e, M6a, M7a–M7c, M5f, M8a, M9a; Autostart Sa 08:17: durch Nutzungslimit erst 11:18 gestartet, nur Abschluss)
Stand: 21.11.2026, letzter Commit 95ad855 (+ diese Ergänzung)
Branch: `claude/ai-schaltplan-generator-u6lzbz`

## 1. Meilenstein aktuell / Fortschritt
| Meilenstein | Stand | Fortschritt (Schätzung, nicht gemessen) |
|---|---|---|
| M1–M4 | erledigt (M4e interner Umbau zurückgestellt) | 100 % |
| M5 Lernen/Lernschleife | M5a–M5f erledigt; offen M5g (Bedingungen nach Motordaten, Regressionsfall gegen Planergebnis) | ca. 85 % |
| M6 lokale KI | Kern erledigt; echter Ollama-Test = PC5 | ca. 80 % |
| M7 Artikel/Bausteine | M7a–M7c erledigt (Artikelstamm, Sicherheits-Platzhalter, Motor mit FU); offen M7d (FU-Nacharbeit, Wende-/Stern-Dreieck); „10 echte Pläne“ = PC3 | ca. 70 % |
| M8 Abnahme | M8a erledigt (Abweichungsliste Referenz ↔ Nachbau); offen M8b, echte Erprobung PC8 | ca. 40 % |
| M9 Verteilung | M9a umgesetzt (Windows-Paket ohne Python, CI-Artefakt); offen Software-Prüfung M9a, M9b Installer | ca. 40 % |

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
| 21.11. | M5e | Korrekturart Mindestquerschnitt, Vorschau, Menüpunkte K/L, Artikelliste | 253/253 |
| 21.11. | M6a | Lokale KI (Ollama): Auftrag direkt, Antwort wie Chat geprüft, Proxy umgangen | 263/263 |
| 21.11. | M7a | Eigener Artikelstamm: Export → Zuordnungsliste (Vorschläge ohne Kennwert-Widerspruch) → Stückliste/EPLAN | 270/270 |
| 21.11. | M7b | Sicherheitskreis nur als rote Platzhalterseite (Not-Halt/PL, Stoppkategorie, betroffene Antriebe); Plan „NICHT FÜR FERTIGUNG“ bis Freigabevermerk „Name, Datum“ der Elektrofachkraft (nie aus KI-Antwort); Not-Halt-Geräte an Standard-SPS = FEHLER | 296/296 |
| 21.11. | M7c | Motorabgang mit Frequenzumrichter (`anlauf: fu`): FU-Auswahl, MSS auf Netzstrom, Motorleitung geschirmt nach I_aus, Freigabe/Sollwert/Störung an SPS, STO nur als Platzhalter | 304/304 |
| 21.11. | M5f | Lernschleife: vom Programm gewählte Geräte (FU/Schütz/MSS/Klemmen) per Hausregel ersetzen mit Auslegungsprüfung; Sammelregel Kennbuchstabe → 24-V-Gruppe | 310/310 |
| 21.11. | CI | rot durch neue pypdf 7 (Typprüfung) und Windows-Zeitverhalten eines Tests → beide behoben, CI grün | 310/310 |
| 21.11. | M8a | Abweichungsliste Referenzplan ↔ Nachbau: Kennzeichen, Klemmen, Adressen, SPS-Belegung je Adresse, Artikel je Gerät; Excel mit Bewertung, Auszählung, Abnahmefeld; Menü V | 316/316 |
| 21.11. | M9a | Windows-Programmpaket per PyInstaller ohne Python; Workflow „Paket“ baut auf Windows und prüft die Exe (Selbsttest, Excel, KI-Auftrag) – grün; start.bat erkennt die Exe | 318/318 |
| 20.11. | Autostart | `docs/ARBEITSVORRAT.md` als Warteschlange; alle 3 Autostarts arbeiten sie ab und füllen sie auf ≥ 5 Pakete auf | – |

Prüfungen (`docs/pruefungen/`): M2a 7 hoch, M2b 6 hoch, M2c 1 kritisch + 5 hoch, M3 1 hoch, M4a 2 hoch, M4b 3 hoch, M4c 4 hoch, M4d 3 hoch, M5a 3 hoch, M5b 2 hoch, M5c 7 hoch, M5d 2 hoch, M5e 2 hoch, M6a 2 hoch, M7a 2 hoch, M7b 1 kritisch + 7 hoch (inkl. Nachprüfung), M7c 2 hoch, M5f 2 hoch (1 neue Funktion → M5g), M8a 4 kritisch + 6 hoch (Rest → M8b), M9a Einsteiger 2 hoch – alle kritisch/hoch behoben oder als eigenes Paket eingeplant; Software-Prüfung M9a durch Nutzungslimit abgebrochen (offen). Wichtigster Fund: Ohne Gegenmaßnahme wäre das Lastenheft bei eingestelltem Proxy an diesen statt an die lokale KI gegangen. Zweimal hat eine eigene Textersetzung start.bat beschädigt; der Strukturtest fängt das jetzt sofort. Der kritische Befund (zerrissenes Menü in start.bat) war ein eigener Einfügefehler; start.bat ist jetzt per Test abgesichert.

## 3. Tests
318/318 grün (Nacht: +48 Tests: Sicherheit, FU, Lernschleife, Abweichungsliste, Exe-Pfade); ruff und mypy ohne Befund; CI Ubuntu+Windows grün; Workflow „Paket“ (Windows-Exe) grün.

## 4. Neue vorläufige Annahmen
A17–A33 (siehe frühere Fassung); neu in dieser Nacht: A49 Sicherheit nur Platzhalter, A50 Freigabevermerk nur „Name, Datum“ und nie aus KI, A51 Motor mit FU (MSS als Vorsicherung auf I_ein, Motorleitung nach I_aus, STO-Platzhalter), A52 Hausregel für programmgewählte Geräte, A53 Sammelbedingung nur Kennbuchstabe, A54 Abweichungsliste (Hausstil-Muster, „nicht auswertbar“ statt 100 %), A55 Windows-Paket unsigniert als CI-Artefakt.

## 5. Offene Fehler / Risiken
- Leitungsschutz-/Kurzschlussnachweise fehlen (A5, A15); I_z-Tabelle ohne Quelle (A3).
- Abweichungsliste nur an selbst erzeugten Plänen erprobt – echte EPLAN-PDFs können „nicht auswertbar“ ergeben (PC8).
- Windows-Paket unsigniert: Virenscanner/SmartScreen am Firmen-PC ungeprüft (PC9); Software-Prüfung M9a steht aus.
- FU-Stammwerte und Sicherheitsangaben sind synthetisch bzw. Platzhalter – nichts davon ist fertigungsreif.
- Nutzungslimit: Autostart 08:17 kam erst 11:18 an (5-h- und Wochenlimit), dadurch ging ein Fenster verloren.

## 6. Abweichungen von ZIEL.md
- Steuerdateien in `docs/`, ZIEL.md unter `schaltplan_generator/docs/`.
- „Externe KI“ für das M2-Kriterium: unabhängige KI-Instanz ohne Projektkontext statt Betriebs-KI (PC6 folgt).

## 7. Nächster geplanter Schritt
Software-Prüfung M9a nachholen, dann laut Arbeitsvorrat: M8b (Abnahme vertiefen), M5g (Regeln nach Motordaten), M7d (FU-Nacharbeit, weitere Anlaufarten), M9b (Installer), M4e. Am PC: PC3, PC5, PC7, PC8, PC9.

## 8. Fragen an die Überwachung (max. 3)
0. Produkt-Prüfer empfiehlt Reihenfolge M4c → M4d → M5 → M8-Vorabtest mit echtem Plan → M7 → M6 → M4e und die Lernschleife (M5c) vor M7. ZIEL-Reihenfolge ist verbindlich – ändern? Umgesetzt: M4e (reiner Umbau) hinter M5/M6 gestellt; übrige Reihenfolge bleibt.
1. Sollen die Steuerdateien nach `schaltplan_generator/docs/` umziehen? Annahme: bleiben in `docs/`.
2. Für die Elektrofachkraft: A3, A5, A11, A12, A17, A20, A21, A30, A31, A34, A36, A42, A44, A45, A46, A47, **neu A49–A51 (Sicherheit, FU)** in `docs/OFFENE_PUNKTE.md`; am PC: PC3 (echte Pläne lernen), PC5 (Ollama), PC7 (Artikelexport), **PC8 (Abnahme an 3 echten Plänen), PC9 (Programmpaket ohne Python)**.
