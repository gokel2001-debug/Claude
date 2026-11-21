# Anleitung für Einsteiger – Stromlaufplan-Generator (Windows)

**Was ist das?** Ein lauffähiger **Prototyp**. Aus einer ausgefüllten Excel-Tabelle (Feldgeräte, Motoren,
Regeln) erzeugt er automatisch einen Stromlaufplan als PDF, dazu Stückliste, Klemmenplan, Kabelliste und
Auslegungsnachweis.
**Was ist es (noch) nicht?** Ein fertiges Produkt. Die Artikel im Gerätestamm sind Platzhalter, das Layout
ist noch nicht Ihr Hausstandard. Jeder erzeugte Plan trägt den Vermerk „nicht freigegeben“ und muss von
einer Elektrofachkraft geprüft werden.

---

## 0 Ohne Python: fertiges Programmpaket (erprobt nur automatisch, PC-Test steht aus)

1. Im GitHub-Repository (im Browser **angemeldet**) oben **„Actions“** → links **„Paket“** → den obersten grünen
   Lauf öffnen, bei dem unter dem Titel der Zweig **`claude/ai-schaltplan-generator-u6lzbz`** steht.
2. Unten bei **Artifacts** auf **„Stromlaufplan-Generator-Windows“** klicken (ZIP wird geladen).
3. ZIP mit der rechten Maustaste → **„Alle extrahieren…“**, z. B. nach `C:\slpgen`.
4. Im entpackten Ordner **`start.bat`** doppelklicken – Schritte 1 und 2 entfallen, das Programm startet sofort
   (keine Einrichtung, kein Internet nötig).

Steht bei „Artifacts“ nichts oder „expired“: Pakete werden nur 14 Tage aufbewahrt – geladene ZIP daher selbst
aufheben; für ein neues Paket den Betreuer bitten, den Lauf neu zu starten („Re-run“).

