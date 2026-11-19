"""Hausprofil lernen: Zeichenkonventionen statistisch aus vielen Bestands-PDFs ableiten.

„Lernen“ heißt hier nachvollziehbar und prüfbar: Für jedes Merkmal werden Wert, Anteil,
Belegdateien und die Entwicklung über die Jahre ermittelt. Ein Mensch bestätigt die Werte
(Status `vorgeschlagen` -> `freigegeben`). Freigegebene Werte überschreibt ein erneuter
Lernlauf nicht; abweichende neue Erkenntnisse landen dann unter `vorschlag_neu`.

Das Profil enthält Hausinhalte und gehört nur lokal nach `hausprofil/` (nicht ins Repository).
"""
from __future__ import annotations

import datetime as dt
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

import yaml

from .analyse import analysiere_pdf
from .struktur import lese_struktur

MIN_PLAENE_SICHER = 3          # weniger Belege -> Sicherheit "unsicher"
MIN_PLAENE_JE_SEITE_TREND = 2  # Trend erst, wenn vor und nach dem Wechsel je so viele Pläne belegen
INFRASTRUKTUR = ("AC", "DC")   # Anlagen-Präfixe ohne Feldgeräte (Einspeisung, 24 V)


def _feldklemmleiste(st: dict) -> str | None:
    """Häufigste Klemmleiste (X + Nummer) in Funktionsanlagen eines Plans."""
    z = Counter(b for name, a in st["anlagen"].items()
                if not a["leer"] and not name.startswith(INFRASTRUKTUR)
                for b in a["bmk"] if b[:1] == "X" and b[1:].isdigit())
    return f"-{z.most_common(1)[0][0]}" if z else None


def _sps_schreibweise(st: dict) -> str | None:
    adr = [a for an in st["anlagen"].values() for a in an["sps_adressen"]]
    if not adr:
        return None
    iec = sum(a.startswith("%") for a in adr)
    return "IEC (%I/%Q/%IW)" if iec > len(adr) / 2 else "deutsch (E/A/EW/AW)"


def _signalader_24v(st: dict) -> str | None:
    """Häufigste Aderkennzeichnung im Querschnitt 0,75 mm² (Steuer-/Signalverdrahtung)."""
    z = {k: v for k, v in st["aderkennzeichnung_gesamt"].items() if k.endswith(" 0,75")}
    return max(z, key=z.get) if z else None


# Einzelwert-Merkmale: je Plan ein Wert -> Mehrheit, Anteil, Jahrestrend
EINZELWERTE: dict[str, tuple[str, Callable[[dict], str | None]]] = {
    "feldklemmleiste": ("Klemmleiste für Feldgeräte in Funktionsanlagen", _feldklemmleiste),
    "sps_adressschreibweise": ("Schreibweise der SPS-Adressen", _sps_schreibweise),
    "signalader_0_75": ("häufigste Aderkennzeichnung 0,75 mm² (Signal/24 V)", _signalader_24v),
}


def _trend(je_jahr: dict[int, Counter]) -> list[dict]:
    """Wechsel des dominanten Werts zwischen aufeinanderfolgenden Jahren mit Belegen."""
    jahre = sorted(je_jahr)
    dominant = {j: je_jahr[j].most_common(1)[0][0] for j in jahre}
    wechsel = []
    for vor, nach in zip(jahre, jahre[1:]):
        if dominant[vor] != dominant[nach]:
            n_vor = sum(je_jahr[j][dominant[vor]] for j in jahre if j <= vor)
            n_nach = sum(je_jahr[j][dominant[nach]] for j in jahre if j >= nach)
            sicher = min(n_vor, n_nach) >= MIN_PLAENE_JE_SEITE_TREND
            wechsel.append({"ab_jahr": nach, "von": dominant[vor], "nach": dominant[nach],
                            "belege_vorher": n_vor, "belege_nachher": n_nach,
                            "sicherheit": "hoch" if sicher else "unsicher"})
    return wechsel


