import os
import requests
from sqlalchemy import inspect  # <-- Toegevoegd
from config import ELIA_API_BASE
from utils import fetch_api_data, save_raw_json, load_json_to_df
from db import write_to_db

DATASETS = {
    "ods001": ("total_load", "elia_total_load"),
    "ods031": ("wind_power", "elia_wind_power"),
    "ods032": ("solar_pv_power", "elia_solar_pv"),
}

DATE_FILTER = {"start": "2024-01-01", "end": "2025-12-31"}

def build_where_clause(date_field: str = "datetime") -> str | None:
    start = os.getenv("FILTER_START", DATE_FILTER.get("start"))
    end = os.getenv("FILTER_END", DATE_FILTER.get("end"))
    if start and end:
        return f"{date_field} >= '{start}' AND {date_field} <= '{end}'"
    return None

def run_elia_pipeline(engine, force_reload=False):  # <-- Parameter toegevoegd
    print("--- Start Elia Pipeline ---")
    
    # Check bestaande tabellen
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    for ds_id, (label, table_name) in DATASETS.items():
        print(f"\nVerwerken: {ds_id} ({label})")
        
        # Sla over als de tabel al bestaat en we niet forceren
        if not force_reload and table_name in existing_tables:
            print(f"  Tabel '{table_name}' bestaat al. Data wordt niet opnieuw gedownload.")
            continue
            
        # 1. Extract
        url = f"{ELIA_API_BASE}/{ds_id}/exports/json"
        params = {"limit": -1}
        where = build_where_clause()
        if where:
            params["where"] = where
            
        try:
            records = fetch_api_data(url, params)
            save_raw_json(label, records)
            
            # 2. Transform & Load
            df = load_json_to_df(label)
            print(f"  DataFrame shape: {df.shape}")
            write_to_db(engine, df, table_name)
            
        except requests.exceptions.HTTPError as e:
            print(f"  HTTP FOUT bij {ds_id}: {e.response.status_code}")
        except Exception as e:
            print(f"  FOUT bij {ds_id}: {e}")