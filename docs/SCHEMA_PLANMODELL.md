# Schema Planmodell (`planmodell/1`)

Erzeugt aus `slpgen/modell.py` (`python -m slpgen schema --planmodell`) – nicht von Hand ändern.

Das Planmodell ist das Ergebnis des Planungskerns (Schicht B) und die **einzige** Eingabe der Ausgabe (Schicht C: PDF bisher, PDF Hausstil, Stückliste, später EPLAN-Adapter). Datei: `<Projektnummer>_Planmodell.json`.

| Feld | Art | Inhalt |
|---|---|---|
| `schema` | Text | immer „planmodell/1“ |
| `projekt` | Objekt | Kopfdaten aus dem Projektmodell (nummer, bezeichnung, anlage, ort, …; `_netz` = Netzform; `_sicherheit` = Platzhalterseite Sicherheit: not_halt, pl, stoppkategorie, funktionen, freigabe, ausloeser, geraete, antriebe) |
| `betriebsmittel` | Liste Betriebsmittel | alle Geräte, Bausteinteile, Kabel, Klemmleisten mit Lage im Plan |
| `klemmen` | Liste Klemme | Klemmenbelegung innen/außen je Leiste |
| `sps_kanaele` | Liste SpsKanal | SPS-Kanalzuordnung mit Adresse |
| `absicherungen` | Liste Absicherung | 24-V-Abgänge mit Gruppenstrom und Verbrauchern |
| `kabel` | Liste Kabel | Leitungsauslegung (Querschnitt, I_z, ΔU) |
| `seiten` | Liste [Nr, Titel, Art, Index] | Seitenfolge des bisherigen Plans |
| `bilanz` | Objekt | 24-V-Bilanz und Netzteilauswahl |
| `warnungen` | Liste Text | Auslegungsnachweis: Annahmen, offene Fragen, nicht geprüfte Punkte |
| `artikel` | Objekt Artikel → Daten | Auszug Gerätestamm, nur verwendete Artikel (Ausgabe braucht keinen Stamm) |
| `kennzeichen` | Objekt BMK → [Anlage, lokales BMK] | Kennzeichen im Hausstil, im Planungsablauf vor dem Speichern vergeben; PDF Hausstil und EPLAN-Adapter verwenden dieselben (A27) |

Pflicht: `projekt.nummer` (wird Dateiname: Buchstaben, Ziffern, `. - _`). Seitenarten: deckblatt, inhalt, einspeisung, verteilung, sps, motor_last, motor_steuer, feld, klemmen, kabel, stueckliste, auslegung.

## Freie Objekte

| Objekt | Schlüssel |
|---|---|
| `artikel.<Artikel>` | kategorie, bezeichnung (Pflicht); hersteller, artikelnummer und technische Werte je Kategorie |
| `bilanz` | netzteil, i_nenn_A, i_summe_A, i_bedarf_A, gleichzeitigkeit, reserve, auslastung, gruppen, i_motoren_A, i_netzgeraete_A, i_je_aussenleiter_A, i_400V_max_A, i_primaer_max_A |
| `betriebsmittel.daten` (alle mit 24-V-Strom) | i_A (A), gruppe, absicherung (BMK des Abgangs) |
| `betriebsmittel.daten` (sensor/aktor) | signal (DI/DO/AI/AO/BAUSTEIN), sps (Kanal), adresse, anschluss (Pins), klemmen, typical, versorgung, versorgt, teilsignale, quellsignale, leistung (Leistungsteil: mss, kabel, aussenleiter …) |
| `betriebsmittel.daten` (teilsignal/bauteil/kabel eines Bausteins) | eltern (BMK des Geräts), lokal (BMK im Baustein), i_r_A, laenge_m |
| `betriebsmittel.daten` (motor) | p_kW, i_N_A, cos_phi, mss, schuetz, kabel (BMK) |
| `betriebsmittel.daten` (motorschutz/schuetz) | i_r_A, signal, sps, adresse, funktion_sps, steuer_seite, steuer_spalte |
| `betriebsmittel.daten` (netzteil) | Artikeldaten des gewählten Netzteils (i_nenn_A, u_ein_V, u_aus_V, wirkungsgrad, vorsicherung_A) |
| `betriebsmittel.daten` (klemme (Leiste)) | anzahl |
| `betriebsmittel.daten` (selektivkanal/meldung) | modul, kanal |

Verbindungen und Potentiale sind (noch) kein eigener Teil: sie ergeben sich aus `klemmen` (innen/außen, Potential) und `absicherungen` (Abgang → Verbraucher). Annahme A28.

## Betriebsmittel

| Feld | Typ | Pflicht |
|---|---|---|
| `bmk` | `str` | ja |
| `artikel` | `str` | ja |
| `bezeichnung` | `str` | ja |
| `funktion` | `str` | – |
| `kategorie` | `str` | – |
| `seite` | `int | None` | – |
| `spalte` | `int | None` | – |
| `daten` | `dict[str, Any]` | – |

## Klemme

| Feld | Typ | Pflicht |
|---|---|---|
| `leiste` | `str` | ja |
| `nr` | `int` | ja |
| `potential` | `str` | ja |
| `ziel_innen` | `str` | ja |
| `ziel_aussen` | `str` | ja |
| `seite` | `int | None` | – |
| `spalte` | `int | None` | – |
| `signal` | `str` | – |

## SpsKanal

| Feld | Typ | Pflicht |
|---|---|---|
| `modul_bmk` | `str` | ja |
| `kanal` | `int` | ja |
| `art` | `str` | ja |
| `adresse` | `str` | ja |
| `geraet_bmk` | `str` | ja |
| `funktion` | `str` | ja |
| `anschluss` | `str` | – |

## Absicherung

| Feld | Typ | Pflicht |
|---|---|---|
| `bmk` | `str` | ja |
| `artikel` | `str` | ja |
| `i_nenn_A` | `float` | ja |
| `gruppe` | `str` | ja |
| `i_gruppe_A` | `float` | ja |
| `verbraucher` | `list[str]` | ja |

## Kabel

| Feld | Typ | Pflicht |
|---|---|---|
| `bmk` | `str` | ja |
| `artikel` | `str` | ja |
| `von` | `str` | ja |
| `nach` | `str` | ja |
| `adern` | `int` | ja |
| `querschnitt_mm2` | `float` | ja |
| `laenge_m` | `float` | ja |
| `i_b_A` | `float` | ja |
| `i_z_A` | `float` | ja |
| `du_prozent` | `float` | ja |
| `seite` | `int | None` | – |
| `spalte` | `int | None` | – |
