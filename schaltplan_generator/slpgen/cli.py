"""Kommandozeile: python -m slpgen <befehl> ..."""
from __future__ import annotations

import argparse
import json
import re
import sys
import traceback
from pathlib import Path

import yaml

from . import analyse, regeln, zeichnen

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


_Lader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


RE_KOMMAZAHL = re.compile(r"(:\s*-?\d+),(\d+)(?=\s*[a-zA-Z%²]*\s*[,}])")


def _bereinige(text: str) -> str:
    """KI-Antworten: Codeblock ```yaml … ``` und Einleitungssätze entfernen."""
    if "```" in text:
        teile = text.split("```")
        if len(teile) >= 3:
            text = teile[1].split("\n", 1)[1] if teile[1].split("\n", 1)[0].strip().isalpha() else teile[1]
    zeilen = text.splitlines()
    while zeilen and zeilen[0].strip() and not re.match(r"\s*(#|[\w-]+\s*:|- |---)", zeilen[0]):
        zeilen.pop(0)
    # Dezimalkomma in einzeiligen Einträgen {cos_phi: 0,81} würde YAML als zwei Felder lesen -> 0.81
    zeilen = [RE_KOMMAZAHL.sub(r"\1.\2", z) if "{" in z else z for z in zeilen]
    return "\n".join(zeilen)


def lade_yaml(p: str) -> dict:
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
        return yaml.load(text, Loader=_Lader)
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
    return lade_yaml(p)


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
    name = m.projekt["nummer"]
    seiten = zeichnen.erzeuge_pdf(m, stamm, str(ziel / f"{name}_Stromlaufplan.pdf"))
    (ziel / f"{name}_Stueckliste.csv").write_text(zeichnen.stueckliste_csv(m, stamm), encoding="utf-8")
    # Neutrales Modell = Übergabe an Variante A (EPLAN-API)
    (ziel / f"{name}_Planmodell.json").write_text(
        json.dumps(m.als_dict(), indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"{len(seiten)} Seiten -> {ziel}/{name}_Stromlaufplan.pdf")
    from .hausstil import erzeuge_hausstil_pdf, lade_hausstil
    try:
        hs = erzeuge_hausstil_pdf(m, stamm, str(ziel / f"{name}_Stromlaufplan_Hausstil.pdf"), lade_hausstil(a.profil))
        print(f"Hausstil: {len(hs)} Seiten in {len({k for k, _, _ in hs})} Anlagen -> "
              f"{ziel}/{name}_Stromlaufplan_Hausstil.pdf")
    except regeln.RegelFehler as e:            # bisheriger Plan, Stückliste und Modell bleiben erhalten
        print(f"HINWEIS: Hausstil-PDF nicht erzeugt: {e}")
    print(f"Netzteil: {m.bilanz['netzteil']} (Bedarf {m.bilanz['i_bedarf_A']} A)")
    for w in m.warnungen:
        print("WARNUNG:", w)


def cmd_pruefen(a):
    from .projektmodell import bereit_machen
    daten = lade_projekt(a.projekt)
    hinweise = []
    for titel, k in (("Annahmen der Aufbereitung", "annahmen"), ("Offene Fragen", "offene_fragen")):
        if isinstance(daten, dict) and isinstance(daten.get(k), list) and daten[k]:
            hinweise += [f"{titel} (bitte prüfen):", *[f"  • {x}" for x in daten[k]]]
    try:
        _, ergaenzt = bereit_machen(daten, lade_yaml(a.stamm), _vorgaben(a.vorgaben))
    except regeln.RegelFehler as e:
        print("\n".join(hinweise))
        korr = Path(a.projekt).with_name(Path(a.projekt).stem + "_Korrektur_fuer_KI.txt")
        korr.write_text("Die Software hat dein Projektmodell geprüft und diese Punkte gefunden. Bitte korrigiere sie "
                        "und gib das vollständige Projektmodell erneut als einen YAML-Block aus (gleiche Regeln wie "
                        "vorher, nichts erfinden – Unklares in offene_fragen):\n\n" + str(e) + "\n", encoding="utf-8")
        raise regeln.RegelFehler(f"{e}\n\nSo geht es weiter: Inhalt von {korr} in denselben KI-Chat kopieren, "
                                 f"die neue Antwort über {Path(a.projekt).name} speichern und erneut prüfen. "
                                 f"Kleine Fehler können Sie auch direkt in der Datei (Editor) korrigieren.") from None
    n = len(daten.get("offene_fragen") or []) if isinstance(daten.get("offene_fragen"), list) else 0
    print(f"Projektmodell {Path(a.projekt).name}: vollständig, Plan kann erzeugt werden"
          + (f" – {n} offene Frage{'' if n == 1 else 'n'} (stehen im Auslegungsnachweis; Plan kann trotzdem "
             f"erzeugt werden, vor Fertigstellung klären)." if n else "."))
    if ergaenzt:
        print("Aus Hausvorgaben ergänzt (bitte prüfen):")
        print("\n".join(f"  • {x}" for x in ergaenzt))
    if hinweise:
        print("\n".join(hinweise))


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
    antwort = quelle.with_name("projektmodell.yaml")
    print("So geht es weiter:")
    print("1. Inhalt der Datei vollständig in einen KI-Chat einfügen (nur eine vom Betrieb freigegebene KI;")
    print("   Kundennamen vorher entfernen, wenn die KI nicht freigegeben ist).")
    print(f"2. Antwort der KI mit dem Editor speichern als: {antwort}")
    print(f"3. Prüfen:        python -m slpgen pruefen \"{antwort}\"")
    print(f"4. Plan erzeugen: python -m slpgen generieren \"{antwort}\"")


def cmd_schema(a):
    from .projektmodell import schema_markdown
    Path(a.ziel).write_text(schema_markdown(), encoding="utf-8")
    print(f"Schema -> {a.ziel}")


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
    sc.add_argument("ziel", nargs="?", default="../docs/SCHEMA_PROJEKTMODELL.md")
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
        sys.exit(f"Datei gesperrt: {e.filename}\n-> Ist die Datei noch in einem PDF-Programm oder Excel geöffnet? "
                 f"Bitte schließen und erneut starten.")
    except FileNotFoundError as e:
        sys.exit(f"Datei nicht gefunden: {e.filename or e} – Pfad und Namen prüfen")
    except IsADirectoryError as e:
        sys.exit(f"Das ist ein Ordner, keine Datei: {e.filename}")
    except Exception:  # noqa: BLE001 – Sicherheitsnetz: nie Traceback für den Anwender
        log = Path("slpgen_fehler.log")
        log.write_text(traceback.format_exc(), encoding="utf-8")
        sys.exit(f"Unerwarteter Programmfehler – bitte die Datei {log.resolve()} an den Betreuer schicken.")
