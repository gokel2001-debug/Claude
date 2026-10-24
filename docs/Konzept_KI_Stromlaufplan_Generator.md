# Konzept: Lokale KI zur (teil-)automatisierten Erstellung von Stromlaufplänen für den Schaltschrankbau

| Feld | Inhalt |
|---|---|
| Bezug | Bestand: mehrere hundert Stromlaufpläne (PDF) verschiedener Kunden/Jahrgänge; Datenblätter der Feldgeräte; EPLAN Electric P8 im Einsatz |
| Ziel | Programm mit lokaler KI, das aus dem Bestand die Hausstandards und deren Entwicklung erfasst und daraus neue Stromlaufpläne teilautomatisiert erzeugt – Variante A über die EPLAN-API, Variante B direkt als PDF inkl. Stückliste |
| Stand | Konzept + Prototyp Variante B (`schaltplan_generator/`), 24.10.2026 |

Kennzeichnung der Aussagen:
**[P]** = am Prototyp nachgewiesen (Befehl angegeben, reproduzierbar) ·
**[Q n]** = Online-Quelle (Liste am Ende) ·
**[A]** = Annahme / Bewertung, nicht verifiziert, Herleitung jeweils angegeben.

---

## 1 Kernaussage

| Nr. | Aussage | Beleg |
|---|---|---|
| K1 | Ein KI-Modell, das Stromlaufpläne „frei zeichnet“, ist für den Fertigungseinsatz nicht der richtige Ansatz. Die veröffentlichte Forschung zu Schaltplänen behandelt überwiegend das **Erkennen** von Symbolen (YOLO u. ä., oft auf Einlinienplänen) mit dem Hinweis auf fehlende öffentliche Datensätze; einen erprobten Weg zur normgerechten **Erzeugung** kompletter Stromlaufpläne fand ich nicht. | [Q9][Q10][Q11]; Bewertung **[A]**: abgeleitet aus dem Fehlen solcher Arbeiten in der Recherche und daraus, dass ein Stromlaufplan prüfbar korrekt sein muss (Absicherung, Querschnitte, Potentiale). |
| K2 | Tragfähig ist ein **hybrider Aufbau**: KI zum *Lesen und Vorschlagen* (Bestand auswerten, Datenblätter extrahieren, ähnliche Geräte zuordnen, Anfrage strukturieren) – **Regeln + Typicals (Makros)** zum *Erzeugen*. So bleibt jede Zeichnung deterministisch und nachrechenbar. | Gleiches Prinzip nutzt EPLAN Cogineer (Regelwerke auf Makro-Basis) [Q4]; Prototyp [P] |
| K3 | Variante A und B teilen sich ein **neutrales Planmodell** (Betriebsmittel, Klemmen, SPS-Kanäle, Absicherungen). Nur der letzte Schritt (Ausgabe) unterscheidet sich. Damit muss man sich nicht vorab für A oder B entscheiden. | Prototyp schreibt `*_Planmodell.json` [P] |
| K4 | Der wertvollste Lernstoff sind nicht die PDFs, sondern – falls vorhanden – die **EPLAN-Projekte** dazu: Dort liegen Betriebsmittel, Artikel und Verbindungen strukturiert vor (z. B. Stücklistenexport per API `PartsService.ExportPartsList` nach XML/CSV [Q3]). Aus PDFs muss diese Struktur erst rekonstruiert werden. | [Q3]; **[A]**: ob die Projekte noch vorliegen, ist offen (Kap. 9) |

---

## 2 Ist-Analyse / Datenlage

