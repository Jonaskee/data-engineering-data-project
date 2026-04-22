# Units & Preprocessing — Data Engineering project

Dit document beschrijft de kolommen, eenheden en datakwaliteit van de 4 finale tabellen
(`consumptie`, `productie`, `wind`, `zon`) in de lokale Postgres.

---

## 1. Staat VÓÓR normalisatie (initiële laad vanuit bronnen)

### `consumptie` (240 rijen, uurlijks, 2026-02-01 → 2026-02-10)

| Kolom | Type | Unit | Bron | Opmerking |
|---|---|---|---|---|
| `tijd` | `timestamp` (naive) | — | DATE_TRUNC('hour', …) | UTC, geen tz-info |
| `elia_total_load_mw` | `double` | **MW** | Elia `ods001` | Nationale belasting België, 8318–13049 |
| `ev_zon_mw` | `double` | **MW** | Energie Vlaanderen `realtime_solar_*` | Som per uur over alle gemeenten, 0–3799 |
| `ev_wind_mw` | `double` | **MW** | Energie Vlaanderen `realtime_wind_*` | Som per uur over alle gemeenten, 95–1231 |

### `productie` (9192 rijen, uurlijks, 2025-02-28 → 2026-03-18)

| Kolom | Type | Unit | Opmerking |
|---|---|---|---|
| `tijd` | **`text`** | — | Bv. `"2025-02-28 23:00:00+00:00"` — moet cast naar timestamptz |
| `vlaanderen_zon_kwh` | `double` | **kWh** | Per uur |
| `vlaanderen_wind_kwh` | `double` | **kWh** | Per uur |
| `elia_zon_kwh` | `double` | **kWh** | Per uur |
| `elia_wind_kwh` | `double` | **kWh** | Per uur |

### `wind` (1.137.675 rijen, uurlijks, 2005-11 → 2026-03) — eigenlijk weerdata

| Kolom | Type | Unit | Opmerking |
|---|---|---|---|
| `tijdstip` | **`text`** | — | Met `+00:00`, moet cast |
| `wind_ecmwf_2026` | `double` | **m/s** | Windsnelheid (ECMWF model) |
| `wind_kmi_2002` | `double` | **m/s** | KMI station, veel NULLs |
| `wind_ukkel_2024` | `double` | **m/s** | Ukkel station, veel NULLs |
| `wind_antwerpen_archive` | `double` | **m/s** | Antwerpen archief, veel NULLs |

⚠️ Deze tabel bevat **windsnelheidsmetingen**, geen productie — features voor modellering.

### `zon` (2269 rijen, **dagelijks**, 2020-01-01 → 2026-03-18)

| Kolom | Type | Unit | Opmerking |
|---|---|---|---|
| `id` | `bigint` | — | Row-id (overbodig na load) |
| `datum` | **`text`** | — | Moet cast naar timestamp |
| `open_meteo_radiation` | `double` | **W/m² of MJ/m²** | 2264 non-null rijen |
| `kmi_radiation_avg` | `double` | idem | 1217/2269 non-null (46% missing) |
| `kaggle_radiation_avg` | `double` | idem | 1847/2269 non-null (19% missing) |

⚠️ Dagelijkse granulariteit — niet uurlijks zoals de andere tabellen.
⚠️ Kolommen zijn weerdata-features, geen productie.

---

## 2. Geïdentificeerde problemen

1. **Tijdkolommen als `text`** in `productie`, `wind`, `zon` — joins/filters op tijd vergen een cast.
2. **Unit-inconsistentie** tussen `consumptie` (MW) en `productie` (kWh). Factor 1000.
3. **Tijdzone-mix**: `consumptie.tijd` naive timestamp (UTC), `productie`/`wind` text met `+00:00`, `zon` naive.
4. **Temporele granulariteit**: `zon` is dagelijks, de rest uurlijks.
5. **NULL-dichtheid** in `wind`- en `zon`-tabellen (deels door historische gaps).
6. **Kolomnaamconventie** niet uniform: sommige hebben `_mw`/`_kwh` suffix, andere niet.
7. **Overbodige `id`-kolom** in `zon` (rij-index uit CSV).
8. **`wind`/`zon`** zijn weerdata, geen productie — naam misleidend maar functioneel OK als features.

