# Konzept: Geführte Erstellung der Stecker-Bepinnungsliste (EMA) in Excel auf Basis der VG-Datenbank

| Feld | Inhalt |
|---|---|
| Bezug | `VG_Datenbank.1.2.accdb` (ACE12), Beispiel `HAI00002-VG_Typ_C-0-EMA-00` (Fertigungsdokumentation VG 96927-2 Grundtyp C, Rev. 00) |
| Ziel | Excel-Arbeitsmappe (Layout Vorlage FO-IUD-004), die den Nutzer Schritt für Schritt zur fertigen Bepinnungsliste je Stecker führt; Werkzeug-/Verarbeitungsdaten kommen ausschließlich aus der Datenbank |
| Stand | Konzept, 01.10.2026 |

Kennzeichnung der Aussagen:
**[DB]** = direkt aus der Datenbankdatei ausgelesen (mdbtools 1.x, reproduzierbar) ·
**[PDF]** = aus der Beispieldoku abgelesen ·
**[Q n]** = Online-Quelle (Liste am Ende) ·
**[A]** = Annahme / nicht verifiziert, Herleitung jeweils angegeben.

---

## 1 Ist-Analyse

### 1.1 Was das Zieldokument (EMA) braucht [PDF, S. 8–10]

Je Stecker (X1, X2, X3) eine Tabelle mit den Spalten:

| EMA-Spalte | Beispielwert X1:A | Herkunft im Zielkonzept |
|---|---|---|
| Artikelnummer (Kontakt) | VG96912P20 | Regel/Tabelle Kontakt (Lücke, s. 2) |
| Pos. | 17:A | Nutzer (Pos. aus Stückliste EPC) + Polbild (Kontaktbezeichner) |
| Ader Typ | VG95218T020A003 | Nutzer (aus Stromlaufplan EFS) |
| Ader AWG / mm² | – / 0,6 | aus Leitung abgeleitet (Lücke, s. 2) |
| Abisolierlänge [mm] | 5,5 [+0,5/0] | DB `tb_Abisolierlaenge` über Wertesatz |
| Crimpwerkzeug | M22520/2-01 | DB `tb_Crimpwerkzeug` |
| Crimpeinsatz | M22520/2-10 | DB `tb_Crimpeinsatz` |
| Selector-Einstellung | 7 | DB `tb_Crimpeinsatz_Komb.Selector_Text` |
| Bemerkung | (z. B. „Anleitung L-2035-AD“) | Nutzer / Koax-Sonderfall |
| Werkzeug Einbau / Ausbau | M81969/14-10 | DB `tb_EinUndAusbauwerkzeug_Kontakt` |
| Referenzzeichnung | HAI00002-VG_Typ_C-0-EFS-00 | Projektkopf |
| Batch-/Inventarnummer | leer | bleibt Handeintrag in der Fertigung |
| Kopfzeile „Referenz“ | VG 96927-5, Abschnitt 4.5, Tabelle 6 | DB `tb_Norm_Wertesatz.Ursprung` |
| Block „Zusätzliche Komponenten“ | M83519/1-2, Blindstopfen, Schrumpfschlauch | Nutzer + DB `tb_Blindstopfen` |

### 1.2 Was die Datenbank liefert [DB]

| Bereich | Tabellen | Datensätze (ohne Kopfzeile) | Bewertung |
|---|---|---|---|
| Normen | `tb_Norm` | 23 (davon 5 Test, ungültig) | VG 96912, VG 95328, VG 95234 … vorhanden |
| Werkzeug-Wertesätze | `tb_Norm_Wertesatz` → Crimpkonfiguration → Crimpwerkzeug/-einsatz, Abisolierlänge, Ein-/Ausbau | 1 731 (1 622 gültig) | Kern der Anbindung, gut normalisiert |
| Lesbare Sichten | `qry_Wertesatz_Lesbar` (gesamt) + 12 normspezifische `qry_Wertesatz_Lesbar_<Norm>` | – | bereits fertig aufgelöste Klartext-Spalten → direkt als Excel-Quelle nutzbar |
| Parameterabfrage | `qryMassenanfrageWerkzeug` (`p_NormID`, `p_KGID`, `p_LQID`, `p_NurFav`) | – | exakt der Lookup „Norm + Kontaktgröße + Querschnitt → Werkzeug“ |
| Polbilder | `tb_Polbild` / `tb_Steckerpolbild` | 198 / 2 153 | **nur VG 95234** (Serien GCB-B, GCA-B) |
| Leitungen | `tb_Kabel_Leitung` | 18 | nur Text, **keine** Attribute (mm², AWG, Adern, Schirm); Beispiel-Leitungen fehlen |
| Blindstopfen | `tb_Blindstopfen` u. a. | 62 | vorhanden inkl. VG 96912 (EN 4529-003N20 usw.) |
| Koax | `tb_Koax_Abisolierlaenge` | 0 (nur Kopfzeile) | **leer** |
| Excel-Bezug | Modul `_excelAuswahl`, `tb_Feld_Konfiguration.ExcelAusdruck` (27 Felder) | – | Access steuert Excel bereits per Automation (`Excel.Application`) |

