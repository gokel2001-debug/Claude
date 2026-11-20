# Prüfung M5b – Software, 20.11.2026 (Commit 21f4096)

| Nr. | Schwere | Befund | Erledigung |
|---|---|---|---|
| 1 | hoch | Sonderzweig Vorgaben (A18) verwarf abweichende gelernte Kennbuchstaben still | Sonderzweig nur noch für echte Vorgaben; gelernter Wert läuft über `vorschlag_neu`; Test Vorgabe → Lernwert |
| 2 | hoch | Karten-Regex zählte Spulenanschlüsse A1/A2 als SPS-Adresse | nur volle Adressen (E0.1, EW256, %I0.1), Fenster ohne weiteres Kennzeichen; Negativtests |
| 3 | mittel | vollständiges Kennzeichen (=NT24+S1-T1) nicht erkannt | Präfix =Anlage(+Ort) zugelassen; Tests |
| 4 | mittel | Infrastruktur-/leere Anlagen im Anlagenschema | nur Anlagen mit SPS-Adressen; Test |
| 5 | mittel | nur Gutfall getestet; Ende-zu-Ende fehlte | Negativtests, Ende-zu-Ende lernen → JA → Plan mit -G1 |
| 6 | gering | tautologische Testerwartung | feste Schlüsselliste |
| 7 | gering | keine Form/Prüfung für anlagen_feldgeraete | Form + Prüfung ergänzt |
| 8 | gering | irreführende Sicherheit „Vorgabe“ bei belegtem Wert | durch 1 erledigt |
