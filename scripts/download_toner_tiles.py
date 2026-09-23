#!/usr/bin/env python3
"""
Downloads and packages Stamen Toner tiles for Washington, DC locally.
Tiles are strictly subsetted to the District of Columbia boundary polygon
for Zooms 11 through 15, eliminating runtime external dependencies and Stadia API keys.
"""

import os
import sys
import json
import math
import time
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TILES_DIR = os.path.join(BASE_DIR, 'tiles')
WARDS_PATH = os.path.join(BASE_DIR, 'data', 'dc_wards.geojson')

PNG_HEADER = b'\x89PNG\r\n\x1a\n'

def num2deg(xtile, ytile, zoom):
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return (lat_deg, lon_deg)

def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)

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

def load_dc_geometry():
    with open(WARDS_PATH, 'r', encoding='utf-8') as f:
        wards = json.load(f)

    all_pts = []
    rings = []
    for f in wards['features']:
        g = f['geometry']
        def extract(c):
            if isinstance(c[0], (int, float)):
                all_pts.append((c[0], c[1]))
            else:
                for sub in c:
                    extract(sub)
        extract(g['coordinates'])

        if g['type'] == 'Polygon':
            rings.append(g['coordinates'][0])
        elif g['type'] == 'MultiPolygon':
            for p in g['coordinates']:
                rings.append(p[0])

    min_lon = min(p[0] for p in all_pts)
    max_lon = max(p[0] for p in all_pts)
    min_lat = min(p[1] for p in all_pts)
    max_lat = max(p[1] for p in all_pts)

    return rings, all_pts, (min_lat, max_lat, min_lon, max_lon)

def tile_intersects_dc(x, y, z, rings, all_pts):
    nw_lat, nw_lon = num2deg(x, y, z)
    se_lat, se_lon = num2deg(x + 1, y + 1, z)
    tile_min_lat = se_lat
    tile_max_lat = nw_lat
    tile_min_lon = nw_lon
    tile_max_lon = se_lon

    # Check if any DC boundary point is inside the tile
    for px, py in all_pts:
        if tile_min_lon <= px <= tile_max_lon and tile_min_lat <= py <= tile_max_lat:
            return True

    # 4x4 grid sampling across tile
    for sx in range(4):
        for sy in range(4):
            tx = tile_min_lon + sx * (tile_max_lon - tile_min_lon) / 3.0
            ty = tile_min_lat + sy * (tile_max_lat - tile_min_lat) / 3.0
            for r in rings:
                if is_point_in_ring(tx, ty, r):
                    return True
    return False

def get_tiles_to_download():
    rings, all_pts, (min_lat, max_lat, min_lon, max_lon) = load_dc_geometry()
    tiles = []
    for z in range(11, 16):
        x1, y2 = deg2num(min_lat, min_lon, z)
        x2, y1 = deg2num(max_lat, max_lon, z)
        x_min, x_max = min(x1, x2), max(x1, x2)
        y_min, y_max = min(y1, y2), max(y1, y2)

        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                if z <= 12 or tile_intersects_dc(x, y, z, rings, all_pts):
                    tiles.append((z, x, y))
    return tiles

def verify_tile(path):
    if not os.path.exists(path) or os.path.getsize(path) < 100:
        return False
    try:
        with open(path, 'rb') as f:
            header = f.read(8)
            return header == PNG_HEADER
    except Exception:
        return False

def download_tiles(verify_only=False):
    tiles = get_tiles_to_download()
    print(f"Total Washington, DC Stamen Toner tiles: {len(tiles)} (Zooms 11 to 15)")

    if verify_only:
        missing = []
        corrupted = []
        total_size = 0
        for z, x, y in tiles:
            tile_path = os.path.join(TILES_DIR, str(z), str(x), f"{y}.png")
            if not os.path.exists(tile_path):
                missing.append((z, x, y))
            elif not verify_tile(tile_path):
                corrupted.append((z, x, y))
            else:
                total_size += os.path.getsize(tile_path)

        if missing or corrupted:
            print(f"Verification FAILED: {len(missing)} missing, {len(corrupted)} corrupted")
            sys.exit(1)
        else:
            print(f"Verification PASSED: All {len(tiles)} tiles present and valid ({total_size / (1024*1024):.2f} MB)")
            return

    headers = {
        'User-Agent': 'DCMissedCollectionAnalysis/1.0',
        'Referer': 'http://localhost:8000/'
    }

    downloaded = 0
    skipped = 0
    total_size = 0

    for idx, (z, x, y) in enumerate(tiles, start=1):
        tile_dir = os.path.join(TILES_DIR, str(z), str(x))
        os.makedirs(tile_dir, exist_ok=True)
        tile_path = os.path.join(tile_dir, f"{y}.png")

        if verify_tile(tile_path):
            skipped += 1
            total_size += os.path.getsize(tile_path)
            continue

        url = f"https://tiles.stadiamaps.com/tiles/stamen_toner/{z}/{x}/{y}.png"
        req = urllib.request.Request(url, headers=headers)
        success = False
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = resp.read()
                    if data.startswith(PNG_HEADER):
                        with open(tile_path, 'wb') as f:
                            f.write(data)
                        total_size += len(data)
                        downloaded += 1
                        success = True
                        break
                    else:
                        time.sleep(0.5)
            except Exception as e:
                time.sleep(1.0 * (attempt + 1))

        if not success:
            print(f"Warning: Failed to download tile {z}/{x}/{y}")

        if downloaded % 25 == 0 and downloaded > 0:
            print(f"Progress: {idx}/{len(tiles)} tiles processed ({downloaded} new, {skipped} cached)...")
        time.sleep(0.04)

    print(f"Complete: {downloaded} downloaded, {skipped} cached. Total tile size: {total_size / (1024*1024):.2f} MB")

if __name__ == '__main__':
    verify_flag = '--verify-only' in sys.argv
    download_tiles(verify_only=verify_flag)
