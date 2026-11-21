"""Lokale KI (M6a, P8): KI-Auftrag an einen Ollama-Server senden, Antwort als KI-Antwort speichern.

Die Antwort durchläuft danach dieselbe Prüfung wie eine Chat-Antwort (`pruefen`/`generieren`). Es verlässt nichts
den eigenen Rechner bzw. das eigene Netz (Server-Adresse z. B. http://localhost:11434).
ANNAHME A46: Ollama-Schnittstelle POST /api/generate mit {"model", "prompt", "stream": false} liefert JSON mit
"response" (laut Ollama-API-Dokumentation; in dieser Umgebung nicht gegen einen echten Server geprüft – PC5).
"""
from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request

from .modell import RegelFehler

STANDARD_MODELL = "qwen2.5:7b"          # ANNAHME A46: Modellwahl am PC erproben (PC5)
ZEITLIMIT_S = 600


def frage_lokale_ki(auftrag: str, server: str, modell: str = STANDARD_MODELL, zeitlimit_s: float = ZEITLIMIT_S) -> str:
    """-> Antworttext der lokalen KI. Fehler im Klartext (Server nicht erreichbar, Modell fehlt, Zeitlimit)."""
    url = server.rstrip("/") + "/api/generate"
    body = json.dumps({"model": modell, "prompt": auftrag, "stream": False,
                       "options": {"temperature": 0}}).encode("utf-8")       # reproduzierbar: keine Zufallsstreuung
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=zeitlimit_s) as antwort:
            daten = json.loads(antwort.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        hinweis = f" – Modell „{modell}“ vorhanden? (ollama pull {modell})" if e.code == 404 else ""
        raise RegelFehler(f"Lokale KI meldet Fehler {e.code}{hinweis}") from None
    except (urllib.error.URLError, ConnectionError) as e:
        if isinstance(getattr(e, "reason", None), socket.timeout):
            raise RegelFehler(f"Lokale KI antwortet nicht innerhalb von {zeitlimit_s:g} s – kleineres Modell oder "
                              f"kürzeres Lastenheft") from None
        raise RegelFehler(f"Lokale KI unter {server} nicht erreichbar – läuft Ollama? (Programm starten)") from None
    except TimeoutError:
        raise RegelFehler(f"Lokale KI antwortet nicht innerhalb von {zeitlimit_s:g} s – kleineres Modell oder "
                          f"kürzeres Lastenheft") from None
    except json.JSONDecodeError:
        raise RegelFehler("Antwort der lokalen KI ist kein gültiges JSON – Server-Adresse prüfen") from None
    text = daten.get("response") if isinstance(daten, dict) else None
    if not isinstance(text, str) or not text.strip():
        raise RegelFehler("Lokale KI hat eine leere Antwort geliefert")
    return text
