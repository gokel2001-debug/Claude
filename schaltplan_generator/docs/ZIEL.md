# ZIEL.md – Auftrag für Claude Code (Langläufer)

Diese Datei liegt im Repo unter `schaltplan_generator/docs/ZIEL.md` und wird in `CLAUDE.md` verlinkt. Sie hat Vorrang vor ROADMAP.md, wenn die beiden sich widersprechen. Bei jedem Start zuerst lesen.

## 0. Selbststart: Was du tust, wenn du diese Datei erhältst

Der Nutzer lädt diese Datei hoch und gibt dir keinen weiteren Auftrag. Du führst die folgenden Schritte selbstständig aus, ohne Rückfrage:

1. Diese Datei unverändert als `schaltplan_generator/docs/ZIEL.md` ablegen. Eine ältere Version wird ersetzt.
2. In `CLAUDE.md` (fehlt sie, anlegen) ganz oben eintragen: „Vor jeder Arbeit `docs/ZIEL.md` lesen. Sie hat Vorrang.“
3. `ROADMAP.md` an die Meilensteine aus Abschnitt 3 anpassen. Erledigtes bleibt als erledigt markiert.
4. Die Autostart-Zeiten aus Abschnitt 4 einrichten bzw. prüfen.
5. Committen und pushen mit der Nachricht „ZIEL.md übernommen“.
6. Mit dem nächsten offenen Meilenstein beginnen, wenn genug Token-Budget vorhanden ist.
7. Nach jedem abgeschlossenen Paket und am Ende jeder Sitzung, auch bei Abbruch wegen des Budgets, einen Statusbericht nach Abschnitt 5 nach `docs/STATUSBERICHT.md` fortschreiben (Sammelbericht, siehe Abschnitt 5) und im Chat ausgeben.

**Kommunikation:** Der Nutzer gibt keine fachlichen Aufträge. Deine Ansprechpartnerin ist die Überwachung (ein Claude-Chat), und der Nutzer trägt die Nachrichten hin und her. Schreib deine Fragen deshalb so in den Statusbericht, dass die Überwachung sie ohne Repo-Zugang beantworten kann. Antworten der Überwachung bekommst du als Datei `UEBERWACHUNG_ANTWORT.md` oder als eingefügten Text. Übernimm sie wie Nutzer-Entscheidungen und vermerke sie in `ENTSCHEIDUNGEN.md`. Nur Fragen zur Elektrofachkraft-Freigabe gehen direkt an den Nutzer.

**Grundregel „Annahme zuerst“:** Offene Fragen halten die Arbeit nie auf. Bei jeder Unklarheit:

1. Die plausibelste Annahme treffen. Bei sicherheitsrelevanten oder normativen Fragen die konservativste Variante wählen.
2. Die Annahme umsetzen, sodass die Software vollständig weiterläuft.
3. Die Annahme in `docs/OFFENE_PUNKTE.md` eintragen (Nr., Annahme, Begründung/Quelle, Alternative, betroffene Dateien, Frage dazu) und im Code mit `# ANNAHME A-Nr.` markieren.
4. Annahmen so kapseln (Konfiguration, Hausprofil, Baustein-Parameter), dass sie später geändert werden können, ohne Code umzubauen.
5. Die Frage bleibt offen, bis sie beantwortet ist, und steht in jedem Statusbericht. Eine Antwort wird dann umgesetzt und der Punkt geschlossen.

Das gilt auch für Punkte, die eine Elektrofachkraft freigeben muss: Annahme treffen, umsetzen, und im Plan und im Auslegungsnachweis sichtbar als „nicht freigegeben“ kennzeichnen.

## 1. Endziel (Definition of Done)

Am Ende steht eine **fertige, auf einem Windows-PC lauffähige Software**, die ohne Programmierkenntnisse bedient werden kann:

1. **Eingabe:** Lastenheft (Freitext/PDF/Word) und optional Feldgeräteliste und Datenblätter.
2. **Ausgabe:** vollständiger Stromlaufplan als PDF im Hausstil, dazu Stückliste, Klemmenplan, Kabelliste und Auslegungsnachweis.
3. **Lernen:** Die Software lernt den Hausstil aus Bestandsplänen (Vektor-PDF, später Scans) und gibt ihn per Freigabeliste frei.
4. **Nachvollziehbarkeit:** Jede technische Auslegung hat eine Quelle (Norm, Datenblatt, Hausprofil) oder ist als **Annahme** gekennzeichnet.
5. **Abnahme:** Ein echter Referenzplan wird aus seinem Lastenheft nachgebaut, und eine Elektrofachkraft bewertet ihn als „fachlich gleichwertig“.
6. **Installation:** ein Installer oder eine portable Version, ein Handbuch für Einsteiger, alle Tests grün.

