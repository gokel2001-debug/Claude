"""M10a: Anwender-Oberfläche – End-to-End per HTTP (Server auf 127.0.0.1, Startseite, Projekt anlegen, Hilfe, Schutz)."""
import http.client
import urllib.parse
from pathlib import Path

import pytest

from slpgen.oberflaeche import starte

VORLAGE = Path(__file__).resolve().parent.parent / "beispiele" / "Projekt_Vorlage.xlsx"


GEOEFFNET: list = []


@pytest.fixture
def server(tmp_path):
    GEOEFFNET.clear()
    s = starte(tmp_path / "meine_projekte", VORLAGE, oeffner=lambda p: GEOEFFNET.append(p) or True)
    yield s, tmp_path / "meine_projekte"
    s.shutdown()


def _anfrage(server, methode, pfad, daten=None, host=None, origin=None):
    port = server.server_address[1]
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    kopf = {"Host": host or f"127.0.0.1:{port}"}
    if origin:
        kopf["Origin"] = origin
    rumpf = urllib.parse.urlencode(daten) if daten is not None else None
    if rumpf is not None:
        kopf["Content-Type"] = "application/x-www-form-urlencoded"
    c.request(methode, pfad, body=rumpf, headers=kopf)
    r = c.getresponse()
    return r.status, r.read().decode("utf-8") or r.getheader("Location", "")


def test_nur_lokal_gebunden(server):
    s, _ = server
    assert s.server_address[0] == "127.0.0.1"


def test_startseite_und_hilfe(server):
    s, _ = server
    code, text = _anfrage(s, "GET", "/")
    assert code == 200 and "Neues Projekt" in text and "Noch keine Projekte" in text and 'href="/hilfe/start"' in text
    assert "<script" not in text and "http://" not in text.split("</style>")[1]
    code, text = _anfrage(s, "GET", "/hilfe/start")
    assert code == 200 and "Fenster" in text and 'class="hilfe"' not in text.split("<main>")[0]   # kein ? auf Hilfeseite
    assert _anfrage(s, "GET", "/hilfe/gibtsnicht")[0] == 404


def test_projekt_anlegen_weiterleiten_oeffnen(server):
    """M10a + Prüfung (UX 2/3, Einsteiger 1/4/6): Weiterleitung auf Projektseite, Schrittleiste, Excel/Ordner öffnen."""
    s, ordner = server
    code, ort = _anfrage(s, "POST", "/projekt/neu", {"name": "Kunde_Anlage1"})
    assert code == 303 and ort == "/projekt/Kunde_Anlage1?neu=1" and (ordner / "Kunde_Anlage1" / "Kunde_Anlage1.xlsx").is_file()
    code, text = _anfrage(s, "GET", ort)
    assert code == 200 and "angelegt" in text and text.count("<li class=") == 6 and text.count('class="folgt"') == 5
    assert "Excel öffnen" in text and "Nächster Schritt" in text
    code, ort = _anfrage(s, "POST", "/projekt/Kunde_Anlage1/oeffnen", {"was": "excel"})
    assert code == 303 and GEOEFFNET[-1] == ordner / "Kunde_Anlage1" / "Kunde_Anlage1.xlsx"
    _anfrage(s, "POST", "/projekt/Kunde_Anlage1/oeffnen", {"was": "ordner"})
    assert GEOEFFNET[-1] == ordner / "Kunde_Anlage1"
    assert 'href="/projekt/Kunde_Anlage1"' in _anfrage(s, "GET", "/")[1]                # Liste mit Öffnen
    code, text = _anfrage(s, "POST", "/projekt/neu", {"name": "Kunde_Anlage1"})
    assert code == 400 and "gibt es schon" in text and 'value="Kunde_Anlage1"' in text and 'aria-invalid="true"' in text
    assert _anfrage(s, "GET", "/projekt/gibtsnicht")[0] == 404
    assert _anfrage(s, "GET", "/projekt/..%2F..%2Fetc")[0] == 404


@pytest.mark.parametrize("name", ["../boese", "a b", "", "x" * 61, "C:\\temp", "con/nul", "CON", "lpt1"])
def test_projektname_ohne_pfad(server, name):
    s, ordner = server
    code, text = _anfrage(s, "POST", "/projekt/neu", {"name": name})
    assert code == 400 and ("nur aus Buchstaben" in text or "reservierter Name" in text)
    assert not (ordner.parent / "boese").exists()


def test_fremder_host_und_fremde_herkunft_abgewiesen(server):
    """Schutz gegen DNS-Rebinding und Formular-Angriffe aus fremden Webseiten."""
    s, ordner = server
    assert _anfrage(s, "GET", "/", host="angreifer.example")[0] == 403
    code, _ = _anfrage(s, "POST", "/projekt/neu", {"name": "X1"}, origin="http://angreifer.example")
    assert code == 403 and not (ordner / "X1").exists()
