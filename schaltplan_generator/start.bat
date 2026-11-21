@echo off
rem Stromlaufplan-Generator - Start per Doppelklick (Windows)
setlocal
cd /d "%~dp0"
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
title Stromlaufplan-Generator (slpgen)

rem ---- Python suchen: bevorzugt Versionen, fuer die alle Bibliotheken fertig vorliegen ----
set "PY="
for %%V in (3.13 3.14 3.12) do if not defined PY py -%%V -c "pass" >nul 2>nul && set "PY=py -%%V"
if not defined PY where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY goto :keinpython

rem ---- Einrichtung beim ersten Start ----
if exist ".venv\eingerichtet.txt" goto :bereit
echo.
echo Erster Start: Programmumgebung wird eingerichtet (1-3 Minuten, Internet noetig) ...
%PY% -m venv .venv
if errorlevel 1 goto :keinpython
rem PyYAML ohne C-Erweiterung bauen: kein C++-Compiler noetig (z. B. bei sehr neuen Python-Versionen)
set "PYYAML_FORCE_LIBYAML=0"
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 goto :fehler_install
echo ok> ".venv\eingerichtet.txt"

:bereit
set "SLP=.venv\Scripts\python.exe -m slpgen"
if not exist "meine_projekte" mkdir "meine_projekte"

:menue
cls
echo ==========================================================
echo   Stromlaufplan-Generator  (Prototyp - nicht freigegeben)
echo ==========================================================
echo.
echo   Projekt aus Lastenheft (mit KI-Chat):
echo   8  KI-Auftrag aus Lastenheft erstellen
echo   9  KI-Antwort pruefen und Plan erzeugen
echo.
echo   Projekt aus Excel:
echo   2  Neues Projekt anlegen (Excel-Vorlage kopieren)
echo   3  Projekt aus Excel erzeugen
echo.
echo   Hausprofil:
echo   6  Hausprofil lernen (Ordner mit Bestands-PDFs)
echo   7  Hausprofil freigeben (Excel-Liste uebernehmen)
echo   K  Korrektur merken (Hausregel, wirkt in allen weiteren Plaenen)
echo   L  Hausregeln ansehen / abschalten
echo   A  Eigenen Artikelstamm einlesen (Excel/CSV-Export)
echo   Z  Artikel-Zuordnung uebernehmen (Excel-Liste)
echo.
echo   Werkzeuge:
echo   1  Beispielplan erzeugen und anzeigen (bisher + Hausstil)
echo   4  Bestands-PDF auswerten (Struktur, Typicals)
echo   5  Selbsttest
echo.
echo   0  Beenden
echo.
set "W="
set /p "W=Auswahl eingeben und Enter druecken: "
if defined W set "W=%W:"=%"
if "%W%"=="1" goto :beispiel
if "%W%"=="2" goto :neu
if "%W%"=="3" goto :excel
if "%W%"=="4" goto :struktur
if "%W%"=="5" goto :selbsttest
if "%W%"=="6" goto :lernen
if "%W%"=="7" goto :freigabe
if "%W%"=="8" goto :kiauftrag
if "%W%"=="9" goto :kiantwort
if /i "%W%"=="K" goto :korrektur
if /i "%W%"=="L" goto :hausregeln
if /i "%W%"=="A" goto :artikelstamm
if /i "%W%"=="Z" goto :artikelzuordnung
if "%W%"=="0" goto :ende
goto :menue

:beispiel
%SLP% generieren beispiele\Projekt_Vorlage.xlsx --ausgabe ausgabe
if errorlevel 1 goto :fehler_lauf
start "" "ausgabe\P-2026-001_Stromlaufplan.pdf"
start "" "ausgabe\P-2026-001_Stromlaufplan_Hausstil.pdf"
pause
goto :menue