| Datenquelle | Was daraus gelernt werden kann | Aufbereitung | Risiko |
|---|---|---|---|
| Stromlaufplan-PDF, **Vektor** (aus EPLAN exportiert) | Blattformat, Schriftfeld, Seitenaufbau, BMK-Schema, Kennbuchstaben, Klemmen-/Querverweisschema, Datum → Entwicklung über die Jahre | Text-Ebene direkt auslesen (`slpgen analysieren`) [P] | gering |
| Stromlaufplan-PDF, **Scan** | wie oben, aber nur über OCR / Vision-Modell | Docling (lokal, OCR optional) [Q7] oder Vision-LLM [Q8] | hoch: Fehlerrate muss gemessen werden **[A]** |
| EPLAN-Projekte (falls vorhanden) | zusätzlich: Artikel, Verbindungen, Makros, Eigenschaften | Export über EPLAN-API (Stückliste XML/CSV [Q3]) bzw. Berichte | gering |
| Datenblätter Feldgeräte | Spannung, Strom/Leistung, Signalart, Anschlussbelegung | Regex-Kandidaten + lokales LLM → Vorschlag Gerätestamm, Freigabe durch Mensch (`slpgen datenblatt`) [P] | mittel: LLM kann Werte falsch zuordnen → Pflichtprüfung |
| Wiederkehrende Schaltungsteile (z. B. 24-V-Erzeugung 10 A / 20 A) | Typicals: immer gleiche Struktur, nur Parameter variieren | aus Bestand clustern, dann als Typical/Makro fixieren | gering |

Prüfung „Vektor oder Scan“ erfolgt automatisch: `analysieren` listet Pläne ohne Text-Ebene unter `ohne_textebene_ocr_noetig` [P].

---

## 3 Architektur

```
 Eingabe                      Wissensbasis                         Ausgabe
 ───────                      ────────────                         ───────
 Projekt-YAML / Dialog ──┐    Gerätestamm (aus Datenblättern) ─┐
 (Freitext → LLM → YAML) │    Typicals / Makros                │
                         ├──► Regelwerk (Auslegung, BMK, ──────┼──► Planmodell (JSON) ──┬─► B: PDF + Stückliste + Klemmenplan
 Datenblätter (PDF) ─────┘    Klemmen, SPS-Adressen)           │                        └─► A: EPLAN-API (Makros einfügen)
                              Layout-/Zeichenstandard ◄────────┘
                                   ▲
 Bestand (PDF / EPLAN) ──► Bestandsanalyse (Stufe 1 regelbasiert, Stufe 2 KI)
```

| Schicht | Aufgabe | KI nötig? | Prototyp |
|---|---|---|---|
| Eingabe | Projektdaten, Einspeisung, Feldgeräteliste | optional (LLM übersetzt Freitext/Kundenliste in YAML) **[A]** | YAML-Format `beispiele/projekt_beispiel.yaml` [P] |
| Gerätestamm | Artikel mit technischen Daten | ja, für Extraktion aus Datenblättern; Freigabe manuell | `beispiele/geraetestamm.yaml` (Platzhalter-Artikel) [P] |
| Regelwerk | 24-V-Bilanz, Netzteilwahl, Absicherung, SPS-Kanäle, Klemmen, BMK | nein (deterministisch) | `slpgen/regeln.py` [P] |
| Layoutstandard | Blattformat, Schriftfeld, Spalten, Symbole | nein; Parameter aus Bestandsanalyse | `LAYOUT` in `slpgen/zeichnen.py` [P] |
| Bestandsanalyse | Standards und deren Entwicklung erkennen | Stufe 1 nein, Stufe 2 ja | Stufe 1 `slpgen/analyse.py` [P] |
| Ausgabe B | PDF, Stückliste CSV | nein | [P] |
| Ausgabe A | EPLAN-Projekt | nein | offen (Kap. 5) |

---

## 4 Was „Lernen“ konkret heißt

