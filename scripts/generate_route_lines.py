#!/usr/bin/env python3
"""
Generates street-level DPW route line geometries from DC Open Data
Trash and Recycling Collection Points GIS data:
https://opendata.dc.gov/datasets/110d1c51124b4154aab5ca64445afdb0_2/explore

Produces:
- data/dc_trash_routes_lines.geojson
- data/dc_recycle_routes_lines.geojson

Strict repository standards:
- Strictly zero emojis across code, logs, and output strings
- Zero third-party pip dependencies (standard library only)
- High contrast, lo-fi styling metadata
"""

import os
import sys
import json
import re
import math
import time
import urllib.request
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

COLLECTION_POINTS_URL = (
    "https://opendata.arcgis.com/api/v3/datasets/110d1c51124b4154aab5ca64445afdb0_2"
    "/downloads/data?format=geojson&spatialRefId=4326&where=1%3D1"
)

LOCAL_POINTS_PATH = os.path.join(DATA_DIR, 'dc_collection_points.geojson')
SCRATCH_POINTS_PATH = os.path.join(
    os.path.dirname(BASE_DIR),
    '.gemini/antigravity-cli/brain/82b706a0-f62c-4d3a-8964-31ead6cff2d3/scratch/collection_points.geojson'
)

def dist_m(p1, p2):
    """Euclidean distance in meters between two [lon, lat] coordinates."""
    dx = (p2[0] - p1[0]) * 40000000 * math.cos(math.radians(p1[1])) / 360.0
    dy = (p2[1] - p1[1]) * 40000000 / 360.0
    return math.hypot(dx, dy)

def point_line_dist(pt, l1, l2):
    """Perpendicular distance in meters from point pt to line segment l1-l2."""
    x0, y0 = pt
    x1, y1 = l1
    x2, y2 = l2
    d = dist_m(l1, l2)
    if d == 0:
        return dist_m(pt, l1)
    cos_lat = math.cos(math.radians(y1))
    dx = (x2 - x1) * 40000000 * cos_lat / 360.0
    dy = (y2 - y1) * 40000000 / 360.0
    px = (x0 - x1) * 40000000 * cos_lat / 360.0
    py = (y0 - y1) * 40000000 / 360.0
    return abs(dx * py - dy * px) / math.hypot(dx, dy)

def rdp_simplify(pts, tol_m=2.0):
    """Ramer-Douglas-Peucker line simplification with tolerance in meters."""
    if len(pts) <= 2:
        return pts
    dmax = 0.0
    index = 0
    for i in range(1, len(pts) - 1):
        d = point_line_dist(pts[i], pts[0], pts[-1])
        if d > dmax:
            dmax = d
            index = i
    if dmax > tol_m:
        rec1 = rdp_simplify(pts[:index + 1], tol_m)
        rec2 = rdp_simplify(pts[index:], tol_m)
        return rec1[:-1] + rec2
    else:
        return [pts[0], pts[-1]]

