"""Anwender-Oberfläche (ZIEL 4a/4b, Meilenstein M10, Entscheidung E19): lokaler Webserver nur auf 127.0.0.1.

Keine Internetverbindung, keine externen Dateien (kein CDN), nur Python-Standardbibliothek – läuft unverändert
im PyInstaller-Paket. Die Oberfläche ruft denselben Planungskern auf wie Menü und Kommandozeile.

M10a (dieses Paket): Grundgerüst, Startseite mit geführtem Ablauf in 6 Schritten, Schritt 1 „Projekt anlegen“
(Projektordner mit Excel-Vorlage), Hilfe-Seiten (Fragezeichen). Schritte 2–6 folgen in M10b–M10d.

Sicherheit: nur 127.0.0.1; Anfragen mit fremdem Host-Kopf (DNS-Rebinding) oder fremder Herkunft (Origin) bei
POST werden abgewiesen; Projektnamen nur aus Buchstaben, Ziffern, _ und - (kein Pfad).
"""
from __future__ import annotations

import html
import re
import shutil
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

RE_NAME = re.compile(r"^[A-Za-z0-9ÄÖÜäöüß_-]{1,60}$")

SCHRITTE = [
    ("Projekt anlegen", "Ein Projekt ist ein Ordner mit allen Eingaben und Ergebnissen. Kopieren = sichern.", True),
    ("Unterlagen laden", "Lastenheft, Feldgeräteliste (Excel) oder Antwort des KI-Chats hochladen.", False),
    ("Rückfragen und Annahmen prüfen", "Fehlende Angaben und Annahmen der Software im Klartext bestätigen oder ändern.", False),
    ("Plan erzeugen", "Stromlaufplan im Hausstil mit Stückliste, Klemmenplan und Kabelliste.", False),
    ("Prüfbericht ansehen", "Was die Software geprüft hat – Fehler verhindern die Freigabe zur Fertigung.", False),
    ("PDF und Listen herunterladen", "Ergebnisse liegen im Projektordner und hier zum Herunterladen.", False),
]

HILFE = {
    "start": ("So arbeiten Sie mit dem Programm",
              "Gehen Sie die Schritte 1 bis 6 von oben nach unten durch. Jeder Schritt zeigt, was er braucht. "
              "Alles bleibt auf diesem PC – es wird nichts ins Internet geschickt. Das alte Menüfenster "
              "(start.bat) funktioniert weiter, falls Sie es lieber nutzen."),
    "projekt": ("Projekt anlegen",
                "Geben Sie einen kurzen Namen ein, z. B. Kunde_Anlage1 (nur Buchstaben, Ziffern, _ und -). "
                "Das Programm legt den Ordner meine_projekte\\<Name> an und legt eine Excel-Vorlage hinein. "
                "Diesen Ordner können Sie kopieren, um das Projekt zu sichern."),
}

STIL = """
:root{--text:#1b1f24;--grund:#ffffff;--leicht:#f2f4f7;--rand:#c9d0d8;--akzent:#0b5cad;--gut:#1d7a3a;--schlecht:#b3261e}
@media (prefers-color-scheme:dark){:root{--text:#e8eaed;--grund:#16181c;--leicht:#22262c;--rand:#3a4048;--akzent:#7ab4ff;
--gut:#6fd08c;--schlecht:#ff8a80}}
*{box-sizing:border-box}body{margin:0;font:16px/1.5 system-ui,Segoe UI,Arial,sans-serif;color:var(--text);background:var(--grund)}
header{padding:14px 20px;border-bottom:1px solid var(--rand);display:flex;justify-content:space-between;align-items:center}
header h1{font-size:20px;margin:0}main{max-width:920px;margin:0 auto;padding:20px}
a{color:var(--akzent)}.hilfe{font-weight:700;text-decoration:none;border:1px solid var(--rand);border-radius:50%;
display:inline-block;width:28px;height:28px;text-align:center;line-height:26px}
ol.schritte{list-style:none;padding:0;counter-reset:s}ol.schritte li{counter-increment:s;border:1px solid var(--rand);
border-radius:8px;padding:12px 14px 12px 56px;margin:10px 0;position:relative;background:var(--leicht)}
ol.schritte li::before{content:counter(s);position:absolute;left:14px;top:12px;width:30px;height:30px;border-radius:50%;
background:var(--akzent);color:var(--grund);text-align:center;line-height:30px;font-weight:700}
ol.schritte li.spaeter{opacity:.65}ol.schritte li.spaeter::before{background:var(--rand);color:var(--text)}
.knopf{background:var(--akzent);color:var(--grund);border:0;border-radius:6px;padding:9px 16px;font-size:16px;cursor:pointer}
input[type=text]{font-size:16px;padding:8px;border:1px solid var(--rand);border-radius:6px;width:min(100%,360px);
background:var(--grund);color:var(--text)}
.meldung{border-left:4px solid var(--gut);padding:8px 12px;background:var(--leicht);margin:12px 0}
.meldung.fehler{border-color:var(--schlecht)}table{border-collapse:collapse;width:100%}
td,th{border-bottom:1px solid var(--rand);padding:6px 8px;text-align:left}
"""


def _seite(titel: str, inhalt: str, hilfe: str = "start") -> bytes:
    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(titel)} – Stromlaufplan-Generator</title>
