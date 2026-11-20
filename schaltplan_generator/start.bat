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
echo   1  Beispielplan erzeugen und anzeigen (bisher + Hausstil)
echo   2  Neues Projekt anlegen (Excel-Vorlage kopieren)
echo   3  Projekt aus Excel erzeugen
echo   4  Bestands-PDF auswerten (Struktur, Typicals)
echo   5  Selbsttest
echo   6  Hausprofil lernen (Ordner mit Bestands-PDFs)
echo   7  Hausprofil freigeben (Excel-Liste uebernehmen)
echo   8  KI-Auftrag aus Lastenheft erstellen (fuer einen KI-Chat)
echo   9  KI-Antwort pruefen und Plan erzeugen
echo   0  Beenden
echo.
set "W="
set /p "W=Auswahl eingeben und Enter druecken: "
if "%W%"=="1" goto :beispiel
if "%W%"=="2" goto :neu
if "%W%"=="3" goto :excel
if "%W%"=="4" goto :struktur
if "%W%"=="5" goto :kiauftrag
echo Lastenheft (.docx, .pdf oder .txt) in dieses Fenster ziehen und Enter druecken:
set "LH="
set /p "LH=> "
if not defined LH goto :menue
set "LH=%LH:"=%"
for %%F in ("%LH%") do (set "LHDIR=%%~dpF" & set "LHNAME=%%~nF")
set "SLPGEN_MENUE=1"
%SLP% ki-auftrag "%LH%"
if errorlevel 1 goto :fehler_lauf
rem Auftrag in die Zwischenablage (UTF-8, Umlaute bleiben erhalten)
powershell -NoProfile -Command "Get-Content -Raw -Encoding UTF8 -LiteralPath '%LHDIR%%LHNAME%_KI_Auftrag.txt' | Set-Clipboard"
if not exist "%LHDIR%projektmodell.yaml" type nul > "%LHDIR%projektmodell.yaml"
start "" notepad "%LHDIR%projektmodell.yaml"
pause
goto :menue

:kiantwort
echo Gespeicherte KI-Antwort (z. B. projektmodell.yaml) in dieses Fenster ziehen und Enter druecken:
set "KA="
set /p "KA=> "
if not defined KA goto :menue
set "KA=%KA:"=%"
for %%F in ("%KA%") do (set "KADIR=%%~dpF" & set "KANAME=%%~nF")
set "SLPGEN_MENUE=1"
del "%KADIR%%KANAME%_Korrektur_fuer_KI.txt" 2>nul
%SLP% pruefen "%KA%"
if errorlevel 1 goto :ki_korrektur
%SLP% generieren "%KA%" --ausgabe ausgabe
if errorlevel 1 goto :fehler_lauf
start "" "ausgabe"
pause
goto :menue

:ki_korrektur
if not exist "%KADIR%%KANAME%_Korrektur_fuer_KI.txt" goto :fehler_lauf
echo.
echo Der Korrekturauftrag fuer die KI liegt jetzt in der Zwischenablage:
echo im selben KI-Chat mit Strg+V einfuegen, neue Antwort speichern, dann wieder Punkt 9.
powershell -NoProfile -Command "Get-Content -Raw -Encoding UTF8 -LiteralPath '%KADIR%%KANAME%_Korrektur_fuer_KI.txt' | Set-Clipboard" 2>nul
pause
goto :menue

:selbsttest
if "%W%"=="6" goto :lernen
if "%W%"=="7" goto :freigabe
if "%W%"=="8" goto :kiauftrag
if "%W%"=="9" goto :kiantwort
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
if "%N%"=="" goto :menue
if exist "meine_projekte\%N%.xlsx" echo Gibt es schon: meine_projekte\%N%.xlsx & pause & goto :menue
copy "beispiele\Projekt_Vorlage.xlsx" "meine_projekte\%N%.xlsx" >nul
echo Angelegt: meine_projekte\%N%.xlsx  - wird jetzt in Excel geoeffnet.
echo Nach dem Ausfuellen speichern und hier Punkt 3 waehlen.
start "" "meine_projekte\%N%.xlsx"
pause
goto :menue

:excel
echo Excel-Datei mit der Maus in dieses Fenster ziehen und Enter druecken
echo (oder Pfad eintippen, z. B. meine_projekte\Kunde_Anlage1.xlsx):
set "XL="
set /p "XL=> "
if not defined XL goto :menue
set "XL=%XL:"=%"
%SLP% generieren "%XL%" --ausgabe ausgabe
if errorlevel 1 goto :fehler_lauf
start "" "ausgabe"
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

:fehler_lauf
echo.
echo Das Programm hat einen Fehler gemeldet (siehe Text oben).
pause
goto :menue

:ende
endlocal
