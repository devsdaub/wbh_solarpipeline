# SolarPipeline

Datenpipeline für mein 800-W-Balkonkraftwerk in Stuttgart. Führt die
Produktionsdaten aus der Hoymiles-Anlage mit Wetter- und
Luftqualitätsdaten zusammen und zeigt das Ganze in einem Dashboard.

## Starten

```bash
cp .env.example .env
docker compose up --build
```

Dashboard auf http://localhost:8008, Swagger auf /docs. Ports je nach Docker Config

## Was drin ist

| | |
|---|---|
| Backend | FastAPI |
| DB | PostgreSQL 16 |
| Verarbeitung | pandas |
| Validierung | Pandera |
| Scheduler | APScheduler |
| Diagramme | Chart.js |
| Tests | pytest |

Bewusst kein React und kein Node. Zwei Seiten mit ein paar Diagrammen
brauchen keinen Buildprozess. Frontend ist Jinja2 plus etwa 200 Zeilen
JavaScript.

SQLAlchemy nutze ich synchron. Bei den paar tausend Zeilen bringt async
nichts außer Komplexität.

## Datenquellen

**Open-Meteo Wetter** (`archive-api.open-meteo.com/v1/archive`)
Einstrahlung auf die geneigte Fläche, Temperatur, Bewölkung. Kostenlos,
kein Key.

**Open-Meteo Luftqualität** (`air-quality-api.open-meteo.com/v1/air-quality`)
Saharastaub und Feinstaub. Eigener Host, gleiche Bauart.

**Hoymiles Energy-Report**
CSV-Export aus dem Portal, hochladen unter /settings.

**Hoymiles Cloud-API** (`neapi.hoymiles.com`)
Dieselben Tageswerte, nur ohne den manuellen Exportschritt. Undokumentiert,
mehr dazu weiter unten.

Der Power-Report mit 20-Minuten-Werten fehlt noch. Die Tabelle
`power_readings` ist da, aber leer.

An- und abschalten lassen sich die API-Quellen in `config/sources.yaml`
oder direkt unter /settings.

### Azimut, Stolperfalle

Open-Meteo will den Azimut süd-basiert und zwischen -180 und 180.
Meine 203° sind nord-basiert. Mit 203 kommt HTTP 400 zurück. Umgerechnet
sind das 23. Die Umrechnung steckt im Adapter, in der plant.yaml bleibt
der richtige Wert für die Anlage stehen.

Ärgerlich daran: Ein falscher Azimut fällt nicht auf. Die API antwortet
mit jedem Wert zwischen -180 und 180 völlig normal, nur passen die
Einstrahlungswerte dann nicht zu meinem Dach. Deswegen gibt es dafür
einen Test.

### visibility bringt nichts

Der Parameter wird von der Archiv-API akzeptiert, kommt aber immer leer
zurück (Einheit ist sogar `undefined`). Die Spalte ist deshalb durchgehend
NULL, in keiner einzigen von 12000 Zeilen steht ein Wert. Gibt es nur in
der Forecast-API.

Ich hab die Anfrage trotzdem drin gelassen. Kostet nichts, und falls sie
irgendwann Daten nachliefern, läuft es ohne Änderung ein.

## Hoymiles-Export

Das Portal hat das Format zwischendurch geändert, ich hab inzwischen drei
Varianten gesehen:

| | alt | mittel | aktuell |
|---|---|---|---|
| Datum | `Date` | `Time` | `Time` |
| Leistung | keine | `Rated Power (W)` | `Capacity (kW)` |
| Verbrauch | dabei | weg | wieder dabei |
| Extras | keine | `Model`, `SN` | `Plant Creation Time` |

Konstant ist nur `Production (kWh)`. Der Parser sucht sich deshalb gezielt
die Datums- und die Produktionsspalte raus und ignoriert alles andere.
Anders herum (bekannte Störspalten löschen) wäre er beim Formatwechsel
kaputtgegangen.

Was verworfen wird, landet im Log. Fehlt `Production (kWh)` komplett,
bricht der Import ab statt leere Daten zu schreiben.

