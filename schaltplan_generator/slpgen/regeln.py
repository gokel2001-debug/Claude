"""Regelwerk: aus Projekteingabe + Gerätestamm wird ein vollständiges Planmodell.

Alle Hausregeln (Reserve, Absicherungsfaktor, Kennbuchstaben) sind Parameter,
damit sie später aus der Bestandsanalyse (gelernte Standards) gesetzt werden
können, statt im Code zu stehen.
"""
from __future__ import annotations

import math
from collections import OrderedDict
from typing import Any

from .modell import Absicherung, Betriebsmittel, Klemme, Planmodell, RegelFehler, SpsKanal
from .motor import MOTOREN_JE_SEITE, plane_motoren

# Feste Seiten; ab Seite 6 folgen Motor-Last-, Motor-Steuer- und Feldgeräteseiten (dynamisch)
SEITE_EINSPEISUNG = 3
SEITE_VERTEILUNG = 4
SEITE_SPS = 5
ERSTE_DYN_SEITE = 6
SPALTEN_JE_SEITE = 8
ZEILEN_JE_SEITE = 36          # Listen (Klemmen, Kabel, Stückliste)


def strom_A(art: dict[str, Any]) -> float:
    """Stromaufnahme an 24 V aus Datenblattwerten (i_mA oder p_W)."""
    if "i_mA" in art:
        return art["i_mA"] / 1000.0
    if "p_W" in art:
        return art["p_W"] / art.get("u_V", 24)
    raise RegelFehler(f"Keine Stromangabe (i_mA oder p_W) für {art.get('bezeichnung')}")


def waehle_kleinste(stamm: dict, kandidaten: list[str], i_min: float) -> str | None:
    passend = [k for k in kandidaten if stamm[k]["i_nenn_A"] >= i_min]
    return min(passend, key=lambda k: stamm[k]["i_nenn_A"]) if passend else None


