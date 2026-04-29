import pandas as pd
from sqlalchemy import inspect
from config import DATA_DIR
import os

def export_all_tables_to_csv(engine):
    """Exporteert alle tabellen uit de database naar aparte CSV-bestanden in de data map."""
    print("Start met het exporteren van tabellen naar CSV...")
    
    # Haal alle tabelnamen op
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    if not tables:
        print("  Geen tabellen gevonden om te exporteren.")
        return
        
    export_dir = DATA_DIR / "exports"
    export_dir.mkdir(exist_ok=True, parents=True)
    
    for table_name in tables:
        # Sla Airflow metadata tabellen over om het overzichtelijk te houden voor de gebruiker
        if table_name.startswith(('ab_', 'dag_', 'task_', 'log', 'job', 'slot', 'variable', 'dataset', 'trigger', 'xcom', 'session', 'alembic')):
            continue
            
        print(f"  Exporteren van tabel '{table_name}'...")
        try:
            query = f"SELECT * FROM {table_name}"
            df = pd.read_sql(query, con=engine)
            
            csv_path = export_dir / f"{table_name}.csv"
            df.to_csv(csv_path, index=False)
            print(f"  [DONE] Opgeslagen: {csv_path} ({len(df)} rijen)")
        except Exception as e:
            print(f"  [ERROR] Fout bij exporteren van '{table_name}': {e}")
            
    print("Export pipeline voltooid!\n")