:neu
set "N="
set /p "N=Name fuer das neue Projekt (ohne Leerzeichen, z. B. Kunde_Anlage1): "
if defined N set "N=%N:"=%"
if "%N%"=="" goto :menue
if exist "meine_projekte\%N%" echo Gibt es schon: meine_projekte\%N% & pause & goto :menue
mkdir "meine_projekte\%N%"
copy "beispiele\Projekt_Vorlage.xlsx" "meine_projekte\%N%\%N%.xlsx" >nul
echo Angelegt: Projektordner meine_projekte\%N%  - die Excel-Datei wird jetzt geoeffnet.
echo Nach dem Ausfuellen speichern und hier Punkt 3 waehlen. Ergebnisse landen in meine_projekte\%N%\ausgabe.
start "" "meine_projekte\%N%\%N%.xlsx"
pause
goto :menue

:excel
echo Excel-Datei mit der Maus in dieses Fenster ziehen und Enter druecken
echo (oder Pfad eintippen, z. B. meine_projekte\Kunde_Anlage1\Kunde_Anlage1.xlsx):
set "XL="
set /p "XL=> "
if not defined XL goto :menue
set "XL=%XL:"=%"
for %%F in ("%XL%") do (set "XLDIR=%%~dpF")
set "SLPGEN_MENUE=1"
%SLP% generieren "%XL%"
if errorlevel 1 goto :plan_mit_fehler
start "" "%XLDIR%ausgabe"
pause
goto :menue

:struktur
echo PDF-Datei (aus E-CAD exportiert) in dieses Fenster ziehen und Enter druecken:
set "PDF="
set /p "PDF=> "
if not defined PDF goto :menue
set "PDF=%PDF:"=%"
if not exist "analyse" mkdir "analyse"
%SLP% struktur "%PDF%" --ausgabe "analyse\struktur.json"
if errorlevel 1 goto :fehler_lauf
echo.
echo Vollstaendiges Ergebnis: analyse\struktur.json
pause
goto :menue

:lernen
echo Ordner mit Ihren Bestands-PDFs in dieses Fenster ziehen und Enter druecken:
set "ORD="
set /p "ORD=> "
if not defined ORD goto :menue
set "ORD=%ORD:"=%"
rem abschliessenden Backslash entfernen (z. B. D:\ ), sonst wird das Anfuehrungszeichen maskiert
if "%ORD:~-1%"=="\" set "ORD=%ORD%."
%SLP% lernen "%ORD%" --profil "hausprofil\profil.yaml"
if errorlevel 1 goto :fehler_lauf
echo.
echo Profil gespeichert in hausprofil\ (bleibt nur auf diesem PC).
echo Es oeffnen sich die Zusammenfassung und die Freigabeliste (Excel).
echo In Excel je Zeile JA oder NEIN waehlen, speichern, dann hier Punkt 7.
start "" notepad "hausprofil\profil_uebersicht.txt"
start "" "hausprofil\profil_freigabe.xlsx"
pause
goto :menue

:freigabe
%SLP% freigabe --profil "hausprofil\profil.yaml" --liste "hausprofil\profil_freigabe.xlsx"
if errorlevel 1 goto :fehler_lauf
pause
goto :menue

:kiauftrag
echo Lastenheft (.docx, .pdf oder .txt) in dieses Fenster ziehen und Enter druecken:
set "LH="
set /p "LH=> "
if not defined LH goto :menue
set "LH=%LH:"=%"
for %%F in ("%LH%") do (set "LHDIR=%%~dpF" & set "LHNAME=%%~nF")
set "SLPGEN_MENUE=1"
set "LOKAL="
set /p "LOKAL=Lokale KI (Ollama auf diesem PC) verwenden? J/N (Enter = N, Chat im Browser): "
if /i "%LOKAL%"=="J" goto :kiauftrag_lokal
%SLP% ki-auftrag "%LH%"
if errorlevel 1 goto :fehler_lauf
set "CLIPDATEI=%LHDIR%%LHNAME%_KI_Auftrag.txt"
call :zwischenablage
set "ANTWORT=%LHDIR%%LHNAME%_projektmodell.yaml"
if not exist "%ANTWORT%" type nul > "%ANTWORT%"
start "" notepad "%ANTWORT%"
pause
goto :menue