| Lernziel | Methode | KI | Ergebnis im System |
|---|---|---|---|
| Blattformat, Schriftfeld, Seitenreihenfolge | Statistik über PDF-Metadaten/Text (Format, Erzeuger, Seitentitel) | nein | Layout-Parameter |
| Entwicklung der Kennbuchstaben (BMK) über die Jahre | Regex `-<Kennbuchstabe><Nr>` je Plan, Anteil je Jahr → `kennbuchstaben_je_jahr.csv` [P] | nein | aktuelle BMK-Tabelle; Hintergrund: IEC 81346-2:2019 hat die Ausgabe 2009 technisch überarbeitet (u. a. Klassen nach inhärenter Funktion, dreistufiges Klassenschema) [Q5] → in Plänen ab ca. 2019 können andere Kennbuchstaben auftreten **[A]**: welche konkret, muss der Bestand zeigen; die Code-Gegenüberstellung lag mir online nicht vor |
| Typicals (z. B. 24-V-Erzeugung) | Gruppierung gleicher Artikel-/Verbindungsmuster über Projekte; Häufigkeit je Jahr | optional (Clustering) | Makro/Typical mit Parametern (I_N 5/10/20 A) |
| „Ähnliches“ Feldgerät | Vergleich Datenblatt-Merkmale (Signalart, Spannung, Anschluss) bzw. Text-Embeddings | ja | Vorschlag „wie Gerät X anschließen“ |
| Datenblattwerte | lokales LLM mit JSON-Ausgabe (Ollama `POST /api/generate`, `format: "json"`) [Q12] | ja | Gerätestamm-Vorschlag, Status `PRUEFEN` [P] |
| Symbol-/Verbindungserkennung aus Scans | Objekterkennung (YOLO-Klasse, in Literatur ~95 % auf Einlinienplänen) [Q10] | ja | nur nötig bei Scan-Bestand; eigenes Training mit gelabelten Plänen **[A]** |

---

## 5 Gegenüberstellung Variante A / B

| Kriterium | A: über EPLAN-API | B: direkte PDF-Erzeugung |
|---|---|---|
| Ergebnis | bearbeitbares EPLAN-Projekt (Makros, Artikel, Berichte durch EPLAN) | PDF + Stückliste + Klemmenplan, nicht nachträglich in EPLAN editierbar |
| Normgerechte Darstellung | über vorhandene Haus-Makros/Symbolbibliothek gesichert | Symbole/Layout müssen nachgebaut werden (IEC 60617 ist als kostenpflichtige Datenbank verfügbar [Q6]) |
| Lizenz / Kosten | EPLAN-Lizenz; API-Programme setzen Lizenzdatei/-variante vor `Init` [Q1][Q2]. Ob Skripte ohne API-Lizenz laufen, ist in den EPLAN-Hilfeseiten **widersprüchlich** dargestellt [Q1] → beim Händler klären | keine CAD-Lizenz; nur Python-Bibliotheken |
| Technik | C#/.NET; Skripte ohne Zusatz-Assemblies [Q1]; Offline-Programme über `Eplan.EplApi.Starter` [Q2] | Python (reportlab), Prototyp vorhanden [P] |
| Alternative ohne Eigenentwicklung | EPLAN Cogineer: Regelwerke auf Makros, Add-on (Mietmodell) [Q4] | – |
| Änderungen nach Erzeugung | normal in EPLAN | Neu generieren aus Eingabe |
| Weiterverwendung Fertigung (Klemmen, Beschriftung, Stückliste) | EPLAN-Berichte, Stücklistenexport [Q3] | CSV-Stückliste [P]; weitere Exporte selbst bauen |
| Risiko | Abhängigkeit EPLAN-Version/API-Änderungen | Akzeptanz bei Kunden, die EPLAN-Daten erwarten **[A]** |

**Empfehlung [A]** (Herleitung: Betrieb zeichnet heute in EPLAN; Makros und Symbolbibliothek existieren bereits und müssten in B nachgebaut werden):
1. Regelwerk und Planmodell zuerst mit Variante B entwickeln und am Bestand validieren (schnell, ohne Lizenzfrage).
2. Produktiv Variante A: dasselbe Planmodell per EPLAN-API als Makros einsetzen.
3. Vor Eigenentwicklung A ein Angebot/Test für EPLAN Cogineer einholen – es löst den Teil „Regeln → Makros → Schaltplan“ bereits [Q4]; die Eigenleistung beschränkt sich dann auf Bestandsanalyse, Datenblatt-KI und Eingabe.

---

## 6 Lokale KI – Bausteine

