# Energie Data Pipeline

Deze repository bevat een geautomatiseerde data pipeline, gedreven door Apache Airflow, die energiedata ophaalt, verwerkt en opslaat in een PostgreSQL database.

## Architectuur en Setup

- **Airflow**: Draait in Docker (`apache/airflow:2.9.3-python3.11`) in standalone mode en gebruikt PostgreSQL voor de metadata.
- **PostgreSQL**: Slaat zowel de Airflow metadata op als de verwerkte datasets.
- **DAG**: `dags/energie_dag.py` bevat de `energie_pipeline` DAG, met flow:
  1. `elia`, `energie_vlaanderen`, `kaggle` (parallel)
  2. `consumptie_combine`, `extra_datasets`, `zon_hourly_ecmwf` (parallel)
  3. `normalize_units` (types + units: kWh→MW, m/s→km/h, text→timestamp)
  4. `export_csv`

## Datasets

Na een succesvolle run zijn 4 tabellen aanwezig in de Postgres database. Bron-mapping volgens opdracht-spec:

| Tabel | Bronnen (spec) | Feature | Implementatie |
|-------|---------------|---------|---------------|
| `consumptie` | Energie Vlaanderen, Elia, Kaggle | Grid load (MW) per uur | Elia `ods001` total_load. EV-productie-kolommen zijn bewust weggelaten (horen in `productie`). **Kaggle: known gap (geen credentials).** |
| `productie` | Energie Vlaanderen, Elia | Solar & wind production (MW) per uur | `productie_combined.csv` → tabel `productie`, kolommen `vlaanderen_zon_mw`, `vlaanderen_wind_mw`, `elia_zon_mw`, `elia_wind_mw` |
| `wind` | Open Meteo ECMWF, Geo.be, Kaggle (Uccle, Antwerpen) | Wind speed (km/h) per uur | `v_wind_alles_compleet.csv` → genormaliseerd van m/s naar km/h (×3.6). Kolommen eindigen op `_kmh`. **Kaggle: known gap.** |
| `zon` | Open Meteo ECMWF, Geo.be, Kaggle (Uccle) | Solar radiation (W/m²) per uur | Uurlijks opgehaald via Open Meteo ECMWF archive-API voor Antwerpen (lat 51.2194, lon 4.4025). Kolommen: `ecmwf_radiation_wm2`, `ecmwf_direct_wm2`, `ecmwf_diffuse_wm2`. **Kaggle/Geo.be: known gap.** |

Het date-window (`FILTER_START` / `FILTER_END` in `.env`) stuurt Elia én de ECMWF-fetch. Default: 2024-01-01 → 2026-03-31.

### Known gaps
- **Kaggle-integratie**: geen credentials beschikbaar. Wordt voor alle 3 Kaggle-bronnen (consumptie/wind/zon) overgeslagen. De Open Meteo ECMWF-bron dekt de kritieke data voor het ML-project (Renewable Energy Forecasting).

## Gebruik

1. **Start de omgeving:**
   Zorg dat Docker draait en start alle services via docker compose:
   ```bash
   docker compose up -d
   ```

2. **Toegang tot Services:**

   - **Apache Airflow UI:** [http://localhost:8080](http://localhost:8080)
     - Login: `admin`
     - Wachtwoord: `hCmNTNHrs7duBzcn`
   
   - **pgAdmin:** [http://localhost:5050](http://localhost:5050)
     - Login: `admin@admin.com`
     - Wachtwoord: `admin`

   - **PostgreSQL Database:**
     - Gebruiker: `data_user`
     - Wachtwoord: `super_geheim_wachtwoord`

3. **Pipeline uitvoeren:**
   Je kunt de pipeline handmatig triggeren via de play-knop in de Airflow UI of via de command line interface:
   ```bash
   docker exec energie_airflow airflow dags trigger energie_pipeline
   ```
