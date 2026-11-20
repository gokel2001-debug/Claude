# Prüfung M2b – Software-Qualität (pruefer-software), 20.11.2026

| Nr. | Schwere | Befund | Erledigung |
|---|---|---|---|
| 1 | hoch | kaputtes/verschlüsseltes PDF, .xlsx, Binär-Text → „Unerwarteter Programmfehler“; .rtf/.odt als Text | nur .txt/.md/.docx/.pdf; jeder Fall Klartext; pypdf-Warnungen leise; 9 Testfälle |
| 2 | mittel | leeres Lastenheft ergibt Auftrag | Mindesttext für alle Formate |
| 3 | mittel | keine Längengrenze | Zeichenzahl ausgegeben, Warnung > 60 000 Zeichen (A23) |
| 4 | mittel | .docx: Entities, Tabulator, Tabellenzellen | html.unescape, Tab, Zellen mit „ | “; Test |
| 5 | mittel | s_motor_steuer leitet -Q aus Schütznummer ab | Motor über daten["schuetz"] gesucht |
| 6 | mittel | E2E-Test nur mit handgeschriebener Antwort | echte Rohantwort einer unabhängigen KI-Instanz als Testdaten, Test über `pruefen`/`generieren` |
| 7 | gering | Test Motor ≠ M1 tautologisch; Ordner als Eingabe | Zusicherung auf PDF-Text; Ordner-Meldung |
| 8 | gering | ruff in zeichnen.py; Anleitung außerhalb Programmordner | ruff behoben; Ablage der Anleitung → A24 (M9) |
