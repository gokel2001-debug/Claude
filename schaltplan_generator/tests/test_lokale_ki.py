"""M6a: lokale KI (Ollama) – Lastenheft -> Auftrag -> lokale KI (Attrappe) -> gültige YAML -> Plan."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from slpgen.cli import main
from slpgen.lokale_ki import frage_lokale_ki
from slpgen.modell import RegelFehler

B = Path(__file__).resolve().parent.parent / "beispiele"
ROHANTWORT = (B / "ki_antwort_roh_2026-11-20.txt").read_text(encoding="utf-8")


def _server(antwort, status=200, empfangen=None):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            daten = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if empfangen is not None:
                empfangen.append(daten)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(antwort if isinstance(antwort, bytes) else json.dumps(antwort).encode())

        def log_message(self, *args):
            pass

    srv = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_port}"


def test_lastenheft_ueber_lokale_ki_zum_plan(tmp_path, capsys):
    empfangen = []
    srv, url = _server({"model": "x", "response": ROHANTWORT, "done": True}, empfangen=empfangen)
    try:
        lh = tmp_path / "lastenheft.md"
        lh.write_text((B / "lastenheft_beispiel.md").read_text(encoding="utf-8"), encoding="utf-8")
        main(["ki-auftrag", str(lh), "--ollama", url, "--modell", "testmodell"])
    finally:
        srv.shutdown()
    assert empfangen[0]["model"] == "testmodell" and empfangen[0]["stream"] is False
    assert "### LASTENHEFT" in empfangen[0]["prompt"] and empfangen[0]["options"]["temperature"] == 0
    antwort = tmp_path / "lastenheft_projektmodell.yaml"
    assert antwort.exists() and "gespeichert" in capsys.readouterr().out
    main(["pruefen", str(antwort)])
    main(["generieren", str(antwort), "--profil", str(tmp_path / "x.yaml")])
    assert (tmp_path / "ausgabe" / "P-2026-017_Stromlaufplan_Hausstil.pdf").exists()


@pytest.mark.parametrize("antwort, status, meldung", [
    ({"error": "model not found"}, 404, "ollama pull"),
    (b"kein json", 200, "kein gültiges JSON"),
    ({"response": ""}, 200, "leere Antwort"),
])
def test_fehler_der_lokalen_ki_klartext(antwort, status, meldung):
    srv, url = _server(antwort, status)
    try:
        with pytest.raises(RegelFehler, match=meldung):
            frage_lokale_ki("x", url, "m")
    finally:
        srv.shutdown()


def test_server_nicht_erreichbar():
    with pytest.raises(RegelFehler, match="nicht erreichbar"):
        frage_lokale_ki("x", "http://127.0.0.1:9", "m", zeitlimit_s=2)