### 1.3 Abgleich Beispiel ↔ Datenbank [PDF + DB]

| Stecker / Kontakt | Beispiel (EMA) | Treffer in DB | Ergebnis |
|---|---|---|---|
| X1, VG 96912, P20, 0,6 mm² | 5,5 [+0,5/0] · M22520/2-01 · M22520/2-10 · Sel. 7 | identischer Wertesatz vorhanden | ✔ |
| X1 Einbau/Ausbau | M81969/14-10 | DB: Einbau M81969/8-05, Ausbau M81969/8-06 | ✘ Abweichung |
| X2, VG 96912, S16, AWG 16 (1,3 mm²) | 5,5 · M22520/1-01 · M22520/1-04 · Sel. 6 | identisch | ✔ |
| X2 S16 Einbau/Ausbau | M81969/14-03 | DB: M81969/8-07 / 8-08 | ✘ Abweichung |
| X3, VG 95328, S20C, 0,6 mm² | 4,5 [+0,5/0] · M22520/2-01 · M22520/2-02 · Sel. 7 · M81969/17-03 / 19-06 | identisch | ✔ |
| Koax W/Z/L/M (M39029/76-424, VG95319T1009P16 …) | Mantel/Schirm/Seele, Crimpeinsatz M22520/2-35 | nicht abgebildet | ✘ Lücke |

Einordnung der Ein-/Ausbau-Abweichung: M81969/14-10 ist ein kombiniertes Kunststoff-Ein-/Ausbauwerkzeug für Kontaktgröße 20 [Q1][Q2]; M81969/8-05 ist ein Einbauwerkzeug Größe 20 aus derselben Normfamilie [Q3]. Für M81969/8-06 wurde online keine eindeutige Bezeichnung gefunden **[A: vermutlich das zugehörige Ausbauwerkzeug Gr. 20 – abgeleitet aus der Paarung 8-05/8-06 in der DB]**. Beide Varianten sind also technisch plausibel; das Beispiel nutzt die Haus-Präferenz (kombiniertes Werkzeug), die DB den Normwert. → muss als Auswahl/Präferenz modelliert werden (Kap. 2, L3).

---

## 2 Lückenanalyse (Voraussetzung für „geführt“)

| Nr. | Lücke [DB] | Auswirkung auf Führung | Maßnahme | Prio |
|---|---|---|---|---|
| L1 | Polbilder nur für VG 95234 | Nach Steckerwahl können die Kontaktzeilen (A…Z, Größe, P/S) nicht automatisch erzeugt werden | `tb_Steckerpolbild` für VG 96912, VG 95328 (… je Bedarf) befüllen: Polbild, Klemme, Kontaktgröße, Kontaktseite | hoch |
| L2 | `tb_Kabel_Leitung` ohne Attribute, Beispiel-Leitungen (VG95218T020A003 …) fehlen | mm²/AWG kann nicht aus der Leitungswahl abgeleitet werden → Nutzer müsste Querschnitt manuell setzen (Fehlerquelle) | Leitungsstamm erweitern: `ID_Leiterquerschnitt`, Aderzahl, Schirm (j/n), Koax (j/n) | hoch |
| L3 | Mehrdeutigkeit: je Norm + Kontaktgröße + Querschnitt bis zu 4 Wertesätze (z. B. VG 96912 P20 0,6 mm²: Zange /1-01 oder /2-01 × Einsatz /2-04 oder /2-10); `Favorit` = 0 bei allen 1 731 Sätzen | keine automatische Eindeutigkeit möglich | `Favorit` je Kombination pflegen; zusätzlich Filter `Vorraetig` (1 091 Sätze = 1) | hoch |
| L4 | `Ueberprueft` = 0 bei allen Sätzen | Freigabestatus nicht nachweisbar | Prüfstatus pflegen; Excel zeigt ungeprüfte Werte farbig an | mittel |
| L5 | Kontakt-Artikelnummer (VG96912P20, VG95328S20C, M39029/76-424) nicht in DB (`tb_Kontakt`: 0 Sätze) | Spalte „Artikelnummer“ nicht ableitbar | Tabelle Kontakt-Artikel (Norm, Kontaktgröße, P/S, Art.-Nr.) | mittel |
| L6 | Koax-Daten leer | Koax-Zeilen (2 Zeilen je Kontakt: Seele/Schirm) nicht automatisierbar | `tb_Koax_Abisolierlaenge` + Koax-Wertesätze befüllen; bis dahin manueller Sonderpfad | mittel |
| L7 | Ein-/Ausbau: Norm- vs. Hauswerkzeug (s. 1.3) | falsches Werkzeug in Fertigungsdoku | Alternativ-Werkzeug je Kontaktgröße (Feld `Alternativ` existiert in `tb_Feld_Konfiguration`) bzw. Favorit | mittel |

