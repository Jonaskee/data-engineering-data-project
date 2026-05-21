import pandas as pd
from sqlalchemy import text
from db import write_to_db

def run_metadata_pipeline(engine):
    print("Start metadata pipeline...")
    with engine.begin() as conn:
        # Zorg dat de view altijd blijft bestaan, zelfs als we tabellen met CASCADE droppen
        conn.execute(text("""
        CREATE OR REPLACE VIEW public.v_productie_consumptie AS
         SELECT c.tijd,
            c.elia_total_load_mw AS consumptie_mw,
            p.elia_zon_mw,
            p.elia_wind_mw,
            COALESCE(p.vlaanderen_zon_mw, 0) AS vlaanderen_zon_mw,
            COALESCE(p.vlaanderen_wind_mw, 0) AS vlaanderen_wind_mw,
            p.elia_zon_mw + p.elia_wind_mw + COALESCE(p.vlaanderen_zon_mw, 0) + COALESCE(p.vlaanderen_wind_mw, 0) AS totale_productie_mw,
            c.elia_total_load_mw - (p.elia_zon_mw + p.elia_wind_mw + COALESCE(p.vlaanderen_zon_mw, 0) + COALESCE(p.vlaanderen_wind_mw, 0)) AS netto_vraag_mw
           FROM consumptie c
             JOIN productie p ON date_trunc('hour', c.tijd::timestamp) = date_trunc('hour', p.tijd::timestamp)
          WHERE p.elia_zon_mw IS NOT NULL AND p.elia_wind_mw IS NOT NULL;
        """))

        # Haal alle tabellen in de public schema op (sluit Airflow systeemtabellen uit)
        tables_query = text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE' 
            AND table_name != 'table_metadata'
            AND table_name NOT LIKE 'ab_%'
            AND table_name NOT LIKE 'alembic_%'
            AND table_name NOT LIKE 'celery_%'
            AND table_name NOT LIKE 'dag%'
            AND table_name NOT LIKE 'task_%'
            AND table_name NOT LIKE 'job%'
            AND table_name NOT LIKE 'log%'
            AND table_name NOT LIKE 'xcom%'
            AND table_name NOT LIKE 'connection%'
            AND table_name NOT LIKE 'sla_%'
            AND table_name NOT LIKE 'import_error%'
            AND table_name NOT LIKE 'dataset%'
            AND table_name NOT LIKE 'slot_pool%'
            AND table_name NOT LIKE 'variable%'
            AND table_name NOT LIKE 'rendered_%'
            AND table_name NOT LIKE 'trigger%'
            AND table_name NOT LIKE 'serialized_%'
            AND table_name NOT LIKE 'session%'
            AND table_name NOT LIKE 'sensor_%';
        """)
        tables = conn.execute(tables_query).fetchall()
        
        metadata_list = []
        for table in tables:
            table_name = table[0]
            # Haal column count en column details
            cols_query = text(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'public' AND table_name = '{table_name}';")
            columns = conn.execute(cols_query).fetchall()
            column_count = len(columns)
            column_details = ", ".join([f"{c[0]} ({c[1]})" for c in columns])
            
            # Haal row count
            count_query = text(f"SELECT COUNT(*) FROM {table_name};")
            row_count = conn.execute(count_query).scalar()
            
            metadata_list.append({
                "table_name": table_name,
                "row_count": row_count,
                "column_count": column_count,
                "columns": column_details
            })
            
    if metadata_list:
        df = pd.DataFrame(metadata_list)
        write_to_db(engine, df, "table_metadata", if_exists="replace")
        print("Metadata pipeline succesvol afgerond.")
    else:
        print("Geen tabellen gevonden voor metadata.")

if __name__ == "__main__":
    from db import get_engine
    run_metadata_pipeline(get_engine())
