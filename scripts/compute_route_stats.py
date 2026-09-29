#!/usr/bin/env python3
"""
Computes DPW route performance metrics and exports data/route_180d_stats.json.
Performs spatial point-in-polygon ray casting matching 180-day service requests
against 103 DPW Trash Routes and 120 DPW Recycling Routes.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spatial_utils import is_point_in_ring, is_point_in_poly, get_poly_rings_list, get_bbox, anc_sort_key
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

    