Das Projekt ist erst fertig, wenn alle sechs Punkte erfüllt sind.

## 2. Architektur (festgelegt)

Drei getrennte Stufen mit festen Schnittstellen dazwischen:

| Stufe | Aufgabe | Technik |
| --- | --- | --- |
| A – Aufbereitung (KI) | Lastenheft, Datenblätter und Freitext → **Projektmodell** | lokale KI (Ollama) **oder** externe KI mit der Anleitung `docs/KI_AUFBEREITUNG.md` |
| B – Planungskern (deterministisch) | Projektmodell → Auslegung, Bausteinauswahl, Betriebsmittelkennzeichen, Prüfungen | Python, regelbasiert, testbar |
| C – Ausgabe | Planmodell → PDF (jetzt) bzw. EPLAN (später) | reportlab; EPLAN-Adapter als Schnittstelle vorbereitet |

**Begründung:** Die KI übernimmt nur das Verstehen und Strukturieren. Gezeichnet und ausgelegt wird regelbasiert, damit die Ergebnisse reproduzierbar, prüfbar und haftungsfähig sind. Eine KI darf nie direkt Planinhalte erzeugen, ohne dass der Planungskern sie geprüft hat.

**Schnittstellen:**

- `projektmodell.yaml`: Anlagen, Funktionen, Feldgeräte, Signale, Einspeisung. Ein Schema wird in `docs/SCHEMA_PROJEKTMODELL.md` versioniert. Die Excel-Vorlage ist nur eine andere Ansicht desselben Modells.
- `planmodell.json`: Seiten, Betriebsmittel, Verbindungen, Potentiale, Klemmen. Es ist neutral und weiß nichts von PDF oder EPLAN.
- Der EPLAN-Adapter liest `planmodell.json`. Bis eine API oder ein Importweg zur Verfügung steht, bleibt er ein Stub mit Tests gegen das Schema. **Annahme:** Ein späterer Import über Makros oder XML ist möglich. Das ist noch nicht geprüft.

**Zweigleisige Aufbereitung:** Ohne lokale KI kann der Nutzer das Lastenheft mit `KI_AUFBEREITUNG.md` in eine beliebige KI geben und die erzeugte `projektmodell.yaml` einlesen. Die Software prüft diese Datei immer gegen das Schema und meldet Lücken im Klartext.

## 3. Meilensteine (Reihenfolge verbindlich)

| M | Inhalt | fertig, wenn |
| --- | --- | --- |
| M1 | Offene Fehler aus P5a beheben | Tests für ungültige Werte und Überschreiben grün |
| M2 | Projektmodell-Schema und `KI_AUFBEREITUNG.md` | ein Beispiel-Lastenheft → gültige YAML (manuell über externe KI) |
| M3 | Planungskern trennen (`planmodell.json`) | PDF entsteht nur noch aus dem Planmodell |
| M4 | P5b, P6: SPS-Übersicht, Listen im Hausformat, Konsistenzprüfungen | Prüfbericht ohne Fehler am Testkorpus |
| M5 | P7: Geometrie und Schriftfeld lernen | Hausprofil aus 10 echten Plänen mit Sicherheitsangabe |
| M6 | P8: Ollama-Anbindung für Stufe A | gleiches Ergebnis wie M2, nur lokal |
| M7 | Bausteinbibliothek erweitern (Motoren 3~, FU, Sicherheitskreise als Platzhalter) | jeder Baustein mit Quelle/Annahme und Test |
| M8 | P9: Abnahme, Nachbau des Referenzplans | Abweichungsliste mit Bewertung |
| M9 | Verteilung: Installer, Handbuch, EPLAN-Stub | DoD Punkt 6 erfüllt |

## 4. Regeln für den Langläufer

