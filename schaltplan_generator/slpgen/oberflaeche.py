"""Anwender-Oberfläche (ZIEL 4a/4b, Meilenstein M10, Entscheidung E19): lokaler Webserver nur auf 127.0.0.1.

Keine Internetverbindung, keine externen Dateien (kein CDN), nur Python-Standardbibliothek – läuft unverändert
im PyInstaller-Paket. Die Oberfläche ruft denselben Planungskern auf wie Menü und Kommandozeile.

Aufbau: Startseite = Projektliste + „Neues Projekt“; je Projekt eine Seite /projekt/<Name> mit Schrittleiste
(6 Schritte nach ZIEL 4b, Zustand erledigt/aktuell/folgt). M10a: Schritt 1 (Projekt anlegen, Excel/Ordner öffnen),
Hilfe-Seiten. Schritte 2–6 folgen in M10b–M10d.

Sicherheit: nur 127.0.0.1; fremder Host-Kopf (DNS-Rebinding) oder fremde Herkunft (Origin) bei POST → 403;
Projektnamen nur Buchstaben, Ziffern, _ und -, keine unter Windows reservierten Namen (kein Pfad).
"""
from __future__ import annotations

import html
import os
import re
import shutil
import subprocess
import sys
import threading
import urllib.parse
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

RE_NAME = re.compile(r"^[A-Za-z0-9ÄÖÜäöüß_-]{1,60}$")
WINDOWS_RESERVIERT = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
FENSTER = "Stromlaufplan-Generator Oberflaeche"     # Fenstertitel aus start.bat

SCHRITTE = [
    ("Projekt anlegen", "Ein Projekt ist ein Ordner mit allen Eingaben und Ergebnissen. Kopieren = sichern."),
    ("Unterlagen einlesen", "Lastenheft, Feldgeräteliste (Excel) oder Antwort des KI-Chats auswählen."),
    ("Rückfragen und Annahmen prüfen", "Fehlende Angaben und Annahmen der Software im Klartext bestätigen oder ändern."),
    ("Plan erzeugen", "Stromlaufplan im Hausstil mit Stückliste, Klemmenplan und Kabelliste."),
    ("Prüfbericht ansehen", "Was die Software geprüft hat – Fehler verhindern die Freigabe zur Fertigung."),
    ("PDF und Listen öffnen", "Ergebnisse liegen im Projektordner (Unterordner ausgabe)."),
]
FERTIG_BIS = 1          # Schritte 1..FERTIG_BIS sind in der Oberfläche bedienbar (M10a)

HILFE = {
    "start": ("So arbeiten Sie mit dem Programm",
              "Legen Sie ein Projekt an oder öffnen Sie ein vorhandenes. Auf der Projektseite führen die Schritte 1 bis 6 "
              "durch den Ablauf. Alles bleibt auf diesem PC – nichts geht ins Internet. Die Oberfläche läuft, solange das "
              f"Fenster „{FENSTER}“ offen ist; schließen Sie es, wenn Sie fertig sind. Wieder öffnen: Programm starten, "
              "Taste O. Schritte, die hier noch fehlen, erledigen Sie im Menüfenster des Programms."),
    "projekt": ("Projekt anlegen",
                "Geben Sie einen kurzen Namen ein, z. B. Kunde_Anlage1 (nur Buchstaben, Ziffern, _ und -). Das Programm "
                "legt den Ordner meine_projekte\\<Name> mit einer Excel-Vorlage an. Diesen Ordner können Sie kopieren, "
                "um das Projekt zu sichern."),
}

