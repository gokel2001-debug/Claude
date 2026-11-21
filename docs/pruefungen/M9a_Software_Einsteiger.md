# Prüfung M9a – Windows-Programmpaket (Commits 785d655, fd2c066)

Prüfer: Einsteiger (vor dem Nutzungslimit), Software (nachgeholt als M9p). Nacharbeit in fd2c066 und Folgecommit.

| Nr. | Prüfer | Schwere | Befund (kurz) | Nacharbeit | Stand |
|---|---|---|---|---|---|
| E1 | Einsteiger | hoch | fehlende Exe → irreführende Meldung „Python fehlt“ | eigene Meldung :keineexe (Entpacken/Virenscanner), Abschnitt 6 | behoben |
| E2 | Einsteiger | hoch | kein Weg zu neuer Version ohne Verlust von Hausprofil/Projekten | Anleitung „Neue Version einspielen“ | behoben (Automatik → M9b) |
| E3–E6 | Einsteiger | mittel | 14-Tage-Aufbewahrung, Zweig/Anmeldung, Abschnitt 3 widersprüchlich, Virenscanner | Anleitung ergänzt | behoben |
| E7 / S4 | beide | gering | Hinweise mit `python -m slpgen` im Paket | Hinweistexte zeigen im Paket `programm\\slpgen.exe`, Anleitung ergänzt | behoben |
| E8–E10 | Einsteiger | gering | Anleitung nur .md, keine Versionsnummer, „Betreuer“ unbenannt | → M9b (Handbuch PDF, Version) | offen (M9b) |
| S1 | Software | mittel | Prüfausgabe KI-Auftrag blieb im Artefakt (falscher Dateiname beim Löschen) | KI-Auftrag im Selbsttest nach `ausgabe\\`, wird mit gelöscht | behoben |
| S2 | Software | gering | lokaler Bau konnte ungetrackte Dateien aus `beispiele\\` mitnehmen | nur `git ls-files beispiele`; Sperrliste um ausgabe, VERTRAULICH, hausregeln*, profil*, Fehlerlog erweitert | behoben |
| S3 | Software | gering | `schema` schrieb in der Exe außerhalb des Pakets | `DOCS` | behoben |
| S5 | Software | gering | Workflow ohne `permissions`, läuft auf jedem Zweig | `contents: read`, nur Arbeitszweig/main; Versionen festlegen → M9b | teilweise |
| S6 | Software | gering | Tests für :keineexe und Paketquellen fehlten | Test ergänzt | behoben |
