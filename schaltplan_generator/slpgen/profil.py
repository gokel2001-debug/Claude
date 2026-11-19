"""Hausprofil lernen: Zeichenkonventionen statistisch aus vielen Bestands-PDFs ableiten.

„Lernen“ heißt hier nachvollziehbar und prüfbar: Für jedes Merkmal werden Wert, Anteil,
Belegdateien und die Entwicklung über die Jahre ermittelt. Ein Mensch bestätigt die Werte
(Status `vorgeschlagen` -> `freigegeben`). Freigegebene Werte überschreibt ein erneuter
Lernlauf nicht; abweichende neue Erkenntnisse landen dann unter `vorschlag_neu`.

Das Profil enthält Hausinhalte und Dateinamen der Bestandspläne; es gehört nur lokal nach
`hausprofil/` (per .gitignore ausgeschlossen, nicht ins Repository).
"""
from __future__ import annotations

import datetime as dt
import errno
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

import yaml

from .analyse import analysiere_pdf
from .modell import RegelFehler
from .struktur import lese_struktur

MIN_PLAENE_SICHER = 3          # weniger Belege -> Sicherheit "unsicher"
MIN_PLAENE_JE_SEITE_TREND = 2  # Trend erst, wenn vor und nach dem Wechsel je so viele Pläne belegen
INFRASTRUKTUR = ("AC", "DC")   # Anlagen-Präfixe ohne Feldgeräte (Einspeisung, 24 V) – Hausparameter
RE_LEISTE = re.compile(r"X[A-Z]?\d+")


class ProfilFehler(RegelFehler):
    pass


def _eindeutig_haeufigster(z: Counter) -> str | None:
    """Häufigster Wert; bei Gleichstand None (nicht raten)."""
    top = z.most_common(2)
    if not top or (len(top) == 2 and top[0][1] == top[1][1]):
        return None
    return top[0][0]


def _feldklemmleiste(st: dict) -> str | None:
    """Leiste, auf die Feldsignale geführt sind: bevorzugt Klemmenbezüge (-X20:3) aus
    Funktionsanlagen, sonst X-Leisten unter deren Betriebsmitteln."""
    funktion = [a for name, a in st["anlagen"].items() if not a["leer"] and not name.startswith(INFRASTRUKTUR)]
    bezuege = Counter()
    for a in funktion:
        bezuege.update(a.get("klemmenbezuege", {}))
    z = bezuege or Counter(b for a in funktion for b in a["bmk"] if RE_LEISTE.fullmatch(b))
    w = _eindeutig_haeufigster(z)
    return f"-{w}" if w else None


def _sps_schreibweise(st: dict) -> str | None:
    adr = [a for an in st["anlagen"].values() for a in an["sps_adressen"]]
    if not adr:
        return None
    iec = sum(a.startswith("%") for a in adr)
    if iec == len(adr) - iec:
        return None
    return "IEC (%I/%Q/%IW)" if iec > len(adr) / 2 else "deutsch (E/A/EW/AW)"


def _haeufigste_ader_075(st: dict) -> str | None:
    """Häufigste Aderkennzeichnung 0,75 mm² – OHNE Zuordnung zu einem Potential (siehe E9)."""
    return _eindeutig_haeufigster(Counter({k: v for k, v in st["aderkennzeichnung_gesamt"].items()
                                           if k.endswith(" 0,75")}))


# Einzelwert-Merkmale: je Plan ein Wert -> Mehrheit, Anteil, Jahrestrend
EINZELWERTE: dict[str, tuple[str, Callable[[dict], str | None]]] = {
    "feldklemmleiste": ("Klemmleiste für Feldgeräte (Funktionsanlagen)", _feldklemmleiste),
    "sps_adressschreibweise": ("Schreibweise der SPS-Adressen", _sps_schreibweise),
    "haeufigste_ader_0_75": ("häufigste Aderkennzeichnung 0,75 mm² (noch ohne Potentialzuordnung)",
                             _haeufigste_ader_075),
}


def _bloecke(je_jahr: dict[int, Counter]) -> list[dict]:
    """Aufeinanderfolgende Jahre mit gleichem dominanten Wert zu Blöcken zusammenfassen.
    Jahre mit Gleichstand gehören zu keinem Block (unentschieden)."""
    bloecke: list[dict] = []
    for jahr in sorted(je_jahr):
        w = _eindeutig_haeufigster(je_jahr[jahr])
        if w is None:
            continue
        if bloecke and bloecke[-1]["wert"] == w:
            bloecke[-1]["bis"] = jahr
            bloecke[-1]["belege"] += je_jahr[jahr][w]
        else:
            bloecke.append({"wert": w, "von": jahr, "bis": jahr, "belege": je_jahr[jahr][w]})
    return bloecke