- Starts: Fr 22:07, Sa 03:12, Sa 08:17 (Europe/Berlin). Ab Sa 09:45 nichts Neues beginnen, laufende Arbeit sauber committen.
- Vorher Token-Budget prüfen. Wird es knapp, kleinsten sinnvollen Teilschritt abschließen, committen, `STATUS.md` schreiben.
- Im Autostart keine Fragen. Entscheidungen begründet als „vorläufig“ in `ENTSCHEIDUNGEN.md` eintragen.
- Je Paket: Umsetzung → Tests → Commit/Push → Prüfer-Agenten (Elektro/Norm, Software, Einsteiger, Vertraulichkeit) → Nacharbeit.
- Sicherheitsrelevantes (Not-Halt, Schutztüren, PL/SIL) nie selbst festlegen, nur als Platzhalter mit Pflicht zur Freigabe durch eine Elektrofachkraft.
- Vertraulichkeit: Kundendaten nur in `hausprofil/` und lokal, niemals im Repo.

## 4a. Entwicklungsumgebung und Auslieferung (festgelegt)

Der Nutzer startet die Arbeit nur vom Handy (Claude Code in der Cloud). Sein Windows-PC ist dabei meistens aus. Daraus folgt:

| Thema | Regel |
| --- | --- |
| Entwicklung | Alles muss in der Cloud-Umgebung von Claude Code laufen und testbar sein (Linux, ohne GPU, ohne Windows, ohne EPLAN). |
| Windows-Exe | Wird über **GitHub Actions** auf einem Windows-Runner gebaut (z. B. mit PyInstaller) und als Release-Datei zum Herunterladen abgelegt. Lokal muss niemand bauen. |
| Oberfläche | Portable Exe ohne Installation; öffnet eine lokale Browser-Oberfläche (nur `localhost`) mit „Pläne einlernen“, „Lastenheft laden“, „Plan erzeugen“, „Freigabeliste“. Das Konsolenmenü bleibt als Rückfallebene. |
| Lokale KI (Ollama/GPU) | Kann in der Cloud nicht getestet werden. Schnittstelle bauen und mit Attrappen (Mocks) testen. Echte Tests sammeln sich in `docs/PC_AUFGABEN.md`. |
| PC-Termine | Alles, was nur am PC geht (Ollama, echte Kundenpläne, Abnahme), sammelt sich in `docs/PC_AUFGABEN.md` als Schritt-für-Schritt-Anleitung für Einsteiger. Sie wird an einem PC-Tag gesammelt abgearbeitet. |
| Vertraulichkeit | Echte Kundenpläne kommen nie in die Cloud. Hausprofil lernen läuft nur lokal in der Exe. |

**Zeitplan:** Die zeitgesteuerten Starts (Fr/Sa) hat der Nutzer bereits mit Claude Code getestet, sie funktionieren. Fallen sie aus, startet der Nutzer die Sitzung vom Handy mit „weiter“.

## 4b. Zielgruppe: Anwender, nicht Programmierer (verbindlich)

Die Software wird von einem Elektroplaner ohne Programmierkenntnisse benutzt. Jede Entscheidung wird daran gemessen, ob dieser Anwender sie ohne Hilfe bedienen kann.

| Regel | Bedeutung |
| --- | --- |
| Kein Code, keine Konsole | Der Anwender sieht nie YAML, JSON, Python oder Fehler-Tracebacks. Alles, was er bearbeitet, ist eine Oberfläche oder eine Excel-Datei. |
| Geführter Ablauf | Startseite mit Assistent: 1. Projekt anlegen → 2. Lastenheft/Feldgeräteliste/Datenblätter laden → 3. Rückfragen und Annahmen prüfen → 4. Plan erzeugen → 5. Prüfbericht ansehen → 6. PDF und Listen herunterladen. |
| Projektordner | Jedes Projekt ist ein Ordner mit allen Eingaben, Ergebnissen und Versionen. Kopieren = sichern. Ältere Stände lassen sich wiederherstellen. |
| Annahmen sichtbar | Eine Seite „Offene Punkte“ zeigt jede Annahme der Software im Klartext mit Auswahl (übernehmen / ändern / Wert eintragen). Nach einer Änderung wird der Plan auf Knopfdruck neu erzeugt. |
| Fehlermeldungen | Immer auf Deutsch, mit Ursache und Lösung („Feldgerät B12 hat keine Spannungsangabe – bitte in Zeile 14 der Feldgeräteliste ergänzen“). |
| KI-Aufbereitung ohne lokale KI | Ein Knopf „KI-Auftrag kopieren“ legt Anleitung und Lastenheft in die Zwischenablage. Der Anwender fügt das in einen beliebigen KI-Chat ein und lädt die Antwort per Knopf wieder hoch. Die Software prüft sie und zeigt fehlende Angaben an. Mit lokaler KI passiert das automatisch. |
| Einlernen | Ordner mit Bestandsplänen auswählen → Fortschrittsbalken → Ergebnis als Freigabeliste mit Vorschau („so würde ein Plan aussehen“). |
| Hilfe | Ein Fragezeichen auf jeder Seite, ein Beispielprojekt zum Ausprobieren, ein Handbuch als PDF mit Bildschirmfotos. |
| Updates | Neue Version = neue Exe herunterladen. Hausprofil und Projekte bleiben erhalten und werden bei Bedarf automatisch übernommen. |
| Einsteiger-Prüfer | Der Prüfer-Agent „Einsteiger“ testet jedes Paket aus Sicht dieses Anwenders und spielt jeden neuen Ablauf einmal Schritt für Schritt durch. Was er nicht ohne Erklärung versteht, ist ein Fehler. |

