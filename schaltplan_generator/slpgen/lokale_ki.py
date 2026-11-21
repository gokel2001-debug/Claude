"""Lokale KI (M6a, P8): KI-Auftrag an einen Ollama-Server senden, Antwort als KI-Antwort speichern.

Die Antwort durchläuft danach dieselbe Prüfung wie eine Chat-Antwort (`pruefen`/`generieren`). Standard ist der
Ollama-Server auf diesem PC (http://localhost:11434); ein anderer Rechner nur ausdrücklich (fremder_server=True).
Ein eingestellter Proxy wird umgangen, damit das Lastenheft den PC nicht verlässt.
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
KONTEXT_TOKENS = 16384                  # ANNAHME A46: Standard-Kontext von Ollama (2048/4096) ist für den Auftrag zu klein
LOKAL = {"localhost", "127.0.0.1", "::1"}


def ist_lokal(server: str) -> bool:
    from urllib.parse import urlparse
    return (urlparse(server).hostname or "") in LOKAL


def frage_lokale_ki(auftrag: str, server: str, modell: str = STANDARD_MODELL, zeitlimit_s: float = ZEITLIMIT_S,
                    fremder_server: bool = False) -> str:
    """-> Antworttext der lokalen KI. Fehler im Klartext (Server nicht erreichbar, Modell fehlt, Zeitlimit, gekürzt)."""
    if not ist_lokal(server) and not fremder_server:
        raise RegelFehler(f"{server} ist nicht dieser PC – das Lastenheft würde den Rechner verlassen. Nur mit "
                          f"ausdrücklicher Freigabe (--fremder-server) zulässig")
    url = server.rstrip("/") + "/api/generate"
    body = json.dumps({"model": modell, "prompt": auftrag, "stream": False,
                       "options": {"temperature": 0, "seed": 0, "num_ctx": KONTEXT_TOKENS}}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    ohne_proxy = urllib.request.build_opener(urllib.request.ProxyHandler({}))   # Proxy nie verwenden (Vertraulichkeit)
    try:
        with ohne_proxy.open(req, timeout=zeitlimit_s) as antwort:
            daten = json.loads(antwort.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            grund = json.loads(e.read().decode("utf-8")).get("error", "")
        except (ValueError, AttributeError):
            grund = ""
        hinweis = f" – Modell „{modell}“ vorhanden? (ollama pull {modell})" if e.code == 404 else ""
        raise RegelFehler(f"Lokale KI meldet Fehler {e.code}{': ' + grund if grund else ''}{hinweis}") from None
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
    if isinstance(daten, dict) and daten.get("done_reason") == "length":
        raise RegelFehler("Antwort der lokalen KI wurde abgeschnitten (Längengrenze) – Lastenheft kürzen oder Modell mit "
                          "größerem Kontext verwenden")
    text = daten.get("response") if isinstance(daten, dict) else None
    if not isinstance(text, str) or not text.strip():
        raise RegelFehler("Lokale KI hat eine leere Antwort geliefert")
    return text
