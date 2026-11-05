#!/usr/bin/env python3
"""
Fetch Washington, DC historical weather observations (temperature and precipitation)
for the FOIA attendance analysis period (2026-04-01 to 2026-09-30).
Queries Open-Meteo Historical Weather Archive API (NOAA/ERA5 reanalysis).

Strict repository standards:
- Strictly zero emojis across code, logs, and output strings
- Zero third-party pip dependencies (standard library only)
"""

import json
import os
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "data")
OUT_FILE = os.path.join(OUT_DIR, "dc_weather_2026.json")

# Washington, DC centroid: 38.8895 N, -77.0353 W
LATITUDE = 38.8895
LONGITUDE = -77.0353
START_DATE = "2026-04-01"
END_DATE = "2026-09-30"

def fetch_weather():
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "daily": "temperature_2m_max,temperature_2m_min,temperature_2m_mean,precipitation_sum,precipitation_hours",
        "temperature_unit": "fahrenheit",
        "precipitation_unit": "inch",
        "timezone": "America/New_York",
    }
    query_str = urllib.parse.urlencode(params)
    url = f"https://archive-api.open-meteo.com/v1/archive?{query_str}"
    headers = {"User-Agent": "DC-Missed-Collection-Analysis/1.0"}

    print(f"Fetching DC weather data from {START_DATE} to {END_DATE}...")
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    t_max = daily.get("temperature_2m_max", [])
    t_min = daily.get("temperature_2m_min", [])
    t_mean = daily.get("temperature_2m_mean", [])
    precip = daily.get("precipitation_sum", [])
    precip_hrs = daily.get("precipitation_hours", [])

    records = {}
    for i, dt in enumerate(dates):
        records[dt] = {
            "date": dt,
            "temp_max_f": t_max[i] if i < len(t_max) else None,
            "temp_min_f": t_min[i] if i < len(t_min) else None,
            "temp_mean_f": t_mean[i] if i < len(t_mean) else None,
            "precipitation_in": precip[i] if i < len(precip) else 0.0,
            "precipitation_hours": precip_hrs[i] if i < len(precip_hrs) else 0.0,
            "is_extreme_heat_90": bool(t_max[i] and t_max[i] >= 90.0),
            "is_extreme_heat_95": bool(t_max[i] and t_max[i] >= 95.0),
            "is_heavy_rain": bool(precip[i] and precip[i] >= 0.5),
        }

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "metadata": {
                "location": "Washington, DC",
                "latitude": LATITUDE,
                "longitude": LONGITUDE,
                "start_date": START_DATE,
                "end_date": END_DATE,
                "days_count": len(records),
                "source": "Open-Meteo Historical Weather Archive API",
            },
            "daily": records
        }, f, indent=2)

    print(f"Successfully saved {len(records)} daily weather records to {OUT_FILE}")
    return records

if __name__ == "__main__":
    fetch_weather()
