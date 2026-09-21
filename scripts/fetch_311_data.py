#!/usr/bin/env python3
"""
Fetch 311 Missed Trash (S0441) and Missed Recycling (S0321) service requests
from the Open Data DC GIS FeatureServer with incremental fetching, retry logic,
and 180-day rolling window maintenance.
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DATA_FILE = os.path.join(BASE_DIR, "data/dc_180d_service_requests.json")

def fetch_with_retry(url, headers, max_retries=3):
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            wait_time = 2 ** attempt
            print(f"Fetch failed: {e}. Retrying in {wait_time}s...")
            time.sleep(wait_time)

def update_service_requests(output_file=DEFAULT_DATA_FILE, full_fetch=False, rolling_days=180):
    existing_records = {}
    
    if os.path.exists(output_file) and not full_fetch:
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    attrs = item.get("attributes", {})
                    oid = attrs.get("OBJECTID")
                    if oid is not None:
                        existing_records[oid] = item
            print(f"Loaded {len(existing_records)} existing records from {output_file}")
        except Exception as e:
            print(f"Could not load existing records: {e}. Proceeding with full fetch.")
            existing_records = {}

    now = datetime.now()
    if existing_records and not full_fetch:
        max_dt_ms = max(
            r["attributes"]["ADDDATE"]
            for r in existing_records.values()
            if r.get("attributes", {}).get("ADDDATE")
        )
        max_dt = datetime.fromtimestamp(max_dt_ms / 1000.0)
        # 48-hour buffer to capture status/resolution changes on recent tickets
        start_date = max_dt - timedelta(hours=48)
        mode_desc = f"Incremental query from {start_date.strftime('%Y-%m-%d %H:%M:%S')} (48h buffer)"
    else:
        start_date = now - timedelta(days=rolling_days)
        mode_desc = f"Full {rolling_days}-day query from {start_date.strftime('%Y-%m-%d 00:00:00')}"

    print(mode_desc)
    start_str = start_date.strftime("%Y-%m-%d %H:%M:%S")
    where = f"SERVICECODE IN ('S0441', 'S0321') AND ADDDATE >= timestamp '{start_str}'"
    fields = "OBJECTID,SERVICEREQUESTID,SERVICECODE,STREETADDRESS,MARADDRESSREPOSITORYID,ADDDATE,RESOLUTIONDATE,LATITUDE,LONGITUDE,WARD"

    new_count = 0
    updated_count = 0
    offset = 0
    headers = {"User-Agent": "DC-311-Missed-Collection-Pipeline/1.0"}

    while True:
        url = (
            f"https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/ServiceRequests/FeatureServer/13/query"
            f"?where={urllib.parse.quote(where)}&outFields={fields}&returnGeometry=false"
            f"&resultOffset={offset}&resultRecordCount=1000&f=json"
        )
        data = fetch_with_retry(url, headers)
        features = data.get("features", [])
        if not features:
            break

        for feat in features:
            attrs = feat.get("attributes", {})
            oid = attrs.get("OBJECTID")
            if oid is None:
                continue
            if oid in existing_records:
                updated_count += 1
            else:
                new_count += 1
            existing_records[oid] = feat

        print(f"Batch received: {len(features)} records (Offset: {offset})")
        if len(features) < 1000:
            break
        offset += 1000

    print(f"Downloaded records: {new_count} new, {updated_count} refreshed.")

    # Prune records older than rolling_days
    cutoff_ms = int((now - timedelta(days=rolling_days)).timestamp() * 1000)
    initial_total = len(existing_records)
    active_records = [
        r for r in existing_records.values()
        if r.get("attributes", {}).get("ADDDATE", 0) >= cutoff_ms
    ]
    pruned_count = initial_total - len(active_records)
    if pruned_count > 0:
        print(f"Pruned {pruned_count} records older than {rolling_days} days to maintain rolling window.")

    # Sort descending by ADDDATE
    active_records.sort(key=lambda r: r.get("attributes", {}).get("ADDDATE", 0), reverse=True)

    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(active_records, f)

    print(f"Successfully saved {len(active_records)} records to {output_file}")
    return len(active_records)

if __name__ == "__main__":
    full = "--full" in sys.argv
    update_service_requests(full_fetch=full)
