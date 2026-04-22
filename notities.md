Alles draait via Airflow. DAG-run afgerond in 15s, 4 tabellen aanwezig in Postgres:                                            
                                                                                                                                 
  ┌────────────┬───────────┐                                                                         
  │   Tabel    │   Rijen   │                                                                                                   ├────────────┼───────────┤
  │ consumptie │ 240       │                                                                                                   
  ├────────────┼───────────┤
  │ productie  │ 9.192     │
  ├────────────┼───────────┤
  │ wind       │ 1.137.675 │
  ├────────────┼───────────┤
  │ zon        │ 2.269     │
  └────────────┴───────────┘

  Nieuwe setup:
  - dags/energie_dag.py — DAG energie_pipeline met 5 tasks: elia + energie_vlaanderen (parallel) → consumptie_combine +
  extra_datasets (parallel) → export_csv
  - docker-compose.yml — app service vervangen door airflow (image apache/airflow:2.9.3-python3.11, standalone mode, metadata in 
  bestaande Postgres)

  Gebruik:
  - Start alles: docker compose up -d
  - Airflow UI: http://localhost:8080 — login admin / hCmNTNHrs7duBzcn
  - pgAdmin: http://localhost:5050
  - DAG triggeren via UI (play-knop) of CLI: docker exec energie_airflow airflow dags trigger energie_pipeline


  De inloggegevens voor de Airflow UI in deze folder zijn:

URL: http://localhost:8080
Gebruikersnaam: admin
Wachtwoord: hCmNTNHrs7duBzcn
Deze gegevens zijn terug te vinden in het bestand notities.md.

Ter aanvulling zijn dit de overige inloggegevens voor de bijbehorende services (uit .env):

pgAdmin (http://localhost:5050): admin@admin.com / admin
Postgres Database: data_user / super_geheim_wachtwoord