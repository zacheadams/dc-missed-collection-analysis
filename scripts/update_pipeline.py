#!/usr/bin/env python3
"""
Master Data Refresh & Build Pipeline for Washington, DC Missed Collection Analysis.
Reads 311 service requests and DC boundary GeoJSONs from the sibling
dc-311-sentinel repository and its DuckDB warehouse, then executes spatial
calculations, metric aggregations, and HTML compilation for all applications:
- index.html (Central Project Hub)
- map.html (Dedicated Interactive Map Explorer)
- report.html (Unified Operational Report)
- tables.html (Tables and Graphs)

Usage:
  python3 scripts/update_pipeline.py                      # Build from dc-311-sentinel warehouse
  python3 scripts/update_pipeline.py --refresh-sentinel   # Refresh dc-311-sentinel first, then build
  python3 scripts/update_pipeline.py --skip-route-lines   # Skip regenerating DPW street route lines

Strictly adheres to:
- No emojis across all logs and outputs
"""

import os
import subprocess
import sys
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))

from sentinel_source import (
    ensure_duckdb_interpreter,
    get_sentinel_dir,
    get_sentinel_python,
    get_warehouse_summary,
)


def run_step(step_num, total_steps, title, func):
    print(f"\n[{step_num}/{total_steps}] {title}...")
    t0 = time.time()
    try:
        func()
        elapsed = time.time() - t0
        print(f"[{step_num}/{total_steps}] Completed in {elapsed:.2f}s")
    except Exception as e:
        print(f"[{step_num}/{total_steps}] Failed: {e}")
        sys.exit(1)


def refresh_sentinel_pipeline():
    sentinel_dir = get_sentinel_dir()
    sentinel_py = get_sentinel_python() or sys.executable
    sentinel_script = os.path.join(sentinel_dir, "scripts", "update_pipeline.py")
    subprocess.check_call([sentinel_py, sentinel_script], cwd=sentinel_dir)


def verify_sentinel_warehouse():
    count, min_date, max_date = get_warehouse_summary()
    print(
        f"Verified dc-311-sentinel warehouse: {count:,} missed collection records "
        f"({min_date} to {max_date})"
    )


def main():
    ensure_duckdb_interpreter()

    t_start = time.time()
    total_steps = 10
    print("=" * 70)
    print(f"DC Missed Collection Pipeline -- Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    refresh_sentinel = "--refresh-sentinel" in sys.argv
    skip_route_lines = "--skip-route-lines" in sys.argv

    # Step 1: Verify or refresh shared dc-311-sentinel warehouse
    if refresh_sentinel:
        run_step(
            1,
            total_steps,
            "Refreshing Shared dc-311-sentinel Data & Warehouse",
            refresh_sentinel_pipeline,
        )
    else:
        run_step(
            1,
            total_steps,
            "Verifying Shared dc-311-sentinel DuckDB Warehouse",
            verify_sentinel_warehouse,
        )

    # Step 2: Compute 180-day address deduplication & repeat stats
    from analyze_repeat_addresses import analyze_repeat_addresses
    run_step(2, total_steps, "Computing 180-Day SMD & Ward Address Deduplication", analyze_repeat_addresses)

    # Step 3: Compute route areas, ANCs, and neighborhoods (catchments)
    from compute_route_areas import compute_route_areas
    run_step(3, total_steps, "Computing DPW Catchment Areas, ANCs & Neighborhoods", compute_route_areas)

    # Step 4: Compute route metrics
    from compute_route_stats import compute_route_stats
    run_step(4, total_steps, "Computing DPW Route Performance Metrics", compute_route_stats)

    # Step 5: Generate DPW route line geometries from collection points (with fresh stats and areas)
    if skip_route_lines:
        print(f"\n[5/{total_steps}] Skipping DPW route line generation (--skip-route-lines specified)")
    else:
        from generate_route_lines import generate_route_lines
        run_step(5, total_steps, "Generating DPW Route Line Geometries from Collection Points", generate_route_lines)

    # Step 6: Update map data (180-day default and 30-day windows)
    from update_map_data import update_map_data
    run_step(6, total_steps, "Updating SMD & Ward Map Metrics and Bundling Map Data", update_map_data)

    # Step 7: Build tables.html
    run_step(
        7,
        total_steps,
        "Compiling Tables and Graphs (tables.html)",
        lambda: subprocess.check_call([sys.executable, os.path.join(BASE_DIR, 'scripts', 'build_tables_page.py')])
    )

    # Step 8: Build report.html
    run_step(
        8,
        total_steps,
        "Compiling Unified Operational Report (report.html)",
        lambda: subprocess.check_call([sys.executable, os.path.join(BASE_DIR, 'scripts', 'build_report_page.py')])
    )

    # Step 9: Build map.html
    run_step(
        9,
        total_steps,
        "Compiling Dedicated Interactive Map (map.html)",
        lambda: subprocess.check_call([sys.executable, os.path.join(BASE_DIR, 'scripts', 'build_page.py')])
    )

    # Step 10: Build index.html
    run_step(
        10,
        total_steps,
        "Compiling Central Project Hub (index.html)",
        lambda: subprocess.check_call([sys.executable, os.path.join(BASE_DIR, 'scripts', 'build_index_page.py')])
    )

    total_elapsed = time.time() - t_start
    print("\n" + "=" * 70)
    print(f"Pipeline finished successfully in {total_elapsed:.2f}s!")
    print("=" * 70)


if __name__ == "__main__":
    main()
