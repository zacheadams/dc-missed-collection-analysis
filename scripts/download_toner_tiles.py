#!/usr/bin/env python3
"""
Downloads and packages Stamen Toner (Light) and Stamen Toner Blacklite (Dark)
tiles for Washington, DC locally.
Tiles are strictly subsetted to the District of Columbia boundary polygon
for Zooms 11 through 15, eliminating runtime external dependencies and Stadia API keys.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spatial_utils import is_point_in_ring, is_point_in_poly, get_poly_rings_list, get_bbox, anc_sort_key
import sys
import json
import math
import time
import shutil
import urllib.request
import concurrent.futures

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TILES_DIR = os.path.join(BASE_DIR, 'tiles')
LIGHT_DIR = os.path.join(TILES_DIR, 'light')
BLACKLITE_DIR = os.path.join(TILES_DIR, 'blacklite')
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

def get_tiles_to_download():
    rings, all_pts, (min_lat, max_lat, min_lon, max_lon) = load_dc_geometry()

    # Build spatial index grid for points
    from collections import defaultdict
    grid = defaultdict(list)
    grid_size = 0.02
    for px, py in all_pts:
        gx = int(px / grid_size)
        gy = int(py / grid_size)
        grid[(gx, gy)].append((px, py))

    # Ring bounding boxes
    ring_bboxes = []
    for r in rings:
        rx = [p[0] for p in r]
        ry = [p[1] for p in r]
        ring_bboxes.append((min(rx), max(rx), min(ry), max(ry), r))

    def fast_tile_intersects_dc(x, y, z):
        nw_lat, nw_lon = num2deg(x, y, z)
        se_lat, se_lon = num2deg(x + 1, y + 1, z)
        tile_min_lat, tile_max_lat = se_lat, nw_lat
        tile_min_lon, tile_max_lon = nw_lon, se_lon

        # Check grid for points inside tile
        gx_min = int(tile_min_lon / grid_size)
        gx_max = int(tile_max_lon / grid_size)
        gy_min = int(tile_min_lat / grid_size)
        gy_max = int(tile_max_lat / grid_size)
        for gx in range(gx_min, gx_max + 1):
            for gy in range(gy_min, gy_max + 1):
                for px, py in grid.get((gx, gy), []):
                    if tile_min_lon <= px <= tile_max_lon and tile_min_lat <= py <= tile_max_lat:
                        return True

        # Check center and corners in rings
        pts_to_test = [
            ((tile_min_lon + tile_max_lon) / 2, (tile_min_lat + tile_max_lat) / 2),
            (tile_min_lon, tile_min_lat),
            (tile_max_lon, tile_min_lat),
            (tile_min_lon, tile_max_lat),
            (tile_max_lon, tile_max_lat)
        ]
        for min_rx, max_rx, min_ry, max_ry, r in ring_bboxes:
            if tile_max_lon < min_rx or tile_min_lon > max_rx or tile_max_lat < min_ry or tile_min_lat > max_ry:
                continue
            for tx, ty in pts_to_test:
                if is_point_in_ring(tx, ty, r):
                    return True
        return False

    tiles = []
    for z in range(11, 18):
        x1, y2 = deg2num(min_lat, min_lon, z)
        x2, y1 = deg2num(max_lat, max_lon, z)
        x_min, x_max = min(x1, x2), max(x1, x2)
        y_min, y_max = min(y1, y2), max(y1, y2)

        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                if z <= 12 or fast_tile_intersects_dc(x, y, z):
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

def migrate_existing_light_tiles():
    # If tiles were stored directly in tiles/{z}/{x}/{y}.png, migrate them to tiles/light/{z}/{x}/{y}.png
    for z in range(11, 18):
        src_z = os.path.join(TILES_DIR, str(z))
        if os.path.exists(src_z) and os.path.isdir(src_z):
            dst_z = os.path.join(LIGHT_DIR, str(z))
            os.makedirs(os.path.dirname(dst_z), exist_ok=True)
            if not os.path.exists(dst_z):
                shutil.move(src_z, dst_z)
            else:
                shutil.rmtree(src_z)

def download_set(style_name, target_dir, tiles, verify_only=False):
    print(f"\nProcessing {style_name} tiles in {target_dir} ({len(tiles)} tiles)...")
    if verify_only:
        missing = []
        corrupted = []
        total_size = 0
        for z, x, y in tiles:
            tile_path = os.path.join(target_dir, str(z), str(x), f"{y}.png")
            if not os.path.exists(tile_path):
                missing.append((z, x, y))
            elif not verify_tile(tile_path):
                corrupted.append((z, x, y))
            else:
                total_size += os.path.getsize(tile_path)

        if missing or corrupted:
            print(f" - Verification FAILED: {len(missing)} missing, {len(corrupted)} corrupted")
            return False
        else:
            print(f" - Verification PASSED: All {len(tiles)} tiles present and valid ({total_size / (1024*1024):.2f} MB)")
            return True

    headers = {
        'User-Agent': 'DCMissedCollectionAnalysis/1.0',
        'Referer': 'http://localhost:8000/'
    }

    import urllib.error

    def fetch_tile(item):
        z, x, y = item
        tile_dir = os.path.join(target_dir, str(z), str(x))
        os.makedirs(tile_dir, exist_ok=True)
        tile_path = os.path.join(tile_dir, f"{y}.png")

        if verify_tile(tile_path):
            return ('skipped', os.path.getsize(tile_path))

        url = f"https://tiles.stadiamaps.com/tiles/{style_name}/{z}/{x}/{y}.png"
        req = urllib.request.Request(url, headers=headers)
        for attempt in range(5):
            try:
                time.sleep(0.015)
                with urllib.request.urlopen(req, timeout=12) as resp:
                    data = resp.read()
                    if data.startswith(PNG_HEADER):
                        with open(tile_path, 'wb') as f:
                            f.write(data)
                        return ('downloaded', len(data))
                    else:
                        time.sleep(0.3)
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    time.sleep(2.0 * (attempt + 1))
                else:
                    time.sleep(0.5 * (attempt + 1))
            except Exception:
                time.sleep(0.5 * (attempt + 1))
        return ('failed', 0)

    downloaded = 0
    skipped = 0
    failed = 0
    total_size = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        for status, size in executor.map(fetch_tile, tiles):
            if status == 'downloaded':
                downloaded += 1
                total_size += size
                if downloaded % 250 == 0:
                    print(f" ... downloaded {downloaded} new tiles ({total_size / (1024*1024):.2f} MB)")
            elif status == 'skipped':
                skipped += 1
                total_size += size
            elif status == 'failed':
                failed += 1

    print(f"Complete: {downloaded} downloaded, {skipped} cached, {failed} failed. Total size: {total_size / (1024*1024):.2f} MB")
    return failed == 0

def main():
    verify_flag = '--verify-only' in sys.argv
    migrate_existing_light_tiles()
    tiles = get_tiles_to_download()
    print(f"Washington, DC tile set: {len(tiles)} tiles (Zooms 11 to 17)")

    ok_light = download_set('stamen_toner', LIGHT_DIR, tiles, verify_only=verify_flag)
    ok_blacklite = download_set('stamen_toner_blacklite', BLACKLITE_DIR, tiles, verify_only=verify_flag)

    if verify_flag and (not ok_light or not ok_blacklite):
        sys.exit(1)

if __name__ == '__main__':
    main()
