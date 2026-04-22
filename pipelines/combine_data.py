from sqlalchemy import text, inspect


def _detect_elia_load_column(engine) -> str | None:
    """Detecteer de kolom met de totale belasting in elia_total_load."""
    insp = inspect(engine)
    if "elia_total_load" not in insp.get_table_names():
        return None
    cols = [c["name"] for c in insp.get_columns("elia_total_load")]
    for candidate in ("eliagridload", "totalload", "total_load", "load"):
        if candidate in cols:
            return candidate
    # fallback: eerste numerieke-achtige kolom die geen datum is
    for c in cols:
        if c not in ("datetime", "resolutioncode") and "forecast" not in c:
            return c
    return None


def run_consumptie_combine(engine):
    print("\n--- Start Consumptie Combinatie Pipeline ---")

    insp = inspect(engine)
    tables = insp.get_table_names()

    load_col = _detect_elia_load_column(engine)
    has_elia = load_col is not None

    if not has_elia:
        print("  Geen Elia-bron gevonden voor consumptie-tabel. Skipping.")
        return

    sql = f"""
    DROP TABLE IF EXISTS consumptie;
    CREATE TABLE consumptie AS
    SELECT DATE_TRUNC('hour', datetime::timestamp) AS tijd,
           AVG({load_col}) AS elia_total_load_mw
    FROM elia_total_load
    WHERE {load_col} IS NOT NULL
    GROUP BY 1
    ORDER BY 1 ASC;
    """

    try:
        with engine.begin() as conn:
            conn.execute(text(sql))
            row_count = conn.execute(text("SELECT COUNT(*) FROM consumptie")).scalar()
        print(f"  SUCCES: 'consumptie' tabel aangemaakt ({row_count} rijen, bron: elia_total_load).")
    except Exception as e:
        print(f"  FOUT bij het bouwen van consumptie-tabel: {e}")