Liefert der Export eine Leistungsangabe mit, wird die gegen
`module_capacity_wp` geprüft. Einheit ist mal W, mal kW, wird umgerechnet.
Passt es nicht, gibt es eine Warnung im Log, aber keinen Abbruch.

`Consumption (kWh)` steht bei mir durchgehend auf `-`, ist also nutzlos.
Das Zeichen ist übrigens ein normaler Bindestrich, kein Gedankenstrich.

Nochmal hochladen ist unproblematisch, überlappende Tage werden
aktualisiert statt doppelt angelegt.

## Hoymiles Cloud-API

Irgendwann hatte ich keine Lust mehr, monatlich eine CSV zu exportieren.
Die S-Miles-Cloud hat keine öffentliche API, aber die Weboberfläche redet
ja mit irgendwas. Anmeldeablauf und Antwortformat hab ich aus deren
JavaScript rausgelesen und gegen mein eigenes Konto geprüft. Also meine
Anlage, meine Zugangsdaten, meine Daten.

Drei Dinge sind anders als bei Open-Meteo.

**Kein API-Key.** Stattdessen holt man sich eine Nonce, rechnet daraus
einen Passwort-Hash und bekommt ein Token. Das Hash-Verfahren hängt am
Alter des Kontos: ältere Konten MD5 plus SHA256, neuere argon2id. Beide
sind drin, welches gebraucht wird, sagt die Voranfrage im Feld `v`.

**Kein JSON.** Die historischen Tageswerte kommen als Protobuf-Binärformat,
und eine `.proto`-Datei gibt es natürlich nicht. Der Parser in
`app/adapters/hoymiles_api.py` liest die zwei Feldtypen, die tatsächlich
vorkommen: Feld 1 die Tagesnummern als Strings, Feld 2 eine Unternachricht
mit Reihenname und den Werten als 32-Bit-Fliesskomma.

**Keine Zusicherungen.** Ändert Hoymiles was, ist die Anbindung kaputt.
Deshalb bleibt der CSV-Import bestehen, nicht als Notlösung, sondern als
bewusst gehaltener zweiter Weg.

Abgerufen wird monatsweise mit 1,5 Sekunden Abstand zwischen den Aufrufen.
Der laufende Tag wird ausgelassen, dessen Ertrag wäre nur ein
Zwischenstand.

Zugangsdaten liegen in `config/hoymiles_auth.yaml`, die Datei steht in
der `.gitignore`. Als Vorlage liegt `config/hoymiles_auth.example.yaml`
daneben. Fehlt die echte Datei, wird die Quelle beim Pipeline-Lauf
übersprungen, der Rest läuft normal weiter.

`GET /api/hoymiles/realtime` fragt die Momentanleistung ab, ohne etwas zu
speichern. Praktisch als Verbindungstest, wenn man wissen will, ob die
Zugangsdaten noch stimmen.

### Gegeneinander prüfen

Zwei Quellen für dieselbe Zahl sind eine Gelegenheit.
`GET /api/quality/compare?start=&end=` holt den Zeitraum frisch aus der
API und vergleicht ihn mit dem, was in der DB steht. Toleranz 0,02 kWh
wegen der Rundung.

Für den Mai 2026: 31 Tage verglichen, 0 Abweichungen, größte Differenz
0,005 kWh. Damit ist auch die Einheitenumrechnung von Wattstunden auf
Kilowattstunden bestätigt, die sonst still falsch sein könnte.

### Nullen sind keine Messwerte

Ein Unterschied ist mir dabei aufgefallen: Für die 29 Umzugstage liefert
die API glatte 0,00 kWh, die CSV lässt die Zeilen einfach weg. Zwei
Quellen, dieselbe Größe, unterschiedliche Kodierung für "keine Daten".

Dass die Nullen wirklich "nichts empfangen" heißen und nicht "nichts
erzeugt", zeigt der Zeitraum vor der Inbetriebnahme. Die Anlage hängt
seit dem 26.04.2025. Frage ich den April 2025 ab, stehen die Tage vom
01. bis 25. auf exakt 0,000, und ausgerechnet am Installationstag selbst
auf 0,007 kWh, ein paar Wattstunden vom Abend. Ein meldender
Wechselrichter liefert immer irgendwas.

