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
echo   1  Beispielplan erzeugen und anzeigen
echo   2  Neues Projekt anlegen (Excel-Vorlage kopieren)
echo   3  Projekt aus Excel erzeugen
echo   4  Bestands-PDF auswerten (Struktur, Typicals)
echo   5  Selbsttest
echo   0  Beenden
echo.
set "W="
set /p "W=Auswahl eingeben und Enter druecken: "
if "%W%"=="1" goto :beispiel
if "%W%"=="2" goto :neu
if "%W%"=="3" goto :excel
if "%W%"=="4" goto :struktur
if "%W%"=="5" goto :selbsttest
if "%W%"=="0" goto :ende
goto :menue

:beispiel
%SLP% generieren beispiele\Projekt_Vorlage.xlsx --ausgabe ausgabe
if errorlevel 1 goto :fehler_lauf
start "" "ausgabe\P-2026-001_Stromlaufplan.pdf"
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
