"""Typical „Motorabgang Direktstart“ (DOL): Motorschutzschalter, Schütz, Klemmen, Kabel, Motor.

Auslegung je Motor (alle Grenzwerte sind Projektparameter, siehe `leitungen`):
  Motorschutzschalter: Einstellbereich enthält I_N  -> Einstellstrom I_r = I_N
  Schütz:              kleinster AC-3-Bemessungsstrom >= I_N
  Leitung:             kleinster Querschnitt mit  I_z · f >= I_r  und  ΔU <= ΔU_max
                       ΔU = √3 · I_N · l · cos φ / (κ · A)   (ohmsche Näherung, l einfache Länge)
"""
from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

from .modell import Betriebsmittel, Kabel, Klemme, Planmodell, RegelFehler

MOTOREN_JE_SEITE = 4
ANLAUFARTEN = ("direkt", "fu")
FU_PFLICHT = {"p_kW": "Bemessungsleistung (p_kW)", "i_aus_A": "Ausgangsstrom (i_aus_A)",
              "i_ein_A": "Netzeingangsstrom (i_ein_A)", "vorsicherung_max_A": "max. Vorsicherung (vorsicherung_max_A)"}


class MotorFehler(RegelFehler):
    pass


def spannungsfall_prozent(i_A: float, l_m: float, cos_phi: float, kappa: float, a_mm2: float,
                          u_V: float = 400.0, phasen: int = 3) -> float:
    """Drehstrom: √3 · I · l · cos φ / (κ · A); Wechselstrom: Hin- und Rückleiter -> Faktor 2 statt √3."""
    faktor = math.sqrt(3) if phasen == 3 else 2.0
    return faktor * i_A * l_m * cos_phi / (kappa * a_mm2) / u_V * 100.0


def waehle_querschnitt(i_r: float, l_m: float, cos_phi: float, ltg: dict[str, Any],
                       u_V: float = 400.0, phasen: int = 3) -> tuple[float, float, float]:
    """-> (Querschnitt, I_z·f, ΔU %). Tabelle `i_z_A` {mm²: A} muss aufsteigend sinnvoll sein."""
    f = ltg.get("reduktionsfaktor", 1.0)
    if not ltg.get("i_z_A"):
        raise MotorFehler("Keine Strombelastbarkeitstabelle (Regeln: iz_…) angegeben")
    a_min = float(ltg.get("min_querschnitt_mm2") or 0)          # Hausregel (Lernschleife), z. B. 2,5 mm²
    for a in sorted(float(k) for k in ltg["i_z_A"]):
        if a < a_min:
            continue
        i_z = ltg["i_z_A"][a] if a in ltg["i_z_A"] else ltg["i_z_A"][str(a)]
        du = spannungsfall_prozent(i_r, l_m, cos_phi, ltg.get("kappa", 56), a, u_V, phasen)
        if i_z * f >= i_r and du <= ltg.get("du_max_prozent", 3.0):
            return a, i_z * f, du
    vorhanden = " / ".join(f"{float(k):g}" for k in sorted(float(k) for k in ltg["i_z_A"])).replace(".", ",")
    if a_min and a_min > max(float(k) for k in ltg["i_z_A"]):
        raise MotorFehler(f"Für {a_min:g} mm² (Mindestquerschnitt aus Hausregel) fehlt ein Wert in der "
                          f"Strombelastbarkeitstabelle – vorhanden: {vorhanden} mm². Tabelle in den Hausvorgaben ergänzen "
                          f"oder kleineren Mindestquerschnitt wählen".replace(".", ","))
    raise MotorFehler(f"Kein Querschnitt der Strombelastbarkeitstabelle ({vorhanden} mm²) reicht für {i_r:g} A bei "
                      f"{l_m:g} m Leitungslänge – Tabelle in den Hausvorgaben um größere Querschnitte ergänzen".replace(".", ","))


