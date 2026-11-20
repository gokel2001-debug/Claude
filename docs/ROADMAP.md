# Roadmap (angepasst an `schaltplan_generator/docs/ZIEL.md`, Stand 20.11.2026)

ZIEL.md hat Vorrang. Reihenfolge der Meilensteine ist verbindlich.

## Meilensteine
| M | Inhalt | fertig, wenn | Status |
|---|---|---|---|
| M1 | Offene Fehler aus P5a beheben | Tests für ungültige Werte und Überschreiben grün | **erledigt** 20.11.2026 (2 Prüfer, Befunde behoben) |
| M2 | Projektmodell-Schema und `KI_AUFBEREITUNG.md` | Beispiel-Lastenheft → gültige YAML (manuell über externe KI) | **Kern erledigt** 20.11.2026 (unabhängige KI-Instanz, synthetisches Lastenheft; Menü 8/9 fertig (M2c); CI = M2d; Erprobung mit Betriebs-KI = PC6) |
| M3 | Planungskern trennen (`planmodell.json`) | PDF entsteht nur noch aus dem Planmodell | **erledigt** 20.11.2026 (planmodell.json, Schema, EPLAN-Stub; PDFs aus JSON byte-gleich) |
| M4 | SPS-Übersicht, Listen im Hausformat, Konsistenzprüfungen | Prüfbericht ohne Fehler am Testkorpus | **erledigt** 20.11.2026 (SPS-Übersicht, Listen, Prüfbericht ohne Fehler am Testkorpus; M4e = interner Umbau, A27) |
| M5 | Geometrie und Schriftfeld lernen | Hausprofil aus 10 echten Plänen mit Sicherheitsangabe | offen (Vorarbeit: P2 Lernen aus Text) |
| M6 | Ollama-Anbindung Stufe A | gleiches Ergebnis wie M2, lokal | offen |
| M7 | Bausteinbibliothek erweitern (3~, FU, Sicherheitskreise als Platzhalter) | jeder Baustein mit Quelle/Annahme und Test | offen (Vorarbeit: P4a–P4c) |
| M8 | Abnahme, Nachbau des Referenzplans | Abweichungsliste mit Bewertung | offen |
| M9 | Installer/Exe (GitHub Actions), Handbuch, Browser-Oberfläche, EPLAN-Stub | DoD Punkt 6 erfüllt | offen |

## Erledigte Pakete (vor ZIEL.md)
| Paket | Inhalt | Beitrag zu |
|---|---|---|
| P1/P1b | Steuerdateien, erfundener Testkorpus | Grundlage |
| P2 | Hausprofil lernen aus Text-Ebene, Jahrestrend | M5 |
| P3a | Freigabe per Excel-Liste | M5 |
| P3b | Hausstil-PDF (Anlage je Funktion, Spalten 0–9, Verweise) | M3/M4 |
| P4a–P4c | Bausteine (Zähler, Stellantrieb, Pumpe 1~), Selektivmodul | M7 |
| P5a | Aderfarben/Kennbuchstaben als Vorgaben (Befunde offen → M1) | M4/M5 |

## Langläufer (ZIEL.md Abschnitt 4)
Autostart Fr 22:07, Sa 03:12, Sa 08:17 (Europe/Berlin); ab Sa 09:45 nichts Neues beginnen.
Je Paket: Umsetzung → Tests → Commit/Push → Prüfer-Agenten (`.claude/agents/`) → Nacharbeit → `docs/STATUSBERICHT.md`.