| Baustein | Zweck | Lokal? | Beleg |
|---|---|---|---|
| Docling (IBM) | PDF → strukturierter Text/Tabellen (Layout, Tabellen, OCR optional) | ja, MIT-Lizenz, Standard-Hardware | [Q7] |
| Qwen2.5-VL (3B/7B/32B/72B) via Ollama | Vision-LLM für Scans, Tabellen, Diagramme | ja | [Q8]; Hardwarebedarf 7B „≥ 8 GB VRAM“ nur aus Drittquelle → **[A]** |
| Ollama REST-API | einheitlicher lokaler Modellaufruf, JSON-Ausgabe | ja | [Q12] |
| YOLO-Objekterkennung | Symbole in Rasterbildern | ja (eigenes Training) | [Q10][Q11] |
| Regelwerk (Python) | Auslegung, Zeichnen | ja, keine KI | [P] |

Datenschutz: Alle Kundenpläne bleiben im Haus; kein Cloud-Dienst nötig (alle Bausteine oben lokal betreibbar).

---

## 7 Prototyp Variante B (Stand dieses Commits)

Aufruf (im Ordner `schaltplan_generator/`):

| Befehl | Ergebnis |
|---|---|
| `python -m slpgen generieren beispiele/projekt_beispiel.yaml` | `ausgabe/P-2026-001_Stromlaufplan.pdf` (10 Seiten A3), `…_Stueckliste.csv`, `…_Planmodell.json` |
| `python -m slpgen analysieren <ordner-mit-pdfs>` | `analyse/plaene.json`, `zusammenfassung.json`, `kennbuchstaben_je_jahr.csv` |
| `python -m slpgen datenblatt <pdf> [--ollama http://localhost:11434]` | Vorschlag Gerätestamm-Eintrag (Status `PRUEFEN`) |
| `python -m pytest tests` | 6 Tests (Bilanz handgerechnet, Netzteilwechsel 5 → 10 A, DO-Lastzuordnung, Klemmen lückenlos, fehlender Artikel, PDF) |

Seiten des erzeugten Plans: Deckblatt · Inhaltsverzeichnis · Einspeisung/Netzteil · Verteilung 24 V · SPS-Übersicht · Feldgeräte (8 Strompfade je Blatt, Querverweise `/Seite.Spalte`) · Klemmenplan · Stückliste · Auslegungsnachweis 24 V.

Nachrechnung Beispiel [P]:

| Größe | Rechnung | Wert |
|---|---|---|
| Σ I | SPS 0,72 A + Sensoren 0,122 A + 3 × 4,2 W / 24 V + 0,02 A | 1,387 A |
| Bedarf | 1,387 A × g 1,0 × (1 + 0,25) | 1,734 A → kleinstes Netzteil ≥ Bedarf: 5 A |
| Primärstrom | 24 V × 5 A / (0,90 × 230 V) | 0,58 A (Vorsicherung lt. Datenblatt 6 A) |
| Abgänge | I_Sicherung ≥ 1,25 × I_Gruppe | -F2 SPS 0,68 A → 1 A; -F3 Sensorik 0,12 A → 1 A; -F4 DO-Last 0,59 A → 1 A |

Grenzen des Prototyps (bewusst):

| Grenze | Folge |
|---|---|
| Gerätestamm enthält **Platzhalter**-Artikel, keine realen Produkte | vor Nutzung mit echten Datenblattwerten befüllen |
| Symbole nur vereinfacht nach IEC 60617 | Haus-Symbolbibliothek bzw. EPLAN-Makros übernehmen |
| Hausregeln (Reserve 25 %, Faktor 1,25, Kennbuchstaben, Adressschema `%I/%Q/%IW`) sind Annahmen **[A]** | aus Bestand/Hausstandard festlegen |
| Keine Leitungsquerschnitt-/Selektivitätsprüfung, keine Lastkreise 400 V (Motoren) | nächste Ausbaustufe; Auslegungsregeln nach geltender Norm einzupflegen (IEC 60204-1 nennt u. a. Überstromschutz und Dokumentation [Q13]) |
| BMK-Erkennung per Regex erfasst nur das Muster `-<Buchstaben><Nr>` | bei abweichendem Hausschema Regex anpassen |