Der Adapter lässt Tage mit exakt 0 deshalb komplett aus, statt sie als
Messwert zu speichern. Damit verhält sich die API genau wie die CSV, die
solche Zeilen gar nicht erst enthält, und die Umzugslücke bleibt im
Lückenbericht sichtbar. Hätte ich die Nullen importiert, wäre die Lücke
still verschwunden und jeder Februar-Mittelwert um 29 Nullen zu niedrig.
Genau das ist mir einmal passiert, nach einem `down -v`.

### Wie weit zurück geholt wird

Steht noch keine Produktion in der Datenbank, holt die Pipeline alles ab
`installation_date` aus `plant.yaml`. Danach reicht das übliche Fenster
aus `default_days_back`, sonst liefe jeder Durchlauf über alle Monate.

Nach einem `docker compose down -v` füllt sich der Bestand beim nächsten
Lauf also von selbst wieder komplett, ohne dass ich eine CSV suchen muss.
Knapp 40 Sekunden für anderthalb Jahre.

### Gegenprobe über den Gesamtzähler

`GET /api/hoymiles/realtime` liefert unter `gesamt_kwh` den Lebenszähler
der Anlage. Der lag zuletzt bei 1110,8 kWh, die Summe über alle
Tageswerte in der Datenbank bei 1110,774 kWh. Differenz drei Hundertstel,
also Rundung.

Das ist die beste Vollständigkeitsprüfung, die ich habe, und nebenbei der
Beweis, dass die Anlage in den 29 Umzugstagen tatsächlich nichts erzeugt
hat. Hätte sie, läge der Zähler über der Summe.

## Datenbank

| Tabelle | was drin ist |
|---|---|
| `plant_config` | Stammdaten der Anlage |
| `daily_facts` | Tageswerte, hier läuft alles zusammen |
| `hourly_weather` | Stundenwerte aus beiden APIs |
| `power_readings` | 20-Minuten-Werte, noch leer |
| `pipeline_runs` | Protokoll der Pipeline-Läufe |

Tabellen legt SQLAlchemy beim Start selbst an (`create_all`), kein Alembic.
Reicht für ein Projekt mit genau einer Zielumgebung.

**Nachteil davon:** Neue Spalten in bestehenden Tabellen legt `create_all`
nicht an. Solange keine Daten drin sind, hilft `docker compose down -v`.
Danach von Hand, so wie bei `hours`:

```sql
ALTER TABLE daily_facts ADD COLUMN IF NOT EXISTS hours INTEGER;
```

Zeitstempel sind alle `TIMESTAMPTZ` und intern UTC. Umgerechnet wird erst
in der Anzeige, über einen Jinja-Filter in `app/filters.py`.

Fehlende Messwerte stehen als NULL drin, nicht als 0. Bei pandas muss man
da aufpassen: `NaN` wandert sonst als Zahlenwert NaN in die DB und wird
von `IS NULL` nicht gefunden. Wird in `to_records()` abgefangen.

## Verarbeitung

Stundenwerte werden mit pandas zu Tageswerten verdichtet
(`app/pipeline/transformation.py`):

| Spalte | Berechnung |
|---|---|
| `gti_kwh` | Summe der Stundenwerte / 1000 |
| `avg_temperature` | Mittel |
| `avg_cloud_cover` | gerundetes Mittel |
| `max_dust` | Maximum |
| `avg_pm10` | Mittel |
| `eq` | `production_kwh / (gti_kwh × module_kwp)` |
| `hours` | Anzahl Stundenwerte, aus denen der Tag gerechnet wurde |

Warum pandas und nicht SQL: Die Rechenlogik liegt so als normale Funktion
vor, die man ohne laufende Datenbank testen kann. Laden und Schreiben ist
davon getrennt. Beim Tests schreiben hat sich das ausgezahlt.

