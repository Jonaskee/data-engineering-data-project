from db import get_engine
from pipelines.elia import run_elia_pipeline
from pipelines.energie_vlaanderen import run_vlaanderen_pipeline
from pipelines.combine_data import run_consumptie_combine
from pipelines.extra_datasets import run_extra_datasets_pipeline
from pipelines.normalize import run_normalize_pipeline
from pipelines.export_csv import export_all_tables_to_csv

if __name__ == "__main__":
    print("Test verbinding met database...")
    try:
        engine = get_engine()
        print("Verbinding OK!\n")
    except Exception as e:
        print(f"Database verbinding mislukt: {e}")
        exit(1)

    # 1. Haal ruwe bronnen op (consumptie-groep)
    run_elia_pipeline(engine)
    run_vlaanderen_pipeline(engine)

    # 2. Bouw de consumptie-tabel uit de opgehaalde bronnen
    run_consumptie_combine(engine)

    # 3. Laad de 3 CSVs van de andere groepen in productie/wind/zon
    run_extra_datasets_pipeline(engine)

    # 4. Normaliseer types en units (kWh -> MW, text -> timestamp)
    run_normalize_pipeline(engine)

    # 5. Exporteer alle tabellen naar CSV (handig voor controle)
    export_all_tables_to_csv(engine)

    print("\nAlle pipelines zijn afgerond! 4 finale tabellen: consumptie, productie, wind, zon")
