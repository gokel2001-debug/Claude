# Prüfung M2a – Einsteiger (pruefer-einsteiger), 20.11.2026

Gegenstand: KI-Antwort mit typischen Fehlern über `pruefen`/`generieren`.
Ergebnis: 2 hoch, 4 mittel, 2 gering – 7 behoben, 1 teilweise (offener Punkt A22).

| Nr. | Schwere | Befund | Erledigung |
|---|---|---|---|
| 1 | hoch | Annahmen/offene Fragen der KI nur bei fehlerfreier Prüfung, nicht im Plan | immer angezeigt; im Auslegungsnachweis des PDF; „vollständig – aber N offene Fragen“ |
| 2 | hoch | „ergänzt“ als 14 technische Schlüssel ohne Werte | je Abschnitt Klartext mit Wert, z. B. „Einspeisung (Hausvorgabe): Hauptschalter = HS-3P-40“ |
| 3 | mittel | Codeblock ```yaml / Einleitungssatz / Tabulator → irreführender Formatfehler | werden entfernt bzw. gezielt gemeldet |
| 4 | mittel | Programmbezeichnungen statt Klartext, „ja“ nicht angenommen, keine Zeilennummer | „Feldgerät M10 (7. Eintrag): Leitungslänge zum Gerät in m („laenge_m“) fehlt“; ja/nein angenommen; **Zeilennummer offen (A22)** |
| 5 | mittel | Pfade relativ zum aktuellen Ordner, englische Systemtexte | Gerätestamm/Hausvorgaben relativ zum Programmordner; deutsche Meldung |
| 6 | mittel | Schema-Doku für Einsteiger unlesbar | Abschnitt „Kurz für Anwender“, Minimalbeispiel, Arten im Klartext |
| 7 | gering | „1 Punkte“, leere Datei | „1 Punkt / N Punkte zu korrigieren“, „Die Datei ist leer“ |
| 8 | gering | „15 m“ abgelehnt | Einheiten m, kW, A, V, W, %, mm² werden angenommen |