Bei `sum()` steht `min_count=1`. Ohne das gibt pandas für einen Tag ohne
jeden Messwert eine 0 zurück, und 0 kWh Einstrahlung ist etwas anderes als
keine Messung. SQL macht das von sich aus richtig, pandas nicht.

### Tagesgrenzen

Gruppiert wird nach **lokalen** Kalendertagen, nicht nach UTC-Tagen. Der
Hoymiles-Export grenzt Tage nach Ortszeit ab, also müssen die Wetterdaten
genauso abgegrenzt werden.

Ich hab beides mal durchgerechnet: Bei der Einstrahlung kommt exakt
dasselbe raus, weil die verschobenen Stunden nachts liegen und da eh 0
ist. Bei der Temperatur sind es im Mittel 0,13 K Unterschied, maximal
0,68 K. Also nicht dramatisch, aber methodisch ist die lokale Abgrenzung
die richtige.

An den Tagen der Zeitumstellung gibt es 23 bzw. 25 Stundenwerte. Passt so,
die Tage hatten real so viele Stunden.

### Warum es `hours` gibt

Die APIs liefern Stunden bis 23:00 UTC. In Ortszeit ist das im Sommer
schon 01:00 des nächsten Tages. Der jüngste Kalendertag hat dadurch immer
nur ein oder zwei Stunden, beide nachts, Einstrahlung 0. Im Diagramm gab
das jedes Mal einen senkrechten Absturz auf null.

`hours` hält fest, aus wie vielen Stunden ein Tag gerechnet wurde. Die
Diagramme zeigen nur Tage mit mindestens 23. Die Daten bleiben trotzdem
in der DB stehen.

## Was geprüft wird

Jede Quelle hat ein Pandera-Schema mit `strict=True` und `coerce=True`.
Unerwartete Spalten, fehlende Spalten und falsche Typen fliegen sofort
auf. Dazu Wertebereiche, Einstrahlung nicht negativ, Temperatur zwischen
-40 und 55, Bewölkung 0 bis 100.

Bei den Wetterquellen wird ein einzelner unplausibler Wert zu NULL, die
Zeile bleibt stehen. Das ist keine Bequemlichkeit, sondern nötig: Wirft
man die Zeile weg, hat der Tag weniger als 23 Stundenwerte, gilt damit
als unvollständig, und der Backfill holt ihn bei jedem Lauf erneut. Und
verwirft ihn wieder. Endlos.

Fachlich passt NULL sowieso besser. Eine Temperatur von 99 Grad heißt
nicht "diese Stunde gab es nicht", sondern "für diese Stunde hab ich
keinen brauchbaren Wert".

Zwei Sachen werden **nicht** geheilt:

- Strukturelles. Fehlende oder überzählige Spalte heißt, die Schnittstelle
  hat sich geändert, und das soll auffallen.
- Die Produktion. `production_kwh` ist bewusst nicht nullbar. Ein falscher
  Tagesertrag auf NULL zu setzen wäre schlimmer als abzubrechen, dann
  stünde da ein Tag ohne Ertrag und der Lückenbericht würde ihn als
  Erfassungslücke melden.

Fällt eine Quelle wegen ungültiger Daten aus, läuft der Rest weiter. Der
Lauf steht dann auf `teilweise` statt auf `ok`, und in der Historie steht,
welche Quelle es war.

Was ein Schema nicht sehen kann, prüft `app/pipeline/pruefung.py` auf den
fertigen Tageswerten: Ertrag ohne Einstrahlung, Ertrag über der
Anlagengrenze, Wirkungsgrad über 1, negativer Ertrag. Dazu den Füllgrad
jeder Spalte, denn eine dauerhaft leere Spalte verletzt formal nichts.
Abrufbar über `GET /api/quality/report`. Bewusst nicht in der Oberfläche:
das sind Hinweise für mich beim Draufschauen, keine Bedienelemente, und
die Settings-Seite ist schon voll genug. Fehlgeschlagene
Schema-Validierungen sieht man dagegen sehr wohl, die stehen als
`teilweise` in der Lauf-Historie mit der betroffenen Quelle dahinter.

