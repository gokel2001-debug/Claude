# Prüfung M10a – Oberfläche Grundgerüst (Commit db9aa73)

Prüfer: UX/Design, Einsteiger (Agenten, ändern keinen Code). Nacharbeit im Folgecommit. Erprobt: synthetisch (lokaler Server, Bildschirmfotos hell/dunkel, E2E per HTTP).

| Nr. | Prüfer | Schwere | Befund (kurz) | Nacharbeit | Stand |
|---|---|---|---|---|---|
| U2 | UX | hoch | kein „aktuelles Projekt“, Schritte 2–6 ohne Bezug, nicht erweiterbar | Startseite = Projektliste + Neues Projekt; Projektseite /projekt/<Name> mit Schrittleiste (erledigt/folgt) | behoben |
| U1 / N5 | beide | hoch/mittel | „unten öffnen“ ohne Öffnen-Funktion | Liste mit „Öffnen“, Projektseite mit „Excel öffnen“/„Ordner öffnen“ | behoben |
| N1 | Einsteiger | hoch | nach dem Anlegen kein nächster Schritt, Excel öffnet nicht | Weiterleitung auf Projektseite, Knopf Excel öffnen, Text „Nächster Schritt“ | behoben |
| N2 / N3 | Einsteiger | hoch/mittel | Menü blockiert solange Oberfläche läuft; Enter beendet versehentlich | Oberfläche in eigenem Fenster (`start`), Menü bleibt frei; Beenden nur Fenster schließen oder B + Enter; Hinweis auf jeder Seite/Hilfe | behoben |
| U3 / N6 | beide | mittel | F5 sendet Formular erneut | 303-Weiterleitung nach jedem POST | behoben |
| U4 | UX | mittel | Eingabe nach Fehler weg, Fehler nicht am Feld | Wert bleibt, Fehler am Feld mit aria-invalid/-describedby, role=alert | behoben |
| U5 | UX | mittel | reservierte Windows-Namen, OSError ohne Klartext | abgewiesen bzw. Klartext mit Lösung | behoben |
| U6 / U7 | UX | mittel/gering | Kontrast Eingaberahmen, Fokus/Hover | eigene Farbe für Bedienelemente, :focus-visible, Hover | behoben |
| U9, U10, U12, N7, N8 | beide | gering | Kennzeichnung in h1, „folgt“ fünfmal mit start.bat, ? auf Hilfeseite, „hochladen/herunterladen“, Anleitung O | behoben | behoben |
| U8, U11, N9 | beide | gering | Seitentitel bei Fehler (umgesetzt), Stand je Projekt, Namensregeln Menü 2 ↔ Oberfläche | Stand je Projekt mit M10b–d; Namensregeln angleichen → M10b | teilweise |