def lerne(pdfs: list[Path]) -> dict[str, Any]:
    plaene = []
    fehler = []
    for p in pdfs:
        try:
            plaene.append((p.name, analysiere_pdf(p)["jahr"], lese_struktur(p)))
        except Exception as e:                      # defekte PDFs nicht abbrechen lassen
            fehler.append({"datei": p.name, "fehler": str(e)})

    merkmale: dict[str, Any] = {}
    for key, (beschreibung, funktion) in EINZELWERTE.items():
        werte = [(datei, jahr, funktion(st)) for datei, jahr, st in plaene]
        werte = [w for w in werte if w[2] is not None]
        if not werte:
            continue
        gesamt = Counter(w for _, _, w in werte)
        je_jahr: dict[int, Counter] = defaultdict(Counter)
        belege: dict[str, list[str]] = defaultdict(list)
        for datei, jahr, w in werte:
            belege[w].append(datei)
            if jahr:
                je_jahr[jahr][w] += 1
        trend = _trend(je_jahr) if je_jahr else []
        # aktueller Wert: nach dem letzten sicheren Wechsel, sonst Mehrheit über alles
        sichere = [t for t in trend if t["sicherheit"] == "hoch"]
        wert = sichere[-1]["nach"] if sichere else gesamt.most_common(1)[0][0]
        merkmale[key] = {
            "beschreibung": beschreibung,
            "wert": wert,
            "status": "vorgeschlagen",
            "sicherheit": "hoch" if len(werte) >= MIN_PLAENE_SICHER else "unsicher",
            "anteil_gesamt": {w: round(n / len(werte), 3) for w, n in gesamt.most_common()},
            "je_jahr": {j: je_jahr[j].most_common(1)[0][0] for j in sorted(je_jahr)},
            "trend": trend,
            "belege": {w: sorted(d) for w, d in belege.items()},
        }

    # Häufigkeits-Merkmale: über alle Pläne zählen
    leitungen, dokarten, adern = Counter(), Counter(), Counter()
    for _, _, st in plaene:
        leitungen.update({lt for a in st["anlagen"].values() for lt in a["leitungstypen"]})
        dokarten.update(st["seiten_je_dokumentart"].keys())
        adern.update(st["aderkennzeichnung_gesamt"])
    merkmale["leitungstypen"] = {"beschreibung": "Leitungstypen (Anzahl Pläne)", "status": "vorgeschlagen",
                                 "haeufigkeit": dict(leitungen.most_common())}
    merkmale["dokumentarten"] = {"beschreibung": "Dokumentarten (Anzahl Pläne)", "status": "vorgeschlagen",
                                 "haeufigkeit": dict(dokarten.most_common())}
    merkmale["aderkennzeichnung"] = {"beschreibung": "Aderkennzeichnung Farbe + Querschnitt (Anzahl)",
                                     "status": "vorgeschlagen", "haeufigkeit": dict(adern.most_common(15))}
    jahre = sorted({j for _, j, _ in plaene if j})
    return {
        "meta": {"erstellt": dt.date.today().isoformat(), "plaene": len(plaene),
                 "jahre": jahre, "fehler": fehler},
        "merkmale": merkmale,
    }


def zusammenfuehren(alt: dict | None, neu: dict) -> dict:
    """Freigegebene Merkmale aus dem alten Profil behalten; Abweichung als `vorschlag_neu`."""
    if not alt:
        return neu
    for key, m_alt in alt.get("merkmale", {}).items():
        if m_alt.get("status") != "freigegeben":
            continue
        m_neu = neu["merkmale"].get(key)
        behalten = dict(m_alt)
        behalten.pop("vorschlag_neu", None)
        if m_neu and m_neu.get("wert", m_neu.get("haeufigkeit")) != m_alt.get("wert", m_alt.get("haeufigkeit")):
            behalten["vorschlag_neu"] = m_neu
        neu["merkmale"][key] = behalten
    return neu


def lerne_ordner(ordner: str | Path, profil_pfad: str | Path) -> dict:
    pdfs = sorted(Path(ordner).rglob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"Keine PDF-Dateien in {ordner}")
    profil_pfad = Path(profil_pfad)
    alt = yaml.safe_load(profil_pfad.read_text(encoding="utf-8")) if profil_pfad.exists() else None
    profil = zusammenfuehren(alt, lerne(pdfs))
    profil_pfad.parent.mkdir(parents=True, exist_ok=True)
    profil_pfad.write_text("# Hausprofil – VERTRAULICH, nur lokal. Status je Merkmal: vorgeschlagen -> freigegeben\n"
                           + yaml.safe_dump(profil, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return profil
