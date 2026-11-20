# Status Langläufer (wird nach jedem Teilschritt aktualisiert)

| Feld | Inhalt |
|---|---|
| Stand | 20.11.2026, manuell |
| Aktuelles Paket | M2 + M3 erledigt → nächstes: M4a (SPS-Übersicht) |
| Nächster Schritt | oberstes offenes Paket in docs/ARBEITSVORRAT.md (Warteschlange für Autostarts) |
| **Für Sie** | Menüpunkt 1: die PDF mit „_Hausstil“ ansehen und E11 beantworten |
| **Bitte bestätigen** | **E8–E18** – siehe [ENTSCHEIDUNGEN.md](ENTSCHEIDUNGEN.md) („ja“ genügt; E14/E15 bitte mit Elektrofachkraft) |
| Tests | 184/184 grün |

## Paketübersicht
| Paket | Status |
|---|---|
| P1 Steuerdateien | erledigt (ROADMAP, STATUS, ENTSCHEIDUNGEN) |
| P1b Synthetischer Testkorpus | erledigt: `slpgen/korpus.py` – interner Testbefehl `slpgen korpus`, nicht im Menü, für Sie keine Aktion nötig |
| P2 Hausprofil lernen | erledigt: Menüpunkt 6 lernt aus einem Ordner mit PDFs Ihre Zeichenregeln inkl. Änderungen über die Jahre. **Für Sie:** optional mit echten PDFs ausprobieren, nichts freigeben nötig |
| P3a Freigabe per Excel | erledigt: Menüpunkt 7 übernimmt JA/NEIN aus `profil_freigabe.xlsx` |
| P3b Anlagen-Struktur / Layout aus Profil | erledigt: zweite PDF `…_Stromlaufplan_Hausstil.pdf` – eine Anlage je Funktion, Spalten 0–9, Verweise =Anlage/Seite.Spalte |
| P4 Typical-Bibliothek | P4a erledigt: Bausteine mit mehreren Signalen (Zähler DI, Zähler AI 4-Leiter, Stellantrieb mit Koppelrelais/AO/Rückmeldung), Pins werden gegen den Artikel geprüft. P4b erledigt: Pumpe 1~230 V mit Motorschutzschalter, Leitungsprüfung (I_z, Spannungsfall 1~), potentialfreier Start/Stopp über Koppelrelais, Stellsignal, Betriebs-/Störmeldung, Hilfskontakt-Meldung; Netzkette über Motoren und Pumpen. P4c erledigt: 24 V über Selektivmodul wählbar (Kanäle, Sammelmeldung) |
| P5 SPS-Kasten, Übersichten, Aderkennzeichnung | P5a erledigt: Aderfarben je Potential und Kennbuchstaben (Netzteil, SPS-Karte) über die Freigabeliste einstellbar. Offen P5b: SPS-Kartenübersicht im Hausstil verfeinern |
| P6 Listen im Hausformat + Konsistenzprüfungen | offen |
| P7 Geometrie-Auslese, Vergleichsmaß | offen |
| P8 Lokale KI (Ollama/GPU) | offen |
| P9 Abnahmepaket PC-Test | offen |

