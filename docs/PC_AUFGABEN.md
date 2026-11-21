# PC-Aufgaben (nur am Windows-PC möglich, an einem PC-Tag gesammelt abarbeiten)

Schritt-für-Schritt für Einsteiger. Echte Kundenpläne bleiben auf dem PC.

| Nr. | Aufgabe | Schritte | Ergebnis zurückmelden |
|---|---|---|---|
| PC1 | Programm starten und Selbsttest | ZIP vom Branch laden, entpacken, `schaltplan_generator\start.bat` doppelklicken, Menü 5 | Text „SELBSTTEST OK“ oder Bildschirmfoto der Meldung |
| PC2 | Beispielplan im Hausstil ansehen | Menü 1, PDF mit „_Hausstil“ öffnen | Was weicht vom eigenen Hausstil ab? (Stichpunkte) |
| PC3 | Hausprofil aus 10 echten Plänen lernen | Menü 6, Ordner mit Bestands-PDFs ins Fenster ziehen | Inhalt von `hausprofil\profil_uebersicht.txt` (enthält keine Kundendaten, nur Regeln) |
| PC4 | Freigabeliste ausfüllen | `hausprofil\profil_freigabe.xlsx` JA/NEIN, Menü 7 | Meldung von Menü 7 |
| PC5 | Lokale KI (Ollama) prüfen | Ollama installieren, `ollama pull qwen2.5:7b`, Menü 8 → „Lokale KI? J“ mit `beispiele\lastenheft_beispiel.md`, dann Menü 9 | Meldung von Menü 9 und Dauer der KI-Antwort |
| PC6 | KI-Aufbereitung mit der im Betrieb freigegebenen KI erproben | `python -m slpgen ki-auftrag beispiele\lastenheft_beispiel.md`, Text in den Chat, Antwort speichern, `pruefen` | Meldung von `pruefen` und welche KI (Name) |
| PC7 | Eigenen Artikelstamm bereitstellen (Produkt-Befund) | Excel- oder EPLAN-Artikelexport der häufigsten Artikel (Netzteile, Sicherungen, Klemmen, SPS-Karten) in `hausprofil\` ablegen | Spaltenköpfe der Datei (keine Inhalte) |
| PC8 | Abnahme-Vergleich an echten Plänen (M8a) | Für 1–3 echte Projekte: Projekt nachbauen (Menü 3 oder 9), dann Menü V: Referenz-PDF + `…_Planmodell.json` → Abweichungsliste, Spalte „Bewertung“ ausfüllen | nur Blatt „Zusammenfassung“ (Zahlen, keine Kennzeichen) |
