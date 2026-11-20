# STATUSBERICHT – Sammelbericht für die Überwachung

Berichtszeitraum: seit Projektbeginn (noch keine Überwachungsantwort) – Sitzungen: 1 (20.11.2026, Übernahme ZIEL.md + M1)
Branch: `claude/ai-schaltplan-generator-u6lzbz` – letzter Commit: „M1: Prüferbefunde behoben, M1 erledigt“

## 1. Meilenstein aktuell / Fortschritt
M1 (offene Fehler aus P5a) – **100 %, erledigt**. M2 (Projektmodell-Schema) – 0 %, nächster Schritt.

## 2. Seit letztem Bericht erledigt
| Datum | Paket | Ergebnis | Tests |
|---|---|---|---|
| 19.11.2026 | P1–P5a (vor ZIEL.md) | Excel → PDF (bisheriger Stil + Hausstil), Hausprofil lernen/freigeben, Bausteine Zähler/Stellantrieb/Pumpe 1~, Selektivmodul, Aderfarben/Kennbuchstaben als Vorgaben | 75/75 |
| 20.11.2026 | ZIEL.md übernommen | ZIEL.md, CLAUDE.md, Roadmap M1–M9, 6 Prüfer-Agenten, OFFENE_PUNKTE, PC_AUFGABEN, Sammelbericht | 75/75 |
| 20.11.2026 | M1 | Eigene Werte der Freigabeliste je Merkmal geprüft (Farbkürzel IEC 60757, Kennbuchstabe, Klemmleiste, Adressschreibweise), alle Fehler auf einmal mit „nichts übernommen“, Spalte „Erlaubte Form / Beispiel“, Vorgaben nach Freigabe nicht neu angeboten, Auslegungsnachweis mit Beschreibung + Wert, Nachprüfung älterer Profile mit Warnung | 90/90 |

Prüfungen M1: `docs/pruefungen/M1_Software.md`, `docs/pruefungen/M1_Einsteiger.md` – 0 kritisch/hoch, 3 mittel, 6 gering, alle behoben.

## 3. Tests
90/90 grün (pytest), davon 15 neu für M1. Linter und Abdeckungsmessung sind noch nicht eingerichtet (Ziel ≥ 90 %, geplant mit CI).

## 4. Neue vorläufige Entscheidungen
- A17: Aderfarben DBU/LBU zusätzlich zu IEC 60757 zulässig (Hausregel, im Bestand üblich).
- A18: freigegebene/abgelehnte Vorgaben werden beim Lernen nicht neu angeboten (bis M5).
- E8–E18 weiter als Annahmen A6–A14 in `docs/OFFENE_PUNKTE.md`.

## 5. Offene Fehler / Risiken
- Architektur noch nicht A/B/C-getrennt (→ M2/M3); keine Browser-Oberfläche/Exe (→ M9); kein CI/Linter (→ M2/M9).
- Leitungsschutz-/Kurzschlussnachweise fehlen (A5, A15).
- Alte Freigabelisten (9 Spalten) werden abgewiesen → Menüpunkt 6 neu ausführen (Klartext-Hinweis vorhanden).

## 6. Abweichungen von ZIEL.md
- Steuerdateien liegen im Repo-Ordner `docs/`, ZIEL.md unter `schaltplan_generator/docs/` (bestehende Autostarts verweisen auf `docs/`).

## 7. Nächster geplanter Schritt
M2: `docs/SCHEMA_PROJEKTMODELL.md`, `docs/KI_AUFBEREITUNG.md`, Schemaprüfung `projektmodell.yaml` mit Lücken im Klartext.

## 8. Fragen an die Überwachung (max. 3)
1. Sollen alle Steuerdateien nach `schaltplan_generator/docs/` umziehen? Annahme bis zur Antwort: bleiben in `docs/`.
2. Für die Elektrofachkraft (direkt an den Nutzer): A3, A5, A11, A12, A17 in `docs/OFFENE_PUNKTE.md`.
