# Entscheidungen (Datum, Frage, Antwort, Status)

Status: **bestätigt** = vom Nutzer entschieden · **vorläufig – bitte bestätigen** = im Autostart begründet getroffen.

| Nr. | Datum | Frage | Entscheidung | Status |
|---|---|---|---|---|
| E1 | 24.10.2026 | Variante A (EPLAN-API) oder B (PDF direkt)? | vorerst nur B, ohne EPLAN; Typicals so schneiden, dass spätere Brücke zu A möglich bleibt | bestätigt |
| E2 | 24.10.2026 | Cogineer? | nein | bestätigt |
| E3 | 24.10.2026 | Zielrechner / Eingabe | Windows-PC, Eingabe per Excel-Vorlage, Start per start.bat | bestätigt |
| E4 | 24.10.2026 | Lernbestand / GPU | vorerst 10 Pläne (mittelfristig 50+), GPU vorhanden | bestätigt |
| E5 | 19.11.2026 | Arbeitsweise | Langläufer, mehrere Prüfer-Agenten, Autostart Fr 22:07 / Sa 03:12 / Sa 08:17, im Autostart keine Fragen | bestätigt |
| E6 | 24.10.2026 | Hausprofil (Schriftfeld, Logo, Farbtabelle) | nur lokal in `hausprofil/` (gitignored), im Repo neutrales Musterprofil | bestätigt (19.11.2026) |
| E7 | 19.11.2026 | Testdaten | nur synthetische Pläne im Repo; echte Pläne ausschließlich lokal | bestätigt (19.11.2026) |
| E8 | 19.11.2026 | Wie prüfen wir ohne Ihre echten Pläne, ob das Programm Änderungen über die Jahre erkennt? | Mit **erfundenen Testplänen**, in denen sich absichtlich etwas ändert: die Feldklemmleiste heißt bis 2024 `-X20`, ab 2025 `-X10`. Das Programm muss diese Änderung selbst finden. Alternative (verworfen): Änderung nur im Schriftfeld – weniger aussagekräftig. **Ihre Antwort:** „ja“ genügt; oder nennen Sie eine typische Änderung aus Ihren Plänen, die stattdessen nachgebildet werden soll | vorläufig – bitte bestätigen |
| E9 | 19.11.2026 | Soll das Profil jetzt schon „Aderfarbe je Potential“ lernen? | Nein, zunächst nur „häufigste Aderkennzeichnung 0,75 mm²“ – ehrlich als „ohne Potentialzuordnung“ bezeichnet. Die Zuordnung je Potential (+24 V, 0 V, Signal, L/N, PE) braucht die Lage der Beschriftung auf der Seite und kommt mit P5. Alternative (verworfen): grobe Zuordnung über Textnähe jetzt – zu fehleranfällig | vorläufig – bitte bestätigen |
| E10 | 19.11.2026 | Wie geben Sie gelernte Werte frei? | Vorerst gar nicht nötig (nur ansehen, kurze Textübersicht). Freigabe kommt mit P3 als Excel-Liste mit Spalte „Freigabe JA/NEIN“ – kein Bearbeiten von Programmdateien. Alternative (verworfen): YAML-Datei von Hand ändern – für Einsteiger fehleranfällig | vorläufig – bitte bestätigen |
