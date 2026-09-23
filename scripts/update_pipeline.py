#!/usr/bin/env python3
"""
Master Data Refresh & Build Pipeline for Washington, DC Missed Collection Analysis.
Executes end-to-end data ingestion, spatial calculations, metric aggregations,
and HTML compilation for all three applications:
- index.html (Central Project Hub)
- map.html (Dedicated Interactive Map Explorer)
- report.html (Unified Operational Report)
Strictly adheres to:
- No emojis across all logs and outputs
- Zero external pip dependencies
"""

import os
import sys
import subprocess
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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

def main():
    t_start = time.time()
    total_steps = 7
    print("=" * 70)
    print(f"DC Missed Collection Pipeline -- Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    skip_fetch = "--skip-fetch" in sys.argv
    full_fetch = "--full-fetch" in sys.argv

    # Step 1: Fetch 311 data
    if skip_fetch:
        print(f"\n[1/{total_steps}] Skipping 311 data fetch (--skip-fetch specified)")
    else:
        from fetch_311_data import update_service_requests
        run_step(
            1,
            total_steps,
            "Fetching 311 Missed Trash & Recycling Records (Incremental)",
            lambda: update_service_requests(full_fetch=full_fetch)
        )

    # Step 2: Update map data (180-day default and 30-day windows)
    from update_map_data import update_map_data
    run_step(2, total_steps, "Updating SMD & Ward Map Metrics (180d & 30d Windows)", update_map_data)

    # Step 3: Compute 180-day address deduplication & repeat stats
    from analyze_repeat_addresses import analyze_repeat_addresses
    run_step(3, total_steps, "Computing 180-Day SMD & Ward Address Deduplication", analyze_repeat_addresses)

    # Step 4: Compute route metrics
    from compute_route_stats import compute_route_stats
    run_step(4, total_steps, "Computing DPW Route Performance Metrics", compute_route_stats)

    # Step 5: Build report.html
    run_step(
        5,
        total_steps,
        "Compiling Unified Operational Report (report.html)",
        lambda: subprocess.check_call([sys.executable, os.path.join(BASE_DIR, 'scripts', 'build_report_page.py')])
    )

    # Step 6: Build map.html
    run_step(
        6,
        total_steps,
        "Compiling Dedicated Interactive Map (map.html)",
        lambda: subprocess.check_call([sys.executable, os.path.join(BASE_DIR, 'scripts', 'build_page.py')])
    )

    # Step 7: Build index.html
    run_step(
        7,
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
