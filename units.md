# Units & Preprocessing — Data Engineering project

Dit document beschrijft de 4 finale tabellen (`consumptie`, `productie`, `wind`, `zon`) in de lokale Postgres, zoals ze in de database staan **na** de volledige pipeline (fetch + combine + normalize). Cijfers gebaseerd op laatste succesvolle run (2026-04-22).

Date-window wordt gestuurd door `FILTER_START` / `FILTER_END` in `.env` (default: 2024-01-01 → 2026-03-31).

---

## 1. Finale schema's

### `consumptie` — Elia totale belasting België
**19.704 rijen · uurlijks · 2024-01-01 → 2026-03-31**

| Kolom | Type | Unit | Bereik |
|---|---|---|---|
| `tijd` | `timestamp` (naive UTC) | — | — |
| `elia_total_load_mw` | `double` | MW | 6.121 – 14.303 (gem. 9.330) |

Bron: Elia `ods001` (kwartierresolutie, geaggregeerd via `DATE_TRUNC('hour')` + `AVG()` in `pipelines/combine_data.py`).

### `productie` — Zon/wind-productie België + Vlaanderen
**9.192 rijen · uurlijks · 2025-02-28 → 2026-03-18**

| Kolom | Type | Unit | Bereik |
|---|---|---|---|
| `tijd` | `timestamptz` | — | — |
| `vlaanderen_zon_mw` | `double` | MW | na ÷1000 conversie |
| `vlaanderen_wind_mw` | `double` | MW | 0,28 – 1.825 |
| `elia_zon_mw` | `double` | MW | — |
| `elia_wind_mw` | `double` | MW | 0,31 – 901 |

Bron: `extra_datasets/productie_combined.csv` (input van productie-groep). Originele kolommen waren in kWh met `_kwh` suffix; `normalize_units` deelt door 1000 en hernoemt naar `_mw`.

### `wind` — Windsnelheidsmetingen
**1.137.675 rijen · uurlijks · 2005-11-10 → 2026-03-24**

| Kolom | Type | Unit | Opmerking |
|---|---|---|---|
| `tijdstip` | `timestamptz` | — | UTC |
| `wind_ecmwf_2026_kmh` | `double` | km/h | ECMWF, 1,8 – 84,9, volledig gevuld |
| `wind_kmi_2002_kmh` | `double` | km/h | KMI/Geo.be-station, veel NULLs |
| `wind_ukkel_2024_kmh` | `double` | km/h | Ukkel, veel NULLs |
| `wind_antwerpen_archive_kmh` | `double` | km/h | Antwerpen archief, veel NULLs |

Bron: `extra_datasets/v_wind_alles_compleet.csv`. Origineel in m/s — `normalize_units` doet ×3.6 en hernoemt kolommen naar `*_kmh` (spec vereist km/h).

### `zon` — Zonneradiatie Antwerpen (ECMWF)
**19.704 rijen · uurlijks · 2024-01-01 → 2026-03-31**

| Kolom | Type | Unit | Bereik |
|---|---|---|---|
| `tijdstip` | `timestamptz` | — | UTC |
| `ecmwf_radiation_wm2` | `double` | W/m² | 0 – 891 |
| `ecmwf_direct_wm2` | `double` | W/m² | — |
| `ecmwf_diffuse_wm2` | `double` | W/m² | — |

Bron: **Open Meteo ECMWF archive-API** live ophalen via `pipelines/zon_hourly.py` voor coördinaten 51,2194°N / 4,4025°E (Antwerpen). Vervangt de oorspronkelijke dagelijkse CSV-laad omdat de spec uurlijkse granulariteit vereist. Kaggle (Uccle) en Geo.be: known gap.

---

## 2. Transformaties (`pipelines/normalize.py`)

`normalize_units` is idempotent — detecteert al-uitgevoerde stappen via `information_schema` en slaat ze over bij een herlopen.

| Tabel | Transformatie | Reden |
|---|---|---|
| `productie` | `tijd` text → `timestamptz` | Joinbaar op tijd |
| `productie` | kolommen `_kwh` → `_mw`, waarden ÷1000 | Consistente eenheid met `consumptie` |
| `wind` | `tijdstip` text → `timestamptz` | Joinbaar op tijd |
| `wind` | kolommen m/s → km/h (×3.6) + rename naar `*_kmh` | Spec vereist km/h |
| `zon` | (legacy) `datum` text → `timestamp`, drop `id` | Alleen voor oude CSV-schema; nieuwe uurlijkse schema heeft dit al |

---

## 3. Wat nu consistent is