def parse_address(addr):
    """Extract street name, 100-block, parity, and house number."""
    m = re.match(r'^(\d+)', addr or '')
    num = int(m.group(1)) if m else 0
    parity = num % 2
    block = (num // 100) * 100
    parts = (addr or '').split()
    st_parts = [p for p in parts if not p.isdigit() and p not in ['REAR', '1/2']]
    st_name = ' '.join(st_parts)
    return st_name, block, parity, num

def get_collection_points():
    """Load or download DPW collection points GeoJSON."""
    if os.path.exists(LOCAL_POINTS_PATH):
        print(f"Loading collection points from {LOCAL_POINTS_PATH}...")
        with open(LOCAL_POINTS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    elif os.path.exists(SCRATCH_POINTS_PATH):
        print(f"Loading collection points from cache {SCRATCH_POINTS_PATH}...")
        with open(SCRATCH_POINTS_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Cache to data directory
        try:
            with open(LOCAL_POINTS_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f)
        except Exception:
            pass
        return data
    else:
        print("Downloading collection points from Open Data DC...")
        req = urllib.request.Request(COLLECTION_POINTS_URL, headers={'User-Agent': 'DCMissedCollectionAnalysis/1.0'})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        with open(LOCAL_POINTS_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        return data

def build_route_lines(data, route_key, stream_name, stats_lookup, areas_lookup):
    """
    Construct MultiLineString features for each route with full operational properties.
    """
    routes = defaultdict(list)
    route_meta = {}

    for f in data.get('features', []):
        p = f.get('properties', {})
        r = p.get(route_key)
        if not r or str(r).strip() in ['', 'NA', 'None']:
            continue
        r_str = str(r).strip()
        routes[r_str].append(f)
        if r_str not in route_meta:
            route_meta[r_str] = {
                'route': r_str,
                'stream': stream_name,
                'day': p.get('DAY') or 'Scheduled',
                'ward': p.get('WARD') or 'Citywide'
            }

    features = []

    for r_id, pts_list in sorted(routes.items()):
        # Group points by street, 100-block, parity, and service location
        groups = defaultdict(list)
        all_lons = []
        all_lats = []

        for f in pts_list:
            addr = f['properties'].get('ADDRESS', '')
            st_name, block, parity, num = parse_address(addr)
            loc = f['properties'].get('SERVICE_LOCATION', 'Street')
            c = f['geometry']['coordinates']
            all_lons.append(c[0])
            all_lats.append(c[1])
            groups[(st_name, block, parity, loc)].append((num, c, addr))

        raw_lines = []
        for (st_name, block, parity, loc), block_pts in groups.items():
            if len(block_pts) == 1:
                pt = block_pts[0][1]
                # Single pickup point: create small 8-meter corridor segment along latitude
                raw_lines.append([
                    [round(pt[0] - 0.00004, 5), round(pt[1], 5)],
                    [round(pt[0] + 0.00004, 5), round(pt[1], 5)]
                ])
            else:
                block_pts.sort(key=lambda x: x[0])
                cur_seg = [block_pts[0][1]]
                for i in range(len(block_pts) - 1):
                    d = dist_m(block_pts[i][1], block_pts[i + 1][1])
                    if d > 80.0:
                        if len(cur_seg) >= 2:
                            raw_lines.append(rdp_simplify(cur_seg, 2.0))
                        elif len(cur_seg) == 1:
                            p = cur_seg[0]
                            raw_lines.append([
                                [round(p[0] - 0.00004, 5), round(p[1], 5)],
                                [round(p[0] + 0.00004, 5), round(p[1], 5)]
                            ])
                        cur_seg = [block_pts[i + 1][1]]
                    else:
                        cur_seg.append(block_pts[i + 1][1])

                if len(cur_seg) >= 2:
                    raw_lines.append(rdp_simplify(cur_seg, 2.0))
                elif len(cur_seg) == 1:
                    p = cur_seg[0]
                    raw_lines.append([
                        [round(p[0] - 0.00004, 5), round(p[1], 5)],
                        [round(p[0] + 0.00004, 5), round(p[1], 5)]
                    ])

        # Coordinate precision rounded to 5 decimal places (~1.1 meter accuracy)
        cleaned_lines = [
            [[round(c[0], 5), round(c[1], 5)] for c in seg]
            for seg in raw_lines if len(seg) >= 2
        ]

        # Calculate bounding box area in sq mi
        if all_lons and all_lats:
            min_lon, max_lon = min(all_lons), max(all_lons)
            min_lat, max_lat = min(all_lats), max(all_lats)
            width_mi = (max_lon - min_lon) * 69.0 * math.cos(math.radians((min_lat + max_lat) / 2.0))
            height_mi = (max_lat - min_lat) * 69.0
            bbox_area_sq_mi = round(width_mi * height_mi, 2)
        else:
            bbox_area_sq_mi = 0.0

        props = dict(route_meta[r_id])
        props['point_count'] = len(pts_list)
        props['segment_count'] = len(cleaned_lines)
        props['route_area'] = r_id

        # Match to existing route stats and catchment areas
        stat_match = None
        area_match = None

        if stream_name == 'Trash':
            # Map Trash Route (e.g. 104_2 -> IC104, 301_1 -> OR301)
            num = r_id.split('_')[0]
            for candidate in ['IC' + num, 'OR' + num, r_id]:
                if candidate in stats_lookup:
                    stat_match = stats_lookup[candidate]
                    break
            if not stat_match:
                for k, v in stats_lookup.items():
                    if num in k:
                        stat_match = v
                        break

            for candidate in ['IC' + num, 'OR' + num, r_id]:
                if candidate in areas_lookup:
                    area_match = areas_lookup[candidate]
                    break
            if not area_match:
                for k, v in areas_lookup.items():
                    if num in k:
                        area_match = v
                        break
        else:
            # Recycling route mapping (e.g. R519_3)
            stat_match = stats_lookup.get(r_id)
            if not stat_match:
                num = r_id.split('_')[0]
                for k, v in stats_lookup.items():
                    if num in k:
                        stat_match = v
                        break

            area_match = areas_lookup.get(r_id)
            if not area_match:
                num = r_id.split('_')[0]
                for k, v in areas_lookup.items():
                    if num in k:
                        area_match = v
                        break

        # Populate operational stats
        if stat_match:
            props['total'] = stat_match.get('total', 0)
            props['trash'] = props['total'] if stream_name == 'Trash' else 0
            props['recycling'] = props['total'] if stream_name == 'Recycling' else 0
            props['repeat_rate'] = stat_match.get('repeat_rate', 0.0)
            props['unique_addrs'] = stat_match.get('unique_addrs', 0)
            props['polygon_route_id'] = stat_match.get('route_id')
        else:
            props['total'] = 0
            props['trash'] = 0
            props['recycling'] = 0
            props['repeat_rate'] = 0.0
            props['unique_addrs'] = 0
            props['polygon_route_id'] = None

        if area_match:
            props['ward'] = area_match.get('ward') or props['ward']
            props['neighborhoods'] = area_match.get('neighborhoods', '')
            props['ancs'] = area_match.get('ancs', '')
            props['area_desc'] = area_match.get('area_desc', '')
            props['area_sq_mi'] = area_match.get('area_sq_mi') or bbox_area_sq_mi
        else:
            props['area_sq_mi'] = bbox_area_sq_mi
            props['neighborhoods'] = 'Residential Service Corridor'
            props['ancs'] = ''
            props['area_desc'] = f"{props['ward']} Corridor ({props['point_count']} collection points)"

        # Compute density (requests per square mile)
        if props['area_sq_mi'] and props['area_sq_mi'] > 0:
            props['density'] = round(props['total'] / props['area_sq_mi'], 1)
        else:
            props['density'] = 0.0

        feat = {
            'type': 'Feature',
            'properties': props,
            'geometry': {
                'type': 'MultiLineString',
                'coordinates': cleaned_lines
            }
        }
        features.append(feat)

    return {'type': 'FeatureCollection', 'features': features}

def generate_route_lines():
    t0 = time.time()
    print("=" * 70)
    print("Generating DPW Route Line Layers from Collection Points...")
    print("=" * 70)

    data = get_collection_points()
    print(f"Total collection points in dataset: {len(data.get('features', []))}")

    # Load stats and areas
    stats_path = os.path.join(DATA_DIR, 'route_180d_stats.json')
    areas_path = os.path.join(DATA_DIR, 'route_areas.json')

    trash_stats_lookup = {}
    rec_stats_lookup = {}
    if os.path.exists(stats_path):
        with open(stats_path, 'r', encoding='utf-8') as f:
            stats_raw = json.load(f)
            for r in stats_raw.get('trash_routes', []):
                trash_stats_lookup[r['route_id']] = r
            for r in stats_raw.get('recycle_routes', []):
                rec_stats_lookup[r['route_id']] = r

    trash_areas_lookup = {}
    rec_areas_lookup = {}
    if os.path.exists(areas_path):
        with open(areas_path, 'r', encoding='utf-8') as f:
            areas_raw = json.load(f)
            trash_areas_lookup = areas_raw.get('trash_routes', {})
            rec_areas_lookup = areas_raw.get('recycle_routes', {})

    # Build Trash Routes (line)
    trash_fc = build_route_lines(
        data,
        route_key='TRASH_ROUTE',
        stream_name='Trash',
        stats_lookup=trash_stats_lookup,
        areas_lookup=trash_areas_lookup
    )

    out_trash = os.path.join(DATA_DIR, 'dc_trash_routes_lines.geojson')
    with open(out_trash, 'w', encoding='utf-8') as f:
        json.dump(trash_fc, f, separators=(',', ':'))

    trash_size = os.path.getsize(out_trash) / (1024 * 1024)
    print(f"Generated Trash Routes (line): {len(trash_fc['features'])} routes -> {out_trash} ({trash_size:.2f} MB)")

    # Build Recycling Routes (line)
    rec_fc = build_route_lines(
        data,
        route_key='RECYCLING_ROUTE',
        stream_name='Recycling',
        stats_lookup=rec_stats_lookup,
        areas_lookup=rec_areas_lookup
    )

    out_rec = os.path.join(DATA_DIR, 'dc_recycle_routes_lines.geojson')
    with open(out_rec, 'w', encoding='utf-8') as f:
        json.dump(rec_fc, f, separators=(',', ':'))

    rec_size = os.path.getsize(out_rec) / (1024 * 1024)
    print(f"Generated Recycling Routes (line): {len(rec_fc['features'])} routes -> {out_rec} ({rec_size:.2f} MB)")

    print(f"Completed route line generation in {time.time() - t0:.2f}s")
    print("=" * 70)

if __name__ == '__main__':
    generate_route_lines()