<style>{STIL}</style></head><body><header><h1><a href="/" style="color:inherit;text-decoration:none">Stromlaufplan-Generator</a>
<span style="font-weight:400;font-size:14px"> · Prototyp, Pläne nicht zur Fertigung freigegeben</span></h1>
<a class="hilfe" href="/hilfe/{hilfe}" title="Hilfe zu dieser Seite" aria-label="Hilfe zu dieser Seite">?</a></header>
<main>{inhalt}</main></body></html>""".encode()


class Oberflaeche:
    """Zustand der Oberfläche: Ordner der Projekte und Excel-Vorlage."""

    def __init__(self, projekte: Path, vorlage: Path) -> None:
        self.projekte, self.vorlage = Path(projekte), Path(vorlage)

    def liste(self) -> list[str]:
        if not self.projekte.is_dir():
            return []
        return sorted(p.name for p in self.projekte.iterdir() if p.is_dir())

    def neu(self, name: str) -> tuple[bool, str]:
        name = name.strip()
        if not RE_NAME.match(name):
            return False, ("Name bitte nur aus Buchstaben, Ziffern, _ und - (ohne Leerzeichen), höchstens 60 Zeichen – "
                           "z. B. Kunde_Anlage1")
        ordner = self.projekte / name
        if ordner.exists():
            return False, f"Das Projekt „{name}“ gibt es schon – bitte einen anderen Namen wählen oder es unten öffnen."
        ordner.mkdir(parents=True)
        shutil.copy2(self.vorlage, ordner / f"{name}.xlsx")
        return True, f"Projekt „{name}“ angelegt: Ordner {ordner} mit der Excel-Vorlage {name}.xlsx."

    # ---- Seiten --------------------------------------------------------------------------------------------
    def startseite(self, meldung: str = "", fehler: bool = False) -> bytes:
        formular = """<form method="post" action="/projekt/neu" style="margin-top:8px"><label for="name">Projektname</label>
<a class="hilfe" href="/hilfe/projekt" aria-label="Hilfe zu Projekt anlegen">?</a><br>
<input type="text" id="name" name="name" placeholder="z. B. Kunde_Anlage1" required maxlength="60"
 pattern="[A-Za-z0-9ÄÖÜäöüß_\\-]+" title="Buchstaben, Ziffern, _ und -">
<button class="knopf" type="submit">Projekt anlegen</button></form>"""
        schritte = "".join(
            f'<li class="{"" if aktiv else "spaeter"}"><strong>{html.escape(t)}</strong><br>{html.escape(b)}'
            + (formular if i == 0 else "")
            + ("" if aktiv else "<br><em>kommt in einer der nächsten Versionen – bis dahin Menüfenster (start.bat)</em>")
            + "</li>" for i, (t, b, aktiv) in enumerate(SCHRITTE))
        hinweis = f'<p class="meldung{" fehler" if fehler else ""}" role="status">{html.escape(meldung)}</p>' if meldung else ""
        projekte = self.liste()
        tabelle = ("<table><thead><tr><th>Projekt</th><th>Ordner</th></tr></thead><tbody>" + "".join(
            f"<tr><td>{html.escape(p)}</td><td>{html.escape(str(self.projekte / p))}</td></tr>" for p in projekte)
            + "</tbody></table>") if projekte else "<p>Noch keine Projekte.</p>"
        return _seite("Start", f"""<h2>Geführter Ablauf</h2>{hinweis}
<ol class="schritte">{schritte}</ol>
<h2>Ihre Projekte</h2>{tabelle}""")

    def hilfeseite(self, thema: str) -> bytes | None:
        if thema not in HILFE:
            return None
        titel, text = HILFE[thema]
        return _seite(f"Hilfe: {titel}", f'<h2>Hilfe: {html.escape(titel)}</h2><p>{html.escape(text)}</p>'
                                         f'<p><a href="/">Zurück zum Start</a></p>', thema)


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

        def do_GET(self) -> None:                    # Name von http.server vorgegeben
            if not self._host_ok():
                self._senden(403, b"Zugriff nur von diesem PC")
                return
            pfad = urllib.parse.urlsplit(self.path).path
            if pfad == "/":
                self._senden(200, o.startseite())
            elif pfad.startswith("/hilfe/") and (s := o.hilfeseite(pfad[len("/hilfe/"):])):
                self._senden(200, s)
            else:
                self._senden(404, _seite("Nicht gefunden", '<p>Diese Seite gibt es nicht. <a href="/">Zum Start</a></p>'))

        def do_POST(self) -> None:
            herkunft = self.headers.get("Origin")
            if not self._host_ok() or (herkunft and urllib.parse.urlsplit(herkunft).netloc not in erlaubte_hosts):
                self._senden(403, b"Zugriff nur von diesem PC")
                return
            laenge = min(int(self.headers.get("Content-Length") or 0), 10_000)
            daten = urllib.parse.parse_qs(self.rfile.read(laenge).decode("utf-8", "replace"))
            if urllib.parse.urlsplit(self.path).path == "/projekt/neu":
                ok, text = o.neu((daten.get("name") or [""])[0])
                self._senden(200 if ok else 400, o.startseite(text, fehler=not ok))
            else:
                self._senden(404, _seite("Nicht gefunden", '<p><a href="/">Zum Start</a></p>'))

        def log_message(self, *args: Any) -> None:     # keine Konsolenausgabe je Anfrage
            pass

    return Handler


def starte(projekte: Path, vorlage: Path, port: int = 0) -> ThreadingHTTPServer:
    """Server auf 127.0.0.1 starten (Port 0 = freier Port); läuft in einem Hintergrund-Thread."""
    server = ThreadingHTTPServer(("127.0.0.1", port), BaseHTTPRequestHandler)
    p = server.server_address[1]
    server.RequestHandlerClass = _handler(Oberflaeche(projekte, vorlage), {f"127.0.0.1:{p}", f"localhost:{p}"})
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def oeffnen(server: ThreadingHTTPServer) -> str:
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    webbrowser.open(url)
    return url
