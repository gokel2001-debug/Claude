# STATUSBERICHT – Sammelbericht für die Überwachung

Berichtszeitraum: seit 21.11.2026 (Antwort der Überwachung, archiviert unter `docs/berichte/2026-11-21_*`) – Sitzungen: 1
Branch: `claude/ai-schaltplan-generator-u6lzbz`

## 0. DoD-Abgleich (ZIEL.md Abschnitt 1)
| Nr. | DoD-Punkt | Status | Nachweis / was fehlt |
|---|---|---|---|
| 1 | Eingabe Lastenheft (Freitext/PDF/Word), Feldgeräteliste, Datenblätter | teilweise | Lastenheft .txt/.md/.docx/.pdf → KI-Auftrag → Projektmodell (M2/M6), Excel-Feldgeräteliste (M2c), Datenblatt-Vorschlag (`datenblatt`). Fehlt: Bedienung über Oberfläche (M10b); nur synthetisch erprobt |
| 2 | Ausgabe Plan-PDF im Hausstil, Stückliste, Klemmenplan, Kabelliste, Auslegungsnachweis | teilweise | alle Teile vorhanden (M4). Fehlt: Leitungsschutz/Kurzschluss mit Normquelle (M4f), Download über Oberfläche (M10d); nur synthetisch erprobt |
| 3 | Hausstil aus Bestandsplänen lernen, Freigabeliste | teilweise | Lernen aus Vektor-PDF + Freigabe per Excel (M5a–M5d), Lernschleife (M5c–M5f). Fehlt: Erprobung an 10 echten Plänen (PC3), Scans, Gelernt-Seite (M10f) |
| 4 | Jede Auslegung mit Quelle oder als Annahme | teilweise | Prüfbericht mit Quelle je Regel, 55 Annahmen in `OFFENE_PUNKTE.md`, neu `EFK_FREIGABE.xlsx`. Fehlt: Normquellen für I_z/Leitungsschutz/Kurzschluss (A3, A5, A15 → M4f) |
| 5 | Abnahme: echter Referenzplan nachgebaut, EFK bewertet „gleichwertig“ | offen | Werkzeug vorhanden (M8a, Abweichungsliste), nur gegen selbst erzeugte Pläne erprobt; echte Abnahme = PC8 |
| 6 | Installer/portable Version, Handbuch, alle Tests grün | teilweise | portables Windows-Paket per CI (M9a, Exe-Selbsttest grün), Einsteiger-Anleitung (Markdown), 318 Tests grün. Fehlt: Oberfläche (M10), Handbuch als PDF mit Bildschirmfotos, Installer (M9b), PC-Test (PC9) |

## 1. Meilenstein aktuell / Fortschritt (Teilpakete erledigt / geplant)
| Meilenstein | Fortschritt | Anmerkung |
|---|---|---|
| M1–M3 | alle erledigt | – |
| M4 | 4 von 6 (M4a–d; offen M4e, M4f) | M4f = Ü3-Nachweise |
| M5 | 6 von 7 (M5a–f; offen M5g) | „10 echte Pläne“ braucht PC3 |
| M6 | 1 von 1 | echter Ollama-Test = PC5 |
| M7 | 3 von 4 (M7a–c; offen M7d) | – |
| M8 | 1 von 2 (M8a; offen M8b) | echte Abnahme = PC8 |
| M9 | 2 von 3 (M9a, M9p; offen M9b Installer) | – |
| M10 | 1 von 6 (M10a; offen M10b–f) | neu (Ü-E1) |

## 2. Seit letztem Bericht erledigt
| Datum | Paket | Ergebnis | Erprobt an | Tests |
|---|---|---|---|---|
| 21.11. | Überwachungsantwort übernommen | archiviert, Ü-E1–E6 in `ENTSCHEIDUNGEN.md`, E19 (Technik M10) vorläufig, Arbeitsvorrat auf neue Reihenfolge, ROADMAP M10, PC-Tag-Reihenfolge, Satz in ZIEL.md (Ü-E5), `docs/EFK_FREIGABE.xlsx` (55 Annahmen) | – | 318/318 |
| 21.11. | M9p | Software-Prüfung M9a nachgeholt: keine kritisch/hoch; behoben: Prüfausgabe im Artefakt, nur git-erfasste Beispiele ins Paket, Exe-Hinweistexte, Workflow-Rechte; Test ergänzt | synthetisch (CI-Windows-Lauf) | 319/319 |
| 21.11. | M10a | Oberfläche im Browser (nur 127.0.0.1): Projektliste, Projekt anlegen, Projektseite mit 6-Schritte-Leiste, Excel/Ordner öffnen, Hilfe; eigenes Fenster, Menü bleibt frei; Prüfung UX+Einsteiger 4 hoch → behoben | synthetisch (E2E per HTTP, Bildschirmfotos) | 331/331 |

## 3. Tests
331/331 grün; ruff und mypy ohne Befund; CI Ubuntu+Windows und Workflow „Paket“ (Windows-Exe) grün.

## 4. Neue vorläufige Entscheidungen
E19 – Oberfläche als lokaler Webserver aus der Python-Standardbibliothek (127.0.0.1, ohne Internet, ohne neue Abhängigkeit, im Exe-Paket lauffähig, End-to-End-Test per HTTP in CI).

## 5. Offene Fehler / Risiken
- Alles nur an synthetischen bzw. selbst erzeugten Plänen erprobt (Ü2) – größtes Risiko; erster PC-Tag: PC9 → PC3 → PC8.
- Leitungsschutz-/Kurzschlussnachweis fehlt, I_z ohne Quelle (Ü3 → M4f).
- Nutzungslimit (5 h und Woche) kann Autostarts ausfallen lassen.

## 6. Abweichungen von ZIEL.md (jede Lücke)
- Oberfläche nach 4a/4b fehlt (Ü1): Bedienung über Konsolenmenü und Excel → M10.
- 4b „Kein Code, keine Konsole“: Konsolenfenster und Excel sind die Oberfläche; Hausregel-Datei YAML wird nicht vom Anwender bearbeitet, `hausprofil` aber als Ordner sichtbar.
- 4b Projektordner mit Versionen/Wiederherstellen: Projektordner ja, Versionen nein (→ M10d).
- 4b Hilfe: kein Fragezeichen je Seite, Handbuch nur Markdown ohne Bildschirmfotos (→ M10a, M9b).
- 4b Updates „automatisch übernommen“: nur Anleitung zum Kopieren von `hausprofil`/`meine_projekte` (→ M9b).
- 4b Einlernen mit Fortschrittsbalken und Vorschau: nur Konsole (→ M10f).
- DoD 3 „später Scans“: nicht begonnen.
- DoD 5/M5 „10 echte Pläne“: nur synthetisch (PC3, PC8).
- M9 „Installer“: nur portables Paket (→ M9b).
- Steuerdateien in `docs/` (bestätigt Ü-E5).

## 7. Nächster geplanter Schritt
M10b (Unterlagen einlesen + prüfen in der Oberfläche). Arbeitsvorrat: M10a–f, M4f, M8b, M5g, M7d, M9b, M4e.

## 8. Fragen an die Überwachung (max. 3)
1. E19 (Oberfläche als lokaler Webserver aus der Standardbibliothek) – so bestätigen?
2. Für die Elektrofachkraft: `docs/EFK_FREIGABE.xlsx` ausdrucken und abzeichnen lassen (55 Annahmen, Schwerpunkt A3, A5, A15, A49–A51).
