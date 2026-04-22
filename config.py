import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Database
DB_URL = (
    f"postgresql+psycopg2://{os.getenv('PGUSER')}:"
    f"{os.getenv('PGPASSWORD')}@{os.getenv('PGHOST')}:"
    f"{os.getenv('PGPORT')}/{os.getenv('PGDATABASE')}"
)

# Mappen
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# API & URL Instellingen
ELIA_API_BASE = os.getenv("ELIA_API_BASE", "https://opendata.elia.be/api/explore/v2.1/catalog/datasets")

# Energie Vlaanderen (Netlify Mock/Test API) & Statbel
VLAANDEREN_URLS = {
    "solar": "https://admiring-leakey-15793c.netlify.app/data/realtime/realtime_solar_{date}.csv",
    "wind": "https://admiring-leakey-15793c.netlify.app/data/realtime/realtime_wind_{date}.csv",
    "capacity_solar": "https://admiring-leakey-15793c.netlify.app/data/realtime/installed_capacity_solar_{date}.csv",
    "capacity_wind": "https://admiring-leakey-15793c.netlify.app/data/realtime/installed_capacity_wind_{date}.csv"
}
REFNIS_URL = "https://statbel.fgov.be/sites/default/files/Over_Statbel_FR/Nomenclaturen/REFNIS_2025.csv"

# Filters
FILTER_START = os.getenv("FILTER_START", "2026-02-01")
FILTER_END = os.getenv("FILTER_END", "2026-02-10")