---

## 3 Lösungsvarianten Anbindung Excel ↔ Access

| Kriterium | A: Power Query (nur lesen) | B: VBA + ADO aus Excel | C: Access exportiert nach Excel (vorhandenes `_excelAuswahl`) |
|---|---|---|---|
| Technik | Daten › Daten abrufen › Aus Microsoft Access-Datenbank [Q4] | `ADODB.Connection`, Provider `Microsoft.ACE.OLEDB.12.0` | Access-Formular + Automation `Excel.Application` [DB] |
| Voraussetzung | ACE-OLEDB-Provider, Bitness passend zu Office [Q4] | dto. | Access auf jedem Nutzer-PC |
| Nutzerführung | über Formeln/Dropdowns in Excel | beliebig (UserForm-Assistent) | in Access-Formular |
| Schreibzugriff DB | nein (gewünscht) | möglich, aber nicht nötig | ja |
| Offline-Fähigkeit | Snapshot in Mappe, nach Aktualisierung offline | Snapshot oder live | nein |
| Wartbarkeit | hoch, kein Code für Datenzugriff | mittel (Code) | mittel; Ausgabe-Layout muss in Access-Code gepflegt werden |
| Rückverfolgbarkeit | ID_Wertesatz + DB-Stand mitführbar | dto. | dto. |

**Empfehlung: Hybrid A + schlanke B-Anteile.**
- Power Query lädt die Stammdaten als **Snapshot** in ausgeblendete Blätter (Button „Datenbank aktualisieren“). Quelle sind die vorhandenen Sichten `qry_Wertesatz_Lesbar_*` bzw. eine neue Gesamtsicht (Kap. 6).
- Die Führung erfolgt mit abhängigen Dropdowns (`FILTER`/`UNIQUE` in Hilfszellen, Datenüberprüfung auf Überlaufbereich `=$X$1#` [Q5][Q6]) – kein Code nötig, funktioniert ab Excel 2021 / Microsoft 365 [Q6].
- VBA nur für drei Komfortfunktionen: „Stecker hinzufügen“ (Zeilen aus Polbild erzeugen), „Prüfen“, „EMA-Blatt erzeugen/PDF“.
- Begründung: Fertigung arbeitet bereits mit der Excel-Vorlage FO-IUD-004 [PDF]; die DB bleibt alleinige Datenquelle und wird nur gelesen (keine Konflikte mit dem Änderungsworkflow `tb_Aenderungen_Pending` [DB]).

---

## 4 Geführter Ablauf (Nutzersicht)

| Schritt | Blatt | Nutzer tut | System tut | Prüfung (Ampel) |
|---|---|---|---|---|
| 0 | Start | „Datenbank aktualisieren“ | lädt Snapshot, schreibt DB-Datei, Änderungsdatum, Zeitstempel in Kopf | DB erreichbar? Snapshot älter als X Tage → gelb |
| 1 | Projekt | Projekt-Nr., Dok-Nr. (…-EMA-00), Titel, Referenzzeichnung (EFS), Bearbeiter | übernimmt in Kopf-/Fußzeile aller Ausgabeblätter | Pflichtfelder gefüllt |
| 2 | Stecker | je Stecker: X-Bezeichner, Pos. (EPC), Norm → Polbild/Typ → Stift/Buchse | Dropdowns kaskadiert (Norm → nur deren Polbilder) | Polbild in DB vorhanden (L1) |
| 3 | Stecker | Button „Kontakte erzeugen“ | legt je Klemme eine Zeile an: `Pos:Klemme`, Kontaktgröße, Kontakt-Art.-Nr. | – |
| 4 | Belegung | je Zeile: Leitung (Dropdown) oder „NC“ | leitet mm²/AWG ab (L2); bei NC Blindstopfen aus `tb_Blindstopfen` passend zu Norm + Kontaktgröße | Leitung bekannt |
| 5 | Belegung | – (nur bei Mehrdeutigkeit: Werkzeugvariante wählen) | Lookup Norm + Kontaktgröße + Querschnitt → Wertesatz; 1 Treffer = automatisch, >1 = Dropdown, Favorit vorbelegt | 0 Treffer → rot; ungeprüft (L4) → gelb |
| 6 | Belegung | Sonderfälle: Koax, Löt-/Crimpverbinder, Bemerkung | Koax: 2 Zeilen (Seele/Schirm) | Koax-Daten vorhanden (L6) |
| 7 | Zusatz | Zusätzliche Komponenten (Lötverbinder, Schrumpfschlauch …) | Auswahl aus Stückliste | – |
| 8 | Ausgabe | „EMA erzeugen“ | ein Blatt je Stecker im Layout des Beispiels, Referenzzeile aus `Ursprung`, Drucklayout A4 quer, optional PDF | alle Zeilen grün |