Der Meilenstein M9 ist erst erfüllt, wenn ein Anwender mit dem Handbuch allein ein Beispielprojekt vom Lastenheft bis zum PDF durchziehen kann.

## 4c. Qualitätsanspruch: Produkt, nicht Prototyp

Ziel ist eine Software, die ein professionelles Softwarehaus beeindruckt und einem Betrieb messbar Planungszeit spart. Zeit spielt keine Rolle: Lieber länger arbeiten als eine schwächere Lösung abliefern. Nach M9 geht es mit Verbesserungsrunden weiter, bis keine Prüfer-Kritik mehr offen ist.

**Lernschleife (Kernfunktion):**

1. Der Anwender markiert im erzeugten Plan eine Stelle (Seite, Spalte oder Betriebsmittel) und schreibt in Klartext, was falsch ist („Klemme gehört auf -X2“, „Schütz immer links vom Motorschutz“).
2. Die Software (bzw. die KI-Aufbereitung) übersetzt das in eine **Regel** und zeigt sie zur Bestätigung: gilt nur dieses Projekt / immer / für diesen Baustein.
3. Bestätigte Regeln landen im Hausprofil mit Herkunft und Datum. Jede Regel kann man einsehen, abschalten und zurücknehmen.
4. Jede Korrektur wird automatisch zum **Regressionstest**: Derselbe Fehler kann nicht wiederkommen.
5. Eine Seite „Was die Software gelernt hat“ zeigt den Verlauf und die Verbesserung über die Zeit.

**Messbare Qualitätsziele:**

| Bereich | Ziel |
| --- | --- |
| Zeichnung | Ein Referenzplan wird so nachgebaut, dass die Elektrofachkraft ihn ohne inhaltliche Korrektur freigibt. Abweichungen im Layout gegenüber dem Hausstil werden in einer Liste erfasst und gegen null gebracht. |
| Prüfungen | Automatische Konsistenzprüfung vor jeder Ausgabe: Querverweise, doppelte BMK, offene Potentiale, Klemmenbelegung, Absicherung gegen Querschnitt (Quelle je Regel). |
| Zeitersparnis | Eine Kennzahl im Prüfbericht: erzeugte Seiten, Betriebsmittel, Klemmen und geschätzte eingesparte Zeichenstunden (Berechnungsgrundlage offenlegen). |
| Bedienung | Ein Erstanwender schafft das Beispielprojekt ohne Hilfe in unter 30 Minuten. |
| Software | Typisierung und Linter ohne Befund, Testabdeckung des Planungskerns ≥ 90 %, End-to-End-Test vom Lastenheft bis zum PDF bei jedem Commit über GitHub Actions. |
| Robustheit | Keine Eingabe bringt die Software zum Absturz. Fehler werden immer im Klartext gemeldet, Projekte gehen nie verloren. |
| Design | Ruhige, moderne Oberfläche, in Gestaltung und Bedienung auf professionellem Niveau. Der Einsteiger-Prüfer bewertet jede neue Seite. |

Zusätzliche Prüfer-Agenten ab M4: **UX/Design** und **Produkt** („Würde ein Betrieb dafür bezahlen?“). Ihre Kritik kommt als offener Punkt in die Liste.

## 4d. Prüfer-Agenten (Vorgabe zum Anlegen)

Claude Code legt jeden Prüfer als eigenen Subagenten unter `.claude/agents/<name>.md` an (Rolle, Prüfliste, Ausgabeformat wie unten). Ein Prüfer ändert nie selbst Code. Er liefert Befunde, und die Nacharbeit erledigt der Hauptagent.

