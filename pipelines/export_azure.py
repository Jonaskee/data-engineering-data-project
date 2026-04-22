import os
import pandas as pd
from sqlalchemy import create_engine

def export_master_to_azure(local_engine):
    print("\n--- Start Export naar Azure PostgreSQL ---")
    
    # Haal de Azure URL op uit je environment variabelen
    azure_url = os.getenv("AZURE_DB_URL")
    
    if not azure_url:
        print("  ✗ FOUT: AZURE_DB_URL niet gevonden. Check je .env bestand.")
        return

    try:
        # Maak verbinding met de Azure database
        print("  Verbinden met Azure PostgreSQL...")
        azure_engine = create_engine(azure_url)
        
        # 1. Lees de master_energy_table uit je lokale/bron database
        print("  Ophalen van 'master_energy_table' uit lokale database...")
        df_master = pd.read_sql("SELECT * FROM master_energy_table", con=local_engine)
        
        if df_master.empty:
            print("  ! WAARSCHUWING: master_energy_table is leeg. Export geannuleerd.")
            return

        # 2. Schrijf naar Azure
        # if_exists="replace" zorgt ervoor dat de oude tabel in Azure wordt verwijderd 
        # en een nieuwe, schone tabel wordt aangemaakt.
        print(f"  Wegschrijven van {len(df_master)} rijen naar Azure (oude data wordt overschreven)...")
        df_master.to_sql(
            name="master_energy_table", 
            con=azure_engine, 
            if_exists="replace", 
            index=False
        )
        
        print("  ✓ SUCCES: master_energy_table staat vers op Azure!")
        
    except Exception as e:
        print(f"  ✗ FOUT bij het exporteren naar Azure: {e}")