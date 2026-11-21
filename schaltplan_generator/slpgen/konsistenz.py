"""Konsistenzprüfungen am Planmodell -> Prüfbericht.

Jede Prüfung liefert Befunde der Art FEHLER (Plan widersprüchlich, nicht für die Fertigung) oder HINWEIS
(auffällig, bitte ansehen), jeweils mit Quelle der Regel. Der Bericht wird bei JEDER Ausgabe frisch berechnet
(`cli._ausgabe`, Auslegungsnachweis) und ist über `python -m slpgen pruefbericht <planmodell.json>` abrufbar.
"""
from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass

from .modell import SAMMELMELDUNG, Planmodell, eltern_bmk

FEHLER, HINWEIS = "FEHLER", "HINWEIS"
PLANLOGIK = "Planlogik (Widerspruch im Plan)"
Q_LEITUNGSSCHUTZ = "I_B ≤ I_n ≤ I_z nach IEC 60364-4-43 Abschn. 433.1 (Abschnitt nicht online verifiziert)"
Q_SPANNUNGSFALL = "zulässiger Spannungsfall laut Hausvorgabe (Annahme A4)"
Q_MSS = "Einstellbereich laut Gerätestamm/Datenblatt"


@dataclass(frozen=True)
class Befund:
    art: str          # FEHLER | HINWEIS
    pruefung: str     # kurzer Name der Prüfung
    text: str
    quelle: str = PLANLOGIK


def pruefe_plan(m: Planmodell) -> list[Befund]:
    pruefungen: list[Callable[[Planmodell], list[Befund]]] = [
        _bmk_eindeutig, _verweise, _klemmen, _potentiale, _sps, _absicherungen, _netzteil, _do_last, _leitungen,
        _motorschutz, _sicherheit, _texte]
    befunde: list[Befund] = []
    for f in pruefungen:
        try:
            befunde.extend(f(m))
        except (KeyError, TypeError, ValueError, IndexError, AttributeError) as e:     # handbearbeitetes Modell
            befunde.append(Befund(FEHLER, "Daten", f"Prüfung {f.__name__.strip('_')} nicht möglich – Planmodell "
                                                   f"enthält ungültige Werte ({type(e).__name__}: {e})"))
    return befunde


def _bmk_eindeutig(m: Planmodell) -> list[Befund]:
    doppelt = [k for k, n in Counter(x.bmk for x in m.betriebsmittel).items() if n > 1]
    befunde = [Befund(FEHLER, "Kennzeichen", f"Betriebsmittelkennzeichen {k} ist mehrfach vergeben") for k in doppelt]
    if m.kennzeichen:
        hs = Counter(tuple(v) for v in m.kennzeichen.values())
        befunde += [Befund(FEHLER, "Kennzeichen", f"Kennzeichen im Hausstil ={a}{lok} ist mehrfach vergeben")
                    for (a, lok), n in hs.items() if n > 1]
    return befunde


def _bekannt(m: Planmodell) -> set[str]:
    return {x.bmk for x in m.betriebsmittel} | {"PE-Schiene", SAMMELMELDUNG}


def _verweise(m: Planmodell) -> list[Befund]:
    """Jeder Verweis (Kanal, Abgang, Kabel, Klemme) zeigt auf ein vorhandenes Betriebsmittel bzw. eine Leiste."""
    bekannt = _bekannt(m)
    leisten = {k.leiste for k in m.klemmen}
    teile = bekannt | {t for x in m.betriebsmittel for t in x.daten.get("teilsignale", [])}
    befunde = []
    for kanal in m.sps_kanaele:
        if kanal.geraet_bmk not in teile and eltern_bmk(kanal.geraet_bmk) not in bekannt:
            befunde.append(Befund(FEHLER, "Verweis", f"SPS-Kanal {kanal.adresse}: Gerät {kanal.geraet_bmk} gibt es nicht"))
        if kanal.anschluss and kanal.anschluss.rsplit(":", 1)[0] not in bekannt:
            befunde.append(Befund(FEHLER, "Verweis", f"SPS-Kanal {kanal.adresse}: Anschluss {kanal.anschluss} gibt es nicht"))
    for a in m.absicherungen:
        befunde += [Befund(FEHLER, "Verweis", f"Abgang {a.bmk}: Verbraucher {v} gibt es nicht")
                    for v in a.verbraucher if v not in bekannt]
    for c in m.kabel:
        for ende in (c.von, c.nach):
            ziel = ende.split(":")[0]
            if ziel not in bekannt and ziel not in leisten:
                befunde.append(Befund(FEHLER, "Verweis", f"Kabel {c.bmk}: Ende {ende} gibt es nicht"))
    for k in m.klemmen:
        geraet = k.ziel_aussen.split(":")[0]
        if geraet not in bekannt:
            befunde.append(Befund(FEHLER, "Verweis", f"Klemme {k.leiste}:{k.nr}: Feldgerät {geraet} gibt es nicht"))
    return befunde