**Die Falle dabei:** Pandera hat zwei Ausnahmen, `SchemaError` für den
ersten Verstoß und `SchemaErrors` für die gesammelte Prüfung mit
`lazy=True`. Die beiden stehen nebeneinander und erben nicht voneinander.
Als ich auf `lazy` umgestellt hab, hat mein `except SchemaError` von einem
Moment auf den anderen nichts mehr gefangen, ohne dass ich es angefasst
hätte. Prüfungen auf Ebene der ganzen Tabelle, also fehlende oder
überzählige Spalten, kommen übrigens auch ohne `lazy` als `SchemaErrors`.

## Datenlücken

Vom **25.01. bis 22.02.2026** hab ich keine Produktionsdaten, 29 Tage am
Stück. Da war der Umzug.

Auffinden lassen sich Lücken über `GET /api/quality/gaps`. Gesucht wird
nur innerhalb des Zeitraums, für den überhaupt Produktionsdaten da sind.
Alles danach fehlt nicht, sondern ist noch nicht gemeldet, der laufende
und der vorige Tag stehen naturgemäß noch nicht in der Cloud.

Gesucht wird gegen den **Kalender**, nicht gegen die vorhandenen Zeilen.
Das klingt nach Haarspalterei, ist aber der Unterschied zwischen 29 und
3 gemeldeten Tagen. Zu einem Lückentag gibt es nämlich oft gar keine
Zeile in `daily_facts`: Die Produktion wird ausgelassen, weil die API
nur eine Null liefert, und Wetter holt der Backfill nur für Tage, an
denen Produktion vorliegt. Kein Wetter, keine Zeile. Eine Suche über die
vorhandenen Zeilen findet dann nur die Ränder.

Aufgefallen ist mir das erst nach einem `down -v`, als der Bericht
plötzlich 3 statt 29 Tage meldete. Vorher hatte die Lücke nur deshalb
Zeilen, weil ich einmal manuell Wetter über den ganzen Zeitraum geholt
hatte. Dafür gibt es jetzt einen Test.

Im Verlaufsdiagramm sieht man die Lücke als Unterbrechung, in der Heatmap
als schraffierte Felder. Die Heatmap läuft ohnehin über den Kalender und
war deshalb nie betroffen.

### Noch was aufgefallen

Zwischen 23.02. und 08.03.2026 lief die Anlage mit etwa einem Drittel
Leistung. Am 05.03. bei fast wolkenlosem Himmel nur 1,1 kWh, der
Wirkungsgrad lag bei 0,24 statt der üblichen 0,6. Ab dem 09.03. ist er
schlagartig auf 0,79 hoch.

Das ist genau nach der Umzugslücke, vermutlich war da erst ein Teil der
Anlage wieder aufgebaut. Muss ich noch klären.

Sechs Tage haben außerdem einen Wirkungsgrad über 1, was physikalisch
nicht geht, verteilt über beide Jahre: 29.09. und 04.10.2025, 17.11.2025,
03.01., 12.01. und 12.03.2026. Alle sechs sind trübe Tage mit sehr wenig
Einstrahlung. Im Nenner steht ja keine
Messung, sondern ein Modellwert von Open-Meteo, und bei diffusem Licht
unter geschlossener Wolkendecke ist der ungenau. Kein Datenfehler also,
aber ein Hinweis, dass der Wirkungsgrad in dem Bereich nichts taugt.
Nachzusehen unter `GET /api/quality/report`.

## Backfill

Produktionsdaten reichen bis Januar zurück, Wetter holt der Scheduler
aber nur für die letzten 30 Tage. Ohne Gegenmaßnahme hätten alle älteren
Tage keine Einstrahlung und damit keinen Wirkungsgrad, und weil alle
Diagramme auf `hours >= 23` filtern, wären sie überall unsichtbar.

