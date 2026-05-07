import os
import sys
import pandas as pd
from sqlalchemy import text

# Zorg dat we de database connectie kunnen importeren
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from db import get_engine

def bereken_dagelijks_koop_advies():
    """
    Berekent per dag of het een gunstig moment is om energie aan te kopen (1 = Ja, 0 = Nee)
    gebaseerd op de verhouding tussen de totale hernieuwbare productie en consumptie.
    """
    print("Verbinden met de database...")
    engine = get_engine()
    
    query = """
    WITH dagelijkse_stats AS (
        SELECT 
            DATE(c.tijd AT TIME ZONE 'UTC') as dag,
            AVG(c.elia_total_load_mw) as avg_consumptie_mw,
            AVG(p.elia_zon_mw + p.elia_wind_mw + COALESCE(p.vlaanderen_zon_mw, 0) + COALESCE(p.vlaanderen_wind_mw, 0)) as avg_productie_mw
        FROM consumptie c
        JOIN productie p ON DATE_TRUNC('hour', c.tijd AT TIME ZONE 'UTC') = DATE_TRUNC('hour', p.tijd AT TIME ZONE 'UTC')
        GROUP BY 1
    )
    SELECT 
        dag as "Datum",
        ROUND(avg_consumptie_mw::numeric, 0) as "Gem. Consumptie (MW)",
        ROUND(avg_productie_mw::numeric, 0) as "Gem. Productie (MW)",
        ROUND((avg_productie_mw / NULLIF(avg_consumptie_mw, 0))::numeric, 3) as "Ratio (Prod/Cons)",
        CASE 
            -- Threshold bepalen voor een 'goede' inkoopdag. 
            -- We stellen in dat wanneer productie minimaal 30% (0.30) van de consumptie
            -- dekt op daggemiddelde, dit uitzonderlijk hoog is en een ideaal koopmoment is (1 = Kopen).
            WHEN (avg_productie_mw / NULLIF(avg_consumptie_mw, 0)) >= 0.30 THEN 1 
            ELSE 0 
        END as "Kopen? (0/1)"
    FROM dagelijkse_stats
    ORDER BY "Datum" DESC
    LIMIT 30; -- Toon de laatste 30 beschikbare dagen
    """
    
    print("Dagelijks aankoopadvies ophalen...")
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
        
    print("\n--- Dagelijks Koop-advies (Laatste 30 Dagen) ---")
    print(df.to_string(index=False))
    
    # 1. Opslaan in de database
    print("\nData opslaan in PostgreSQL tabel 'dagelijks_koop_advies'...")
    df.to_sql('dagelijks_koop_advies', con=engine, if_exists='replace', index=False)
    print("Succesvol opgeslagen in de database!")

    # 2. Opslaan als CSV
    output_dir = os.path.join(project_root, "data", "exports")
    os.makedirs(output_dir, exist_ok=True)
    export_path = os.path.join(output_dir, "dagelijks_koop_advies.csv")
    df.to_csv(export_path, index=False)
    print(f"Advies succesvol geëxporteerd naar: {export_path}")

if __name__ == "__main__":
    bereken_dagelijks_koop_advies()
