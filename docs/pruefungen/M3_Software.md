# Prüfung M3 (M3a + M3b) – Software-Qualität (pruefer-software), 20.11.2026

Ergebnis: M3-Kriterium formal erfüllt; 1 hoch, 5 mittel, 2 gering – alle behoben.

| Nr. | Schwere | Befund | Erledigung |
|---|---|---|---|
| 1 | hoch | Hausstil-Ausgabe vergab Kennzeichen selbst; PDF (=NT24-T1) ≠ EPLAN (=FB1+SS1-G1) | Kennzeichen werden im Planungsablauf vor dem Speichern festgelegt (`kennzeichne`, Feld `kennzeichen` im Planmodell); Hausstil prüft nur noch auf Übereinstimmung (geändertes Profil → Klartext), EPLAN-Adapter nutzt dieselben; Test PDF = EPLAN; A27 |
| 2 | mittel | Ausgabe importierte `regeln` | gemeinsame Konstanten in `modell.py`; Test: zeichnen/hausstil/eplan_adapter importieren weder regeln noch motor noch projektmodell |
| 3 | mittel | beschädigtes JSON → Programmfehler | `aus_dict` prüft Wurzel, projekt.nummer, seiten (4 Werte, bekannte Art), artikel/bilanz/kennzeichen, jeden Listeneintrag; Sammelmeldung im Klartext; 9 Testfälle |
| 4 | mittel | falsche Typen still übernommen | Typprüfung je Feld gegen die Dataclass |
| 5 | mittel | Identitätstest schwach (str-Normalisierung, nur Text) | Datum als ISO-Text im Modell, `speichere` ohne `default=str`, `geladen == m`, PDFs mit `invariant` **byte-gleich** verglichen |
| 6 | mittel | Schema-Doku unvollständig | `daten`, `artikel`, `bilanz`, `kennzeichen`, Pflicht `projekt.nummer`, Seitenarten; Verbindungen/Potentiale als A28 |
| 7 | gering | Projektnummer als Dateiname | Prüfung in der Ausgabe |
| 8 | gering | `vergleichen` ohne Schemaprüfung; Artikeltest selbstbestätigend | über `Planmodell.lade`; feste erwartete Artikel |
