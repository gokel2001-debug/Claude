# UEBERWACHUNG_ANTWORT – 21.11.2026

Bezug: STATUSBERICHT, Stand 21.11.2026, Commit 95ad855 (4 Sitzungen). Diese Antwort gilt als Nutzer-Entscheidung. Bitte nach ZIEL.md Abschnitt 5 archivieren, einen neuen Sammelbericht beginnen und die Punkte unten in `ENTSCHEIDUNGEN.md` übernehmen.

## 1. Gesamtbewertung

Die Richtung stimmt, die Arbeitsweise ist gut (Tests, CI, Typprüfung, Prüfer, Sicherheit nur als Platzhalter). Es gibt aber zwei Lücken, die vor allem anderen behoben werden:

| Nr. | Befund | Schwere |
|---|---|---|
| Ü1 | Die Anwender-Oberfläche aus ZIEL.md 4a/4b (lokale Browser-Oberfläche, geführter Ablauf in 6 Schritten, Seite „Offene Punkte“, Seite „Was die Software gelernt hat“, Lernschleife per Markieren im Plan) fehlt. Bedient wird weiterhin über Konsolenmenü und Excel. Das ist im Bericht nicht als Abweichung genannt. Ursache liegt auch bei der Überwachung: Die Meilenstein-Tabelle in ZIEL.md hatte keinen eigenen Meilenstein dafür. | kritisch |
| Ü2 | Alle Funktionen sind nur an synthetischen bzw. selbst erzeugten Plänen erprobt. Die Abweichungsliste vergleicht das Programm mit sich selbst. Ob das Lernen an echten EPLAN-PDFs funktioniert, ist das größte offene Risiko des Projekts. | hoch |
| Ü3 | Kernnachweise der Auslegung fehlen bzw. sind ohne Quelle (A3 I_z-Tabelle, A5/A15 Leitungsschutz und Kurzschluss). Ohne sie ist kein Plan fachlich belastbar. | hoch |
| Ü4 | Fortschritt in % ist geschätzt. M9 mit 40 % ist zu hoch, solange die Oberfläche fehlt. | mittel |

## 2. Entscheidungen

| E | Entscheidung |
|---|---|
| Ü-E1 | Neuer Meilenstein **M10 – Anwender-Oberfläche** nach ZIEL.md 4a/4b/4c, in der Exe enthalten. Reihenfolge ab jetzt: Software-Prüfung M9a → **M10** → Ü3-Nachweise → M8b → M5g → M7d → M9b → M4e. M10 darf in Teilpakete zerlegt werden (z. B. M10a Grundgerüst + Projekt anlegen, M10b Laden + Prüfen, M10c Offene Punkte, M10d Plan erzeugen + Prüfbericht + Download, M10e Lernschleife per Markieren, M10f Gelernt-Seite). Das Konsolenmenü bleibt als Rückfallebene. UX/Design- und Einsteiger-Prüfer bewerten jedes Teilpaket. |
| Ü-E2 | Technik für M10: frei wählbar, aber nur lokal (`127.0.0.1`), ohne Internetzugriff, im PyInstaller-Paket lauffähig, mit End-to-End-Test in CI (z. B. Playwright oder HTTP-Test). Entscheidung begründet in `ENTSCHEIDUNGEN.md` eintragen. |
| Ü-E3 | Ü3: Leitungsschutz und Kurzschlussnachweis mit Normquelle umsetzen. Erwartete Grundlagen (aus Fachwissen der Überwachung, **nicht online geprüft** – Abschnitt im Original bzw. aktueller Ausgabe prüfen und mit Nummer zitieren): DIN VDE 0100-430 / IEC 60364-4-43 (Überlastschutz I_B ≤ I_n ≤ I_z und I_2 ≤ 1,45·I_z; Kurzschlussschutz), DIN VDE 0298-4 (Strombelastbarkeit von Leitungen), für Maschinen DIN EN 60204-1 (Leiterquerschnitte/Strombelastbarkeit), für die Schaltgerätekombination DIN EN 61439-1/-2. Wo eine Quelle nicht zugänglich ist: Annahme mit Kennzeichnung, Wert konservativ. |
| Ü-E4 | Frage 0 (Reihenfolge): Verschiebung von M4e hinter M5/M6 bestätigt. Ein früher Test mit echtem Plan (M8-Vorabtest) ist richtig, braucht aber den PC → in `PC_AUFGABEN.md` als **ersten** PC-Schritt nach vorne stellen (Reihenfolge: PC9 Exe startet, PC3 echte Pläne lernen, PC8 Abnahme an einem echten Plan, dann PC5, PC7). Anleitung so knapp, dass ein PC-Tag von ca. 2 h reicht. |
| Ü-E5 | Frage 1: Steuerdateien bleiben in `docs/`. Pfadangabe in ZIEL.md entsprechend anpassen (nur dieser Satz). |
| Ü-E6 | Frage 2: Liste der Elektrofachkraft-Punkte ist richtig adressiert, bleibt beim Nutzer. Bitte zusätzlich `docs/EFK_FREIGABE.xlsx` erzeugen: je Annahme eine Zeile mit Klartext-Frage, vorgeschlagenem Wert, Quelle, Feld „freigegeben (Name, Datum)“ – so kann der Nutzer sie ausgedruckt an die Elektrofachkraft geben. |

## 3. Änderungen am Statusbericht ab jetzt

1. Neuer Abschnitt **„DoD-Abgleich“**: die 6 Punkte aus ZIEL.md Abschnitt 1 mit Status (erfüllt / teilweise / offen) und Nachweis.
2. Fortschritt je Meilenstein nur noch als „x von y Teilpaketen erledigt“, nicht mehr in % geschätzt.
3. In Abschnitt 6 jede Lücke zwischen ZIEL.md und Ist nennen, auch wenn sie nicht bewusst entschieden wurde.
4. Bei jedem Paket angeben, ob es an synthetischen oder echten Daten erprobt ist.

## 4. Positiv (beibehalten)

- Trennung KI-Aufbereitung / regelbasierter Planungskern / Ausgabe ist umgesetzt (M3).
- Sicherheitsfunktionen nur als rote Platzhalter, „NICHT FÜR FERTIGUNG“ bis zum Freigabevermerk, Vermerk nie aus KI-Antwort (M7b).
- Prüfer finden echte Fehler (Proxy-Umleitung des Lastenhefts), Fehler werden mit Tests abgesichert (start.bat).
- CI auf Ubuntu und Windows, ruff/mypy ohne Befund, Exe-Paket per Workflow.