STIL = """
:root{--text:#1b1f24;--grund:#ffffff;--leicht:#f2f4f7;--rand:#c9d0d8;--bedien:#6b7684;--akzent:#0b5cad;--auf-akzent:#ffffff;
--gut:#1d7a3a;--schlecht:#b3261e}
@media (prefers-color-scheme:dark){:root{--text:#e8eaed;--grund:#16181c;--leicht:#22262c;--rand:#3a4048;--bedien:#8a94a3;
--akzent:#7ab4ff;--auf-akzent:#0d1117;--gut:#6fd08c;--schlecht:#ff8a80}}
*{box-sizing:border-box}body{margin:0;font:16px/1.5 system-ui,Segoe UI,Arial,sans-serif;color:var(--text);background:var(--grund)}
header{padding:12px 20px;border-bottom:1px solid var(--rand);display:flex;justify-content:space-between;align-items:center;gap:12px}
header h1{font-size:20px;margin:0}header h1 a{color:inherit;text-decoration:none}.kennzeichnung{margin:0;font-size:14px}
main{max-width:920px;margin:0 auto;padding:20px}a{color:var(--akzent)}
:focus-visible{outline:3px solid var(--akzent);outline-offset:2px}
.hilfe{font-weight:700;text-decoration:none;border:1px solid var(--bedien);border-radius:50%;display:inline-block;width:28px;
height:28px;text-align:center;line-height:26px}
ol.schritte{list-style:none;padding:0;counter-reset:s}ol.schritte li{counter-increment:s;border:1px solid var(--rand);
border-radius:8px;padding:12px 14px 12px 56px;margin:10px 0;position:relative;background:var(--leicht)}
ol.schritte li::before{content:counter(s);position:absolute;left:14px;top:12px;width:30px;height:30px;border-radius:50%;
background:var(--akzent);color:var(--auf-akzent);text-align:center;line-height:30px;font-weight:700}
ol.schritte li.erledigt::before{content:"✓";background:var(--gut)}ol.schritte li.folgt{opacity:.7}
ol.schritte li.folgt::before{background:var(--rand);color:var(--text)}.merkmal{font-size:14px;font-style:italic}
.knopf{background:var(--akzent);color:var(--auf-akzent);border:0;border-radius:6px;padding:9px 16px;font-size:16px;cursor:pointer}
.knopf:hover{filter:brightness(1.12)}.knopf.zweit{background:transparent;color:var(--akzent);border:1px solid var(--bedien)}
form.inline{display:inline}input[type=text]{font-size:16px;padding:8px;border:1px solid var(--bedien);border-radius:6px;
width:min(100%,360px);background:var(--grund);color:var(--text)}input[aria-invalid=true]{border-color:var(--schlecht)}
.meldung{border-left:4px solid var(--gut);padding:8px 12px;background:var(--leicht);margin:12px 0}
.meldung.fehler,.feldfehler{border-color:var(--schlecht)}.feldfehler{color:var(--schlecht);margin:6px 0}
table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid var(--rand);padding:6px 8px;text-align:left}
"""


def _seite(titel: str, inhalt: str, hilfe: str | None = "start") -> bytes:
    knopf = (f'<a class="hilfe" href="/hilfe/{hilfe}" title="Hilfe zu dieser Seite" aria-label="Hilfe zu dieser Seite">?</a>'
             if hilfe else "")
    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(titel)} – Stromlaufplan-Generator</title>
<style>{STIL}</style></head><body><header><div><h1><a href="/">Stromlaufplan-Generator</a></h1>
<p class="kennzeichnung">Prototyp – Pläne nicht zur Fertigung freigegeben · läuft nur auf diesem PC</p></div>{knopf}</header>
<main>{inhalt}</main></body></html>""".encode()


def oeffne_im_system(pfad: Path) -> bool:
    """Datei/Ordner mit dem zugehörigen Programm öffnen (Excel, Explorer). False, wenn das System das nicht kann."""
    try:
        if hasattr(os, "startfile"):
            os.startfile(pfad)                       # type: ignore[attr-defined]  # nur Windows
            return True
        befehl = "open" if sys.platform == "darwin" else "xdg-open"
        if shutil.which(befehl):
            subprocess.Popen([befehl, str(pfad)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
    except OSError:
        pass
    return False


class Oberflaeche:
    """Zustand der Oberfläche: Ordner der Projekte und Excel-Vorlage."""

    def __init__(self, projekte: Path, vorlage: Path, oeffner: Any = oeffne_im_system) -> None:
        self.projekte, self.vorlage, self.oeffner = Path(projekte), Path(vorlage), oeffner

    def liste(self) -> list[tuple[str, str]]:
        if not self.projekte.is_dir():
            return []
        ordner = sorted((p for p in self.projekte.iterdir() if p.is_dir()), key=lambda p: -p.stat().st_mtime)
        return [(p.name, datetime.fromtimestamp(p.stat().st_mtime).strftime("%d.%m.%Y %H:%M")) for p in ordner]

    def pruefe_name(self, name: str) -> str:
        if not RE_NAME.match(name):
            return "Name bitte nur aus Buchstaben, Ziffern, _ und - (ohne Leerzeichen), höchstens 60 Zeichen – z. B. Kunde_Anlage1"
        if name.upper() in WINDOWS_RESERVIERT:
            return f"„{name}“ ist unter Windows ein reservierter Name – bitte einen anderen wählen, z. B. {name}_1"
        return ""

    def neu(self, name: str) -> tuple[bool, str]:
        name = name.strip()
        if fehler := self.pruefe_name(name):
            return False, fehler
        ordner = self.projekte / name
        if ordner.exists():
            return False, f"Das Projekt „{name}“ gibt es schon – bitte einen anderen Namen wählen oder es in der Liste öffnen."
        try:
            ordner.mkdir(parents=True)
            shutil.copy2(self.vorlage, ordner / f"{name}.xlsx")
        except OSError as e:
            return False, (f"Projekt konnte nicht angelegt werden ({e.strerror or type(e).__name__}) – Schreibrechte im Ordner "
                           f"{self.projekte} prüfen oder das Programm in einen eigenen Ordner (z. B. C:\\slpgen) entpacken.")
        return True, name

    # ---- Seiten --------------------------------------------------------------------------------------------
    def startseite(self, fehler: str = "", eingabe: str = "") -> bytes:
        projekte = self.liste()
        zeilen = "".join(f'<tr><td><a href="/projekt/{urllib.parse.quote(n)}">{html.escape(n)}</a></td><td>{d}</td>'
                         f'<td><a class="knopf zweit" href="/projekt/{urllib.parse.quote(n)}">Öffnen</a></td></tr>'
                         for n, d in projekte)
        tabelle = (f"<table><thead><tr><th>Projekt</th><th>zuletzt geändert</th><th></th></tr></thead><tbody>{zeilen}"
                   "</tbody></table>") if projekte else "<p>Noch keine Projekte – legen Sie oben Ihr erstes an.</p>"
        fehlertext = (f'<p class="feldfehler" id="namefehler" role="alert">{html.escape(fehler)}</p>' if fehler else "")
        feld_aria = ' aria-invalid="true" aria-describedby="namefehler" autofocus' if fehler else ""
        return _seite("Fehler: Projekt anlegen" if fehler else "Start", f"""<h2>Neues Projekt</h2>
