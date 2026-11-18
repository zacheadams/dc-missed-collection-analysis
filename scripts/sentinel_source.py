#!/usr/bin/env python3
"""
Shared data loader for reading 311 service requests and DC boundary GeoJSONs
from the sibling dc-311-sentinel repository and its DuckDB warehouse.

Strictly adheres to:
- Strictly zero emojis across code, logs, and outputs
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_START_DATE = "2026-04-01"


def get_sentinel_dir():
    """Return the path to the dc-311-sentinel repository."""
    env_dir = os.environ.get("SENTINEL_DIR") or os.environ.get("DC_311_SENTINEL_DIR")
    sentinel_dir = os.path.abspath(env_dir) if env_dir else os.path.join(os.path.dirname(BASE_DIR), "dc-311-sentinel")
    if not os.path.isdir(sentinel_dir):
        raise FileNotFoundError(
            f"Missing dc-311-sentinel directory at '{sentinel_dir}'. "
            "Clone it alongside dc-missed-collections or set SENTINEL_DIR."
        )
    return sentinel_dir


def get_sentinel_python():
    """Return dc-311-sentinel virtualenv python executable if present."""
    try:
        sentinel_dir = get_sentinel_dir()
    except FileNotFoundError:
        return None
    venv_py = os.path.join(sentinel_dir, ".venv", "bin", "python")
    if os.path.isfile(venv_py) and os.access(venv_py, os.X_OK):
        return venv_py
    return None


def ensure_duckdb_interpreter():
    """
    Ensure duckdb is importable; if not, transparently re-exec using
    dc-311-sentinel's virtualenv python when available.
    """
    try:
        import duckdb  # noqa: F401
        return
    except ModuleNotFoundError:
        if os.environ.get("_SENTINEL_REEXEC") != "1":
            sentinel_py = get_sentinel_python()
            if sentinel_py and os.path.abspath(sys.executable) != os.path.abspath(sentinel_py):
                os.environ["_SENTINEL_REEXEC"] = "1"
                os.execv(sentinel_py, [sentinel_py] + sys.argv)
        raise ModuleNotFoundError(
            "Missing 'duckdb' package. Install dependencies with 'pip install -r requirements.txt' "
            "or run via '../dc-311-sentinel/.venv/bin/python'."
        )


def get_warehouse_path():
    """Return path to dc-311-sentinel/data/warehouse.duckdb."""
    path = os.path.join(get_sentinel_dir(), "data", "warehouse.duckdb")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Missing shared DuckDB warehouse at '{path}'. "
            "Run dc-311-sentinel/scripts/update_pipeline.py first."
        )
    return path


def get_boundary_path(filename):
    """Return path to a shared boundary GeoJSON inside dc-311-sentinel/data/."""
    path = os.path.join(get_sentinel_dir(), "data", filename)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Missing shared boundary file '{path}'. "
            "Ensure dc-311-sentinel/data/ contains the boundary GeoJSON files."
        )
    return path


def get_warehouse_summary(start_date=DEFAULT_START_DATE):
    """Return (row_count, min_date, max_date) for missed collection codes in DuckDB."""
    ensure_duckdb_interpreter()
    import duckdb

    with duckdb.connect(get_warehouse_path(), read_only=True) as con:
        row = con.execute(
            """
            SELECT
                COUNT(*),
                MIN(add_date),
                MAX(add_date)
            FROM requests
            WHERE service_code IN ('S0441', 'S0321')
              AND add_date >= CAST(? AS DATE)
            """,
            [start_date],
        ).fetchone()
    return int(row[0]), str(row[1]) if row[1] else None, str(row[2]) if row[2] else None


def load_missed_collection_requests(start_date=DEFAULT_START_DATE):
    """
    Query S0441 (Trash) and S0321 (Recycling) service requests from
    dc-311-sentinel's DuckDB warehouse in ArcGIS feature-attribute format.
    """
    ensure_duckdb_interpreter()
    import duckdb

    warehouse_path = get_warehouse_path()
    with duckdb.connect(warehouse_path, read_only=True) as con:
        rows = con.execute(
            """
            SELECT
                object_id,
                service_request_id,
                service_code,
                street_address,
                mar_id,
                CAST(epoch_ms(add_ts AT TIME ZONE 'America/New_York') AS BIGINT) AS add_ms,
                CASE WHEN resolution_ts IS NOT NULL
                     THEN CAST(epoch_ms(resolution_ts AT TIME ZONE 'America/New_York') AS BIGINT)
                     ELSE NULL END AS res_ms,
                latitude,
                longitude,
                ward
            FROM requests
            WHERE service_code IN ('S0441', 'S0321')
              AND add_date >= CAST(? AS DATE)
            ORDER BY add_ts DESC
            """,
            [start_date],
        ).fetchall()

    records = []
    for oid, srid, scode, addr, mar_id, add_ms, res_ms, lat, lon, ward in rows:
        records.append({
            "attributes": {
                "OBJECTID": oid,
                "SERVICEREQUESTID": srid,
                "SERVICECODE": scode,
                "STREETADDRESS": addr,
                "MARADDRESSREPOSITORYID": mar_id,
                "ADDDATE": add_ms,
                "RESOLUTIONDATE": res_ms,
                "LATITUDE": lat,
                "LONGITUDE": lon,
                "WARD": f"Ward {ward}" if ward else None,
            }
        })
    return records
