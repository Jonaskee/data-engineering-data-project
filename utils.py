import json
import requests
import pandas as pd
from pathlib import Path
from config import DATA_DIR
from io import StringIO
from datetime import date, timedelta

def fetch_api_data(url: str, params: dict = None) -> list[dict]:
    """Haalt data op van een generieke API en retourneert een lijst met records."""
    response = requests.get(url, params=params, timeout=120, stream=True)
    response.raise_for_status()
    data = response.json()
    
    if isinstance(data, list):
        return data
    return data.get("results", data)

def save_raw_json(label: str, records: list[dict]) -> Path:
    """Slaat een lijst met dicts op als JSON."""
    path = DATA_DIR / f"{label}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"  Opgeslagen: {path} ({len(records)} records)")
    return path

def load_json_to_df(label: str) -> pd.DataFrame:
    """Laadt een JSON bestand in een opgeschoond Pandas DataFrame."""
    path = DATA_DIR / f"{label}.json"
    if not path.exists():
        raise FileNotFoundError(f"Bestand niet gevonden: {path}")
        
    with open(path, "r", encoding="utf-8") as f:
        records = json.load(f)
        
    df = pd.json_normalize(records)
    # Kolommen opschonen
    df.columns = (
        df.columns.str.lower()
        .str.replace(".", "_", regex=False)
        .str.replace(" ", "_", regex=False)
    )
    return df
def daterange(start: date, end: date):
    """Genereert een reeks datums van start tot eind."""
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)

def fetch_csv_to_df(url: str, sep: str = ",") -> pd.DataFrame | None:
    """Download een CSV via een URL en zet het direct in een DataFrame."""
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()

        # Specifieke afhandeling voor Statbel (REFNIS) ivm pipe-scheidingstekens en encodings
        if sep == "|":
            decoded = None
            for enc in ("utf-8", "cp1252", "latin-1"):
                try:
                    decoded = resp.content.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            if decoded is None:
                decoded = resp.content.decode("utf-8", errors="replace")
            return pd.read_csv(StringIO(decoded), sep=sep, dtype=str)
            
        return pd.read_csv(StringIO(resp.text), sep=sep)
        
    except requests.RequestException as exc:
        print(f"  Fout bij ophalen {url}: {exc}")
        return None