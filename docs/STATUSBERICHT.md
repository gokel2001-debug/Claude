# STATUSBERICHT – Sammelbericht für die Überwachung

Berichtszeitraum: seit Projektbeginn (noch keine Überwachungsantwort) – Sitzungen: 1 (20.11.2026, manuell: ZIEL.md, M1, M2a–M2d)
Branch: `claude/ai-schaltplan-generator-u6lzbz`

## 1. Meilenstein aktuell / Fortschritt
- M1 – 100 %, erledigt.
- M2 – erledigt (M2a–M2d, CI grün auf Ubuntu+Windows); Fertig-Kriterium belegt mit einer unabhängigen KI-Instanz und synthetischem Lastenheft. Erprobung mit der im Betrieb freigegebenen KI = PC6.
- Nächster Meilenstein: M3 (Planungskern trennen, `planmodell.json`).

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
| 20.11. | Autostart | `docs/ARBEITSVORRAT.md` als Warteschlange; alle 3 Autostarts arbeiten sie ab und füllen sie auf ≥ 5 Pakete auf | – |

Prüfungen (`docs/pruefungen/`): M2a 7 hoch, M2b 6 hoch, M2c 1 kritisch + 5 hoch – alle behoben. Der kritische Befund (zerrissenes Menü in start.bat) war ein eigener Einfügefehler; start.bat ist jetzt per Test abgesichert.

## 3. Tests
164/164 grün; ruff ohne Befund; Abdeckung gesamt 95 %, Planungskern 95 %.

## 4. Neue vorläufige Annahmen
A17 DBU/LBU als Hausfarben; A18 Vorgaben nicht neu anbieten; A19 Hauptschalter als Hausvorgabe; A20 Hausvorgaben = Beispielwerte; A21 Kennbuchstaben der KI-Anleitung (Hausregel, nicht IEC 81346-2); A23 Längengrenze KI-Auftrag; A24 Ablage KI-Anleitung; A25 strukturierte Meldungen für die Oberfläche.

## 5. Offene Fehler / Risiken
- Leitungsschutz-/Kurzschlussnachweise fehlen (A5, A15); I_z-Tabelle ohne Quelle (A3).
- 230-V-Pumpen erscheinen in der 24-V-Abgangsliste (0 A) → M4d.
- start.bat kann nur gelesen, nicht unter Windows ausgeführt werden (PC-Test nötig).

## 6. Abweichungen von ZIEL.md
- Steuerdateien in `docs/`, ZIEL.md unter `schaltplan_generator/docs/`.
- „Externe KI“ für das M2-Kriterium: unabhängige KI-Instanz ohne Projektkontext statt Betriebs-KI (PC6 folgt).

## 7. Nächster geplanter Schritt
Autostart Fr 22:07: oberstes offenes Paket in `docs/ARBEITSVORRAT.md` (M3a Planungskern trennen).

## 8. Fragen an die Überwachung (max. 3)
1. Sollen die Steuerdateien nach `schaltplan_generator/docs/` umziehen? Annahme: bleiben in `docs/`.
2. Für die Elektrofachkraft: A3, A5, A11, A12, A17, A20, A21 in `docs/OFFENE_PUNKTE.md`.
