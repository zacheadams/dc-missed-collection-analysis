#!/usr/bin/env python3
"""
Precomputes spatial intersections mapping DPW routes to wards, neighborhoods, and ANCs.
Combines polygon geometries with street-level collection point boundaries for ground-truth accuracy.
Generates data/route_areas.json.

Strict standards:
- Strictly zero emojis across code, logs, and outputs
- Zero third-party pip dependencies (standard library only)
"""

import json
import math
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import re
from collections import defaultdict, Counter

from spatial_utils import is_point_in_ring, is_point_in_poly, get_poly_rings_list, get_bbox, anc_sort_key

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def ring_area_sq_mi(coords):
    if len(coords) < 3:
        return 0.0
    lat_rad = math.radians(38.9)
    kx = 69.0 * math.cos(lat_rad)
    ky = 69.0
    area = 0.0
    for i in range(len(coords) - 1):
        x1, y1 = coords[i][0] * kx, coords[i][1] * ky
        x2, y2 = coords[i+1][0] * kx, coords[i+1][1] * ky
        area += (x1 * y2 - x2 * y1)
    return abs(area) * 0.5

def feat_list_area_sq_mi(feat_list):
    total = 0.0
    for f in feat_list:
        geom = f.get('geometry', {})
        t = geom.get('type')
        coords = geom.get('coordinates', [])
        if t == 'Polygon':
            total += ring_area_sq_mi(coords[0])
            for hole in coords[1:]:
                total -= ring_area_sq_mi(hole)
        elif t == 'MultiPolygon':
            for poly in coords:
                total += ring_area_sq_mi(poly[0])
                for hole in poly[1:]:
                    total -= ring_area_sq_mi(hole)
    return round(max(0.001, total), 3)






def merge_line_props(props_list):
    """
    Merge spatial properties from multiple line route runs (e.g. 101_2 and 101_4).
    Ensures ANCs are sorted in ascending numerical and then alphabetical order.
    """
    # Collect unique wards in order
    wards = []
    for p in props_list:
        for w in re.findall(r'Ward\s+(\d+)', p.get('ward', '')):
            if w not in wards:
                wards.append(w)
    ward_str = ' / '.join([f'Ward {w}' for w in sorted(wards)]) if wards else 'District-Wide'

    # Collect unique ANCs and sort in ascending numerical then alphabetical order
    raw_ancs = []
    for p in props_list:
        parts = p.get('ancs', '').replace('ANC', '').split(',')
        for a in parts:
            a = a.strip()
            if a and a not in raw_ancs:
                raw_ancs.append(a)
    sorted_ancs = sorted(raw_ancs, key=anc_sort_key)
    ancs_str = 'ANC ' + ', '.join(sorted_ancs) if sorted_ancs else ''

    # Collect unique neighborhoods in order
    nbhs = []
    for p in props_list:
        for n in p.get('neighborhoods', '').split(','):
            n = n.strip()
            if n and n not in nbhs and len(nbhs) < 3:
                nbhs.append(n)
    nbhs_str = ', '.join(nbhs) if nbhs else 'Residential Corridor'
    area_desc = f'{ward_str} • {nbhs_str}' + (f' ({ancs_str})' if ancs_str else '')
    return ward_str, nbhs_str, ancs_str, area_desc

