# Prüfung M6a – Software, 21.11.2026 (Commit 958d34a)

| Nr. | Schwere | Befund | Erledigung |
|---|---|---|---|
| 1 | hoch | Mit HTTP_PROXY (oder Windows-Proxy) ging das Lastenheft an den Proxy (nachgestellt) | eigener Opener ohne Proxy; Test mit Proxy-Attrappe und gelöschtem no_proxy |
| 2 | hoch (am PC zu prüfen) | Kontextfenster von Ollama zu klein → stille Kürzung | `num_ctx` 16384 (A46); `done_reason == length` → Klartext-Fehler; Prüfung am PC (PC5) |
| 3 | mittel | beliebige Server-Adresse ohne Warnung | nur dieser PC (localhost/127.0.0.1/::1), sonst nur mit `--fremder-server` |
| 4 | mittel | vorhandene KI-Antwort überschrieben | Sicherung `.bak` |
| 5 | gering | Fehlertext bei 500 ohne Grund; Zeitlimit ungetestet | Grund aus `error`; Test Zeitlimit |
| 6 | gering | kein seed; Batch-Block ungetestet | `seed: 0`; Strukturtest für `:kiauftrag_lokal` |
