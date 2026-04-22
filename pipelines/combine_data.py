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
    has_ev_solar = "vlaanderen_energie_solar" in tables
    has_ev_wind = "vlaanderen_energie_wind" in tables

    if not (has_elia or has_ev_solar or has_ev_wind):
        print("  Geen bronnen gevonden voor consumptie-tabel. Skipping.")
        return

    ctes = []
    selects = ["h.tijd"]
    joins = []

    if has_elia:
        ctes.append(f"""elia AS (
            SELECT DATE_TRUNC('hour', datetime::timestamp) AS tijd,
                   AVG({load_col}) AS elia_total_load_mw
            FROM elia_total_load
            WHERE {load_col} IS NOT NULL
            GROUP BY 1
        )""")
        selects.append("e.elia_total_load_mw")
        joins.append("LEFT JOIN elia e USING(tijd)")

    if has_ev_solar:
        ctes.append("""ev_solar AS (
            SELECT DATE_TRUNC('hour', datumtijd::timestamp) AS tijd,
                   SUM(vermogen_mw) AS ev_zon_mw
            FROM vlaanderen_energie_solar
            GROUP BY 1
        )""")
        selects.append("s.ev_zon_mw")
        joins.append("LEFT JOIN ev_solar s USING(tijd)")

    if has_ev_wind:
        ctes.append("""ev_wind AS (
            SELECT DATE_TRUNC('hour', datumtijd::timestamp) AS tijd,
                   SUM(vermogen_mw) AS ev_wind_mw
            FROM vlaanderen_energie_wind
            GROUP BY 1
        )""")
        selects.append("w.ev_wind_mw")
        joins.append("LEFT JOIN ev_wind w USING(tijd)")

    union_parts = []
    if has_elia:
        union_parts.append("SELECT tijd FROM elia")
    if has_ev_solar:
        union_parts.append("SELECT tijd FROM ev_solar")
    if has_ev_wind:
        union_parts.append("SELECT tijd FROM ev_wind")
    ctes.append("all_hours AS (\n    " + "\n    UNION ".join(union_parts) + "\n)")

    sql = f"""
    DROP TABLE IF EXISTS consumptie;
    CREATE TABLE consumptie AS
    WITH {", ".join(ctes)}
    SELECT {", ".join(selects)}
    FROM all_hours h
    {chr(10).join(joins)}
    ORDER BY h.tijd ASC;
    """

    try:
        with engine.begin() as conn:
            conn.execute(text(sql))
        print(f"  SUCCES: 'consumptie' tabel aangemaakt (bronnen: "
              f"{'elia ' if has_elia else ''}"
              f"{'ev_solar ' if has_ev_solar else ''}"
              f"{'ev_wind' if has_ev_wind else ''}).")
    except Exception as e:
        print(f"  FOUT bij het bouwen van consumptie-tabel: {e}")