def _klemmen(m: Planmodell) -> list[Befund]:
    """Klemmennummern je Leiste ≥ 1, eindeutig, lückenlos; kein Geräteanschluss doppelt."""
    befunde = []
    je_leiste: dict[str, list[int]] = {}
    for k in m.klemmen:
        je_leiste.setdefault(k.leiste, []).append(int(k.nr))
    for leiste, nrn in je_leiste.items():
        if min(nrn) < 1:
            befunde.append(Befund(FEHLER, "Klemmen", f"Leiste {leiste}: Klemmennummer {min(nrn)} ungültig (ab 1)"))
        doppelt = sorted(n for n, c in Counter(nrn).items() if c > 1)
        if doppelt:
            befunde.append(Befund(FEHLER, "Klemmen", f"Leiste {leiste}: Klemme {', '.join(map(str, doppelt))} doppelt belegt"))
        luecken = sorted(set(range(1, max(nrn) + 1)) - set(nrn))
        if luecken:
            befunde.append(Befund(HINWEIS, "Klemmen", f"Leiste {leiste}: Lücke bei Klemme {', '.join(map(str, luecken[:10]))}"))
    for ziel, n in Counter(k.ziel_aussen for k in m.klemmen).items():
        if n > 1:
            befunde.append(Befund(FEHLER, "Klemmen", f"Geräteanschluss {ziel} liegt auf {n} Klemmen"))
    return befunde


def _potentiale(m: Planmodell) -> list[Befund]:
    """Kein offenes Potential: jedes Gerät mit 24L+-Klemme hängt an einem 24-V-Abgang."""
    versorgt = {v for a in m.absicherungen for v in a.verbraucher}
    befunde = []
    for k in m.klemmen:
        geraet = k.ziel_aussen.split(":")[0]
        if k.potential == "+24V" and geraet not in versorgt:
            befunde.append(Befund(FEHLER, "Potential", f"Klemme {k.leiste}:{k.nr} führt 24L+ zu {geraet}, das an keinem "
                                                      f"24-V-Abgang hängt (offenes Potential)"))
    return befunde


def _sps(m: Planmodell) -> list[Befund]:
    """Adressen und Kanäle eindeutig, Kanal innerhalb der Karte, Bytebereiche der Karten überschneidungsfrei."""
    befunde = []
    for adr, n in Counter(k.adresse for k in m.sps_kanaele).items():
        if n > 1:
            befunde.append(Befund(FEHLER, "SPS", f"Adresse {adr} ist {n}-mal vergeben"))
    for (modul, nr), n in Counter((k.modul_bmk, k.kanal) for k in m.sps_kanaele).items():
        if n > 1:
            befunde.append(Befund(FEHLER, "SPS", f"Karte {modul} Kanal {nr} ist {n}-mal belegt"))
    karten = {x.bmk: x for x in m.betriebsmittel if x.kategorie in ("sps_di", "sps_do", "sps_ai", "sps_ao")}
    for k in m.sps_kanaele:
        karte = karten.get(k.modul_bmk)
        if karte is None:
            befunde.append(Befund(FEHLER, "SPS", f"Kanal {k.adresse}: Karte {k.modul_bmk} gibt es nicht"))
            continue
        gesamt = int(m.artikel.get(karte.artikel, {}).get("kanaele", 0))
        if gesamt and k.kanal >= gesamt:
            befunde.append(Befund(FEHLER, "SPS", f"Kanal {k.kanal} auf {k.modul_bmk} – Karte hat nur {gesamt} Kanäle"))
    for bereich in (("sps_di", "sps_ai"), ("sps_do", "sps_ao")):
        belegt: Counter[int] = Counter()
        for x in karten.values():
            if x.kategorie in bereich and x.daten.get("bytebereich"):
                von, bis = x.daten["bytebereich"]
                belegt.update(range(int(von), int(bis) + 1))
        doppelt = sorted(n for n, c in belegt.items() if c > 1)
        if doppelt:
            befunde.append(Befund(FEHLER, "SPS", f"Adressbereiche überschneiden sich (Byte {doppelt[0]}…{doppelt[-1]})"))
    return befunde


