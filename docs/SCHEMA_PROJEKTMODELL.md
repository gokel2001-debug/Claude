# Schema Projektmodell (`projektmodell/1`)

Erzeugt aus `slpgen/projektmodell.py` (`python -m slpgen schema`) – nicht von Hand ändern.

## Kurz für Anwender

Das Projektmodell beschreibt, **was** gebaut wird: Projektdaten, Einspeisung, Feldgeräte und Motoren. Es entsteht aus der Excel-Vorlage oder aus der Antwort einer KI (Anleitung `docs/KI_AUFBEREITUNG.md`). Die Software prüft die Datei und meldet jede Lücke im Klartext.

- **P** = Angaben aus dem Lastenheft (muss die KI liefern).
- **H** = Hausvorgabe: fehlt der Abschnitt, ergänzt die Software ihn aus `beispiele/hausvorgaben.yaml` und nennt das im Auslegungsnachweis.
- Zahlen mit Punkt oder Komma, ohne Einheit (`0.75` oder `0,75`). Texte mit `=`, `+`, `:` oder führender Null in Anführungszeichen (`"=FB1"`, `"00"`).
- Artikel und Bausteine nur aus dem Gerätestamm (`beispiele/geraetestamm.yaml`); der KI-Auftrag enthält die Liste.

Kleinstes gültiges Beispiel (Rest aus Hausvorgaben):

```yaml
schema: projektmodell/1
projekt: {nummer: P-2026-001, bezeichnung: Förderband}
einspeisung: {netz: "3/N/PE AC 400/230 V 50 Hz"}
feldgeraete:
  - {bmk: B1, artikel: IND-M12-PNP, funktion: "Endlage vorne", gruppe: Sensorik}
```

Pflichtabschnitte: projekt, einspeisung, feldgeraete.

| Zusatzfeld | Bedeutung |
|---|---|
| `schema` | Schemaversion, immer „projektmodell/1“ |
| `annahmen` | Liste: was die KI angenommen hat (erscheint im Auslegungsnachweis) |
| `offene_fragen` | Liste: was im Lastenheft fehlt oder unklar ist (erscheint im Auslegungsnachweis) |
| `auswahl_ersetzen` | nur Hausregeln (Lernschleife): vom Programm gewählter Artikel → Ersatz, z. B. {SCH-09: SCH-12} |

## Felder

### `projekt` (P) – Kopfdaten für Deckblatt und Schriftfeld

| Feld | Art | Pflicht | Bedeutung | Beispiel |
|---|---|---|---|---|
| `nummer` | Text | ja | Projekt-/Auftragsnummer (wird Dateiname) | `P-2026-001` |
| `bezeichnung` | Text | ja | Kurzbezeichnung der Anlage | `Steuerschrank Förderband` |
| `kunde` | Text | – | Kunde (bleibt lokal, nie ins Repository) | `Musterkunde AG` |
| `anlage` | Text | – | Anlagenkennzeichen (Funktionsaspekt IEC 81346), beginnt mit = | `=FB1` |
| `ort` | Text | – | Ortskennzeichen (Schrank), beginnt mit + | `+SS1` |
| `ersteller` | Text | – | Bearbeiter | `N.N.` |
| `datum` | Datum JJJJ-MM-TT | – | Erstelldatum JJJJ-MM-TT | `2026-10-24` |
| `revision` | Text | – | Revisionsstand | `"00"` |

### `einspeisung` (P) – Netzanschluss des Schranks

| Feld | Art | Pflicht | Bedeutung | Beispiel |
|---|---|---|---|---|
| `netz` | Text | ja | Netzform und Spannung | `3/N/PE AC 400/230 V 50 Hz` |
| `hauptschalter` | Artikel aus Gerätestamm | – | Hauptschalter (Artikel); fehlt er, gilt die Hausvorgabe | `HS-3P-40` |

### `feldgeraete` (P, Liste) – Sensoren, Aktoren und Bausteine im Feld

| Feld | Art | Pflicht | Bedeutung | Beispiel |
|---|---|---|---|---|
| `bmk` | Kennzeichen wie B1 | ja | Betriebsmittelkennzeichen: Kennbuchstabe(n) + Nummer | `B1` |
| `artikel` | Artikel aus Gerätestamm | ja | Artikel aus dem Gerätestamm (Sensor/Aktor) | `IND-M12-PNP` |
| `funktion` | Text | ja | Funktionstext für Plan und SPS-Liste | `Endlage Band vorne` |
| `gruppe` | Text | – | gemeinsamer 24-V-Abgang (DO-Aktoren: DO-Last) | `Sensorik` |
| `typical` | Bausteinname | – | Baustein aus der Bibliothek (mehrere Signale/Leistungsteil) | `pumpe_ec` |
| `laenge_m` | Zahl (Punkt oder Komma, ohne Einheit) (0.1…1000) | – | Leitungslänge zum Gerät in m (Pflicht bei Leistungsteil, sonst für Kabelliste) | `15` |

### `motoren` (P, Liste) – Drehstrommotoren mit Direktstart oder Frequenzumrichter

