from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Zorg dat de project-root op de PYTHONPATH staat zodat we pipelines/ kunnen importeren
PROJECT_ROOT = Path("/app")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from airflow import DAG
from airflow.operators.python import PythonOperator


def _get_engine():
    from db import get_engine
    return get_engine()


def task_elia(**_):
    from pipelines.elia import run_elia_pipeline
    run_elia_pipeline(_get_engine(), force_reload=True)


def task_vlaanderen(**_):
    from pipelines.energie_vlaanderen import run_vlaanderen_pipeline
    run_vlaanderen_pipeline(_get_engine())


def task_kaggle(**_):
    # Skipt netjes als de CSVs niet in data/kaggle/ staan
    from pipelines.kaggle import run_kaggle_pipeline
    run_kaggle_pipeline(_get_engine())


def task_consumptie(**_):
    from pipelines.combine_data import run_consumptie_combine
    run_consumptie_combine(_get_engine())


def task_extra_datasets(**_):
    from pipelines.extra_datasets import run_extra_datasets_pipeline
    run_extra_datasets_pipeline(_get_engine())


def task_zon_hourly(**_):
    from pipelines.zon_hourly import run_zon_hourly_pipeline
    run_zon_hourly_pipeline(_get_engine())


def task_normalize(**_):
    from pipelines.normalize import run_normalize_pipeline
    run_normalize_pipeline(_get_engine())


def task_export_csv(**_):
    from pipelines.export_csv import export_all_tables_to_csv
    export_all_tables_to_csv(_get_engine())


default_args = {
    "owner": "consumptie-groep",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="energie_pipeline",
    description="Haalt Elia + Energie Vlaanderen op, bouwt consumptie-tabel, laadt extra_datasets (productie/wind/zon), exporteert naar CSV.",
    start_date=datetime(2026, 1, 1),
    schedule=None,  # manueel triggeren
    catchup=False,
    default_args=default_args,
    tags=["energie", "data-eng-project"],
) as dag:

    t_elia = PythonOperator(task_id="elia", python_callable=task_elia)
    t_vlaanderen = PythonOperator(task_id="energie_vlaanderen", python_callable=task_vlaanderen)
    t_kaggle = PythonOperator(task_id="kaggle", python_callable=task_kaggle)
    t_consumptie = PythonOperator(task_id="consumptie_combine", python_callable=task_consumptie)
    t_extra = PythonOperator(task_id="extra_datasets", python_callable=task_extra_datasets)
    t_zon = PythonOperator(task_id="zon_hourly_ecmwf", python_callable=task_zon_hourly)
    t_normalize = PythonOperator(task_id="normalize_units", python_callable=task_normalize)
    t_export = PythonOperator(task_id="export_csv", python_callable=task_export_csv)

    [t_elia, t_vlaanderen, t_kaggle] >> t_consumptie
    [t_consumptie, t_extra, t_zon] >> t_normalize >> t_export
