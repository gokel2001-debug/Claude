"""Typical „Motorabgang Direktstart“ (DOL): Motorschutzschalter, Schütz, Klemmen, Kabel, Motor.

Auslegung je Motor (alle Grenzwerte sind Projektparameter, siehe `leitungen`):
  Motorschutzschalter: Einstellbereich enthält I_N  -> Einstellstrom I_r = I_N
  Schütz:              kleinster AC-3-Bemessungsstrom >= I_N
  Leitung:             kleinster Querschnitt mit  I_z · f >= I_r  und  ΔU <= ΔU_max
                       ΔU = √3 · I_N · l · cos φ / (κ · A)   (ohmsche Näherung, l einfache Länge)
"""
from __future__ import annotations

import math
from typing import Any

from .modell import Betriebsmittel, Kabel, Klemme, Planmodell, RegelFehler

MOTOREN_JE_SEITE = 4


class MotorFehler(RegelFehler):
    pass


def spannungsfall_prozent(i_A: float, l_m: float, cos_phi: float, kappa: float, a_mm2: float,
                          u_V: float = 400.0) -> float:
    return math.sqrt(3) * i_A * l_m * cos_phi / (kappa * a_mm2) / u_V * 100.0


def waehle_querschnitt(i_r: float, l_m: float, cos_phi: float, ltg: dict[str, Any]) -> tuple[float, float, float]:
    """-> (Querschnitt, I_z·f, ΔU %). Tabelle `i_z_A` {mm²: A} muss aufsteigend sinnvoll sein."""
    f = ltg.get("reduktionsfaktor", 1.0)
    for a in sorted(float(k) for k in ltg["i_z_A"]):
        i_z = ltg["i_z_A"][a] if a in ltg["i_z_A"] else ltg["i_z_A"][str(a)]
        du = spannungsfall_prozent(i_r, l_m, cos_phi, ltg.get("kappa", 56), a)
        if i_z * f >= i_r and du <= ltg.get("du_max_prozent", 3.0):
            return a, i_z * f, du
    raise MotorFehler(f"Kein Querschnitt in Tabelle i_z_A erfüllt I_r = {i_r} A / l = {l_m} m "
                      f"-> Tabelle erweitern (Normwerte eintragen)")


def plane_motoren(m: Planmodell, projekt: dict, art: dict, erste_seite: int) -> list[Betriebsmittel]:
    """Legt alle Motorabgänge an. Liefert die Signal-Betriebsmittel (Schütz = DO, MSS = DI)."""
    motoren = projekt.get("motoren", [])
    ltg = projekt.get("leitungen", {})
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

        mss = [a for a in kat("motorschutz") if art[a]["bereich_A"][0] <= i_n <= art[a]["bereich_A"][1]]
        if not mss:
            raise MotorFehler(f"Kein Motorschutzschalter mit Einstellbereich für {i_n} A")
        mss_key = min(mss, key=lambda a: art[a]["bereich_A"][1])
        sch = [a for a in kat("schuetz") if art[a]["ac3_A"] >= i_n]
        if not sch:
            raise MotorFehler(f"Kein Schütz mit AC-3 >= {i_n} A")
        sch_key = min(sch, key=lambda a: art[a]["ac3_A"])
        a_mm2, i_z, du = waehle_querschnitt(i_n, float(mo["laenge_m"]), cos_phi, ltg)
        kab = [a for a in kat("kabel") if art[a]["adern"] == 4 and art[a]["querschnitt_mm2"] == a_mm2]
        if not kab:
            raise MotorFehler(f"Kein Kabel 4 x {a_mm2} mm² im Gerätestamm")

        mbmk = "-" + mo["bmk"].lstrip("-")
        q = Betriebsmittel(f"-Q{nr + 1}", mss_key, art[mss_key]["bezeichnung"], f"Schutz {mbmk}",
                           "motorschutz", s_last, sp,
                           {"i_r_A": i_n, "signal": "DI", "i_A": 0.0, "gruppe": "SPS",
                            "steuer_seite": s_steu, "steuer_spalte": sp + 1,
                            "funktion_sps": f"Rückmeldung {mbmk} {mo.get('funktion', '')}".strip()})
        k = Betriebsmittel(f"-K{nr}", sch_key, art[sch_key]["bezeichnung"], f"Schütz {mbmk}",
                           "schuetz", s_last, sp + 1,
                           {"signal": "DO", "i_A": art[sch_key]["spule_W"] / 24.0, "gruppe": "DO-Last",
                            "steuer_seite": s_steu, "steuer_spalte": sp,
                            "funktion_sps": f"Ein {mbmk} {mo.get('funktion', '')}".strip()})
        w = Kabel(f"-W{nr}", kab[0], f"-X2", mbmk, 4, a_mm2, float(mo["laenge_m"]), i_n,
                  round(i_z, 2), round(du, 2), s_last, sp + 1)
        mot = Betriebsmittel(mbmk, mo.get("artikel", "KUNDE"), f"Drehstrommotor {mo['p_kW']} kW",
                             mo.get("funktion", ""), "motor", s_last, sp,
                             {"p_kW": mo["p_kW"], "i_N_A": i_n, "cos_phi": cos_phi, "kabel": w.bmk})
        m.kabel.append(w)
        m.betriebsmittel.append(Betriebsmittel(w.bmk, kab[0], art[kab[0]]["bezeichnung"],
                                               f"Zuleitung {mbmk}", "kabel", s_last, sp + 1,
                                               {"laenge_m": w.laenge_m}))
        for j, ader in enumerate(("U", "V", "W", "PE")):
            m.klemmen.append(Klemme("-X2", 4 * i + j + 1, ader, f"-K{nr}" if ader != "PE" else "PE-Schiene",
                                    f"{mbmk}:{ader}1" if ader != "PE" else f"{mbmk}:PE", s_last, sp))
        # Signale: Funktionstext für die SPS-Liste
        q.funktion, k.funktion = q.daten["funktion_sps"], k.daten["funktion_sps"]
        m.betriebsmittel.extend([q, k, mot])
        signale.extend([k, q])
    if motoren:
        n_kl = 4 * len(motoren)
        m.betriebsmittel.append(Betriebsmittel("-X2", "RK-4", art["RK-4"]["bezeichnung"], "Klemmleiste Motoren",
                                               "klemme", daten={"anzahl": n_kl}))
    return signale
