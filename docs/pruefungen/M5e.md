# Prüfung M5e – Software + Einsteiger, 21.11.2026 (Commit 398ee5a)

| Prüfer | Nr. | Schwere | Befund | Erledigung |
|---|---|---|---|---|
| Software | 1 | hoch | leitungen leer → falscher „Kreis“; „2,5“ im Projekt → Absturz | leitungen wird angelegt; Zahlen tolerant (Komma), ungültig = Klartext; Test |
| Software | 2 | mittel | niedrigere Regel überschreibt höhere Hausvorgabe | strengerer Mindestwert gilt; Test |
| Software | 3 | mittel | Fall speichert ganze I_z-Tabelle, prüft nicht die Kabel | Fall nur `min_querschnitt_mm2`; Probelauf ermittelt Kabel alt → neu, ohne Wirkung abgelehnt |
| Software | 4 | gering | Korrektur ohne Wirkung gespeichert | abgelehnt („haben schon mindestens …“) |
| Software | 5 | gering | Meldung bei zu großem Mindestquerschnitt irreführend | nennt fehlenden Tabellenwert und vorhandene Querschnitte |
| Software | 6 | gering | dann als Text, Punkt statt Komma, Handänderung „2,5“ | Prüfung beim Laden, Anzeige mit Komma |
| Einsteiger | 1 | hoch | Meldungen in Programmsprache, Sackgasse bei Widerspruch | Klartext „Bitte eine Zahl in mm² (0,5 bis 240)“; Menüpunkt L Hausregeln ansehen/abschalten |
| Einsteiger | 2 | mittel | Artikel-/Gruppennamen unbekannt, Tippfehler bei Gruppe still angenommen | Artikelliste vor der Eingabe; Groß-/Kleinschreibung egal; Hinweis „NEUE 24-V-Gruppe“ in der Vorschau |
| Einsteiger | 3 | mittel | Vorschau ohne Wirkung im Plan | Leitungen alt → neu; Text ohne interne Schlüssel |
| Einsteiger | 4 | mittel | Meldung bei großem Wert unverständlich | wie Software 5 |
| Einsteiger | 5 | mittel | leerer Grund wird zu „=“ | `if defined KG` |
| Einsteiger | 6 | gering | stilles Zurückspringen, Frage für alle Arten gleich | Meldungen „Ungültige Wahl“/„Nicht gespeichert“; Frage je Art |
