"""Uurlijkse zonneradiatie voor Antwerpen via Open Meteo ECMWF archive.

Vervangt de dagelijkse `zon` tabel door een uurlijkse versie (W/m²) die matcht
met de opdracht-spec en meteen als feature-bron voor de ML-web-service dient
(zelfde endpoint-familie wordt later gebruikt voor live 24h-forecast).
"""

import os
import pandas as pd
import requests
from sqlalchemy import inspect, text

ANTWERPEN_LAT = 51.2194
ANTWERPEN_LON = 4.4025
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def _fetch_hourly_radiation(start: str, end: str) -> pd.DataFrame:
    params = {
        "latitude": ANTWERPEN_LAT,
        "longitude": ANTWERPEN_LON,
        "start_date": start,
        "end_date": end,
        "hourly": "shortwave_radiation,direct_radiation,diffuse_radiation",
        "timezone": "UTC",
    }
    r = requests.get(ARCHIVE_URL, params=params, timeout=120)
    r.raise_for_status()
    h = r.json()["hourly"]
    return pd.DataFrame({
        "tijdstip": pd.to_datetime(h["time"], utc=True),
        "ecmwf_radiation_wm2": h["shortwave_radiation"],
        "ecmwf_direct_wm2": h["direct_radiation"],
        "ecmwf_diffuse_wm2": h["diffuse_radiation"],
    })


def _needs_rebuild(engine) -> bool:
    insp = inspect(engine)
    if "zon" not in insp.get_table_names():
        return True
    cols = {c["name"] for c in insp.get_columns("zon")}
    # Nieuwe schema heeft tijdstip + ecmwf_radiation_wm2; oude had datum + open_meteo_radiation
    return not ({"tijdstip", "ecmwf_radiation_wm2"} <= cols)


def run_zon_hourly_pipeline(engine, force_reload=False):
    print("\n--- Start Zon Hourly Pipeline (ECMWF Archive, Antwerpen) ---")

    if not force_reload and not _needs_rebuild(engine):
        print("  'zon' tabel is al uurlijks (ECMWF). Skipping.")
        return

    from config import FILTER_START, FILTER_END
    start = FILTER_START
    end = FILTER_END

    print(f"  Ophalen {start} - {end} (lat={ANTWERPEN_LAT}, lon={ANTWERPEN_LON})")
    try:
        df = _fetch_hourly_radiation(start, end)
    except Exception as e:
        print(f"  FOUT bij ophalen ECMWF archive: {e}")
        return

    print(f"  {len(df)} uurlijkse rijen opgehaald.")

    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS zon"))
    df.to_sql("zon", engine, if_exists="replace", index=False)
    print(f"  SUCCES: 'zon' tabel herbouwd ({len(df)} rijen, uurlijks, W/m²).")
