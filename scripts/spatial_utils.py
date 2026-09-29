#!/usr/bin/env python3
"""
Shared spatial utility functions for geometric point-in-polygon tests,
bounding box calculations, and ANC sorting logic.

Strict standards:
- Strictly zero emojis across code, logs, and outputs
- Zero third-party pip dependencies (standard library only)
"""

import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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

def anc_sort_key(anc):
    """
    Sort key for ascending numerical and alphabetical ordering of DC ANCs.
    e.g. 1A < 1B < ... < 2A < 2B < ... < 3F < 3/4G < 4A ... < 8F
    """
    anc = anc.strip().replace('ANC', '').strip()
    if not anc:
        return (99, '', '')
    if anc.startswith('3/4G'):
        return (3, '4G', '')
    m = re.match(r'^(\d+)([A-Z]+)?(.*)$', anc)
    if m:
        return (int(m.group(1)), m.group(2) or '', m.group(3) or '')
    return (99, anc, '')