Die Pipeline sucht deshalb vor jeder Aggregation nach Tagen mit
Produktion, aber ohne vollständige Wetterdaten, und lädt die nach.
Reihenfolge ist wichtig: `hours` schreibt nur die Aggregation, also erst
holen, dann verdichten. Andersrum würde der Backfill dieselben Tage beim
nächsten Lauf nochmal holen.

Zusammenhängende Tage werden zu einem Block zusammengefasst, ein Block
ist ein Aufruf. 243 Tage einzeln abzufragen wären 243 Aufrufe und würde
die Drosselung auslösen, als ein Block sind es 0,2 Sekunden und 180 KB.

**Der Fehler, der mich am längsten gekostet hat:** Der Block wird an
beiden Rändern um einen Tag erweitert. Ich frag ja in UTC ab, verdichte
aber nach Ortszeit, und die ersten zwei Stunden eines lokalen Sommertags
gehören in UTC noch zum Vortag. Ohne die Zugabe hat der erste Tag des
Blocks nur 22 Stundenwerte, gilt damit als unvollständig und wird beim
nächsten Lauf wieder geholt. Und wieder. Gemerkt hab ich es erst, als
derselbe Block zum dritten Mal im Log stand.

Nach oben wird auf heute begrenzt, das Archiv reicht nicht weiter. Fragt
man darüber hinaus, kommt ein 400 mit `end_date is out of allowed range`,
und der wird nicht wiederholt (siehe unten), fliegt also sofort durch und
killt den Lauf.

Manuell geht das über `POST /api/backfill/weather` oder den Knopf in den
Einstellungen. `GET /api/quality/weather-gaps` zeigt, was gerade offen ist.

## Wenn was schiefgeht

Die APIs sind nicht immer erreichbar. Ein Timeout oder ein 503 wird bis
zu dreimal wiederholt, mit einer, dann zwei Sekunden Pause dazwischen.
Danach gibt die Pipeline auf und der Lauf landet mit Status `fehler` in
der Historie.

Wiederholt wird aber nur, was Sinn hat: 408, 425, 429, 5xx und
Verbindungsfehler. Die Regel dahinter ist simpel, 4xx ist mein Fehler und
5xx seiner, und meinen eigenen Fehler heilt kein Warten. Bei einem 400
kommt der Fehler sofort durch.

Gemerkt hab ich das, als ich eine Variable in `sources.yaml` falsch
geschrieben hatte. Open-Meteo antwortet mit 400 und schreibt sogar
hin, was los ist, und ich hatte drei identische Anfragen und drei
Sekunden Wartezeit für nichts.

Ein falsches Passwort bei Hoymiles wird ebenfalls nicht wiederholt.
Dreimal falsch anmelden ist bei einem fremden Dienst keine gute Idee.

## Scheduler

Läuft im Hintergrund mit APScheduler, Intervall in
`config/scheduler.yaml` oder über /settings.

```yaml
scheduler:
  enabled: true
  jobs:
    pipeline:
      interval_minutes: 180
      enabled: true
```

Jeder Lauf landet in `pipeline_runs` mit Start, Ende, Auslöser
(`scheduler` oder `manuell`), Status und Fehlermeldung. Eingetragen wird
schon **vor** dem Lauf. Wenn der Container mittendrin abstürzt, bleibt
eine Zeile mit Status `laeuft` und ohne Endzeit stehen, und das ist ein
Unterschied zu "hat nie angefangen".

Beim Start holt sich der Scheduler eine Advisory Lock in Postgres. Falls
mal eine zweite Instanz gegen dieselbe DB läuft, merkt die das und plant
nichts ein. Die Sperre hängt an der Verbindung, bei einem Absturz gibt
Postgres sie automatisch frei.

Die Sperre war eigentlich als reine Vorsichtsmaßnahme gedacht. Beim
Testen hat sie dann wirklich zugeschlagen, dazu unten mehr.

**Nicht wundern beim Entwickeln:** APScheduler startet den ersten Lauf
erst nach Ablauf des Intervalls, und jeder Container-Neustart setzt den
Timer zurück. Wenn man dauernd Code ändert, kommt der Scheduler nie zum
Zug. Zum Testen Intervall auf 3 stellen und zehn Minuten die Finger
stilllassen.