---

## 8 Relevante Normen (Bezugsrahmen)

| Norm | Inhalt | Stand laut Quelle | Relevanz |
|---|---|---|---|
| IEC 81346-1/-2 | Strukturierung, Referenzkennzeichen (=, +, -), Kennbuchstaben | -2:2019 ersetzt 2009, technische Überarbeitung [Q5] | BMK-Vergabe, Entwicklung im Bestand |
| IEC 61082-1 | Regeln für Dokumente der Elektrotechnik (Diagramme, Verbindungslinien, Lage von Referenzkennzeichen) | 2014, 3. Ausgabe; EN 61082-1:2015 [Q14] | Darstellung, Layout |
| IEC 60617 | Grafische Symbole (Datenbank, ca. 1 900 Symbole) | Datenbank, Abo [Q6] | Symbolbibliothek |
| IEC 60204-1 | Elektrische Ausrüstung von Maschinen, inkl. Dokumentationsanforderungen | 2016 (+AMD1:2021) [Q13] | Inhalt der Dokumentation, Schutz |
| IEC 61439-1 | Niederspannungs-Schaltgerätekombinationen, allgemeine Regeln | 2020, 3. Ausgabe [Q15] | Schaltschrank als Bauart |

Hinweis: Die Normtexte selbst sind kostenpflichtig und wurden nicht eingesehen; die Tabelle stützt sich auf die Inhaltsangaben der Herausgeber/Händler.

---

## 9 Umsetzungsreihenfolge

| Phase | Inhalt | Ergebnis / Abnahme | Voraussetzung |
|---|---|---|---|
| 0 | Stichprobe 20–30 Pläne über alle Jahrgänge bereitstellen; klären, ob EPLAN-Projekte vorhanden | Entscheidung Datenweg (PDF vs. EPLAN-Export) | Zugriff Bestand |
| 1 | `analysieren` über gesamten Bestand; Haus-Layout, BMK-Schema, Kennbuchstaben-Trend auswerten | Bericht „Hausstandard Ist + Entwicklung“ | Phase 0 |
| 2 | Gerätestamm aus Datenblättern (KI-Vorschlag + Freigabe), Start mit Standardgeräten (Netzteile, Schutz, SPS) | freigegebener Stamm | lokales LLM installiert |
| 3 | Typicals definieren (24-V-Erzeugung, Sensor-/Aktor-Anschluss, Motorabgang …) und Regelwerk erweitern | Regelwerk + Tests | Phase 1 |
| 4 | Validierung: 3–5 Bestandsprojekte nachgenerieren, Abweichung zum Original bewerten | Abweichungsliste | Phase 2–3 |
| 5 | Variante A: Planmodell → EPLAN (Eigenentwicklung oder Cogineer) | EPLAN-Projekt aus Eingabe | EPLAN-Lizenzklärung |
| 6 | Eingabe-Assistent (Freitext/Kundenliste → Projekt-YAML per LLM) | Dialog-Eingabe | Phase 3 |

---

## 10 Offene Punkte / Entscheidungen

| Nr. | Frage | Warum relevant |
|---|---|---|
| O1 | Liegen zu den PDFs die EPLAN-Projekte (bzw. Exporte) vor? | bestimmt Aufwand Phase 1 (K4) |
| O2 | Anteil Vektor-PDF vs. Scan? | Scan → OCR/Vision nötig |
| O3 | EPLAN-Version und Lizenzumfang (API, Cogineer)? | Variante A, [Q1] widersprüchlich |
| O4 | Gibt es Haus-Makros/Typicals bereits (z. B. 24-V-Erzeugung)? | direkt als Typicals nutzbar |
| O5 | Haus-Regeln für Reserve, Absicherung, SPS-Adressierung, Kennbuchstaben | ersetzen die Annahmen im Prototyp |
| O6 | Hardware für lokale KI (GPU/VRAM) | Modellgröße (3B … 72B) [Q8] |

