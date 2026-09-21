#!/usr/bin/env python3
"""
Master Data Refresh & Build Pipeline for Washington, DC Missed Collection Analysis.
Executes the end-to-end data ingestion, spatial calculations, metric aggregations,
and HTML compilation steps.
"""

import os
import sys
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run_step(step_num, title, func):
    print(f"\n[{step_num}/5] {title}...")
    t0 = time.time()
    try:
        func()
        elapsed = time.time() - t0
        print(f"[{step_num}/5] Completed in {elapsed:.2f}s")
    except Exception as e:
        print(f"[{step_num}/5] Failed: {e}")
        sys.exit(1)

def main():
    t_start = time.time()
    print("=" * 70)
    print(f"DC Missed Collection Pipeline • Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    skip_fetch = "--skip-fetch" in sys.argv
    full_fetch = "--full-fetch" in sys.argv

    # Step 1: Fetch 311 data
    if skip_fetch:
        print("\n[1/5] Skipping 311 data fetch (--skip-fetch specified)")
    else:
        from fetch_311_data import update_service_requests
        run_step(
            1,
            "Fetching 311 Missed Trash & Recycling Records (Incremental)",
            lambda: update_service_requests(full_fetch=full_fetch)
        )

    # Step 2: Update 30-day map data
    from update_map_data import update_map_data
    run_step(2, "Updating 30-Day SMD & Ward Map Metrics", update_map_data)

    # Step 3: Compute 180-day address deduplication & repeat stats
    from analyze_repeat_addresses import analyze_repeat_addresses
    run_step(3, "Computing 180-Day SMD & Ward Address Deduplication", analyze_repeat_addresses)

    # Step 4: Compute route metrics and generate routes.html
    # We execute generate_route_report as a subprocess or import main
    run_step(4, "Computing DPW Route Performance & Compiling routes.html", lambda: os.system(f"python3 {os.path.join(BASE_DIR, 'scripts/generate_route_report.py')}"))

    # Step 5: Build index.html and dc_missed_collection_map.html
    run_step(5, "Compiling index.html and dc_missed_collection_map.html", lambda: os.system(f"python3 {os.path.join(BASE_DIR, 'scripts/build_page.py')}"))

    total_elapsed = time.time() - t_start
    print("\n" + "=" * 70)
    print(f"Pipeline finished successfully in {total_elapsed:.2f}s!")
    print("=" * 70)

if __name__ == "__main__":
    main()