## Endpunkte

| | |
|---|---|
| `POST /api/pipeline/run` | alles: abrufen, nachladen, aggregieren |
| `POST /api/ingest/all` | nur die Wetter-APIs abrufen |
| `POST /api/ingest/weather`, `/air` | einzeln, optional mit `?start=&end=` |
| `POST /api/ingest/production` | Tageswerte aus der Hoymiles-Cloud |
| `POST /api/backfill/weather` | fehlende Wetterdaten nachladen |
| `POST /api/transform/daily` | nur aggregieren |
| `POST /api/upload/energy` | CSV hochladen |
| `GET /api/hoymiles/realtime` | aktuelle Leistung, direkt aus der Cloud |
| `GET /api/quality/gaps` | Lücken in der Produktion |
| `GET /api/quality/weather-gaps` | Tage mit Produktion, aber ohne Wetter |
| `GET /api/quality/report` | fachliche Befunde und Füllgrad je Spalte |
| `GET /api/quality/compare` | CSV gegen Cloud-API, braucht `?start=&end=` |
| `GET /api/pipeline/status`, `/runs` | Scheduler-Zustand, Historie |
| `GET /api/data/daily`, `/scatter`, `/monthly`, `/trends` | Daten für die Diagramme |

Einen bestimmten Zeitraum von Hand nachladen, etwa nach einem Eingriff
in der Datenbank:

```bash
curl -X POST "http://localhost:8008/api/ingest/all?start=2026-01-01&end=2026-08-17"
```

## Oberfläche

**Dashboard** (`/`) zeigt nur Daten, keine Bedienelemente.

- Vier Kennzahlen: Tage mit Daten, Tage mit Produktion, kWh gesamt,
  Ø Wirkungsgrad
- Verlauf Produktion und Einstrahlung, umschaltbar 30 / 90 / 365 Tage
- Monatssummen als Balken
- Heatmap der Tagesproduktion übers Jahr
- Produktion gegen Temperatur, Bewölkung oder Staub im Wochenverlauf
- Streudiagramm Produktion über Einstrahlung
- Tabelle mit den letzten 21 Tagen

Die ersten beiden Kennzahlen sind absichtlich nebeneinander. Bei mir
stehen da 501 und 469, und die Differenz von 32 ist genau die Geschichte:
29 Umzugstage, der Tag vor der Inbetriebnahme und zwei Tage am aktuellen
Rand, für die noch keine Produktion gemeldet ist. Vorher stand da mal
"Stundenwerte", was nichts weiter war als die Zahl der Tage mal 24.

**Settings** (`/settings`) macht alles andere: CSV-Upload,
Scheduler-Intervall, Quellen an und aus, Pipeline von Hand starten,
Wetterdaten nachladen, Lauf-Historie.

Der Zeitraum im Verlaufsdiagramm zählt vom letzten vorhandenen Datenpunkt
rückwärts, nicht von heute. Sonst sieht man bei "30 Tage" fast nur Tage
ohne Produktion, weil die Wetterdaten weiter reichen als der CSV-Export.

Alle Diagramm-Endpunkte liefern immer dieselbe Struktur, auch wenn sie
nichts zu liefern haben. `/api/data/trends` gab bei leerer Datenbank mal
`{"reihen": {}}` zurück, und weil das JavaScript fest auf
`reihen.produktion.werte` zugreift, ist das Dashboard beim allerersten
Start mit einem TypeError ausgestiegen. Charts leer, Knöpfe tot. Ist mir
erst nach einem `down -v` aufgefallen, also genau in der Situation, die
jemand sieht, der das Projekt zum ersten Mal startet.

Chart.js liegt lokal unter `app/static/js/`. Kein CDN, damit das Ding
offline läuft und keine Besucher-IPs bei Dritten landen. Aus demselben
Grund gibt es keine Google Fonts mehr, sondern Systemschriften.

### Konfiguration über die UI

Geschrieben wird in dieselben YAML-Dateien, die man auch von Hand
bearbeiten kann. Keine zweite Konfiguration in der Datenbank.

