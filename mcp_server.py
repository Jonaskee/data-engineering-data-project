from mcp.server.fastmcp import FastMCP

# 1. Initialiseer de FastMCP server
mcp = FastMCP("Mijn Energie Project MCP")

# 2. Voeg simpele tools toe die de AI kan aanroepen.
# De docstrings ("""...""") worden door Claude gelezen om te begrijpen wat de tool doet.
@mcp.tool()
def get_project_status() -> str:
    """Geeft de huidige status of uitleg van het data project terug."""
    return (
        "Dit is het Energie Data Engineering Project. "
        "De Airflow pipeline verwerkt data van Elia, Energie Vlaanderen en Kaggle. "
        "Het project draait via docker-compose (Postgres, pgAdmin, Airflow, Grafana)."
    )

@mcp.tool()
def bereken_energie_conversie(waarde: float, van_eenheid: str, naar_eenheid: str) -> str:
    """
    Simpele tool om eenheden om te rekenen (bijv. kW naar MW of m/s naar km/h).
    De pipeline doet dit ook in normalize_units!
    """
    van = van_eenheid.lower()
    naar = naar_eenheid.lower()
    
    if van == "kw" and naar == "mw":
        return f"{waarde} kW is {waarde / 1000} MW"
    elif van == "mw" and naar == "kw":
        return f"{waarde} MW is {waarde * 1000} kW"
    elif van == "m/s" and naar == "km/h":
        return f"{waarde} m/s is {waarde * 3.6} km/h"
    else:
        return f"Conversie van {van_eenheid} naar {naar_eenheid} is niet ondersteund in deze educatieve tool."

if __name__ == "__main__":
    # 3. Start de server (via stdin/stdout voor lokale AI clients)
    mcp.run()
