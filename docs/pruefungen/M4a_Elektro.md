# Prüfung M4a – Elektro/Norm (pruefer-elektro-norm), 20.11.2026

Gegenstand: SPS-Übersicht (Kartenseiten, Steckplatzübersicht), Commit c8995e0. Stichproben Adresse/Klemme/Verweis stimmen.

| Nr. | Schwere | Befund | Erledigung |
|---|---|---|---|
| 1 | hoch | Kanal über Koppelrelais/Hilfskontakt zeigte Feldgerät und Feldklemme statt des Schrankgeräts | Planmodell: `SpsKanal.anschluss` (z. B. `-M1-K1:A1`, `-M1-Q1:13`); Kartenseite zeigt Gerät/Anschluss und „im Schrank“; Test |
| 2 | hoch | Analog- und Digitaladressen überschneiden sich (%IW0 = %IB0/1); Reserve ohne Adresse | Adressen fortlaufend je Ein-/Ausgabebereich in Steckplatzreihenfolge inkl. Reserve (A30, Planungskern); Bytebereich je Karte; Test auf Überschneidungsfreiheit |
| 3 | mittel | Versorgung der Karten fehlt | Kopfzeile „Versorgung 1L+ / Lastspannung 2L+ / M“ mit Verweis |
| 4 | mittel | Kartenanschlüsse (Frontstecker) fehlen | offen → A32 (Pinbelegung im Gerätestamm nötig) |
| 5 | mittel | Analog: Signalart, Bezugsklemme, Messbereich, Diagnose fehlen | offen → A33 (Daten fehlen im Gerätestamm/Projektmodell) |
| 6 | mittel | Feldgeräte tragen Schrankort (+SS1) | offen → A31 (EF-Entscheidung Ortsaspekt) |
| 7 | gering | Rückverweis auf Spalte 2 | Verweis auf Spalte 0 (Kanal) |
| 8 | gering | Adressbereich in Steckplatzübersicht; Wortdopplung im Funktionstext | Bytebereich auf Kartenseite; Wortdopplung → M4c |
