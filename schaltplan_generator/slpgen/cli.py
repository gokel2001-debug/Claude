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


def cmd_generieren(a):
    projekt, stamm = lade_yaml(a.projekt), lade_yaml(a.stamm)
    m = regeln.plane(projekt, stamm)
    ziel = Path(a.ausgabe)
    ziel.mkdir(parents=True, exist_ok=True)
    name = m.projekt["nummer"]
    seiten = zeichnen.erzeuge_pdf(m, stamm, str(ziel / f"{name}_Stromlaufplan.pdf"))
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


def main(argv=None):
    p = argparse.ArgumentParser(prog="slpgen", description="Stromlaufplan-Generator (Prototyp)")
    sub = p.add_subparsers(dest="befehl", required=True)
    g = sub.add_parser("generieren", help="Projekt-YAML -> PDF + Stückliste + Planmodell")
    g.add_argument("projekt")
    g.add_argument("--stamm", default="beispiele/geraetestamm.yaml")
    g.add_argument("--ausgabe", default="ausgabe")
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
    a = p.parse_args(argv)
    try:
        a.f(a)
    except regeln.RegelFehler as e:
        sys.exit(f"Regelfehler: {e}")