def _absicherungen(m: Planmodell) -> list[Befund]:
    """24-V-Abgänge: Gruppenstrom ≤ Sicherung; kein Verbraucher ohne 24-V-Strom und ohne Kontaktspeisung."""
    befunde = []
    bm = {x.bmk: x for x in m.betriebsmittel}

    def ohne_grund(v: str) -> bool:
        x = bm.get(v)
        return (x is not None and float(x.daten.get("i_A", 0) or 0) == 0 and x.kategorie not in ("motorschutz", "meldung")
                and not x.daten.get("versorgt") and not x.daten.get("fu_pin"))     # FU-Störrelais = Kontaktspeisung

    for a in m.absicherungen:
        if a.i_gruppe_A > a.i_nenn_A:
            befunde.append(Befund(FEHLER, "Absicherung", f"Abgang {a.bmk}: Gruppenstrom {a.i_gruppe_A} A > Sicherung "
                                                        f"{a.i_nenn_A} A", Q_LEITUNGSSCHUTZ))
        ohne = [v for v in a.verbraucher if ohne_grund(v)]
        if ohne:
            befunde.append(Befund(HINWEIS, "Absicherung", f"Abgang {a.bmk}: {', '.join(ohne)} ohne 24-V-Strom in der "
                                                          f"Verbraucherliste (fremdversorgt oder 230 V?)"))
    return befunde


def _netzteil(m: Planmodell) -> list[Befund]:
    """24-V-Bedarf (mit Gleichzeitigkeit und Reserve) ≤ Nennstrom des gewählten Netzteils."""
    bil = m.bilanz
    if not bil:
        return []
    if float(bil["i_bedarf_A"]) > float(bil["i_nenn_A"]):
        return [Befund(FEHLER, "Netzteil", f"Bedarf {bil['i_bedarf_A']} A (Summe {bil['i_summe_A']} A mit Gleichzeitigkeit und "
                                           f"Reserve) > Nennstrom {bil['i_nenn_A']} A ({bil['netzteil']}) – größeres Netzteil",
                       "Datenblatt Netzteil; Gleichzeitigkeit/Reserve laut Hausvorgabe (A1)")]
    return []


def _do_last(m: Planmodell) -> list[Befund]:
    """Strom am DO-Kanal (Gerät bzw. Relais-/Schützspule) ≤ Ausgangsstrom je Kanal der Karte."""
    befunde = []
    bm = {x.bmk: x for x in m.betriebsmittel}
    for k in m.sps_kanaele:
        if k.art != "DO":
            continue
        karte = bm.get(k.modul_bmk)
        grenze = m.artikel.get(karte.artikel, {}).get("i_kanal_A") if karte else None
        if grenze is None:
            befunde.append(Befund(HINWEIS, "DO-Last", f"Kanal {k.adresse}: nicht geprüft – Kanalstrom (i_kanal_A) der Karte "
                                                     f"fehlt im Gerätestamm", "Datenblatt E/A-Karte"))
            continue
        teilsignal = k.geraet_bmk != eltern_bmk(k.geraet_bmk)
        last = bm.get(k.anschluss.rsplit(":", 1)[0]) if k.anschluss else (None if teilsignal else bm.get(k.geraet_bmk))
        if last is None:
            befunde.append(Befund(HINWEIS, "DO-Last", f"Kanal {k.adresse}: Last am Steuereingang von {k.geraet_bmk} "
                                                     f"unbekannt – nicht geprüft", "Datenblatt Gerät"))
            continue
        strom = float(last.daten.get("i_A", 0) or 0)
        if strom > float(grenze):
            befunde.append(Befund(FEHLER, "DO-Last", f"Kanal {k.adresse}: {last.bmk} braucht {strom:.2f} A > {grenze} A je Kanal "
                                                    f"– Koppelrelais vorsehen", "Datenblatt E/A-Karte (i_kanal_A)"))
    return befunde


