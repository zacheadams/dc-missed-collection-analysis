#!/usr/bin/env python3
"""
Recompute 180-day (default) and 30-day Single Member District (SMD) and Ward metrics
from 311 service requests, preserve DPW route overlays and precomputed area descriptions,
and update data/dc_map_data_v2.json.
"""

import json
import os
from collections import defaultdict
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WARD_COUNCILMEMBERS = {
    1: "Brianne Nadeau",
    2: "Brooke Pinto",
    3: "Matthew Frumin",
    4: "Janeese Lewis George",
    5: "Zachary Parker",
    6: "Charles Allen",
    7: "Wendell Felder",
    8: "Trayon White, Sr."
}

def is_point_in_ring(x, y, ring):
    inside = False
    n = len(ring)
    for i in range(n):
        j = (i - 1) % n
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
    return inside

def is_point_in_poly(x, y, poly_rings):
    if not is_point_in_ring(x, y, poly_rings[0]):
        return False
    for h in range(1, len(poly_rings)):
        if is_point_in_ring(x, y, poly_rings[h]):
            return False
    return True

def get_poly_rings_list(geom):
    t = geom["type"]
    coords = geom["coordinates"]
    if t == "Polygon":
        return [coords]
    elif t == "MultiPolygon":
        return coords
    return []

def get_bbox(polys):
    min_x = min_y = 1e9
    max_x = max_y = -1e9
    for poly in polys:
        for ring in poly:
            for x, y in ring:
                if x < min_x: min_x = x
                if x > max_x: max_x = x
                if y < min_y: min_y = y
                if y > max_y: max_y = y
    return (min_x, min_y, max_x, max_y)

def get_smd_ward(smd_id, anc_id):
    """
    Deterministically map DC SMDs and ANCs to their official Wards pursuant
    to the DC 2022 redistricting act (D.C. Law 24-148).
    All ANCs belong to the Ward of their first digit, with the sole exception
    of cross-ward ANC 3/4G (3/4G01-3/4G04 in Ward 4, 3/4G05-3/4G07 in Ward 3).
    """
    if anc_id == "3/4G":
        try:
            num = int(smd_id[-2:])
            return 4 if num <= 4 else 3
        except Exception:
            return 3
    return int(anc_id[0])

def compute_window_ranks(smd_index, ward_index, prefix):
    """
    Compute ranks, ANC sums, and Ward totals/shares for a given window prefix ('180d' or '30d').
    """
    tot_key = f"total_{prefix}"
    trash_key = f"trash_{prefix}"
    rec_key = f"recycling_{prefix}"
    city_rank_key = f"city_rank_{prefix}"
    anc_rank_key = f"anc_rank_{prefix}"
    anc_tot_key = f"anc_total_{prefix}"
    anc_count_key = f"anc_count_{prefix}"
    ward_share_key = f"ward_share_pct_{prefix}"

    # Citywide ranks
    smd_by_total = sorted(smd_index, key=lambda s: s[tot_key], reverse=True)
    for rank, s in enumerate(smd_by_total, 1):
        s[city_rank_key] = rank

    # ANC totals and ranks
    anc_groups = defaultdict(list)
    for s in smd_index:
        anc_groups[s["anc_id"]].append(s)

    for anc_id, smds_in_anc in anc_groups.items():
        anc_tot = sum(s[tot_key] for s in smds_in_anc)
        smds_in_anc.sort(key=lambda s: s[tot_key], reverse=True)
        for rank, s in enumerate(smds_in_anc, 1):
            s[anc_rank_key] = rank
            s[anc_tot_key] = anc_tot
            s[anc_count_key] = len(smds_in_anc)

    # Ward totals
    ward_stats = {w["ward"]: {"total": 0, "trash": 0, "recycling": 0, "smd_count": 0, "top_smd_id": None, "top_smd_total": -1} for w in ward_index}
    for s in smd_index:
        w = s["ward"]
        ward_stats[w]["total"] += s[tot_key]
        ward_stats[w]["trash"] += s[trash_key]
        ward_stats[w]["recycling"] += s[rec_key]
        ward_stats[w]["smd_count"] += 1
        if s[tot_key] > ward_stats[w]["top_smd_total"]:
            ward_stats[w]["top_smd_total"] = s[tot_key]
            ward_stats[w]["top_smd_id"] = s["smd_id"]

    # Calculate ward_share_pct
    for s in smd_index:
        w = s["ward"]
        wtot = ward_stats[w]["total"]
        s[ward_share_key] = round((s[tot_key] / wtot * 100), 1) if wtot > 0 else 0.0

    return ward_stats