---

## 3. Staat NÁ normalisatie

Uitgevoerd door de `normalize_units` task in de Airflow DAG (`pipelines/normalize.py`).
Transformaties zijn **idempotent**: de task detecteert reeds uitgevoerde stappen via
`information_schema` en slaat ze over bij een herlopen.

### `consumptie` (ongewijzigd — al correct)

| Kolom | Type | Unit |
|---|---|---|
| `tijd` | `timestamp` (naive, UTC) | — |
| `elia_total_load_mw` | `double` | **MW** |
| `ev_zon_mw` | `double` | **MW** |
| `ev_wind_mw` | `double` | **MW** |

### `productie` — types + units genormaliseerd

| Kolom | Type | Unit | Waardebereik |
|---|---|---|---|
| `tijd` | **`timestamptz`** | — | 2025-02-28 → 2026-03-18 |
| `vlaanderen_zon_mw` | `double` | **MW** (was kWh, ÷1000) | — |
| `vlaanderen_wind_mw` | `double` | **MW** | 0.28–1825.08 |
| `elia_zon_mw` | `double` | **MW** | — |
| `elia_wind_mw` | `double` | **MW** | 0.31–900.88 |

### `wind` (weerdata, types genormaliseerd)

| Kolom | Type | Unit |
|---|---|---|
| `tijdstip` | **`timestamptz`** | — |
| `wind_ecmwf_2026` | `double` | **m/s** |
| `wind_kmi_2002` | `double` | **m/s** |
| `wind_ukkel_2024` | `double` | **m/s** |
| `wind_antwerpen_archive` | `double` | **m/s** |

### `zon` (weerdata, types genormaliseerd + id verwijderd)

| Kolom | Type | Unit |
|---|---|---|
| `datum` | **`timestamp`** | — |
| `open_meteo_radiation` | `double` | W/m² of MJ/m² |
| `kmi_radiation_avg` | `double` | idem |
| `kaggle_radiation_avg` | `double` | idem |

---

## 4. Wat nu consistent is

- ✅ **Tijdkolommen**: allemaal `timestamp`/`timestamptz` (geen `text` meer) → direct joinable en filterbaar.
- ✅ **Productie-units**: alles in MW, zelfde schaal als `consumptie` → directe numerieke vergelijking mogelijk.
- ✅ **Kolomnaamconventie** voor productie-metrics: uniforme `_mw` suffix.
- ✅ **`zon.id`** verwijderd.

## 5. Wat bewust **niet** is aangepast

- **`wind`/`zon`** blijven in hun oorspronkelijke eenheden (m/s, W/m²). Dit zijn weerfeatures,
  geen productie-output — conversie naar MW heeft geen fysische betekenis.
- **`zon` blijft dagelijks** — resampling naar uurlijks vereist een domeinkeuze
  (forward-fill, lineaire interpolatie, …) die niet geautomatiseerd zou moeten gebeuren.
- **Missing values** in `wind` en `zon` worden niet ingevuld — imputatie is een model-
  specifieke keuze die hoort bij analyse, niet bij de ETL.
- **Tijdzones**: `consumptie.tijd` is naive UTC, `productie`/`wind` zijn `timestamptz` UTC,
  `zon.datum` is naive dagbasis. Bij joins: cast naar dezelfde type of gebruik `AT TIME ZONE 'UTC'`.

## 6. Pipeline flow

```
 elia          energie_vlaanderen    kaggle (optioneel)
   \                  |                 /
    \                 v                /
     -------> consumptie_combine <----
                      |
                      |        extra_datasets
                      v              |
                      +------> normalize_units
                                     |
                                     v
                                 export_csv
```

