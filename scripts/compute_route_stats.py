#!/usr/bin/env python3
"""
Computes DPW route performance metrics and exports data/route_180d_stats.json.
Performs spatial point-in-polygon ray casting matching 180-day service requests
against 103 DPW Trash Routes and 120 DPW Recycling Routes.
"""

import os
import sys
import json
from collections import defaultdict
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def compute_route_stats():
    # Load datasets
    sr_path = os.path.join(BASE_DIR, 'data', 'dc_180d_service_requests.json')
    trash_geo_path = os.path.join(BASE_DIR, 'data', 'dc_trash_routes.geojson')
    rec_geo_path = os.path.join(BASE_DIR, 'data', 'dc_recycle_routes.geojson')
    areas_path = os.path.join(BASE_DIR, 'data', 'route_areas.json')

    with open(sr_path, 'r', encoding='utf-8') as f:
        srs = json.load(f)

    with open(trash_geo_path, 'r', encoding='utf-8') as f:
        trash_geo = json.load(f)

    with open(rec_geo_path, 'r', encoding='utf-8') as f:
        rec_geo = json.load(f)

    route_areas = {}
    if os.path.exists(areas_path):
        with open(areas_path, 'r', encoding='utf-8') as f:
            route_areas = json.load(f)

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

    trash_routes = []
    for f in trash_geo['features']:
        polys = get_poly_rings_list(f['geometry'])
        bbox = get_bbox(polys)
        trash_routes.append({
            'id': f['properties']['TrashRouteArea'],
            'polys': polys,
            'bbox': bbox,
            'props': f['properties']
        })

    recycle_routes = []
    for f in rec_geo['features']:
        polys = get_poly_rings_list(f['geometry'])
        bbox = get_bbox(polys)
        recycle_routes.append({
            'id': f['properties']['Route'],
            'polys': polys,
            'bbox': bbox,
            'props': f['properties']
        })

    def find_match(x, y, routes):
        for r in routes:
            if x < r['bbox'][0] or x > r['bbox'][2] or y < r['bbox'][1] or y > r['bbox'][3]:
                continue
            if any(is_point_in_poly(x, y, p) for p in r['polys']):
                return r
        return None

    unique_trash_props = {}
    for r in trash_routes:
        if r['id'] not in unique_trash_props:
            unique_trash_props[r['id']] = r['props']

    unique_rec_props = {}
    for r in recycle_routes:
        if r['id'] not in unique_rec_props:
            unique_rec_props[r['id']] = r['props']

    trash_srs_by_route = defaultdict(list)
    recycle_srs_by_route = defaultdict(list)

    for item in srs:
        attrs = item.get('attributes', item)
        x = attrs.get('LONGITUDE', attrs.get('x'))
        y = attrs.get('LATITUDE', attrs.get('y'))
        service_code = attrs.get('SERVICECODE')

        if x is None or y is None:
            continue

        if service_code == 'S0441':
            matched = find_match(x, y, trash_routes)
            if matched:
                trash_srs_by_route[matched['id']].append(attrs)
        elif service_code == 'S0321':
            matched = find_match(x, y, recycle_routes)
            if matched:
                recycle_srs_by_route[matched['id']].append(attrs)

    def analyze_route(route_id, req_list, props, is_trash=True):
        total = len(req_list)
        addrs = defaultdict(int)
        days_count = defaultdict(int)

        for attrs in req_list:
            addr = attrs.get('STREETADDRESS') or attrs.get('MARADDRESSREPOSITORYID') or 'UNKNOWN'
            addr = str(addr).strip().upper()
            addrs[addr] += 1
            add_date = attrs.get('ADDDATE')
            if add_date:
                try:
                    if isinstance(add_date, (int, float)):
                        dt = datetime.fromtimestamp(add_date / 1000.0)
                    else:
                        dt = datetime.fromisoformat(str(add_date).replace('Z', '+00:00'))
                    days_count[dt.strftime('%A')] += 1
                except Exception:
                    pass

        unique_addrs = len(addrs)
        repeat_addrs = sum(1 for a, count in addrs.items() if count > 1)
        repeat_rate = round(repeat_addrs / unique_addrs * 100, 1) if unique_addrs > 0 else 0.0
        req_per_addr = round(total / unique_addrs, 2) if unique_addrs > 0 else 0.0

        sched = props.get('CollectionDays') or props.get('CollectionDay') or props.get('Day' if not is_trash else 'DayWeb') or 'Unassigned'
        runs = props.get('RunsWeb', 1) if is_trash else 1
        service_area = props.get('ServiceAre', 'Outer Ring') if is_trash else 'Standard'
        status = props.get('Status', 'Active')

        return {
            'route_id': route_id,
            'type': 'Trash' if is_trash else 'Recycling',
            'route_name': f"{'Trash' if is_trash else 'Recycling'} Route {route_id}",
            'schedule': sched,
            'service_area': service_area,
            'runs_per_week': runs,
            'status': status,
            'ward': props.get('Ward', ''),
            'neighborhoods': props.get('Neighborhoods', ''),
            'ancs': props.get('ANCs', ''),
            'area_desc': props.get('AreaDesc', ''),
            'total': total,
            'unique_addrs': unique_addrs,
            'repeat_addrs': repeat_addrs,
            'single_addrs': unique_addrs - repeat_addrs,
            'repeat_rate': repeat_rate,
            'req_per_addr': req_per_addr,
            'days_count': dict(days_count)
        }

    trash_out = []
    for r_id, props in unique_trash_props.items():
        reqs = trash_srs_by_route.get(r_id, [])
        trash_out.append(analyze_route(r_id, reqs, props, is_trash=True))

    recycle_out = []
    for r_id, props in unique_rec_props.items():
        reqs = recycle_srs_by_route.get(r_id, [])
        recycle_out.append(analyze_route(r_id, reqs, props, is_trash=False))

    route_stats_path = os.path.join(BASE_DIR, 'data', 'route_180d_stats.json')
    with open(route_stats_path, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'period': '180 Days Rolling Window',
                'trash_routes_count': len(trash_out),
                'recycle_routes_count': len(recycle_out),
                'trash_requests_matched': sum(r['total'] for r in trash_out),
                'recycle_requests_matched': sum(r['total'] for r in recycle_out)
            },
            'trash_routes': trash_out,
            'recycle_routes': recycle_out
        }, f, indent=2)

    print(f"Successfully computed route statistics -> {route_stats_path} ({len(trash_out)} trash, {len(recycle_out)} recycling)")

if __name__ == '__main__':
    compute_route_stats()
