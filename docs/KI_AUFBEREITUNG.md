# KI-Aufbereitung: Lastenheft → `projektmodell.yaml`

Diese Anleitung ist für eine **beliebige KI** (Chat). Der Befehl `python -m slpgen ki-auftrag <lastenheft>`
(Menüpunkt „KI-Auftrag erstellen“) setzt daraus **einen** Text zusammen:
diese Anleitung + Schema + Artikelliste aus dem Gerätestamm + Lastenheft.
Den Text in den KI-Chat einfügen, die Antwort als `projektmodell.yaml` speichern und mit
`python -m slpgen pruefen projektmodell.yaml` (Menüpunkt „KI-Antwort prüfen“) prüfen.

Vertraulichkeit: Ein Lastenheft mit Kundendaten nur in eine KI geben, die der Betrieb dafür freigegeben hat.
Ohne Freigabe den Kundennamen vorher entfernen (Feld `kunde` darf leer bleiben).

---

## AUFTRAG AN DIE KI

Du bist Elektroplaner im Schaltschrankbau. Lies das Lastenheft am Ende und erstelle daraus ein
**Projektmodell im YAML-Format** nach dem Schema `projektmodell/1` (Tabellen unten).

### Ausgabe
- Antworte **nur** mit einem YAML-Block (```yaml … ```), ohne weiteren Text.
- Erste Zeile: `schema: projektmodell/1`.
- Gib **nur** die Abschnitte `projekt`, `einspeisung` (nur `netz`), `feldgeraete`, `motoren`,
  `annahmen`, `offene_fragen` aus. SPS, Netzteile und Leitungstabellen sind Hausvorgaben und werden
  von der Software ergänzt – **nicht erfinden**.
- Zahlen mit Punkt schreiben (`0.75`), Texte mit Sonderzeichen in Anführungszeichen (`"=FB1"`).

### Regeln
1. **Nur Artikel aus der Artikelliste** verwenden (Spalte „Artikel“). Passt keiner genau, den
   ähnlichsten nehmen und in `offene_fragen` begründen. Keine Artikel erfinden.
   Bei einem **Ersatzartikel mit 230-V-/400-V-Anschluss** (z. B. Pumpe) bestimmen dessen Bemessungsdaten
   die Absicherung: dann **immer** in `annahmen` („Bemessungsdaten von PUMPE-EC-230 übernommen“) **und**
   in `offene_fragen` („Datenblatt Pumpe anfordern: U, I_N, Anschluss“).
2. Geräte mit mehreren Signalen oder eigenem 230-V-Anschluss als **Baustein**: Feld `typical` mit dem
   Bausteinnamen aus der Bausteinliste. Bausteine mit Leistungsteil brauchen `laenge_m`.
3. Drehstrommotoren mit Direktstart gehören in `motoren` (nicht in `feldgeraete`); Werte vom Typenschild.
   **Motordaten (Leistung, Bemessungsstrom, cos φ) nie annehmen** – fehlen sie, den Motor trotzdem
   eintragen, das Feld leer lassen und in `offene_fragen` nachfragen. (Die Software meldet die Lücke.)
4. **Betriebsmittelkennzeichen** (`bmk`): Kennbuchstabe(n) + laufende Nummer, eindeutig, ohne Bindestrich.
   **Hausregel** wie im Beispielprojekt (nicht aus IEC 81346-2 abgeleitet): B = Sensor/Zähler,
   Y = Ventil/Stellantrieb, P = Meldeleuchte, M = Motor/Pumpe. <!-- ANNAHME A21 -->
5. `gruppe`: Sensoren `Sensorik`, Aktoren mit DO-Signal `DO-Last`, Bausteine weglassen.
6. `funktion`: kurzer Funktionstext aus dem Lastenheft (wird im Plan und in der SPS-Liste gezeigt).
7. **Annahmen nur vorsichtig und immer sichtbar:** Jede Festlegung, die nicht wörtlich im Lastenheft steht
   (Ersatzartikel, Signalart aktiv/passiv, Kontaktart, Versorgung des Feldgeräts), als Satz in `annahmen`.
   Eine fehlende **Leitungslänge** mit dem ungünstigsten Wert annehmen (größte Länge der Anlage + 20 %)
   und zusätzlich in `offene_fragen` nachfragen. Unklare Punkte ohne sinnvolle Annahme nur in `offene_fragen`.
8. **Sicherheit nicht auslegen, immer nachfragen** – auch wenn das Lastenheft dazu schweigt, stets in
   `offene_fragen`: Not-Halt/Risikobeurteilung (PL/SIL), Reparatur-/Trennschalter vor Ort je Motor und Pumpe,
   Ruhestellung der Ventile bei Energieausfall, anlagenspezifische Sicherheitseinrichtungen
   (z. B. Wassermangel, Druck, Temperatur). Diese Punkte gibt nur eine Elektrofachkraft frei.

### Beispiel (Ausschnitt)
```yaml
schema: projektmodell/1
projekt: {nummer: P-2026-001, bezeichnung: Steuerschrank Förderband Linie 1, anlage: "=FB1", ort: "+SS1", revision: "00"}
einspeisung: {netz: "3/N/PE AC 400/230 V 50 Hz"}
feldgeraete:
  - {bmk: B1, artikel: IND-M12-PNP, funktion: "Endlage Band vorne", gruppe: Sensorik}
  - {bmk: Y1, artikel: MV-24-4W, funktion: "Stopper Einlauf", gruppe: DO-Last}
motoren:
  - {bmk: M1, funktion: "Bandantrieb", p_kW: 0.75, i_N_A: 1.9, cos_phi: 0.78, laenge_m: 12}
annahmen: ["Endlagensensor als induktiver Näherungsschalter PNP angenommen (Bauart nicht angegeben)"]
offene_fragen: ["Not-Halt/Risikobeurteilung: welcher PL ist gefordert?", "Reparaturschalter vor Ort an M1?"]
```
