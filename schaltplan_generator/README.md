# slpgen – Stromlaufplan-Generator (Prototyp Variante B)

Konzept, Begründung und Quellen: [`../docs/Konzept_KI_Stromlaufplan_Generator.md`](../docs/Konzept_KI_Stromlaufplan_Generator.md)

```bash
pip install -r requirements.txt
python -m slpgen generieren beispiele/projekt_beispiel.yaml      # -> ausgabe/
python -m slpgen analysieren /pfad/zu/bestandsplaenen             # -> analyse/
python -m slpgen datenblatt datenblatt.pdf --ollama http://localhost:11434
python -m pytest tests
```

| Datei | Inhalt |
|---|---|
| `beispiele/projekt_beispiel.yaml` | Eingabe: Projektkopf, Einspeisung, 24-V-Regeln, SPS, Feldgeräte |
| `beispiele/geraetestamm.yaml` | Gerätestamm (Platzhalter-Artikel, aus Datenblättern zu befüllen) |
| `slpgen/regeln.py` | Regelwerk: 24-V-Bilanz, Netzteil, Absicherung, SPS-Kanäle, Klemmen, BMK |
| `slpgen/zeichnen.py` | PDF-Ausgabe A3 (Rahmen, Schriftfeld, Strompfade, Listen) |
| `slpgen/analyse.py` | Bestandsanalyse (Format, Jahr, Kennbuchstaben je Jahr) und Datenblatt-Extraktion (optional lokales LLM über Ollama) |
| `slpgen/modell.py` | neutrales Planmodell (auch Übergabe an Variante A / EPLAN) |
| `eplan_skripte/Test_Beschriftung.cs` | Test in EPLAN: Laufen Skripte ohne API-Lizenz? (Konzept Kap. 11, Phase 0) |

Erzeugte Pläne tragen im Schriftfeld den Vermerk „nicht freigegeben“; sie ersetzen keine Prüfung durch eine Elektrofachkraft.
