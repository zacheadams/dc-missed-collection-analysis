import json
from datetime import datetime
from collections import defaultdict

with open("/tmp/dc_smds.geojson") as f:
    smds_geojson = json.load(f)

with open("/tmp/dc_180d_sr_addresses.json") as f:
    sr_data = json.load(f)

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
        "ward": None,
        "rings": rings,
        "bbox": bbox,
        "trash": 0,
        "recycling": 0,
        "total": 0,
        "addr_dates": defaultdict(set), # addr -> set of distinct date strings
        "addr_trash_dates": defaultdict(set),
        "addr_rec_dates": defaultdict(set)
    })

with open("/tmp/dc_map_data_v2.json") as f:
    v2 = json.load(f)
ward_map = {f["properties"]["smd_id"]: f["properties"]["ward"] for f in v2["smds"]["features"]}
for s in smd_cache:
    s["ward"] = ward_map.get(s["smd_id"])

matched = 0
unmatched = 0
for sr in sr_data:
    attrs = sr["attributes"]
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

print(f"Matched {matched}, unmatched {unmatched}")

# Citywide aggregation
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
    # Address with repeat requests on DIFFERENT DAYS
    repeat_addrs = sum(1 for a, dates in s["addr_dates"].items() if len(dates) >= 2)
    single_addrs = unique_addrs - repeat_addrs
    repeat_rate = (repeat_addrs / unique_addrs * 100) if unique_addrs > 0 else 0
    
    # Total tickets from addresses that complained on >= 2 different days
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
        "repeat_rate": round(repeat_rate, 1),
        "repeat_tickets": repeat_tickets,
        "max_days_single_addr": max_days
    })

print("\n=== CITYWIDE SUMMARY (180 DAYS) ===")
total_city_tickets = matched
total_city_unique = len(city_addrs)
total_city_repeat = sum(1 for a, dates in city_addrs.items() if len(dates) >= 2)
print(f"Total Requests: {total_city_tickets}")
print(f"Unique Complaining Addresses: {total_city_unique}")
print(f"Addresses with Repeat Requests (>= 2 distinct days): {total_city_repeat} ({total_city_repeat/total_city_unique*100:.1f}%)")
print(f"Single-Incident Addresses: {total_city_unique - total_city_repeat} ({(total_city_unique - total_city_repeat)/total_city_unique*100:.1f}%)")
print(f"Citywide Spread Factor (Requests per Unique Address): {total_city_tickets/total_city_unique:.2f}")

print("\n=== WARD-BY-WARD ADDRESS & REPEAT BREAKDOWN ===")
for w in sorted(ward_agg.keys()):
    wd = ward_agg[w]
    tot = wd["total"]
    uniq = len(wd["addrs"])
    rep = sum(1 for a, dates in wd["addrs"].items() if len(dates) >= 2)
    rep_pct = rep / uniq * 100 if uniq > 0 else 0
    print(f"Ward {w}: Total Requests: {tot:4d} | Unique Addrs: {uniq:4d} | Repeat Addrs (diff days): {rep:3d} ({rep_pct:4.1f}%) | Req/Addr: {tot/uniq:.2f}")

# Top 10 by Unique Addresses (Most Addresses Skipped Over / Widespread Misses)
print("\n=== TOP 10 SMDs: MOST UNIQUE ADDRESSES SKIPPED OVER ===")
smd_results.sort(key=lambda x: x["unique_addrs"], reverse=True)
for rank, s in enumerate(smd_results[:10], 1):
    sid = s["smd_id"]
    u = s["unique_addrs"]
    t = s["total"]
    r = s["repeat_addrs"]
    rr = s["repeat_rate"]
    w = s["ward"]
    print(f"{rank:2d}. SMD {sid} (Ward {w}): {u} unique addrs | {t} total requests | {r} repeat addrs ({rr}%)")

# Top 10 by Repeat Addresses (Persistent Unresolved Issues / Chronic Failures)
print("\n=== TOP 10 SMDs: HIGHEST REPEAT ADDRESSES ON DIFFERENT DAYS (Unresolved Chronic Failures) ===")
smd_results.sort(key=lambda x: x["repeat_addrs"], reverse=True)
for rank, s in enumerate(smd_results[:10], 1):
    sid = s["smd_id"]
    r = s["repeat_addrs"]
    rr = s["repeat_rate"]
    u = s["unique_addrs"]
    t = s["total"]
    m = s["max_days_single_addr"]
    w = s["ward"]
    print(f"{rank:2d}. SMD {sid} (Ward {w}): {r} repeat addrs ({rr}%) | {u} unique addrs | {t} total reqs | Max days one addr: {m}")

# Top 10 by Repeat Rate % (Among SMDs with at least 15 requests)
print("\n=== TOP 10 SMDs: HIGHEST REPEAT RATE % (Min 15 requests) ===")
smd_qual = [s for s in smd_results if s["total"] >= 15]
smd_qual.sort(key=lambda x: x["repeat_rate"], reverse=True)
for rank, s in enumerate(smd_qual[:10], 1):
    sid = s["smd_id"]
    rr = s["repeat_rate"]
    r = s["repeat_addrs"]
    u = s["unique_addrs"]
    t = s["total"]
    w = s["ward"]
    print(f"{rank:2d}. SMD {sid} (Ward {w}): {rr}% repeat rate ({r}/{u} addrs) | {t} total reqs")

# Save detailed stats to /tmp/smd_180d_address_stats.json
with open("/tmp/smd_180d_address_stats.json", "w") as f:
    json.dump({
        "citywide": {
            "total_requests": total_city_tickets,
            "unique_addresses": total_city_unique,
            "repeat_addresses": total_city_repeat,
            "repeat_rate": round(total_city_repeat / total_city_unique * 100, 1),
            "single_addresses": total_city_unique - total_city_repeat,
            "requests_per_address": round(total_city_tickets / total_city_unique, 2)
        },
        "wards": {w: {
            "total": ward_agg[w]["total"],
            "trash": ward_agg[w]["trash"],
            "recycling": ward_agg[w]["recycling"],
            "unique_addresses": len(ward_agg[w]["addrs"]),
            "repeat_addresses": sum(1 for a, dates in ward_agg[w]["addrs"].items() if len(dates) >= 2),
            "repeat_rate": round(sum(1 for a, dates in ward_agg[w]["addrs"].items() if len(dates) >= 2) / len(ward_agg[w]["addrs"]) * 100, 1),
            "requests_per_address": round(ward_agg[w]["total"] / len(ward_agg[w]["addrs"]), 2)
        } for w in ward_agg},
        "smds": smd_results
    }, f, indent=2)

print("\nSuccessfully exported address metrics to /tmp/smd_180d_address_stats.json")