Weitere Komfortpunkte: Zellen, die aus der DB kommen, sind gesperrt (Blattschutz) – Eingaben nur in hellgelben Feldern; jede Zeile trägt verdeckt `ID_Wertesatz`, damit jeder Wert auf den DB-Datensatz zurückführbar ist; „Kontakt kopieren“ für gleich belegte Zeilen.

---

## 5 Aufbau der Arbeitsmappe

| Blatt | Sichtbar | Inhalt |
|---|---|---|
| `Start` | ja | Anleitung, Buttons, DB-Stand |
| `Projekt` | ja | Kopfdaten |
| `Stecker` | ja | Steckerliste (X, Pos., Norm, Polbild, P/S) |
| `Belegung` | ja | Arbeitstabelle aller Kontakte (strukturierte Tabelle `tblBelegung`) |
| `Zusatz` | ja | Zusätzliche Komponenten je Stecker |
| `EMA_X1 … EMA_Xn` | ja | erzeugte Ausgabeblätter (Layout FO-IUD-004) |
| `_DB_Wertesatz` | nein | Snapshot Gesamtsicht (Kap. 6) |
| `_DB_Polbild` | nein | Snapshot Steckerpolbild |
| `_DB_Leitung` | nein | Snapshot Leitungen inkl. Querschnitt |
| `_DB_Blindstopfen` | nein | Snapshot Blindstopfen |
| `_Listen` | nein | Hilfszellen mit `FILTER`/`UNIQUE` für Dropdowns |

Kernformel Wertesatz-Lookup (Zeile in `tblBelegung`, Excel 365):

```
=FILTER(_DB_Wertesatz[ID_Wertesatz];
        (_DB_Wertesatz[Norm]=[@Norm]) *
        (_DB_Wertesatz[Kontaktgroesse]=[@Kontaktgroesse]) *
        (_DB_Wertesatz[mm2]=[@mm2]) *
        (_DB_Wertesatz[Gueltig]=WAHR);
        "kein Wertesatz")
```
Anzahl Treffer über `ANZAHL(...)` → steuert Ampel und ob ein Auswahl-Dropdown angezeigt wird.

---

## 6 Datenbankseitig erforderliche Anpassungen

| Nr. | Anpassung | Zweck | Bezug Lücke |
|---|---|---|---|
| D1 | Gesamtsicht `qry_Excel_Wertesatz` (Basis: vorhandene `qry_Wertesatz_Lesbar`) (alle Normen, je Spalte ein Feld statt `IIf(...)`-Ausdrücken ohne Alias; zusätzlich `Tol_plus`, `Tol_minus`, `Favorit`, `Vorraetig`, `Ueberprueft`, `Ursprung`) | eine stabile Schnittstelle für Power Query; Spaltennamen ändern sich nicht bei DB-Pflege | – |
| D2 | `tb_Steckerpolbild` für benötigte Normen befüllen | Schritt 3 | L1 |
| D3 | `tb_Kabel_Leitung` um `ID_Leiterquerschnitt`, `Aderzahl`, `Schirm`, `Koax` erweitern | Schritt 4 | L2 |
| D4 | `Favorit` pflegen (Haus-Standard je Norm + Kontaktgröße + Querschnitt) | Schritt 5 eindeutig | L3, L7 |
| D5 | Kontakt-Artikeltabelle | Spalte „Artikelnummer“ | L5 |
| D6 | Koax-Daten | Schritt 6 | L6 |
| D7 | Ablage der .accdb auf Netzlaufwerk, Excel-Verbindung schreibgeschützt | keine Sperrkonflikte, DB bleibt führend | – |

