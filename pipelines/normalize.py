"""Normaliseert de 4 eindtabellen: types + units.

Transformaties:
- productie.tijd    text -> timestamptz; kWh-kolommen / 1000 naar MW; hernoem *_kwh -> *_mw
- wind.tijdstip     text -> timestamptz
- zon.datum         text -> timestamp; drop overbodige id-kolom
- consumptie.tijd   blijft timestamp (UTC naive) — al juist

Idempotent: detecteert al-uitgevoerde stappen via information_schema.
"""

from sqlalchemy import text, inspect


def _col_types(engine, table):
    insp = inspect(engine)
    return {c["name"]: str(c["type"]).lower() for c in insp.get_columns(table)}


def _exec(conn, sql, desc):
    try:
        conn.execute(text(sql))
        print(f"    ✓ {desc}")
    except Exception as e:
        print(f"    ✗ {desc}: {e}")


def normalize_productie(engine, conn):
    cols = _col_types(engine, "productie")
    if "text" in cols.get("tijd", ""):
        _exec(conn,
              "ALTER TABLE productie ALTER COLUMN tijd TYPE timestamptz USING tijd::timestamptz",
              "productie.tijd -> timestamptz")

    # Hernoem + converteer kWh -> MW (deel door 1000)
    mapping = {
        "vlaanderen_zon_kwh": "vlaanderen_zon_mw",
        "vlaanderen_wind_kwh": "vlaanderen_wind_mw",
        "elia_zon_kwh": "elia_zon_mw",
        "elia_wind_kwh": "elia_wind_mw",
    }
    cols = _col_types(engine, "productie")
    for old, new in mapping.items():
        if old in cols:
            _exec(conn, f"UPDATE productie SET {old} = {old} / 1000.0", f"productie.{old} kWh -> MW (deel door 1000)")
            _exec(conn, f"ALTER TABLE productie RENAME COLUMN {old} TO {new}", f"productie.{old} -> {new}")


def normalize_wind(engine, conn):
    cols = _col_types(engine, "wind")
    if "text" in cols.get("tijdstip", ""):
        _exec(conn,
              "ALTER TABLE wind ALTER COLUMN tijdstip TYPE timestamptz USING tijdstip::timestamptz",
              "wind.tijdstip -> timestamptz")


def normalize_zon(engine, conn):
    cols = _col_types(engine, "zon")
    if "text" in cols.get("datum", ""):
        _exec(conn,
              "ALTER TABLE zon ALTER COLUMN datum TYPE timestamp USING datum::timestamp",
              "zon.datum -> timestamp")
    if "id" in cols:
        _exec(conn, "ALTER TABLE zon DROP COLUMN id", "zon.id drop (overbodige row-index)")


def run_normalize_pipeline(engine):
    print("\n--- Start Normalize Pipeline (types + units) ---")
    existing = set(inspect(engine).get_table_names())

    with engine.begin() as conn:
        if "productie" in existing:
            print("  productie:")
            normalize_productie(engine, conn)
        if "wind" in existing:
            print("  wind:")
            normalize_wind(engine, conn)
        if "zon" in existing:
            print("  zon:")
            normalize_zon(engine, conn)

    print("  Normalize pipeline klaar.")
