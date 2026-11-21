"""M10a: Anwender-Oberfläche – End-to-End per HTTP (Server auf 127.0.0.1, Startseite, Projekt anlegen, Hilfe, Schutz)."""
import http.client
import urllib.parse
from pathlib import Path

import pytest

from slpgen.oberflaeche import starte

VORLAGE = Path(__file__).resolve().parent.parent / "beispiele" / "Projekt_Vorlage.xlsx"


@pytest.fixture
def server(tmp_path):
    s = starte(tmp_path / "meine_projekte", VORLAGE)
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
    return r.status, r.read().decode("utf-8")


def test_nur_lokal_gebunden(server):
    s, _ = server
    assert s.server_address[0] == "127.0.0.1"


def test_startseite_mit_sechs_schritten_und_hilfe(server):
    s, _ = server
    code, text = _anfrage(s, "GET", "/")
    assert code == 200 and text.count('<li class=') == 6 and "Projekt anlegen" in text and "PDF und Listen herunterladen" in text
    assert 'href="/hilfe/start"' in text and "<script" not in text and "http://" not in text.split("</style>")[1]
    code, text = _anfrage(s, "GET", "/hilfe/projekt")
    assert code == 200 and "meine_projekte" in text
    assert _anfrage(s, "GET", "/hilfe/gibtsnicht")[0] == 404


def test_projekt_anlegen_ende_zu_ende(server):
    s, ordner = server
    code, text = _anfrage(s, "POST", "/projekt/neu", {"name": "Kunde_Anlage1"})
    assert code == 200 and "angelegt" in text and (ordner / "Kunde_Anlage1" / "Kunde_Anlage1.xlsx").is_file()
    assert "Kunde_Anlage1" in _anfrage(s, "GET", "/")[1]                      # erscheint in der Projektliste
    code, text = _anfrage(s, "POST", "/projekt/neu", {"name": "Kunde_Anlage1"})
    assert code == 400 and "gibt es schon" in text


@pytest.mark.parametrize("name", ["../boese", "a b", "", "x" * 61, "C:\\temp", "con/nul"])
def test_projektname_ohne_pfad(server, name):
    s, ordner = server
    code, text = _anfrage(s, "POST", "/projekt/neu", {"name": name})
    assert code == 400 and "nur aus Buchstaben" in text
    assert not (ordner.parent / "boese").exists()


def test_fremder_host_und_fremde_herkunft_abgewiesen(server):
    """Schutz gegen DNS-Rebinding und Formular-Angriffe aus fremden Webseiten."""
    s, ordner = server
    assert _anfrage(s, "GET", "/", host="angreifer.example")[0] == 403
    code, _ = _anfrage(s, "POST", "/projekt/neu", {"name": "X1"}, origin="http://angreifer.example")
    assert code == 403 and not (ordner / "X1").exists()
