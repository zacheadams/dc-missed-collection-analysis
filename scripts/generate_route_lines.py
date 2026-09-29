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
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spatial_utils import is_point_in_ring, is_point_in_poly, get_poly_rings_list, get_bbox, anc_sort_key
import sys
import json
import re
import math
import time
import urllib.request
from collections import defaultdict, Counter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

COLLECTION_POINTS_URL = (
    "https://opendata.arcgis.com/api/v3/datasets/110d1c51124b4154aab5ca64445afdb0_2"
    "/downloads/data?format=geojson&spatialRefId=4326&where=1%3D1"
)

LOCAL_POINTS_PATH = os.path.join(DATA_DIR, 'dc_collection_points.geojson')

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


def build_spatial_indexes():
    """Build spatial grid indexes for Wards, SMDs/ANCs, and Neighborhood Clusters."""
    grid_size = 0.01
    ward_grid = defaultdict(list)
    smd_grid = defaultdict(list)
    clust_grid = defaultdict(list)

    ward_path = os.path.join(DATA_DIR, 'dc_wards.geojson')
    smd_path = os.path.join(DATA_DIR, 'dc_smds.geojson')
    clust_path = os.path.join(DATA_DIR, 'dc_neighborhood_clusters.geojson')

    if os.path.exists(ward_path):
        with open(ward_path, 'r', encoding='utf-8') as f:
            ward_geo = json.load(f)
        for f in ward_geo['features']:
            props = f['properties']
            polys = get_poly_rings_list(f['geometry'])
            bbox = get_bbox(polys)
            item = {'ward': str(props.get('WARD', props.get('NAME', ''))), 'polys': polys, 'bbox': bbox}
            for gx in range(int(bbox[0]/grid_size), int(bbox[2]/grid_size)+1):
                for gy in range(int(bbox[1]/grid_size), int(bbox[3]/grid_size)+1):
                    ward_grid[(gx, gy)].append(item)

    if os.path.exists(smd_path):
        with open(smd_path, 'r', encoding='utf-8') as f:
            smd_geo = json.load(f)
        for f in smd_geo['features']:
            props = f['properties']
            polys = get_poly_rings_list(f['geometry'])
            bbox = get_bbox(polys)
            item = {'anc_id': props['ANC_ID'], 'smd_id': props.get('SMD_ID'), 'polys': polys, 'bbox': bbox}
            for gx in range(int(bbox[0]/grid_size), int(bbox[2]/grid_size)+1):
                for gy in range(int(bbox[1]/grid_size), int(bbox[3]/grid_size)+1):
                    smd_grid[(gx, gy)].append(item)

    if os.path.exists(clust_path):
        with open(clust_path, 'r', encoding='utf-8') as f:
            clust_geo = json.load(f)
        for f in clust_geo['features']:
            props = f['properties']
            polys = get_poly_rings_list(f['geometry'])
            bbox = get_bbox(polys)
            item = {'names': [p.strip() for p in props.get('NBH_NAMES', '').split(',') if p.strip()], 'polys': polys, 'bbox': bbox}
            for gx in range(int(bbox[0]/grid_size), int(bbox[2]/grid_size)+1):
                for gy in range(int(bbox[1]/grid_size), int(bbox[3]/grid_size)+1):
                    clust_grid[(gx, gy)].append(item)

    return grid_size, ward_grid, smd_grid, clust_grid

def annotate_collection_points(data, grid_size, ward_grid, smd_grid, clust_grid):
    """Spatially index all collection points to their Ward, ANC, and Neighborhoods."""
    print("Classifying collection points against spatial boundaries...")
    t0 = time.time()
    for f in data.get('features', []):
        c = f['geometry']['coordinates']
        x, y = c[0], c[1]
        cell = (int(x / grid_size), int(y / grid_size))

        pt_ward = None
        for item in ward_grid.get(cell, []):
            bb = item['bbox']
            if bb[0] <= x <= bb[2] and bb[1] <= y <= bb[3]:
                if any(is_point_in_poly(x, y, p) for p in item['polys']):
                    pt_ward = item['ward']
                    break

        pt_anc = None
        for item in smd_grid.get(cell, []):
            bb = item['bbox']
            if bb[0] <= x <= bb[2] and bb[1] <= y <= bb[3]:
                if any(is_point_in_poly(x, y, p) for p in item['polys']):
                    pt_anc = item['anc_id']
                    break

        pt_clusters = []
        for item in clust_grid.get(cell, []):
            bb = item['bbox']
            if bb[0] <= x <= bb[2] and bb[1] <= y <= bb[3]:
                if any(is_point_in_poly(x, y, p) for p in item['polys']):
                    pt_clusters.extend(item['names'])
                    break

        # Fallback to feature properties if point fell on outer boundary edge
        if not pt_ward:
            raw_w = f['properties'].get('WARD')
            if raw_w:
                m = re.search(r'\d+', str(raw_w))
                if m:
                    pt_ward = m.group(0)

        f['_spatial'] = {
            'ward': pt_ward,
            'anc_id': pt_anc,
            'clusters': pt_clusters
        }
    print(f"Annotated {len(data.get('features', []))} collection points in {time.time() - t0:.2f}s")

