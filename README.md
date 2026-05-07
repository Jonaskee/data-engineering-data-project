# Energie Data Pipeline

Deze repository bevat een data pipeline, door Apache Airflow, die energiedata ophaalt, verwerkt en opslaat in een PostgreSQL database.

## Architectuur en Setup

- **Airflow**: Draait in Docker (`apache/airflow:2.9.3-python3.11`) in standalone mode en gebruikt PostgreSQL voor de metadata.
- **PostgreSQL**: Slaat zowel de Airflow metadata op als de verwerkte datasets.
- **DAG**: `dags/energie_dag.py` bevat de `energie_pipeline` DAG, met flow:
  1. `elia`, `energie_vlaanderen`, `kaggle` (parallel)
  2. `consumptie_combine`, `extra_datasets`, `zon_hourly_ecmwf` (parallel)
  3. `normalize_units` (types + units: kWh→MW, m/s→km/h, text→timestamp)
  4. `export_csv`

## Datasets
!!! folder extra_datasets bevat nog niets, download deze via digitap data engineering. En zet productie_combined, sun_combined en v_wind_alles_compleet csv bestanden in de folder extra_datasets. !!! verwijder consumptie.csv. !!!

Na een succesvolle run zijn 4 tabellen aanwezig in de Postgres database:

| Tabel | Bronnen (spec) | Feature | Implementatie |
|-------|---------------|---------|---------------|
| `consumptie` | Energie Vlaanderen, Elia, Kaggle | Grid load (MW) per uur | Elia `ods001` total_load. EV-productie-kolommen zijn bewust weggelaten (horen in `productie`). |
| `productie` | Energie Vlaanderen, Elia | Solar & wind production (MW) per uur | `productie_combined.csv` → tabel `productie`, kolommen `vlaanderen_zon_mw`, `vlaanderen_wind_mw`, `elia_zon_mw`, `elia_wind_mw` |
| `wind` | Open Meteo ECMWF, Geo.be, Kaggle (Uccle, Antwerpen) | Wind speed (km/h) per uur | `v_wind_alles_compleet.csv` → genormaliseerd van m/s naar km/h (×3.6). Kolommen eindigen op `_kmh`.|
| `zon` | Open Meteo ECMWF, Geo.be, Kaggle (Uccle) | Solar radiation (W/m²) per uur | Uurlijks opgehaald via Open Meteo ECMWF archive-API voor Antwerpen (lat 51.2194, lon 4.4025). Kolommen: `ecmwf_radiation_wm2`, `ecmwf_direct_wm2`, `ecmwf_diffuse_wm2`. |

**pas het date window aan in de .env file als je meer data wilt downloaden**, het date-window (`FILTER_START` / `FILTER_END` in `.env`) stuurt Elia én de ECMWF-fetch. Default: 2024-01-01 → 2026-03-31.

### Dataset Structuur (Kolommen, Rijen & Waarden)
De daadwerkelijke datasetgrootte (aantal rijen) hangt af van het geselecteerde tijdsvenster in je `.env`

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

## Data Opslag & Externe Toegang

De verwerkte data wordt persistent opgeslagen in de PostgreSQL-container (`energie_db`) via een Docker Named Volume (`pgdata`). Om deze data voor MLops/ander project te gebruiken, kan je het doen op volgende manieren:

### 1. PostgreSQL Connectie via Poort 5432
De databasepoort `5432` is via `docker-compose.yml` expliciet gemapped naar de host machine. Dit maakt rechtstreekse en up-to-date SQL-queries mogelijk vanuit externe applicaties (zoals een extern Python/pandas script).

**Connectiestring:**
```text
postgresql+psycopg2://<PGUSER>:<PGPASSWORD>@localhost:5432/<PGDATABASE>
```
*(Voorbeeld met standaardgegevens: `postgresql+psycopg2://data_user:super_geheim_wachtwoord@localhost:5432/energie_db`)*

### 2. CSV Bestanden (Statische Export)
De pijplijn bevat een automatische export-taak (`export_csv.py`) die de volledige inhoud van alle tabellen exporteert naar losse `.csv`-bestanden. Deze bestanden bieden een statische momentopname en zijn ideaal voor analyses zonder dat de database online staat.

- **Relatief pad in project:** `./data/exports/`
- **Voorbeeld pad naar consumptie dataset:** `C:\Jaar2_semester_2\data_eng\data_project\data\exports\consumptie.csv`

## Claude MCP Integratie

Om de educatieve MCP (Model Context Protocol) server toe te voegen aan je lokale Claude omgeving, voer je het volgende commando uit. Dit zorgt ervoor dat Claude de lokale server herkent en de tools uit het script kan gebruiken:

```bash
claude mcp add mijn-educatieve-mcp python mcp_server.py
```

## Energie Inkoop Optimalisatie (Grafana Analyse)

Voor deze week heb ik in Grafana een uitgebreide analyse toegevoegd om het beste moment te bepalen voor de inkoop van energie. Dit gebeurt op basis van de historische netto-vraag (consumptie min totale productie van zon en wind) en de verhouding tussen productie en consumptie.

- **Koop-score (%)**: Een berekende score waarbij uren met een hoog aanbod (productie) en een relatief lage vraag (consumptie) de hoogste percentages behalen.
- **Beste bestelmomenten**: Uit de analyse blijkt dat de uren rond de middag (door piek in zonne-productie) en in het weekend (door lager verbruik) de meest gunstige momenten zijn om energie in te kopen.

## Voorbeeld uivoer
### airflow pipeline
![airflow pipeline](dag.png)
### grafana visualisatie
![grafana visualisatie](grafana.png)
### metadata visualisatie in grafana
![grafana visualisatie](metadata.png)
### koop-score tabel (beste inkoopuren)
![koop-score tabel](koop-score-procent.png)
### bestelmoment 24 uur (koop-score en correlatie)
![beste moment per uur](koop-score-24u.png)
### beste koopdagen (laagste netto-vraag)
![beste inkoop dagen](beste-dagen-kopen.png)
### mcp server test met claude code
![mcp server](mcp.png)