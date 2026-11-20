# Schema Planmodell (`planmodell/1`)

Erzeugt aus `slpgen/modell.py` (`python -m slpgen schema --planmodell`) – nicht von Hand ändern.

Das Planmodell ist das Ergebnis des Planungskerns (Schicht B) und die **einzige** Eingabe der Ausgabe (Schicht C: PDF bisher, PDF Hausstil, Stückliste, später EPLAN-Adapter). Datei: `<Projektnummer>_Planmodell.json`.

| Feld | Art | Inhalt |
|---|---|---|
| `schema` | Text | immer „planmodell/1“ |
| `projekt` | Objekt | Kopfdaten aus dem Projektmodell (nummer, bezeichnung, anlage, ort, …; `_netz` = Netzform) |
| `betriebsmittel` | Liste Betriebsmittel | alle Geräte, Bausteinteile, Kabel, Klemmleisten mit Lage im Plan |
| `klemmen` | Liste Klemme | Klemmenbelegung innen/außen je Leiste |
| `sps_kanaele` | Liste SpsKanal | SPS-Kanalzuordnung mit Adresse |
| `absicherungen` | Liste Absicherung | 24-V-Abgänge mit Gruppenstrom und Verbrauchern |
| `kabel` | Liste Kabel | Leitungsauslegung (Querschnitt, I_z, ΔU) |
| `seiten` | Liste [Nr, Titel, Art, Index] | Seitenfolge des bisherigen Plans |
| `bilanz` | Objekt | 24-V-Bilanz und Netzteilauswahl |
| `warnungen` | Liste Text | Auslegungsnachweis: Annahmen, offene Fragen, nicht geprüfte Punkte |
| `artikel` | Objekt Artikel → Daten | Auszug Gerätestamm, nur verwendete Artikel (Ausgabe braucht keinen Stamm) |

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
