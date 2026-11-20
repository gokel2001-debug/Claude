# Prüfung M1 – Software-Qualität (pruefer-software), 20.11.2026

Gegenstand: Commit 71162c0 (Eingabeprüfung Freigabeliste, Vorgaben ohne Neuangebot, Auslegungsnachweis).
Ergebnis: keine kritischen/hohen Befunde.

| Nr. | Schwere | Befund | Stelle | Erledigung |
|---|---|---|---|---|
| S1 | mittel | Großschreibung auch für freie Merkmale; `haeufigste_ader_0_75`, `sps_adressschreibweise` ungeprüft | `freigabe.py` | behoben: Prüfung je Merkmal, kein `upper()` für freie Texte |
| S2 | mittel | Aderfarbe akzeptiert beliebige Buchstaben (z. B. XYZ) | `freigabe.py` | behoben: Liste IEC 60757 + Hausregel DBU/LBU (A17), GN/YE → GNYE |
| S3 | gering | ältere Profile werden beim Laden nicht nachgeprüft | `hausstil.lade_hausstil` | behoben: Nachprüfung, Warnung im Auslegungsnachweis |
| S4 | gering | Fehlermeldung zeigt Rohwert 1.5 statt 1,5; Wertprüfung vor JA/NEIN-Prüfung | `freigabe.py` | behoben |
| S5 | gering | Sonderzweig Vorgaben ohne Annahme-Markierung | `profil.zusammenfuehren` | behoben: `# ANNAHME A18` |