:kiauftrag_lokal
%SLP% ki-auftrag "%LH%" --ollama http://localhost:11434
if errorlevel 1 goto :fehler_lauf
pause
goto :menue

:kiantwort
echo Gespeicherte KI-Antwort (...._projektmodell.yaml) in dieses Fenster ziehen und Enter druecken:
set "KA="
set /p "KA=> "
if not defined KA goto :menue
set "KA=%KA:"=%"
for %%F in ("%KA%") do (set "KADIR=%%~dpF" & set "KANAME=%%~nF")
set "SLPGEN_MENUE=1"
del "%KADIR%%KANAME%_Korrekturauftrag.txt" 2>nul
%SLP% pruefen "%KA%"
if errorlevel 1 goto :ki_korrektur
set "XLDIR=%KADIR%"
%SLP% generieren "%KA%" --ausgabe "%KADIR%ausgabe"
if errorlevel 1 goto :plan_mit_fehler
start "" "%KADIR%ausgabe"
pause
goto :menue

:ki_korrektur
if not exist "%KADIR%%KANAME%_Korrekturauftrag.txt" goto :fehler_lauf
set "CLIPDATEI=%KADIR%%KANAME%_Korrekturauftrag.txt"
call :zwischenablage
pause
goto :menue

:zwischenablage
rem Pfad ueber Umgebungsvariable: Apostroph, Klammern und & im Pfad stoeren so nicht
powershell -NoProfile -Command "Get-Content -Raw -Encoding UTF8 -LiteralPath $env:CLIPDATEI | Set-Clipboard"
rem keine Klammerbloecke: eine Klammer im Pfad wuerde sie vorzeitig schliessen
if errorlevel 1 goto :zwischenablage_fehler
echo.
echo Der Text liegt in der Zwischenablage: im KI-Chat mit Strg+V einfuegen und absenden.
exit /b 0
:zwischenablage_fehler
echo.
echo Zwischenablage ging nicht. Bitte die Datei selbst kopieren (Editor oeffnet sich: Strg+A, Strg+C):
echo "%CLIPDATEI%"
start "" notepad "%CLIPDATEI%"
exit /b 0

:korrektur
echo Projektdatei (Excel oder ..._projektmodell.yaml) in dieses Fenster ziehen und Enter druecken:
set "KP="
set /p "KP=> "
if not defined KP goto :menue
set "KP=%KP:"=%"
%SLP% artikelliste "%KP%"
if errorlevel 1 goto :fehler_lauf
echo.
echo Was soll sich in allen weiteren Plaenen aendern?
echo   1 = Artikel ersetzen   2 = 24-V-Gruppe setzen   3 = Mindestquerschnitt Motor-/Leistungsleitung
echo   4 = vom Programm gewaehltes Geraet ersetzen (Frequenzumrichter, Schuetz, Motorschutzschalter)
set "KA="
set /p "KA=> "
set "KART="
if "%KA%"=="1" set "KART=artikel_ersetzen"
if "%KA%"=="2" set "KART=gruppe_setzen"
if "%KA%"=="3" set "KART=mindestquerschnitt"
if "%KA%"=="4" set "KART=auswahl_ersetzen"
if not defined KART echo Ungueltige Wahl - zurueck zum Menue. & pause & goto :menue
set "KW=motorleitung"
set "FRAGE=Mindestquerschnitt in mm2 (0,5 bis 240, z. B. 2,5): "
if "%KART%"=="mindestquerschnitt" goto :korrektur_wert
set "KW="
set /p "KW=Artikel aus der Liste oben, fuer den die Regel gilt: "
if not defined KW echo Kein Artikel eingegeben - zurueck zum Menue. & pause & goto :menue
set "FRAGE=Ersatzartikel aus dem Geraetestamm: "
if "%KART%"=="gruppe_setzen" set "FRAGE=24-V-Gruppe (aus der Liste oben oder neuer Name): "
:korrektur_wert
set "KD="
set /p "KD=%FRAGE%"
if not defined KD echo Kein Wert eingegeben - zurueck zum Menue. & pause & goto :menue
set "KG="
set /p "KG=Grund (kurz, Enter = ohne): "
if defined KG set "KG=%KG:"=%"
%SLP% korrektur "%KP%" --art %KART% --wenn "%KW%" --dann "%KD%" --grund "%KG%" --vorschau
if errorlevel 1 goto :fehler_lauf
set "OK="
set /p "OK=So speichern? (J/N): "
if /i not "%OK%"=="J" echo Nicht gespeichert. & pause & goto :menue
%SLP% korrektur "%KP%" --art %KART% --wenn "%KW%" --dann "%KD%" --grund "%KG%"
if errorlevel 1 goto :fehler_lauf
pause
goto :menue

