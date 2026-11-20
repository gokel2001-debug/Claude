"""Lernschleife (M5c, ZIEL 4c): Korrektur erfassen -> Hausregel mit Herkunft/Datum/Geltung -> wirkt beim nächsten
Plan -> Regressionstest.

Hausregeln liegen lokal in `hausprofil/hausregeln.yaml` (vertraulich, nie im Repository). Jede Regel ändert das
Projektmodell VOR der Planung (Schicht A -> B) und wird im Auslegungsnachweis genannt. Zu jeder Regel wird der
Fall gespeichert, an dem sie erfasst wurde (Eingabe-Ausschnitt + erwartetes Ergebnis); `pruefe_regressionen`
spielt alle Fälle erneut durch und meldet, wenn eine spätere Regel einen früheren Fall verändert.

Regelarten (Grundgerüst, erweiterbar):
  artikel_ersetzen  wenn ein Feldgerät Artikel `wenn` hat, wird `dann` eingesetzt (z. B. Hausstandard-Hersteller)
  gruppe_setzen     Feldgeräte mit Artikel `wenn` bekommen die 24-V-Gruppe `dann`
"""
from __future__ import annotations

import copy
import datetime as dt
from pathlib import Path
from typing import Any

import yaml

from .modell import RegelFehler

ARTEN = {"artikel_ersetzen": "Artikel ersetzen", "gruppe_setzen": "24-V-Gruppe setzen"}


def lade_regeln(pfad: str | Path) -> list[dict[str, Any]]:
    p = Path(pfad)
    if not p.is_file():
        return []
    try:
        daten = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        raise RegelFehler(f"{p.name} ist beschädigt – Sicherung {p.name}.bak zurückkopieren") from None
    return list(daten.get("regeln", []))


def speichere_regeln(pfad: str | Path, regeln: list[dict[str, Any]]) -> None:
    p = Path(pfad)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        p.with_name(p.name + ".bak").write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
    p.write_text("# Hausregeln aus Korrekturen – VERTRAULICH, nur lokal\n"
                 + yaml.safe_dump({"regeln": regeln}, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _gilt(regel: dict[str, Any], stichtag: str | None) -> bool:
    ab = str(regel.get("gilt_ab", ""))
    return not ab or not stichtag or str(stichtag) >= ab


def wende_an(projekt: dict[str, Any], regeln: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    """Regeln auf das Projektmodell anwenden. -> (geändertes Modell, Klartext je Änderung für den Nachweis)."""
    neu = copy.deepcopy(projekt)
    stichtag = str((neu.get("projekt") or {}).get("datum", "")) or None
    meldungen: list[str] = []
    for r in regeln:
        if not r.get("aktiv", True) or not _gilt(r, stichtag):
            continue
        for fg in neu.get("feldgeraete") or []:
            if not isinstance(fg, dict) or fg.get("artikel") != r["wenn"]:
                continue
            if r["art"] == "artikel_ersetzen":
                fg["artikel"] = r["dann"]
            elif r["art"] == "gruppe_setzen":
                fg["gruppe"] = r["dann"]
            else:
                continue
            meldungen.append(f"Hausregel {r['id']} ({ARTEN[r['art']]}): {fg.get('bmk')} {r['wenn']} → {r['dann']} "
                             f"– Herkunft: {r.get('herkunft', '?')}, {r.get('datum', '?')}")
    return neu, meldungen


def erfasse_korrektur(pfad: str | Path, art: str, wenn: str, dann: str, herkunft: str, grund: str,
                      projekt: dict[str, Any], stamm: dict[str, Any], gilt_ab: str | None = None) -> dict[str, Any]:
    """Korrektur als Hausregel speichern, samt Regressionsfall (betroffene Feldgeräte vorher/nachher)."""
    if art not in ARTEN:
        raise RegelFehler(f"Regelart „{art}“ unbekannt – möglich: {', '.join(ARTEN)}")
    artikel = stamm.get("artikel", {})
    if wenn not in artikel:
        raise RegelFehler(f"Artikel „{wenn}“ gibt es nicht im Gerätestamm")
    if art == "artikel_ersetzen" and dann not in artikel:
        raise RegelFehler(f"Ersatzartikel „{dann}“ gibt es nicht im Gerätestamm")
    betroffen = [fg for fg in projekt.get("feldgeraete") or [] if isinstance(fg, dict) and fg.get("artikel") == wenn]
    if not betroffen:
        raise RegelFehler(f"Im Projekt kommt Artikel „{wenn}“ nicht vor – Korrektur würde nichts ändern")
    regeln = lade_regeln(pfad)
    widerspruch = [r for r in regeln if r.get("aktiv", True) and r["art"] == art and r["wenn"] == wenn and r["dann"] != dann]
    if widerspruch:
        raise RegelFehler(f"Widerspruch zu Hausregel {widerspruch[0]['id']} ({wenn} → {widerspruch[0]['dann']}) – "
                          f"alte Regel erst deaktivieren")
    regel: dict[str, Any] = {"id": f"R{len(regeln) + 1}", "art": art, "wenn": wenn, "dann": dann, "aktiv": True,
             "herkunft": herkunft, "grund": grund, "datum": dt.date.today().isoformat(),
             "gilt_ab": gilt_ab or "",
             "fall": {"eingabe": copy.deepcopy(betroffen), "erwartet": None}}
    nachher, _ = wende_an({"feldgeraete": copy.deepcopy(betroffen)}, [*regeln, regel])
    regel["fall"]["erwartet"] = nachher["feldgeraete"]
    speichere_regeln(pfad, [*regeln, regel])
    return regel


def pruefe_regressionen(regeln: list[dict[str, Any]]) -> list[str]:
    """Jeden gespeicherten Fall mit ALLEN aktiven Regeln erneut durchspielen; Abweichungen im Klartext."""
    befunde = []
    for r in regeln:
        if not r.get("aktiv", True):
            continue
        ist, _ = wende_an({"feldgeraete": copy.deepcopy(r["fall"]["eingabe"])}, regeln)
        if ist["feldgeraete"] != r["fall"]["erwartet"]:
            befunde.append(f"Regressionsfall zu {r['id']} ({r['wenn']} → {r['dann']}) liefert jetzt ein anderes Ergebnis "
                           f"– eine spätere Regel verändert ihn")
    return befunde
