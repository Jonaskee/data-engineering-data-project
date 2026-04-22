import pandas as pd
from pathlib import Path
from sqlalchemy import inspect
from db import write_to_db

EXTRA_DIR = Path("extra_datasets")

MAPPING = {
    "productie_combined.csv":    "productie",
    "v_wind_alles_compleet.csv": "wind",
    "sun_combined.csv":          "zon",
}


def _clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = (
        df.columns
        .str.strip()
        .str.strip('"')
        .str.lower()
        .str.replace(" ", "_", regex=False)
    )
    return df


def run_extra_datasets_pipeline(engine, force_reload=False):
    print("\n--- Start Extra Datasets Pipeline (productie, wind, zon) ---")

    existing = set(inspect(engine).get_table_names())

    for fname, table in MAPPING.items():
        path = EXTRA_DIR / fname
        if not path.exists():
            print(f"  ! {path} niet gevonden — overslaan.")
            continue

        if not force_reload and table in existing:
            print(f"  Tabel '{table}' bestaat al. Skipping.")
            continue

        print(f"  Lezen: {path.name} → tabel '{table}'")
        df = pd.read_csv(path)
        df = _clean_columns(df)
        write_to_db(engine, df, table)
