# Schema Projektmodell (`projektmodell/1`)

Erzeugt aus `slpgen/projektmodell.py` (`python -m slpgen schema`) – nicht von Hand ändern.

Datei: `projektmodell.yaml` (UTF-8). Abschnittsart **P** = Projektangaben aus dem Lastenheft, **H** = Hausvorgabe (fehlt sie, wird sie aus `hausvorgaben.yaml` ergänzt).

Pflichtabschnitte: projekt, einspeisung, feldgeraete.

| Zusatzfeld | Bedeutung |
|---|---|
| `schema` | Schemaversion, immer „projektmodell/1“ |
| `annahmen` | Liste: was die KI angenommen hat (wird im Prüfbericht gezeigt) |
| `offene_fragen` | Liste: was im Lastenheft fehlt oder unklar ist |

## `projekt` (P) – Kopfdaten für Deckblatt und Schriftfeld

| Feld | Typ | Pflicht | Bedeutung | Beispiel |
|---|---|---|---|---|
| `nummer` | text | ja | Projekt-/Auftragsnummer | `P-2026-001` |
| `bezeichnung` | text | ja | Kurzbezeichnung der Anlage | `Steuerschrank Förderband` |
| `kunde` | text | – | Kunde (bleibt lokal, nie ins Repository) | `Musterkunde AG` |
| `anlage` | text | – | Anlagenkennzeichen (Funktionsaspekt IEC 81346), beginnt mit = | `=FB1` |
| `ort` | text | – | Ortskennzeichen (Schrank), beginnt mit + | `+SS1` |
| `ersteller` | text | – | Bearbeiter | `N.N.` |
| `datum` | datum | – | Erstelldatum JJJJ-MM-TT | `2026-10-24` |
| `revision` | text | – | Revisionsstand | `00` |

## `einspeisung` (P) – Netzanschluss des Schranks

| Feld | Typ | Pflicht | Bedeutung | Beispiel |
|---|---|---|---|---|
| `netz` | text | ja | Netzform und Spannung | `3/N/PE AC 400/230 V 50 Hz` |
| `hauptschalter` | artikel:hauptschalter | – | Hauptschalter (Artikel aus Gerätestamm) | `HS-3P-40` |

## `feldgeraete` (P, Liste) – Sensoren, Aktoren und Bausteine im Feld

| Feld | Typ | Pflicht | Bedeutung | Beispiel |
|---|---|---|---|---|
| `bmk` | bmk | ja | Betriebsmittelkennzeichen: Kennbuchstabe(n) + Nummer | `B1` |
| `artikel` | artikel:* | ja | Artikel aus dem Gerätestamm | `IND-M12-PNP` |
| `funktion` | text | ja | Funktionstext für Plan und SPS-Liste | `Endlage Band vorne` |
| `gruppe` | text | – | gemeinsamer 24-V-Abgang (DO-Aktoren: DO-Last) | `Sensorik` |
| `typical` | typical | – | Baustein aus der Bibliothek (mehrere Signale/Leistungsteil) | `pumpe_ec` |
| `laenge_m` | zahl (0.1…1000) | – | Leitungslänge zum Gerät in m (Bausteine mit Leistungsteil) | `15` |

## `motoren` (P, Liste) – Drehstrommotoren mit Direktstart

| Feld | Typ | Pflicht | Bedeutung | Beispiel |
|---|---|---|---|---|
| `bmk` | bmk | ja | Betriebsmittelkennzeichen | `M1` |
| `funktion` | text | – | Funktionstext | `Bandantrieb` |
| `p_kW` | zahl (0.01…500) | ja | Bemessungsleistung in kW (Typenschild) | `0.75` |
| `i_N_A` | zahl (0.01…1000) | ja | Bemessungsstrom in A (Typenschild) | `1.9` |
| `cos_phi` | zahl (0.1…1) | – | Leistungsfaktor (Typenschild), Standard 0,8 | `0.78` |
| `laenge_m` | zahl (0.1…1000) | ja | Leitungslänge Schrank–Motor in m | `12` |

## `versorgung_24V` (H) – 24-V-Versorgung (Hausregeln)

| Feld | Typ | Pflicht | Bedeutung | Beispiel |
|---|---|---|---|---|
| `netzteile` | liste_artikel:netzteil | ja | Netzteil-Kandidaten, das kleinste passende wird gewählt | `[NT-24-05, NT-24-10]` |
| `gleichzeitigkeit` | zahl (0.1…1) | – | Gleichzeitigkeitsfaktor g | `1.0` |
| `reserve` | zahl (0…2) | – | Reserve auf den Bedarf | `0.25` |
| `absicherungsfaktor` | zahl (1…3) | – | I_Sicherung ≥ Faktor · I_Gruppe | `1.25` |
| `verteilung` | text | – | einzelsicherungen oder selektivmodul | `einzelsicherungen` |
| `selektivmodul` | artikel:selektivmodul | – | Selektivmodul bei verteilung = selektivmodul | `SEL-24-4K` |

## `sps` (H) – Steuerung (Hausvorgabe)

| Feld | Typ | Pflicht | Bedeutung | Beispiel |
|---|---|---|---|---|
| `cpu` | artikel:sps_cpu | ja | SPS-CPU | `SPS-CPU` |
| `module_kandidaten` | tabelle | ja | E/A-Karte je Signalart DI/DO/AI/AO | `{DI: SPS-DI16, ...}` |
| `adressschema` | tabelle | ja | Adressformat je Signalart | `{DI: "%I{byte}.{bit}", ...}` |

## `leitungen` (H) – Leitungsauslegung (Hausregeln, Freigabe durch Elektrofachkraft)

| Feld | Typ | Pflicht | Bedeutung | Beispiel |
|---|---|---|---|---|
| `freigegeben` | ja_nein | – | Tabelle von Elektrofachkraft freigegeben | `false` |
| `verlegeart` | text | – | Verlegeart (Dokumentation) | `B2` |
| `i_z_A` | tabelle | – | Strombelastbarkeit I_z in A je Querschnitt mm² | `{1.5: 13.1}` |
| `reduktionsfaktor` | zahl (0.1…1) | – | Reduktionsfaktor Häufung/Umgebung | `0.8` |
| `kappa` | zahl (30…60) | – | Leitfähigkeit in m/(Ω·mm²) | `56` |
| `du_max_prozent` | zahl (0.5…10) | – | zulässiger Spannungsfall in % | `3.0` |

