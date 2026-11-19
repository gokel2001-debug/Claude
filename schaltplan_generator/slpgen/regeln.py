"""Regelwerk: aus Projekteingabe + Gerätestamm wird ein vollständiges Planmodell.

Alle Hausregeln (Reserve, Absicherungsfaktor, Kennbuchstaben) sind Parameter,
damit sie später aus der Bestandsanalyse (gelernte Standards) gesetzt werden
können, statt im Code zu stehen.
"""
from __future__ import annotations

import math
import re
from collections import OrderedDict
from typing import Any

from .modell import Absicherung, Betriebsmittel, Kabel, Klemme, Planmodell, RegelFehler, SpsKanal
from .motor import MOTOREN_JE_SEITE, plane_motoren, waehle_querschnitt

# Feste Seiten; ab Seite 6 folgen Motor-Last-, Motor-Steuer- und Feldgeräteseiten (dynamisch)
SEITE_EINSPEISUNG = 3
SEITE_VERTEILUNG = 4
SEITE_SPS = 5
ERSTE_DYN_SEITE = 6
SPALTEN_JE_SEITE = 8
ZEILEN_JE_SEITE = 36          # Listen (Klemmen, Kabel, Stückliste)
MAX_FELDKLEMMEN = 9           # je Feldgerät/Baustein (eine Seite, Spalten 1..9)
RE_GERAETE_BMK = re.compile(r"[A-Z]{1,3}\d{1,4}")


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
    # Einfaches Gerät: ein Signal laut Artikel. Baustein (Spalte „typical“): mehrere Signale,
    # Zusatzbauteile und Klemmenbelegung laut Bibliothek `typicals` im Gerätestamm.
    feld, teilsignale, bauteile = [], [], []
    typicals = stamm.get("typicals", {})
    gesehen: set[str] = set()
    for fg in projekt["feldgeraete"]:
        a = artikel(fg["artikel"])
        kurz = str(fg["bmk"]).strip().lstrip("-")
        if not RE_GERAETE_BMK.fullmatch(kurz):
            raise RegelFehler(f"Betriebsmittelkennzeichen '{fg['bmk']}' ungültig – erlaubt sind Kennbuchstaben "
                              f"und Nummer, z. B. B7 oder KF12 (ohne Punkt/Bindestrich)")
        if kurz in gesehen:
            raise RegelFehler(f"Betriebsmittelkennzeichen '{kurz}' ist doppelt vergeben")
        gesehen.add(kurz)
        bmk = "-" + kurz
        tname = (str(fg.get("typical") or "").strip()) or None
        netzgeraet = bool(tname and typicals.get(tname, {}).get("leistung"))
        i_24 = strom_A(a) if ("i_mA" in a or "p_W" in a or not netzgeraet) else 0.0   # Netzgeräte: kein 24-V-Strom
        b = Betriebsmittel(bmk=bmk, artikel=fg["artikel"], bezeichnung=a["bezeichnung"],
                           funktion=fg.get("funktion", ""), kategorie=a["kategorie"],
                           daten={"gruppe": fg.get("gruppe", "Allgemein"), "i_A": i_24,
                                  "signal": a.get("signal"), "anschluss": a.get("anschluss", [])})
        if tname:
            if tname not in typicals:
                raise RegelFehler(f"Baustein (Typical) '{tname}' für {bmk} fehlt in der Bibliothek")
            tp = typicals[tname]
            vs = tp.get("versorgung", {})
            lst = tp.get("leistung") or {}
            pins = list(vs.values()) + list(lst.get("pins", {}).values()) + \
                [sg[x] for sg in tp["signale"] for x in ("pin", "rueckleiter", "speisung", "rueckkontakt") if x in sg]
            if any(not isinstance(p, str) for p in pins):     # YAML liest z. B. NO/ON ohne Anführungszeichen als bool
                raise RegelFehler(f"Baustein '{tname}': Anschlussnamen bitte in Anführungszeichen setzen ({pins})")
            fehlend = [p for p in pins if p not in a.get("anschluss", [])]
            if fehlend:
                raise RegelFehler(f"{bmk}: Baustein '{tname}' braucht Anschlüsse {fehlend}, Artikel {fg['artikel']} "
                                  f"hat {a.get('anschluss', [])}")
            n_signal = len(pins) - len(lst.get("pins", {}))      # L/N/PE liegen auf der Leistungsleiste
            if n_signal > MAX_FELDKLEMMEN:
                raise RegelFehler(f"Baustein '{tname}' hat {n_signal} Signalklemmen, höchstens {MAX_FELDKLEMMEN} möglich")
            versorgt = "+24V" in vs or any(sg.get("speisung") or sg.get("quelle")
                                           or (sg.get("ueber") and not sg.get("rueckkontakt")) for sg in tp["signale"])
            b.daten.update(typical=tname, signal="BAUSTEIN", versorgung=vs, versorgt=versorgt)
            if "+24V" not in vs:
                b.daten["i_A"] = 0.0              # fremdversorgt: kein Verbraucher an unserem 24-V-Netz
            b.daten["teilsignale"] = []
            for n, sg in enumerate(tp["signale"], 1):
                t = Betriebsmittel(bmk=f"{bmk}.{n}", artikel="", bezeichnung=sg["text"],
                                   funktion=f"{sg['text']} {b.funktion}".strip(), kategorie="teilsignal",
                                   daten={"signal": sg["art"], "i_A": 0.0, "pin": sg.get("pin", ""),
                                          "eltern": bmk, "ueber": sg.get("ueber"), "quelle": sg.get("quelle"),
                                          "rueckleiter": sg.get("rueckleiter"), "speisung": sg.get("speisung"),
                                          "rueckkontakt": sg.get("rueckkontakt")})
                teilsignale.append(t)
                b.daten["teilsignale"].append(t.bmk)
                if sg.get("quelle"):
                    b.daten.setdefault("quellsignale", {})[t.bmk] = sg["quelle"]   # z. B. Hilfskontakt -Q1
            for bt in tp.get("bauteile", []):
                ba = artikel(bt["artikel"])
                bauteile.append(Betriebsmittel(bmk=f"{bmk}{bt['bmk']}", artikel=bt["artikel"],
                                               bezeichnung=ba["bezeichnung"], funktion=bt.get("text", ""),
                                               kategorie="bauteil",
                                               daten={"eltern": bmk, "lokal": bt["bmk"],
                                                      "i_A": strom_A(ba) if ("i_mA" in ba or "p_W" in ba) else 0.0,
                                                      "gruppe": bt.get("gruppe", b.daten["gruppe"])}))
            if lst:
                bauteile.extend(_leistungsteil(m, b, a, lst, fg, projekt.get("leitungen", {}), art))
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
    for sig in ("DI", "DO", "AI", "AO"):
        geraete = [b for b in feld + motor_signale + teilsignale if b.daten["signal"] == sig]
        if not geraete:
            continue
        if sig not in sps["module_kandidaten"] or sig not in sps["adressschema"]:
            raise RegelFehler(f"Für {sig}-Signale ist kein SPS-Modul/Adressschema angegeben (Regeln: modul_{sig})")
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
        if b.daten["signal"] == "BAUSTEIN" and not b.daten["versorgt"]:
            continue                 # fremdversorgter Baustein ohne 24-V-Anschluss
        if b.daten["signal"] == "DO":
            b.daten["gruppe"] = "DO-Last"
            do_last.append(b)
        else:
            gruppen.setdefault(b.daten["gruppe"], []).append(b)
    for b in bauteile:              # z. B. Koppelrelais-Spulen: Gruppe laut Bibliothek; passive Bauteile nicht
        if b.daten["i_A"] > 0:
            (do_last if b.daten["gruppe"] == "DO-Last" else gruppen.setdefault(b.daten["gruppe"], [])).append(b)
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
    # Außenleiterströme: Motoren auf allen drei, Netzteil auf L1, 1~-Geräte reihum L1/L2/L3
    i_mot = sum(float(x["i_N_A"]) for x in projekt.get("motoren", []))
    je_leiter = {"L1": i_mot + i_primaer, "L2": i_mot, "L3": i_mot}
    netzgeraete = [b for b in feld if b.daten.get("leistung")]
    for i, b in enumerate(netzgeraete):
        leiter = ("L2", "L3", "L1")[i % 3]          # L1 trägt bereits das Netzteil
        b.daten["leistung"]["aussenleiter"] = leiter
        je_leiter[leiter] += b.daten["leistung"]["i_N_A"]
    m.bilanz["i_motoren_A"] = round(i_mot, 2)
    m.bilanz["i_netzgeraete_A"] = round(sum(b.daten["leistung"]["i_N_A"] for b in netzgeraete), 2)
    m.bilanz["i_je_aussenleiter_A"] = {k: round(v, 2) for k, v in je_leiter.items()}
    m.bilanz["i_400V_max_A"] = round(max(je_leiter.values()), 2)          # höchstbelasteter Außenleiter

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
        plan: list[tuple] = []
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
        elif sig == "BAUSTEIN":   # Versorgung + je Teilsignal Klemmen, Reihenfolge laut Bibliothek
            vs = b.daten["versorgung"]
            ts = {t.bmk: t for t in teilsignale if t.daten["eltern"] == b.bmk}
            if "+24V" in vs:
                plan.append(("+24V", f"{b.daten['absicherung']}:2", vs["+24V"]))
            for k in b.daten["teilsignale"]:
                d = ts[k].daten
                if d["quelle"]:           # Meldung aus einem Schrankbauteil (z. B. Hilfskontakt) – keine Feldklemme
                    continue
                if d["speisung"]:         # potentialfreier Kontakt: Wurzel aus 24L+ der Gruppe
                    plan.append(("+24V", f"{b.daten['absicherung']}:2", d["speisung"]))
                if d["ueber"]:            # Signal über Schrankbauteil, z. B. Koppelrelais-Kontakt 11/14
                    plan.append(("Kontakt", f"{b.bmk}{d['ueber']}:14", d["pin"], k))
                    if d["rueckkontakt"]:  # potentialfrei: Kontaktwurzel 11 geht ins Feld statt an 24L+
                        plan.append(("Kontakt-Rück", f"{b.bmk}{d['ueber']}:11", d["rueckkontakt"]))
                else:
                    plan.append(("Signal", d["sps"], d["pin"], k))
                if d["rueckleiter"]:      # z. B. 4–20 mA Minus zurück auf den Kanal
                    plan.append(("Bezug", d["sps"].split(" ")[0] + "M", d["rueckleiter"], k))
            if "0V" in vs:
                plan.append(("0V", "0V-Schiene", vs["0V"]))
        b.daten["klemmen"] = []
        for eintrag in plan:
            pot, innen, aussen = eintrag[:3]
            schluessel = eintrag[3] if len(eintrag) > 3 else (b.bmk if pot == "Signal" else "")
            if pot == "Bezug":
                schluessel = ""          # gehört zum Kanal, aber kein eigener SPS-Kasten
            m.klemmen.append(Klemme("-X1", knr, pot, innen, f"{b.bmk}:{aussen}", b.seite, b.spalte, schluessel))
            b.daten["klemmen"].append(knr)
            knr += 1
        m.betriebsmittel.append(b)
    for bt in bauteile:             # Zusatzbauteile stehen beim zugehörigen Gerät
        eltern = next(f for f in feld if f.bmk == bt.daten["eltern"])
        bt.seite, bt.spalte = eltern.seite, eltern.spalte
    m.betriebsmittel.extend(bauteile)
    # Leistungsklemmen der Netzgeräte hinter den Motorklemmen auf -X2 fortlaufend nummerieren
    naechste = max([k.nr for k in m.klemmen if k.leiste == "-X2"] + [0]) + 1
    for k in [k for k in m.klemmen if k.leiste == "-X2" and k.nr == 0]:
        k.nr, naechste = naechste, naechste + 1
        eltern = next(f for f in feld if k.ziel_aussen.startswith(f.bmk + ":"))
        k.seite, k.spalte = eltern.seite, eltern.spalte
    for w in m.kabel:                # Leitungen der Netzgeräte: Seite des Geräts (bisheriger Plan)
        if w.seite is None:
            eltern = next((f for f in feld if f.bmk == w.nach), None)
            if eltern:
                w.seite, w.spalte = eltern.seite, eltern.spalte
    m.klemmen.sort(key=lambda k: (k.leiste, k.nr))
    n_x2 = len([k for k in m.klemmen if k.leiste == "-X2"])
    if n_x2:                         # Stückliste: tatsächliche Zahl der Leistungsklemmen
        x2 = next((b for b in m.betriebsmittel if b.bmk == "-X2"), None)
        if x2 is None:
            x2 = Betriebsmittel("-X2", "RK-4", artikel("RK-4")["bezeichnung"], "Klemmleiste Leistung", "klemme")
            m.betriebsmittel.append(x2)
        x2.daten["anzahl"] = n_x2
    m.warnungen = list(dict.fromkeys(m.warnungen))   # gleiche Hinweise nur einmal

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