def update_map_data():
    sr_path = os.path.join(BASE_DIR, "data/dc_180d_service_requests.json")
    smd_path = os.path.join(BASE_DIR, "data/dc_smds.geojson")
    ward_path = os.path.join(BASE_DIR, "data/dc_wards.geojson")
    route_areas_path = os.path.join(BASE_DIR, "data/route_areas.json")
    output_path = os.path.join(BASE_DIR, "data/dc_map_data_v2.json")

    with open(sr_path, "r", encoding="utf-8") as f:
        srs = json.load(f)

    with open(smd_path, "r", encoding="utf-8") as f:
        smd_geo = json.load(f)

    with open(ward_path, "r", encoding="utf-8") as f:
        ward_geo = json.load(f)

    with open(route_areas_path, "r", encoding="utf-8") as f:
        route_areas = json.load(f)

    # Determine date windows
    valid_dates = [
        sr["attributes"]["ADDDATE"]
        for sr in srs
        if sr.get("attributes", {}).get("ADDDATE")
    ]
    max_dt_ms = max(valid_dates)
    max_dt = datetime.fromtimestamp(max_dt_ms / 1000.0)

    cutoff_30d = max_dt - timedelta(days=30)
    cutoff_30d_ms = int(cutoff_30d.timestamp() * 1000)

    cutoff_180d = max_dt - timedelta(days=180)
    cutoff_180d_ms = int(cutoff_180d.timestamp() * 1000)

    print(f"180-day window: {cutoff_180d.strftime('%Y-%m-%d')} to {max_dt.strftime('%Y-%m-%d')}")
    print(f"30-day window:  {cutoff_30d.strftime('%Y-%m-%d')} to {max_dt.strftime('%Y-%m-%d')}")

    # Build spatial index for SMDs
    smd_index = []
    for f in smd_geo["features"]:
        props = f["properties"]
        smd_id = props.get("SMD_ID")
        anc_id = props.get("ANC_ID")
        rep_name = props.get("REP_NAME", "Vacant")
        polys = get_poly_rings_list(f["geometry"])
        bbox = get_bbox(polys)
        smd_index.append({
            "smd_id": smd_id,
            "anc_id": anc_id,
            "rep_name": rep_name,
            "geometry": f["geometry"],
            "polys": polys,
            "bbox": bbox,
            "trash_180d": 0,
            "recycling_180d": 0,
            "total_180d": 0,
            "trash_30d": 0,
            "recycling_30d": 0,
            "total_30d": 0,
            "ward": None
        })

    # Build spatial index for Wards
    ward_index = []
    for f in ward_geo["features"]:
        props = f["properties"]
        ward_num = int(props.get("WARD", props.get("NAME", 0)))
        polys = get_poly_rings_list(f["geometry"])
        bbox = get_bbox(polys)
        ward_index.append({
            "ward": ward_num,
            "geometry": f["geometry"],
            "polys": polys,
            "bbox": bbox
        })

    # Assign official Ward to each SMD pursuant to DC Law 24-148
    for smd in smd_index:
        smd["ward"] = get_smd_ward(smd["smd_id"], smd["anc_id"])

    # Match service requests to SMDs in single pass
    matched_180d = 0
    matched_30d = 0

    for sr in srs:
        attrs = sr.get("attributes", {})
        add_date = attrs.get("ADDDATE", 0)
        if add_date < cutoff_180d_ms:
            continue

        x = attrs.get("LONGITUDE")
        y = attrs.get("LATITUDE")
        code = attrs.get("SERVICECODE")
        if not x or not y:
            continue

        matched_smd = None
        for smd in smd_index:
            if smd["bbox"][0] <= x <= smd["bbox"][2] and smd["bbox"][1] <= y <= smd["bbox"][3]:
                if any(is_point_in_poly(x, y, p) for p in smd["polys"]):
                    matched_smd = smd
                    break

        if matched_smd:
            matched_180d += 1
            matched_smd["total_180d"] += 1
            if code == "S0441":
                matched_smd["trash_180d"] += 1
            elif code == "S0321":
                matched_smd["recycling_180d"] += 1

            if add_date >= cutoff_30d_ms:
                matched_30d += 1
                matched_smd["total_30d"] += 1
                if code == "S0441":
                    matched_smd["trash_30d"] += 1
                elif code == "S0321":
                    matched_smd["recycling_30d"] += 1

    print(f"Matched {matched_180d} 180-day requests and {matched_30d} 30-day requests to SMDs")

    # Compute ranks and ward stats for both windows
    ward_stats_180d = compute_window_ranks(smd_index, ward_index, "180d")
    ward_stats_30d = compute_window_ranks(smd_index, ward_index, "30d")

    # Build SMD GeoJSON feature collections with 180d as default root properties
    smd_features = []
    for s in smd_index:
        smd_features.append({
            "type": "Feature",
            "geometry": s["geometry"],
            "properties": {
                "smd_id": s["smd_id"],
                "anc_id": s["anc_id"],
                "rep_name": s["rep_name"],
                "ward": s["ward"],
                # Default (180-day) root properties for backward-compatibility
                "trash": s["trash_180d"],
                "recycling": s["recycling_180d"],
                "total": s["total_180d"],
                "city_rank": s["city_rank_180d"],
                "anc_rank": s["anc_rank_180d"],
                "anc_total": s["anc_total_180d"],
                "anc_count": s["anc_count_180d"],
                "ward_share_pct": s["ward_share_pct_180d"],
                # Explicit window metrics
                "metrics_180d": {
                    "trash": s["trash_180d"],
                    "recycling": s["recycling_180d"],
                    "total": s["total_180d"],
                    "city_rank": s["city_rank_180d"],
                    "anc_rank": s["anc_rank_180d"],
                    "anc_total": s["anc_total_180d"],
                    "anc_count": s["anc_count_180d"],
                    "ward_share_pct": s["ward_share_pct_180d"]
                },
                "metrics_30d": {
                    "trash": s["trash_30d"],
                    "recycling": s["recycling_30d"],
                    "total": s["total_30d"],
                    "city_rank": s["city_rank_30d"],
                    "anc_rank": s["anc_rank_30d"],
                    "anc_total": s["anc_total_30d"],
                    "anc_count": s["anc_count_30d"],
                    "ward_share_pct": s["ward_share_pct_30d"]
                }
            }
        })

    # Build Ward GeoJSON feature collections
    ward_features = []
    for w in sorted(ward_index, key=lambda x: x["ward"]):
        wnum = w["ward"]
        st180 = ward_stats_180d[wnum]
        st30 = ward_stats_30d[wnum]
        ward_features.append({
            "type": "Feature",
            "geometry": w["geometry"],
            "properties": {
                "ward": wnum,
                "name": f"Ward {wnum}",
                "councilmember": WARD_COUNCILMEMBERS.get(wnum, "DC Council"),
                # Default (180-day) root properties
                "total": st180["total"],
                "trash": st180["trash"],
                "recycling": st180["recycling"],
                "smd_count": st180["smd_count"],
                "top_smd_id": st180["top_smd_id"],
                "top_smd_total": st180["top_smd_total"],
                # Explicit window metrics
                "metrics_180d": {
                    "total": st180["total"],
                    "trash": st180["trash"],
                    "recycling": st180["recycling"],
                    "smd_count": st180["smd_count"],
                    "top_smd_id": st180["top_smd_id"],
                    "top_smd_total": st180["top_smd_total"]
                },
                "metrics_30d": {
                    "total": st30["total"],
                    "trash": st30["trash"],
                    "recycling": st30["recycling"],
                    "smd_count": st30["smd_count"],
                    "top_smd_id": st30["top_smd_id"],
                    "top_smd_total": st30["top_smd_total"]
                }
            }
        })

    # Existing map data for routes preservation
    with open(output_path, "r", encoding="utf-8") as f:
        old_map_data = json.load(f)

    trash_routes = old_map_data.get("trash_routes", {"type": "FeatureCollection", "features": []})
    recycle_routes = old_map_data.get("recycle_routes", {"type": "FeatureCollection", "features": []})

    # Ensure route area descriptions are up-to-date
    for feat in trash_routes.get("features", []):
        rid = feat.get("properties", {}).get("route_area")
        if rid and rid in route_areas.get("trash_routes", {}):
            ra = route_areas["trash_routes"][rid]
            feat["properties"]["ward"] = ra["ward"]
            feat["properties"]["neighborhoods"] = ra["neighborhoods"]
            feat["properties"]["ancs"] = ra["ancs"]
            feat["properties"]["area_desc"] = ra["area_desc"]

    for feat in recycle_routes.get("features", []):
        rid = feat.get("properties", {}).get("route")
        if rid and rid in route_areas.get("recycle_routes", {}):
            ra = route_areas["recycle_routes"][rid]
            feat["properties"]["ward"] = ra["ward"]
            feat["properties"]["neighborhoods"] = ra["neighborhoods"]
            feat["properties"]["ancs"] = ra["ancs"]
            feat["properties"]["area_desc"] = ra["area_desc"]

    date_range_180d = f"{cutoff_180d.strftime('%Y-%m-%d')} to {max_dt.strftime('%Y-%m-%d')}"
    date_range_30d = f"{cutoff_30d.strftime('%Y-%m-%d')} to {max_dt.strftime('%Y-%m-%d')}"

    metadata = {
        "title": "DC Trash and Recycling Missed Collection Map",
        "default_period": "180d",
        "date_range": date_range_180d,
        "date_range_180d": date_range_180d,
        "date_range_30d": date_range_30d,
        "total_city_tickets": matched_180d,
        "total_city_tickets_180d": matched_180d,
        "total_city_tickets_30d": matched_30d,
        "total_smds": len(smd_features),
        "max_tickets_180d": max(s["total_180d"] for s in smd_index) if smd_index else 0,
        "max_tickets_30d": max(s["total_30d"] for s in smd_index) if smd_index else 0,
        "max_tickets": max(s["total_180d"] for s in smd_index) if smd_index else 0,
        "avg_tickets_180d": round(matched_180d / len(smd_features), 1) if smd_features else 0.0,
        "avg_tickets_30d": round(matched_30d / len(smd_features), 1) if smd_features else 0.0,
        "avg_tickets": round(matched_180d / len(smd_features), 1) if smd_features else 0.0
    }

    final_payload = {
        "metadata": metadata,
        "smds": {"type": "FeatureCollection", "features": smd_features},
        "trash_routes": trash_routes,
        "recycle_routes": recycle_routes,
        "wards": {"type": "FeatureCollection", "features": ward_features}
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_payload, f)

    print(f"Successfully updated {output_path} with 180-day and 30-day metrics.")
    print(f"180-day tickets: {matched_180d}, 30-day tickets: {matched_30d}")

if __name__ == "__main__":
    update_map_data()