def ersatz(projekt: dict, key: str, art: dict, bmk: str, passt: Callable[..., bool], bedingung: str) -> str:
    """Hausregel „vom Programm gewähltes Gerät ersetzen“ anwenden; der Ersatz muss die Auslegung weiter erfüllen."""
    neu = (projekt.get("auswahl_ersetzen") or {}).get(key) if isinstance(projekt.get("auswahl_ersetzen"), dict) else None
    if not neu:
        return key
    if neu not in art or art[neu].get("kategorie") != art[key].get("kategorie") or not passt(art[neu]):
        raise MotorFehler(f"{bmk}: Hausregel ersetzt {key} durch {neu} – {neu} erfüllt nicht {bedingung}; Regel "
                          f"prüfen (Menü L)")
    return str(neu)


def plane_motoren(m: Planmodell, projekt: dict, art: dict, erste_seite: int) -> list[Betriebsmittel]:
    """Legt alle Motorabgänge an. Liefert die Signal-Betriebsmittel (Schütz = DO, MSS = DI)."""
    motoren = projekt.get("motoren", [])
    ltg = projekt.get("leitungen", {})
    if motoren:
        m.warnungen.append("Motorabgänge: Kurzschluss-/Abschaltbedingung der Leitungen (Schleifenimpedanz, "  # ANNAHME A5
                           "Schaltvermögen) nicht geprüft")
    if motoren and not ltg.get("freigegeben", False):
        m.warnungen.append("Strombelastbarkeitstabelle (leitungen.i_z_A) nicht freigegeben – "
                           "Querschnitte vorläufig")
    n_seiten = math.ceil(len(motoren) / MOTOREN_JE_SEITE)
    signale: list[Betriebsmittel] = []

    def kat(k):
        return [a for a, d in art.items() if d["kategorie"] == k]

    for i, mo in enumerate(motoren):
        nr = i + 1
        s_last = erste_seite + i // MOTOREN_JE_SEITE
        s_steu = s_last + n_seiten
        sp = 2 * (i % MOTOREN_JE_SEITE) + 1          # erste von zwei Spalten je Motor
        i_n = float(mo["i_N_A"])
        cos_phi = float(mo.get("cos_phi", 0.8))
        mbmk = "-" + mo["bmk"].lstrip("-")
        anlauf = str(mo.get("anlauf") or "direkt").strip().lower()
        if anlauf not in ANLAUFARTEN:
            raise MotorFehler(f"{mbmk}: Anlauf „{mo.get('anlauf')}“ unbekannt – erlaubt: {', '.join(ANLAUFARTEN)}")
        fu_key = ""
        i_netz = i_n                                   # Strom im Netzzweig (Motorschutzschalter, Außenleiter)
        if anlauf == "fu":
            # ANNAHME A51: kleinster FU mit I_aus >= I_N und P >= P_N; Motorschutzschalter als Leitungs-/Kurzschlussschutz
            # vor dem FU, eingestellt auf den Netzeingangsstrom laut Datenblatt; Motorschutz übernimmt der FU (I²t)
            for a in kat("fu"):                        # eigene FU-Artikel: Pflichtwerte im Klartext melden
                fehlt = [w for w in FU_PFLICHT if not isinstance(art[a].get(w), (int, float))]
                if fehlt:
                    raise MotorFehler(f"Artikel {a} (Frequenzumrichter): {', '.join(FU_PFLICHT[w] for w in fehlt)} "
                                      f"fehlt – bitte aus dem Datenblatt im Gerätestamm ergänzen")
            fus = [a for a in kat("fu") if float(art[a]["i_aus_A"]) >= i_n and float(art[a]["p_kW"]) >= float(mo["p_kW"])]
            if not fus:
                raise MotorFehler(f"{mbmk}: kein Frequenzumrichter mit I_aus ≥ {i_n:g} A und P ≥ {mo['p_kW']} kW im "
                                  f"Gerätestamm (Kategorie fu)".replace(".", ","))
            fu_key = min(fus, key=lambda a: float(art[a]["i_aus_A"]))
            fu_key = ersatz(projekt, fu_key, art, mbmk, lambda d, i=i_n, p=float(mo["p_kW"]): float(d.get("i_aus_A", 0)) >= i
                            and float(d.get("p_kW", 0)) >= p and isinstance(d.get("i_ein_A"), (int, float)),
                            f"I_aus ≥ {i_n:g} A und P ≥ {mo['p_kW']} kW")
            i_netz = float(art[fu_key]["i_ein_A"])

        mss = [a for a in kat("motorschutz") if art[a]["bereich_A"][0] <= i_netz <= art[a]["bereich_A"][1]]
        if not mss:
            raise MotorFehler(f"{mbmk}: kein Motorschutzschalter mit Einstellbereich für {i_netz:g} A".replace(".", ","))
        mss_key = min(mss, key=lambda a: art[a]["bereich_A"][1])
        mss_key = ersatz(projekt, mss_key, art, mbmk, lambda d, i=i_netz: d["bereich_A"][0] <= i <= d["bereich_A"][1],
                         f"Einstellbereich mit {i_netz:g} A")
        if fu_key and art[mss_key]["bereich_A"][1] > float(art[fu_key]["vorsicherung_max_A"]):
            raise MotorFehler(f"{mbmk}: Motorschutzschalter {mss_key} über der zulässigen Vorsicherung von {fu_key} "
                              f"({art[fu_key]['vorsicherung_max_A']} A laut Datenblatt)")
        if not fu_key:
            sch = [a for a in kat("schuetz") if art[a]["ac3_A"] >= i_n]
            if not sch:
                raise MotorFehler(f"Kein Schütz mit AC-3 >= {i_n} A")
            sch_key = min(sch, key=lambda a: art[a]["ac3_A"])
            sch_key = ersatz(projekt, sch_key, art, mbmk, lambda d, i=i_n: float(d.get("ac3_A", 0)) >= i,
                             f"AC-3 ≥ {i_n:g} A")
        # Motorleitung hinter dem FU: Strom begrenzt der FU (bis I_aus), nicht der MSS davor -> Bemessung nach I_aus
        i_ltg = float(art[fu_key]["i_aus_A"]) if fu_key else i_n                      # ANNAHME A51
        a_mm2, i_z, du = waehle_querschnitt(i_ltg, float(mo["laenge_m"]), cos_phi, ltg)
        kab = [a for a in kat("kabel") if art[a]["adern"] == 4 and art[a]["querschnitt_mm2"] == a_mm2
               and bool(art[a].get("geschirmt")) == bool(fu_key)]
        if not kab:
            raise MotorFehler(f"{mbmk}: kein Kabel 4 x {a_mm2:g} mm²{' geschirmt (geschirmt: true)' if fu_key else ''} "
                              f"im Gerätestamm".replace(".", ","))

        q = Betriebsmittel(f"-Q{nr + 1}", mss_key, art[mss_key]["bezeichnung"], f"Schutz {mbmk}",
                           "motorschutz", s_last, sp,
                           {"i_r_A": i_netz, "signal": "DI", "i_A": 0.0, "gruppe": "SPS",
                            "steuer_seite": s_steu, "steuer_spalte": sp + 1,
                            "funktion_sps": f"Rückmeldung {mbmk} {mo.get('funktion', '')}".strip()})
        teile: list[Betriebsmittel] = []
        if fu_key:
            k = Betriebsmittel(f"-T{nr}", fu_key, art[fu_key]["bezeichnung"], f"Frequenzumrichter {mbmk}",
                               "fu", s_last, sp + 1,
                               {"signal": "DO", "i_A": float(art[fu_key].get("i_steuer_A", 0.01)), "gruppe": "DO-Last",
                                "steuer_seite": s_steu, "steuer_spalte": sp, "i_aus_A": art[fu_key]["i_aus_A"],
                                "i_r_A": float(art[fu_key]["i_aus_A"]),     # Stromgrenze = Schutz der Motorleitung
                                "funktion_sps": f"Freigabe {mbmk} {mo.get('funktion', '')}".strip(),
                                "teilsignale": [f"-T{nr}.2", f"-T{nr}.3"]})
            for nr_t, sig, text, pin, gruppe in ((2, "AO", "Sollwert Drehzahl", "AI1", "-"),
                                                 (3, "DI", "Störung", "RL1", "SPS")):
                teile.append(Betriebsmittel(f"-T{nr}.{nr_t}", "", f"{text} {mbmk}", f"{text} {mbmk}".strip(),
                                            "teilsignal", s_last, sp + 1,
                                            {"signal": sig, "i_A": 0.0, "gruppe": gruppe, "eltern": k.bmk,
                                             "fu_pin": pin, "steuer_seite": s_steu, "steuer_spalte": sp + 1}))
            m.warnungen.append(f"{mbmk}: Frequenzumrichter {fu_key} – Vorsicherung, EMV (Schirmauflage beidseitig), "
                               f"Ableitstrom/RCD-Typ/PE, Motorschutz-Parameter (I²t = I_N) und Stromgrenze ≤ I_aus "
                               f"nach Herstellerangabe; STO (sicher abgeschaltetes Moment) nur als Platzhalter (A49/A51)")
        else:
            k = Betriebsmittel(f"-K{nr}", sch_key, art[sch_key]["bezeichnung"], f"Schütz {mbmk}",
                               "schuetz", s_last, sp + 1,
                               {"signal": "DO", "i_A": art[sch_key]["spule_W"] / 24.0, "gruppe": "DO-Last",
                                "steuer_seite": s_steu, "steuer_spalte": sp,
                                "funktion_sps": f"Ein {mbmk} {mo.get('funktion', '')}".strip()})
        w = Kabel(f"-W{nr}", kab[0], "-X2", mbmk, 4, a_mm2, float(mo["laenge_m"]), i_ltg,
                  round(i_z, 2), round(du, 2), s_last, sp + 1)
        mot = Betriebsmittel(mbmk, mo.get("artikel", "KUNDE"), f"Drehstrommotor {mo['p_kW']} kW",
                             mo.get("funktion", ""), "motor", s_last, sp,
                             {"p_kW": mo["p_kW"], "i_N_A": i_n, "cos_phi": cos_phi, "kabel": w.bmk,
                              "mss": q.bmk, "schuetz": "" if fu_key else k.bmk, "fu": k.bmk if fu_key else "",
                              "anlauf": anlauf, "i_netz_A": i_netz})
        m.kabel.append(w)
        m.betriebsmittel.append(Betriebsmittel(w.bmk, kab[0], art[kab[0]]["bezeichnung"],
                                               f"Zuleitung {mbmk}", "kabel", s_last, sp + 1,
                                               {"laenge_m": w.laenge_m}))
        for j, ader in enumerate(("U", "V", "W", "PE")):
            m.klemmen.append(Klemme("-X2", 4 * i + j + 1, ader, (f"{k.bmk}:{ader}" if fu_key else k.bmk)
                                    if ader != "PE" else "PE-Schiene",
                                    f"{mbmk}:{ader}1" if ader != "PE" else f"{mbmk}:PE", s_last, sp))
        # Signale: Funktionstext für die SPS-Liste
        q.funktion, k.funktion = q.daten["funktion_sps"], k.daten["funktion_sps"]
        m.betriebsmittel.extend([q, k, *teile, mot])
        signale.extend([k, q, *teile])
    if motoren:
        n_kl = 4 * len(motoren)
        m.betriebsmittel.append(Betriebsmittel("-X2", "RK-4", art["RK-4"]["bezeichnung"], "Klemmleiste Motoren",
                                               "klemme", daten={"anzahl": n_kl}))
    return signale
