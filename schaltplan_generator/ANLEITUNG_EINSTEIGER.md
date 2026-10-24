# Anleitung für Einsteiger – Stromlaufplan-Generator (Windows)

**Was ist das?** Ein lauffähiger **Prototyp**. Aus einer ausgefüllten Excel-Tabelle (Feldgeräte, Motoren,
Regeln) erzeugt er automatisch einen Stromlaufplan als PDF, dazu Stückliste, Klemmenplan, Kabelliste und
Auslegungsnachweis.
**Was ist es (noch) nicht?** Ein fertiges Produkt. Die Artikel im Gerätestamm sind Platzhalter, das Layout
ist noch nicht Ihr Hausstandard. Jeder erzeugte Plan trägt den Vermerk „nicht freigegeben“ und muss von
einer Elektrofachkraft geprüft werden.

---

## 1 Einmalig: Python installieren (ca. 5 Minuten)

1. https://www.python.org/downloads/ öffnen → gelben Knopf **„Download Python 3.x“** klicken.
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

- Beim **ersten Start** richtet sich das Programm selbst ein (1–3 Minuten, Internet nötig).
- Meldet Windows „Der Computer wurde durch Windows geschützt“: **„Weitere Informationen“ → „Trotzdem ausführen“**.
  (Die Datei ist ein einfaches Textskript; Inhalt mit dem Editor einsehbar.)

Danach erscheint ein Menü:

| Taste | Funktion | Ergebnis |
|---|---|---|
| **1** | Beispielplan erzeugen und anzeigen | PDF öffnet sich – so sieht man sofort, ob alles funktioniert |
| **2** | Neues Projekt anlegen | Kopie der Excel-Vorlage in `meine_projekte\` öffnet sich in Excel |
| **3** | Projekt aus Excel erzeugen | Excel-Datei ins Fenster ziehen, Enter → Ordner `ausgabe` öffnet sich |
| **4** | Bestands-PDF auswerten | PDF ins Fenster ziehen → Struktur und gleichartige Anlagen (Typicals) |
| **5** | Selbsttest | „SELBSTTEST OK“ = Programm funktionsfähig |

## 4 Die Excel-Vorlage ausfüllen

| Blatt | Was eintragen | Hinweise |
|---|---|---|
| **Projekt** | Nummer, Bezeichnung, Kunde, Anlage, Ort, Datum … | Anlage/Ort **ohne** `=`/`+` eingeben (sonst hält Excel es für eine Formel) |
| **Feldgeraete** | je Zeile ein Gerät: BMK (z. B. `B7`), Artikel, Funktion, Gruppe | Artikel aus der **Auswahlliste** wählen (Liste = Blatt *Artikel*) |
| **Motoren** | BMK, Funktion, Leistung kW, Nennstrom A, cos φ, Kabellänge m | Werte vom Typenschild |
| **Regeln** | Reserve, Absicherungsfaktor, Netzteile, SPS-Module, Leitungswerte | erst ändern, wenn klar ist, was es bewirkt |
| **Artikel** | nur zum Nachschlagen | neue Artikel kommen in `beispiele\geraetestamm.yaml` |

Leere Zeilen werden übersprungen. Fehlt in einer Zeile ein Pflichtwert, nennt das Programm Blatt und
Zeilennummer.

## 5 Ergebnisse

Im Ordner **`ausgabe`**:

| Datei | Inhalt |
|---|---|
| `<Projektnummer>_Stromlaufplan.pdf` | Plan mit Deckblatt, Inhalt, Einspeisung, 24 V, SPS, Motoren, Feldgeräten, Klemmen-/Kabelliste, Stückliste, Auslegung |
| `<Projektnummer>_Stueckliste.csv` | Stückliste, mit Excel zu öffnen |
| `<Projektnummer>_Planmodell.json` | alle Daten maschinenlesbar (für spätere Weiterverarbeitung) |

## 6 Probleme und Lösungen

| Meldung | Ursache | Lösung |
|---|---|---|
| „Python wurde nicht gefunden“ | Python fehlt oder Haken „PATH“ nicht gesetzt | Schritt 1 wiederholen, Haken setzen |
| „FEHLER bei der Einrichtung“ | kein Internet / Firmen-Proxy | Ordner `.venv` löschen, mit Internet erneut starten; ggf. IT fragen |
| „Datei gesperrt“ | PDF oder Excel noch geöffnet | Datei schließen, erneut erzeugen |
| „Regelfehler: Artikel … fehlt im Gerätestamm“ | Artikel nicht im Stamm | Artikel aus der Auswahlliste wählen |
| „Regelfehler: Kein Querschnitt …“ | Kabel zu lang / Strom zu hoch für Tabelle | im Blatt *Regeln* weitere `iz_…`-Zeilen (Normwerte) ergänzen |
| Warnung „nicht freigegeben“ | Strombelastbarkeitswerte vorläufig | Normwerte eintragen, dann `leitungen_freigegeben` = JA |

## 7 Vertraulichkeit

Eigene Projekte liegen in `meine_projekte\` und Ergebnisse in `ausgabe\` – beide Ordner werden **nicht**
ins Repository übertragen. Kunden-PDFs nur lokal auswerten (Menüpunkt 4), nicht ins Repository kopieren.
