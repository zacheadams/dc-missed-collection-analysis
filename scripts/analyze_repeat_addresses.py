#!/usr/bin/env python3
"""
Compute address deduplication and distinct-day repeat failure metrics across
all 345 DC Single Member Districts (SMDs) and 8 Wards over 180 days.
Outputs data/smd_180d_address_stats.json.
"""

import json
import os
from collections import defaultdict
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def extract_polys(geom):
    gtype = geom.get("type")
    coords = geom.get("coordinates", [])
    if gtype == "Polygon":
        return coords
    elif gtype == "MultiPolygon":
        res = []
        for poly in coords:
            res.extend(poly)
        return res
    return []

def point_in_ring(x, y, ring):
    n = len(ring)
    inside = False
    p1x, p1y = ring[0]
    for i in range(n + 1):
        p2x, p2y = ring[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside

def analyze_repeat_addresses():
    smd_path = os.path.join(BASE_DIR, "data/dc_smds.geojson")
    sr_path = os.path.join(BASE_DIR, "data/dc_180d_service_requests.json")
    map_data_path = os.path.join(BASE_DIR, "data/dc_map_data_v2.json")
    output_path = os.path.join(BASE_DIR, "data/smd_180d_address_stats.json")

    with open(smd_path, "r", encoding="utf-8") as f:
        smds_geojson = json.load(f)

    with open(sr_path, "r", encoding="utf-8") as f:
        sr_data = json.load(f)

    with open(map_data_path, "r", encoding="utf-8") as f:
        v2 = json.load(f)

    ward_map = {f["properties"]["smd_id"]: f["properties"]["ward"] for f in v2["smds"]["features"]}

    smd_cache = []
    for feat in smds_geojson["features"]:
        props = feat["properties"]
        smd_id = props.get("SMD_ID")
        rings = extract_polys(feat["geometry"])
        all_lons = [p[0] for r in rings for p in r]
        all_lats = [p[1] for r in rings for p in r]
        bbox = (min(all_lons), min(all_lats), max(all_lons), max(all_lats)) if all_lons else (0,0,0,0)
        smd_cache.append({
            "smd_id": smd_id,
            "anc_id": props.get("ANC_ID"),
            "ward": ward_map.get(smd_id),
            "rings": rings,
            "bbox": bbox,
            "trash": 0,
            "recycling": 0,
            "total": 0,
            "addr_dates": defaultdict(set),
            "addr_trash_dates": defaultdict(set),
            "addr_rec_dates": defaultdict(set)
        })

    matched = 0
    unmatched = 0
    for sr in sr_data:
        attrs = sr.get("attributes", {})
        lon = attrs.get("LONGITUDE")
        lat = attrs.get("LATITUDE")
        code = attrs.get("SERVICECODE")
        adddate_ms = attrs.get("ADDDATE")
        addr = attrs.get("STREETADDRESS") or attrs.get("MARADDRESSREPOSITORYID") or f"COORD_{lat}_{lon}"
        addr = str(addr).strip().upper()

        if lon is None or lat is None or adddate_ms is None:
            unmatched += 1
            continue

        dt = datetime.fromtimestamp(adddate_ms / 1000.0)
        date_str = dt.strftime("%Y-%m-%d")

        found = False
        for smd in smd_cache:
            b = smd["bbox"]
            if b[0] <= lon <= b[2] and b[1] <= lat <= b[3]:
                for ring in smd["rings"]:
                    if point_in_ring(lon, lat, ring):
                        smd["total"] += 1
                        smd["addr_dates"][addr].add(date_str)
                        if code == "S0441":
                            smd["trash"] += 1
                            smd["addr_trash_dates"][addr].add(date_str)
                        else:
                            smd["recycling"] += 1
                            smd["addr_rec_dates"][addr].add(date_str)
                        matched += 1
                        found = True
                        break
            if found:
                break
        if not found:
            unmatched += 1

    print(f"Matched {matched} 180-day records across SMDs, {unmatched} unmatched.")

    city_addrs = defaultdict(set)
    ward_agg = defaultdict(lambda: {
        "total": 0, "trash": 0, "recycling": 0,
        "addrs": defaultdict(set), "smd_count": 0
    })

    smd_results = []
    for s in smd_cache:
        w = s["ward"]
        tot = s["total"]
        trash = s["trash"]
        rec = s["recycling"]

        unique_addrs = len(s["addr_dates"])
        repeat_addrs = sum(1 for a, dates in s["addr_dates"].items() if len(dates) >= 2)
        single_addrs = unique_addrs - repeat_addrs
        repeat_rate = round(repeat_addrs / unique_addrs * 100, 1) if unique_addrs > 0 else 0.0
        repeat_tickets = sum(len(dates) for a, dates in s["addr_dates"].items() if len(dates) >= 2)
        max_days = max([len(dates) for dates in s["addr_dates"].values()]) if s["addr_dates"] else 0

        ward_agg[w]["total"] += tot
        ward_agg[w]["trash"] += trash
        ward_agg[w]["recycling"] += rec
        ward_agg[w]["smd_count"] += 1
        for a, dates in s["addr_dates"].items():
            ward_agg[w]["addrs"][a].update(dates)
            city_addrs[a].update(dates)

        smd_results.append({
            "smd_id": s["smd_id"],
            "anc_id": s["anc_id"],
            "ward": w,
            "total": tot,
            "trash": trash,
            "recycling": rec,
            "unique_addrs": unique_addrs,
            "repeat_addrs": repeat_addrs,
            "single_addrs": single_addrs,
            "repeat_rate": repeat_rate,
            "repeat_tickets": repeat_tickets,
            "max_repeat_days": max_days
        })

    total_city_tickets = matched
    total_city_unique = len(city_addrs)
    total_city_repeat = sum(1 for a, dates in city_addrs.items() if len(dates) >= 2)
    city_repeat_rate = round(total_city_repeat / total_city_unique * 100, 1) if total_city_unique > 0 else 0.0

    payload = {
        "citywide": {
            "total_requests": total_city_tickets,
            "unique_addresses": total_city_unique,
            "repeat_addresses": total_city_repeat,
            "repeat_rate": city_repeat_rate,
            "single_addresses": total_city_unique - total_city_repeat,
            "requests_per_address": round(total_city_tickets / total_city_unique, 2) if total_city_unique > 0 else 0.0
        },
        "wards": {str(w): {
            "total": ward_agg[w]["total"],
            "trash": ward_agg[w]["trash"],
            "recycling": ward_agg[w]["recycling"],
            "unique_addresses": len(ward_agg[w]["addrs"]),
            "repeat_addresses": sum(1 for a, dates in ward_agg[w]["addrs"].items() if len(dates) >= 2),
            "repeat_rate": round(sum(1 for a, dates in ward_agg[w]["addrs"].items() if len(dates) >= 2) / len(ward_agg[w]["addrs"]) * 100, 1) if len(ward_agg[w]["addrs"]) > 0 else 0.0,
            "requests_per_address": round(ward_agg[w]["total"] / len(ward_agg[w]["addrs"]), 2) if len(ward_agg[w]["addrs"]) > 0 else 0.0
        } for w in ward_agg if w is not None},
        "smds": smd_results
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"Successfully exported address metrics to {output_path}")

if __name__ == "__main__":
    analyze_repeat_addresses()