def _schutzorgan_je_kabel(m: Planmodell) -> dict[str, str]:
    """Kabel -> Motorschutzschalter, der es schützt (Motor-Direktstart und Bausteine mit Leistungsteil)."""
    zuordnung = {}
    for x in m.betriebsmittel:
        if x.kategorie == "motor":            # hinter einem FU schützt dessen Stromgrenze die Motorleitung (A51)
            zuordnung[x.daten["kabel"]] = x.daten.get("fu") or x.daten["mss"]
        if x.daten.get("leistung"):
            zuordnung[x.daten["leistung"]["kabel"]] = x.daten["leistung"]["mss"]
    return zuordnung


def _leitungen(m: Planmodell) -> list[Befund]:
    """Leitungsschutz I_B ≤ I_n ≤ I_z und Spannungsfall je Motor-/Leistungsleitung."""
    befunde = []
    bm = {x.bmk: x for x in m.betriebsmittel}
    schutz = _schutzorgan_je_kabel(m)
    du_max = float(m.bilanz.get("du_max_prozent", 3.0))
    for c in m.kabel:
        mss = bm.get(schutz.get(c.bmk, ""))
        if mss is None:
            befunde.append(Befund(HINWEIS, "Leitungsschutz", f"Kabel {c.bmk}: kein Schutzorgan zugeordnet – Schutz nicht geprüft"))
            continue
        i_n = float(mss.daten.get("i_r_A", 0))
        if not c.i_b_A <= i_n <= c.i_z_A:
            befunde.append(Befund(FEHLER, "Leitungsschutz", f"Kabel {c.bmk}: I_B {c.i_b_A} A ≤ I_n {i_n} A ≤ I_z {c.i_z_A} A "
                                                           f"nicht erfüllt (Schutz {mss.bmk})", Q_LEITUNGSSCHUTZ))
        if c.du_prozent > du_max:
            befunde.append(Befund(FEHLER, "Spannungsfall", f"Kabel {c.bmk}: ΔU {c.du_prozent} % > {du_max} %", Q_SPANNUNGSFALL))
    return befunde


def _motorschutz(m: Planmodell) -> list[Befund]:
    """Einstellwert des Motorschutzschalters im Einstellbereich des Artikels und gleich dem Bemessungsstrom."""
    befunde = []
    bm = {x.bmk: x for x in m.betriebsmittel}
    paare = [(x.daten["mss"], float(x.daten.get("i_netz_A", x.daten["i_N_A"]))) for x in m.betriebsmittel
             if x.kategorie == "motor"]
    paare += [(x.daten["leistung"]["mss"], float(x.daten["leistung"]["i_N_A"])) for x in m.betriebsmittel
              if x.daten.get("leistung")]
    for mss_bmk, i_nenn in paare:
        mss = bm.get(mss_bmk)
        if mss is None:
            continue
        i_r = float(mss.daten.get("i_r_A", 0))
        bereich = m.artikel.get(mss.artikel, {}).get("bereich_A")
        if bereich and not float(bereich[0]) <= i_r <= float(bereich[1]):
            befunde.append(Befund(FEHLER, "Motorschutz", f"{mss_bmk}: Einstellwert {i_r} A außerhalb des Bereichs "
                                                        f"{bereich[0]}–{bereich[1]} A ({mss.artikel})", Q_MSS))
        if abs(i_r - i_nenn) > 1e-6:
            befunde.append(Befund(HINWEIS, "Motorschutz", f"{mss_bmk}: Einstellwert {i_r} A ≠ Bemessungsstrom {i_nenn} A", Q_MSS))
    return befunde


SI_QUELLE = ("EN 60204-1:2018 Abschn. 9.2.3.4.2 (Not-Halt); EN ISO 13849-1:2023 Abschn. 4 (PL_r) – Abschnitte vor "
             "Freigabe gegen die Normausgabe prüfen; ANNAHME A49")