def plane(projekt: dict[str, Any], stamm: dict[str, Any]) -> Planmodell:
    pk = projekt["projekt"]
    m = Planmodell(projekt=dict(pk))
    m.projekt["_netz"] = projekt["einspeisung"].get("netz", "")
    art = stamm["artikel"]
    v24 = projekt["versorgung_24V"]

    def artikel(key: str) -> dict:
        if key not in art:
            raise RegelFehler(f"Artikel '{key}' fehlt im Gerätestamm")
        return art[key]

    # ---- Feldgeräte -------------------------------------------------------
    feld = []
    for fg in projekt["feldgeraete"]:
        a = artikel(fg["artikel"])
        bmk = "-" + fg["bmk"].lstrip("-")
        b = Betriebsmittel(bmk=bmk, artikel=fg["artikel"], bezeichnung=a["bezeichnung"],
                           funktion=fg.get("funktion", ""), kategorie=a["kategorie"],
                           daten={"gruppe": fg.get("gruppe", "Allgemein"), "i_A": strom_A(a),
                                  "signal": a["signal"], "anschluss": a.get("anschluss", [])})
        feld.append(b)

    # ---- Motorabgänge (Typical DOL) ------------------------------------------
    n_mot = len(projekt.get("motoren", []))
    n_motseiten = math.ceil(n_mot / MOTOREN_JE_SEITE)
    erste_feldseite = ERSTE_DYN_SEITE + 2 * n_motseiten
    motor_signale = plane_motoren(m, projekt, art, ERSTE_DYN_SEITE)

    # ---- SPS: Module bestimmen, Kanäle zuweisen ----------------------------
    sps = projekt["sps"]
    cpu = artikel(sps["cpu"])
    sps_bm = [Betriebsmittel(bmk="-A1", artikel=sps["cpu"], bezeichnung=cpu["bezeichnung"],
                             funktion="Steuerung", kategorie="sps_cpu",
                             seite=SEITE_SPS, spalte=1, daten={"i_A": strom_A(cpu)})]
    modul_nr = 2
    zaehler: dict[str, int] = {}
    for sig in ("DI", "DO", "AI"):
        geraete = [b for b in feld + motor_signale if b.daten["signal"] == sig]
        if not geraete:
            continue
        mod_key = sps["module_kandidaten"][sig]
        mod = artikel(mod_key)
        anzahl = math.ceil(len(geraete) / mod["kanaele"])
        module = []
        for i in range(anzahl):
            mb = Betriebsmittel(bmk=f"-A{modul_nr}", artikel=mod_key, bezeichnung=mod["bezeichnung"],
                                funktion=f"{sig}-Modul {i + 1}", kategorie=mod["kategorie"],
                                seite=SEITE_SPS, spalte=modul_nr, daten={"i_A": strom_A(mod)})
            module.append(mb)
            sps_bm.append(mb)
            modul_nr += 1
        for idx, g in enumerate(geraete):
            mb = module[idx // mod["kanaele"]]
            kanal = idx % mod["kanaele"]
            n = zaehler.get(sig, 0)
            zaehler[sig] = n + 1
            adr = sps["adressschema"][sig].format(byte=n // 8, bit=n % 8, wort=2 * n)
            m.sps_kanaele.append(SpsKanal(mb.bmk, kanal, sig, adr, g.bmk, g.funktion))
            g.daten["sps"] = f"{mb.bmk}:{kanal} ({adr})"
            g.daten["adresse"] = adr

    # ---- 24-V-Bilanz und Netzteilwahl ---------------------------------------
    # DO-Aktoren werden über die Lastspannung des Ausgabemoduls versorgt; ihr
    # Strom zählt daher zum Abgang, der die DO-Module speist (nicht zur Feldgruppe).
    gruppen: "OrderedDict[str, list[Betriebsmittel]]" = OrderedDict()
    gruppen["SPS"] = [b for b in sps_bm if b.kategorie != "sps_do"]
    do_last = [b for b in sps_bm if b.kategorie == "sps_do"]
    for b in motor_signale:          # Schützspulen -> DO-Last, MSS-Rückmeldung -> SPS
        (do_last if b.daten["gruppe"] == "DO-Last" else gruppen["SPS"]).append(b)
    for b in feld:
        if b.daten["signal"] == "DO":
            b.daten["gruppe"] = "DO-Last"
            do_last.append(b)
        else:
            gruppen.setdefault(b.daten["gruppe"], []).append(b)
    if do_last:
        gruppen["DO-Last"] = do_last

    i_summe = sum(b.daten["i_A"] for gl in gruppen.values() for b in gl)
    g, r = v24.get("gleichzeitigkeit", 1.0), v24.get("reserve", 0.25)
    i_bedarf = i_summe * g * (1 + r)
    nt_key = waehle_kleinste(art, v24["netzteile"], i_bedarf)
    if nt_key is None:
        raise RegelFehler(f"Kein Netzteil für {i_bedarf:.2f} A in {v24['netzteile']}")
    nt = art[nt_key]
    p_aus = nt["u_aus_V"] * nt["i_nenn_A"]
    i_primaer = p_aus / nt["wirkungsgrad"] / nt["u_ein_V"]
    m.bilanz = {
        "i_summe_A": round(i_summe, 3), "gleichzeitigkeit": g, "reserve": r,
        "i_bedarf_A": round(i_bedarf, 3), "netzteil": nt_key, "i_nenn_A": nt["i_nenn_A"],
        "auslastung": round(i_summe * g / nt["i_nenn_A"], 3),
        "i_primaer_max_A": round(i_primaer, 2),
        "gruppen": {k: round(sum(b.daten["i_A"] for b in v), 3) for k, v in gruppen.items()},
    }
    # 400-V-Summenstrom gegen Hauptschalter (Netzteil vereinfacht auf einem Außenleiter addiert)
    i_mot = sum(float(x["i_N_A"]) for x in projekt.get("motoren", []))
    m.bilanz["i_motoren_A"] = round(i_mot, 2)
    m.bilanz["i_400V_max_A"] = round(i_mot + i_primaer, 2)

    # ---- Einspeisung -----------------------------------------------------------
    hs_key = projekt["einspeisung"]["hauptschalter"]
    m.betriebsmittel.append(Betriebsmittel("-Q1", hs_key, artikel(hs_key)["bezeichnung"],
                                           "Hauptschalter", "hauptschalter", SEITE_EINSPEISUNG, 2))
    if m.bilanz["i_400V_max_A"] > artikel(hs_key)["i_nenn_A"]:
        m.warnungen.append(f"Σ I 400 V = {m.bilanz['i_400V_max_A']} A > Hauptschalter {artikel(hs_key)['i_nenn_A']} A")
    ls_kand = [k for k, a in art.items() if a["kategorie"] == "schutz"]
    ls_key = waehle_kleinste(art, ls_kand, nt["vorsicherung_A"])
    if ls_key is None or art[ls_key]["i_nenn_A"] != nt["vorsicherung_A"]:
        m.warnungen.append(f"Vorsicherung {nt['vorsicherung_A']} A laut Datenblatt {nt_key} nicht exakt im "
                           f"Stamm; gewählt: {ls_key}")
    m.betriebsmittel.append(Betriebsmittel("-F1", ls_key, art[ls_key]["bezeichnung"],
                                           "Vorsicherung Netzteil", "schutz", SEITE_EINSPEISUNG, 5))
    m.betriebsmittel.append(Betriebsmittel("-G1", nt_key, nt["bezeichnung"], "Versorgung 24 V DC",
                                           "netzteil", SEITE_EINSPEISUNG, 7, dict(nt)))

    # ---- Absicherung der 24-V-Gruppen ----------------------------------------
    es_kand = [k for k, a in art.items() if a["kategorie"] == "schutz_dc"]
    fak = v24.get("absicherungsfaktor", 1.25)
    for n, (gname, gl) in enumerate(gruppen.items(), start=2):
        i_g = sum(b.daten["i_A"] for b in gl)
        es_key = waehle_kleinste(art, es_kand, i_g * fak)
        if es_key is None:
            raise RegelFehler(f"Keine 24-V-Sicherung >= {i_g * fak:.2f} A für Gruppe {gname}")
        if art[es_key]["i_nenn_A"] > nt["i_nenn_A"]:
            m.warnungen.append(f"-F{n}: Sicherung {art[es_key]['i_nenn_A']} A > Netzteil-Nennstrom")
        spalte = n - 1
        m.betriebsmittel.append(Betriebsmittel(f"-F{n}", es_key, art[es_key]["bezeichnung"],
                                               f"24 V {gname}", "schutz_dc", SEITE_VERTEILUNG, spalte))
        m.absicherungen.append(Absicherung(f"-F{n}", es_key, art[es_key]["i_nenn_A"], gname,
                                           round(i_g, 3), [b.bmk for b in gl]))
        for b in gl:
            b.daten["absicherung"] = f"-F{n}"
    if i_summe * g > nt["i_nenn_A"]:
        m.warnungen.append("Summenstrom übersteigt Netzteil-Nennstrom")

    m.betriebsmittel.extend(sps_bm)

    # ---- Feldgeräte auf Seiten/Spalten + Klemmen -X1 --------------------------
    knr = 1
    for i, b in enumerate(feld):
        b.seite = erste_feldseite + i // SPALTEN_JE_SEITE
        b.spalte = i % SPALTEN_JE_SEITE + 1
        ans = b.daten["anschluss"]
        sig = b.daten["signal"]
        plan: list[tuple[str, str, str]] = []
        if sig == "DI":   # 3-Leiter: L+, L-, Q
            plan = [("+24V", f"{b.daten['absicherung']}:2", ans[0]),
                    ("Signal", b.daten["sps"], ans[2]),
                    ("0V", "0V-Schiene", ans[1])]
        elif sig == "AI":  # 2-Leiter 4–20 mA
            plan = [("+24V", f"{b.daten['absicherung']}:2", ans[0]),
                    ("Signal", b.daten["sps"], ans[1])]
        elif sig == "DO":
            plan = [("Signal", b.daten["sps"], ans[0]),
                    ("0V", "0V-Schiene", ans[1])]
        b.daten["klemmen"] = []
        for pot, innen, aussen in plan:
            m.klemmen.append(Klemme("-X1", knr, pot, innen, f"{b.bmk}:{aussen}", b.seite, b.spalte))
            b.daten["klemmen"].append(knr)
            knr += 1
        m.betriebsmittel.append(b)

    m.betriebsmittel.append(Betriebsmittel("-X1", "RK-2.5", artikel("RK-2.5")["bezeichnung"],
                                           "Klemmleiste Feld", "klemme",
                                           daten={"anzahl": knr - 1}))
    # ---- Seitenplan --------------------------------------------------------------
    n_feldseiten = math.ceil(len(feld) / SPALTEN_JE_SEITE)
    plan = [("Deckblatt", "deckblatt", 0), ("Inhaltsverzeichnis", "inhalt", 0),
            ("Einspeisung / Netzteil 24 V", "einspeisung", 0), ("Verteilung 24 V DC", "verteilung", 0),
            ("SPS-Übersicht", "sps", 0)]
    plan += [(f"Motorabgänge {i + 1} (Last)", "motor_last", i) for i in range(n_motseiten)]
    plan += [(f"Motorabgänge {i + 1} (Steuerung)", "motor_steuer", i) for i in range(n_motseiten)]
    plan += [(f"Feldgeräte {i + 1}", "feld", i) for i in range(n_feldseiten)]
    def listenseiten(titel, art_, n):
        k = max(1, math.ceil(n / ZEILEN_JE_SEITE))
        return [(titel if k == 1 else f"{titel} {i + 1}", art_, i) for i in range(k)]
    plan += listenseiten("Klemmenplan", "klemmen", len(m.klemmen))
    if m.kabel:
        plan += listenseiten("Kabelliste", "kabel", len(m.kabel))
    plan += listenseiten("Stückliste", "stueckliste", len({b.artikel for b in m.betriebsmittel}))
    plan += [("Auslegungsnachweis", "auslegung", 0)]
    m.seiten = [(i + 1, t, a, x) for i, (t, a, x) in enumerate(plan)]
    assert m.seiten[SEITE_SPS - 1][2] == "sps" and (n_mot == 0 or m.seiten[ERSTE_DYN_SEITE - 1][2] == "motor_last")
    return m
