# Status Langläufer (wird nach jedem Teilschritt aktualisiert)

| Feld | Inhalt |
|---|---|
| Stand | 19.11.2026, Dauerlauf (manuell gestartet) |
| Aktuelles Paket | P3 erledigt → als Nächstes P4 (Typical-Bibliothek nach Bestand) |
| Nächster Schritt | P4: Bausteine wie im Bestand – Zähler DI (Impuls + Drahtbruch), Messstelle AI, Pumpe (Motorschutz, Koppelrelais, Stellsignal), 24 V mit Selektivmodul |
| **Für Sie** | Menüpunkt 1: die PDF mit „_Hausstil“ ansehen und E11 beantworten |
| **Bitte bestätigen** | **E8–E14** – siehe [ENTSCHEIDUNGEN.md](ENTSCHEIDUNGEN.md) („ja“ genügt; E14 bitte mit Elektrofachkraft) |
| Tests | 65/65 grün |

## Paketübersicht
| Paket | Status |
|---|---|
| P1 Steuerdateien | erledigt (ROADMAP, STATUS, ENTSCHEIDUNGEN) |
| P1b Synthetischer Testkorpus | erledigt: `slpgen/korpus.py` – interner Testbefehl `slpgen korpus`, nicht im Menü, für Sie keine Aktion nötig |
| P2 Hausprofil lernen | erledigt: Menüpunkt 6 lernt aus einem Ordner mit PDFs Ihre Zeichenregeln inkl. Änderungen über die Jahre. **Für Sie:** optional mit echten PDFs ausprobieren, nichts freigeben nötig |
| P3a Freigabe per Excel | erledigt: Menüpunkt 7 übernimmt JA/NEIN aus `profil_freigabe.xlsx` |
| P3b Anlagen-Struktur / Layout aus Profil | erledigt: zweite PDF `…_Stromlaufplan_Hausstil.pdf` – eine Anlage je Funktion, Spalten 0–9, Verweise =Anlage/Seite.Spalte |
| P4 Typical-Bibliothek | P4a erledigt: Bausteine mit mehreren Signalen (Zähler DI, Zähler AI 4-Leiter, Stellantrieb mit Koppelrelais/AO/Rückmeldung), Pins werden gegen den Artikel geprüft. P4b erledigt: Pumpe 1~230 V mit Motorschutzschalter, Leitungsprüfung (I_z, Spannungsfall 1~), potentialfreier Start/Stopp über Koppelrelais, Stellsignal, Betriebs-/Störmeldung, Hilfskontakt-Meldung; Netzkette über Motoren und Pumpen. **Offen P4c:** 24 V mit Selektivmodul (Prüfung P4b läuft) |
| P5 SPS-Kasten, Übersichten, Aderkennzeichnung | offen |
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