- ✅ **Tijdkolommen**: `timestamp`/`timestamptz`, nooit meer `text` → direct joinable
- ✅ **Productie-units**: alles in MW (zelfde schaal als `consumptie`)
- ✅ **Wind-units**: km/h conform spec
- ✅ **Zon-granulariteit**: uurlijks conform spec
- ✅ **Zon-unit**: expliciet W/m² (geen meer MJ/m²-ambiguïteit)
- ✅ **Kolomnaamconventie**: uniforme suffix per unit (`_mw`, `_kmh`, `_wm2`)

---

## 4. Wat bewust **niet** is aangepast

- **`wind` en `zon` blijven weer-features**, geen productie. Conversie naar MW heeft geen fysische betekenis en gebeurt niet.
- **Missing values** in oudere `wind`-kolommen (KMI/Ukkel/Antwerpen) worden niet ingevuld — imputatie is een modelkeuze (hoort bij analyse, niet bij ETL).
- **Kaggle-bronnen** (consumptie/wind/zon): geen credentials → bewust skip, gedocumenteerd in README als known gap. ECMWF dekt de kritieke data voor het ML-project.
- **Tijdzones**: `consumptie.tijd` is naive UTC, `productie`/`wind`/`zon` zijn `timestamptz` UTC. Bij joins: cast of gebruik `AT TIME ZONE 'UTC'`.

---

## 5. Pipeline flow

```
 elia          energie_vlaanderen   kaggle (skip)
   \                  |                 /
    \                 v                /
     -------> consumptie_combine <----
                      |                 extra_datasets (productie + wind CSVs)
                      |                          |
                      |                 zon_hourly_ecmwf (live Open Meteo API)
                      |                          |
                      +------> normalize_units <-+
                                     |
                                     v
                                     metadata
                                 export_csv
```

---

## 6. Bronnen per tabel (spec → implementatie)

| Tabel | Spec zegt | Geïmplementeerd |
|---|---|---|
| `consumptie` | Energie Vlaanderen, Elia, Kaggle | Elia ✓ · EV bewust weg (hoorde in productie) · Kaggle = known gap |
| `productie` | Energie Vlaanderen, Elia | EV ✓ · Elia ✓ (beide kolommen aanwezig) |
| `wind` | Open Meteo ECMWF, Geo.be, Kaggle (Uccle, Antwerpen) | ECMWF ✓ · KMI-stations dekken Geo.be gedeeltelijk · Kaggle = known gap |
| `zon` | Open Meteo ECMWF, Geo.be, Kaggle (Uccle) | ECMWF ✓ (live-fetch Antwerpen) · Geo.be + Kaggle = known gap |

overlapping -> 2025-02-28 → 2026-03-18 ≈ 9.000 uurlijkse rijen

  1. "Antwerpen" in spec vs. data-scope: productie is Vlaanderen/BE-breed, niet strikt Antwerps. zon-radiatie is
   wél specifiek voor Antwerpen (ECMWF fetch op 51,2194°N/4,4025°E). Model voorspelt dus BE-aggregaat met       
  Antwerpse weer-features. Noem dit expliciet in je README-problem-description.
  2. Kolom wind_ecmwf_2026_kmh: naam suggereert jaar 2026, maar data loopt 2005→2026. "2026" is eigenlijk een   
  bron-tag in de originele CSV. Verwarrend maar niet fout.
  3. NULLs in wind_kmi/ukkel/antwerpen_archive_kmh: geen probleem, gebruik alleen wind_ecmwf_2026_kmh als       
  feature (100% gevuld).
  4. Kaggle: documenteerbare gap, geen impact op trainbaarheid.

  Wat nog niet klaar is (MLops-infra, geen data)

  - Feature-tabel (join productie ⋈ zon ⋈ wind + lag/time-features) — nog niet gebouwd
  - MLFlow server + tracking + registry — nog niks opgezet
  - Prefect — nog steeds Airflow; moet vervangen worden
  - FastAPI web service + Docker-image — bestaat niet
  - Live ECMWF-forecast-fetcher (andere endpoint dan archive) voor batch-inference + API-input — nog niet       
  geschreven
  - Evidently + Grafana + auto-retrain trigger — niks
  - Tests, pre-commit, pinned deps — niks

  Conclusie: data-laag is go. Volgende stap is het ML-plan uitschrijven en Fase 1 starten (feature-tabel +      
  MLFlow).

  database checken: docker exec energie_db psql -U data_user -d energie_vlaanderen_db -c "SELECT 'consumptie' as t, COUNT(*) FROM consumptie UNION ALL SELECT 'productie', COUNT(*) FROM productie UNION ALL SELECT 'wind', COUNT(*) FROM wind UNION ALL SELECT 'zon', COUNT(*) FROM zon;"