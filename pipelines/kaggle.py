import pandas as pd
import numpy as np
from pathlib import Path
from sqlalchemy import inspect  # <-- Toegevoegd
from db import write_to_db

KAGGLE_DIR = Path("data/kaggle")

# ==============================
# ROBUUST CSV INLEZEN
# ==============================
def read_csv_clean(path):
    print(f"    Lezen van: {path.name}...")
    df = pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig")
    df.columns = df.columns.str.strip()
    return df

# ==============================
# TRANSFORMATIES
# ==============================
def convert_all_to_kw(df, year, time_col="Time"):
    """
    Zet alle energie kolommen naar kW.
    Voor 6 juni staat data al in kW.
    Na 6 juni staat data in W → delen door 1000.
    """
    df[time_col] = pd.to_datetime(df[time_col])
    cutoff = pd.Timestamp(f"{year}-06-06")

    numeric_cols = df.select_dtypes(include=[np.number]).columns
    mask = df[time_col] >= cutoff

    # W → kW
    df.loc[mask, numeric_cols] = df.loc[mask, numeric_cols] / 1000.0
    return df

def process_district(path, year):
    df = read_csv_clean(path)
    df = convert_all_to_kw(df, year)
    df["Year"] = year

    components = ["Warmtenet", "Warmtepomp", "Waterzuivering", "Vacuum", "Laadpalen", "Overig"]
    missing = [c for c in components if c not in df.columns]
    if missing:
        raise ValueError(f"Ontbrekende kolommen in district {year}: {missing}")

    # herbereken total
    df["Total_calc"] = df[components].sum(axis=1)
    
    # Kolomnamen opschonen voor de DB
    df.columns = df.columns.str.lower()
    return df

def process_private_2021(path):
    df = read_csv_clean(path)
    
    # private units 2021 zijn blijkbaar altijd in W → kW
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df[numeric_cols] = df[numeric_cols] / 1000.0
    df["Time"] = pd.to_datetime(df["Time"])

    df_long = df.melt(id_vars=["Time"], var_name="Apartment", value_name="Power_kW")
    df_long["Apartment"] = df_long["Apartment"].astype(int)
    df_long["Tariff"] = 0
    df_long["Year"] = 2021
    return df_long

def process_private_2022(path):
    df = read_csv_clean(path)
    df["Time"] = pd.to_datetime(df["Time"])
    
    # verwijder duplicates
    df = df.loc[:, ~df.columns.duplicated()]

    # alleen kolommen met x.y structuur
    valid_cols = ["Time"] + [c for c in df.columns if c.count(".") == 1]
    df = df[valid_cols]

    # W → kW
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df[numeric_cols] = df[numeric_cols] / 1000.0

    df_long = df.melt(id_vars=["Time"], var_name="Apartment_Tariff", value_name="Power_kW")
    
    split_cols = df_long["Apartment_Tariff"].str.split(".", expand=True)
    split_cols.columns = ["Apartment", "Tariff"]
    df_long["Apartment"] = split_cols["Apartment"].astype(int)
    df_long["Tariff"] = split_cols["Tariff"].astype(int)
    df_long["Year"] = 2022
    df_long = df_long.drop(columns=["Apartment_Tariff"])
    return df_long

# ==============================
# PIPELINE FUNCTIE
# ==============================
def run_kaggle_pipeline(engine, force_reload=False):
    print("\n--- Start Kaggle Pipeline ---")
    
    # Check of de tabellen al bestaan
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    if not force_reload and "kaggle_district_raw" in existing_tables and "kaggle_private_raw" in existing_tables:
        print("  Kaggle tabellen bestaan al in de DB. Skipping verwerking.")
        return

    # Paden
    d21_path = KAGGLE_DIR / "2021_ElectricPower_15min.csv"
    d22_path = KAGGLE_DIR / "2022_ElectricPower_15min.csv"
    p21_path = KAGGLE_DIR / "2021_ElectricPowerPrivateUnits_15min.csv"
    p22_path = KAGGLE_DIR / "2022_ElectricPowerPrivateUnits_15min.csv"

    # Check of bestanden bestaan
    if not all(p.exists() for p in [d21_path, d22_path, p21_path, p22_path]):
        print("  Skipping Kaggle pipeline: Niet alle CSV bestanden gevonden in data/kaggle/")
        return

    # 1. District Data (Openbaar/Gedeeld)
    print("\n  Verwerken District Data...")
    try:
        district_2021 = process_district(d21_path, 2021)
        district_2022 = process_district(d22_path, 2022)
        district_merged = pd.concat([district_2021, district_2022]).sort_values("time")
        
        write_to_db(engine, district_merged, "kaggle_district_raw")
    except Exception as e:
         print(f"  FOUT in District Data: {e}")

    # 2. Private Units Data
    print("\n  Verwerken Private Units Data...")
    try:
        private_2021 = process_private_2021(p21_path)
        private_2022 = process_private_2022(p22_path)
        private_merged = pd.concat([private_2021, private_2022]).sort_values(["Time", "Apartment"])
        
        # Kolomnamen opschonen voor DB
        private_merged.columns = private_merged.columns.str.lower()
        write_to_db(engine, private_merged, "kaggle_private_raw")
    except Exception as e:
         print(f"  FOUT in Private Units Data: {e}")