## Protokoll
| Datum | Sitzung | Ergebnis |
|---|---|---|
| 19.11.2026 | manuell | Konzept Langläufer freigegeben, 3 Autostarts angelegt, Steuerdateien angelegt |
| 19.11.2026 | manuell | E6 und E7 vom Nutzer bestätigt; nächster Schritt P1b im Autostart Fr 22:07 |
| 19.11.2026 | Autostart-**Testlauf** (vorgezogen, manuell ausgelöst) | P1b umgesetzt; 4 Prüfer-Agenten: 1 kritischer Befund (SPS-Adressen überlappten) + 15 weitere → behoben; 23/23 Tests grün. Planmäßige Autostarts Fr 22:07 / Sa 03:12 / Sa 08:17 bleiben aktiv |
| 19.11.2026 | Dauerlauf (manuell) | P2 Hausprofil lernen umgesetzt; 4 Prüfer: 21 Befunde (4 hoch: Trend-Ausreißer, Klemmleisten-Erkennung, Signalader ohne Potential, Freigabe für Einsteiger) → behoben bzw. als E9/E10 entschieden; 34/34 Tests grün |
| 19.11.2026 | Dauerlauf (manuell) | P3a Freigabe per Excel; 2 Prüfer (klein): 9 Befunde, 2 hoch (neuer Lernvorschlag konnte ungesehen verloren gehen; veraltete Liste konnte falschen Wert freigeben) → behoben; 43/43 Tests grün |
| 19.11.2026 | Dauerlauf (manuell) | P3b Hausstil-Ausgabe; 3 Prüfer: 20 Befunde (5 hoch: Verweise 24-V-Verteilung, Potentialkette Motoren, Absturz bei Motornummern, doppelte Kennungen, fehlende Anleitung) → behoben; Kennungen aus Kundenplänen neutralisiert (EIN/NT24/VT24); 52/52 Tests grün |
| 19.11.2026 | Dauerlauf (manuell) | P4a Bausteine; 2 Prüfer: 11 Befunde (5 hoch: Koppelrelais nicht verdrahtet, AO ohne Rückleiter, Kontakt ohne Speisung, BMK mit Punkt, doppelte Kanalschlüssel) → behoben; Drahtbruch-Variante als E14 zur Bestätigung; 63/63 Tests grün |
| 19.11.2026 | Dauerlauf (manuell) | P4b Pumpe mit Leistungsteil; 2 Prüfer: 11 Befunde (1 hoch: Hilfskontakt 13/14 als „Störung“ statt „eingeschaltet“; Netzkette zeigte teils ins Leere) → behoben; E15/E16 zur Bestätigung; 67/67 Tests grün |
| 19.11.2026 | Dauerlauf (manuell) | P4c Selektivmodul; Prüfer (Elektro+Qualität): 6 Befunde (2 hoch: Spaltenüberlauf ab 5 Gruppen, Sammelmeldung nicht als Reihe/Ruhestrom) → behoben; bisheriger Plan zeigt Kanäle weiterhin als Einzelsymbole (läuft aus, E11); 74/74 Tests grün |
| 20.11.2026 | manuell | ZIEL.md übernommen: CLAUDE.md, Roadmap M1–M9, 6 Prüfer-Agenten (.claude/agents), OFFENE_PUNKTE (A1–A16), PC_AUFGABEN, STATUSBERICHT; Autostarts lesen jetzt zuerst ZIEL.md |
| 20.11.2026 | manuell | M1 umgesetzt: eigene Werte in der Freigabeliste geprüft (Klartext), Vorgaben ohne erneutes Angebot, Auslegungsnachweis mit Beschreibung + Wert, Annahmen im Code markiert; 83/83 Tests grün |
| 20.11.2026 | manuell | M1 geprüft (Software, Einsteiger): 0 kritisch/hoch, 3 mittel, 6 gering → alle behoben (Farbliste IEC 60757 + A17, alle Fehler auf einmal, Spalte „Erlaubte Form“, Nachprüfung alter Profile); M1 erledigt; 90/90 Tests grün |
| 20.11.2026 | manuell | M2a Schema Projektmodell v1 + Prüfung (Klartext), Hausvorgaben; Prüfer: 7 hoch (Abstürze bei leeren/verschachtelten Werten, Annahmen unsichtbar) → behoben; Arbeitsvorrat für Autostarts angelegt; 144/144 Tests |
| 20.11.2026 | manuell | M2b KI_AUFBEREITUNG.md, Befehl ki-auftrag, synthetisches Lastenheft → KI-Antwort → PDF (E2E-Test); Fehler Motor-Lastseite (KeyError bei Motor ≠ M1) behoben; 146/146 Tests |
| 20.11.2026 | manuell | M2b geprüft (Elektro, Software, Einsteiger): 6 hoch (Regeln erlaubten angenommene Motordaten/stille Ersatzartikel, fehlende Sicherheitsfragen, Abstürze bei kaputten Lastenheften, Komma-Zahlen, kein Rückweg zur KI) → behoben; Korrekturauftrag für die KI; echte Rohantwort einer unabhängigen KI-Instanz → PDF als Test; 158/158 Tests |
| 20.11.2026 | manuell | M2c Menüpunkte 8/9 (KI-Auftrag in Zwischenablage, KI-Antwort prüfen → Plan oder Korrekturauftrag), Zeilennummern; Prüfer UX+Einsteiger: 1 kritisch (eigener Einfügefehler zerriss das Menü) + 5 hoch → behoben, start.bat jetzt per Test abgesichert; 164/164 Tests |
| 20.11.2026 | manuell | M2d CI (GitHub Actions Ubuntu+Windows, Python 3.12/3.13): ruff ohne Befund (pyproject.toml), Abdeckung 95 % (Kern 95 %, Grenze 90 %); Sammelbericht fortgeschrieben |
| 20.11.2026 | manuell | M3 Planungskern getrennt: Ausgabe nur aus planmodell.json (Schema planmodell/1, Artikelauszug, Kennzeichen), Befehl zeichnen, EPLAN-Adapter-Stub; Prüfer: 1 hoch (Kennzeichen PDF ≠ EPLAN) + 5 mittel → behoben; PDFs aus JSON byte-gleich; 184/184 Tests |
