#!/usr/bin/env python3
"""
Compiles the Dedicated Interactive Map Application (map.html).
Features:
- Local Stamen Toner (Light) and Stamen Toner Blacklite (Dark) basemaps cached offline
- Browser-default light/dark theme with manual switcher and local persistence
- Single-hue relative intensity color ramps for Trash (Red), Recycling (Green), Combined (Blue)
- Dual analytic period toggle: 180-Day (Default) vs 30-Day
- Permanent Ward boundary overlays
- Renamed '311 Requests' layer and streamlined controls
- Primary monospace font (IBM Plex Mono)
- Strictly zero emojis across UI and code
- Context-aware PDF and PNG map exports
"""

import os
import sys
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
map_data_path = os.path.join(BASE_DIR, 'data', 'dc_map_data_v2.json')
route_stats_path = os.path.join(BASE_DIR, 'data', 'route_180d_stats.json')
route_areas_path = os.path.join(BASE_DIR, 'data', 'route_areas.json')

with open(map_data_path, 'r', encoding='utf-8') as f:
    map_data = json.load(f)

if 'trash_routes_lines' not in map_data:
    trash_lines_path = os.path.join(BASE_DIR, 'data', 'dc_trash_routes_lines.geojson')
    if os.path.exists(trash_lines_path):
        with open(trash_lines_path, 'r', encoding='utf-8') as f:
            map_data['trash_routes_lines'] = json.load(f)

if 'recycle_routes_lines' not in map_data:
    rec_lines_path = os.path.join(BASE_DIR, 'data', 'dc_recycle_routes_lines.geojson')
    if os.path.exists(rec_lines_path):
        with open(rec_lines_path, 'r', encoding='utf-8') as f:
            map_data['recycle_routes_lines'] = json.load(f)

route_areas = {}
if os.path.exists(route_areas_path):
    with open(route_areas_path, 'r', encoding='utf-8') as f:
        route_areas = json.load(f)

# Synchronize polygon route features with latest route_areas data
has_map_data_changes = False
for feat in map_data.get('trash_routes', {}).get('features', []):
    rid = feat.get('properties', {}).get('route_area')
    if rid and rid in route_areas.get('trash_routes', {}):
        ra = route_areas['trash_routes'][rid]
        for prop in ['ward', 'neighborhoods', 'ancs', 'area_desc']:
            if feat['properties'].get(prop) != ra.get(prop, ''):
                feat['properties'][prop] = ra.get(prop, '')
                has_map_data_changes = True

for feat in map_data.get('recycle_routes', {}).get('features', []):
    rid = feat.get('properties', {}).get('route')
    if rid and rid in route_areas.get('recycle_routes', {}):
        ra = route_areas['recycle_routes'][rid]
        for prop in ['ward', 'neighborhoods', 'ancs', 'area_desc']:
            if feat['properties'].get(prop) != ra.get(prop, ''):
                feat['properties'][prop] = ra.get(prop, '')
                has_map_data_changes = True

if has_map_data_changes:
    with open(map_data_path, 'w', encoding='utf-8') as f:
        json.dump(map_data, f, separators=(',', ':'))

with open(route_stats_path, 'r', encoding='utf-8') as f:
    route_stats_raw = json.load(f)

trash_days_map = {f['properties']['route_area']: f['properties'].get('days') for f in map_data.get('trash_routes', {}).get('features', []) if f.get('properties', {}).get('route_area')}
recycle_days_map = {f['properties']['route']: f['properties'].get('day') for f in map_data.get('recycle_routes', {}).get('features', []) if f.get('properties', {}).get('route')}

route_stats_lookup = {}
for r in route_stats_raw.get('trash_routes', []):
    r_copy = dict(r)
    aid = r_copy.get('route_id')
    ra = route_areas.get('trash_routes', {}).get(aid, {})
    area_sq_mi = ra.get('area_sq_mi', 0.0)
    r_copy['area_sq_mi'] = area_sq_mi
    r_copy['density'] = round(r_copy['total'] / area_sq_mi, 1) if area_sq_mi > 0 else 0.0
    if ra.get('ward'):
        r_copy['ward'] = ra.get('ward')
    if ra.get('neighborhoods'):
        r_copy['neighborhoods'] = ra.get('neighborhoods')
    if ra.get('ancs'):
        r_copy['ancs'] = ra.get('ancs')
    if ra.get('area_desc'):
        r_copy['area_desc'] = ra.get('area_desc')
    col_day = trash_days_map.get(aid) or (r_copy.get('schedule') if r_copy.get('schedule') != 'Unassigned' else None)
    if col_day:
        r_copy['schedule'] = col_day
        r_copy['day'] = col_day
    route_stats_lookup['trash_' + str(aid)] = r_copy

for r in route_stats_raw.get('recycle_routes', []):
    r_copy = dict(r)
    aid = r_copy.get('route_id')
    ra = route_areas.get('recycle_routes', {}).get(aid, {})
    area_sq_mi = ra.get('area_sq_mi', 0.0)
    r_copy['area_sq_mi'] = area_sq_mi
    r_copy['density'] = round(r_copy['total'] / area_sq_mi, 1) if area_sq_mi > 0 else 0.0
    if ra.get('ward'):
        r_copy['ward'] = ra.get('ward')
    if ra.get('neighborhoods'):
        r_copy['neighborhoods'] = ra.get('neighborhoods')
    if ra.get('ancs'):
        r_copy['ancs'] = ra.get('ancs')
    if ra.get('area_desc'):
        r_copy['area_desc'] = ra.get('area_desc')
    col_day = recycle_days_map.get(aid) or (r_copy.get('schedule') if r_copy.get('schedule') != 'Unassigned' else None)
    if col_day:
        r_copy['schedule'] = col_day
        r_copy['day'] = col_day
    route_stats_lookup['recycle_' + str(aid)] = r_copy

# Incorporate line routes directly into route_stats_lookup with line-specific keys to prevent clobbering polygon stats
for feat in map_data.get('trash_routes_lines', {}).get('features', []):
    p = feat.get('properties', {})
    rid = p.get('route')
    if rid:
        pid = p.get('polygon_route_id')
        p_stats = route_stats_lookup.get('trash_' + str(pid), {})
        total = p.get('total', p_stats.get('total', 0))
        area_sq = p.get('area_sq_mi', p_stats.get('area_sq_mi', 0.0))
        line_entry = {
            'route_id': rid,
            'type': 'Trash',
            'route_name': f"Trash Route {rid}",
            'schedule': p.get('day', p_stats.get('schedule', 'Scheduled')),
            'service_area': p_stats.get('service_area', 'Standard'),
            'runs_per_week': p_stats.get('runs_per_week', 1),
            'status': 'Active',
            'ward': p.get('ward', p_stats.get('ward', '')),
            'neighborhoods': p.get('neighborhoods', p_stats.get('neighborhoods', '')),
            'ancs': p.get('ancs', p_stats.get('ancs', '')),
            'area_desc': p.get('area_desc', p_stats.get('area_desc', '')),
            'total': total,
            'unique_addrs': p.get('unique_addrs', p_stats.get('unique_addrs', 0)),
            'repeat_rate': p.get('repeat_rate', p_stats.get('repeat_rate', 0.0)),
            'area_sq_mi': area_sq,
            'density': round(total / area_sq, 1) if area_sq > 0 else 0.0,
            'point_count': p.get('point_count', 0),
            'segment_count': p.get('segment_count', 0)
        }
        route_stats_lookup['trash_line_' + str(rid)] = line_entry
        if ('trash_' + str(rid)) not in route_stats_lookup:
            route_stats_lookup['trash_' + str(rid)] = line_entry

for feat in map_data.get('recycle_routes_lines', {}).get('features', []):
    p = feat.get('properties', {})
    rid = p.get('route')
    if rid:
        p_stats = route_stats_lookup.get('recycle_' + str(rid), {})
        total = p.get('total', p_stats.get('total', 0))
        area_sq = p.get('area_sq_mi', p_stats.get('area_sq_mi', 0.0))
        rec_entry = {
            'route_id': rid,
            'type': 'Recycling',
            'route_name': f"Recycling Route {rid}",
            'schedule': p.get('day', p_stats.get('schedule', 'Scheduled')),
            'service_area': p_stats.get('service_area', 'Standard'),
            'runs_per_week': 1,
            'status': 'Active',
            'ward': p.get('ward', p_stats.get('ward', '')),
            'neighborhoods': p.get('neighborhoods', p_stats.get('neighborhoods', '')),
            'ancs': p.get('ancs', p_stats.get('ancs', '')),
            'area_desc': p.get('area_desc', p_stats.get('area_desc', '')),
            'total': total,
            'unique_addrs': p.get('unique_addrs', p_stats.get('unique_addrs', 0)),
            'repeat_rate': p.get('repeat_rate', p_stats.get('repeat_rate', 0.0)),
            'area_sq_mi': area_sq,
            'density': round(total / area_sq, 1) if area_sq > 0 else 0.0,
            'point_count': p.get('point_count', 0),
            'segment_count': p.get('segment_count', 0)
        }
        route_stats_lookup['recycle_line_' + str(rid)] = rec_entry
        if rid.startswith('R'):
            route_stats_lookup['recycle_line_' + str(rid[1:])] = rec_entry
        if ('recycle_' + str(rid)) not in route_stats_lookup:
            route_stats_lookup['recycle_' + str(rid)] = rec_entry
        if rid.startswith('R') and ('recycle_' + str(rid[1:])) not in route_stats_lookup:
            route_stats_lookup['recycle_' + str(rid[1:])] = rec_entry

route_stats_json = json.dumps(route_stats_lookup, separators=(',', ':'))

ward_council = {
    1: "Brianne Nadeau",
    2: "Brooke Pinto",
    3: "Matthew Frumin",
    4: "Janeese Lewis George",
    5: "Zachary Parker",
    6: "Charles Allen",
    7: "Wendell Felder",
    8: "Trayon White, Sr."
}
ward_council_json = json.dumps(ward_council)