def get_collection_points():
    """Load or download DPW collection points GeoJSON."""
    if os.path.exists(LOCAL_POINTS_PATH):
        print(f"Loading collection points from {LOCAL_POINTS_PATH}...")
        with open(LOCAL_POINTS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
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
    Construct MultiLineString features for each route with accurate spatial boundaries and enumeration.
    """
    routes = defaultdict(list)

    for f in data.get('features', []):
        p = f.get('properties', {})
        r = p.get(route_key)
        if not r or str(r).strip() in ['', 'NA', 'None']:
            continue
        r_str = str(r).strip()
        routes[r_str].append(f)

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

        # Determine operational schedule day from collection points
        day_counts = Counter(f['properties'].get('DAY') for f in pts_list if f['properties'].get('DAY'))
        best_day = day_counts.most_common(1)[0][0] if day_counts else 'Scheduled'

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

        # Compute spatial boundary presence from actual collection points
        ward_counts = Counter()
        anc_counts = Counter()
        cluster_counts = Counter()

        for f in pts_list:
            sp = f.get('_spatial', {})
            if sp.get('ward'):
                ward_counts[sp['ward']] += 1
            if sp.get('anc_id'):
                anc_counts[sp['anc_id']] += 1
            for cl in sp.get('clusters', []):
                cluster_counts[cl] += 1

        total_pts = len(pts_list)
        # Significant wards: at least 15 collection points or >= 5% of route points
        sig_wards = [w for w, cnt in ward_counts.most_common() if cnt >= 15 or cnt / total_pts >= 0.05]
        if not sig_wards and ward_counts:
            sig_wards = [ward_counts.most_common(1)[0][0]]

        if len(sig_wards) > 1:
            m = r_id.replace('R', '').split('_')[0]
            root_w = m[0] if m and m[0].isdigit() else None
            if root_w in sig_wards:
                sorted_wards = [root_w] + [w for w in sorted(sig_wards) if w != root_w]
            else:
                sorted_wards = [w for w, _ in ward_counts.most_common() if w in sig_wards]
        else:
            sorted_wards = sig_wards

        ward_str = ' / '.join([f'Ward {w}' for w in sorted_wards])

        # Significant ANCs: at least 10 collection points or >= 5% of route points
        sig_ancs = [a for a, cnt in anc_counts.most_common() if cnt >= 10 or cnt / total_pts >= 0.05]
        if not sig_ancs and anc_counts:
            sig_ancs = [anc_counts.most_common(1)[0][0]]
        sig_ancs = sorted(sig_ancs, key=anc_sort_key)
        ancs_str = 'ANC ' + ', '.join(sig_ancs[:5])

        # Neighborhoods: distinct names in frequency order
        top_nbhs = []
        for n, _ in cluster_counts.most_common():
            if n not in top_nbhs and len(top_nbhs) < 3:
                top_nbhs.append(n)
        nbhs_str = ', '.join(top_nbhs) if top_nbhs else (area_match.get('neighborhoods') if area_match else 'Residential Service Corridor')

        area_desc = f'{ward_str} • {nbhs_str}' + (f' ({ancs_str})' if ancs_str else '')

        # Build feature properties
        props = {
            'route': r_id,
            'stream': stream_name,
            'day': best_day,
            'ward': ward_str,
            'point_count': total_pts,
            'segment_count': len(cleaned_lines),
            'route_area': r_id,
            'neighborhoods': nbhs_str,
            'ancs': ancs_str,
            'area_desc': area_desc,
            'total': stat_match.get('total', 0) if stat_match else 0,
            'trash': (stat_match.get('total', 0) if stat_match else 0) if stream_name == 'Trash' else 0,
            'recycling': (stat_match.get('total', 0) if stat_match else 0) if stream_name == 'Recycling' else 0,
            'repeat_rate': stat_match.get('repeat_rate', 0.0) if stat_match else 0.0,
            'unique_addrs': stat_match.get('unique_addrs', 0) if stat_match else 0,
            'polygon_route_id': stat_match.get('route_id') if stat_match else None,
            'area_sq_mi': (area_match.get('area_sq_mi') if area_match else 0.0) or bbox_area_sq_mi
        }

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

    # Build spatial index and classify collection points
    grid_size, ward_grid, smd_grid, clust_grid = build_spatial_indexes()
    annotate_collection_points(data, grid_size, ward_grid, smd_grid, clust_grid)

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
