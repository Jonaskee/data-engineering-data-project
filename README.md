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

### Dataset Structuur (Kolommen, Rijen & Waarden)
De daadwerkelijke datasetgrootte (aantal rijen) hangt af van het geselecteerde tijdsvenster in je `.env` bestand en de historische databeschikbaarheid. Gebaseerd op de standaard tijdsperiode (ca. 2 jaar) en de huidige data, ziet de structuur er als volgt uit:

#### 1. `consumptie` (~19.704 rijen)
- **Granulariteit**: Uurlijks
- **Kolommen**:
  - `tijd` (`timestamp`): Tijdstip van de meting (naive UTC).
  - `elia_total_load_mw` (`double`): Totale netbelasting in MW.
  - `ev_zon_mw` (`double`): Zonne-energie productiecapaciteit in MW.
  - `ev_wind_mw` (`double`): Windenergie productiecapaciteit in MW.

#### 2. `productie` (~9.192 rijen)
- **Granulariteit**: Uurlijks
- **Kolommen**:
  - `tijd` (`timestamptz`): Tijdstip van de meting met tijdzone.
  - `vlaanderen_zon_mw` (`double`): Zonne-energie productie in Vlaanderen (genormaliseerd naar MW).
  - `vlaanderen_wind_mw` (`double`): Windenergie productie in Vlaanderen (genormaliseerd naar MW).
  - `elia_zon_mw` (`double`): Zonne-energie productie volgens Elia (MW).
  - `elia_wind_mw` (`double`): Windenergie productie volgens Elia (MW).

#### 3. `wind` (~1.137.675 rijen)
- **Granulariteit**: Uurlijks (historische waarden vanaf 2002)
- **Kolommen**:
  - `tijdstip` (`timestamptz`): Tijdstip van de meting.
  - `wind_ecmwf_2026_kmh` (`double`): Windsnelheid via ECMWF (km/h).
  - `wind_kmi_2002_kmh` (`double`): Windsnelheid via KMI (km/h, bevat `NULL`s).
  - `wind_ukkel_2024_kmh` (`double`): Windsnelheid Ukkel (km/h, bevat `NULL`s).
  - `wind_antwerpen_archive_kmh` (`double`): Windsnelheid Antwerpen (km/h, bevat `NULL`s).

#### 4. `zon` (~19.704 rijen)
- **Granulariteit**: Uurlijks
- **Kolommen**:
  - `tijd` (`timestamp`): Tijdstip van de meting.
  - `ecmwf_radiation_wm2` (`double`): Globale zonnestraling (W/m²).
  - `ecmwf_direct_wm2` (`double`): Directe zonnestraling (W/m²).
  - `ecmwf_diffuse_wm2` (`double`): Diffuse zonnestraling (W/m²).
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

4. **Grafana Dashboard:**
    docker compose up -d grafana

   - **Grafana UI:** [http://localhost:3000](http://localhost:3000)
     - Login: `admin`
     - Wachtwoord: `admin`

   Het dashboard **"Energie Dashboard"** wordt automatisch geladen via provisioning (geen handmatige configuratie nodig). De PostgreSQL datasource is al geconfigureerd.

   Het dashboard bevat 5 panelen:

   | Paneel | Tabel | Eenheid |
   |--------|-------|---------|
   | Elektriciteitsverbruik (Elia) | `consumptie` | MW |
   | Productie per bron | `productie` | MW |
   | Zonnestraling Antwerpen | `zon` | W/m² |
   | Windsnelheid | `wind` | km/h |
   | Totale productie vs verbruik | `consumptie` + `productie` | MW |

   > Zorg dat je eerst de pipeline hebt uitgevoerd (stap 3) voordat je data in Grafana verwacht.

![airflow pipeline](dag.png)
![grafana visualisatie](image.png)