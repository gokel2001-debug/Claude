# Roadmap Langläufer „Stromlaufplan-Generator“ – Mehr-Agenten-Entwicklung (Steuerdatei)

## Context
Der Nutzer möchte das Projekt als **Langläufer** führen: freitags und samstags ungenutzte Token einsetzen,
die Steuerung erfolgt **vom Handy** (kurze Rückmeldungen), eine echte Erprobung am PC (Windows, GPU) erst
in einigen Wochen mit einem **ersten sehr guten Ergebnis**. Gearbeitet werden soll mit **mehreren
spezialisierten Agenten**, die das Ergebnis aus verschiedenen Perspektiven prüfen.
Stand heute (Branch `claude/ai-schaltplan-generator-u6lzbz`): lauffähiger Prototyp (Excel → PDF,
start.bat, Strukturauslese), Lernen bisher nur Textauslese ohne Rückfluss in den Generator.

## Zielbild „erstes sehr gutes Ergebnis“ (Abnahme am PC)
Aus einer Excel-Eingabe entsteht ein Plan **im Hausstil** (Spalten 0–9, eine Anlage je Funktion,
Seiten/Querverweise `=Anlage/Seite.Spalte`, SPS-Kasten, Aderkennzeichnung, Stückliste/Klemmenplan/
Kabelübersicht im Hausformat). Prüfstein: Nachbau eines Referenzplans aus dem Bestand (nur lokal beim Nutzer)
mit messbarer Abweichung (`slpgen vergleichen`), Hausprofil aus 10 Bestandsplänen gelernt, lokale KI (GPU)
für Datenblatt und Freitext angebunden.

## Arbeitsweise je Sitzung (Fr/Sa)
| Schritt | Wer | Inhalt |
|---|---|---|
| 1 Planung | Orchestrator (Hauptsitzung) | nächstes Arbeitspaket aus Roadmap + offene Entscheidungen lesen (`docs/STATUS.md`, `docs/ENTSCHEIDUNGEN.md`) |
| 2 Umsetzung | Orchestrator / Entwickler-Agent | Code + Tests, kleine Commits |
| 3 Prüfung parallel | 4 Prüfer-Agenten (je eine Perspektive) | siehe Tabelle unten, Befunde mit Datei/Zeile |
| 4 Nacharbeit | Orchestrator | Befunde beheben oder begründet zurückstellen |
| 5 Abschluss | Orchestrator | Tests grün, Commit + Push, `docs/STATUS.md` aktualisieren, Handy-Zusammenfassung mit max. 3 Fragen (Auswahl) |

### Agenten-Perspektiven
| Agent | Prüft | Grundlage |
|---|---|---|
| Elektrokonstruktion/Norm | fachliche Richtigkeit: Absicherung, Querschnitte, BMK nach IEC 81346, Darstellung nach IEC 61082, Hausstandard | Konzept Kap. 8, Hausprofil |
| Software-Qualität | Fehler, Tests, Wartbarkeit, keine Regression | `pytest`, Code-Review |
| Anwender/Einsteiger | Bedienbarkeit Excel/start.bat, verständliche Meldungen, Anleitung | `ANLEITUNG_EINSTEIGER.md` |
| Vertraulichkeit | keine Kunden-/Firmendaten im Repo, Commits, Testdaten | `.gitignore`, Diff-Suche |
Token-Ökonomie: Prüfer mit begrenztem Auftrag (nur Diff der Sitzung), keine Agenten für Kleinigkeiten,
ein Arbeitspaket je Sitzung.