def compute_route_areas():
    trash_geo_path = os.path.join(BASE_DIR, 'data/dc_trash_routes.geojson')
    rec_geo_path = os.path.join(BASE_DIR, 'data/dc_recycle_routes.geojson')
    clust_geo_path = os.path.join(BASE_DIR, 'data/dc_neighborhood_clusters.geojson')
    nbh_geo_path = os.path.join(BASE_DIR, 'data/dc_neighborhoods.geojson')
    smd_geo_path = os.path.join(BASE_DIR, 'data/dc_smds.geojson')
    ward_geo_path = os.path.join(BASE_DIR, 'data/dc_wards.geojson')

    with open(trash_geo_path, 'r', encoding='utf-8') as f:
        trash_geo = json.load(f)
    with open(rec_geo_path, 'r', encoding='utf-8') as f:
        rec_geo = json.load(f)
    with open(clust_geo_path, 'r', encoding='utf-8') as f:
        clust_geo = json.load(f)
    with open(nbh_geo_path, 'r', encoding='utf-8') as f:
        nbh_geo = json.load(f)
    with open(smd_geo_path, 'r', encoding='utf-8') as f:
        smd_geo = json.load(f)
    with open(ward_geo_path, 'r', encoding='utf-8') as f:
        ward_geo = json.load(f)

    # Build spatial boundary indexes for fallback polygon sampling
    clusters = []
    for f in clust_geo['features']:
        polys = get_poly_rings_list(f['geometry'])
        clusters.append({
            'name': f['properties'].get('NBH_NAMES', ''),
            'cluster': f['properties'].get('NAME', ''),
            'polys': polys,
            'bbox': get_bbox(polys)
        })

    nbh_pts = []
    for f in nbh_geo['features']:
        nbh_pts.append({
            'name': f['properties']['NAME'],
            'coord': f['geometry']['coordinates']
        })

    smds = []
    for f in smd_geo['features']:
        polys = get_poly_rings_list(f['geometry'])
        smds.append({
            'smd_id': f['properties']['SMD_ID'],
            'anc_id': f['properties']['ANC_ID'],
            'polys': polys,
            'bbox': get_bbox(polys)
        })

    wards = []
    for f in ward_geo['features']:
        polys = get_poly_rings_list(f['geometry'])
        wards.append({
            'ward': f['properties'].get('WARD', f['properties'].get('NAME', '')),
            'polys': polys,
            'bbox': get_bbox(polys)
        })

    def analyze_polygon_features(feat_list):
        all_polys = []
        for f in feat_list:
            all_polys.extend(get_poly_rings_list(f['geometry']))

        grid_clusters = Counter()
        grid_ancs = Counter()
        grid_wards = Counter()

        for p in all_polys:
            p_box = get_bbox([p])
            p_steps = 5
            sampled_inside = 0
            for ix in range(p_steps):
                gx = p_box[0] + (p_box[2] - p_box[0]) * (ix + 0.5) / p_steps
                for iy in range(p_steps):
                    gy = p_box[1] + (p_box[3] - p_box[1]) * (iy + 0.5) / p_steps
                    if is_point_in_poly(gx, gy, p):
                        sampled_inside += 1
                        for s in smds:
                            if s['bbox'][0] <= gx <= s['bbox'][2] and s['bbox'][1] <= gy <= s['bbox'][3]:
                                if any(is_point_in_poly(gx, gy, sp) for sp in s['polys']):
                                    grid_ancs[s['anc_id']] += 1
                                    break
                        for w in wards:
                            if w['bbox'][0] <= gx <= w['bbox'][2] and w['bbox'][1] <= gy <= w['bbox'][3]:
                                if any(is_point_in_poly(gx, gy, wp) for wp in w['polys']):
                                    grid_wards[str(w['ward'])] += 1
                                    break
                        for c in clusters:
                            if c['bbox'][0] <= gx <= c['bbox'][2] and c['bbox'][1] <= gy <= c['bbox'][3]:
                                if any(is_point_in_poly(gx, gy, cp) for cp in c['polys']):
                                    for part in c['name'].split(','):
                                        p_clean = part.strip()
                                        if p_clean: grid_clusters[p_clean] += 1
                                    break
            # Fallback for very small polygons: sample centroid or first vertex
            if sampled_inside == 0:
                ring = p[0]
                cx = sum(pt[0] for pt in ring) / len(ring)
                cy = sum(pt[1] for pt in ring) / len(ring)
                test_pt = (cx, cy) if is_point_in_poly(cx, cy, p) else ring[0]
                for s in smds:
                    if s['bbox'][0] <= test_pt[0] <= s['bbox'][2] and s['bbox'][1] <= test_pt[1] <= s['bbox'][3]:
                        if any(is_point_in_poly(test_pt[0], test_pt[1], sp) for sp in s['polys']):
                            grid_ancs[s['anc_id']] += 1
                            break
                for w in wards:
                    if w['bbox'][0] <= test_pt[0] <= w['bbox'][2] and w['bbox'][1] <= test_pt[1] <= w['bbox'][3]:
                        if any(is_point_in_poly(test_pt[0], test_pt[1], wp) for wp in w['polys']):
                            grid_wards[str(w['ward'])] += 1
                            break
                for c in clusters:
                    if c['bbox'][0] <= test_pt[0] <= c['bbox'][2] and c['bbox'][1] <= test_pt[1] <= c['bbox'][3]:
                        if any(is_point_in_poly(test_pt[0], test_pt[1], cp) for cp in c['polys']):
                            for part in c['name'].split(','):
                                p_clean = part.strip()
                                if p_clean: grid_clusters[p_clean] += 1
                            break

        total_anc_hits = sum(grid_ancs.values())
        raw_top = [a for a, count in grid_ancs.most_common() if count >= 2 or (total_anc_hits > 0 and count / total_anc_hits >= 0.03)]
        if not raw_top and grid_ancs:
            raw_top = [grid_ancs.most_common(1)[0][0]]
        sorted_ancs = sorted(raw_top[:6], key=anc_sort_key)

        anc_wards = set()
        for a in sorted_ancs:
            if a and a[0].isdigit():
                anc_wards.add(a[0])
            elif a.startswith('3/4G'):
                anc_wards.add('3')
                anc_wards.add('4')

        top_ward = f"Ward {grid_wards.most_common(1)[0][0]}" if grid_wards else "District-Wide"
        if len(grid_wards) > 1:
            w1_cnt = grid_wards.most_common(1)[0][1]
            for w, cnt in grid_wards.most_common()[1:]:
                if cnt > w1_cnt * 0.15 or (cnt > w1_cnt * 0.08 and w in anc_wards):
                    top_ward += f" / Ward {w}"

        nbh_names = []
        for n, _ in grid_clusters.most_common():
            if n not in nbh_names and len(nbh_names) < 3:
                nbh_names.append(n)
        area_str = ", ".join(nbh_names) if nbh_names else "Residential Corridor"
        ancs_str = f"ANC {', '.join(sorted_ancs)}" if sorted_ancs else ""
        return {
            'ward': top_ward,
            'neighborhoods': area_str,
            'ancs': ancs_str,
            'area_desc': f"{top_ward} • {area_str}" + (f" ({ancs_str})" if ancs_str else ""),
            'area_sq_mi': feat_list_area_sq_mi(feat_list)
        }

    # Load pre-annotated line geometries or existing route_areas if available
    trash_lines_path = os.path.join(BASE_DIR, 'data/dc_trash_routes_lines.geojson')
    rec_lines_path = os.path.join(BASE_DIR, 'data/dc_recycle_routes_lines.geojson')
    out_path = os.path.join(BASE_DIR, 'data/route_areas.json')

    existing_ra = {}
    if os.path.exists(out_path):
        try:
            with open(out_path, 'r', encoding='utf-8') as f:
                existing_ra = json.load(f)
        except Exception:
            existing_ra = {}

    trash_poly_to_lines = defaultdict(list)
    trash_line_entries = dict(existing_ra.get('trash_lines', {}))
    if os.path.exists(trash_lines_path):
        with open(trash_lines_path, 'r', encoding='utf-8') as f:
            tl_data = json.load(f)
        for feat in tl_data.get('features', []):
            p = feat.get('properties', {})
            rid = p.get('route')
            pid = p.get('polygon_route_id')
            if pid:
                trash_poly_to_lines[pid].append(p)
            if rid:
                raw_a = [x.strip() for x in p.get('ancs', '').replace('ANC', '').split(',') if x.strip()]
                sorted_a = 'ANC ' + ', '.join(sorted(raw_a, key=anc_sort_key)) if raw_a else ''
                trash_line_entries[rid] = {
                    'ward': p.get('ward', ''),
                    'neighborhoods': p.get('neighborhoods', ''),
                    'ancs': sorted_a,
                    'area_desc': p.get('area_desc', ''),
                    'area_sq_mi': p.get('area_sq_mi', 0.0)
                }

    rec_line_entries = dict(existing_ra.get('recycle_lines', {}))
    if os.path.exists(rec_lines_path):
        with open(rec_lines_path, 'r', encoding='utf-8') as f:
            rl_data = json.load(f)
        for feat in rl_data.get('features', []):
            p = feat.get('properties', {})
            rid = p.get('route')
            if rid:
                raw_a = [x.strip() for x in p.get('ancs', '').replace('ANC', '').split(',') if x.strip()]
                sorted_a = 'ANC ' + ', '.join(sorted(raw_a, key=anc_sort_key)) if raw_a else ''
                rec_line_entries[rid] = {
                    'ward': p.get('ward', ''),
                    'neighborhoods': p.get('neighborhoods', ''),
                    'ancs': sorted_a,
                    'area_desc': p.get('area_desc', ''),
                    'area_sq_mi': p.get('area_sq_mi', 0.0)
                }

    # Group polygon features by Route ID
    trash_groups = defaultdict(list)
    for f in trash_geo['features']:
        trash_groups[f['properties']['TrashRouteArea']].append(f)

    recycle_groups = defaultdict(list)
    for f in rec_geo['features']:
        recycle_groups[f['properties']['Route']].append(f)

    trash_poly_areas = {}
    for rid, feats in trash_groups.items():
        trash_poly_areas[rid] = analyze_polygon_features(feats)

    recycle_poly_areas = {}
    for rid, feats in recycle_groups.items():
        recycle_poly_areas[rid] = analyze_polygon_features(feats)

    # For backward-compatible unified lookups, combine line and polygon entries
    # Polygon entries take strict precedence for polygon route IDs
    trash_merged = dict(trash_line_entries)
    trash_merged.update(trash_poly_areas)

    recycle_merged = dict(rec_line_entries)
    for lid, entry in list(recycle_merged.items()):
        alt_id = lid[1:] if lid.startswith('R') else f"R{lid}"
        if alt_id not in recycle_merged:
            recycle_merged[alt_id] = entry
    recycle_merged.update(recycle_poly_areas)

    output = {
        'trash_routes': trash_poly_areas,
        'recycle_routes': recycle_poly_areas,
        'trash_lines': trash_line_entries,
        'recycle_lines': rec_line_entries,
        'trash': trash_merged,
        'recycle': recycle_merged
    }

    out_path = os.path.join(BASE_DIR, 'data/route_areas.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)

    print(f"Generated data/route_areas.json: {len(trash_poly_areas)} trash routes, {len(recycle_poly_areas)} recycle routes")
    return output

if __name__ == '__main__':
    compute_route_areas()