<form method="post" action="/projekt/neu"><label for="name">Projektname</label>
<a class="hilfe" href="/hilfe/projekt" aria-label="Hilfe zu Projekt anlegen">?</a><br>
<input type="text" id="name" name="name" value="{html.escape(eingabe)}" placeholder="z. B. Kunde_Anlage1" required
 maxlength="60" pattern="[A-Za-z0-9ÄÖÜäöüß_\\-]+" title="Buchstaben, Ziffern, _ und -"{feld_aria}>
<button class="knopf" type="submit">Projekt anlegen</button>{fehlertext}</form>
<h2>Ihre Projekte</h2>{tabelle}""")

    def projektseite(self, name: str, meldung: str = "", fehler: bool = False) -> bytes | None:
        if self.pruefe_name(name) or not (self.projekte / name).is_dir():
            return None
        q = urllib.parse.quote(name)
        excel = self.projekte / name / f"{name}.xlsx"
        oeffnen = (f'<form class="inline" method="post" action="/projekt/{q}/oeffnen"><input type="hidden" name="was" '
                   f'value="excel"><button class="knopf" type="submit"{"" if excel.exists() else " disabled"}>Excel öffnen'
                   f'</button></form> <form class="inline" method="post" action="/projekt/{q}/oeffnen"><input type="hidden" '
                   f'name="was" value="ordner"><button class="knopf zweit" type="submit">Ordner öffnen</button></form>')
        punkte = []
        for i, (t, b) in enumerate(SCHRITTE, 1):
            klasse = "erledigt" if i <= FERTIG_BIS else "folgt"
            zusatz = ""
            if i == 1:
                zusatz = (f"<p>Excel-Vorlage: <strong>{html.escape(str(excel))}</strong></p>{oeffnen}"
                          "<p>Nächster Schritt: Excel ausfüllen und speichern. Den Plan erzeugen Sie bis zur nächsten Version "
                          "im Menüfenster des Programms mit Punkt 3 – die Ergebnisse landen im Unterordner ausgabe.</p>")
            elif klasse == "folgt":
                zusatz = '<p class="merkmal">folgt</p>'
            punkte.append(f'<li class="{klasse}"><strong>{html.escape(t)}</strong><br>{html.escape(b)}{zusatz}</li>')
        hinweis = (f'<p class="meldung{" fehler" if fehler else ""}" role="{"alert" if fehler else "status"}">'
                   f'{html.escape(meldung)}</p>' if meldung else "")
        return _seite(f"Projekt {name}", f"""<p><a href="/">← Alle Projekte</a></p><h2>Projekt {html.escape(name)}</h2>
{hinweis}<p class="merkmal">Schritte mit „folgt“ sind in der Oberfläche noch nicht fertig – bis dahin im Menüfenster des
Programms.</p><ol class="schritte">{"".join(punkte)}</ol>""")

    def oeffne(self, name: str, was: str) -> tuple[bool, str]:
        if self.pruefe_name(name) or not (self.projekte / name).is_dir():
            return False, "Projekt nicht gefunden"
        ziel = self.projekte / name / f"{name}.xlsx" if was == "excel" else self.projekte / name
        if not ziel.exists():
            return False, f"{ziel.name} fehlt im Projektordner – Projekt neu anlegen oder Datei hineinkopieren."
        if self.oeffner(ziel):
            return True, f"{'Excel-Datei' if was == 'excel' else 'Ordner'} wird geöffnet: {ziel}"
        return False, f"Konnte nicht automatisch geöffnet werden – bitte im Explorer öffnen: {ziel}"

    def hilfeseite(self, thema: str) -> bytes | None:
        if thema not in HILFE:
            return None
        titel, text = HILFE[thema]
        return _seite(f"Hilfe: {titel}", f'<h2>Hilfe: {html.escape(titel)}</h2><p>{html.escape(text)}</p>'
                                         f'<p><a href="/">Zurück zum Start</a></p>', None)


def _handler(o: Oberflaeche, erlaubte_hosts: set[str]) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "slpgen"

        def _host_ok(self) -> bool:
            return self.headers.get("Host", "") in erlaubte_hosts

        def _senden(self, code: int, inhalt: bytes, typ: str = "text/html; charset=utf-8") -> None:
            self.send_response(code)
            self.send_header("Content-Type", typ)
            self.send_header("Content-Length", str(len(inhalt)))
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'")
            self.end_headers()
            self.wfile.write(inhalt)

        def _weiter(self, ziel: str) -> None:               # nach POST immer weiterleiten (kein erneutes Senden bei F5)
            self.send_response(303)
            self.send_header("Location", ziel)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self) -> None:                    # Name von http.server vorgegeben
            if not self._host_ok():
                self._senden(403, b"Zugriff nur von diesem PC")
                return
            teile = urllib.parse.urlsplit(self.path)
            pfad, abfrage = urllib.parse.unquote(teile.path), urllib.parse.parse_qs(teile.query)
            seite: bytes | None = None
            if pfad == "/":
                seite = o.startseite()
            elif pfad.startswith("/hilfe/"):
                seite = o.hilfeseite(pfad[len("/hilfe/"):])
            elif pfad.startswith("/projekt/"):
                name = pfad[len("/projekt/"):]
                meldung = (abfrage.get("m") or [""])[0]
                if "neu" in abfrage:
                    meldung = f"Projekt „{name}“ angelegt."
                seite = o.projektseite(name, meldung, "f" in abfrage)
            if seite is None:
                self._senden(404, _seite("Nicht gefunden", '<p>Diese Seite gibt es nicht. <a href="/">Zum Start</a></p>'))
            else:
                self._senden(200, seite)

        def do_POST(self) -> None:
            herkunft = self.headers.get("Origin")
            if not self._host_ok() or (herkunft and urllib.parse.urlsplit(herkunft).netloc not in erlaubte_hosts):
                self._senden(403, b"Zugriff nur von diesem PC")
                return
            laenge = min(int(self.headers.get("Content-Length") or 0), 10_000)
            daten = urllib.parse.parse_qs(self.rfile.read(laenge).decode("utf-8", "replace"))
            pfad = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path)
            if pfad == "/projekt/neu":
                eingabe = (daten.get("name") or [""])[0]
                ok, text = o.neu(eingabe)
                if ok:
                    self._weiter(f"/projekt/{urllib.parse.quote(text)}?neu=1")
                else:
                    self._senden(400, o.startseite(text, eingabe))
            elif pfad.startswith("/projekt/") and pfad.endswith("/oeffnen"):
                name = pfad[len("/projekt/"):-len("/oeffnen")]
                ok, text = o.oeffne(name, (daten.get("was") or [""])[0])
                self._weiter(f"/projekt/{urllib.parse.quote(name)}?" + urllib.parse.urlencode({"m": text, **({} if ok else {"f": 1})}))
            else:
                self._senden(404, _seite("Nicht gefunden", '<p><a href="/">Zum Start</a></p>'))

        def log_message(self, *args: Any) -> None:     # keine Konsolenausgabe je Anfrage
            pass

    return Handler


def starte(projekte: Path, vorlage: Path, port: int = 0, oeffner: Any = oeffne_im_system) -> ThreadingHTTPServer:
    """Server auf 127.0.0.1 starten (Port 0 = freier Port); läuft in einem Hintergrund-Thread."""
    server = ThreadingHTTPServer(("127.0.0.1", port), BaseHTTPRequestHandler)
    p = server.server_address[1]
    server.RequestHandlerClass = _handler(Oberflaeche(projekte, vorlage, oeffner), {f"127.0.0.1:{p}", f"localhost:{p}"})
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def oeffnen(server: ThreadingHTTPServer) -> str:
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    webbrowser.open(url)
    return url
