import pandas as pd
from sqlalchemy import create_engine, text
from config import DB_URL

def get_engine():
    """Maakt en test de database connectie."""
    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return engine

def write_to_db(engine, df: pd.DataFrame, table_name: str, if_exists: str = "replace") -> None:
    """Schrijft een DataFrame weg naar de database."""
    with engine.begin() as conn:
        df.to_sql(table_name, con=conn, if_exists=if_exists, index=False)
    print(f"  Geschreven naar tabel: {table_name} ({len(df)} rijen)")