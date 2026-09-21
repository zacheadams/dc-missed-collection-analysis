import json
import os
from collections import defaultdict, Counter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
    t = geom['type']
    coords = geom['coordinates']
    if t == 'Polygon':
        return [coords]
    elif t == 'MultiPolygon':
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

with open(os.path.join(BASE_DIR, 'data/dc_trash_routes.geojson')) as f:
    trash_geo = json.load(f)
with open(os.path.join(BASE_DIR, 'data/dc_recycle_routes.geojson')) as f:
    rec_geo = json.load(f)
with open(os.path.join(BASE_DIR, 'data/dc_neighborhood_clusters.geojson')) as f:
    clust_geo = json.load(f)
with open(os.path.join(BASE_DIR, 'data/dc_neighborhoods.geojson')) as f:
    nbh_geo = json.load(f)
with open(os.path.join(BASE_DIR, 'data/dc_smds.geojson')) as f:
    smd_geo = json.load(f)
with open(os.path.join(BASE_DIR, 'data/dc_wards.geojson')) as f:
    ward_geo = json.load(f)

# Build spatial indexes
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

def analyze_route(feat_list):
    all_polys = []
    for f in feat_list:
        all_polys.extend(get_poly_rings_list(f['geometry']))
    bbox = get_bbox(all_polys)

    contained_nbhs = []
    for np in nbh_pts:
        nx, ny = np['coord']
        if bbox[0] <= nx <= bbox[2] and bbox[1] <= ny <= bbox[3]:
            if any(is_point_in_poly(nx, ny, p) for p in all_polys):
                contained_nbhs.append(np['name'])

    grid_clusters = Counter()
    grid_ancs = Counter()
    grid_wards = Counter()

    steps = 14
    for ix in range(steps):
        gx = bbox[0] + (bbox[2] - bbox[0]) * (ix + 0.5) / steps
        for iy in range(steps):
            gy = bbox[1] + (bbox[3] - bbox[1]) * (iy + 0.5) / steps
            if any(is_point_in_poly(gx, gy, p) for p in all_polys):
                for c in clusters:
                    if c['bbox'][0] <= gx <= c['bbox'][2] and c['bbox'][1] <= gy <= c['bbox'][3]:
                        if any(is_point_in_poly(gx, gy, cp) for cp in c['polys']):
                            for part in c['name'].split(','):
                                p_clean = part.strip()
                                if p_clean: grid_clusters[p_clean] += 1
                for s in smds:
                    if s['bbox'][0] <= gx <= s['bbox'][2] and s['bbox'][1] <= gy <= s['bbox'][3]:
                        if any(is_point_in_poly(gx, gy, sp) for sp in s['polys']):
                            grid_ancs[s['anc_id']] += 1
                for w in wards:
                    if w['bbox'][0] <= gx <= w['bbox'][2] and w['bbox'][1] <= gy <= w['bbox'][3]:
                        if any(is_point_in_poly(gx, gy, wp) for wp in w['polys']):
                            grid_wards[str(w['ward'])] += 1

    final_nbhs = []
    for n in contained_nbhs:
        if n not in final_nbhs: final_nbhs.append(n)
    for n, count in grid_clusters.most_common(5):
        if n not in final_nbhs and len(final_nbhs) < 4:
            final_nbhs.append(n)

    top_ancs = [a[0] for a in grid_ancs.most_common(3)]
    top_ward = f"Ward {grid_wards.most_common(1)[0][0]}" if grid_wards else "District-Wide"
    if len(grid_wards) > 1 and grid_wards.most_common(2)[1][1] > grid_wards.most_common(1)[0][1] * 0.4:
        top_ward += f" / Ward {grid_wards.most_common(2)[1][0]}"

    area_str = ", ".join(final_nbhs[:3]) if final_nbhs else "Residential Corridor"
    ancs_str = f"ANC {', '.join(top_ancs)}" if top_ancs else ""
    return {
        'ward': top_ward,
        'neighborhoods': area_str,
        'ancs': ancs_str,
        'area_desc': f"{top_ward} • {area_str}" + (f" ({ancs_str})" if ancs_str else "")
    }

trash_groups = defaultdict(list)
for f in trash_geo['features']:
    trash_groups[f['properties']['TrashRouteArea']].append(f)

recycle_groups = defaultdict(list)
for f in rec_geo['features']:
    recycle_groups[f['properties']['Route']].append(f)

trash_areas = {}
for rid, feats in trash_groups.items():
    trash_areas[rid] = analyze_route(feats)

recycle_areas = {}
for rid, feats in recycle_groups.items():
    recycle_areas[rid] = analyze_route(feats)

output = {
    'trash_routes': trash_areas,
    'recycle_routes': recycle_areas
}

with open(os.path.join(BASE_DIR, 'data/route_areas.json'), 'w') as f:
    json.dump(output, f, indent=2)

print(f"Generated data/route_areas.json: {len(trash_areas)} trash routes, {len(recycle_areas)} recycle routes")