Wirkt beides sofort, aber unterschiedlich: Die Quellen werden bei jedem
Lauf frisch aus der Datei gelesen, da passiert das von selbst. Der
Scheduler hält seinen Auftrag im Speicher, dem muss man über
`apply_config()` Bescheid sagen. Hab ich beim ersten Versuch vergessen,
dann stand der neue Wert in der Datei und der Job lief trotzdem im alten
Takt weiter.

Eine Kleinigkeit, über die ich gestolpert bin: Sobald die Oberfläche eine
YAML-Datei schreibt, formatiert `yaml.safe_dump` sie nach eigenen Regeln
neu. Anführungszeichen weg, Listen anders eingerückt, Leerzeilen raus.
Inhaltlich identisch, aber `git diff` zeigt trotzdem was an. Einmal
mitcommitten und gut.

## Tests

```bash
docker compose exec app pytest -q
```

25 Tests in vier Dateien, eine Sekunde. Läuft im Container, weil
`app/database.py` die Variable `DATABASE_URL` schon beim Import braucht.

Bewusst wenige. Ich hab mir drei Bedingungen gesetzt: Es ist eine reine
Funktion ohne DB und ohne Netz, ein Fehler darin wäre still statt laut,
und es ist beim Bauen schon mal schiefgegangen. Das trifft auf die
Zeitzonenumrechnung zu, auf die Blockbildung, auf die
Retry-Unterscheidung, auf den Protobuf-Parser und auf die Schemata.

Nicht getestet: `ingest_source`, `run_pipeline` und die `fetch`-Methoden.
Die Attrappen dafür wären größer als der geprüfte Code und würden
hauptsächlich die Attrappe prüfen. Dazu kommen drei Smoke-Tests über die
Endpunkte, die nur Statuscodes und die Form der Antwort prüfen, keine
Werte. Ein Test, der 215 Tage festschreibt, wäre beim nächsten
Pipeline-Lauf rot ohne dass was kaputt ist.

Der Protobuf-Test baut sich seine Bytes selbst, mit einem winzigen
Kodierer im Test. Wollte keine Binärdatei im Repo liegen haben, die
keiner nachvollziehen kann.

**Zwei Sachen, die mich Zeit gekostet haben.** Ohne `pytest.ini` mit
`pythonpath = .` findet pytest zwar die Tests, kann aber `app.*` nicht
importieren und bricht beim Einsammeln ab. Und `with TestClient(app)`,
so wie es in der FastAPI-Doku steht, führt den Startvorgang aus, legt
also Tabellen an und startet einen Scheduler. Im Testprozess. Gemerkt
hab ich das nur, weil die Advisory Lock angeschlagen und den zweiten
Scheduler abgewiesen hat. Ohne `with` passiert nichts davon, und den
Startvorgang brauchen die Tests sowieso nicht.

## Entwickeln

Der Code ist als Volume gemountet, uvicorn läuft mit `--reload`.
Änderungen wirken ohne Rebuild. Neu bauen nur bei Änderungen an
`requirements.txt`, `Dockerfile` oder `pytest.ini`:

```bash
docker compose up --build
```

`tests/` ist auch gemountet, Teständerungen brauchen also keinen Rebuild.
`pytest.ini` nicht, die geht nur per `COPY` ins Image.

Python-Shell im Container, praktisch zum Ausprobieren:

```bash
docker compose exec app python
```

Datenbank zurücksetzen (löscht alles):

```bash
docker compose down -v
```

Wenn die Seite hängt statt einen Fehler zu zeigen, ist meistens der
Worker-Prozess beim Import gestorben und der Reloader lebt noch weiter.
Der Container steht dann trotzdem auf "Up". Hilft:

```bash
docker compose logs app --tail 30
```

## Offen

- Power-Report (20-Minuten-Werte) einlesen, `power_readings` ist noch leer
- Teilleistung Ende Februar bis Anfang März klären
- `aerosol_optical_depth` wäre für die Trübung wahrscheinlich
  aussagekräftiger als `dust`