def _leistungsteil(m: Planmodell, b: Betriebsmittel, a: dict, lst: dict, fg: dict, ltg: dict,
                   art: dict) -> list[Betriebsmittel]:
    """Netzversorgtes Feldgerät (z. B. Pumpe 1~230 V): Motorschutzschalter, Leitung, Klemmen L/N/PE."""
    if "i_N_A" not in a:
        raise RegelFehler(f"{b.bmk}: Artikel {b.artikel} braucht i_N_A (Nennstrom) für den Leistungsteil")
    i_n, cos_phi = float(a["i_N_A"]), float(a.get("cos_phi", 0.9))
    mss = [k for k, d in art.items() if d["kategorie"] == "motorschutz" and d["bereich_A"][0] <= i_n <= d["bereich_A"][1]]
    if not mss:
        raise RegelFehler(f"{b.bmk}: kein Motorschutzschalter mit Einstellbereich für {i_n} A")
    mss_key = min(mss, key=lambda k: art[k]["bereich_A"][1])
    laenge = fg.get("laenge_m")
    if laenge not in (None, ""):
        try:
            laenge = float(str(laenge).replace(",", "."))
        except ValueError:
            raise RegelFehler(f"{b.bmk}: Leitungslänge '{fg.get('laenge_m')}' ist keine Zahl") from None
    try:
        if laenge in (None, ""):
            a_mm2, i_z, du = waehle_querschnitt(i_n, 0.0, cos_phi, ltg, lst.get("u_V", 230), lst.get("phasen", 1))
            du = None
            m.warnungen.append(f"{b.bmk}: Spannungsfall nicht geprüft – Leitungslänge fehlt (Excel-Spalte Länge)")
        else:
            a_mm2, i_z, du = waehle_querschnitt(i_n, laenge, cos_phi, ltg, lst.get("u_V", 230), lst.get("phasen", 1))
    except RegelFehler as e:
        raise RegelFehler(f"{b.bmk}: {e}") from None
    adern = lst.get("kabel_adern", 3)
    kab = [k for k, d in art.items() if d["kategorie"] == "kabel" and d["adern"] == adern and d["querschnitt_mm2"] == a_mm2]
    if not kab:
        raise RegelFehler(f"{b.bmk}: kein Kabel {adern} x {a_mm2} mm² im Gerätestamm")
    if not ltg.get("freigegeben", False):
        m.warnungen.append("Strombelastbarkeitstabelle (leitungen.i_z_A) nicht freigegeben – Querschnitte vorläufig")
    m.warnungen.append(f"{b.bmk}: 1~-Anschluss am Motorschutzschalter nach Herstellerangabe verdrahten "
                       f"(Strompfade ggf. in Reihe); Kurzschluss-/Abschaltbedingung der Leitung nicht geprüft")
    b.daten["leistung"] = {"i_N_A": i_n, "mss": f"{b.bmk}-Q1", "kabel": f"{b.bmk}-W2", "pins": lst.get("pins", {})}
    w = Kabel(f"{b.bmk}-W2", kab[0], f"{b.bmk}-Q1", b.bmk, adern, a_mm2, float(laenge or 0), i_n, round(i_z, 2),
              round(du, 2) if du is not None else -1.0)
    m.kabel.append(w)
    pins = lst.get("pins", {})
    for pot, innen in (("L", f"{b.bmk}-Q1:2"), ("N", f"{b.bmk}-Q1:4"), ("PE", "PE-Schiene")):
        if pot in pins:
            m.klemmen.append(Klemme("-X2", 0, pot, innen, f"{b.bmk}:{pins[pot]}"))
    return [Betriebsmittel(f"{b.bmk}-Q1", mss_key, art[mss_key]["bezeichnung"], f"Motorschutz {b.bmk}", "bauteil",
                           daten={"eltern": b.bmk, "lokal": "-Q1", "i_A": 0.0, "i_r_A": i_n, "gruppe": "-"}),
            Betriebsmittel(f"{b.bmk}-W2", kab[0], art[kab[0]]["bezeichnung"], f"Zuleitung {b.bmk}", "kabel",
                           daten={"eltern": b.bmk, "lokal": "-W2", "laenge_m": float(laenge or 0), "i_A": 0.0,
                                  "gruppe": "-"})]