def _trend(bloecke: list[dict]) -> list[dict]:
    return [{"ab_jahr": b["von"], "von": a["wert"], "nach": b["wert"], "belege_vorher": a["belege"],
             "belege_nachher": b["belege"],
             "sicherheit": "hoch" if min(a["belege"], b["belege"]) >= MIN_PLAENE_JE_SEITE_TREND else "unsicher"}
            for a, b in zip(bloecke, bloecke[1:])]


def _norm_leitung(lt: str) -> str:
    lt = lt.strip().upper()
    return lt.split()[0] if lt.startswith("ÖLFLEX") else lt


def lerne(pdfs: list[Path]) -> dict[str, Any]:
    plaene = []
    fehler = []
    for p in pdfs:
        try:
            a = analysiere_pdf(p)
            plaene.append((p.name, a["jahr"], a.get("jahr_eindeutig", True), lese_struktur(p)))
        except Exception as e:                      # defekte PDFs nicht abbrechen lassen
            fehler.append({"datei": p.name, "fehler": type(e).__name__})

    merkmale: dict[str, Any] = {}
    for key, (beschreibung, funktion) in EINZELWERTE.items():
        alle = [(datei, jahr if eindeutig else None, funktion(st)) for datei, jahr, eindeutig, st in plaene]
        werte = [w for w in alle if w[2] is not None]
        ohne_wert = sorted(d for d, _, w in alle if w is None)
        if not werte:
            continue
        gesamt = Counter(w for _, _, w in werte)
        je_jahr: dict[int, Counter] = defaultdict(Counter)
        belege: dict[str, list[str]] = defaultdict(list)
        for datei, jahr, w in werte:
            belege[w].append(datei)
            if jahr:
                je_jahr[jahr][w] += 1
        bloecke = _bloecke(je_jahr)
        trend = _trend(bloecke)
        # aktueller Wert: jüngster Block, wenn ausreichend belegt; sonst Mehrheit über alles
        if bloecke and bloecke[-1]["belege"] >= MIN_PLAENE_JE_SEITE_TREND:
            wert = bloecke[-1]["wert"]
        else:
            wert = _eindeutig_haeufigster(gesamt) or gesamt.most_common(1)[0][0]
        merkmale[key] = {
            "beschreibung": beschreibung,
            "wert": wert,
            "status": "vorgeschlagen",
            "sicherheit": "hoch" if gesamt[wert] >= MIN_PLAENE_SICHER else "unsicher",
            "belegt_in": f"{gesamt[wert]} von {len(alle)} Plänen",
            "anteil_gesamt": {w: round(n / len(werte), 3) for w, n in gesamt.most_common()},
            "je_jahr": {j: (_eindeutig_haeufigster(je_jahr[j]) or "unentschieden") for j in sorted(je_jahr)},
            "trend": trend,
            "ohne_wert": ohne_wert,
            "belege": {w: sorted(d) for w, d in belege.items()},
        }

    # Häufigkeits-Merkmale: über alle Pläne zählen
    leitungen, dokarten, adern = Counter(), Counter(), Counter()
    for _, _, _, st in plaene:
        leitungen.update({_norm_leitung(lt) for a in st["anlagen"].values() for lt in a["leitungstypen"]})
        dokarten.update(st["seiten_je_dokumentart"].keys())
        adern.update(st["aderkennzeichnung_gesamt"])
    merkmale["leitungstypen"] = {"beschreibung": "Leitungstypen (Anzahl Pläne)", "status": "vorgeschlagen",
                                 "haeufigkeit": dict(leitungen.most_common())}
    merkmale["dokumentarten"] = {"beschreibung": "Dokumentarten (Anzahl Pläne)", "status": "vorgeschlagen",
                                 "haeufigkeit": dict(dokarten.most_common())}
    merkmale["aderkennzeichnung"] = {"beschreibung": "Aderkennzeichnung Farbe + Querschnitt (Anzahl)",
                                     "status": "vorgeschlagen", "haeufigkeit": dict(adern.most_common(15))}
    jahre = sorted({j for _, j, _, _ in plaene if j})
    return {
        "meta": {"erstellt": dt.date.today().isoformat(), "plaene": len(plaene), "jahre": jahre,
                 "jahr_unsicher": sorted(d for d, _, e, _ in plaene if not e), "fehler": fehler},
        "merkmale": merkmale,
    }


def _vergleichswert(m: dict):
    """Für Häufigkeiten zählt nur die Rangfolge der 5 häufigsten Einträge, nicht die Zahl."""
    return m["wert"] if "wert" in m else list(m.get("haeufigkeit", {}))[:5]