Hinweis zu D1: Die vorhandenen Sichten `qry_Wertesatz_Lesbar_*` liefern formatierte Texte (z. B. „5,5 [+0,5/-0] mm“, gebildet per `CStr(...)`) [DB]. Für Berechnung/Filterung in Excel sind Rohwerte besser; die Formatierung im EMA-Layout („5,5 [+0,5/0]“) erfolgt dann in Excel.

---

## 7 Umsetzungsreihenfolge

| Phase | Inhalt | Ergebnis / Abnahme |
|---|---|---|
| 1 | D1 Gesamtsicht + Power-Query-Snapshot + Blatt `Belegung` mit Wertesatz-Lookup (ohne Polbild) | X1/X2/X3 aus dem Beispiel nachbilden: Crimp-/Abisolierdaten müssen 1:1 mit EMA-00 übereinstimmen (laut 1.3 für alle Nicht-Koax-Kontakte erreichbar) |
| 2 | D3, D4 Leitungsstamm + Favoriten | Leitung wählen → Werkzeug ohne Rückfrage |
| 3 | D2 Polbilder + „Kontakte erzeugen“ | Stecker in < 1 min angelegt **[A: Zielwert, nicht gemessen]** |
| 4 | Ausgabeblätter im Layout FO-IUD-004 + PDF | Layoutvergleich mit EMA-00 |
| 5 | D5, D6 Kontakt-Art.-Nr., Koax | vollständige EMA ohne Handeintrag (außer Batch-Nr.) |

Phase 1 ist bereits mit dem heutigen DB-Stand umsetzbar und liefert den größten Nutzen (Werkzeugdaten fehlerfrei aus der DB).

---

## 8 Offene Punkte / Entscheidungen

| Nr. | Frage | Warum relevant |
|---|---|---|
| O1 | Welche Excel-Version ist im Einsatz (365/2021 oder älter)? | `FILTER`/`UNIQUE` und `#`-Bezüge erst ab Excel 2021/365 [Q6]; sonst Fallback über VBA |
| O2 | Office 32- oder 64-bit? ACE-Provider installiert? | Power Query/ADO benötigen passenden Provider [Q4] |
| O3 | Haus-Ein-/Ausbauwerkzeug (M81969/14-xx) generell bevorzugt? | Abweichung 1.3 / L7 |
| O4 | Soll die Excel-Mappe Daten zurückschreiben (z. B. neue Leitungen)? | aktuell bewusst nein; DB-Pflege bleibt in Access mit `tb_Aenderungen_Pending` |

---

## Quellen

| Nr. | Quelle | Gestützte Aussage |
|---|---|---|
| Q1 | DigiKey, M81969/14-10 „Insertion/Extraction Tool For Circular Contacts, Size 20“ – https://digikey.my/en/products/detail/amphenol-aerospace-operations/M81969-14-10/20001854 | M81969/14-10 = Ein-/Ausbauwerkzeug Gr. 20 |
| Q2 | Farnell/CPC, M81969/14-10 „Insertion Tool, Size 20, Plastic“ – https://cpc.farnell.com/amphenol-socapex/m81969-14-10/insertion-tool-size-20-plastic/dp/CN24942 | Ausführung Kunststoff |
| Q3 | Mouser, Extraction/Removal/Insertion Tools (M81969/8-05 „Installing Tool #20“) – https://www.mouser.in/en/c/tools-supplies/tools/extraction-removal-insertion-tools/?pg=2 | M81969/8-05 = Einbauwerkzeug Gr. 20 |
| Q4 | Microsoft Learn, Power Query Access database connector – https://learn.microsoft.com/en-us/power-query/connectors/access-database | Import aus Access, ACE-OLEDB-Provider und Bitness |
| Q5 | Microsoft Support, FILTER-Funktion – https://support.microsoft.com/en-us/office/filter-function-f4f7cb66-82eb-4767-8f7c-4877ad80c759 | FILTER als dynamische Matrix |
| Q6 | Microsoft Q&A, Filter Function In Data Validation – https://learn.microsoft.com/en-us/answers/questions/4456627/filter-function-in-data-validation-not-working ; Dependent drop down lists – https://learn.microsoft.com/en-us/answers/questions/5169441/dependent-drop-down-lists | Datenüberprüfung über Überlaufbereich `#`; abhängige Dropdowns mit FILTER/UNIQUE ab Excel 2021/365 |

Datenbankaussagen [DB] wurden mit `mdb-tables`, `mdb-schema`, `mdb-export`, `mdb-queries` (mdbtools) aus der übergebenen Datei gewonnen und sind damit jederzeit reproduzierbar.
