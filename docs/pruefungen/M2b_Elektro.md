# Prüfung M2b – Elektro/Norm (pruefer-elektro-norm), 20.11.2026

Gegenstand: KI_AUFBEREITUNG.md, Beispiel-Lastenheft, KI-Antwort, hausvorgaben.yaml. Alle 9 Lastenheftpositionen abgebildet.

| Nr. | Schwere | Befund | Erledigung |
|---|---|---|---|
| 1 | hoch | Ersatzartikel mit Leistungsteil (Pumpe) übernimmt Bemessungsdaten still → MSS-Auslegung ohne Annahme | Regel 1: immer in annahmen **und** offene_fragen (Datenblatt) |
| 2 | hoch | Regel 7 erlaubte angenommene Motordaten; Länge „wie Nord“ statt ungünstig | Motordaten nie annehmen (nur offene Frage); fehlende Länge = größte Länge + 20 % und Frage |
| 3 | hoch | Sicherheitsfragen nur, wenn Lastenheft sie nennt | Regel 8: Not-Halt/PL, Reparaturschalter je Motor/Pumpe, Ventil-Ruhestellung, Anlagensicherheit immer fragen |
| 4 | mittel | Zähler-Annahmen (24 V aus Schrank, Ruhestrom, Widerstand) ungenannt | KI-Antwort-Beispiel ergänzt; Regel 7 verlangt Versorgung/Kontaktart als Annahme |
| 5 | mittel | aktiv/passiv-Annahme ungenannt | Regel 7 |
| 6 | mittel | „Y“ nicht IEC 81346-2 (nicht verifiziert) | Regel 4 sagt „Hausregel, nicht aus IEC 81346-2 abgeleitet“; A21 bleibt offen |
| 7 | gering | Ruhestellung Magnetventile | Regel 8 |
| 8 | gering | I_z-Werte ohne Quelle | Hinweis in hausvorgaben.yaml; bleibt A3 (EF) |
| – | Beobachtung | 230-V-Pumpen in 24-V-Abgangsliste -F3 mit 0 A | → Arbeitsvorrat M4c |

Nachweis: eine unabhängige KI-Instanz hat mit den geänderten Regeln alle Sicherheitsfragen und die Ersatzartikel-Annahmen selbständig geliefert (`beispiele/ki_antwort_roh_2026-11-20.txt`).