html_page = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Missed Collections • The Map</title>

  <!-- Local Vendored Leaflet CSS -->
  <link rel="stylesheet" href="assets/vendor/leaflet/leaflet.css" />

  <!-- Google Fonts: IBM Plex Mono -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">

  <!-- Local Vendored Export Libraries -->
  <script src="assets/vendor/jspdf/jspdf.umd.min.js"></script>
  <script src="assets/vendor/html2canvas/html2canvas.min.js"></script>

  <style>
    :root {{
      --font-mono: 'IBM Plex Mono', monospace;

      /* Light Theme (Default) */
      --bg-page: #f8fafc;
      --bg-surface: #ffffff;
      --bg-panel: rgba(255, 255, 255, 0.95);
      --bg-input: #f1f5f9;
      --border: #d4d4d8;
      --border-dark: #18181b;
      --border-focus: #09090b;
      --text-main: #09090b;
      --text-muted: #52525b;
      --text-dim: #71717a;
      --accent: #2563eb;
      --accent-hover: #1d4ed8;
      --trash-color: #dc2626;
      --recycle-color: #16a34a;
      --combined-color: #2563eb;
      --ward-boundary: #7c3aed;
      --card-shadow: 0 10px 25px rgba(0, 0, 0, 0.08);
      --badge-bg: rgba(37, 99, 235, 0.08);
      --badge-border: rgba(37, 99, 235, 0.25);
    }}

    [data-theme="dark"] {{
      /* Dark Theme (Stamen Toner Blacklite) */
      --bg-page: #09090b;
      --bg-surface: #121215;
      --bg-panel: rgba(18, 18, 21, 0.95);
      --bg-input: #18181b;
      --border: #27272a;
      --border-dark: #3f3f46;
      --border-focus: #f4f4f5;
      --text-main: #f4f4f5;
      --text-muted: #a1a1aa;
      --text-dim: #71717a;
      --accent: #38bdf8;
      --accent-hover: #0284c7;
      --trash-color: #ef4444;
      --recycle-color: #22c55e;
      --combined-color: #38bdf8;
      --ward-boundary: #c084fc;
      --card-shadow: 0 16px 36px rgba(0, 0, 0, 0.5);
      --badge-bg: rgba(56, 189, 248, 0.12);
      --badge-border: rgba(56, 189, 248, 0.3);
    }}

    *, *::before, *::after {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: inherit;
    }}

    input, button, select, textarea, optgroup {{
      font-family: var(--font-mono) !important;
    }}

    .leaflet-container, .leaflet-popup, .leaflet-control, .leaflet-tooltip {{
      font-family: var(--font-mono) !important;
    }}

    body {{
      background-color: var(--bg-page);
      color: var(--text-main);
      font-family: var(--font-mono);
      line-height: 1.5;
      -webkit-font-smoothing: antialiased;
      overflow-x: hidden;
    }}

    /* Keyword Color Classes */
    .kw-trash {{
      color: var(--trash-color);
      font-weight: 700;
    }}

    .kw-recycle {{
      color: var(--recycle-color);
      font-weight: 700;
    }}

    .kw-combined {{
      color: var(--combined-color);
      font-weight: 700;
    }}

    /* Top Navigation Bar */
    .site-nav {{
      background: var(--bg-panel);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: 0;
      z-index: 1000;
      padding: 10px 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      transition: background 0.2s, border-color 0.2s;
    }}

    .nav-brand {{
      display: flex;
      flex-direction: column;
    }}

    .nav-title {{
      font-size: 14px;
      font-weight: 800;
      color: var(--text-main);
      letter-spacing: -0.01em;
    }}

    .nav-subtitle {{
      font-size: 11px;
      color: var(--text-muted);
    }}

    .nav-links {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}

    .nav-link {{
      color: var(--text-muted);
      text-decoration: none;
      font-size: 12px;
      font-weight: 600;
      padding: 5px 10px;
      border-radius: 2px;
      border: 1px solid transparent;
      transition: all 0.15s ease;
    }}

    .nav-link:hover {{
      color: var(--text-main);
      border-color: var(--border);
      background: var(--bg-input);
    }}

    .nav-link.active {{
      color: var(--text-main);
      background: var(--badge-bg);
      border-color: var(--badge-border);
      font-weight: 700;
    }}

    .btn-action {{
      background: var(--bg-surface);
      border: 1px solid var(--border);
      color: var(--text-main);
      padding: 5px 10px;
      border-radius: 2px;
      font-size: 11px;
      font-weight: 700;
      cursor: pointer;
      font-family: var(--font-mono);
      transition: all 0.15s ease;
    }}

    .btn-action:hover {{
      border-color: var(--text-main);
      background: var(--bg-input);
    }}

    /* Main Full-Viewport Workspace */
    .map-workspace {{
      position: relative;
      width: 100vw;
      height: calc(100vh - 54px);
      overflow: hidden;
    }}

    #map {{
      width: 100%;
      height: 100%;
      background: var(--bg-page);
    }}

    /* Floating Left Control Panel */
    .control-panel {{
      position: absolute;
      top: 14px;
      left: 14px;
      width: 320px;
      background: var(--bg-panel);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border);
      border-radius: 2px;
      padding: 14px;
      z-index: 500;
      box-shadow: var(--card-shadow);
      transition: background 0.2s, border-color 0.2s;
    }}

    .panel-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
      padding-bottom: 6px;
      border-bottom: 1px solid var(--border);
    }}

    .panel-title {{
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--text-main);
    }}

    .panel-tag {{
      background: var(--badge-bg);
      color: var(--text-main);
      border: 1px solid var(--badge-border);
      padding: 2px 6px;
      border-radius: 2px;
      font-size: 10px;
      font-weight: 700;
    }}

    /* Period Toggle Group */
    .period-section {{
      margin-bottom: 10px;
    }}

    .period-label {{
      font-size: 10px;
      text-transform: uppercase;
      font-weight: 700;
      color: var(--text-dim);
      margin-bottom: 4px;
      display: block;
    }}

    .period-toggle-group {{
      display: flex;
      gap: 4px;
      background: var(--bg-input);
      padding: 3px;
      border-radius: 2px;
      border: 1px solid var(--border);
    }}

    .period-btn {{
      flex: 1;
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 5px 4px;
      font-size: 11px;
      font-weight: 700;
      border-radius: 2px;
      cursor: pointer;
      font-family: var(--font-mono);
      transition: all 0.15s ease;
      text-align: center;
    }}

    .period-btn.active {{
      background: var(--bg-surface);
      color: var(--text-main);
      border: 1px solid var(--border);
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }}

    /* Hierarchy Dropdowns */
    .hierarchy-container {{
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-bottom: 10px;
    }}

    .hierarchy-row {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .hierarchy-label {{
      width: 44px;
      font-size: 10px;
      font-weight: 700;
      color: var(--text-dim);
      text-transform: uppercase;
    }}

    .hierarchy-select {{
      flex: 1;
      background: var(--bg-surface);
      border: 1px solid var(--border);
      color: var(--text-main);
      padding: 5px 8px;
      border-radius: 2px;
      font-size: 11px;
      font-family: var(--font-mono);
    }}

    .hierarchy-select:focus {{
      outline: none;
      border-color: var(--border-focus);
    }}

    .hierarchy-select:disabled {{
      opacity: 0.4;
      cursor: not-allowed;
    }}

    /* Search Box */
    .search-box {{
      margin-bottom: 10px;
    }}

    .search-box input {{
      width: 100%;
      background: var(--bg-surface);
      border: 1px solid var(--border);
      color: var(--text-main);
      padding: 6px 8px;
      border-radius: 2px;
      font-size: 11px;
      font-family: var(--font-mono);
    }}

    .search-box input:focus {{
      outline: none;
      border-color: var(--border-focus);
    }}

    /* Metric Switcher */
    .metric-toggle-group {{
      display: flex;
      gap: 4px;
      background: var(--bg-input);
      padding: 3px;
      border-radius: 2px;
      border: 1px solid var(--border);
      margin-bottom: 10px;
    }}

    .metric-btn {{
      flex: 1;
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 5px 4px;
      font-size: 10px;
      font-weight: 700;
      border-radius: 2px;
      cursor: pointer;
      font-family: var(--font-mono);
      transition: all 0.15s ease;
      text-align: center;
      line-height: 1.25;
    }}

    .metric-btn.active {{
      background: var(--bg-surface);
      color: var(--text-main);
      border: 1px solid var(--border);
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }}

    /* Layer Controls */
    .layer-controls {{
      display: flex;
      flex-direction: column;
      gap: 6px;
      padding-top: 8px;
      border-top: 1px solid var(--border);
    }}

    .checkbox-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 11px;
      color: var(--text-muted);
      cursor: pointer;
    }}

    .checkbox-row span {{
      display: flex;
      align-items: center;
      gap: 6px;
    }}

    .badge-route {{
      width: 8px;
      height: 8px;
      border-radius: 2px;
      display: inline-block;
    }}


    /* Floating District Inspector (Right Side) */
    .inspector-panel {{
      position: absolute;
      top: 14px;
      right: 14px;
      width: 320px;
      background: var(--bg-panel);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border);
      border-radius: 2px;
      padding: 14px;
      z-index: 500;
      box-shadow: var(--card-shadow);
      transition: background 0.2s, border-color 0.2s;
    }}

    .inspector-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 8px;
      padding-bottom: 6px;
      border-bottom: 1px solid var(--border);
    }}

    .inspector-title {{
      font-size: 15px;
      font-weight: 800;
      color: var(--text-main);
      letter-spacing: -0.01em;
    }}

    .inspector-sub {{
      font-size: 10px;
      color: var(--text-dim);
    }}

    .inspector-stat-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px;
      margin-bottom: 10px;
    }}

    .stat-tile {{
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 2px;
      padding: 6px 8px;
    }}

    .stat-tile-lbl {{
      font-size: 9px;
      color: var(--text-dim);
      text-transform: uppercase;
      font-weight: 700;
    }}

    .stat-tile-val {{
      font-size: 16px;
      font-weight: 800;
      color: var(--text-main);
    }}

    .inspector-details {{
      font-size: 11px;
      color: var(--text-muted);
      line-height: 1.45;
    }}

    .inspector-route-box {{
      margin-top: 8px;
      padding-top: 6px;
      border-top: 1px solid var(--border);
    }}

    /* Floating Legend */
    .legend-panel {{
      position: absolute;
      bottom: 20px;
      left: 14px;
      background: var(--bg-panel);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border);
      border-radius: 2px;
      padding: 8px 12px;
      z-index: 500;
      font-size: 10px;
      box-shadow: var(--card-shadow);
    }}

    .legend-title {{
      font-weight: 700;
      color: var(--text-main);
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin-bottom: 5px;
    }}

    .legend-scale {{
      display: flex;
      align-items: center;
      gap: 2px;
    }}

    .scale-box {{
      width: 24px;
      height: 10px;
      border-radius: 2px;
      border: 1px solid rgba(0, 0, 0, 0.15);
    }}

    .scale-labels {{
      display: flex;
      justify-content: space-between;
      color: var(--text-dim);
      font-size: 9px;
      margin-top: 3px;
    }}

    /* Leaflet Tooltips */
    .leaflet-tooltip-smd {{
      background: var(--bg-panel) !important;
      border: 1px solid var(--border-dark) !important;
      color: var(--text-main) !important;
      border-radius: 2px !important;
      padding: 6px 10px !important;
      font-family: var(--font-mono) !important;
      box-shadow: var(--card-shadow) !important;
    }}

    .leaflet-control-attribution {{
      background: var(--bg-panel) !important;
      backdrop-filter: blur(8px);
      color: var(--text-dim) !important;
      border: 1px solid var(--border) !important;
      border-radius: 2px !important;
      padding: 3px 8px !important;
      font-size: 10px !important;
      font-family: var(--font-mono) !important;
      margin: 0 10px 10px 0 !important;
      box-shadow: var(--card-shadow) !important;
    }}

    .leaflet-control-attribution a {{
      color: var(--accent) !important;
      text-decoration: none !important;
    }}

    .leaflet-control-attribution a:hover {{
      text-decoration: underline !important;
    }}

    /* Mobile Responsive Layout and Touch Handling */
    .sheet-handle {{
      display: none;
    }}

    .mobile-toggle-indicator,
    .mobile-inspector-toggle {{
      display: none;
    }}

    @media (max-width: 768px) {{
      .site-nav {{
        padding: 8px 12px;
        flex-wrap: wrap;
        gap: 6px;
      }}
      .nav-subtitle {{
        display: none;
      }}
      .nav-links {{
        width: 100%;
        overflow-x: auto;
        padding-bottom: 2px;
        gap: 6px;
        -webkit-overflow-scrolling: touch;
      }}
      .nav-link, .btn-action {{
        font-size: 11px;
        padding: 5px 8px;
        white-space: nowrap;
        flex-shrink: 0;
      }}
      .map-workspace {{
        height: calc(100vh - 84px);
      }}
      .control-panel {{
        top: 8px;
        left: 8px;
        right: 8px;
        width: auto;
        padding: 10px 12px;
        border-radius: 2px;
        max-height: calc(100vh - 160px);
        overflow-y: auto;
        -webkit-overflow-scrolling: touch;
      }}
      .panel-header {{
        cursor: pointer;
        margin-bottom: 0;
        padding-bottom: 0;
        border-bottom: none;
      }}
      .control-panel.is-expanded .panel-header {{
        margin-bottom: 10px;
        padding-bottom: 6px;
        border-bottom: 1px solid var(--border);
      }}
      .mobile-toggle-indicator {{
        display: inline-block;
        font-size: 13px;
        color: var(--accent);
        font-weight: 800;
      }}
      .inspector-panel {{
        top: auto;
        bottom: 0;
        left: 0;
        right: 0;
        width: 100%;
        border-radius: 2px 2px 0 0;
        padding: 10px 14px 16px 14px;
        box-shadow: 0 -6px 24px rgba(0, 0, 0, 0.25);
        max-height: 48vh;
        overflow-y: auto;
        -webkit-overflow-scrolling: touch;
        z-index: 600;
      }}
      .sheet-handle {{
        display: block;
        width: 40px;
        height: 4px;
        border-radius: 2px;
        background: var(--border-dark);
        margin: 0 auto 8px auto;
        cursor: pointer;
      }}
      .inspector-header {{
        cursor: pointer;
      }}
      .mobile-inspector-toggle {{
        display: block;
        font-size: 13px;
        font-weight: 800;
        color: var(--accent);
      }}
      .legend-panel {{
        bottom: 64px;
        left: 8px;
        padding: 6px 10px;
        max-width: calc(100vw - 80px);
      }}
      .leaflet-bottom.leaflet-right {{
        bottom: 64px;
        right: 8px;
      }}
      .hierarchy-select, .period-btn, .metric-btn, #smd-search {{
        min-height: 38px;
        font-size: 12px;
      }}
      .checkbox-row {{
        padding: 6px 0;
        font-size: 12px;
      }}
    }}

    /* Map Data Loading Overlay */
    .map-loading-overlay {{
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      background: var(--bg-main);
      z-index: 2000;
      transition: opacity 0.2s ease-out;
    }}

    .map-loading-box {{
      border: 1px solid var(--border);
      padding: 20px 28px;
      background: var(--bg-card);
      border-radius: 2px;
      text-align: center;
      max-width: 480px;
      box-shadow: var(--card-shadow);
      font-family: 'IBM Plex Mono', monospace;
    }}

    .map-loading-title {{
      font-size: 14px;
      font-weight: 700;
      color: var(--text-main);
      margin-bottom: 8px;
    }}

    .map-loading-sub {{
      font-size: 12px;
      color: var(--text-dim);
      line-height: 1.5;
    }}
  </style>