| Feld | Art | Pflicht | Bedeutung | Beispiel |
|---|---|---|---|---|
| `bmk` | Kennzeichen wie B1 | ja | Betriebsmittelkennzeichen | `M1` |
| `funktion` | Text | – | Funktionstext | `Bandantrieb` |
| `p_kW` | Zahl (Punkt oder Komma, ohne Einheit) (0.01…500) | ja | Bemessungsleistung in kW (Typenschild) | `0.75` |
| `i_N_A` | Zahl (Punkt oder Komma, ohne Einheit) (0.01…1000) | ja | Bemessungsstrom in A (Typenschild) | `1.9` |
| `cos_phi` | Zahl (Punkt oder Komma, ohne Einheit) (0.1…1) | – | Leistungsfaktor (Typenschild), Standard 0,8 | `0.78` |
| `laenge_m` | Zahl (Punkt oder Komma, ohne Einheit) (0.1…1000) | ja | Leitungslänge Schrank–Motor in m | `12` |
| `anlauf` | Auswahl: direkt / fu | – | direkt (Schütz, Standard) oder fu (Frequenzumrichter mit Freigabe, Sollwert 4–20 mA, Störmeldung) | `fu` |

### `versorgung_24V` (H) – 24-V-Versorgung (Hausregeln)

| Feld | Art | Pflicht | Bedeutung | Beispiel |
|---|---|---|---|---|
| `netzteile` | Liste von Artikeln | ja | Netzteil-Kandidaten, das kleinste passende wird gewählt | `[NT-24-05, NT-24-10]` |
| `gleichzeitigkeit` | Zahl (Punkt oder Komma, ohne Einheit) (0.1…1) | – | Gleichzeitigkeitsfaktor g | `1.0` |
| `reserve` | Zahl (Punkt oder Komma, ohne Einheit) (0…2) | – | Reserve auf den Bedarf | `0.25` |
| `absicherungsfaktor` | Zahl (Punkt oder Komma, ohne Einheit) (1…3) | – | I_Sicherung ≥ Faktor · I_Gruppe | `1.25` |
| `verteilung` | Text | – | einzelsicherungen oder selektivmodul | `einzelsicherungen` |
| `selektivmodul` | Artikel aus Gerätestamm | – | Selektivmodul bei verteilung = selektivmodul | `SEL-24-4K` |

### `sps` (H) – Steuerung (Hausvorgabe)

| Feld | Art | Pflicht | Bedeutung | Beispiel |
|---|---|---|---|---|
| `cpu` | Artikel aus Gerätestamm | ja | SPS-CPU | `SPS-CPU` |
| `module_kandidaten` | Tabelle | ja | E/A-Karte je Signalart DI/DO/AI/AO | `{DI: SPS-DI16, ...}` |
| `adressschema` | Tabelle | ja | Adressformat je Signalart, Platzhalter {byte} {bit} {wort} | `{DI: "%I{byte}.{bit}", ...}` |

### `leitungen` (H) – Leitungsauslegung (Hausregeln, Freigabe durch Elektrofachkraft)

| Feld | Art | Pflicht | Bedeutung | Beispiel |
|---|---|---|---|---|
| `freigegeben` | ja / nein | – | Tabelle von Elektrofachkraft freigegeben | `false` |
| `verlegeart` | Text | – | Verlegeart (Dokumentation) | `B2` |
| `i_z_A` | Tabelle | – | Strombelastbarkeit I_z in A je Querschnitt mm² | `{1.5: 13.1}` |
| `reduktionsfaktor` | Zahl (Punkt oder Komma, ohne Einheit) (0.1…1) | – | Reduktionsfaktor Häufung/Umgebung | `0.8` |
| `kappa` | Zahl (Punkt oder Komma, ohne Einheit) (30…60) | – | Leitfähigkeit in m/(Ω·mm²) | `56` |
| `du_max_prozent` | Zahl (Punkt oder Komma, ohne Einheit) (0.5…10) | – | zulässiger Spannungsfall in % | `3.0` |
| `min_querschnitt_mm2` | Zahl (Punkt oder Komma, ohne Einheit) (0.5…240) | – | kleinster Querschnitt für Motor-/Leistungsleitungen in mm² (Hausregel) | `2.5` |

### `sicherheit` (P) – Sicherheitsfunktionen – nur Platzhalter, Auslegung und Freigabe durch Elektrofachkraft

| Feld | Art | Pflicht | Bedeutung | Beispiel |
|---|---|---|---|---|
| `not_halt` | ja / nein | – | Not-Halt gefordert (wird nur als Platzhalter gezeichnet) | `true` |
| `pl` | Text | – | geforderter Performance Level laut Risikobeurteilung (z. B. PL d) | `PL d` |
| `funktionen` | Text | – | weitere Sicherheitsfunktionen in Klartext | `Schutztür Pumpenraum` |
| `stoppkategorie` | Text | – | Stoppkategorie 0/1/2 nach EN 60204-1 laut Risikobeurteilung | `0` |
| `freigabe` | Text | – | Freigabevermerk der Elektrofachkraft (Name, Datum) – erst dann entfällt „nicht für Fertigung“; die Auslegung selbst liegt außerhalb dieses Plans | `M. Muster, 2026-11-21` |
| `ausgenommen` | Text | – | Feldgeräte (BMK, mit Komma), die trotz Sicherheitsbegriff an der Standard-SPS bleiben dürfen – nur mit Freigabevermerk wirksam | `S9` |
