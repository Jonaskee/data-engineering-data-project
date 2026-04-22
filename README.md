# Energie Data Pipeline

Deze repository bevat een geautomatiseerde data pipeline, gedreven door Apache Airflow, die energiedata ophaalt, verwerkt en opslaat in een PostgreSQL database.

## Architectuur en Setup

- **Airflow**: Draait in Docker (`apache/airflow:2.9.3-python3.11`) in standalone mode en gebruikt PostgreSQL voor de metadata.
- **PostgreSQL**: Slaat zowel de Airflow metadata op als de verwerkte datasets.
- **DAG**: `dags/energie_dag.py` bevat de `energie_pipeline` DAG, welke bestaat uit 5 tasks:
  1. `elia` + `energie_vlaanderen` (parallel)
  2. `consumptie_combine` + `extra_datasets` (parallel)
  3. `export_csv`

## Datasets

Na een succesvolle run (doorlooptijd ongeveer 15s) zijn de volgende tabellen aanwezig in de Postgres database:

| Tabel | Rijen |
|-------|-------|
| consumptie | 240 |
| productie | 9.192 |
| wind | 1.137.675 |
| zon | 2.269 |

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
