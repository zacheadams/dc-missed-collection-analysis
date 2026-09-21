#!/usr/bin/env python3
"""
Recompute 30-day Single Member District (SMD) and Ward metrics from 311 service requests,
preserve DPW route overlays and precomputed area descriptions, and update data/dc_map_data_v2.json.
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

    # Filter 30-day requests
    valid_dates = [
        sr["attributes"]["ADDDATE"]
        for sr in srs
        if sr.get("attributes", {}).get("ADDDATE")
    ]
    max_dt_ms = max(valid_dates)
    max_dt = datetime.fromtimestamp(max_dt_ms / 1000.0)
    cutoff_dt = max_dt - timedelta(days=30)
    cutoff_ms = int(cutoff_dt.timestamp() * 1000)

    srs_30d = [
        sr for sr in srs
        if sr.get("attributes", {}).get("ADDDATE", 0) >= cutoff_ms
    ]
    print(f"Analyzing 30-day window: {cutoff_dt.strftime('%Y-%m-%d')} to {max_dt.strftime('%Y-%m-%d')} ({len(srs_30d)} requests)")

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
            "trash": 0,
            "recycling": 0,
            "total": 0,
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
            "bbox": bbox,
            "trash": 0,
            "recycling": 0,
            "total": 0
        })

    # Assign Ward to SMDs by checking centroid/first polygon vertex against Wards
    for smd in smd_index:
        bx1, by1, bx2, by2 = smd["bbox"]
        cx = (bx1 + bx2) / 2.0
        cy = (by1 + by2) / 2.0
        assigned_ward = None
        for w in ward_index:
            if w["bbox"][0] <= cx <= w["bbox"][2] and w["bbox"][1] <= cy <= w["bbox"][3]:
                if any(is_point_in_poly(cx, cy, wp) for wp in w["polys"]):
                    assigned_ward = w["ward"]
                    break
        if assigned_ward is None:
            # Fallback to ANC first character
            try:
                assigned_ward = int(smd["anc_id"][0])
            except Exception:
                assigned_ward = 1
        smd["ward"] = assigned_ward

    # Match 30-day tickets to SMDs
    matched_count = 0
    for sr in srs_30d:
        attrs = sr.get("attributes", {})
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
            matched_count += 1
            matched_smd["total"] += 1
            if code == "S0441":
                matched_smd["trash"] += 1
            elif code == "S0321":
                matched_smd["recycling"] += 1

    print(f"Matched {matched_count} of {len(srs_30d)} 30-day service requests to SMDs")

    # Citywide ranks
    smd_by_total = sorted(smd_index, key=lambda s: s["total"], reverse=True)
    for rank, s in enumerate(smd_by_total, 1):
        s["city_rank"] = rank

    # ANC totals and ranks
    anc_groups = defaultdict(list)
    for s in smd_index:
        anc_groups[s["anc_id"]].append(s)

    for anc_id, smds_in_anc in anc_groups.items():
        anc_tot = sum(s["total"] for s in smds_in_anc)
        smds_in_anc.sort(key=lambda s: s["total"], reverse=True)
        for rank, s in enumerate(smds_in_anc, 1):
            s["anc_rank"] = rank
            s["anc_total"] = anc_tot
            s["anc_count"] = len(smds_in_anc)

    # Ward totals
    ward_stats = {w["ward"]: {"total": 0, "trash": 0, "recycling": 0, "smd_count": 0, "top_smd_id": None, "top_smd_total": -1} for w in ward_index}
    for s in smd_index:
        w = s["ward"]
        ward_stats[w]["total"] += s["total"]
        ward_stats[w]["trash"] += s["trash"]
        ward_stats[w]["recycling"] += s["recycling"]
        ward_stats[w]["smd_count"] += 1
        if s["total"] > ward_stats[w]["top_smd_total"]:
            ward_stats[w]["top_smd_total"] = s["total"]
            ward_stats[w]["top_smd_id"] = s["smd_id"]

    # Calculate ward_share_pct
    for s in smd_index:
        w = s["ward"]
        wtot = ward_stats[w]["total"]
        s["ward_share_pct"] = round((s["total"] / wtot * 100), 1) if wtot > 0 else 0.0

    # Build GeoJSON feature collections
    smd_features = []
    for s in smd_index:
        smd_features.append({
            "type": "Feature",
            "geometry": s["geometry"],
            "properties": {
                "smd_id": s["smd_id"],
                "anc_id": s["anc_id"],
                "rep_name": s["rep_name"],
                "trash": s["trash"],
                "recycling": s["recycling"],
                "total": s["total"],
                "city_rank": s["city_rank"],
                "anc_rank": s["anc_rank"],
                "anc_total": s["anc_total"],
                "anc_count": s["anc_count"],
                "ward": s["ward"],
                "ward_share_pct": s["ward_share_pct"]
            }
        })

    ward_features = []
    for w in sorted(ward_index, key=lambda x: x["ward"]):
        wnum = w["ward"]
        st = ward_stats[wnum]
        ward_features.append({
            "type": "Feature",
            "geometry": w["geometry"],
            "properties": {
                "ward": wnum,
                "name": f"Ward {wnum}",
                "councilmember": WARD_COUNCILMEMBERS.get(wnum, "DC Council"),
                "total": st["total"],
                "trash": st["trash"],
                "recycling": st["recycling"],
                "smd_count": st["smd_count"],
                "top_smd_id": st["top_smd_id"],
                "top_smd_total": st["top_smd_total"]
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

    metadata = {
        "title": "DC Trash and Recycling Missed Collection Map (Last 30 Days)",
        "date_range": f"{cutoff_dt.strftime('%Y-%m-%d')} to {max_dt.strftime('%Y-%m-%d')}",
        "total_city_tickets": matched_count,
        "total_smds": len(smd_features),
        "max_tickets": max(s["total"] for s in smd_index) if smd_index else 0,
        "avg_tickets": round(matched_count / len(smd_features), 1) if smd_features else 0.0
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

    print(f"Successfully updated {output_path} with 30-day metrics ({metadata['date_range']})")

if __name__ == "__main__":
    update_map_data()
