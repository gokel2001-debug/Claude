Vor jeder Arbeit `schaltplan_generator/docs/ZIEL.md` lesen. Sie hat Vorrang.

# Projekt: Stromlaufplan-Generator (Langläufer)

| Datei | Zweck |
|---|---|
| `schaltplan_generator/docs/ZIEL.md` | verbindlicher Auftrag (Endziel, Architektur, Meilensteine M1–M9, Regeln) |
| `docs/ROADMAP.md` | Meilensteine und erledigte Pakete |
| `docs/STATUS.md` | laufender Arbeitsstand (nach jedem Teilschritt) |
| `docs/STATUSBERICHT.md` | Sammelbericht für die Überwachung (Format ZIEL.md Abschnitt 5) |
| `docs/ENTSCHEIDUNGEN.md` | bestätigte und vorläufige Entscheidungen |
| `docs/OFFENE_PUNKTE.md` | Annahmen (A-Nr.) mit Frage, im Code markiert mit `# ANNAHME A-Nr.` |
| `docs/PC_AUFGABEN.md` | Aufgaben, die nur am Windows-PC gehen |
| `.claude/agents/` | Prüfer-Agenten (ändern nie Code) |

Regeln: keine Kundendaten im Repository (nur `hausprofil/` lokal); Tests: `cd schaltplan_generator && python3 -m pytest -q tests`.
