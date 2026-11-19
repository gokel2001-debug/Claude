"""Kommandozeile: python -m slpgen <befehl> ..."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from . import analyse, regeln, zeichnen


def lade_yaml(p: str) -> dict:
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


def lade_projekt(p: str) -> dict:
    if p.lower().endswith((".xlsx", ".xlsm")):
        from .excel_eingabe import lade_excel
        return lade_excel(p)
    return lade_yaml(p)


def cmd_generieren(a):
    projekt, stamm = lade_projekt(a.projekt), lade_yaml(a.stamm)
    m = regeln.plane(projekt, stamm)
    ziel = Path(a.ausgabe)
    ziel.mkdir(parents=True, exist_ok=True)
    name = m.projekt["nummer"]
    seiten = zeichnen.erzeuge_pdf(m, stamm, str(ziel / f"{name}_Stromlaufplan.pdf"))
    from .hausstil import erzeuge_hausstil_pdf, lade_hausstil
    hs = erzeuge_hausstil_pdf(m, stamm, str(ziel / f"{name}_Stromlaufplan_Hausstil.pdf"), lade_hausstil(a.profil))
    print(f"Hausstil: {len(hs)} Seiten in {len({k for k, _, _ in hs})} Anlagen -> "
          f"{ziel}/{name}_Stromlaufplan_Hausstil.pdf")
    (ziel / f"{name}_Stueckliste.csv").write_text(zeichnen.stueckliste_csv(m, stamm), encoding="utf-8")
    # Neutrales Modell = Übergabe an Variante A (EPLAN-API)
    (ziel / f"{name}_Planmodell.json").write_text(
        json.dumps(m.als_dict(), indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"{len(seiten)} Seiten -> {ziel}/{name}_Stromlaufplan.pdf")
    print(f"Netzteil: {m.bilanz['netzteil']} (Bedarf {m.bilanz['i_bedarf_A']} A)")
    for w in m.warnungen:
        print("WARNUNG:", w)


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
    g.add_argument("--stamm", default="beispiele/geraetestamm.yaml")
    g.add_argument("--ausgabe", default="ausgabe")
    g.add_argument("--profil", default="hausprofil/profil.yaml",
                   help="Hausprofil; nur freigegebene Werte fließen in den Hausstil ein")
    g.set_defaults(f=cmd_generieren)
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
    vo.add_argument("--stamm", default="beispiele/geraetestamm.yaml")
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
        sys.exit(f"Nicht gefunden: {e.filename or e}" + (f" ({e.strerror})" if e.strerror else ""))
