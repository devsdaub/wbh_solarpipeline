# SolarPipeline

Datenpipeline für mein 800-W-Balkonkraftwerk. Führt Produktionsdaten
(Hoymiles) mit Wetter- und Luftqualitätsdaten in einer PostgreSQL-Datenbank
zusammen und stellt sie in einem Dashboard dar.

## Schnellstart

Voraussetzung: Docker Desktop.

```bash
cp .env.example .env
docker compose up --build
```

## Endpunkte

| Pfad | Zweck |
|---|---|
| `/` | Dashboard |
| `/health` | Betriebszustand von Anwendung und Datenbank |
| `/docs` | Automatisch erzeugte OpenAPI-Dokumentation |


## Konfiguration

Anlagendaten stehen in `config/plant.yaml` und werden beim Start automatisch
in die Tabelle `plant_config` übernommen.


## Datenmodell

Star-Schema mit vier Tabellen:

| Tabelle | Zweck |
|---|---|
| `plant_config` | Stammdaten der Anlage (Dimension) |
| `daily_facts` | Tageswerte, Produktion und Wetter zusammengeführt (Fakten) |
| `hourly_weather` | Stündliche Wetter- und Luftqualitätsdaten |
| `power_readings` | 20-Minuten-Leistungswerte aus dem Hoymiles-Inverter |

Tabellen und Anlagenzeile entstehen automatisch beim Start


## Datenquellen

| Quelle | Endpunkt | Status |
|---|---|---|
| Open-Meteo Wetterarchiv | `archive-api.open-meteo.com/v1/archive` | angebunden |
| Open-Meteo Luftqualität | `air-quality-api.open-meteo.com/v1/air-quality` | angebunden |
| Hoymiles Energy-Report | CSV-Upload über das Dashboard | angebunden |
| Hoymiles Power-Report | CSV-Upload, 20-Minuten-Werte | offen |

Konfiguriert werden die Quellen in `config/sources.yaml`. Über das Feld
`enabled` lässt sich jede Quelle einzeln abschalten, ohne Code zu ändern.

### Datenabruf auslösen

```bash
curl -X POST http://localhost:8008/api/ingest/all
```

| Quelle | Endpunkt | Status |
|---|---|---|
| Open-Meteo Wetterarchiv | `archive-api.open-meteo.com/v1/archive` | angebunden |
| Open-Meteo Luftqualität | `air-quality-api.open-meteo.com/v1/air-quality` | angebunden |
| Hoymiles (CSV-Import) | manueller Upload | geplant |


## Hoymiles-Import

Der Energy-Report wird über das Formular auf der Startseite hochgeladen
oder über `POST /api/upload/energy`. Ein erneuter Import desselben
Zeitraums aktualisiert die vorhandenen Tageswerte.

### Umgang mit Formatvarianten

Das Hoymiles-Portal hat sein Exportformat während der Projektlaufzeit
geändert:

Beobachtete Varianten:

| | Variante 1 | Variante 2 | Variante 3 (aktuell) |
|---|---|---|---|
| Datumsspalte | `Date` | `Time` | `Time` |
| Leistungsangabe | keine | `Rated Power (W)` | `Capacity (kW)` |
| Verbrauch | `Consumption (kWh)` | entfällt | `Consumption (kWh)` |
| Zusatzspalten | keine | `Model`, `SN` | `Plant Creation Time` |
| Messwert | `Production (kWh)` | `Production (kWh)` | `Production (kWh)` |

Der Adapter übernimmt gezielt die Datums- und die Produktionsspalte, statt
bekannte Störspalten zu entfernen. Beide Datumsschreibweisen werden
akzeptiert. Alle nicht übernommenen Spalten werden protokolliert und sind
im Containerlog nachvollziehbar.

Fehlt die Spalte `Production (kWh)`, bricht der Import mit einer
verständlichen Meldung ab, statt leere Daten zu schreiben.

Liefert der Export eine Leistungsangabe mit, wird sie gegen
`module_capacity_wp` aus `config/plant.yaml` geprüft. Die Einheit
unterscheidet sich je nach Variante (Watt oder Kilowatt) und wird
umgerechnet. Eine Abweichung erzeugt eine Warnung, aber keinen Abbruch.


## Transformation

Die Stundenwerte aus `hourly_weather` werden mit pandas zu Tageswerten in
`daily_facts` verdichtet (`app/pipeline/transformation.py`):

| Zielspalte | Berechnung |
|---|---|
| `gti_kwh` | Summe der Stundenwerte geteilt durch 1000 (W/m² → kWh/m²) |
| `avg_temperature` | Tagesmittel |
| `avg_cloud_cover` | gerundetes Tagesmittel |
| `max_dust` | Tagesmaximum |
| `avg_pm10` | Tagesmittel |
| `eq` | `production_kwh / (gti_kwh × module_capacity_kwp)` |

Die Aggregation ist als reine Funktion auf DataFrames umgesetzt
(`aggregate_hourly`, `berechne_eq`, `finde_luecken`) und dadurch ohne
laufende Datenbank testbar. Das Laden und Schreiben ist davon getrennt.

Bei Summen wird `min_count=1` gesetzt. Ohne diese Angabe liefert pandas
für einen Tag ohne jeden Messwert die Summe 0 statt eines Fehlwerts, was
eine fehlende Messung fälschlich als "keine Einstrahlung" ausweisen würde.

## Scheduler

Die Pipeline läuft automatisch im Hintergrund. Konfiguration in
`config/scheduler.yaml`:

```yaml
scheduler:
  enabled: true
  jobs:
    pipeline:
      interval_minutes: 180
      enabled: true
```

## Diagramme

Das Dashboard zeigt zwei Diagramme, gezeichnet mit Chart.js:

| Diagramm | Datenendpunkt | Inhalt |
|---|---|---|
| Verlauf | `GET /api/data/daily?days=N` | Produktion und Einstrahlung als Zeitreihe |
| Streuung | `GET /api/data/scatter` | Produktion über Einstrahlung, ein Punkt je Tag |

Der Zeitraum des Verlaufsdiagramms ist über Schaltflächen wählbar
(30 Tage, 90 Tage, 1 Jahr). Er wird vom letzten vorhandenen Datenpunkt aus
zurückgerechnet, nicht vom aktuellen Datum, weil Produktions- und
Wetterdaten unterschiedlich weit reichen.

Fehlende Produktionswerte werden als `null` ausgeliefert und im Diagramm
als Unterbrechung dargestellt. Sie werden nicht durch Nullwerte ersetzt.

### Chart.js lokal eingebunden

`app/static/js/chart.umd.min.js` liegt im Repository und wird nicht von
einem CDN geladen. Damit ist die Anwendung offline lauffähig, und es
werden keine Betrachterdaten an Dritte übertragen.