def zusammenfuehren(alt: dict | None, neu: dict) -> dict:
    """Freigegebene Merkmale aus dem alten Profil behalten; Abweichung als `vorschlag_neu`."""
    if not alt:
        return neu
    for key, m_alt in alt.get("merkmale", {}).items():
        if not isinstance(m_alt, dict):
            continue
        m_neu = neu["merkmale"].get(key)
        if m_alt.get("status") == "abgelehnt" and m_neu and _vergleichswert(m_neu) == _vergleichswert(m_alt):
            m_neu["status"] = "abgelehnt"          # gleicher Vorschlag wie zuvor abgelehnt -> nicht erneut vorlegen
            continue
        if m_alt.get("status") != "freigegeben":
            continue
        behalten = dict(m_alt)
        alt_vorschlag = behalten.pop("vorschlag_neu", None) or {}
        abgelehnt_gleich = (alt_vorschlag.get("status") == "abgelehnt" and m_neu
                            and _vergleichswert(m_neu) == _vergleichswert(alt_vorschlag))
        if abgelehnt_gleich:
            behalten["vorschlag_neu"] = alt_vorschlag          # bereits abgelehnt -> nicht erneut vorlegen
        elif m_neu and _vergleichswert(m_neu) != _vergleichswert(m_alt):
            behalten["vorschlag_neu"] = m_neu
        neu["merkmale"][key] = behalten
    return neu


def uebersicht(profil: dict) -> str:
    """Kurze, lesbare Zusammenfassung (für Menü/Notepad)."""
    meta = profil["meta"]
    jahre = f"{meta['jahre'][0]}–{meta['jahre'][-1]}" if meta["jahre"] else "Jahr unbekannt"
    z = [f"Hausprofil aus {meta['plaene']} Plänen ({jahre}), erstellt {meta['erstellt']}",
         "Freigabe: Liste profil_freigabe.xlsx ausfüllen (JA/NEIN), dann Menüpunkt 7.", ""]
    for m in profil["merkmale"].values():
        if "wert" in m:
            z.append(f"- {m['beschreibung']}: {m['wert']}  (belegt in {m.get('belegt_in', '?')}, "
                     f"Sicherheit {m.get('sicherheit', '?')}, Status {m['status']})")
            for t in m.get("trend", []):
                z.append(f"    Änderung ab {t['ab_jahr']}: {t['von']} -> {t['nach']} (Sicherheit {t['sicherheit']})")
            if m.get("vorschlag_neu") and m["vorschlag_neu"].get("status") != "abgelehnt":
                z.append(f"    ACHTUNG: neuer Lernlauf ergibt {m['vorschlag_neu'].get('wert')} – in der Excel-Liste "
                         f"entscheiden")
        else:
            top = ", ".join(f"{k} ({v})" for k, v in list(m["haeufigkeit"].items())[:4])
            z.append(f"- {m['beschreibung']}: {top}")
    if meta["jahr_unsicher"]:
        z.append(f"\nJahr nicht eindeutig bestimmbar bei {len(meta['jahr_unsicher'])} Plänen (nicht im Trend).")
    if meta["fehler"]:
        z.append(f"Nicht lesbar: {len(meta['fehler'])} Dateien (siehe profil.yaml).")
    return "\n".join(z) + "\n"


def lerne_ordner(ordner: str | Path, profil_pfad: str | Path) -> dict:
    pdfs = sorted(Path(ordner).rglob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(errno.ENOENT, "Keine PDF-Dateien im Ordner", str(ordner))
    profil_pfad = Path(profil_pfad)
    alt = None
    if profil_pfad.exists():
        try:
            alt = yaml.safe_load(profil_pfad.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            raise ProfilFehler(f"{profil_pfad} ist beschädigt ({str(e).splitlines()[0]}) – bitte korrigieren "
                               f"oder löschen und neu lernen") from None
        if alt is not None and not isinstance(alt, dict):
            raise ProfilFehler(f"{profil_pfad} hat kein gültiges Profilformat – bitte löschen und neu lernen")
    neu = lerne(pdfs)
    if neu["meta"]["plaene"] == 0:
        raise ProfilFehler(f"Keine der {len(pdfs)} PDF-Dateien war lesbar – Profil nicht verändert")
    profil = zusammenfuehren(alt, neu)
    profil_pfad.parent.mkdir(parents=True, exist_ok=True)
    # Liste zuerst: ist sie noch in Excel geöffnet, bricht der Lauf ab, bevor das Profil geändert ist
    from .freigabe import schreibe_freigabeliste
    schreibe_freigabeliste(profil, profil_pfad.with_name("profil_freigabe.xlsx"))
    if profil_pfad.exists():
        shutil.copyfile(profil_pfad, profil_pfad.with_suffix(".yaml.bak"))
    profil_pfad.write_text("# Hausprofil – VERTRAULICH, nur lokal. Status je Merkmal: vorgeschlagen -> freigegeben\n"
                           + yaml.safe_dump(profil, allow_unicode=True, sort_keys=False), encoding="utf-8")
    profil_pfad.with_name("profil_uebersicht.txt").write_text(uebersicht(profil), encoding="utf-8")
    return profil