---

## Quellen

| Nr. | Quelle | Inhalt |
|---|---|---|
| Q1 | EPLAN Platform API, „Scripts“: https://www.eplan.help/en-US/Infoportal/content/api/2024/Scripts.html (weitere Fassungen 2022/2027) | Skripte C#/VB, keine Zusatz-Assemblies; Lizenzaussage je Fassung widersprüchlich |
| Q2 | EPLAN Platform API, Namespace `Eplan.EplApi.Starter`: https://www.eplan.help/en-US/Infoportal/content/api/2026/Eplan.EplApi.Starteru~Eplan.EplApi.Starter_namespace.html | Offline-Programme, Lizenzpfad vor `Init` |
| Q3 | EPLAN Platform API, `PartsService.ExportPartsList`: https://www.eplan.help/en-US/Infoportal/content/api/2027/Eplan.EplApi.HEServicesu~Eplan.EplApi.HEServices.PartsService~ExportPartsList(String,String,Format).html | Stückliste nach XML/CSV |
| Q4 | EPLAN: „Schematics now at the push of a button“: https://www.eplan-software.com/company/news/schematics-now-at-the-push-of-a-button ; „Now available: EPLAN Cogineer“: https://www.eplan-software.com/company/news/now-available-eplan-cogineer-simply-automating-engineering | Cogineer: Regelwerke auf Makros, Add-on (Stand Markteinführung 2017) |
| Q5 | IEC Webstore, IEC 81346-2:2019: https://webstore.iec.ch/publication/29181 | ersetzt 2009, Änderungsliste |
| Q6 | IEC Webstore, IEC 60617 DB: https://webstore.iec.ch/publication/2723 | Symboldatenbank, ca. 1 900 Symbole, Abo |
| Q7 | Docling Technical Report, arXiv 2408.09869: https://hyper.ai/en/papers/2408.09869 | lokal, MIT, Layout/Tabellen/OCR |
| Q8 | Qwen2.5-VL Technical Report, arXiv 2502.13923: https://arxiv.org/pdf/2502.13923 ; Ollama-Bibliothek: https://registry.ollama.ai/library/qwen2.5vl | Dokument-Parsing, Größen 3B–72B |
| Q9 | Review Schaltplan-Erkennung, Adv. Radio Sci. 22, 2024: https://ars.copernicus.org/articles/22/61/2024/ars-22-61-2024.pdf | Überblick Symbolerkennung |
| Q10 | Bhanbhro et al., „Symbol Detection in a Multi-class Dataset“, IJACSA 14(8), 2023: https://ftp.saiconference.com/Downloads/Volume14No8/Paper_6-Symbol_Detection_in_a_Multi_class_Dataset.pdf | YOLOv8 ~95 % auf Einlinienplänen |
| Q11 | Bhanbhro et al., Applied Sciences 13(15) 8816, 2023, DOI 10.3390/app13158816: https://doaj.org/article/d8f4084cb8af4543826da589c01a89ef | keine öffentlichen Datensätze |
| Q12 | Ollama API-Dokumentation: https://github.com/ollama/ollama/blob/main/docs/api.md | `POST /api/generate`, `format: json`, Feld `response` |
| Q13 | IEC Webstore, IEC 60204-1:2016: https://webstore.iec.ch/publication/26036 | Geltungsbereich, überarbeitete Dokumentationsanforderungen |
| Q14 | VDE Verlag, Vorschau IEC 61082-1 Ed. 3.0: https://www.vde-verlag.de/iec-normen/preview-pdf/info_iec61082-1{ed3.0}b.pdf | Inhalt/Änderungen 2014 |
| Q15 | AFNOR, IEC 61439-1:2020: https://www.boutique.afnor.org/en-gb/standard/iec-6143912020/lowvoltage-switchgear-and-controlgear-assemblies-part-1-general-rules/xs136993/250624 | 3. Ausgabe, ersetzt 2011 |
