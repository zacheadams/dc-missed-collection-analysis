#!/usr/bin/env python3
"""
Fetch 311 Missed Trash (S0441) and Missed Recycling (S0321) service requests
from the DC GIS FeatureServer.
"""

import urllib.parse
import urllib.request
import json
from datetime import datetime, timedelta
import sys

def fetch_service_requests(days=180, output_file="data/dc_311_requests.json"):
    now = datetime.now()
    start_date = now - timedelta(days=days)
    start_str = start_date.strftime("%Y-%m-%d 00:00:00")
    print(f"Fetching {days} days of 311 data from: {start_str}")

    where = f"SERVICECODE IN ('S0441', 'S0321') AND ADDDATE >= timestamp '{start_str}'"
    fields = "OBJECTID,SERVICEREQUESTID,SERVICECODE,STREETADDRESS,MARADDRESSREPOSITORYID,ADDDATE,RESOLUTIONDATE,LATITUDE,LONGITUDE,WARD"

    all_sr = []
    offset = 0
    while True:
        url = (
            f"https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/ServiceRequests/FeatureServer/13/query"
            f"?where={urllib.parse.quote(where)}&outFields={fields}&returnGeometry=false"
            f"&resultOffset={offset}&resultRecordCount=1000&f=json"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "DC-311-Analysis-Script"})
        with urllib.request.urlopen(req) as resp:
            data = json.load(resp)
        features = data.get("features", [])
        if not features:
            break
        all_sr.extend(features)
        print(f"Fetched {len(features)} records (Total: {len(all_sr)})")
        if len(features) < 1000:
            break
        offset += 1000

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_sr, f)
    print(f"Successfully saved {len(all_sr)} records to {output_file}")

if __name__ == "__main__":
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 180
    fetch_service_requests(days)