## Roadmap (ca. 8–10 Sitzungen)
| Paket | Inhalt | Ergebnis |
|---|---|---|
| P1 | Steuerungsdateien `docs/STATUS.md`, `docs/ENTSCHEIDUNGEN.md`, `docs/ROADMAP.md`; synthetischer Testkorpus „Hausstil“ (generierte PDFs ohne Kundendaten) | Grundlage für alle weiteren Tests |
| P2 | Hausprofil lernen (`slpgen lernen`): Werte + Häufigkeit + Jahrestrend + Belegstellen, Status vorgeschlagen/freigegeben; lokal in `hausprofil/` | „Lernen“ wird messbar |
| P3 | Planmodell auf Anlagen umbauen (Anlage je Funktion, Seitenzählung je Anlage, Querverweise `=A/S.Sp`), Layout aus Profil (Spalten 0–9, Schriftfeld-Felder) | Hausstil-Grundgerüst |
| P4 | Typical-Bibliothek: Einspeisung 230/400 V, 24 V Erzeugung + Selektivmodul, Zähler DI (Impuls + Drahtbruch), Zähler/Messstelle AI, Pumpe (MSS, AO, DO über Koppelrelais, DI) | Bausteine wie im Bestand |
| P5 | SPS-Kasten Hausstil, SPS-Kartenübersichten DI/DO/AI/AO, Adressen E/A/EW/AW; Aderkennzeichnung an jeder Verbindung | Hausstil-Details |
| P6 | Listen im Hausformat (Artikel-/Summenstückliste, Klemmenplan je Leiste, Kabelübersicht) + Konsistenzprüfungen (Kabelrichtung, BMK mit mehreren Artikeln) | Fertigungsunterlagen |
| P7 | Geometrie-Auslese (Linien/Positionen) zur Typical-Erkennung; Vergleichsmaß Original ↔ Nachbau | bessere Lernbasis |
| P8 | Lokale KI (Ollama/GPU): Datenblatt → Geräteeintrag, Freitext → Excel; `start.bat`-Menü „KI-Prüfung“ | KI-Funktionen bereit für PC-Test |
| P9 | Abnahmepaket: Anleitung für den PC-Test (Hausprofil lernen, Referenzplan nachbauen (lokal), KI testen), Checkliste | Termin am PC |

## Steuerung vom Handy
- Jede Sitzung endet mit kurzer Zusammenfassung: erledigt / nächstes Paket / max. 3 Fragen mit Antwortoptionen.
- Entscheidungen werden in `docs/ENTSCHEIDUNGEN.md` festgehalten (Datum, Frage, Antwort) – so geht nichts verloren.
- Ohne Antwort arbeitet die nächste Sitzung mit der empfohlenen Option weiter und vermerkt das.
- Da eine Autostart-Sitzung jederzeit am Guthabenende abbrechen kann: kleine, abgeschlossene Commits;
  `docs/STATUS.md` nach jedem Teilschritt aktualisieren, damit die nächste Sitzung nahtlos weitermacht.

## Sofort nach Freigabe
1. Drei geplante Aufgaben anlegen (siehe oben).
2. Paket P1 beginnen: `docs/ROADMAP.md`, `docs/STATUS.md`, `docs/ENTSCHEIDUNGEN.md` anlegen und pushen.

## Automatischer Start (Vorgabe Nutzer)
Nutzungsfenster: Fr ab 22:00; nach 5 h setzt das Sitzungslimit zurück; wöchentlicher Reset Sa 10:00.
Drei geplante Aufgaben in **diese Sitzung** (Zeitzone Europe/Berlin, wöchentlich):
| Start | Zweck |
|---|---|
| Fr 22:07 | erstes Fenster |
| Sa 03:12 | nach 5-h-Reset |
| Sa 08:17 | nach weiterem Reset, endet spätestens vor 10:00 |
Jeweils arbeiten, bis das Guthaben leer ist; keine Arbeit nach Sa 10:00 beginnen.
Startzeiten leicht nach der vollen Stunde, damit der Reset sicher erfolgt ist.

## Rückfragen (Vorgabe Nutzer)
- **Autostart: keine Fragen.** Fachentscheidungen mit der fachlich begründeten Empfehlung treffen und in
  `docs/ENTSCHEIDUNGEN.md` als „vorläufig – bitte bestätigen“ eintragen (Begründung, Alternativen).
- **Manueller Start (Handy):** wenige Fragen, viel vorbereiten und selbst erledigen; offene vorläufige
  Entscheidungen gesammelt zur Bestätigung vorlegen.

## Grenzen / Vertraulichkeit
- Kunden-PDFs stehen nur in dieser Sitzung als Upload zur Verfügung; sie kommen nie ins Repo. Tests laufen
  mit synthetischen Plänen; Erprobung an echten Plänen erst am PC (lokal).
- Keine Aussage „fertig/normgerecht“ ohne Prüfung durch Elektrofachkraft.

## Verifikation je Paket
`pytest` grün, Beispiel-PDF visuell geprüft, Prüfer-Agenten ohne offene kritische Befunde,
Vertraulichkeits-Suche im Diff leer, Push auf den Branch.

## Geplante Aufgaben (angelegt 19.11.2026)
| Name | Zeit (Europe/Berlin) | Trigger-ID |
|---|---|---|
| slpgen Autostart Fr 22:07 | Fr 22:07 | trig_01R7hSELmtdssQj4y4WkAawB |
| slpgen Autostart Sa 03:12 | Sa 03:12 | trig_01EBt52jGhCvSvo4H8cjzjti |
| slpgen Autostart Sa 08:17 | Sa 08:17 | trig_011QdQnNXH7J2SEgT93ogyze |