def _sicherheit(m: Planmodell) -> list[Befund]:
    """Sicherheitsfunktionen sind nur Platzhalter: ohne Freigabevermerk FEHLER (= Stempel „nicht für Fertigung“)."""
    si = m.projekt.get("_sicherheit")
    if not si:
        return []
    if not isinstance(si, dict):
        return [Befund(FEHLER, "Sicherheit", "Angabe zur Sicherheit im Planmodell unlesbar – Plan neu erzeugen", SI_QUELLE)]
    if si.get("freigabe"):
        befunde = [Befund(HINWEIS, "Sicherheit", f"Sicherheitsfunktion im Plan nur als Platzhalter; Freigabevermerk: "
                                                 f"{si['freigabe']} (Auslegung außerhalb dieses Plans)", SI_QUELLE)]
    else:
        befunde = [Befund(FEHLER, "Sicherheit", (si.get("freigabe_problem") or "Sicherheitsfunktion nicht ausgelegt")
                          + " (nur Platzhalterseite SIK) – Auslegung durch Elektrofachkraft, danach Freigabevermerk "
                            "„Name, Datum“ im Excel-Blatt Sicherheit eintragen", SI_QUELLE)]
    treffer = si.get("treffer") or {}
    for g in si.get("geraete", []):          # bleibt auch mit Freigabevermerk, außer ausdrücklich ausgenommen
        if g in (si.get("ausgenommen") or []):
            befunde.append(Befund(HINWEIS, "Sicherheit", f"{g}: von der Elektrofachkraft als nicht sicherheitsbezogen "
                                                         f"ausgenommen (Standard-SPS)", SI_QUELLE))
        else:
            befunde.append(Befund(FEHLER, "Sicherheit", f"{g} („{treffer.get(g, '?')}“): sicherheitsbezogenes Gerät liegt "
                                                        f"an einem Standard-SPS-Eingang – Anschluss nur über "
                                                        f"Sicherheitsschaltgerät/-steuerung; durch Elektrofachkraft "
                                                        f"festlegen oder unter „ausgenommen“ eintragen", SI_QUELLE))
    return befunde


def _texte(m: Planmodell) -> list[Befund]:
    """Funktionstexte ohne Wortdopplung („Durchfluss Durchfluss“)."""
    befunde = []
    for k in m.sps_kanaele:
        if re.search(r"\b(\w{3,})\s+\1\b", k.funktion, re.I):
            befunde.append(Befund(HINWEIS, "Text", f"Kanal {k.adresse}: Wort doppelt im Funktionstext „{k.funktion}“"))
    return befunde


def bericht_text(befunde: list[Befund]) -> list[str]:
    if not befunde:
        return ["Prüfbericht: keine Befunde"]
    n_f = sum(1 for x in befunde if x.art == FEHLER)
    zeilen = [f"Prüfbericht: {n_f} Fehler, {len(befunde) - n_f} Hinweise"]
    for x in sorted(befunde, key=lambda x: x.art != FEHLER):
        zeilen.append(f"{x.art} ({x.pruefung}): {x.text}" + ("" if x.quelle == PLANLOGIK else f" – Quelle: {x.quelle}"))
    return zeilen


# Zeitansatz für die Kennzahl – ANNAHME A36: Erfahrungswerte fehlen; Platzhalter bis zu Werten aus Hausprofil/Abnahme M8.
MINUTEN_JE = {"Seite": 20.0, "Betriebsmittel": 3.0, "Klemme": 1.0, "SPS-Kanal": 2.0, "Kabel": 2.0}
KENNZAHL = "Stunden Zeichenaufwand (entfällt bei Übernahme ohne Nacharbeit; Annahme A36)"


def kennzahlen(m: Planmodell, seiten_hausstil: int) -> dict[str, float]:
    """Mengen des Plans im Hausstil × Zeitansatz. Kabel = Motor-/Leistungsleitungen + je Feldgerät eine Feldleitung."""
    feldgeraete = [b for b in m.betriebsmittel if b.kategorie in ("sensor", "aktor")]
    mengen = {"Seite": float(seiten_hausstil),
              "Betriebsmittel": float(len([b for b in m.betriebsmittel if b.kategorie not in ("teilsignal", "kabel")])),
              "Klemme": float(len(m.klemmen)), "SPS-Kanal": float(len(m.sps_kanaele)),
              "Kabel": float(len(m.kabel) + len(feldgeraete))}
    mengen[KENNZAHL] = round(sum(mengen[k] * MINUTEN_JE[k] for k in MINUTEN_JE) / 60, 1)
    return mengen