</head>
<body>

  <!-- Top Navigation Bar -->
  <nav class="site-nav">
    <div class="nav-brand">
      <span class="nav-title">Missed Collections</span>
      <span class="nav-subtitle">Where—and why—are <span class="kw-trash">trash</span> and <span class="kw-recycle">recycling</span> pickups missed in DC?</span>
    </div>
    <div class="nav-links">
      <a href="index.html" class="nav-link">Index</a>
      <a href="map.html" class="nav-link active">The Map</a>
      <a href="report.html" class="nav-link">The Report</a>
      <button onclick="toggleTheme()" class="btn-action" id="theme-toggle-btn">Theme: Light</button>
      <button onclick="exportMapPdf()" class="btn-action">Export Map (PDF)</button>
      <button onclick="exportMapPng()" class="btn-action">Export Map (PNG)</button>
    </div>
  </nav>

  <!-- SVG Hatch Patterns for Catchment Routes -->
  <svg id="route-hatch-defs-svg" style="position: absolute; width: 0; height: 0; pointer-events: none;" aria-hidden="true">
    <defs>
      <!-- Trash Pattern (45 deg) -->
      <pattern id="hatch-trash" width="8" height="8" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
        <line x1="0" y1="0" x2="0" y2="8" stroke="#dc2626" stroke-width="1.8" />
      </pattern>
      <pattern id="hatch-trash-hover" width="8" height="8" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
        <rect width="8" height="8" fill="#dc2626" fill-opacity="0.18" />
        <line x1="0" y1="0" x2="0" y2="8" stroke="#dc2626" stroke-width="2.6" />
      </pattern>
      <pattern id="hatch-trash-dark" width="8" height="8" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
        <line x1="0" y1="0" x2="0" y2="8" stroke="#ef4444" stroke-width="1.8" />
      </pattern>
      <pattern id="hatch-trash-dark-hover" width="8" height="8" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
        <rect width="8" height="8" fill="#ef4444" fill-opacity="0.22" />
        <line x1="0" y1="0" x2="0" y2="8" stroke="#ef4444" stroke-width="2.6" />
      </pattern>

      <!-- Recycling Pattern (-45 deg) -->
      <pattern id="hatch-recycle" width="8" height="8" patternTransform="rotate(-45 0 0)" patternUnits="userSpaceOnUse">
        <line x1="0" y1="0" x2="0" y2="8" stroke="#16a34a" stroke-width="1.8" />
      </pattern>
      <pattern id="hatch-recycle-hover" width="8" height="8" patternTransform="rotate(-45 0 0)" patternUnits="userSpaceOnUse">
        <rect width="8" height="8" fill="#16a34a" fill-opacity="0.18" />
        <line x1="0" y1="0" x2="0" y2="8" stroke="#16a34a" stroke-width="2.6" />
      </pattern>
      <pattern id="hatch-recycle-dark" width="8" height="8" patternTransform="rotate(-45 0 0)" patternUnits="userSpaceOnUse">
        <line x1="0" y1="0" x2="0" y2="8" stroke="#22c55e" stroke-width="1.8" />
      </pattern>
      <pattern id="hatch-recycle-dark-hover" width="8" height="8" patternTransform="rotate(-45 0 0)" patternUnits="userSpaceOnUse">
        <rect width="8" height="8" fill="#22c55e" fill-opacity="0.22" />
        <line x1="0" y1="0" x2="0" y2="8" stroke="#22c55e" stroke-width="2.6" />
      </pattern>
    </defs>
  </svg>

  <!-- Full Viewport Map Workspace -->
  <div class="map-workspace" id="map-interactive">
    <div id="map"></div>

    <!-- Map Data Loading Overlay -->
    <div id="map-loading" class="map-loading-overlay">
      <div id="map-loading-box" class="map-loading-box">
        <div class="map-loading-title">Loading Spatial Data...</div>
        <div class="map-loading-sub" id="map-loading-detail">Fetching DC SMDs, Wards, and DPW Routes</div>
      </div>
    </div>

    <!-- Floating Left Control Panel -->
    <div class="control-panel" id="control-panel">
      <div class="panel-header" onclick="toggleMobilePanel('control')">
        <div style="display: flex; align-items: center; gap: 6px;">
          <span class="panel-title">Geographic Subset</span>
          <span class="mobile-toggle-indicator" id="ctrl-toggle-icon">▾</span>
        </div>
      </div>

      <div class="panel-collapsible-body" id="ctrl-panel-body">
        <!-- Analytic Period Switcher -->
        <div class="period-section">
          <span class="period-label">Analytic Period</span>
          <div class="period-toggle-group">
            <button class="period-btn active" id="btn-period-180d" onclick="setPeriod('180d')">180 Days</button>
            <button class="period-btn" id="btn-period-30d" onclick="setPeriod('30d')">30 Days</button>
          </div>
        </div>

        <div class="search-box">
          <input type="text" id="smd-search" placeholder="Search SMD (e.g. 5E03), ANC, or Ward..." oninput="handleSearch(this.value)">
        </div>

        <div class="hierarchy-container">
          <div class="hierarchy-row">
            <span class="hierarchy-label">Ward</span>
            <select class="hierarchy-select" id="ward-select" onchange="handleWardDropdown(this.value)">
              <option value="all">All Wards (Citywide)</option>
              <option value="1">Ward 1 • Brianne Nadeau</option>
              <option value="2">Ward 2 • Brooke Pinto</option>
              <option value="3">Ward 3 • Matthew Frumin</option>
              <option value="4">Ward 4 • Janeese Lewis George</option>
              <option value="5">Ward 5 • Zachary Parker</option>
              <option value="6">Ward 6 • Charles Allen</option>
              <option value="7">Ward 7 • Wendell Felder</option>
              <option value="8">Ward 8 • Trayon White, Sr.</option>
            </select>
          </div>

          <div class="hierarchy-row">
            <span class="hierarchy-label">ANC</span>
            <select class="hierarchy-select" id="anc-select" onchange="handleAncDropdown(this.value)" disabled>
              <option value="all">— Select Ward First —</option>
            </select>
          </div>

          <div class="hierarchy-row">
            <span class="hierarchy-label">SMD</span>
            <select class="hierarchy-select" id="smd-select" onchange="handleSmdDropdown(this.value)" disabled>
              <option value="all">— Select ANC First —</option>
            </select>
          </div>
        </div>

        <div class="metric-toggle-group">
          <button class="metric-btn active" id="btn-total" onclick="setMetric('total')"><span class="kw-combined">Combined</span><br>Requests</button>
          <button class="metric-btn" id="btn-trash" onclick="setMetric('trash')"><span class="kw-trash">Trash</span><br>Only</button>
          <button class="metric-btn" id="btn-recycling" onclick="setMetric('recycling')"><span class="kw-recycle">Recycling</span><br>Only</button>
        </div>

        <div class="layer-controls">
          <label class="checkbox-row">
            <span><span class="badge-route" id="marker-311-requests" style="background: var(--combined-color);"></span>311 Requests</span>
            <input type="checkbox" id="chk-smd" checked onchange="toggleSMDLayer(this.checked)">
          </label>
          <label class="checkbox-row">
            <span><span class="badge-route" style="background: repeating-linear-gradient(45deg, var(--trash-color), var(--trash-color) 2px, transparent 2px, transparent 4px); border: 1px solid var(--trash-color);"></span><span class="kw-trash">Trash</span> Routes (polygon)</span>
            <input type="checkbox" id="chk-trash-routes" onchange="toggleTrashRoutes(this.checked)">
          </label>
          <label class="checkbox-row">
            <span><span class="badge-route" style="background: repeating-linear-gradient(-45deg, var(--recycle-color), var(--recycle-color) 2px, transparent 2px, transparent 4px); border: 1px solid var(--recycle-color);"></span><span class="kw-recycle">Recycling</span> Routes (polygon)</span>
            <input type="checkbox" id="chk-recycle-routes" onchange="toggleRecycleRoutes(this.checked)">
          </label>
          <label class="checkbox-row">
            <span><span class="badge-route" style="background: var(--trash-color); height: 3px; border-radius: 1px; margin-top: 5px;"></span><span class="kw-trash">Trash</span> Routes (line)</span>
            <input type="checkbox" id="chk-trash-lines" onchange="toggleTrashLines(this.checked)">
          </label>
          <label class="checkbox-row">
            <span><span class="badge-route" style="background: var(--recycle-color); height: 3px; border-radius: 1px; margin-top: 5px;"></span><span class="kw-recycle">Recycling</span> Routes (line)</span>
            <input type="checkbox" id="chk-recycle-lines" onchange="toggleRecycleLines(this.checked)">
          </label>
        </div>

        <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--border);">
          <button id="btn-reset-default" class="btn-action" style="width: 100%; text-align: center; padding: 7px 10px; font-weight: 700; border-radius: 2px;" onclick="resetToDefault()">Reset to Default</button>
        </div>
      </div>
    </div>

    <!-- Floating Right Inspector Panel -->
    <div class="inspector-panel" id="inspector-panel">
      <div class="sheet-handle" onclick="toggleMobilePanel('inspector')"></div>
      <div class="inspector-header" onclick="toggleMobilePanel('inspector')">
        <div>
          <div class="inspector-title" id="insp-title">District of Columbia</div>
          <div class="inspector-sub" id="insp-sub">Citywide Performance Summary</div>
        </div>
        <div class="mobile-inspector-toggle" id="insp-toggle-icon">▴</div>
      </div>

      <div class="inspector-collapsible-body" id="insp-panel-body">
        <div class="inspector-stat-grid">
          <div class="stat-tile">
            <div class="stat-tile-lbl" id="insp-lbl-1">Selected Requests</div>
            <div class="stat-tile-val" id="insp-stat-total">0</div>
          </div>
          <div class="stat-tile">
            <div class="stat-tile-lbl" id="insp-lbl-2">Share of Volume</div>
            <div class="stat-tile-val" id="insp-stat-share">100%</div>
          </div>
          <div class="stat-tile">
            <div class="stat-tile-lbl" id="insp-lbl-3"><span class="kw-trash">Trash</span> (S0441)</div>
            <div class="stat-tile-val kw-trash" id="insp-stat-trash">0</div>
          </div>
          <div class="stat-tile">
            <div class="stat-tile-lbl" id="insp-lbl-4"><span class="kw-recycle">Recycling</span> (S0321)</div>
            <div class="stat-tile-val kw-recycle" id="insp-stat-rec">0</div>
          </div>
        </div>

        <div class="inspector-details" id="insp-details">
          Select any Single Member District or Ward on the map or use the dropdowns on the left to inspect localized performance, repeat rates, and DPW collection schedules.
        </div>

        <div class="inspector-route-box" id="insp-route-box" style="display: none;">
          <!-- Filled dynamically -->
        </div>
      </div>
    </div>

    <!-- Floating Legend Panel -->
    <div class="legend-panel">
      <div class="legend-title" id="legend-title"><span class="kw-combined">Combined</span> Requests (180 Days)</div>
      <div class="legend-scale" id="legend-scale">
        <!-- Scale boxes injected dynamically -->
      </div>
      <div class="scale-labels" id="legend-labels">
        <span>0</span>
        <span>Low</span>
        <span>High</span>
        <span>Hot Spot</span>
      </div>
    </div>

  </div>

  <!-- Local Vendored Leaflet JS -->
  <script src="assets/vendor/leaflet/leaflet.js"></script>

  <script>
    let MAP_DATA = null;
    const WARD_COUNCIL = {ward_council_json};
    const ROUTE_STATS = {route_stats_json};

    // State
    let selectedWardNum = null;
    let selectedAncId = null;
    let selectedSmdId = null;
    let currentMetric = 'total';
    let currentPeriod = '180d';
    let currentTheme = 'light';

    const trashRouteById = {{}};
    const recycleRouteById = {{}};
    const trashLineById = {{}};
    const recycleLineById = {{}};
    // Determine default theme from localStorage or system prefers-color-scheme
    const savedTheme = localStorage.getItem('dc_map_theme');
    if (savedTheme) {{
      currentTheme = savedTheme;
    }} else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {{
      currentTheme = 'dark';
    }}
    document.documentElement.setAttribute('data-theme', currentTheme);

    // Initialize Map
    const map = L.map('map', {{
      center: [38.9072, -77.01],
      zoom: 12,
      zoomControl: false,
      minZoom: 11,
      maxZoom: 17,
      scrollWheelZoom: true
    }});

    L.control.zoom({{ position: 'bottomright' }}).addTo(map);

    // Dedicated Map Panes
    map.createPane('tonerBasePane');
    map.getPane('tonerBasePane').style.zIndex = 200;

    map.createPane('maskPane');
    map.getPane('maskPane').style.zIndex = 260;

    map.createPane('wardPane');
    map.getPane('wardPane').style.zIndex = 320;

    map.createPane('smdPane');
    map.getPane('smdPane').style.zIndex = 380;

    map.createPane('routePane');
    map.getPane('routePane').style.zIndex = 420;

    map.createPane('routeLinePane');
    map.getPane('routeLinePane').style.zIndex = 430;

    function getTileUrl(theme) {{
      return theme === 'dark' ? 'tiles/blacklite/{{z}}/{{x}}/{{y}}.png' : 'tiles/light/{{z}}/{{x}}/{{y}}.png';
    }}

    // Basemap: Local Stamen Toner (Zooms 11 to 17)
    let baseTileLayer = L.tileLayer(getTileUrl(currentTheme), {{
      pane: 'tonerBasePane',
      minZoom: 11,
      maxNativeZoom: 17,
      maxZoom: 17,
      bounds: [[38.7916, -77.1198], [38.9960, -76.9091]],
      attribution: 'Tiles: Stamen Design (CC BY 3.0) • Data: OpenStreetMap (ODbL)'
    }}).addTo(map);

    map.attributionControl.setPrefix('<a href="https://leafletjs.com" target="_blank" rel="noopener">Leaflet</a>');

    /*
     * CENSUS TIGERWEB ALTERNATIVE BASEMAP:
     * To revert to U.S. Census TIGERweb basemaps, uncomment the two layers below:
     *
     * L.tileLayer('https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Transportation/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
     *   pane: 'tonerBasePane',
     *   maxZoom: 17,
     *   opacity: 0.95,
     *   attribution: 'U.S. Census Bureau TIGERweb'
     * }}).addTo(map);
     *
     * L.tileLayer('https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Hydro/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
     *   pane: 'tonerBasePane',
     *   maxZoom: 17,
     *   opacity: 0.75,
     *   interactive: false
     * }}).addTo(map);
     */

    let smdLayer = null;
    let wardLayer = null;
    let trashRoutesLayer = null;
    let recycleRoutesLayer = null;
    let trashLinesLayer = null;
    let recycleLinesLayer = null;
    let wardMaskLayer = null;
    let activeHoverLayer = null;

    // Tooltip
    const smdTooltip = L.tooltip({{
      sticky: true,
      direction: 'top',
      className: 'leaflet-tooltip-smd',
      offset: [0, -10]
    }});

    // Thresholds for dual periods
    const THRESHOLDS = {{
      '180d': {{
        total:     [0, 10, 25, 50, 80, 120, 160],
        trash:     [0,  8, 18, 35, 60,  90, 120],
        recycling: [0,  4, 10, 20, 35,  50,  70]
      }},
      '30d': {{
        total:     [0, 3, 7, 12, 18, 26, 36],
        trash:     [0, 2, 5,  9, 14, 20, 28],
        recycling: [0, 1, 3,  6,  9, 13, 18]
      }}
    }};

    // Single-hue relative intensity color ramps (Light to Dark / Deep)
    const PALETTES = {{
      total: [
        'rgba(191, 219, 254, 0.45)', // 0: tint
        '#bfdbfe',                    // low
        '#93c5fd',
        '#60a5fa',
        '#3b82f6',
        '#1d4ed8',
        '#172554'                     // deep navy blue
      ],
      trash: [
        'rgba(254, 202, 202, 0.45)', // 0: tint
        '#fecaca',                    // low
        '#f87171',
        '#ef4444',
        '#dc2626',
        '#b91c1c',
        '#7f1d1d'                     // deep dark crimson
      ],
      recycling: [
        'rgba(187, 247, 208, 0.45)', // 0: tint
        '#bbf7d0',                    // low
        '#86efac',
        '#4ade80',
        '#22c55e',
        '#16a34a',
        '#14532d'                     // deep dark forest green
      ]
    }};

    function getSmdMetric(p, metric, period) {{
      const mObj = period === '30d' ? p.metrics_30d : p.metrics_180d;
      if (mObj && mObj[metric] !== undefined) return mObj[metric];
      return p[metric] || 0;
    }}

    function getColor(val, metric) {{
      if (val <= 0) return currentTheme === 'dark' ? 'rgba(39, 39, 42, 0.3)' : 'rgba(241, 245, 249, 0.45)';
      const th = THRESHOLDS[currentPeriod][metric];
      const pal = PALETTES[metric];
      for (let i = th.length - 1; i >= 0; i--) {{
        if (val >= th[i]) return pal[i];
      }}
      return pal[0];
    }}

    function getStreamColor(metric) {{
      if (metric === 'trash') return currentTheme === 'dark' ? '#ef4444' : '#dc2626';
      if (metric === 'recycling') return currentTheme === 'dark' ? '#22c55e' : '#16a34a';
      return currentTheme === 'dark' ? '#38bdf8' : '#2563eb';
    }}

    function smdStyle(feature) {{
      const p = feature.properties;
      const val = getSmdMetric(p, currentMetric, currentPeriod);
      const isSelected = selectedSmdId === p.smd_id;
      const inAnc = selectedAncId === p.anc_id;
      const inWard = selectedWardNum === p.ward;

      const outlineColor = currentTheme === 'dark' ? '#27272a' : '#71717a';
      const streamColor = getStreamColor(currentMetric);

      if (selectedSmdId) {{
        if (isSelected) {{
          return {{
            fillColor: getColor(val, currentMetric),
            weight: 3.8,
            opacity: 1,
            color: streamColor,
            fillOpacity: 0.95
          }};
        }} else if (inWard) {{
          return {{
            fillColor: getColor(val, currentMetric),
            weight: 0.8,
            opacity: 0.6,
            color: streamColor,
            fillOpacity: 0.38
          }};
        }} else {{
          return {{
            fillColor: getColor(val, currentMetric),
            weight: 0.4,
            opacity: 0.15,
            color: outlineColor,
            fillOpacity: 0.08
          }};
        }}
      }}

      if (selectedAncId) {{
        if (inAnc) {{
          return {{
            fillColor: getColor(val, currentMetric),
            weight: 2.2,
            opacity: 0.95,
            color: streamColor,
            fillOpacity: val === 0 ? 0.35 : 0.80
          }};
        }} else {{
          return {{
            fillColor: getColor(val, currentMetric),
            weight: 0.4,
            opacity: 0.2,
            color: outlineColor,
            fillOpacity: 0.10
          }};
        }}
      }}

      if (selectedWardNum) {{
        if (inWard) {{
          return {{
            fillColor: getColor(val, currentMetric),
            weight: 1.2,
            opacity: 0.95,
            color: streamColor,
            fillOpacity: val === 0 ? 0.35 : 0.80
          }};
        }} else {{
          return {{
            fillColor: getColor(val, currentMetric),
            weight: 0.8,
            opacity: 0.85,
            color: currentTheme === 'dark' ? '#3f3f46' : '#52525b',
            fillOpacity: val === 0 ? 0.25 : 0.72
          }};
        }}
      }}

      return {{
        fillColor: getColor(val, currentMetric),
        weight: 0.8,
        opacity: 0.85,
        color: currentTheme === 'dark' ? '#3f3f46' : '#52525b',
        fillOpacity: val === 0 ? 0.25 : 0.72
      }};
    }}

    function wardStyle(feature) {{
      const isSelected = selectedWardNum === feature.properties.ward;
      return {{
        color: currentTheme === 'dark' ? '#ffffff' : '#000000',
        weight: isSelected ? 4.5 : 3.0,
        dashArray: '2, 5',
        lineCap: 'round',
        fill: false,
        interactive: false
      }};
    }}

    function updateWardMask() {{
      if (wardMaskLayer) {{
        map.removeLayer(wardMaskLayer);
        wardMaskLayer = null;
      }}
    }}

    // Spatial Index for Route Overlaps
    let trashRouteIndex = [];
    let recycleRouteIndex = [];

    function isPointInRing(x, y, ring) {{
      let inside = false;
      const n = ring.length;
      for (let i = 0; i < n; i++) {{
        const j = (i - 1 + n) % n;
        const xi = ring[i][0], yi = ring[i][1];
        const xj = ring[j][0], yj = ring[j][1];
        if (((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) {{
          inside = !inside;
        }}
      }}
      return inside;
    }}

    function isPointInPolygonRings(x, y, rings) {{
      if (!isPointInRing(x, y, rings[0])) return false;
      for (let h = 1; h < rings.length; h++) {{
        if (isPointInRing(x, y, rings[h])) return false;
      }}
      return true;
    }}

    // Canonical Sorting for ANCs and SMDs (Ascending Numerical then Alphabetical)
    function compareAnc(a, b) {{
      if (!a) return 1;
      if (!b) return -1;
      const cleanA = String(a).replace(/^ANC\\s*/i, '').trim();
      const cleanB = String(b).replace(/^ANC\\s*/i, '').trim();
      const is34GA = cleanA.startsWith('3/4G');
      const is34GB = cleanB.startsWith('3/4G');
      if (is34GA && !is34GB) {{
        const numB = parseInt(cleanB, 10);
        return numB <= 3 ? 1 : -1;
      }}
      if (!is34GA && is34GB) {{
        const numA = parseInt(cleanA, 10);
        return numA <= 3 ? -1 : 1;
      }}
      const matchA = cleanA.match(/^(\\d+)([A-Z]+)?(.*)$/);
      const matchB = cleanB.match(/^(\\d+)([A-Z]+)?(.*)$/);
      if (matchA && matchB) {{
        const numA = parseInt(matchA[1], 10);
        const numB = parseInt(matchB[1], 10);
        if (numA !== numB) return numA - numB;
        const letA = matchA[2] || '';
        const letB = matchB[2] || '';
        if (letA !== letB) return letA.localeCompare(letB);
        return (matchA[3] || '').localeCompare(matchB[3] || '');
      }}
      return cleanA.localeCompare(cleanB, undefined, {{ numeric: true }});
    }}

    function compareSmd(a, b) {{
      if (!a) return 1;
      if (!b) return -1;
      const cleanA = String(a).replace(/^SMD\\s*/i, '').trim();
      const cleanB = String(b).replace(/^SMD\\s*/i, '').trim();
      const is34GA = cleanA.startsWith('3/4G');
      const is34GB = cleanB.startsWith('3/4G');
      if (is34GA && !is34GB) {{
        const numB = parseInt(cleanB, 10);
        return numB <= 3 ? 1 : -1;
      }}
      if (!is34GA && is34GB) {{
        const numA = parseInt(cleanA, 10);
        return numA <= 3 ? -1 : 1;
      }}
      if (is34GA && is34GB) {{
        const numA = parseInt(cleanA.substring(4), 10) || 0;
        const numB = parseInt(cleanB.substring(4), 10) || 0;
        return numA - numB;
      }}
      const matchA = cleanA.match(/^(\\d+)([A-Z]+)(\\d+)?/);
      const matchB = cleanB.match(/^(\\d+)([A-Z]+)(\\d+)?/);
      if (matchA && matchB) {{
        const numA = parseInt(matchA[1], 10);
        const numB = parseInt(matchB[1], 10);
        if (numA !== numB) return numA - numB;
        const letA = matchA[2] || '';
        const letB = matchB[2] || '';
        if (letA !== letB) return letA.localeCompare(letB);
        const smdNumA = parseInt(matchA[3] || '0', 10);
        const smdNumB = parseInt(matchB[3] || '0', 10);
        return smdNumA - smdNumB;
      }}
      return cleanA.localeCompare(cleanB, undefined, {{ numeric: true }});
    }}

    function formatSortedAncs(ancsStr) {{
      if (!ancsStr) return '';
      const rawList = ancsStr.replace(/^ANC\\s*/i, '').split(',');
      const ancs = Array.from(new Set(rawList.map(a => a.trim()).filter(Boolean)));
      ancs.sort(compareAnc);
      return ancs.length > 0 ? ('ANC ' + ancs.join(', ')) : '';
    }}

    function buildRouteSpatialIndex() {{
      trashRouteIndex = [];
      MAP_DATA.trash_routes.features.forEach(f => {{
        const geom = f.geometry;
        const ringsList = geom.type === 'Polygon' ? [geom.coordinates] : geom.coordinates;
        let minX = 1e9, maxX = -1e9, minY = 1e9, maxY = -1e9;
        ringsList.forEach(rings => {{
          rings.forEach(ring => {{
            ring.forEach(pt => {{
              if (pt[0] < minX) minX = pt[0];
              if (pt[0] > maxX) maxX = pt[0];
              if (pt[1] < minY) minY = pt[1];
              if (pt[1] > maxY) maxY = pt[1];
            }});
          }});
        }});
        trashRouteIndex.push({{
          bbox: [minX, minY, maxX, maxY],
          ringsList: ringsList,
          route: f.properties.route_area,
          day: f.properties.days,
          ward: f.properties.ward,
          neighborhoods: f.properties.neighborhoods,
          ancs: f.properties.ancs,
          area_desc: f.properties.area_desc
        }});
      }});

      recycleRouteIndex = [];
      MAP_DATA.recycle_routes.features.forEach(f => {{
        const geom = f.geometry;
        const ringsList = geom.type === 'Polygon' ? [geom.coordinates] : geom.coordinates;
        let minX = 1e9, maxX = -1e9, minY = 1e9, maxY = -1e9;
        ringsList.forEach(rings => {{
          rings.forEach(ring => {{
            ring.forEach(pt => {{
              if (pt[0] < minX) minX = pt[0];
              if (pt[0] > maxX) maxX = pt[0];
              if (pt[1] < minY) minY = pt[1];
              if (pt[1] > maxY) maxY = pt[1];
            }});
          }});
        }});
        recycleRouteIndex.push({{
          bbox: [minX, minY, maxX, maxY],
          ringsList: ringsList,
          route: f.properties.route,
          day: f.properties.day,
          ward: f.properties.ward,
          neighborhoods: f.properties.neighborhoods,
          ancs: f.properties.ancs,
          area_desc: f.properties.area_desc
        }});
      }});
    }}

    function isPointInRoute(index, routeId, latlng) {{
      if (!routeId || !latlng) return null;
      const x = latlng.lng;
      const y = latlng.lat;
      for (let i = 0; i < index.length; i++) {{
        const item = index[i];
        if (item.route !== routeId) continue;
        if (x < item.bbox[0] || x > item.bbox[2] || y < item.bbox[1] || y > item.bbox[3]) continue;
        for (let j = 0; j < item.ringsList.length; j++) {{
          if (isPointInPolygonRings(x, y, item.ringsList[j])) return item;
        }}
      }}
      return null;
    }}

    function findRouteAtLatLng(index, latlng, preferredRouteId = null) {{
      if (preferredRouteId) {{
        const pref = isPointInRoute(index, preferredRouteId, latlng);
        if (pref) return pref;
      }}
      const x = latlng.lng;
      const y = latlng.lat;
      for (let i = 0; i < index.length; i++) {{
        const item = index[i];
        if (preferredRouteId && item.route === preferredRouteId) continue;
        if (x < item.bbox[0] || x > item.bbox[2] || y < item.bbox[1] || y > item.bbox[3]) continue;
        for (let j = 0; j < item.ringsList.length; j++) {{
          if (isPointInPolygonRings(x, y, item.ringsList[j])) return item;
        }}
      }}
      return null;
    }}

    function initSMDLayer() {{
      if (smdLayer) map.removeLayer(smdLayer);
      smdLayer = L.geoJSON(MAP_DATA.smds, {{
        pane: 'smdPane',
        style: smdStyle,
        onEachFeature: function(feature, layer) {{
          const p = feature.properties;
          layer.on({{
            mouseover: function(e) {{
              if (activeHoverLayer && activeHoverLayer !== layer) {{
                if (!selectedSmdId || selectedSmdId !== activeHoverLayer.feature?.properties?.smd_id) {{
                  smdLayer.resetStyle(activeHoverLayer);
                }}
              }}
              activeHoverLayer = layer;
              const streamColor = getStreamColor(currentMetric);
              layer.setStyle({{ weight: 3.8, color: streamColor, fillOpacity: 0.88 }});
              const val = getSmdMetric(p, currentMetric, currentPeriod);
              const streamName = currentMetric === 'total' ? 'Combined' : (currentMetric === 'trash' ? 'Trash' : 'Recycling');
              smdTooltip.setContent(`
                <div style="font-weight: 800; font-size: 12px; color: var(--text-main);">SMD ${{p.smd_id}}</div>
                <div style="font-size: 11px; color: var(--text-dim);">ANC ${{p.anc_id}} • Ward ${{p.ward}}</div>
                <div style="margin-top: 4px; font-size: 12px; font-weight: 700; color: ${{streamColor}};">
                  ${{val.toLocaleString()}} ${{streamName}} Requests (${{currentPeriod === '30d' ? '30d' : '180d'}})
                </div>
              `);
              smdTooltip.setLatLng(e.latlng);
              if (!map.hasLayer(smdTooltip)) smdTooltip.openOn(map);
            }},
            mousemove: function(e) {{
              smdTooltip.setLatLng(e.latlng);
            }},
            mouseout: function() {{
              if (!selectedSmdId || selectedSmdId !== p.smd_id) {{
                smdLayer.resetStyle(layer);
              }}
              smdTooltip.close();
            }},
            click: function(e) {{
              selectHierarchy(p.smd_id);
            }}
          }});
        }}
      }}).addTo(map);
    }}

    function initWardLayer() {{
      if (wardLayer) map.removeLayer(wardLayer);
      wardLayer = L.geoJSON(MAP_DATA.wards, {{
        pane: 'wardPane',
        style: wardStyle
      }}).addTo(map);
    }}

    function ensureSvgPatterns() {{
      const template = document.getElementById('route-hatch-defs-svg');
      if (!template) return;
      const defsTemplate = template.querySelector('defs');
      if (!defsTemplate) return;
      document.querySelectorAll('#map svg').forEach(svg => {{
        if (!svg.querySelector('#hatch-trash')) {{
          let defs = svg.querySelector('defs');
          if (!defs) {{
            defs = defsTemplate.cloneNode(true);
            svg.insertBefore(defs, svg.firstChild);
          }} else {{
            Array.from(defsTemplate.children).forEach(child => {{
              if (!defs.querySelector('#' + child.id)) {{
                defs.appendChild(child.cloneNode(true));
              }}
            }});
          }}
        }}
      }});
    }}

    function getTrashRouteStyle() {{
      const isDark = currentTheme === 'dark';
      return {{
        color: isDark ? '#ef4444' : '#dc2626',
        weight: 1.5,
        opacity: 0.85,
        fill: true,
        fillColor: isDark ? 'url(#hatch-trash-dark)' : 'url(#hatch-trash)',
        fillOpacity: 1.0,
        dashArray: null
      }};
    }}

    function getTrashRouteHoverStyle() {{
      const isDark = currentTheme === 'dark';
      return {{
        color: isDark ? '#fca5a5' : '#991b1b',
        weight: 3.5,
        opacity: 1.0,
        fill: true,
        fillColor: isDark ? 'url(#hatch-trash-dark-hover)' : 'url(#hatch-trash-hover)',
        fillOpacity: 1.0,
        dashArray: null
      }};
    }}

    function getRecycleRouteStyle() {{
      const isDark = currentTheme === 'dark';
      return {{
        color: isDark ? '#22c55e' : '#16a34a',
        weight: 1.5,
        opacity: 0.85,
        fill: true,
        fillColor: isDark ? 'url(#hatch-recycle-dark)' : 'url(#hatch-recycle)',
        fillOpacity: 1.0,
        dashArray: null
      }};
    }}

    function getRecycleRouteHoverStyle() {{
      const isDark = currentTheme === 'dark';
      return {{
        color: isDark ? '#86efac' : '#166534',
        weight: 3.5,
        opacity: 1.0,
        fill: true,
        fillColor: isDark ? 'url(#hatch-recycle-dark-hover)' : 'url(#hatch-recycle-hover)',
        fillOpacity: 1.0,
        dashArray: null
      }};
    }}

    function getTrashLineStyle() {{
      const isDark = currentTheme === 'dark';
      return {{
        color: isDark ? '#ef4444' : '#dc2626',
        weight: 3.5,
        opacity: 0.9,
        fill: false,
        lineCap: 'round',
        lineJoin: 'round'
      }};
    }}

    function getTrashLineHoverStyle() {{
      const isDark = currentTheme === 'dark';
      return {{
        color: isDark ? '#fca5a5' : '#991b1b',
        weight: 5.5,
        opacity: 1.0,
        fill: false,
        lineCap: 'round',
        lineJoin: 'round'
      }};
    }}

    function getRecycleLineStyle() {{
      const isDark = currentTheme === 'dark';
      return {{
        color: isDark ? '#22c55e' : '#16a34a',
        weight: 3.5,
        opacity: 0.9,
        fill: false,
        lineCap: 'round',
        lineJoin: 'round'
      }};
    }}

    function getRecycleLineHoverStyle() {{
      const isDark = currentTheme === 'dark';
      return {{
        color: isDark ? '#86efac' : '#166534',
        weight: 5.5,
        opacity: 1.0,
        fill: false,
        lineCap: 'round',
        lineJoin: 'round'
      }};
    }}

    let activeHoverRouteLayers = [];
    let activeHoverRouteLayer = null;
    let selectedRouteId = null;
    let selectedRouteStream = null;
    let selectedRouteType = '';
    let selectedRouteIsLine = false;
    let selectedRouteLayers = [];
    let selectedRouteLayer = null;

    function clearRouteSelection() {{
      if (selectedRouteLayers.length > 0) {{
        selectedRouteLayers.forEach(l => {{
          if (selectedRouteIsLine) {{
            l.setStyle(selectedRouteStream === 'Trash' ? getTrashLineStyle() : getRecycleLineStyle());
          }} else {{
            l.setStyle(selectedRouteStream === 'Trash' ? getTrashRouteStyle() : getRecycleRouteStyle());
          }}
        }});
        selectedRouteLayers = [];
      }}
      selectedRouteLayer = null;
      selectedRouteId = null;
      selectedRouteStream = null;
      selectedRouteType = '';
      selectedRouteIsLine = false;
    }}

    function ensureSelectedRoutesOnTop() {{
      if (selectedRouteLayers && selectedRouteLayers.length > 0) {{
        selectedRouteLayers.forEach(l => {{
          if (l && l.bringToFront) l.bringToFront();
        }});
      }}
    }}

    function clearRouteHover() {{
      if (activeHoverRouteLayers.length > 0) {{
        activeHoverRouteLayers.forEach(l => {{
          if (!selectedRouteLayers.includes(l)) {{
            if (l._isLine) {{
              l.setStyle(l._isTrash ? getTrashLineStyle() : getRecycleLineStyle());
            }} else {{
              l.setStyle(l._isTrash ? getTrashRouteStyle() : getRecycleRouteStyle());
            }}
          }}
        }});
        activeHoverRouteLayers = [];
      }}
      activeHoverRouteLayer = null;
      ensureSelectedRoutesOnTop();
    }}

    function selectRoute(feature, layer, stream) {{
      selectedSmdId = null;
      selectedAncId = null;
      selectedWardNum = null;
      updateDropdowns(null, null, null);
      updateWardMask();
      if (smdLayer) smdLayer.setStyle(smdStyle);

      clearRouteSelection();
      clearRouteHover();

      const rId = stream === 'Trash' ? (feature.properties.route_area || feature.properties.route) : feature.properties.route;
      selectedRouteId = rId;
      selectedRouteStream = stream;
      selectedRouteType = ' (polygon)';
      selectedRouteIsLine = false;

      const lookupDict = stream === 'Trash' ? trashRouteById : recycleRouteById;
      const matchingLayers = lookupDict[rId] ? [...lookupDict[rId]] : [];
      let combinedBounds = null;

      matchingLayers.forEach(l => {{
        if (l.getBounds) {{
          const b = l.getBounds();
          if (b && b.isValid()) {{
            if (combinedBounds) combinedBounds.extend(b);
            else combinedBounds = L.latLngBounds(b.getSouthWest(), b.getNorthEast());
          }}
        }}
      }});
      if (matchingLayers.length === 0) {{
        matchingLayers.push(layer);
        if (layer.getBounds) combinedBounds = layer.getBounds();
      }}

      selectedRouteLayers = matchingLayers;
      selectedRouteLayer = matchingLayers[0];

      const isDark = currentTheme === 'dark';
      const selColor = stream === 'Trash'
        ? (isDark ? '#f87171' : '#b91c1c')
        : (isDark ? '#4ade80' : '#15803d');
      const hatchUrl = stream === 'Trash'
        ? (isDark ? 'url(#hatch-trash-dark-hover)' : 'url(#hatch-trash-hover)')
        : (isDark ? 'url(#hatch-recycle-dark-hover)' : 'url(#hatch-recycle-hover)');

      selectedRouteLayers.forEach(l => {{
        l._isLine = false;
        l.setStyle({{
          color: selColor,
          weight: 4.5,
          opacity: 1.0,
          fill: true,
          fillColor: hatchUrl,
          fillOpacity: 1.0
        }});
        if (l.bringToFront) l.bringToFront();
      }});

      if (combinedBounds && combinedBounds.isValid()) {{
        map.fitBounds(combinedBounds, {{ padding: [50, 50], maxZoom: 15 }});
      }}

      updateInspectorRoute(feature.properties, stream);
      updateBreadcrumbsRoute(feature.properties, stream, ' (polygon)');
    }}

    function selectLineRoute(feature, layer, stream) {{
      selectedSmdId = null;
      selectedAncId = null;
      selectedWardNum = null;
      updateDropdowns(null, null, null);
      updateWardMask();
      if (smdLayer) smdLayer.setStyle(smdStyle);

      clearRouteSelection();
      clearRouteHover();

      const rId = feature.properties.route;
      selectedRouteId = rId;
      selectedRouteStream = stream;
      selectedRouteType = ' (line)';
      selectedRouteIsLine = true;

      const lookupDict = stream === 'Trash' ? trashLineById : recycleLineById;
      const matchingLayers = lookupDict[rId] ? [...lookupDict[rId]] : [];
      let combinedBounds = null;

      matchingLayers.forEach(l => {{
        if (l.getBounds) {{
          const b = l.getBounds();
          if (b && b.isValid()) {{
            if (combinedBounds) combinedBounds.extend(b);
            else combinedBounds = L.latLngBounds(b.getSouthWest(), b.getNorthEast());
          }}
        }}
      }});

      if (matchingLayers.length === 0) {{
        matchingLayers.push(layer);
        if (layer.getBounds) combinedBounds = layer.getBounds();
      }}

      selectedRouteLayers = matchingLayers;
      selectedRouteLayer = matchingLayers[0];

      const isDark = currentTheme === 'dark';
      const selColor = stream === 'Trash'
        ? (isDark ? '#f87171' : '#b91c1c')
        : (isDark ? '#4ade80' : '#15803d');

      selectedRouteLayers.forEach(l => {{
        l._isLine = true;
        l._isTrash = stream === 'Trash';
        l.setStyle({{
          color: selColor,
          weight: 6.5,
          opacity: 1.0
        }});
        if (l.bringToFront) l.bringToFront();
      }});

      if (combinedBounds && combinedBounds.isValid()) {{
        map.fitBounds(combinedBounds, {{ padding: [50, 50], maxZoom: 16 }});
      }}

      updateInspectorRoute(feature.properties, stream);
      updateBreadcrumbsRoute(feature.properties, stream, ' (line)');
    }}

    function handleRouteHover(e, layer, isTrash) {{
      const trashActive = map.hasLayer(trashRoutesLayer);
      const recActive = map.hasLayer(recycleRoutesLayer);
      if (!trashActive && !recActive) return;

      const latlng = e.latlng;
      const p = layer.feature && layer.feature.properties;
      let rId = isTrash ? (p.route_area || p.route) : p.route;

      const inSelRec = (selectedRouteId && !selectedRouteIsLine && selectedRouteStream === 'Recycling')
        ? isPointInRoute(recycleRouteIndex, selectedRouteId, latlng)
        : null;
      const inSelTrash = (selectedRouteId && !selectedRouteIsLine && selectedRouteStream === 'Trash')
        ? isPointInRoute(trashRouteIndex, selectedRouteId, latlng)
        : null;

      if (inSelRec) {{
        rId = selectedRouteId;
        isTrash = false;
        if (activeHoverRouteLayers.length > 0) {{
          clearRouteHover();
        }}
        ensureSelectedRoutesOnTop();
      }} else if (inSelTrash) {{
        rId = selectedRouteId;
        isTrash = true;
        if (activeHoverRouteLayers.length > 0) {{
          clearRouteHover();
        }}
        ensureSelectedRoutesOnTop();
      }} else {{
        if (!activeHoverRouteLayers.includes(layer)) {{
          clearRouteHover();

          const lookupDict = isTrash ? trashRouteById : recycleRouteById;
          const matchingLayers = lookupDict[rId] ? [...lookupDict[rId]] : [];
          if (matchingLayers.length === 0) matchingLayers.push(layer);

          matchingLayers.forEach(l => {{
            l._isTrash = isTrash;
            l._isLine = false;
            if (!selectedRouteLayers.includes(l)) {{
              l.setStyle(isTrash ? getTrashRouteHoverStyle() : getRecycleRouteHoverStyle());
            }}
          }});
          activeHoverRouteLayers = matchingLayers;
          activeHoverRouteLayer = layer;
          ensureSelectedRoutesOnTop();
        }}
      }}

      let prefTrash = null;
      let prefRec = null;

      if (selectedRouteId && !selectedRouteIsLine) {{
        if (selectedRouteStream === 'Trash') prefTrash = selectedRouteId;
        if (selectedRouteStream === 'Recycling') prefRec = selectedRouteId;
      }}
      if (!prefTrash && isTrash && rId) prefTrash = rId;
      if (!prefRec && !isTrash && rId) prefRec = rId;

      const tr = trashActive ? findRouteAtLatLng(trashRouteIndex, latlng, prefTrash) : null;
      const rr = recActive ? findRouteAtLatLng(recycleRouteIndex, latlng, prefRec) : null;

      let html = '';

      if (trashActive && recActive) {{
        if (tr && rr) {{
          const tStats = ROUTE_STATS['trash_' + tr.route] || {{}};
          const rStats = ROUTE_STATS['recycle_' + rr.route] || {{}};
          const tTot = tStats.total || 0;
          const rTot = rStats.total || 0;
          const combTot = tTot + rTot;
          const tAncs = formatSortedAncs(tr.ancs || tStats.ancs || '');
          const rAncs = formatSortedAncs(rr.ancs || rStats.ancs || '');
          const ancsDisplay = (tAncs && rAncs && tAncs === rAncs) ? tAncs : [tAncs ? `Trash: ${{tAncs}}` : '', rAncs ? `Recycling: ${{rAncs}}` : ''].filter(Boolean).join(' • ');

          html = `
            <div style="font-weight: 800; font-size: 12px; color: var(--text-main);">Route Intersection</div>
            <div style="font-size: 11px; color: var(--text-dim);">${{tr.area_desc || rr.area_desc || 'DPW Catchment Area'}}</div>
            ${{ancsDisplay ? `<div style="font-size: 11px; color: var(--text-dim); margin-top: 1px;">ANCs: <strong style="color: var(--text-main);">${{ancsDisplay}}</strong></div>` : ''}}
            <div style="margin-top: 5px; font-size: 12px; font-weight: 700; color: var(--combined-color); border-top: 1px solid rgba(37,99,235,0.25); padding-top: 4px;">
              ${{combTot.toLocaleString()}} Combined Requests (180d)
            </div>
            <div style="margin-top: 4px; display: flex; flex-direction: column; gap: 2px; font-size: 11px;">
              <span style="color: var(--trash-color);">Trash (${{tr.route}}): <strong>${{tTot.toLocaleString()}}</strong> (${{tr.day}})</span>
              <span style="color: var(--recycle-color);">Recycling (${{rr.route}}): <strong>${{rTot.toLocaleString()}}</strong> (${{rr.day}})</span>
            </div>
          `;
        }} else if (tr) {{
          const tStats = ROUTE_STATS['trash_' + tr.route] || {{}};
          const tTot = tStats.total || 0;
          const ancs = formatSortedAncs(tr.ancs || tStats.ancs || '');
          html = `
            <div style="font-weight: 800; font-size: 12px; color: var(--trash-color);">Trash Route ${{tr.route}} (Polygon)</div>
            <div style="font-size: 11px; color: var(--text-dim);">${{tr.area_desc || 'DPW Catchment Area'}}</div>
            ${{ancs ? `<div style="font-size: 11px; color: var(--text-dim); margin-top: 1px;">ANCs: <strong style="color: var(--text-main);">${{ancs}}</strong></div>` : ''}}
            <div style="font-size: 11px; color: var(--text-dim); margin-top: 1px;">Collection day: ${{tr.day || 'Scheduled'}}</div>
            <div style="margin-top: 5px; font-size: 12px; font-weight: 700; color: var(--trash-color); border-top: 1px solid rgba(220,38,38,0.25); padding-top: 4px;">
              ${{tTot.toLocaleString()}} Trash Requests (180d)
            </div>
            <div style="font-size: 10px; color: var(--text-muted); margin-top: 2px;">
              Repeat Rate: ${{tStats.repeat_rate != null ? tStats.repeat_rate + '%' : 'N/A'}} • ${{tStats.unique_addrs || 0}} unique addresses
            </div>
          `;
        }} else if (rr) {{
          const rStats = ROUTE_STATS['recycle_' + rr.route] || {{}};
          const rTot = rStats.total || 0;
          const ancs = formatSortedAncs(rr.ancs || rStats.ancs || '');
          html = `
            <div style="font-weight: 800; font-size: 12px; color: var(--recycle-color);">Recycling Route ${{rr.route}} (Polygon)</div>
            <div style="font-size: 11px; color: var(--text-dim);">${{rr.area_desc || 'DPW Catchment Area'}}</div>
            ${{ancs ? `<div style="font-size: 11px; color: var(--text-dim); margin-top: 1px;">ANCs: <strong style="color: var(--text-main);">${{ancs}}</strong></div>` : ''}}
            <div style="font-size: 11px; color: var(--text-dim); margin-top: 1px;">Collection day: ${{rr.day || 'Scheduled'}}</div>
            <div style="margin-top: 5px; font-size: 12px; font-weight: 700; color: var(--recycle-color); border-top: 1px solid rgba(22,163,74,0.25); padding-top: 4px;">
              ${{rTot.toLocaleString()}} Recycling Requests (180d)
            </div>
            <div style="font-size: 10px; color: var(--text-muted); margin-top: 2px;">
              Repeat Rate: ${{rStats.repeat_rate != null ? rStats.repeat_rate + '%' : 'N/A'}} • ${{rStats.unique_addrs || 0}} unique addresses
            </div>
          `;
        }}
      }} else if (trashActive && tr) {{
        const tStats = ROUTE_STATS['trash_' + tr.route] || {{}};
        const tTot = tStats.total || 0;
        const ancs = formatSortedAncs(tr.ancs || tStats.ancs || '');
        html = `
          <div style="font-weight: 800; font-size: 12px; color: var(--trash-color);">Trash Route ${{tr.route}} (Polygon)</div>
          <div style="font-size: 11px; color: var(--text-dim);">${{tr.area_desc || 'DPW Catchment Area'}}</div>
          ${{ancs ? `<div style="font-size: 11px; color: var(--text-dim); margin-top: 1px;">ANCs: <strong style="color: var(--text-main);">${{ancs}}</strong></div>` : ''}}
          <div style="font-size: 11px; color: var(--text-dim); margin-top: 1px;">Collection day: ${{tr.day || 'Scheduled'}}</div>
          <div style="margin-top: 5px; font-size: 12px; font-weight: 700; color: var(--trash-color); border-top: 1px solid rgba(220,38,38,0.25); padding-top: 4px;">
            ${{tTot.toLocaleString()}} Trash Requests (180d)
          </div>
          <div style="font-size: 10px; color: var(--text-muted); margin-top: 2px;">
            Repeat Rate: ${{tStats.repeat_rate != null ? tStats.repeat_rate + '%' : 'N/A'}} • ${{tStats.unique_addrs || 0}} unique addresses
          </div>
        `;
      }} else if (recActive && rr) {{
        const rStats = ROUTE_STATS['recycle_' + rr.route] || {{}};
        const rTot = rStats.total || 0;
        const ancs = formatSortedAncs(rr.ancs || rStats.ancs || '');
        html = `
          <div style="font-weight: 800; font-size: 12px; color: var(--recycle-color);">Recycling Route ${{rr.route}} (Polygon)</div>
          <div style="font-size: 11px; color: var(--text-dim);">${{rr.area_desc || 'DPW Catchment Area'}}</div>
          ${{ancs ? `<div style="font-size: 11px; color: var(--text-dim); margin-top: 1px;">ANCs: <strong style="color: var(--text-main);">${{ancs}}</strong></div>` : ''}}
          <div style="font-size: 11px; color: var(--text-dim); margin-top: 1px;">Collection day: ${{rr.day || 'Scheduled'}}</div>
          <div style="margin-top: 5px; font-size: 12px; font-weight: 700; color: var(--recycle-color); border-top: 1px solid rgba(22,163,74,0.25); padding-top: 4px;">
            ${{rTot.toLocaleString()}} Recycling Requests (180d)
          </div>
          <div style="font-size: 10px; color: var(--text-muted); margin-top: 2px;">
            Repeat Rate: ${{rStats.repeat_rate != null ? rStats.repeat_rate + '%' : 'N/A'}} • ${{rStats.unique_addrs || 0}} unique addresses
          </div>
        `;
      }}

      if (html) {{
        smdTooltip.setContent(html);
        smdTooltip.setLatLng(latlng);
        if (!map.hasLayer(smdTooltip)) smdTooltip.openOn(map);
      }} else {{
        smdTooltip.close();
      }}
    }}

    function handleRouteMouseout(layer, isTrash) {{
      clearRouteHover();
      smdTooltip.close();
    }}

    function initTrashRoutesLayer() {{
      trashRoutesLayer = L.geoJSON(MAP_DATA.trash_routes, {{
        pane: 'routePane',
        style: getTrashRouteStyle,
        onEachFeature: function(feature, layer) {{
          const rid = feature.properties.route_area || feature.properties.route;
          if (rid) {{
            if (!trashRouteById[rid]) trashRouteById[rid] = [];
            trashRouteById[rid].push(layer);
          }}
          layer.on({{
            mouseover: function(e) {{ handleRouteHover(e, layer, true); }},
            mousemove: function(e) {{ handleRouteHover(e, layer, true); }},
            mouseout: function() {{ handleRouteMouseout(layer, true); }},
            click: function(e) {{
              L.DomEvent.stopPropagation(e);
              selectRoute(feature, layer, 'Trash');
            }}
          }});
        }}
      }});
    }}

    function initRecycleRoutesLayer() {{
      recycleRoutesLayer = L.geoJSON(MAP_DATA.recycle_routes, {{
        pane: 'routePane',
        style: getRecycleRouteStyle,
        onEachFeature: function(feature, layer) {{
          const rid = feature.properties.route;
          if (rid) {{
            if (!recycleRouteById[rid]) recycleRouteById[rid] = [];
            recycleRouteById[rid].push(layer);
          }}
          layer.on({{
            mouseover: function(e) {{ handleRouteHover(e, layer, false); }},
            mousemove: function(e) {{ handleRouteHover(e, layer, false); }},
            mouseout: function() {{ handleRouteMouseout(layer, false); }},
            click: function(e) {{
              L.DomEvent.stopPropagation(e);
              selectRoute(feature, layer, 'Recycling');
            }}
          }});
        }}
      }});
    }}

    function handleLineHover(e, layer, isTrash) {{
      const p = layer.feature && layer.feature.properties;
      const rId = p.route;

      if (!activeHoverRouteLayers.includes(layer)) {{
        clearRouteHover();

        const lookupDict = isTrash ? trashLineById : recycleLineById;
        const matchingLayers = lookupDict[rId] ? [...lookupDict[rId]] : [];
        if (matchingLayers.length === 0) matchingLayers.push(layer);

        matchingLayers.forEach(l => {{
          l._isTrash = isTrash;
          l._isLine = true;
          if (!selectedRouteLayers.includes(l)) {{
            l.setStyle(isTrash ? getTrashLineHoverStyle() : getRecycleLineHoverStyle());
          }}
        }});
        activeHoverRouteLayers = matchingLayers;
        activeHoverRouteLayer = layer;
        ensureSelectedRoutesOnTop();
      }}

      const stream = isTrash ? 'Trash' : 'Recycling';
      const color = isTrash ? 'var(--trash-color)' : 'var(--recycle-color)';
      const totalReq = (p.total || 0).toLocaleString();
      const sched = p.day || 'Scheduled';

      const html = `
        <div style="font-weight: 800; font-size: 12px; color: ${{color}};">${{stream}} Route ${{p.route}} (Line)</div>
        <div style="font-size: 11px; color: var(--text-dim);">${{p.area_desc || p.neighborhoods || 'Residential Service Corridor'}}</div>
        ${{p.ancs ? `<div style="font-size: 11px; color: var(--text-dim); margin-top: 1px;">ANCs: <strong style="color: var(--text-main);">${{formatSortedAncs(p.ancs)}}</strong></div>` : ''}}
        <div style="font-size: 11px; color: var(--text-dim); margin-top: 1px;">Collection day: ${{sched}} • ${{p.ward || 'DC'}}</div>
        <div style="margin-top: 5px; font-size: 12px; font-weight: 700; color: ${{color}}; border-top: 1px solid rgba(${{isTrash ? '220,38,38' : '22,163,74'}},0.25); padding-top: 4px;">
          ${{totalReq}} ${{stream}} Requests (180d)
        </div>
        <div style="font-size: 10px; color: var(--text-muted); margin-top: 2px;">
          ${{(p.point_count || 0).toLocaleString()}} Collection Points • ${{(p.segment_count || 0).toLocaleString()}} Street Segments
        </div>
      `;

      smdTooltip.setContent(html);
      smdTooltip.setLatLng(e.latlng);
      if (!map.hasLayer(smdTooltip)) smdTooltip.openOn(map);
    }}

    function handleLineMouseout(layer, isTrash) {{
      clearRouteHover();
      smdTooltip.close();
    }}

    function initTrashLinesLayer() {{
      if (!MAP_DATA.trash_routes_lines) return;
      trashLinesLayer = L.geoJSON(MAP_DATA.trash_routes_lines, {{
        pane: 'routeLinePane',
        style: getTrashLineStyle,
        onEachFeature: function(feature, layer) {{
          layer._isLine = true;
          layer._isTrash = true;
          const rid = feature.properties.route;
          if (rid) {{
            if (!trashLineById[rid]) trashLineById[rid] = [];
            trashLineById[rid].push(layer);
          }}
          layer.on({{
            mouseover: function(e) {{ handleLineHover(e, layer, true); }},
            mousemove: function(e) {{ handleLineHover(e, layer, true); }},
            mouseout: function() {{ handleLineMouseout(layer, true); }},
            click: function(e) {{
              if (e && e.originalEvent) L.DomEvent.stopPropagation(e);
              selectLineRoute(feature, layer, 'Trash');
            }}
          }});
        }}
      }});
    }}

    function initRecycleLinesLayer() {{
      if (!MAP_DATA.recycle_routes_lines) return;
      recycleLinesLayer = L.geoJSON(MAP_DATA.recycle_routes_lines, {{
        pane: 'routeLinePane',
        style: getRecycleLineStyle,
        onEachFeature: function(feature, layer) {{
          layer._isLine = true;
          layer._isTrash = false;
          const rid = feature.properties.route;
          if (rid) {{
            if (!recycleLineById[rid]) recycleLineById[rid] = [];
            recycleLineById[rid].push(layer);
          }}
          layer.on({{
            mouseover: function(e) {{ handleLineHover(e, layer, false); }},
            mousemove: function(e) {{ handleLineHover(e, layer, false); }},
            mouseout: function() {{ handleLineMouseout(layer, false); }},
            click: function(e) {{
              if (e && e.originalEvent) L.DomEvent.stopPropagation(e);
              selectLineRoute(feature, layer, 'Recycling');
            }}
          }});
        }}
      }});
    }}

    // Citywide Stats Helper
    function getCitywideStats(period) {{
      let total = 0, trash = 0, rec = 0;
      MAP_DATA.wards.features.forEach(f => {{
        const m = period === '30d' ? f.properties.metrics_30d : f.properties.metrics_180d;
        total += (m ? m.total : f.properties.total) || 0;
        trash += (m ? m.trash : f.properties.trash) || 0;
        rec += (m ? m.recycling : f.properties.recycling) || 0;
      }});
      return {{ total, trash, rec }};
    }}

    // Selection Handling
    function selectHierarchy(smdId) {{
      if (!MAP_DATA || !smdLayer) return;
      clearRouteSelection();
      let targetLayer = null;
      smdLayer.eachLayer(l => {{
        if (l.feature.properties.smd_id === smdId) targetLayer = l;
      }});
      if (!targetLayer) return;

      const p = targetLayer.feature.properties;
      selectedSmdId = p.smd_id;
      selectedAncId = p.anc_id;
      selectedWardNum = p.ward;

      updateDropdowns(selectedWardNum, selectedAncId, selectedSmdId);
      updateWardMask();
      smdLayer.setStyle(smdStyle);
      if (wardLayer) wardLayer.setStyle(wardStyle);

      targetLayer.bringToFront();
      map.fitBounds(targetLayer.getBounds(), {{ maxZoom: 16, padding: [60, 60] }});

      updateInspectorSMD(p, targetLayer.getBounds().getCenter());
      updateBreadcrumbs();
    }}

    function selectWard(wNum) {{
      if (!MAP_DATA) return;
      clearRouteSelection();
      selectedWardNum = wNum ? parseInt(wNum) : null;
      selectedSmdId = null;
      selectedAncId = null;

      if (!selectedWardNum) {{
        resetToCitywide();
        return;
      }}

      updateDropdowns(selectedWardNum, null, null);
      updateWardMask();
      smdLayer.setStyle(smdStyle);
      if (wardLayer) wardLayer.setStyle(wardStyle);

      const wardFeat = MAP_DATA.wards.features.find(f => f.properties.ward === selectedWardNum);
      if (wardFeat) {{
        const b = L.geoJSON(wardFeat).getBounds();
        map.fitBounds(b, {{ padding: [30, 30] }});
        updateInspectorWard(wardFeat.properties);
      }}
      updateBreadcrumbs();
    }}

    function selectANC(ancId) {{
      if (!MAP_DATA) return;
      clearRouteSelection();
      selectedAncId = ancId;
      selectedSmdId = null;

      const smdInAnc = MAP_DATA.smds.features.find(f => f.properties.anc_id === ancId);
      if (smdInAnc) selectedWardNum = smdInAnc.properties.ward;

      updateDropdowns(selectedWardNum, selectedAncId, null);
      updateWardMask();
      smdLayer.setStyle(smdStyle);
      if (wardLayer) wardLayer.setStyle(wardStyle);

      const matching = MAP_DATA.smds.features.filter(f => f.properties.anc_id === ancId);
      if (matching.length > 0) {{
        const grp = L.featureGroup(matching.map(f => L.geoJSON(f)));
        map.fitBounds(grp.getBounds(), {{ padding: [40, 40] }});
      }}
      updateInspectorANC(ancId);
      updateBreadcrumbs();
    }}

    function resetToCitywide() {{
      if (!MAP_DATA) return;
      clearRouteSelection();
      selectedWardNum = null;
      selectedAncId = null;
      selectedSmdId = null;

      updateDropdowns(null, null, null);
      document.getElementById('smd-search').value = '';
      updateWardMask();
      if (smdLayer) smdLayer.setStyle(smdStyle);
      if (wardLayer) wardLayer.setStyle(wardStyle);

      map.setView([38.9072, -77.01], 12);
      updateInspectorCitywide();
      updateBreadcrumbs();
    }}

    function updateDropdowns(wardVal, ancVal, smdVal) {{
      if (!MAP_DATA) return;
      const wSel = document.getElementById('ward-select');
      const aSel = document.getElementById('anc-select');
      const sSel = document.getElementById('smd-select');

      wSel.value = wardVal ? String(wardVal) : 'all';

      if (!wardVal) {{
        aSel.innerHTML = '<option value="all">— Select Ward First —</option>';
        aSel.disabled = true;
        sSel.innerHTML = '<option value="all">— Select ANC First —</option>';
        sSel.disabled = true;
        return;
      }}

      // Populate ANCs
      const ancsInWard = Array.from(new Set(
        MAP_DATA.smds.features
          .filter(f => f.properties.ward === parseInt(wardVal))
          .map(f => f.properties.anc_id)
      )).sort(compareAnc);

      aSel.disabled = false;
      aSel.innerHTML = `<option value="all">All ANCs in Ward ${{wardVal}}</option>` +
        ancsInWard.map(a => `<option value="${{a}}">ANC ${{a}}</option>`).join('');
      aSel.value = ancVal || 'all';

      if (!ancVal || ancVal === 'all') {{
        sSel.innerHTML = '<option value="all">— Select ANC First —</option>';
        sSel.disabled = true;
        return;
      }}

      // Populate SMDs
      const smdsInAnc = MAP_DATA.smds.features
        .filter(f => f.properties.anc_id === ancVal)
        .map(f => f.properties.smd_id)
        .sort(compareSmd);

      sSel.disabled = false;
      sSel.innerHTML = `<option value="all">All SMDs in ANC ${{ancVal}}</option>` +
        smdsInAnc.map(s => `<option value="${{s}}">SMD ${{s}}</option>`).join('');
      sSel.value = smdVal || 'all';
    }}

    function handleWardDropdown(val) {{
      if (val === 'all') resetToCitywide();
      else selectWard(parseInt(val));
    }}

    function handleAncDropdown(val) {{
      if (val === 'all') selectWard(selectedWardNum);
      else selectANC(val);
    }}

    function handleSmdDropdown(val) {{
      if (val === 'all') selectANC(selectedAncId);
      else selectHierarchy(val);
    }}

    function handleSearch(query) {{
      if (!MAP_DATA) return;
      const q = query.trim().toUpperCase();
      if (!q) return;

      const exactSMD = MAP_DATA.smds.features.find(f => f.properties.smd_id === q);
      if (exactSMD) {{
        selectHierarchy(exactSMD.properties.smd_id);
        return;
      }}

      const exactANC = MAP_DATA.smds.features.find(f => f.properties.anc_id === q);
      if (exactANC) {{
        selectANC(exactANC.properties.anc_id);
        return;
      }}

      if (['1','2','3','4','5','6','7','8'].includes(q)) {{
        selectWard(parseInt(q));
        return;
      }}

      const wardMatch = q.match(/^WARD\\s*([1-8])$/);
      if (wardMatch) {{
        selectWard(parseInt(wardMatch[1]));
        return;
      }}

      // Route Search Support (Line routes prioritized if layer active, or polygon routes)
      if (recycleLinesLayer && map.hasLayer(recycleLinesLayer)) {{
        let match = null;
        recycleLinesLayer.eachLayer(l => {{
          if (l.feature.properties.route.toUpperCase() === q || l.feature.properties.route.toUpperCase() === 'R' + q) match = l;
        }});
        if (match) {{
          selectLineRoute(match.feature, match, 'Recycling');
          return;
        }}
      }}

      if (trashLinesLayer && map.hasLayer(trashLinesLayer)) {{
        let match = null;
        trashLinesLayer.eachLayer(l => {{
          if (l.feature.properties.route.toUpperCase() === q) match = l;
        }});
        if (match) {{
          selectLineRoute(match.feature, match, 'Trash');
          return;
        }}
      }}

      if (recycleRoutesLayer) {{
        let match = null;
        recycleRoutesLayer.eachLayer(l => {{
          if (l.feature.properties.route.toUpperCase() === q || l.feature.properties.route.toUpperCase() === 'R' + q) match = l;
        }});
        if (match) {{
          if (!map.hasLayer(recycleRoutesLayer)) map.addLayer(recycleRoutesLayer);
          selectRoute(match.feature, match, 'Recycling');
          return;
        }}
      }}

      if (trashRoutesLayer) {{
        let match = null;
        trashRoutesLayer.eachLayer(l => {{
          const r = (l.feature.properties.route_area || l.feature.properties.route || '').toUpperCase();
          if (r === q || r.endsWith(q)) match = l;
        }});
        if (match) {{
          if (!map.hasLayer(trashRoutesLayer)) map.addLayer(trashRoutesLayer);
          selectRoute(match.feature, match, 'Trash');
          return;
        }}
      }}
    }}

    function updateBreadcrumbs() {{
      const bar = document.getElementById('breadcrumb-crumbs');
      if (!bar) return;
      if (selectedRouteId) {{
        bar.innerHTML = ` &rsaquo; <span class="breadcrumb-item active">${{selectedRouteStream}} Route ${{selectedRouteId}}${{selectedRouteType}}</span>`;
        return;
      }}
      let html = '';
      if (selectedWardNum) {{
        html += ` &rsaquo; <span class="breadcrumb-item ${{!selectedAncId ? 'active' : ''}}" onclick="selectWard(${{selectedWardNum}})">Ward ${{selectedWardNum}}</span>`;
      }}
      if (selectedAncId) {{
        html += ` &rsaquo; <span class="breadcrumb-item ${{!selectedSmdId ? 'active' : ''}}" onclick="selectANC('${{selectedAncId}}')">ANC ${{selectedAncId}}</span>`;
      }}
      if (selectedSmdId) {{
        html += ` &rsaquo; <span class="breadcrumb-item active">SMD ${{selectedSmdId}}</span>`;
      }}
      bar.innerHTML = html;
    }}

    function updateBreadcrumbsRoute(p, stream, typeLabel = '') {{
      const bar = document.getElementById('breadcrumb-crumbs');
      if (!bar) return;
      const rId = stream === 'Trash' ? (p.route_area || p.route) : p.route;
      bar.innerHTML = ` &rsaquo; <span class="breadcrumb-item active">${{stream}} Route ${{rId}}${{typeLabel}}</span>`;
    }}

    function updateInspectorCitywide() {{
      const periodLabel = currentPeriod === '30d' ? 'Past 30 Days' : 'Past 180 Days';
      const stats = getCitywideStats(currentPeriod);

      document.getElementById('insp-title').innerText = 'District of Columbia';
      document.getElementById('insp-sub').innerText = `Citywide Performance Summary (${{periodLabel}})`;
      document.getElementById('insp-lbl-1').innerText = 'Selected Requests';
      document.getElementById('insp-stat-total').innerText = stats.total.toLocaleString();
      document.getElementById('insp-lbl-2').innerText = 'Share of Volume';
      document.getElementById('insp-stat-share').innerText = '100%';
      document.getElementById('insp-lbl-3').innerHTML = '<span class="kw-trash">Trash</span> (S0441)';
      document.getElementById('insp-stat-trash').innerText = stats.trash.toLocaleString();
      document.getElementById('insp-lbl-4').innerHTML = '<span class="kw-recycle">Recycling</span> (S0321)';
      document.getElementById('insp-stat-rec').innerText = stats.rec.toLocaleString();
      document.getElementById('insp-details').innerText = `Evaluating ${{stats.total.toLocaleString()}} 311 missed collection service requests across all 8 Wards, 46 ANCs, and 345 Single Member Districts over the ${{periodLabel.toLowerCase()}}.`;
      document.getElementById('insp-route-box').style.display = 'none';
    }}

    function updateInspectorWard(p) {{
      const periodLabel = currentPeriod === '30d' ? 'Past 30 Days' : 'Past 180 Days';
      const m = currentPeriod === '30d' ? p.metrics_30d : p.metrics_180d;
      const total = m ? m.total : p.total;
      const trash = m ? m.trash : p.trash;
      const rec = m ? m.recycling : p.recycling;
      const cityTot = getCitywideStats(currentPeriod).total;
      const share = cityTot > 0 ? (total / cityTot * 100).toFixed(1) : '0.0';

      document.getElementById('insp-title').innerText = `Ward ${{p.ward}}`;
      document.getElementById('insp-sub').innerText = `Councilmember: ${{p.councilmember || WARD_COUNCIL[p.ward] || 'DC Council'}}`;
      document.getElementById('insp-lbl-1').innerText = 'Selected Requests';
      document.getElementById('insp-stat-total').innerText = total.toLocaleString();
      document.getElementById('insp-lbl-2').innerText = 'Share of Volume';
      document.getElementById('insp-stat-share').innerText = `${{share}}%`;
      document.getElementById('insp-lbl-3').innerHTML = '<span class="kw-trash">Trash</span> (S0441)';
      document.getElementById('insp-stat-trash').innerText = trash.toLocaleString();
      document.getElementById('insp-lbl-4').innerHTML = '<span class="kw-recycle">Recycling</span> (S0321)';
      document.getElementById('insp-stat-rec').innerText = rec.toLocaleString();
      document.getElementById('insp-details').innerText = `Ward ${{p.ward}} accounts for ${{total.toLocaleString()}} missed collections (${{share}}% of citywide volume) over the ${{periodLabel.toLowerCase()}}.`;
      document.getElementById('insp-route-box').style.display = 'none';
      ensureMobileInspectorOpen();
    }}

    function updateInspectorANC(ancId) {{
      const periodLabel = currentPeriod === '30d' ? 'Past 30 Days' : 'Past 180 Days';
      const smdsInAnc = MAP_DATA.smds.features.filter(f => f.properties.anc_id === ancId);
      let total = 0, trash = 0, rec = 0;
      smdsInAnc.forEach(f => {{
        const m = currentPeriod === '30d' ? f.properties.metrics_30d : f.properties.metrics_180d;
        total += (m ? m.total : f.properties.total) || 0;
        trash += (m ? m.trash : f.properties.trash) || 0;
        rec += (m ? m.recycling : f.properties.recycling) || 0;
      }});
      const ward = smdsInAnc[0]?.properties.ward;
      const cityTot = getCitywideStats(currentPeriod).total;
      const share = cityTot > 0 ? (total / cityTot * 100).toFixed(1) : '0.0';

      document.getElementById('insp-title').innerText = `ANC ${{ancId}}`;
      document.getElementById('insp-sub').innerText = `Ward ${{ward}} • ${{smdsInAnc.length}} Single Member Districts`;
      document.getElementById('insp-lbl-1').innerText = 'Selected Requests';
      document.getElementById('insp-stat-total').innerText = total.toLocaleString();
      document.getElementById('insp-lbl-2').innerText = 'Share of Volume';
      document.getElementById('insp-stat-share').innerText = `${{share}}%`;
      document.getElementById('insp-lbl-3').innerHTML = '<span class="kw-trash">Trash</span> (S0441)';
      document.getElementById('insp-stat-trash').innerText = trash.toLocaleString();
      document.getElementById('insp-lbl-4').innerHTML = '<span class="kw-recycle">Recycling</span> (S0321)';
      document.getElementById('insp-stat-rec').innerText = rec.toLocaleString();
      document.getElementById('insp-details').innerText = `ANC ${{ancId}} contains ${{smdsInAnc.length}} Single Member Districts with ${{total.toLocaleString()}} missed requests over the ${{periodLabel.toLowerCase()}}.`;
      document.getElementById('insp-route-box').style.display = 'none';
      ensureMobileInspectorOpen();
    }}

    function updateInspectorSMD(p, centerLatLng) {{
      const periodLabel = currentPeriod === '30d' ? 'Past 30 Days' : 'Past 180 Days';
      const m = currentPeriod === '30d' ? p.metrics_30d : p.metrics_180d;
      const total = m ? m.total : p.total;
      const trash = m ? m.trash : p.trash;
      const rec = m ? m.recycling : p.recycling;
      const wardShare = m ? m.ward_share_pct : (p.ward_share_pct || 0);

      document.getElementById('insp-title').innerText = `SMD ${{p.smd_id}}`;
      document.getElementById('insp-sub').innerText = `Councilmember: ${{WARD_COUNCIL[p.ward] || 'DC Council'}}`;
      document.getElementById('insp-lbl-1').innerText = 'Selected Requests';
      document.getElementById('insp-stat-total').innerText = total.toLocaleString();
      document.getElementById('insp-lbl-2').innerText = 'Share of Volume';
      document.getElementById('insp-stat-share').innerText = `${{wardShare}}%`;
      document.getElementById('insp-lbl-3').innerHTML = '<span class="kw-trash">Trash</span> (S0441)';
      document.getElementById('insp-stat-trash').innerText = trash.toLocaleString();
      document.getElementById('insp-lbl-4').innerHTML = '<span class="kw-recycle">Recycling</span> (S0321)';
      document.getElementById('insp-stat-rec').innerText = rec.toLocaleString();
      document.getElementById('insp-details').innerText = `SMD ${{p.smd_id}} represents ${{wardShare}}% of Ward ${{p.ward}}'s total missed collections over the ${{periodLabel.toLowerCase()}}.`;

      const rBox = document.getElementById('insp-route-box');
      if (rBox) {{
        rBox.innerHTML = '';
        rBox.style.display = 'none';
      }}
      ensureMobileInspectorOpen();
    }}

    function updateInspectorRoute(p, stream) {{
      const rId = stream === 'Trash' ? (p.route_area || p.route) : p.route;
      const isLine = !!p.point_count;
      const linePrefix = isLine ? 'line_' : '';
      const key = (stream === 'Trash' ? ('trash_' + linePrefix) : ('recycle_' + linePrefix)) + rId;
      const fallbackKey = (stream === 'Trash' ? 'trash_' : 'recycle_') + rId;
      const stats = ROUTE_STATS[key] || ROUTE_STATS[fallbackKey] || {{}};

      const sched = (stats.schedule && stats.schedule !== 'Unassigned' ? stats.schedule : '') || p.days || p.day || stats.day || 'Scheduled';
      const ward = p.ward || stats.ward || 'Citywide';
      const total = stats.total != null ? stats.total : (p.total || 0);
      const repRate = stats.repeat_rate != null ? stats.repeat_rate : (p.repeat_rate != null ? p.repeat_rate : 0);
      const uniqAddrs = stats.unique_addrs != null ? stats.unique_addrs : (p.unique_addrs || 0);
      const density = stats.density != null ? stats.density : (p.density != null ? p.density : (stats.area_sq_mi > 0 ? (total / stats.area_sq_mi).toFixed(1) : 0));
      const areaSqMi = (isLine ? (p.area_sq_mi || stats.area_sq_mi) : (stats.area_sq_mi || p.area_sq_mi)) || 0;

      const typeBadge = isLine
        ? '<span style="font-size: 11px; font-weight: 600; color: var(--text-dim); margin-left: 6px;">(Line Route)</span>'
        : '<span style="font-size: 11px; font-weight: 600; color: var(--text-dim); margin-left: 6px;">(Polygon)</span>';

      document.getElementById('insp-title').innerHTML = `<span class="${{stream === 'Trash' ? 'kw-trash' : 'kw-recycle'}}">${{stream}}</span> Route ${{rId}} ${{typeBadge}}`;
      document.getElementById('insp-sub').innerText = `Collection day: ${{sched}} • ${{ward}}`;

      document.getElementById('insp-lbl-1').innerText = 'Total Requests';
      document.getElementById('insp-stat-total').innerText = total.toLocaleString();

      document.getElementById('insp-lbl-2').innerText = 'Repeat Rate';
      document.getElementById('insp-stat-share').innerText = `${{repRate}}%`;

      document.getElementById('insp-lbl-3').innerText = 'Unique Addrs';
      document.getElementById('insp-stat-trash').innerText = uniqAddrs.toLocaleString();

      document.getElementById('insp-lbl-4').innerText = 'Density';
      document.getElementById('insp-stat-rec').innerText = `${{density}} /sq mi`;

      const nbhDesc = p.neighborhoods || stats.neighborhoods || 'Residential Corridor';
      const ancsDesc = formatSortedAncs(p.ancs || stats.ancs || '');
      const geomType = isLine ? 'street network alignment' : 'polygon catchment area';

      document.getElementById('insp-details').innerHTML = `<span class="${{stream === 'Trash' ? 'kw-trash' : 'kw-recycle'}}">${{stream}}</span> Route ${{rId}} covers ${{areaSqMi > 0 ? areaSqMi + ' sq mi in ' : ''}}${{ward}} (${{nbhDesc}}), recording ${{total.toLocaleString()}} missed collection service requests across ${{uniqAddrs.toLocaleString()}} unique addresses with a ${{repRate}}% repeat rate over 180 days (viewed via ${{geomType}}).`;

      const pointInfo = isLine
        ? `<div style="font-size: 11px; color: var(--text-dim); margin-top: 2px;">Collection Points: <strong style="color: var(--text-main);">${{(p.point_count || 0).toLocaleString()}}</strong> (${{(p.segment_count || 0).toLocaleString()}} street segments)</div>`
        : '';

      const rBox = document.getElementById('insp-route-box');
      rBox.innerHTML = `
        <div style="font-weight: 700; font-size: 11px; margin-bottom: 4px; text-transform: uppercase;">Route Geography & Service:</div>
        <div style="font-size: 11px; color: var(--text-dim);">Neighborhoods: <strong style="color: var(--text-main);">${{nbhDesc}}</strong></div>
        ${{ancsDesc ? `<div style="font-size: 11px; color: var(--text-dim); margin-top: 2px;">ANCs: <strong style="color: var(--text-main);">${{ancsDesc}}</strong></div>` : ''}}
        ${{areaSqMi > 0 ? `<div style="font-size: 11px; color: var(--text-dim); margin-top: 2px;">Area: <strong style="color: var(--text-main);">${{areaSqMi}} sq mi</strong> (${{density}} req/sq mi)</div>` : ''}}
        ${{pointInfo}}
      `;
      rBox.style.display = 'block';

      ensureMobileInspectorOpen();
    }}

    function setMetric(metric) {{
      if (!MAP_DATA) return;
      currentMetric = metric;
      document.getElementById('btn-total').classList.toggle('active', metric === 'total');
      document.getElementById('btn-trash').classList.toggle('active', metric === 'trash');
      document.getElementById('btn-recycling').classList.toggle('active', metric === 'recycling');
      updateLegend();
      if (smdLayer) smdLayer.setStyle(smdStyle);
    }}

    function setPeriod(period) {{
      if (!MAP_DATA) return;
      currentPeriod = period;
      document.getElementById('btn-period-180d').classList.toggle('active', period === '180d');
      document.getElementById('btn-period-30d').classList.toggle('active', period === '30d');

      updateLegend();
      if (smdLayer) smdLayer.setStyle(smdStyle);

      // Refresh currently active inspector
      if (selectedRouteId && selectedRouteLayer) {{
        updateInspectorRoute(selectedRouteLayer.feature.properties, selectedRouteStream);
      }} else if (selectedSmdId) {{
        const feat = MAP_DATA.smds.features.find(f => f.properties.smd_id === selectedSmdId);
        let centerLatLng = null;
        smdLayer.eachLayer(l => {{
          if (l.feature.properties.smd_id === selectedSmdId) centerLatLng = l.getBounds().getCenter();
        }});
        if (feat) updateInspectorSMD(feat.properties, centerLatLng);
      }} else if (selectedAncId) {{
        updateInspectorANC(selectedAncId);
      }} else if (selectedWardNum) {{
        const wFeat = MAP_DATA.wards.features.find(f => f.properties.ward === selectedWardNum);
        if (wFeat) updateInspectorWard(wFeat.properties);
      }} else {{
        updateInspectorCitywide();
      }}
    }}

    function updateLegend() {{
      const pal = PALETTES[currentMetric];
      const th = THRESHOLDS[currentPeriod][currentMetric];
      const scaleEl = document.getElementById('legend-scale');
      scaleEl.innerHTML = pal.map(c => `<div class="scale-box" style="background: ${{c}};"></div>`).join('');
      const streamName = currentMetric === 'total' ? '<span class="kw-combined">Combined</span>' : (currentMetric === 'trash' ? '<span class="kw-trash">Trash</span>' : '<span class="kw-recycle">Recycling</span>');
      const periodLabel = currentPeriod === '30d' ? '30 Days' : '180 Days';
      document.getElementById('legend-title').innerHTML = `${{streamName}} Requests (${{periodLabel}})`;
      document.getElementById('legend-labels').innerHTML = `
        <span>0</span>
        <span>${{th[1]}}</span>
        <span>${{th[3]}}</span>
        <span>${{th[5]}}+</span>
      `;

      const marker311 = document.getElementById('marker-311-requests');
      if (marker311) {{
        if (currentMetric === 'trash') {{
          marker311.style.background = 'var(--trash-color)';
        }} else if (currentMetric === 'recycling') {{
          marker311.style.background = 'var(--recycle-color)';
        }} else {{
          marker311.style.background = 'var(--combined-color)';
        }}
      }}
    }}

    function toggleTheme() {{
      const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
      setTheme(nextTheme);
    }}

    function setTheme(theme) {{
      currentTheme = theme;
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('dc_map_theme', theme);
      document.getElementById('theme-toggle-btn').innerText = theme === 'dark' ? 'Theme: Dark' : 'Theme: Light';

      if (baseTileLayer) {{
        baseTileLayer.setUrl(getTileUrl(theme));
      }}
      if (smdLayer) smdLayer.setStyle(smdStyle);
      if (wardLayer) wardLayer.setStyle(wardStyle);
      const isDark = theme === 'dark';
      if (trashRoutesLayer) {{
        trashRoutesLayer.eachLayer(l => {{
          if (selectedRouteLayers.includes(l)) {{
            l.setStyle({{
              color: isDark ? '#f87171' : '#b91c1c',
              weight: 4.5,
              opacity: 1.0,
              fill: true,
              fillColor: isDark ? 'url(#hatch-trash-dark-hover)' : 'url(#hatch-trash-hover)',
              fillOpacity: 1.0
            }});
          }} else {{
            l.setStyle(getTrashRouteStyle());
          }}
        }});
      }}
      if (recycleRoutesLayer) {{
        recycleRoutesLayer.eachLayer(l => {{
          if (selectedRouteLayers.includes(l)) {{
            l.setStyle({{
              color: isDark ? '#4ade80' : '#15803d',
              weight: 4.5,
              opacity: 1.0,
              fill: true,
              fillColor: isDark ? 'url(#hatch-recycle-dark-hover)' : 'url(#hatch-recycle-hover)',
              fillOpacity: 1.0
            }});
          }} else {{
            l.setStyle(getRecycleRouteStyle());
          }}
        }});
      }}
      if (trashLinesLayer) {{
        trashLinesLayer.eachLayer(l => {{
          if (selectedRouteLayers.includes(l)) {{
            l.setStyle({{
              color: isDark ? '#f87171' : '#b91c1c',
              weight: 6.5,
              opacity: 1.0
            }});
          }} else {{
            l.setStyle(getTrashLineStyle());
          }}
        }});
      }}
      if (recycleLinesLayer) {{
        recycleLinesLayer.eachLayer(l => {{
          if (selectedRouteLayers.includes(l)) {{
            l.setStyle({{
              color: isDark ? '#4ade80' : '#15803d',
              weight: 6.5,
              opacity: 1.0
            }});
          }} else {{
            l.setStyle(getRecycleLineStyle());
          }}
        }});
      }}
      ensureSelectedRoutesOnTop();
    }}

    function toggleSMDLayer(show) {{
      if (show) {{
        map.addLayer(smdLayer);
      }} else {{
        map.removeLayer(smdLayer);
        smdTooltip.close();
      }}
    }}

    function toggleTrashRoutes(show) {{
      if (show) {{
        map.addLayer(trashRoutesLayer);
        ensureSvgPatterns();
        trashRoutesLayer.setStyle(getTrashRouteStyle());
        ensureSelectedRoutesOnTop();
      }} else {{
        if (selectedRouteStream === 'Trash' && !selectedRouteIsLine) {{
          clearRouteSelection();
          updateInspectorCitywide();
          updateBreadcrumbs();
        }}
        map.removeLayer(trashRoutesLayer);
        clearRouteHover();
      }}
    }}

    function toggleRecycleRoutes(show) {{
      if (show) {{
        map.addLayer(recycleRoutesLayer);
        ensureSvgPatterns();
        recycleRoutesLayer.setStyle(getRecycleRouteStyle());
        ensureSelectedRoutesOnTop();
      }} else {{
        if (selectedRouteStream === 'Recycling' && !selectedRouteIsLine) {{
          clearRouteSelection();
          updateInspectorCitywide();
          updateBreadcrumbs();
        }}
        map.removeLayer(recycleRoutesLayer);
        clearRouteHover();
      }}
    }}

    function toggleTrashLines(show) {{
      if (!trashLinesLayer) initTrashLinesLayer();
      if (show) {{
        if (trashLinesLayer && !map.hasLayer(trashLinesLayer)) {{
          map.addLayer(trashLinesLayer);
          trashLinesLayer.setStyle(getTrashLineStyle());
          ensureSelectedRoutesOnTop();
        }}
      }} else {{
        if (trashLinesLayer && map.hasLayer(trashLinesLayer)) {{
          if (selectedRouteStream === 'Trash' && selectedRouteIsLine) {{
            clearRouteSelection();
            updateInspectorCitywide();
            updateBreadcrumbs();
          }}
          map.removeLayer(trashLinesLayer);
          clearRouteHover();
        }}
      }}
    }}

    function toggleRecycleLines(show) {{
      if (!recycleLinesLayer) initRecycleLinesLayer();
      if (show) {{
        if (recycleLinesLayer && !map.hasLayer(recycleLinesLayer)) {{
          map.addLayer(recycleLinesLayer);
          recycleLinesLayer.setStyle(getRecycleLineStyle());
          ensureSelectedRoutesOnTop();
        }}
      }} else {{
        if (recycleLinesLayer && map.hasLayer(recycleLinesLayer)) {{
          if (selectedRouteStream === 'Recycling' && selectedRouteIsLine) {{
            clearRouteSelection();
            updateInspectorCitywide();
            updateBreadcrumbs();
          }}
          map.removeLayer(recycleLinesLayer);
          clearRouteHover();
        }}
      }}
    }}

    function resetToDefault() {{
      selectedWardNum = null;
      selectedAncId = null;
      selectedSmdId = null;
      clearRouteSelection();

      updateDropdowns(null, null, null);
      document.getElementById('smd-search').value = '';

      currentMetric = 'total';
      document.getElementById('btn-total').classList.add('active');
      document.getElementById('btn-trash').classList.remove('active');
      document.getElementById('btn-recycling').classList.remove('active');

      currentPeriod = '180d';
      document.getElementById('btn-period-180d').classList.add('active');
      document.getElementById('btn-period-30d').classList.remove('active');

      document.getElementById('chk-smd').checked = true;
      if (!map.hasLayer(smdLayer)) map.addLayer(smdLayer);

      document.getElementById('chk-trash-routes').checked = false;
      if (trashRoutesLayer && map.hasLayer(trashRoutesLayer)) map.removeLayer(trashRoutesLayer);

      document.getElementById('chk-recycle-routes').checked = false;
      if (recycleRoutesLayer && map.hasLayer(recycleRoutesLayer)) map.removeLayer(recycleRoutesLayer);

      document.getElementById('chk-trash-lines').checked = false;
      if (trashLinesLayer && map.hasLayer(trashLinesLayer)) map.removeLayer(trashLinesLayer);

      document.getElementById('chk-recycle-lines').checked = false;
      if (recycleLinesLayer && map.hasLayer(recycleLinesLayer)) map.removeLayer(recycleLinesLayer);

      map.setView([38.9072, -77.01], 12);
      updateWardMask();
      if (smdLayer) smdLayer.setStyle(smdStyle);
      if (wardLayer) wardLayer.setStyle(wardStyle);

      smdTooltip.close();
      map.closePopup();

      updateLegend();
      updateInspectorCitywide();
      updateBreadcrumbs();
    }}

    // Static Contextual Exports
    function getExportMetadata() {{
      const periodLabel = currentPeriod === '30d' ? '30-Day' : '180-Day';
      const streamLabel = currentMetric === 'total' ? 'Combined' : (currentMetric === 'trash' ? 'Trash' : 'Recycling');

      if (selectedRouteId) {{
        return {{
          title: `Route Operational Report: ${{selectedRouteStream}} Route ${{selectedRouteId}}${{selectedRouteType}}`,
          subtitle: `Collection Day & Geographic Alignment • ${{periodLabel}} Window`,
          metrics: `Active Route: ${{selectedRouteStream}} Route ${{selectedRouteId}}${{selectedRouteType}}`,
          filename: `dc-map-route-${{selectedRouteStream.toLowerCase()}}-${{selectedRouteId}}-${{currentPeriod}}`
        }};
      }} else if (selectedSmdId) {{
        const feat = MAP_DATA.smds.features.find(f => f.properties.smd_id === selectedSmdId);
        const p = feat ? feat.properties : {{}};
        const m = currentPeriod === '30d' ? p.metrics_30d : p.metrics_180d;
        const tot = m ? m.total : p.total;
        const tr = m ? m.trash : p.trash;
        const rec = m ? m.recycling : p.recycling;
        const ws = m ? m.ward_share_pct : (p.ward_share_pct || 0);
        return {{
          title: `Single Member District Report: SMD ${{selectedSmdId}}`,
          subtitle: `ANC ${{p.anc_id || selectedAncId}} • Ward ${{p.ward || selectedWardNum}} • Councilmember: ${{WARD_COUNCIL[p.ward] || ''}}`,
          metrics: `${{periodLabel}} Missed Requests: Total: ${{tot}} | Trash: ${{tr}} | Recycling: ${{rec}} (Ward Share: ${{ws}}%)`,
          filename: `dc-map-smd-${{selectedSmdId}}-${{currentPeriod}}`
        }};
      }} else if (selectedAncId) {{
        return {{
          title: `Advisory Neighborhood Commission Report: ANC ${{selectedAncId}}`,
          subtitle: `Ward ${{selectedWardNum || ''}}`,
          metrics: `Active Metric: ${{streamLabel}} Missed Collection Requests (${{periodLabel}})`,
          filename: `dc-map-anc-${{selectedAncId}}-${{currentPeriod}}`
        }};
      }} else if (selectedWardNum) {{
        return {{
          title: `Ward Operational Report: Ward ${{selectedWardNum}}`,
          subtitle: `Councilmember: ${{WARD_COUNCIL[selectedWardNum] || ''}}`,
          metrics: `Active Metric: ${{streamLabel}} Missed Collection Requests (${{periodLabel}})`,
          filename: `dc-map-ward-${{selectedWardNum}}-${{currentPeriod}}`
        }};
      }} else {{
        return {{
          title: 'Missed Collections',
          subtitle: `Citywide Spatial Explorer • ${{periodLabel}} Window`,
          metrics: `Active Metric: ${{streamLabel}} Requests across all 8 Wards and 345 SMDs`,
          filename: `dc-map-citywide-${{currentPeriod}}`
        }};
      }}
    }}

    async function exportMapPdf() {{
      const meta = getExportMetadata();
      const mapEl = document.getElementById('map-interactive');

      const canvas = await html2canvas(mapEl, {{
        useCORS: true,
        allowTaint: true,
        scale: 2.0
      }});

      const {{ jsPDF }} = window.jspdf;
      // US Letter Landscape: 11" x 8.5"
      const doc = new jsPDF({{ orientation: 'landscape', format: 'letter', unit: 'in' }});
      const imgData = canvas.toDataURL('image/png');

      // Title & Context Header
      doc.setFont('Courier', 'bold');
      doc.setFontSize(15);
      doc.setTextColor(15, 23, 42);
      doc.text(meta.title, 0.5, 0.6);

      doc.setFont('Courier', 'normal');
      doc.setFontSize(10);
      doc.setTextColor(51, 65, 85);
      doc.text(meta.subtitle, 0.5, 0.82);

      doc.setFontSize(9);
      doc.setTextColor(100, 116, 139);
      doc.text(meta.metrics, 0.5, 1.02);
      doc.text(`Generated: ${{new Date().toLocaleDateString()}} • Stamen Toner Basemap`, 10.5, 1.02, {{ align: 'right' }});

      doc.addImage(imgData, 'PNG', 0.5, 1.15, 10.0, 6.75);
      doc.save(`${{meta.filename}}.pdf`);
    }}

    async function exportMapPng() {{
      const meta = getExportMetadata();
      const mapEl = document.getElementById('map-interactive');
      const canvas = await html2canvas(mapEl, {{
        useCORS: true,
        allowTaint: true,
        scale: 2.0
      }});
      const url = canvas.toDataURL('image/png');
      const a = document.createElement('a');
      a.href = url;
      a.download = `${{meta.filename}}.png`;
      a.click();
    }}

    // Mobile Drawer & Filter Toggles
    function toggleMobilePanel(type) {{
      if (window.innerWidth > 768) return;
      if (type === 'control') {{
        const cp = document.getElementById('control-panel');
        const body = document.getElementById('ctrl-panel-body');
        const icon = document.getElementById('ctrl-toggle-icon');
        const isHidden = body.style.display === 'none';
        body.style.display = isHidden ? 'block' : 'none';
        if (cp) cp.classList.toggle('is-expanded', isHidden);
        if (icon) icon.innerText = isHidden ? '▴' : '▾';
      }} else if (type === 'inspector') {{
        const body = document.getElementById('insp-panel-body');
        const icon = document.getElementById('insp-toggle-icon');
        const isHidden = body.style.display === 'none';
        body.style.display = isHidden ? 'block' : 'none';
        if (icon) icon.innerText = isHidden ? '▾' : '▴';
      }}
    }}

    function ensureMobileInspectorOpen() {{
      if (window.innerWidth <= 768) {{
        const body = document.getElementById('insp-panel-body');
        const icon = document.getElementById('insp-toggle-icon');
        if (body) body.style.display = 'block';
        if (icon) icon.innerText = '▾';
      }}
    }}

    function initMobileHandling() {{
      const cp = document.getElementById('control-panel');
      const insp = document.getElementById('inspector-panel');
      if (cp) {{
        L.DomEvent.disableClickPropagation(cp);
        L.DomEvent.disableScrollPropagation(cp);
      }}
      if (insp) {{
        L.DomEvent.disableClickPropagation(insp);
        L.DomEvent.disableScrollPropagation(insp);
      }}

      // Initial state on mobile: collapse controls so map is prominent
      if (window.innerWidth <= 768) {{
        const ctrlBody = document.getElementById('ctrl-panel-body');
        if (ctrlBody) ctrlBody.style.display = 'none';
        const ctrlIcon = document.getElementById('ctrl-toggle-icon');
        if (ctrlIcon) ctrlIcon.innerText = '▾';
      }}
    }}

    function initMapData(data) {{
      MAP_DATA = data;
      buildRouteSpatialIndex();
      initSMDLayer();
      initWardLayer();
      initTrashRoutesLayer();
      initRecycleRoutesLayer();
      initTrashLinesLayer();
      initRecycleLinesLayer();
      ensureSvgPatterns();
      updateLegend();
      resetToCitywide();

      const loadingEl = document.getElementById('map-loading');
      if (loadingEl) {{
        loadingEl.style.opacity = '0';
        setTimeout(() => {{
          loadingEl.style.display = 'none';
        }}, 200);
      }}

      window.__MAP_DATA_LOADED = true;
      window.dispatchEvent(new CustomEvent('map-data-loaded'));
    }}

    // Initialization
    initMobileHandling();
    setTheme(currentTheme);
    map.on('layeradd', function() {{
      ensureSvgPatterns();
      ensureSelectedRoutesOnTop();
    }});
    map.on('zoomend', ensureSelectedRoutesOnTop);

    fetch('data/dc_map_data_v2.json')
      .then(res => {{
        if (!res.ok) throw new Error(`HTTP ${{res.status}}: ${{res.statusText}}`);
        return res.json();
      }})
      .then(data => {{
        initMapData(data);
      }})
      .catch(err => {{
        console.error('Failed to load map data:', err);
        const loadingBox = document.getElementById('map-loading-box');
        if (loadingBox) {{
          const isFile = window.location.protocol === 'file:';
          loadingBox.innerHTML = `
            <div style="font-weight: 700; font-size: 14px; margin-bottom: 8px; color: var(--accent-trash);">Unable to Load Map Data</div>
            <div style="font-size: 12px; color: var(--text-dim); line-height: 1.5; margin-bottom: 12px;">
              ${{isFile
                ? 'Browsers restrict asynchronous fetch requests over direct <code>file://</code> URLs. To run locally, start a local server:<br><br><code style="background: var(--bg-surface); padding: 3px 6px; border: 1px solid var(--border);">python3 -m http.server 8000</code><br><br>then open <code style="background: var(--bg-surface); padding: 3px 6px; border: 1px solid var(--border);">http://localhost:8000/map.html</code>.'
                : 'Failed to fetch <code>data/dc_map_data_v2.json</code> (' + err.message + ').'}}
            </div>
            ${{isFile ? '<div style="font-size: 11px; color: var(--text-dim);">Alternatively, view the live hosted map on <a href="https://zacheadams.github.io/dc-missed-collection-analysis/map.html" target="_blank" rel="noopener" style="color: var(--accent-combined); text-decoration: underline;">GitHub Pages</a>.</div>' : ''}}
          `;
        }}
      }});

  </script>
</body>
</html>
'''

out_map = os.path.join(BASE_DIR, 'map.html')
with open(out_map, 'w', encoding='utf-8') as f:
    f.write(html_page)

print(f"Successfully compiled Dedicated Interactive Map: {out_map}")

if __name__ == '__main__':
    pass