:hausregeln
%SLP% hausregeln
echo.
echo Regel abschalten: Nummer eingeben (z. B. R2) und Enter, nur Enter = zurueck
set "RID="
set /p "RID=> "
if not defined RID goto :menue
%SLP% hausregel aus "%RID%"
if errorlevel 1 goto :fehler_lauf
pause
goto :menue

:artikelstamm
echo Artikel-Export (Excel .xlsx oder .csv mit Spalten Artikelnummer, Hersteller, Bezeichnung) ins Fenster ziehen:
set "AE="
set /p "AE=> "
if not defined AE goto :menue
set "AE=%AE:"=%"
%SLP% artikelstamm "%AE%"
if errorlevel 1 goto :fehler_lauf
echo In Excel Spalte E: JA = Vorschlag uebernehmen, oder eigene Artikelnummer eintragen. Speichern, dann Punkt Z.
start "" "hausprofil\artikelzuordnung.xlsx"
pause
goto :menue

:artikelzuordnung
%SLP% artikelzuordnung
if errorlevel 1 goto :fehler_lauf
pause
goto :menue

:selbsttest
%SLP% generieren beispiele\projekt_beispiel.yaml --ausgabe ausgabe\selbsttest
if errorlevel 1 goto :fehler_lauf
echo.
echo SELBSTTEST OK - Programm ist funktionsfaehig.
pause
goto :menue

:keinpython
echo.
echo FEHLER: Python wurde nicht gefunden.
echo Bitte Python von https://www.python.org/downloads/ installieren
echo und dabei den Haken "Add python.exe to PATH" setzen.
echo Danach diese Datei erneut doppelklicken. Details: ANLEITUNG_EINSTEIGER.md
pause
goto :ende

:fehler_install
echo.
echo FEHLER bei der Einrichtung - Ursache steht im Text oben (rot: "ERROR").
echo Haeufig: keine Internetverbindung/Firmen-Proxy oder sehr neue Python-Version.
echo Abhilfe: Ordner ".venv" loeschen und erneut starten; sonst Python 3.13 zusaetzlich installieren.
echo Details: ANLEITUNG_EINSTEIGER.md, Abschnitt "Probleme"
pause
goto :ende

:plan_mit_fehler
rem Plan kann trotz Fehler entstanden sein (rot gestempelt) - dann Ordner zeigen
if not exist "%XLDIR%ausgabe" goto :fehler_lauf
echo.
echo Falls PDFs entstanden sind, sind sie rot gestempelt NICHT FUER FERTIGUNG (Ordner oeffnet sich).
start "" "%XLDIR%ausgabe"
goto :fehler_lauf

:fehler_lauf
echo.
echo Das Programm hat einen Fehler gemeldet (siehe Text oben).
pause
goto :menue

:ende
endlocal
