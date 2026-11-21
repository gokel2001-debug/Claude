"""Kommandozeile: python -m slpgen <befehl> ..."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import traceback
from pathlib import Path

import yaml

from . import analyse, regeln, zeichnen
from .modell import Planmodell

PROG = Path(__file__).resolve().parent.parent          # Programmordner (start.bat liegt dort)
PROFIL = str(PROG / "hausprofil" / "profil.yaml")      # fester Ort, unabhängig vom aktuellen Ordner
STAMM = str(PROG / "beispiele" / "geraetestamm.yaml")
VORGABEN = str(PROG / "beispiele" / "hausvorgaben.yaml")


class _Lader(yaml.SafeLoader):
    """SafeLoader, der doppelte Schlüssel meldet statt still zu überschreiben."""


def _mapping(loader, node, deep=False):
    schluessel = set()
    for k, _ in node.value:
        name = loader.construct_object(k, deep=deep)
        if name in schluessel:
            raise regeln.RegelFehler(f"„{name}“ steht doppelt (Zeile {k.start_mark.line + 1}) – "
                                     f"Einträge zusammenführen, sonst geht einer verloren")
        schluessel.add(name)
    return loader.construct_mapping(node, deep=deep)


class _ZeilenLader(_Lader):
    """Wie _Lader; Einträge mit Kennzeichen (Feldgeräte, Motoren) merken sich ihre Zeile für Prüfmeldungen."""


def _mapping_mit_zeile(loader, node, deep=False):
    d = _mapping(loader, node, deep=deep)
    if "bmk" in d:
        d["_zeile"] = node.start_mark.line + 1
    return d


_Lader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)
_ZeilenLader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping_mit_zeile)
MENUE = os.environ.get("SLPGEN_MENUE") == "1"          # aus start.bat: Hinweise mit Menüpunkten statt Befehlen


RE_KOMMAZAHL = re.compile(r"(:\s*-?\d+),(\d+)(?=\s*[a-zA-Z%²]*\s*[,}])")


def _bereinige(text: str) -> str:
    """KI-Antworten: Codeblock ```yaml … ```, Einleitungs- und Schlusssätze ausblenden.

    Ausgeblendete Zeilen werden leer, nicht entfernt – so stimmen Zeilennummern in Meldungen mit der Datei überein.
    """
    zeilen = text.splitlines()
    zaune = [n for n, z in enumerate(zeilen) if z.lstrip().startswith("```")]
    if len(zaune) >= 2:
        a, b = zaune[0], zaune[1]
        zeilen = ["" if not a < n < b else z for n, z in enumerate(zeilen)]
    for n, z in enumerate(zeilen):                       # Einleitungssätze vor dem ersten YAML-Inhalt
        if not z.strip():
            continue
        if re.match(r"\s*(#|[\w-]+\s*:|- |---)", z):
            break
        zeilen[n] = ""
    # Dezimalkomma in einzeiligen Einträgen {cos_phi: 0,81} würde YAML als zwei Felder lesen -> 0.81
    zeilen = [RE_KOMMAZAHL.sub(r"\1.\2", z) if "{" in z else z for z in zeilen]
    return "\n".join(zeilen)


def lade_yaml(p: str, zeilen: bool = False) -> dict:
    roh = Path(p).read_bytes()
    try:
        text = roh.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = roh.decode("cp1252")        # im Windows-Editor als „ANSI“ gespeichert
    text = _bereinige(text)
    for nr, zeile in enumerate(text.splitlines(), 1):
        if "\t" in zeile[:len(zeile) - len(zeile.lstrip())]:
            raise regeln.RegelFehler(f"{Path(p).name}: Zeile {nr} ist mit Tabulator eingerückt – "
                                     f"bitte Leerzeichen verwenden")
    try:
        return yaml.load(text, Loader=_ZeilenLader if zeilen else _Lader)
    except yaml.YAMLError as e:
        stelle = getattr(e, "problem_mark", None)
        zeile = f" in Zeile {stelle.line + 1}" if stelle else ""
        raise regeln.RegelFehler(f"{Path(p).name}: Formatfehler{zeile} – Einrückung und Doppelpunkte prüfen "
                                 f"(z. B. „feld: wert“, Listen mit „- “)") from None
    except ValueError:
        raise regeln.RegelFehler(f"{Path(p).name}: ungültiger Wert, meist ein Datum wie 2026-13-01 – "
                                 f"Datum als JJJJ-MM-TT eintragen") from None


def lade_projekt(p: str) -> dict:
    if p.lower().endswith((".xlsx", ".xlsm")):
        from .excel_eingabe import lade_excel
        return lade_excel(p)
    return lade_yaml(p, zeilen=True)


def _vorgaben(pfad: str | None) -> dict | None:
    if not pfad:
        return None
    if not Path(pfad).is_file():
        raise regeln.RegelFehler(f"Hausvorgaben nicht gefunden: {pfad} – Datei aus dem Programmpaket "
                                 f"wiederherstellen oder mit --vorgaben angeben")
    return lade_yaml(pfad)


def cmd_generieren(a):
    from .projektmodell import bereit_machen
    stamm = lade_yaml(a.stamm)
    from .lernschleife import lade_regeln, pruefe_regressionen, wende_an
    regel_pfad = _hausregeln_pfad(a.profil)
    hausregeln, hinweise = lade_regeln(regel_pfad)
    daten = lade_projekt(a.projekt)
    if isinstance(daten, dict):                                 # Lernschleife: Korrekturen wirken VOR Prüfung/Planung
        daten, angewendet = wende_an(daten, hausregeln)
    else:
        angewendet = []
    projekt, ergaenzt = bereit_machen(daten, stamm, _vorgaben(a.vorgaben))
    m = regeln.plane(projekt, stamm)
    m.warnungen.append(f"Hausregeln: {len(hausregeln)} geladen aus {regel_pfad}" if regel_pfad.is_file()
                       else f"Hausregeln: keine Datei {regel_pfad} – keine Hausregeln angewendet")
    m.warnungen.extend(angewendet + hinweise + pruefe_regressionen(hausregeln))
    for titel, k in (("Annahme der Aufbereitung", "annahmen"), ("Offene Frage", "offene_fragen")):
        m.warnungen.extend(f"{titel}: {x}" for x in projekt.get(k) or [])
    m.warnungen.extend(ergaenzt)
    ziel = Path(a.ausgabe) if a.ausgabe else Path(a.projekt).resolve().parent / "ausgabe"   # Projektordner = alles
    ziel.mkdir(parents=True, exist_ok=True)
    json_pfad = ziel / f"{m.projekt['nummer']}_Planmodell.json"
    from .artikelstamm import wende_zuordnung_an  # eigener Artikelstamm (Hersteller/Artikelnummer)
    m.warnungen.extend(wende_zuordnung_an(m, Path(a.profil or PROFIL).with_name("artikelstamm.yaml")))
    from .hausstil import kennzeichne, lade_hausstil
    try:                                         # Kennzeichen gehören ins Planmodell (gleich in PDF und EPLAN)
        m.kennzeichen = kennzeichne(m, lade_hausstil(a.profil))
    except regeln.RegelFehler as e:
        m.warnungen.append(f"Kennzeichen im Hausstil nicht vergeben: {e}")
    # Schicht B -> C nur über planmodell.json: Ausgabe zeichnet aus dem gespeicherten und wieder geladenen Modell
    m.speichere(json_pfad)
    _ausgabe(Planmodell.lade(json_pfad), ziel, a.profil)


def _seiten_hausstil(m: Planmodell, profil: str | None) -> int:
    from .hausstil import Hausplan, lade_hausstil
    return sum(len(a.seiten) for a in Hausplan(m, lade_hausstil(profil)).anlagen.values())


def cmd_pruefbericht(a):
    from .hausstil import _zahl
    from .konsistenz import FEHLER, bericht_text, kennzahlen, pruefe_plan
    m = Planmodell.lade(a.planmodell)
    befunde = pruefe_plan(m)
    print("\n".join(bericht_text(befunde)))
    print("Kennzahlen: " + ", ".join(f"{k} {_zahl(v)}" for k, v in kennzahlen(m, _seiten_hausstil(m, a.profil)).items()))
    if any(b.art == FEHLER for b in befunde):
        raise regeln.RegelFehler("Prüfbericht enthält FEHLER")


def _hausregeln_pfad(profil: str | None) -> Path:
    return Path(profil or PROFIL).with_name("hausregeln.yaml")


def cmd_korrektur(a):
    from .lernschleife import ARTEN, erfasse_korrektur
    from .projektmodell import bereit_machen
    stamm, vorgaben = lade_yaml(a.stamm), _vorgaben(a.vorgaben)

    kabel_neu: dict[str, float] = {}

    def probelauf(projekt: dict) -> None:                       # Regel nur speichern, wenn der Plan entsteht
        kabel_neu.update({k.bmk: k.querschnitt_mm2 for k in regeln.plane(bereit_machen(projekt, stamm, vorgaben)[0],
                                                                           stamm).kabel})

    def planartikel(projekt: dict) -> set[str]:                 # vom Programm gewählte Artikel im Plan
        m = regeln.plane(bereit_machen(projekt, stamm, vorgaben)[0], stamm)
        return {b.artikel for b in m.betriebsmittel} | set((m.projekt.get("_klemmen") or {}).values())

    r = erfasse_korrektur(_hausregeln_pfad(a.profil), a.art, a.wenn, a.dann, a.herkunft or Path(a.projekt).name,
                          a.grund, lade_projekt(a.projekt), stamm, a.gilt_ab, a.nur_projekt, a.bearbeiter, probelauf,
                          nur_vorschau=a.vorschau, planartikel=planartikel)
    if a.art == "mindestquerschnitt":
        from .lernschleife import lade_regeln, schalte, wende_an
        pfad = _hausregeln_pfad(a.profil)
        bisher = wende_an(lade_projekt(a.projekt), [x for x in lade_regeln(pfad)[0] if x["id"] != r["id"]])[0]
        kabel_alt = {k.bmk: k.querschnitt_mm2 for k in regeln.plane(bereit_machen(bisher, stamm, vorgaben)[0], stamm).kabel}
        aenderung = [f"{b}: {kabel_alt[b]:g} → {q:g} mm²".replace(".", ",") for b, q in kabel_neu.items()
                     if b in kabel_alt and q != kabel_alt[b]]
        if not aenderung:
            if not a.vorschau:
                schalte(pfad, r["id"], "loeschen")
            raise regeln.RegelFehler("Alle Motor-/Leistungsleitungen haben schon mindestens diesen Querschnitt – "
                                     "Korrektur würde nichts ändern (nicht gespeichert)")
        r["vorschau"] += [f"Leitung {x}" for x in aenderung]
    if a.vorschau:
        print("Vorschau – so würde die Regel wirken (noch NICHT gespeichert):")
        print("\n".join(f"  • {x}" for x in r["vorschau"]))
        return
    was = f"mindestens {r['dann']} mm²".replace(".", ",") if r["art"] == "mindestquerschnitt" else f"{r['wenn']} → {r['dann']}"
    print(f"Hausregel {r['id']} gespeichert ({ARTEN[r['art']]}: {was}). Sie wirkt ab dem nächsten Plan und steht im "
          f"Auslegungsnachweis.")


def cmd_artikelstamm(a):
    from .artikelstamm import importiere
    yml, xlsx, n = importiere(a.export, lade_yaml(a.stamm), Path(a.profil).parent)
    print(f"Eigener Artikelstamm gespeichert: {yml}")
    print(f"Zuordnungsliste: {xlsx} – {n} Vorschläge. In Spalte E „JA“ (Vorschlag übernehmen) oder eine eigene "
          f"Artikelnummer eintragen, speichern, dann Befehl artikelzuordnung (Menüpunkt Z).")


def cmd_artikelzuordnung(a):
    from .artikelstamm import uebernehme_zuordnung
    z = uebernehme_zuordnung(Path(a.profil).parent)
    print(f"{len(z)} Zuordnungen übernommen – sie wirken ab dem nächsten Plan (Stückliste, EPLAN-Daten).")


def cmd_artikelliste(a):
    """Artikel und 24-V-Gruppen eines Projekts (Hilfe für Menüpunkt K)."""
    daten = lade_projekt(a.projekt)
    fg = [x for x in (daten.get("feldgeraete") or []) if isinstance(x, dict)] if isinstance(daten, dict) else []
    art = lade_yaml(a.stamm).get("artikel", {})
    print("Artikel im Projekt:")
    for k in sorted({str(x.get("artikel")) for x in fg}):
        print(f"  {k:<18} {art.get(k, {}).get('bezeichnung', '')}")
    print("24-V-Gruppen: " + ", ".join(sorted({str(x.get("gruppe")) for x in fg if x.get("gruppe")})))
    try:                                                        # vom Programm gewählte Geräte (Korrekturart 4)
        from .lernschleife import AUSWAHL_KATEGORIEN
        from .projektmodell import bereit_machen
        m = regeln.plane(bereit_machen(daten, lade_yaml(a.stamm), _vorgaben(a.vorgaben))[0], lade_yaml(a.stamm))
        gewaehlt = sorted({b.artikel for b in m.betriebsmittel if b.kategorie in AUSWAHL_KATEGORIEN})
        if gewaehlt:
            print("Vom Programm gewählt (Frequenzumrichter, Schütze, Motorschutzschalter, Klemmen):")
            for k in gewaehlt:
                print(f"  {k:<18} {art.get(k, {}).get('bezeichnung', '')}")
            for rolle, k in (m.projekt.get("_klemmen") or {}).items():
                if k not in gewaehlt:
                    print(f"  {k:<18} {art.get(k, {}).get('bezeichnung', '')} (Klemme {rolle})")
    except regeln.RegelFehler:
        pass


def cmd_hausregel(a):
    from .lernschleife import schalte
    r = schalte(_hausregeln_pfad(a.profil), a.id, a.aktion)
    print(f"Hausregel {r['id']} ({r['wenn']} → {r['dann']}): " + {"ein": "eingeschaltet", "aus": "ausgeschaltet",
                                                                  "loeschen": "gelöscht"}[a.aktion])


def cmd_hausregeln(a):
    from .lernschleife import ARTEN, bestaetige, lade_regeln, pruefe_regressionen
    pfad = _hausregeln_pfad(a.profil)
    if a.bestaetigen:
        print(f"{bestaetige(pfad)} Regressionsfälle mit dem aktuellen Ergebnis als neuem Soll gespeichert.")
    rs, hinweise = lade_regeln(pfad)
    print(f"Hausregeln aus {pfad}:" if pfad.is_file() else f"Keine Hausregeln ({pfad} fehlt).")
    for h in hinweise:
        print(h)
    for r in rs:
        status = "aktiv" if r.get("aktiv", True) else "aus"
        geltung = ", ".join(x for x in (f"ab {r['gilt_ab']}" if r.get("gilt_ab") else "",
                                        f"nur Projekt {r['nur_projekt']}" if r.get("nur_projekt") else "") if x) or "immer"
        print(f"{r['id']} [{status}] {ARTEN.get(r['art'], r['art'])}: {r['wenn']} → {r['dann']} – gilt {geltung} "
              f"({r.get('bearbeiter', '?')}, {r.get('datum')}, Herkunft {r.get('herkunft')}; Grund: {r.get('grund') or '–'})")
    befunde = pruefe_regressionen(rs)
    print("\n".join(befunde) if befunde else f"Regressionstest: {len(rs)} Fälle unverändert.")
    if befunde:
        raise regeln.RegelFehler("Regressionstest der Hausregeln fehlgeschlagen")


def cmd_zeichnen(a):
    """Schicht C allein: PDFs und Listen aus einem vorhandenen planmodell.json (ohne Projekt/Gerätestamm)."""
    pfad = Path(a.planmodell)
    _ausgabe(Planmodell.lade(pfad), Path(a.ausgabe) if a.ausgabe else pfad.parent, a.profil)


def _ausgabe(m: Planmodell, ziel: Path, profil: str | None) -> None:
    name = str(m.projekt["nummer"])
    if not re.fullmatch(r"[\w.\- ]+", name) or ".." in name:
        raise regeln.RegelFehler(f"Projektnummer „{name}“ ist als Dateiname ungeeignet – nur Buchstaben, Ziffern, . - _")
    ziel.mkdir(parents=True, exist_ok=True)
    seiten = zeichnen.erzeuge_pdf(m, str(ziel / f"{name}_Stromlaufplan.pdf"))
    (ziel / f"{name}_Stueckliste.csv").write_text(zeichnen.stueckliste_csv(m), encoding="utf-8")
    print(f"{len(seiten)} Seiten -> {ziel}/{name}_Stromlaufplan.pdf")
    from .hausstil import erzeuge_hausstil_pdf, lade_hausstil
    try:
        hs = erzeuge_hausstil_pdf(m, str(ziel / f"{name}_Stromlaufplan_Hausstil.pdf"), lade_hausstil(profil))
        print(f"Hausstil: {len(hs)} Seiten in {len({k for k, _, _ in hs})} Anlagen -> "
              f"{ziel}/{name}_Stromlaufplan_Hausstil.pdf")
    except regeln.RegelFehler as e:            # bisheriger Plan, Stückliste und Modell bleiben erhalten
        print(f"HINWEIS: Hausstil-PDF nicht erzeugt: {e}")
    print(f"Netzteil: {m.bilanz['netzteil']} (Bedarf {m.bilanz['i_bedarf_A']} A)")
    from .konsistenz import FEHLER, bericht_text, pruefe_plan  # bei jeder Ausgabe frisch geprüft
    befunde = pruefe_plan(m)
    print(bericht_text(befunde)[0] + " (Einzelheiten im Auslegungsnachweis)")
    fehler = [b for b in befunde if b.art == FEHLER]
    if MENUE:
        if not fehler:
            print(f"FERTIG. {len(m.warnungen)} Hinweise (Annahmen, offene Fragen, nicht geprüfte Punkte) stehen im "
                  f"Auslegungsnachweis – bitte vor Freigabe durchgehen.")
            return
        raise regeln.RegelFehler(f"PDFs liegen in {ziel}, aber rot gestempelt NICHT FÜR FERTIGUNG. Prüfbericht: "
                                 + "; ".join(f"{b.text} ({b.quelle})" for b in fehler[:3]))
    for w in m.warnungen:
        print("WARNUNG:", w)
    if fehler:
        raise regeln.RegelFehler(f"Plan erzeugt, aber der Prüfbericht enthält {len(fehler)} FEHLER – nicht für die "
                                 f"Fertigung verwenden: " + "; ".join(b.text for b in fehler[:3]))


KORREKTUR = "_Korrekturauftrag.txt"


def _korrekturauftrag(projekt: Path, text: str) -> Path:
    korr = projekt.with_name(projekt.stem + KORREKTUR)
    korr.write_text(text, encoding="utf-8")
    return korr


def _weiter(projekt: Path, korr: Path) -> str:
    if MENUE:
        return (f"So geht es weiter: Korrekturauftrag in denselben KI-Chat einfügen (siehe unten), die neue Antwort "
                f"ersetzt den ganzen Inhalt von {projekt.name}, speichern, dann wieder Punkt 9.")
    return (f"So geht es weiter: Inhalt von {korr} in denselben KI-Chat kopieren, die neue Antwort ersetzt den ganzen "
            f"Inhalt von {projekt.name}, speichern und erneut prüfen. Kleine Fehler können Sie auch direkt im Editor "
            f"korrigieren.")


def cmd_pruefen(a):
    from .projektmodell import bereit_machen
    pfad = Path(a.projekt)
    try:
        daten = lade_projekt(a.projekt)
    except regeln.RegelFehler as e:
        if pfad.suffix.lower() in (".xlsx", ".xlsm") or not pfad.is_file() or not pfad.read_bytes().strip():
            raise
        korr = _korrekturauftrag(pfad, "Deine Antwort konnte nicht gelesen werden (" + str(e) + "). Bitte gib das "
                                 "vollständige Projektmodell erneut als genau einen ```yaml-Block aus, ohne Text "
                                 "davor oder danach, und achte auf die Einrückung mit Leerzeichen.\n")
        raise regeln.RegelFehler(f"{e}\n\n{_weiter(pfad, korr)}") from None
    if daten is None:
        raise regeln.RegelFehler(f"{pfad.name} ist leer – die Antwort der KI hineinkopieren und speichern")
    try:
        _, ergaenzt = bereit_machen(daten, lade_yaml(a.stamm), _vorgaben(a.vorgaben))
    except regeln.RegelFehler as e:
        korr = _korrekturauftrag(pfad, "Die Software hat dein Projektmodell geprüft und diese Punkte gefunden. Bitte "
                                 "korrigiere sie und gib das vollständige Projektmodell erneut als einen YAML-Block "
                                 "aus (gleiche Regeln wie vorher, nichts erfinden – Unklares in offene_fragen):\n\n"
                                 + str(e) + "\n")
        raise regeln.RegelFehler(f"{e}\n\n{_weiter(pfad, korr)}") from None
    listen = {k: daten[k] for k in ("annahmen", "offene_fragen") if isinstance(daten.get(k), list) and daten[k]}
    n = len(listen.get("offene_fragen", []))
    print(f"Projektmodell {pfad.name}: vollständig, Plan kann erzeugt werden"
          + (f" – {n} offene Frage{'' if n == 1 else 'n'} vor Fertigstellung klären." if n else "."))
    if MENUE:                                   # knapp; Einzelheiten stehen im Auslegungsnachweis (PDF)
        teile = [f"{len(listen.get('annahmen', []))} Annahmen der KI", f"{n} offene Fragen",
                 f"{len(ergaenzt)} Bereiche nach Hausvorgabe"]
        print("Im Auslegungsnachweis (letzte PDF-Seite) stehen: " + ", ".join(teile) + ".")
        return
    if ergaenzt:
        print("Aus Hausvorgaben ergänzt (bitte prüfen):")
        print("\n".join(f"  • {x}" for x in ergaenzt))
    for titel, k in (("Annahmen der Aufbereitung", "annahmen"), ("Offene Fragen", "offene_fragen")):
        if k in listen:
            print(f"{titel} (bitte prüfen):")
            print("\n".join(f"  • {x}" for x in listen[k]))


def cmd_ki_auftrag(a):
    from .ki_auftrag import erzeuge_auftrag
    quelle = Path(a.lastenheft)
    if not quelle.exists():
        raise FileNotFoundError(2, "fehlt", str(quelle))
    ziel = Path(a.ziel) if a.ziel else quelle.with_name(quelle.stem + "_KI_Auftrag.txt")
    from .ki_auftrag import MAX_ZEICHEN
    text = erzeuge_auftrag(quelle, lade_yaml(a.stamm), a.anleitung)
    ziel.write_text(text, encoding="utf-8")
    print(f"KI-Auftrag -> {ziel} ({len(text):,} Zeichen)".replace(",", "."))
    if len(text) > MAX_ZEICHEN:
        print(f"ACHTUNG: sehr lang – viele KI-Chats nehmen so viel Text nicht auf. Lastenheft auf die Teile mit "
              f"Feldgeräten, Motoren und Einspeisung kürzen (Ziel unter {MAX_ZEICHEN:,} Zeichen).".replace(",", "."))
    antwort = quelle.with_name(quelle.stem + "_projektmodell.yaml")
    if a.ollama:                                      # Stufe A lokal: Auftrag direkt an die lokale KI
        from .lokale_ki import frage_lokale_ki
        print(f"Lokale KI ({a.modell}) arbeitet – das kann einige Minuten dauern …")
        neu = frage_lokale_ki(text, a.ollama, a.modell, fremder_server=a.fremder_server)
        if antwort.exists():                          # von Hand korrigierte Antwort nicht verlieren
            antwort.with_name(antwort.name + ".bak").write_bytes(antwort.read_bytes())
            print(f"Bisherige Antwort gesichert als {antwort.name}.bak")
        antwort.write_text(neu, encoding="utf-8")
        print(f"KI-Antwort gespeichert: {antwort}")
        if MENUE:
            print("Weiter mit Punkt 9 (KI-Antwort prüfen und Plan erzeugen).")
        else:
            print(f"Prüfen: python -m slpgen pruefen \"{antwort}\"")
        return
    print("So geht es weiter:")
    if MENUE:
        print("1. Auftrag im KI-Chat einfügen und absenden (nur eine vom Betrieb freigegebene KI;")
        print("   sonst Kundennamen vorher entfernen).")
        print(f"2. Es öffnet sich der Editor mit {antwort.name}: die ganze Antwort der KI hineinkopieren")
        print("   (vorhandenen Inhalt ersetzen) und speichern.")
        print(f"3. Hier Punkt 9 wählen und {antwort.name} ins Fenster ziehen.")
        return
    print("1. Inhalt der Datei vollständig in einen KI-Chat einfügen (nur eine vom Betrieb freigegebene KI;")
    print("   Kundennamen vorher entfernen, wenn die KI nicht freigegeben ist).")
    print(f"2. Antwort der KI mit dem Editor speichern als: {antwort}")
    print(f"3. Prüfen:        python -m slpgen pruefen \"{antwort}\"")
    print(f"4. Plan erzeugen: python -m slpgen generieren \"{antwort}\"")


def cmd_schema(a):
    if a.planmodell:
        from .modell import schema_planmodell_markdown as erzeuge
        ziel = a.ziel or str(PROG.parent / "docs" / "SCHEMA_PLANMODELL.md")
    else:
        from .projektmodell import schema_markdown as erzeuge
        ziel = a.ziel or str(PROG.parent / "docs" / "SCHEMA_PROJEKTMODELL.md")
    Path(ziel).write_text(erzeuge(), encoding="utf-8")
    print(f"Schema -> {ziel}")


def cmd_analysieren(a):
    zus = analyse.analysiere_bestand(Path(a.ordner), Path(a.ausgabe))
    print(json.dumps(zus, indent=2, ensure_ascii=False, default=str))


def cmd_datenblatt(a):
    print(json.dumps(analyse.datenblatt_vorschlag(Path(a.pdf), a.ollama, a.modell),
                     indent=2, ensure_ascii=False))


def cmd_vergleichen(a):
    modell = Planmodell.lade(a.modell).als_dict()            # mit Schemaprüfung
    print(json.dumps(analyse.vergleiche(Path(a.pdf), modell), indent=2, ensure_ascii=False))


def cmd_abweichungen(a):
    from .abweichung import freier_name, schreibe_liste, vergleiche
    from .hausstil import lade_hausstil
    m = Planmodell.lade(a.nachbau)
    erg = vergleiche(Path(a.referenz), m, lade_hausstil(a.profil) if a.profil else None)
    ziel = freier_name(Path(a.ausgabe or Path(a.nachbau).with_name(Path(a.referenz).stem + "_Abweichungen.xlsx")))
    schreibe_liste(erg, ziel)
    for bereich, (g, r, n, q) in erg["kennzahlen"].items():
        quote = f"{q:.1%}".replace(".", ",") if q is not None else "NICHT AUSWERTBAR (im Referenzplan nichts erkannt)"
        print(f"{bereich:<12} gemeinsam {g:>4}  nur Referenz {r:>4}  nur Nachbau {n:>4}  Übereinstimmung {quote}")
    print(f"Abweichungsliste: {ziel} – Spalte „Bewertung“ je Zeile ausfüllen (Elektrofachkraft).")


def cmd_struktur(a):
    from .struktur import lese_struktur
    e = lese_struktur(Path(a.pdf), schwelle=a.schwelle)
    if a.ausgabe:
        Path(a.ausgabe).write_text(json.dumps(e, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: e[k] for k in ("seiten", "seiten_je_dokumentart", "typical_kandidaten",
                                        "leere_anlagen", "aderkennzeichnung_gesamt")}, indent=1, ensure_ascii=False))


def cmd_vorlage(a):
    from .excel_eingabe import schreibe_vorlage
    schreibe_vorlage(lade_yaml(a.beispiel), lade_yaml(a.stamm), a.ziel)
    print(f"Excel-Vorlage -> {a.ziel}")


def cmd_korpus(a):
    from .korpus import erzeuge_korpus
    plaene = erzeuge_korpus(a.ordner, anzahl=a.anzahl, seed=a.seed)
    for pl in plaene:
        print(f"{pl.datei}  Jahr {pl.jahr}  Feldleiste {pl.feldleiste}  Typicals {pl.typicals}")


def cmd_lernen(a):
    from .profil import lerne_ordner, uebersicht
    ziel = Path(a.profil)
    if "hausprofil" not in ziel.resolve().parts:
        print("WARNUNG: Das Profil enthält vertrauliche Hausinhalte und Dateinamen. Es liegt nicht in einem "
              "Ordner 'hausprofil' und ist damit evtl. NICHT vor dem Einchecken in Git geschützt.")
    profil = lerne_ordner(a.ordner, ziel)
    print(uebersicht(profil), end="")
    print(f"Gespeichert: {ziel} und {ziel.with_name('profil_uebersicht.txt')}")


def cmd_freigabe(a):
    from .freigabe import uebernehme_freigaben
    e = uebernehme_freigaben(a.profil, a.liste)
    for titel, key in (("Freigegeben", "freigegeben"), ("Abgelehnt", "abgelehnt"), ("Noch offen", "offen")):
        print(f"{titel}:")
        for b in e[key] or ["-"]:
            print(f"  {b}")
    if e["offen"] and not (e["freigegeben"] or e["abgelehnt"]):
        print("Hinweis: keine Entscheidung gefunden – Excel-Liste nach dem Ausfüllen gespeichert?")
    for h in e.get("hinweis", []):
        print(f"Hinweis: {h}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="slpgen", description="Stromlaufplan-Generator (Prototyp)")
    sub = p.add_subparsers(dest="befehl", required=True)
    g = sub.add_parser("generieren", help="Projekt (Excel .xlsx oder YAML) -> PDF + Stückliste + Planmodell")
    g.add_argument("projekt")
    g.add_argument("--stamm", default=STAMM)
    g.add_argument("--ausgabe", help="Zielordner (Standard: Unterordner „ausgabe“ im Projektordner)")
    g.add_argument("--profil", default=PROFIL,
                   help="Hausprofil; nur freigegebene Werte fließen in den Hausstil ein")
    g.add_argument("--vorgaben", default=VORGABEN,
                   help="Hausvorgaben für fehlende Abschnitte (versorgung_24V, sps, leitungen)")
    g.set_defaults(f=cmd_generieren)
    kr = sub.add_parser("korrektur", help="Korrektur als Hausregel speichern (Lernschleife)")
    kr.add_argument("projekt")
    kr.add_argument("--art", required=True,
                    choices=["artikel_ersetzen", "gruppe_setzen", "mindestquerschnitt", "auswahl_ersetzen"])
    kr.add_argument("--vorschau", action="store_true", help="nur zeigen, was sich ändern würde – nichts speichern")
    kr.add_argument("--wenn", required=True, help="Artikel, für den die Regel gilt")
    kr.add_argument("--dann", required=True, help="Ersatzartikel bzw. 24-V-Gruppe")
    kr.add_argument("--grund", default="", help="Begründung in Klartext")
    kr.add_argument("--herkunft", help="Projekt/Person (Standard: Dateiname)")
    kr.add_argument("--gilt-ab", dest="gilt_ab", help="Projektdatum JJJJ-MM-TT, ab dem die Regel gilt")
    kr.add_argument("--nur-projekt", dest="nur_projekt", help="Projektnummer, für die allein die Regel gilt")
    kr.add_argument("--bearbeiter", help="Name (Standard: Windows-Anmeldename)")
    kr.add_argument("--vorgaben", default=VORGABEN)
    kr.add_argument("--stamm", default=STAMM)
    kr.add_argument("--profil", default=PROFIL)
    kr.set_defaults(f=cmd_korrektur)
    hr = sub.add_parser("hausregeln", help="Hausregeln auflisten und Regressionstest ausführen")
    hr.add_argument("--profil", default=PROFIL)
    hr.add_argument("--bestaetigen", action="store_true", help="aktuelles Ergebnis aller Fälle als neues Soll übernehmen")
    hr.set_defaults(f=cmd_hausregeln)
    ast_ = sub.add_parser("artikelstamm", help="Eigenen Artikelstamm (Excel/CSV-Export) einlesen, Zuordnungsliste erzeugen")
    ast_.add_argument("export")
    ast_.add_argument("--stamm", default=STAMM)
    ast_.add_argument("--profil", default=PROFIL)
    ast_.set_defaults(f=cmd_artikelstamm)
    az = sub.add_parser("artikelzuordnung", help="Ausgefüllte Zuordnungsliste übernehmen")
    az.add_argument("--profil", default=PROFIL)
    az.set_defaults(f=cmd_artikelzuordnung)
    al = sub.add_parser("artikelliste", help="Artikel und 24-V-Gruppen eines Projekts anzeigen")
    al.add_argument("projekt")
    al.add_argument("--stamm", default=STAMM)
    al.add_argument("--vorgaben", default=VORGABEN)
    al.set_defaults(f=cmd_artikelliste)
    hs = sub.add_parser("hausregel", help="Hausregel ein-/ausschalten oder löschen")
    hs.add_argument("aktion", choices=["ein", "aus", "loeschen"])
    hs.add_argument("id", help="z. B. R3")
    hs.add_argument("--profil", default=PROFIL)
    hs.set_defaults(f=cmd_hausregel)
    pb = sub.add_parser("pruefbericht", help="Konsistenzprüfung eines Planmodells (JSON) mit Kennzahlen")
    pb.add_argument("planmodell")
    pb.add_argument("--profil", default=PROFIL)
    pb.set_defaults(f=cmd_pruefbericht)
    ze = sub.add_parser("zeichnen", help="PDFs und Listen aus einem vorhandenen Planmodell (JSON)")
    ze.add_argument("planmodell")
    ze.add_argument("--ausgabe", help="Zielordner (Standard: Ordner des Planmodells)")
    ze.add_argument("--profil", default=PROFIL)
    ze.set_defaults(f=cmd_zeichnen)
    pr = sub.add_parser("pruefen", help="Projektmodell (YAML/Excel) prüfen, alle Lücken im Klartext")
    pr.add_argument("projekt")
    pr.add_argument("--stamm", default=STAMM)
    pr.add_argument("--vorgaben", default=VORGABEN)
    pr.set_defaults(f=cmd_pruefen)
    ka = sub.add_parser("ki-auftrag", help="Lastenheft (.txt/.md/.docx/.pdf) -> Text für einen KI-Chat")
    ka.add_argument("lastenheft")
    ka.add_argument("--ziel", help="Ausgabedatei (Standard: <Lastenheft>_KI_Auftrag.txt)")
    ka.add_argument("--stamm", default=STAMM)
    ka.add_argument("--ollama", help="lokale KI (Ollama), z. B. http://localhost:11434 – Auftrag wird direkt gesendet")
    ka.add_argument("--modell", default="qwen2.5:7b", help="Modell der lokalen KI")
    ka.add_argument("--fremder-server", dest="fremder_server", action="store_true",
                    help="KI-Server auf einem anderen Rechner ausdrücklich erlauben (Lastenheft verlässt den PC)")
    ka.add_argument("--anleitung", default=str(PROG.parent / "docs" / "KI_AUFBEREITUNG.md"))
    ka.set_defaults(f=cmd_ki_auftrag)
    sc = sub.add_parser("schema", help="Schema des Projektmodells als Markdown schreiben")
    sc.add_argument("ziel", nargs="?", help="Zieldatei (Standard: docs/SCHEMA_PROJEKTMODELL.md bzw. SCHEMA_PLANMODELL.md)")
    sc.add_argument("--planmodell", action="store_true", help="Schema des Planmodells statt des Projektmodells")
    sc.set_defaults(f=cmd_schema)
    an = sub.add_parser("analysieren", help="Bestands-PDFs auswerten (Formate, Jahre, Kennbuchstaben)")
    an.add_argument("ordner")
    an.add_argument("--ausgabe", default="analyse")
    an.set_defaults(f=cmd_analysieren)
    d = sub.add_parser("datenblatt", help="Datenblatt-PDF -> Vorschlag Gerätestamm-Eintrag")
    d.add_argument("pdf")
    d.add_argument("--ollama", help="z. B. http://localhost:11434 (lokales LLM, optional)")
    d.add_argument("--modell", default="qwen2.5:7b")
    d.set_defaults(f=cmd_datenblatt)
    v = sub.add_parser("vergleichen", help="Original-PDF gegen Planmodell (JSON) abgleichen")
    v.add_argument("pdf")
    v.add_argument("modell")
    v.set_defaults(f=cmd_vergleichen)
    ab = sub.add_parser("abweichungen", help="Abnahme: Referenzplan (PDF) gegen Nachbau (Planmodell JSON) -> Excel-Liste")
    ab.add_argument("referenz")
    ab.add_argument("nachbau", help="…_Planmodell.json aus „generieren“")
    ab.add_argument("--ausgabe")
    ab.add_argument("--profil", help="Hausprofil für den Hausstil des Nachbaus (Standard: eingebauter Stil)")
    ab.set_defaults(f=cmd_abweichungen)
    st = sub.add_parser("struktur", help="Vektor-PDF: Anlagen, BMK, SPS-Adressen, Adern, Typical-Kandidaten")
    st.add_argument("pdf")
    st.add_argument("--schwelle", type=float, default=0.75, help="Ähnlichkeit für Typical-Gruppen (0..1)")
    st.add_argument("--ausgabe", help="JSON-Datei für das vollständige Ergebnis")
    st.set_defaults(f=cmd_struktur)
    vo = sub.add_parser("vorlage", help="Excel-Vorlage für die Projekteingabe erzeugen")
    vo.add_argument("ziel", nargs="?", default="beispiele/Projekt_Vorlage.xlsx")
    vo.add_argument("--beispiel", default="beispiele/projekt_beispiel.yaml")
    vo.add_argument("--stamm", default=STAMM)
    vo.set_defaults(f=cmd_vorlage)
    ko = sub.add_parser("korpus", help="Synthetische Testpläne im Hausstil erzeugen (ohne Kundendaten)")
    ko.add_argument("ordner")
    ko.add_argument("--anzahl", type=int, default=10)
    ko.add_argument("--seed", type=int, default=1)
    ko.set_defaults(f=cmd_korpus)
    le = sub.add_parser("lernen", help="Hausprofil aus einem Ordner mit Bestands-PDFs lernen")
    le.add_argument("ordner")
    le.add_argument("--profil", default=PROFIL)
    le.set_defaults(f=cmd_lernen)
    fr = sub.add_parser("freigabe", help="Freigaben aus profil_freigabe.xlsx ins Hausprofil übernehmen")
    fr.add_argument("--profil", default=PROFIL)
    fr.add_argument("--liste", default="hausprofil/profil_freigabe.xlsx")
    fr.set_defaults(f=cmd_freigabe)
    a = p.parse_args(argv)
    try:
        a.f(a)
    except regeln.RegelFehler as e:
        sys.exit(f"Fehler: {e}")
    except PermissionError as e:
        if e.filename and Path(e.filename).exists():
            sys.exit(f"Datei gesperrt: {e.filename}\n-> Ist die Datei noch in einem PDF-Programm oder Excel geöffnet? "
                     f"Bitte schließen und erneut starten.")
        sys.exit(f"In diesen Ordner darf nicht geschrieben werden: {Path(e.filename or '.').parent}\n-> Datei in einen "
                 f"eigenen Projektordner kopieren (z. B. meine_projekte) und erneut versuchen.")
    except FileNotFoundError as e:
        sys.exit(f"Datei nicht gefunden: {e.filename or e} – Pfad und Namen prüfen")
    except IsADirectoryError as e:
        sys.exit(f"Das ist ein Ordner, keine Datei: {e.filename}")
    except Exception:
        log = Path("slpgen_fehler.log")
        log.write_text(traceback.format_exc(), encoding="utf-8")
        sys.exit(f"Unerwarteter Programmfehler – bitte die Datei {log.resolve()} an den Betreuer schicken.")