| Prüfer | Rolle / Blickwinkel | Prüft insbesondere | Maßstab |
| --- | --- | --- | --- |
| Elektro/Norm | erfahrene Elektrofachkraft im Schaltschrankbau | Schaltungslogik, Absicherung/Querschnitt, Potentiale, BMK und Kennbuchstaben, Darstellung nach Norm, Sicherheitsfunktionen nur als gekennzeichnete Platzhalter | Jede Regel mit Normquelle (Nummer + Abschnitt) oder als Annahme gekennzeichnet |
| Software-Qualität | Senior-Entwickler | Architektur (Stufen A/B/C sauber getrennt), Lesbarkeit, Typisierung, Testabdeckung, Fehlerbehandlung, Performance, Sicherheit der Abhängigkeiten | Linter/Typprüfung ohne Befund, Ziele aus 4c |
| Einsteiger | Elektroplaner ohne Programmierkenntnisse | spielt jeden neuen Ablauf Schritt für Schritt durch; Texte, Fehlermeldungen, Handbuch | Alles ohne fremde Hilfe verständlich |
| UX/Design | Produktdesigner | Gestaltung, Konsistenz, Klickwege, Rückmeldungen, Barrierefreiheit | Professionelles Niveau, keine Sackgassen |
| Produkt | Geschäftsführer eines Schaltschrankbauers | Nutzen, Zeitersparnis, Zuverlässigkeit, Lernschleife | „Würde ich dafür bezahlen?“ mit Begründung |
| Vertraulichkeit | Datenschutz/IT-Sicherheit | keine Kundendaten im Repo/Log/Test, `.gitignore`, keine Übertragung echter Pläne in die Cloud | Null Befunde |

**Ausgabeformat jedes Prüfers** (in `docs/pruefungen/<Paket>_<Prüfer>.md`):

| Nr. | Schwere (kritisch/hoch/mittel/gering) | Fundstelle | Befund | Vorschlag | Quelle/Begründung |
| --- | --- | --- | --- | --- | --- |

**Regeln:** Kritische und hohe Befunde werden vor dem nächsten Paket behoben. Mittlere und geringe kommen als offene Punkte in die Liste. Kein Prüfer darf ein Paket ohne Befundliste durchwinken: findet er nichts, nennt er, was er geprüft hat. Die Zusammenfassung aller Prüfungen steht im Statusbericht.

## 5. Statusbericht für die externe Überwachung

Auf den Befehl **„Statusbericht für Überwachung“** gibt Claude Code genau dieses Format aus:

```
STATUSBERICHT – Datum, Branch, letzter Commit
1. Meilenstein aktuell / Fortschritt in %
2. Seit letztem Bericht erledigt (Tabelle: Paket | Ergebnis | Tests)
3. Tests: x/y grün, neue Tests
4. Neue vorläufige Entscheidungen (E-Nr., Kurzbegründung)
5. Offene Fehler / Risiken
6. Abweichungen von ZIEL.md mit Begründung
7. Nächster geplanter Schritt
8. Fragen an den Nutzer (max. 3)
```

Der Nutzer gibt diesen Bericht an einen Überwachungs-Chat weiter. Kommen von dort Korrekturen, werden sie als Nutzer-Entscheidung behandelt.

**Sammelbericht:** Nicht jeder Bericht erreicht die Überwachung. Deshalb gibt es immer genau **einen** offenen Bericht, `docs/STATUSBERICHT.md`, der alles seit der letzten Antwort der Überwachung enthält:

- Neue Sitzungen und Pakete werden **ergänzt**, nie in einer neuen Datei angelegt. Abschnitt 2 wächst als Tabelle mit Datum je Zeile. Die Abschnitte 1, 3, 5, 7 und 8 zeigen immer den aktuellen Gesamtstand.
- Kopf des Berichts: „Berichtszeitraum: seit <Datum der letzten Überwachungsantwort> – Sitzungen: n“.
- Erst wenn eine Antwort der Überwachung kommt (`UEBERWACHUNG_ANTWORT.md` oder eingefügter Text), wird der Bericht nach `docs/berichte/<Datum>_STATUSBERICHT.md` archiviert und ein neuer begonnen. Die Antwort wird mitarchiviert.
- Fragen an die Überwachung bleiben im Bericht stehen, bis sie beantwortet sind. Bis dahin wird mit Annahmen weitergearbeitet.
