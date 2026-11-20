# Prüfung M2a – Software-Qualität (pruefer-software), 20.11.2026

Gegenstand: Commit 4d584be (Schema Projektmodell v1, `pruefe`, `bereit_machen`, CLI `pruefen`/`schema`).
Ergebnis: 5 hoch, 3 mittel, 2 gering – alle behoben (Commit „M2a Nacharbeit“).

| Nr. | Schwere | Befund | Erledigung |
|---|---|---|---|
| 1 | hoch | leere Abschnitte (`sps:` ohne Inhalt) → „vollständig“, dann TypeError in `plane` | leer = fehlt; Hausvorgaben füllen auch leere Abschnitte; Test |
| 2 | hoch | Listen statt Einzelwerte (artikel, typical) → TypeError in `pruefe` | Typprüfung vor jedem Zugriff; Test |
| 3 | hoch | `sps.module_kandidaten`/`adressschema` ungeprüft → KeyError | Kategorie `sps_<art>` + Kanalzahl, Platzhalter `{byte}{bit}{wort}` per Probe; Test |
| 4 | hoch | `leitungen.i_z_A` mit Komma/Text → ValueError/KeyError | Prüfung > 0, Vereinheitlichung zu {Zahl: Zahl}; Test |
| 5 | hoch | ungültiges Datum, ANSI-Datei → Traceback | Klartext bzw. Rückfall cp1252; Sicherheitsnetz in `main` (Log-Datei statt Traceback); Tests |
| 6 | mittel | doppelte Schlüssel überschreiben still | eigener Lader meldet „steht doppelt (Zeile n)“; Test |
| 7 | mittel | Feldgerät mit Netzteil-Artikel besteht Prüfung | nur Kategorie Sensor/Aktor; Test |
| 8 | mittel | Projektnummer mit `../` oder `:` als Dateiname | verbotene Zeichen abgelehnt; Test |
| 9 | gering | ruff I001/ISC004 | behoben, neue Dateien ohne Befund |
| 10 | gering | fehlende Leitungstabelle, still ignorierte `--vorgaben`, bool als Text | alle drei gemeldet; Tests |

Absicherung: `test_keine_stoerung_fuehrt_zum_absturz` – 20 Störungen, jede endet in Klartext-Fehler oder gültigem Plan.