**Neue Version einspielen, ohne Gelerntes zu verlieren:** Hausprofil (gelernte Werte, Freigaben, Hausregeln,
Artikelzuordnung) liegt im Ordner **`hausprofil`**, Ihre Projekte in **`meine_projekte`**. Neue ZIP in einen
**neuen** Ordner entpacken, dann diese **zwei Ordner** aus dem alten in den neuen Ordner kopieren. Eigene Änderungen
in `beispiele\` (z. B. Gerätestamm) vorher sichern – das neue Paket bringt eigene Beispieldateien mit.

Windows kann beim ersten Start warnen („Der Computer wurde durch Windows geschützt“), weil das Programm nicht
signiert ist: „Weitere Informationen“ → „Trotzdem ausführen“ – nur nach Rücksprache mit der IT.

## 1 Einmalig: Python installieren (ca. 5 Minuten)

1. https://www.python.org/downloads/ öffnen → gelben Knopf **„Download Python 3.x“** klicken.
   (Empfohlen: Python **3.13**; neuere Versionen funktionieren ebenfalls.)
2. Heruntergeladene Datei starten.
3. **Wichtig:** im ersten Fenster unten den Haken **„Add python.exe to PATH“** setzen.
4. **„Install Now“** klicken und warten, bis „Setup was successful“ erscheint.

Auf Firmen-PCs braucht man dafür eventuell die IT (Administratorrechte).

## 2 Einmalig: Programm herunterladen

1. Das GitHub-Repository im Browser öffnen (angemeldet).
2. Links oben im Auswahlfeld (Branch, steht meist auf „main“) den Eintrag
   **`claude/ai-schaltplan-generator-u6lzbz`** wählen.
3. Grüner Knopf **„Code“** → **„Download ZIP“**.
4. ZIP-Datei mit der rechten Maustaste → **„Alle extrahieren…“**, z. B. nach `C:\slpgen`.
5. Im entpackten Ordner in den Unterordner **`schaltplan_generator`** wechseln.

## 3 Starten

**Doppelklick auf `start.bat`.**

- **Programmpaket (Abschnitt 0):** startet sofort.
- **Python-Weg (Abschnitte 1–2):** beim **ersten Start** richtet sich das Programm selbst ein (1–3 Minuten, Internet nötig).
- Meldet Windows „Der Computer wurde durch Windows geschützt“: **„Weitere Informationen“ → „Trotzdem ausführen“**.
  (`start.bat` ist ein einfaches Textskript, mit dem Editor einsehbar; das Programmpaket enthält zusätzlich das
  nicht signierte Programm `programm\slpgen.exe` – im Zweifel IT fragen.)

Danach erscheint ein Menü:

| Taste | Funktion | Ergebnis |
|---|---|---|
| **1** | Beispielplan erzeugen und anzeigen | **zwei PDFs** öffnen sich: der bisherige Plan und derselbe Plan **im Hausstil** (Name endet auf `_Hausstil`) – bitte vor allem den Hausstil ansehen |
| **2** | Neues Projekt anlegen | Kopie der Excel-Vorlage in `meine_projekte\` öffnet sich in Excel |
| **3** | Projekt aus Excel erzeugen | Excel-Datei ins Fenster ziehen, Enter → Ordner `ausgabe` öffnet sich |
| **4** | Bestands-PDF auswerten | PDF ins Fenster ziehen → Struktur und gleichartige Anlagen (Typicals) |
| **5** | Selbsttest | „SELBSTTEST OK“ = Programm funktionsfähig |
| **6** | Hausprofil lernen | Ordner mit Ihren Bestands-PDFs ins Fenster ziehen → `hausprofil\profil.yaml` mit gelernten Zeichenregeln (z. B. welche Klemmleiste, welche Aderfarben, Änderungen über die Jahre). Werte mit wenigen Belegen sind als „unsicher“ markiert. Es öffnen sich eine kurze Zusammenfassung und die Excel-Liste `profil_freigabe.xlsx`. Bleibt nur auf Ihrem PC. |
| **7** | Hausprofil freigeben | In der Excel-Liste `hausprofil\profil_freigabe.xlsx` je Zeile **JA** (Wert in Spalte „Zur Freigabe“ stimmt) oder **NEIN** (stimmt nicht) wählen. Einen eigenen Wert nur zusammen mit JA eintragen. Speichern, dann Punkt 7. Nur freigegebene Werte verwendet das Programm beim Zeichnen im Hausstil (Einträge mit „wirkt im Plan noch nicht“ werden vorerst nur gespeichert). In der Liste stehen auch **Vorgaben** (Aderfarben je Potential, Kennbuchstaben) – mit JA bestätigen oder Ihren Wert eintragen. Ihre Freigaben bleiben beim erneuten Lernen erhalten. Welche Form ein eigener Wert haben muss, steht in der letzten Spalte „Erlaubte Form / Beispiel“ (z. B. Aderfarbe `DBU/WH`, Kennbuchstabe `T`, Klemmleiste `-X10`). Ist etwas falsch, meldet Punkt 7 alle Fehler auf einmal und übernimmt nichts – korrigieren, speichern, Punkt 7 erneut. |
| **8** | KI-Auftrag aus Lastenheft erstellen | Lastenheft (.docx, .pdf, .txt) ins Fenster ziehen, Enter. Frage „Lokale KI verwenden?“: **J**, wenn Ollama auf diesem PC läuft – dann schreibt die lokale KI die Antwort selbst, weiter mit Punkt 9. Sonst **N**: Der Auftrag liegt danach in der **Zwischenablage**: im KI-Chat mit Strg+V einfügen und absenden (nur eine vom Betrieb freigegebene KI, sonst Kundennamen vorher entfernen). Der Editor öffnet `<Lastenheft>_projektmodell.yaml` neben dem Lastenheft: die **ganze Antwort der KI** hineinkopieren (vorhandenen Inhalt ersetzen) und speichern. Klappt die Zwischenablage nicht, öffnet sich der Auftrag im Editor: Strg+A, Strg+C. |
| **9** | KI-Antwort prüfen und Plan erzeugen | `<Lastenheft>_projektmodell.yaml` ins Fenster ziehen, Enter. Ist alles vollständig, entstehen die PDFs im Unterordner `ausgabe` **neben dem Lastenheft** (öffnet sich); Annahmen und offene Fragen der KI stehen im Auslegungsnachweis. Fehlt etwas, liegt ein **Korrekturauftrag** in der Zwischenablage: im selben Chat einfügen, neue Antwort speichern, wieder Punkt 9. |
| **K** | Korrektur merken | Projektdatei ins Fenster ziehen – die Artikel und 24-V-Gruppen des Projekts werden angezeigt. Dann Art wählen (1 Artikel ersetzen, 2 24-V-Gruppe, 3 Mindestquerschnitt Motorleitung), Wert und Grund eingeben. Das Programm zeigt zuerst eine **Vorschau**; erst mit **J** wird die Hausregel gespeichert. Sie wirkt in allen weiteren Plänen (siehe „Korrekturen merken“). Mindestquerschnitt: Zahl in mm² von 0,5 bis 240, z. B. 2,5. |
| **L** | Hausregeln ansehen / abschalten | Zeigt alle Hausregeln mit Grund, Bearbeiter und Datum; mit der Nummer (z. B. R2) lässt sich eine Regel abschalten. Widerspricht eine neue Korrektur einer alten Regel, diese hier zuerst abschalten. |
| **A** | Eigenen Artikelstamm einlesen | Export Ihrer Artikelverwaltung bzw. EPLAN-Artikeldatenbank (Excel oder CSV mit Spalten Artikelnummer, Hersteller, Bezeichnung) ins Fenster ziehen. Es öffnet sich die Zuordnungsliste: je Programm-Artikel ein Vorschlag aus Ihrem Stamm – in Spalte E **JA** (Vorschlag) oder eine eigene Artikelnummer eintragen, speichern. |
| **Z** | Artikel-Zuordnung übernehmen | Übernimmt die Liste; ab dem nächsten Plan stehen in Stückliste und EPLAN-Daten Ihre Hersteller und Artikelnummern. |

**Projektordner:** Jedes Projekt hat einen eigenen Ordner (Punkt 2 legt ihn unter `meine_projekte\<Name>` an; beim KI-Weg der Ordner des Lastenhefts). Die Ergebnisse (PDFs, Stückliste, Planmodell) entstehen im Unterordner `ausgabe` dieses Ordners (Ausnahme: Beispielplan und Selbsttest, Punkt 1 und 5, im Programmordner). Steht auf den Seiten rot **„NICHT FÜR FERTIGUNG“**, enthält der Prüfbericht Fehler – Einzelheiten im Auslegungsnachweis (letzte Seiten).

## 4 Die Excel-Vorlage ausfüllen

| Blatt | Was eintragen | Hinweise |
|---|---|---|
| **Projekt** | Nummer, Bezeichnung, Kunde, Anlage, Ort, Datum … | Anlage/Ort **ohne** `=`/`+` eingeben (sonst hält Excel es für eine Formel) |
| **Feldgeraete** | je Zeile ein Gerät: BMK (z. B. `B7`), Artikel, Funktion, Gruppe, optional **Baustein** | Artikel aus der **Auswahlliste** wählen (Liste = Blatt *Artikel*). Für Geräte mit mehreren Signalen (z. B. Zähler mit Impuls + Drahtbruch, Pumpe) in Spalte „Baustein“ einen Eintrag aus Blatt *Bausteine* wählen; Spalte „Leitungslänge m“: Pflicht bei Pumpen (Spannungsfall), sonst für die Kabelliste (leer = „nach Feldmaß“) |
| **Motoren** | BMK, Funktion, Leistung kW, Nennstrom A, cos φ, Kabellänge m | Werte vom Typenschild |
| **Sicherheit** | Not-Halt (JA/NEIN/leer), PL, Stoppkategorie, Freigabe | Das Programm zeichnet **keine** Sicherheitsschaltung, nur eine rote Platzhalterseite. Der Plan bleibt „NICHT FÜR FERTIGUNG“, bis die Elektrofachkraft die Sicherheitsfunktion ausgelegt hat und bei *freigabe* Name und Datum einträgt. Feldgeräte mit „Not-Halt“, „Not-Aus“, „Schutztür“ o. Ä. im Funktionstext lösen das ebenfalls aus |
| **Regeln** | Reserve, Absicherungsfaktor, Netzteile, SPS-Module, Leitungswerte | erst ändern, wenn klar ist, was es bewirkt |
| **Artikel** | nur zum Nachschlagen | neue Artikel kommen in `beispiele\geraetestamm.yaml` |

Leere Zeilen werden übersprungen. Fehlt in einer Zeile ein Pflichtwert, nennt das Programm Blatt und
Zeilennummer.

## 5 Ergebnisse

Im Ordner **`ausgabe`**:

| Datei | Inhalt |
|---|---|
| `<Projektnummer>_Stromlaufplan_Hausstil.pdf` | **neu:** Plan im Hausstil – eine Anlage je Feldgerät/Motor (z. B. `=B01`), Spalten 0–9, Verweise wie `=VT24/1.3` (= Anlage VT24, Seite 1, Spalte 3), SPS-Kasten, Aderfarben |
| `<Projektnummer>_Stromlaufplan.pdf` | bisheriger Plan (bleibt zum Vergleich, bis Sie den Hausstil freigeben – Entscheidung E11) |
| `<Projektnummer>_Stueckliste.csv` | Stückliste, mit Excel zu öffnen |
| `<Projektnummer>_Planmodell.json` | alle Daten maschinenlesbar (für spätere Weiterverarbeitung) |

## 6 Probleme und Lösungen

| Meldung | Ursache | Lösung |
|---|---|---|
| „Python wurde nicht gefunden“ | Python fehlt oder Haken „PATH“ nicht gesetzt | Schritt 1 wiederholen, Haken setzen |
| „Die Programmdatei programm\slpgen.exe fehlt“ (Programmpaket) | ZIP nicht entpackt oder Virenscanner-Quarantäne | ZIP mit „Alle extrahieren…“ entpacken; meldet der Virenscanner `slpgen.exe`, IT fragen (Programm ist nicht signiert) |
| „FEHLER bei der Einrichtung“ | kein Internet / Firmen-Proxy | Ordner `.venv` löschen, mit Internet erneut starten; ggf. IT fragen |
| „Microsoft Visual C++ 14.0 or greater is required“ (Bibliothek PyYAML) | sehr neue Python-Version ohne fertige Bibliothek | ab dieser Programmversion automatisch umgangen; bei älterer `start.bat` neue Version laden. Alternativ Python 3.13 zusätzlich installieren |
| „Datei gesperrt“ | PDF oder Excel noch geöffnet | Datei schließen, erneut erzeugen |
| „Regelfehler: Artikel … fehlt im Gerätestamm“ | Artikel nicht im Stamm | Artikel aus der Auswahlliste wählen |
| „Regelfehler: Kein Querschnitt …“ | Kabel zu lang / Strom zu hoch für Tabelle | im Blatt *Regeln* weitere `iz_…`-Zeilen (Normwerte) ergänzen |
| Warnung „nicht freigegeben“ | Strombelastbarkeitswerte vorläufig | Normwerte eintragen, dann `leitungen_freigegeben` = JA |

## 7 Vertraulichkeit

Eigene Projekte liegen in `meine_projekte\` und Ergebnisse in `ausgabe\` – beide Ordner werden **nicht**
ins Repository übertragen. Kunden-PDFs nur lokal auswerten (Menüpunkt 4), nicht ins Repository kopieren.

## Korrekturen merken (Hausregeln)

Wenn Sie im erzeugten Plan immer wieder dasselbe ändern (z. B. „bei uns induktive statt optischer Sensoren“),
können Sie die Korrektur als **Hausregel** speichern. Sie wirkt ab dem nächsten Plan automatisch und steht im
Auslegungsnachweis unter „Angewendete Hausregeln“ (mit Bearbeiter, Datum und Herkunft).

Im Menü über die Punkte **K** und **L**. Für Fortgeschrittene geht es auch über die Kommandozeile:

- Regel anlegen: `python -m slpgen korrektur <Projektdatei> --art artikel_ersetzen --wenn OPT-REF-PNP --dann IND-M12-PNP --grund "Hausstandard"` (mit `--vorschau` nur ansehen)
- Mindestquerschnitt: `python -m slpgen korrektur <Projektdatei> --art mindestquerschnitt --wenn motorleitung --dann 2,5`
- Regeln ansehen und prüfen: `python -m slpgen hausregeln`
- Regel ausschalten, wieder einschalten, löschen: `python -m slpgen hausregel aus R1` (bzw. `ein`, `loeschen`)

Das Programm speichert eine Regel nur, wenn sie wirklich etwas ändert und der Plan damit weiterhin entsteht.
Die Regeln liegen nur auf diesem PC in `hausprofil\hausregeln.yaml`.
