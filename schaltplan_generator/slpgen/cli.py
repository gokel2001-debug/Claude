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
    projekt, ergaenzt = bereit_machen(lade_projekt(a.projekt), stamm, _vorgaben(a.vorgaben))
    m = regeln.plane(projekt, stamm)
    for titel, k in (("Annahme der Aufbereitung", "annahmen"), ("Offene Frage", "offene_fragen")):
        m.warnungen.extend(f"{titel}: {x}" for x in projekt.get(k) or [])
    m.warnungen.extend(ergaenzt)
    ziel = Path(a.ausgabe)
    ziel.mkdir(parents=True, exist_ok=True)
    json_pfad = ziel / f"{m.projekt['nummer']}_Planmodell.json"
    # Schicht B -> C nur über planmodell.json: Ausgabe zeichnet aus dem gespeicherten und wieder geladenen Modell
    m.speichere(json_pfad)
    _ausgabe(Planmodell.lade(json_pfad), ziel, a.profil)


def cmd_zeichnen(a):
    """Schicht C allein: PDFs und Listen aus einem vorhandenen planmodell.json (ohne Projekt/Gerätestamm)."""
    pfad = Path(a.planmodell)
    _ausgabe(Planmodell.lade(pfad), Path(a.ausgabe) if a.ausgabe else pfad.parent, a.profil)


def _ausgabe(m: Planmodell, ziel: Path, profil: str | None) -> None:
    ziel.mkdir(parents=True, exist_ok=True)
    name = m.projekt["nummer"]
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
    if MENUE:
        print(f"FERTIG. {len(m.warnungen)} Hinweise (Annahmen, offene Fragen, nicht geprüfte Punkte) stehen im "
              f"Auslegungsnachweis – bitte vor Freigabe durchgehen.")
        return
    for w in m.warnungen:
        print("WARNUNG:", w)


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
    modell = json.loads(Path(a.modell).read_text(encoding="utf-8"))
    print(json.dumps(analyse.vergleiche(Path(a.pdf), modell), indent=2, ensure_ascii=False))


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
    g.add_argument("--ausgabe", default="ausgabe")
    g.add_argument("--profil", default="hausprofil/profil.yaml",
                   help="Hausprofil; nur freigegebene Werte fließen in den Hausstil ein")
    g.add_argument("--vorgaben", default=VORGABEN,
                   help="Hausvorgaben für fehlende Abschnitte (versorgung_24V, sps, leitungen)")
    g.set_defaults(f=cmd_generieren)
    ze = sub.add_parser("zeichnen", help="PDFs und Listen aus einem vorhandenen Planmodell (JSON)")
    ze.add_argument("planmodell")
    ze.add_argument("--ausgabe", help="Zielordner (Standard: Ordner des Planmodells)")
    ze.add_argument("--profil", default="hausprofil/profil.yaml")
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
    le.add_argument("--profil", default="hausprofil/profil.yaml")
    le.set_defaults(f=cmd_lernen)
    fr = sub.add_parser("freigabe", help="Freigaben aus profil_freigabe.xlsx ins Hausprofil übernehmen")
    fr.add_argument("--profil", default="hausprofil/profil.yaml")
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
