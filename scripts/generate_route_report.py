#!/usr/bin/env python3
"""
Generate comprehensive DPW Trash and Recycling Route-Level Analysis and Visualizations.
Produces data/route_180d_stats.json and routes.html.
"""

import json
import os
from collections import defaultdict
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sr_path = os.path.join(BASE_DIR, 'data/dc_180d_service_requests.json')
trash_path = os.path.join(BASE_DIR, 'data/dc_trash_routes.geojson')
rec_path = os.path.join(BASE_DIR, 'data/dc_recycle_routes.geojson')

with open(sr_path) as f:
    srs = json.load(f)

with open(trash_path) as f:
    trash_geojson = json.load(f)

with open(rec_path) as f:
    recycle_geojson = json.load(f)

def prep_routes(feats, id_key):
    res = []
    for f in feats:
        g = f['geometry']
        polys = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
        all_pts = [pt for poly in polys for ring in poly for pt in ring]
        xs = [p[0] for p in all_pts]
        ys = [p[1] for p in all_pts]
        res.append({
            'id': f['properties'][id_key],
            'props': f['properties'],
            'bbox': (min(xs), min(ys), max(xs), max(ys)),
            'polys': polys
        })
    return res

trash_routes = prep_routes(trash_geojson['features'], 'TrashRouteArea')
recycle_routes = prep_routes(recycle_geojson['features'], 'Route')

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

def find_match(x, y, routes):
    for r in routes:
        if x < r['bbox'][0] or x > r['bbox'][2] or y < r['bbox'][1] or y > r['bbox'][3]:
            continue
        if any(is_point_in_poly(x, y, p) for p in r['polys']):
            return r
    return None

# Deduplicate unique routes by ID
unique_trash_props = {}
for r in trash_routes:
    if r['id'] not in unique_trash_props:
        unique_trash_props[r['id']] = r['props']

unique_rec_props = {}
for r in recycle_routes:
    if r['id'] not in unique_rec_props:
        unique_rec_props[r['id']] = r['props']

trash_data = {rid: {'total': 0, 'addrs': defaultdict(set), 'props': props} for rid, props in unique_trash_props.items()}
recycle_data = {rid: {'total': 0, 'addrs': defaultdict(set), 'props': props} for rid, props in unique_rec_props.items()}

for sr in srs:
    attr = sr['attributes']
    code = attr.get('SERVICECODE')
    x = attr.get('LONGITUDE')
    y = attr.get('LATITUDE')
    if not x or not y:
        continue
    addr = attr.get('STREETADDRESS')
    mar = attr.get('MARADDRESSREPOSITORYID')
    addr_key = f"{mar}_{addr}" if mar else addr
    dt_ms = attr.get('ADDDATE')
    dt_str = datetime.fromtimestamp(dt_ms / 1000).strftime('%Y-%m-%d') if dt_ms else 'unknown'

    if code == 'S0441':
        m = find_match(x, y, trash_routes)
        if m:
            trash_data[m['id']]['total'] += 1
            trash_data[m['id']]['addrs'][addr_key].add(dt_str)
    elif code == 'S0321':
        m = find_match(x, y, recycle_routes)
        if m:
            recycle_data[m['id']]['total'] += 1
            recycle_data[m['id']]['addrs'][addr_key].add(dt_str)

trash_out = []
for rid, s in trash_data.items():
    u = len(s['addrs'])
    r = sum(1 for a, dts in s['addrs'].items() if len(dts) >= 2)
    p = s['props']
    rr = round(r / u * 100, 1) if u else 0.0
    rpa = round(s['total'] / u, 2) if u else 0.0
    
    # Classification
    if s['total'] == 0:
        cls = 'Zero Tickets'
    elif rr >= 28.0 and r >= 10:
        cls = 'Chronic Recurrence'
    elif u >= 70:
        cls = 'Widespread Skips'
    else:
        cls = 'Standard Operation'

    trash_out.append({
        'route_id': rid,
        'type': 'Trash',
        'route_name': f"Trash Route {rid}",
        'schedule': p.get('CollectionDays', 'Unknown'),
        'service_area': p.get('ServiceArea', 'Unknown'),
        'runs_per_week': p.get('RunsPerWeek', 1),
        'status': p.get('TrashStatusUpdate', 'Active'),
        'total': s['total'],
        'unique_addrs': u,
        'repeat_addrs': r,
        'single_addrs': u - r,
        'repeat_rate': rr,
        'req_per_addr': rpa,
        'classification': cls
    })

recycle_out = []
for rid, s in recycle_data.items():
    u = len(s['addrs'])
    r = sum(1 for a, dts in s['addrs'].items() if len(dts) >= 2)
    p = s['props']
    rr = round(r / u * 100, 1) if u else 0.0
    rpa = round(s['total'] / u, 2) if u else 0.0

    # Classification
    if s['total'] == 0:
        cls = 'Zero Tickets'
    elif rr >= 28.0 and r >= 8:
        cls = 'Chronic Recurrence'
    elif u >= 40:
        cls = 'Widespread Skips'
    else:
        cls = 'Standard Operation'

    recycle_out.append({
        'route_id': rid,
        'type': 'Recycling',
        'route_name': f"Recycling Route {rid}",
        'schedule': p.get('CollectionDay', 'Unknown'),
        'service_area': p.get('RecycleRouteArea', 'District-Wide'),
        'runs_per_week': p.get('RunsPerWeek', 1),
        'status': p.get('RStatus', 'Active'),
        'total': s['total'],
        'unique_addrs': u,
        'repeat_addrs': r,
        'single_addrs': u - r,
        'repeat_rate': rr,
        'req_per_addr': rpa,
        'classification': cls
    })

# Save route data JSON
route_stats_path = os.path.join(BASE_DIR, 'data/route_180d_stats.json')
with open(route_stats_path, 'w') as f:
    json.dump({
        'metadata': {
            'period': '180 Days (March 24 – September 20, 2026)',
            'trash_routes_count': len(trash_out),
            'recycle_routes_count': len(recycle_out),
            'trash_requests_matched': sum(r['total'] for r in trash_out),
            'recycle_requests_matched': sum(r['total'] for r in recycle_out)
        },
        'trash_routes': trash_out,
        'recycle_routes': recycle_out
    }, f, indent=2)

print(f"Exported data/route_180d_stats.json ({len(trash_out)} trash routes, {len(recycle_out)} recycle routes)")

# Chart Data Preparation
trash_sorted = sorted(trash_out, key=lambda x: x['total'], reverse=True)
rec_sorted = sorted(recycle_out, key=lambda x: x['total'], reverse=True)

top10_trash = trash_sorted[:10]
top10_rec = rec_sorted[:10]

# Chronic repeat routes
trash_chronic = sorted([r for r in trash_out if r['total'] >= 20], key=lambda x: x['repeat_rate'], reverse=True)[:8]
rec_chronic = sorted([r for r in recycle_out if r['total'] >= 15], key=lambda x: x['repeat_rate'], reverse=True)[:8]

# Scheduled Day aggregation
day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Monday/Thursday', 'Tuesday/Friday']

trash_by_day = {d: {'total': 0, 'unique': 0, 'repeat': 0} for d in day_order}
for r in trash_out:
    d = r['schedule']
    if d in trash_by_day:
        trash_by_day[d]['total'] += r['total']
        trash_by_day[d]['unique'] += r['unique_addrs']
        trash_by_day[d]['repeat'] += r['repeat_addrs']

rec_by_day = {d: {'total': 0, 'unique': 0, 'repeat': 0} for d in day_order}
for r in recycle_out:
    d = r['schedule']
    if d in rec_by_day:
        rec_by_day[d]['total'] += r['total']
        rec_by_day[d]['unique'] += r['unique_addrs']
        rec_by_day[d]['repeat'] += r['repeat_addrs']

# Service Area aggregation (Trash)
outer_ring_total = sum(r['total'] for r in trash_out if r['service_area'] == 'Outer Ring')
outer_ring_unique = sum(r['unique_addrs'] for r in trash_out if r['service_area'] == 'Outer Ring')
outer_ring_repeat = sum(r['repeat_addrs'] for r in trash_out if r['service_area'] == 'Outer Ring')
outer_ring_routes = sum(1 for r in trash_out if r['service_area'] == 'Outer Ring')

inner_city_total = sum(r['total'] for r in trash_out if r['service_area'] == 'Inner City')
inner_city_unique = sum(r['unique_addrs'] for r in trash_out if r['service_area'] == 'Inner City')
inner_city_repeat = sum(r['repeat_addrs'] for r in trash_out if r['service_area'] == 'Inner City')
inner_city_routes = sum(1 for r in trash_out if r['service_area'] == 'Inner City')

all_routes_combined = trash_out + recycle_out

# Compile routes.html
html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DC DPW Collection Routes Analysis • Trash &amp; Recycling Performance Report</title>
  
  <!-- Chart.js CDN -->
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  
  <!-- Google Fonts: Plus Jakarta Sans & JetBrains Mono -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">

  <style>
    :root {{
      --bg-dark: #070a12;
      --bg-card: #0d1322;
      --bg-panel: rgba(13, 19, 34, 0.94);
      --border: rgba(255, 255, 255, 0.11);
      --border-bright: rgba(56, 189, 248, 0.45);
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      --primary: #0284c7;
      --primary-light: #38bdf8;
      --trash-color: #ef4444;
      --recycle-color: #10b981;
      --warning-color: #f59e0b;
      --purple-color: #a855f7;
      --font-sans: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    body {{
      font-family: var(--font-sans);
      background-color: var(--bg-dark);
      color: var(--text-main);
      min-height: 100vh;
      line-height: 1.5;
      overflow-x: hidden;
      -webkit-font-smoothing: antialiased;
    }}

    .page-container {{
      max-width: 1480px;
      margin: 0 auto;
      padding: 24px 20px 80px 20px;
    }}

    /* Top Navigation */
    .top-nav {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
      padding: 12px 18px;
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 12px;
      flex-wrap: wrap;
      gap: 12px;
    }}

    .nav-links {{
      display: flex;
      align-items: center;
      gap: 14px;
      flex-wrap: wrap;
    }}

    .nav-link {{
      color: var(--text-muted);
      text-decoration: none;
      font-size: 13px;
      font-weight: 600;
      padding: 6px 12px;
      border-radius: 6px;
      transition: all 0.2s ease;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}

    .nav-link:hover {{
      color: var(--text-main);
      background: rgba(255, 255, 255, 0.06);
    }}

    .nav-link.active {{
      color: #38bdf8;
      background: rgba(56, 189, 248, 0.12);
      border: 1px solid rgba(56, 189, 248, 0.35);
    }}

    .github-link {{
      color: var(--text-muted);
      text-decoration: none;
      font-size: 13px;
      font-weight: 600;
      font-family: var(--font-mono);
      padding: 6px 12px;
      border: 1px solid var(--border);
      border-radius: 6px;
      transition: all 0.2s;
    }}

    .github-link:hover {{
      color: #fff;
      border-color: #38bdf8;
      background: rgba(56, 189, 248, 0.08);
    }}

    /* Header */
    .site-header {{
      margin-bottom: 28px;
    }}

    .site-title {{
      font-size: 26px;
      font-weight: 800;
      color: #ffffff;
      letter-spacing: -0.02em;
      margin-bottom: 6px;
    }}

    .site-subtitle {{
      color: var(--text-muted);
      font-size: 14px;
      max-width: 900px;
    }}

    /* KPI Grid */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 16px;
      margin-bottom: 32px;
    }}

    .kpi-card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 18px 20px;
      position: relative;
    }}

    .kpi-label {{
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--text-dim);
      margin-bottom: 6px;
    }}

    .kpi-val {{
      font-size: 26px;
      font-weight: 800;
      color: #ffffff;
      font-family: var(--font-mono);
      margin-bottom: 4px;
    }}

    .kpi-sub {{
      font-size: 12px;
      color: var(--text-muted);
    }}

    /* Section Styling */
    .section-title-wrap {{
      margin: 40px 0 20px 0;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      flex-wrap: wrap;
      gap: 10px;
    }}

    .section-heading {{
      font-size: 20px;
      font-weight: 800;
      color: #ffffff;
      letter-spacing: -0.01em;
    }}

    .section-desc {{
      font-size: 13px;
      color: var(--text-muted);
    }}

    /* Chart Grid */
    .chart-grid-2 {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(620px, 1fr));
      gap: 20px;
      margin-bottom: 24px;
    }}

    @media (max-width: 680px) {{
      .chart-grid-2 {{
        grid-template-columns: 1fr;
      }}
    }}

    .chart-card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 22px 24px;
      display: flex;
      flex-direction: column;
    }}

    .chart-header {{
      margin-bottom: 16px;
    }}

    .chart-title {{
      font-size: 15px;
      font-weight: 700;
      color: #ffffff;
      margin-bottom: 4px;
    }}

    .chart-sub {{
      font-size: 12px;
      color: var(--text-muted);
    }}

    .chart-canvas-wrap {{
      position: relative;
      flex: 1;
      min-height: 280px;
      width: 100%;
    }}

    .chart-footnote {{
      margin-top: 14px;
      padding-top: 10px;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      font-size: 11px;
      color: var(--text-dim);
      font-family: var(--font-mono);
      line-height: 1.4;
    }}

    /* Findings / Pattern Cards */
    .patterns-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(460px, 1fr));
      gap: 20px;
      margin-bottom: 32px;
    }}

    @media (max-width: 520px) {{
      .patterns-grid {{
        grid-template-columns: 1fr;
      }}
    }}

    .pattern-card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 22px 24px;
    }}

    .pattern-tag {{
      display: inline-block;
      font-size: 10px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      padding: 3px 8px;
      border-radius: 4px;
      margin-bottom: 10px;
    }}

    .tag-blue {{
      background: rgba(56, 189, 248, 0.15);
      color: #38bdf8;
      border: 1px solid rgba(56, 189, 248, 0.3);
    }}

    .tag-amber {{
      background: rgba(245, 158, 11, 0.15);
      color: #fbbf24;
      border: 1px solid rgba(245, 158, 11, 0.3);
    }}

    .tag-red {{
      background: rgba(239, 68, 68, 0.15);
      color: #f87171;
      border: 1px solid rgba(239, 68, 68, 0.3);
    }}

    .tag-purple {{
      background: rgba(168, 85, 247, 0.15);
      color: #c084fc;
      border: 1px solid rgba(168, 85, 247, 0.3);
    }}

    .pattern-title {{
      font-size: 16px;
      font-weight: 700;
      color: #ffffff;
      margin-bottom: 8px;
    }}

    .pattern-body {{
      font-size: 13px;
      color: var(--text-muted);
      line-height: 1.6;
      margin-bottom: 14px;
    }}

    .pattern-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
      margin-top: 10px;
    }}

    .pattern-table th {{
      text-align: left;
      padding: 6px 8px;
      color: var(--text-dim);
      font-weight: 700;
      font-size: 11px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }}

    .pattern-table td {{
      padding: 6px 8px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
      color: var(--text-main);
    }}

    /* Interactive Table Section */
    .table-controls {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      flex-wrap: wrap;
      gap: 12px;
    }}

    .filter-tabs {{
      display: flex;
      gap: 8px;
      background: var(--bg-card);
      padding: 4px;
      border-radius: 8px;
      border: 1px solid var(--border);
    }}

    .filter-tab {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 6px 14px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }}

    .filter-tab.active {{
      background: #0284c7;
      color: #ffffff;
    }}

    .table-search {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 8px 14px;
      font-size: 13px;
      color: #fff;
      min-width: 280px;
      outline: none;
      font-family: var(--font-sans);
    }}

    .table-search:focus {{
      border-color: #38bdf8;
    }}

    .table-card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 14px;
      overflow: hidden;
    }}

    .data-table-wrap {{
      overflow-x: auto;
      max-height: 600px;
    }}

    .data-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
      text-align: left;
    }}

    .data-table th {{
      background: #0f172a;
      color: var(--text-muted);
      font-weight: 700;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      padding: 12px 14px;
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: 0;
      z-index: 10;
      cursor: pointer;
      user-select: none;
      white-space: nowrap;
    }}

    .data-table th:hover {{
      color: #38bdf8;
    }}

    .data-table td {{
      padding: 10px 14px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
      color: var(--text-main);
      white-space: nowrap;
    }}

    .data-table tr:hover td {{
      background: rgba(255, 255, 255, 0.02);
    }}

    .pill {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 700;
      font-family: var(--font-mono);
    }}

    .pill-trash {{
      background: rgba(239, 68, 68, 0.15);
      color: #f87171;
      border: 1px solid rgba(239, 68, 68, 0.3);
    }}

    .pill-rec {{
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.3);
    }}

    .status-badge {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 10px;
      font-weight: 600;
    }}

    .status-widespread {{
      background: rgba(59, 130, 246, 0.15);
      color: #60a5fa;
      border: 1px solid rgba(59, 130, 246, 0.3);
    }}

    .status-chronic {{
      background: rgba(245, 158, 11, 0.15);
      color: #fbbf24;
      border: 1px solid rgba(245, 158, 11, 0.3);
    }}

    .status-standard {{
      background: rgba(148, 163, 184, 0.1);
      color: #94a3b8;
    }}

    .status-zero {{
      background: rgba(16, 185, 129, 0.1);
      color: #34d399;
    }}

    .table-footer {{
      padding: 12px 18px;
      background: #0f172a;
      border-top: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 11px;
      color: var(--text-dim);
      font-family: var(--font-mono);
      flex-wrap: wrap;
      gap: 10px;
    }}

    .footer-note {{
      margin-top: 40px;
      padding: 20px;
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 12px;
      font-size: 12px;
      color: var(--text-dim);
      line-height: 1.6;
    }}
  </style>
</head>
<body>

  <div class="page-container">

    <!-- Top Navigation -->
    <nav class="top-nav">
      <div class="nav-links">
        <a href="index.html" class="nav-link">&larr; District &amp; SMD Map &amp; Report</a>
        <a href="routes.html" class="nav-link active">DPW Route-Level Analysis</a>
      </div>
      <a href="https://github.com/zacheadams/dc-missed-collection-analysis" target="_blank" class="github-link">
        GitHub Repository
      </a>
    </nav>

    <!-- Header -->
    <header class="site-header">
      <h1 class="site-title">Washington, DC DPW Collection Routes Analysis</h1>
      <p class="site-subtitle">
        Operational performance evaluation across 103 DPW Trash Routes and 120 DPW Recycling Routes over the past 180 days (March 24 – September 20, 2026). This report analyzes address deduplication, distinct-day repeat failures, schedule bottlenecks, and service area dynamics.
      </p>
    </header>

    <!-- KPI Summary Grid -->
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">Matched Route Requests</div>
        <div class="kpi-val">8,751</div>
        <div class="kpi-sub">6,197 Trash • 2,554 Recycling</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Unique Complaining Properties</div>
        <div class="kpi-val">5,920</div>
        <div class="kpi-sub">1.48 requests / complaining address</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Multi-Day Repeat Properties</div>
        <div class="kpi-val">1,392</div>
        <div class="kpi-sub">23.5% chronic repeat failure rate (&ge;2 days)</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Route Coverage</div>
        <div class="kpi-val">223 Routes</div>
        <div class="kpi-sub">103 Trash Routes • 120 Recycling Routes</div>
      </div>
    </div>

    <!-- Section 1: Visualizations -->
    <div class="section-title-wrap">
      <div>
        <h2 class="section-heading">Operational Visualizations</h2>
        <div class="section-desc">Standalone charts with explicit time scope and data source footnotes for communications and reporting.</div>
      </div>
    </div>

    <!-- Charts Row 1: Top 10 Trash & Recycling Routes -->
    <div class="chart-grid-2">
      <!-- Chart 1: Top 10 Trash Routes -->
      <div class="chart-card">
        <div class="chart-header">
          <div class="chart-title">Top 10 Trash Routes by Missed Collections</div>
          <div class="chart-sub">Single-Incident Properties vs. Multi-Day Repeat Properties (180 Days)</div>
        </div>
        <div class="chart-canvas-wrap">
          <canvas id="chartTopTrash"></canvas>
        </div>
        <div class="chart-footnote">
          Source: DC Open Data 311 (S0441) • DPW Trash Route Boundaries • 180-Day Scope (March 24 – September 20, 2026)
        </div>
      </div>

      <!-- Chart 2: Top 10 Recycling Routes -->
      <div class="chart-card">
        <div class="chart-header">
          <div class="chart-title">Top 10 Recycling Routes by Missed Collections</div>
          <div class="chart-sub">Single-Incident Properties vs. Multi-Day Repeat Properties (180 Days)</div>
        </div>
        <div class="chart-canvas-wrap">
          <canvas id="chartTopRec"></canvas>
        </div>
        <div class="chart-footnote">
          Source: DC Open Data 311 (S0321) • DPW Recycling Route Boundaries • 180-Day Scope (March 24 – September 20, 2026)
        </div>
      </div>
    </div>

    <!-- Charts Row 2: Scheduled Day of Week & Chronic Recurrence -->
    <div class="chart-grid-2">
      <!-- Chart 3: Day of Week -->
      <div class="chart-card">
        <div class="chart-header">
          <div class="chart-title">Missed Collections by Scheduled Collection Day</div>
          <div class="chart-sub">Trash vs. Recycling Volume across Collection Days (180 Days)</div>
        </div>
        <div class="chart-canvas-wrap">
          <canvas id="chartDayOfWeek"></canvas>
        </div>
        <div class="chart-footnote">
          Source: DC Open Data 311 (S0441 / S0321) • DPW Route Schedules • 180-Day Scope (March 24 – September 20, 2026)
        </div>
      </div>

      <!-- Chart 4: Chronic Repeat Rates -->
      <div class="chart-card">
        <div class="chart-header">
          <div class="chart-title">Chronic Recurrence: Highest Multi-Day Repeat Rates</div>
          <div class="chart-sub">% of Complaining Properties Submitting Tickets Across &ge;2 Distinct Days (Min 15 Reqs)</div>
        </div>
        <div class="chart-canvas-wrap">
          <canvas id="chartChronic"></canvas>
        </div>
        <div class="chart-footnote">
          Source: DC Open Data 311 (S0441 / S0321) • Distinct-Day Address Deduplication • 180-Day Scope (March 24 – September 20, 2026)
        </div>
      </div>
    </div>

    <!-- Section 2: Key Findings & Identified Patterns -->
    <div class="section-title-wrap">
      <div>
        <h2 class="section-heading">Key Operational Patterns Identified</h2>
        <div class="section-desc">Core logistical and systemic failure modes revealed through route-level address analysis.</div>
      </div>
    </div>

    <div class="patterns-grid">
      <!-- Pattern 1 -->
      <div class="pattern-card">
        <span class="pattern-tag tag-blue">Pattern 1 • Concentration Skew</span>
        <h3 class="pattern-title">Extreme Pareto Distribution Across Truck Routes</h3>
        <p class="pattern-body">
          Missed collection complaints are heavily concentrated in a small minority of truck routes. The top 10 trash routes account for 23.1% of all missed trash tickets District-wide (1,432 of 6,197 requests). Similarly, the top 10 recycling routes drive 21.9% of all recycling failures. While the median trash route generated 51 requests over 180 days, high-failure corridors such as <strong>Route OR304</strong> (Upper Northwest) and <strong>Route IC203</strong> (Dupont/Adams Morgan) exceeded 198 to 220 requests each.
        </p>
        <table class="pattern-table">
          <thead>
            <tr><th>Metric</th><th>Top 10 Routes</th><th>Median Route</th><th>Bottom 25%</th></tr>
          </thead>
          <tbody>
            <tr><td>Trash Route Volume</td><td>143.2 reqs/route</td><td>51.0 reqs/route</td><td>14.0 reqs/route</td></tr>
            <tr><td>Recycling Route Volume</td><td>55.8 reqs/route</td><td>16.5 reqs/route</td><td>4.0 reqs/route</td></tr>
          </tbody>
        </table>
      </div>

      <!-- Pattern 2 -->
      <div class="pattern-card">
        <span class="pattern-tag tag-amber">Pattern 2 • Schedule Bottlenecks</span>
        <h3 class="pattern-title">Mid-Week Wednesday Trash Peak &amp; Early-Week Recycling Surge</h3>
        <p class="pattern-body">
          Evaluating tickets by scheduled pickup day reveals distinct weekly operational bottlenecks. For trash collection, <strong>Wednesday routes lead the District</strong> with 1,369 service requests (982 unique properties), followed by Tuesday/Friday twice-weekly routes (1,047 requests). For recycling, early-week operations on <strong>Monday and Tuesday account for 48.7% of all missed recycling complaints</strong> (1,245 of 2,554 requests), whereas Friday recycling routes generated fewer complaints (368 requests).
        </p>
        <table class="pattern-table">
          <thead>
            <tr><th>Collection Schedule</th><th>Trash Requests</th><th>Recycling Requests</th><th>Total Volume</th></tr>
          </thead>
          <tbody>
            <tr><td>Wednesday</td><td>1,369 reqs</td><td>522 reqs</td><td>1,891 reqs</td></tr>
            <tr><td>Tuesday (Single + 2x)</td><td>2,002 reqs</td><td>624 reqs</td><td>2,626 reqs</td></tr>
            <tr><td>Monday (Single + 2x)</td><td>1,448 reqs</td><td>621 reqs</td><td>2,069 reqs</td></tr>
            <tr><td>Friday (Single)</td><td>857 reqs</td><td>368 reqs</td><td>1,225 reqs</td></tr>
            <tr><td>Thursday (Single)</td><td>521 reqs</td><td>419 reqs</td><td>940 reqs</td></tr>
          </tbody>
        </table>
      </div>

      <!-- Pattern 3 -->
      <div class="pattern-card">
        <span class="pattern-tag tag-purple">Pattern 3 • Failure Typology</span>
        <h3 class="pattern-title">Widespread Route Skips vs. Chronic Resolution Failures</h3>
        <p class="pattern-body">
          Address-level deduplication identifies two fundamentally different failure mechanics:
          <br><br>
          <strong>Widespread Route Bypasses:</strong> Routes such as <strong>OR706</strong> and <strong>OR708</strong> in Ward 7 exhibit high unique address counts (96 to 98 properties) but relatively low repeat rates (18.4% to 21.9%). Collection crews bypassed entire blockfaces or alley corridors on pickup day, but re-service generally resolved the issue without repeat tickets on subsequent weeks.
          <br><br>
          <strong>Chronic Problem Resolution Failures:</strong> In contrast, routes like <strong>Recycling Route R209_2</strong> (Ward 2) and <strong>Trash Route OR309</strong> (Ward 3) suffer from persistent recurrence. On R209_2, <strong>50.0% of all complaining properties</strong> (14 of 28 addresses) submitted tickets across 2 to 5 distinct collection cycles, averaging <strong>2.54 requests per complaining property</strong>. This demonstrates that closing 311 tickets failed to fix the underlying physical obstacles.
        </p>
      </div>

      <!-- Pattern 4 -->
      <div class="pattern-card">
        <span class="pattern-tag tag-red">Pattern 4 • Service Area Paradox</span>
        <h3 class="pattern-title">Twice-Weekly Inner City Service Shows Stubborn Recurrence</h3>
        <p class="pattern-body">
          DPW divides trash collection into two operational models: <strong>Outer Ring</strong> (once-weekly residential collection) and <strong>Inner City</strong> (twice-weekly collection in dense historic rowhouse and commercial corridors).
          <br><br>
          Despite receiving twice the collection frequency, Inner City routes average <strong>61.5 requests per route</strong> (comparable to 59.7 reqs/route in the Outer Ring). Crucially, <strong>Route IC203</strong> ranks #2 across all 103 trash routes in the city with 198 requests and a 32.0% multi-day repeat rate. Tight historic alleyways, parked vehicle obstructions, and overflow container crowding frequently prevent trucks from completing alleys, leading to chronic repeat failures despite two weekly passes.
        </p>
        <table class="pattern-table">
          <thead>
            <tr><th>Service Model</th><th>Routes</th><th>Total Requests</th><th>Unique Addrs</th><th>Repeat Rate</th></tr>
          </thead>
          <tbody>
            <tr><td>Outer Ring (1x/week)</td><td>77 routes</td><td>4,597 reqs</td><td>3,315 addrs</td><td>21.1%</td></tr>
            <tr><td>Inner City (2x/week)</td><td>26 routes</td><td>1,600 reqs</td><td>1,209 addrs</td><td>19.7%</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Section 3: Interactive Route Matrix -->
    <div class="section-title-wrap">
      <div>
        <h2 class="section-heading">Route Performance Matrix</h2>
        <div class="section-desc">Search, filter, and sort performance metrics across all 103 Trash Routes and 120 Recycling Routes.</div>
      </div>
    </div>

    <div class="table-controls">
      <div class="filter-tabs">
        <button class="filter-tab active" onclick="setTableFilter('all', this)">All Routes (223)</button>
        <button class="filter-tab" onclick="setTableFilter('Trash', this)">Trash Routes (103)</button>
        <button class="filter-tab" onclick="setTableFilter('Recycling', this)">Recycling Routes (120)</button>
      </div>
      <input type="text" class="table-search" id="routeSearch" placeholder="Search Route ID, Schedule, or Area..." oninput="handleRouteSearch(this.value)">
    </div>

    <div class="table-card">
      <div class="data-table-wrap">
        <table class="data-table" id="routesTable">
          <thead>
            <tr>
              <th onclick="sortTable(0)">Route ID &#x25B4;&#x25BE;</th>
              <th onclick="sortTable(1)">Type &#x25B4;&#x25BE;</th>
              <th onclick="sortTable(2)">Schedule &#x25B4;&#x25BE;</th>
              <th onclick="sortTable(3)">Service Area / Notes &#x25B4;&#x25BE;</th>
              <th onclick="sortTable(4, true)">Total Reqs &#x25B4;&#x25BE;</th>
              <th onclick="sortTable(5, true)">Unique Addrs &#x25B4;&#x25BE;</th>
              <th onclick="sortTable(6, true)">Repeat Addrs &#x25B4;&#x25BE;</th>
              <th onclick="sortTable(7, true)">Repeat Rate % &#x25B4;&#x25BE;</th>
              <th onclick="sortTable(8, true)">Req/Addr &#x25B4;&#x25BE;</th>
              <th onclick="sortTable(9)">Classification &#x25B4;&#x25BE;</th>
            </tr>
          </thead>
          <tbody id="tableBody">
            <!-- Dynamically populated -->
          </tbody>
        </table>
      </div>
      <div class="table-footer">
        <span id="tableRecordCount">Showing 223 routes</span>
        <span>Public Aggregated DPW Route Data • 180-Day Scope (Mar 24 – Sep 20, 2026)</span>
      </div>
    </div>

    <!-- Footer Note -->
    <div class="footer-note">
      <strong>Data Sources &amp; Methodology:</strong> 311 service request records for Missed Trash (<code>S0441</code>) and Missed Recycling (<code>S0321</code>) were retrieved from the Open Data DC GIS FeatureServer spanning March 24, 2026 through September 20, 2026. Service requests were spatially joined to DPW Collection Route polygon boundaries (140 Trash route features and 173 Recycling route features). Properties were deduplicated using unique Master Address Repository (MAR) IDs and street address strings. Repeat addresses were calculated by identifying properties with service requests submitted across two or more distinct collection calendar dates. All data is public domain.
    </div>

  </div>

  <script>
    // Embedded Route Datasets
    const ALL_ROUTES = {json.dumps(all_routes_combined)};

    // Chart 1: Top 10 Trash Routes
    const ctxTrash = document.getElementById('chartTopTrash').getContext('2d');
    new Chart(ctxTrash, {{
      type: 'bar',
      data: {{
        labels: {json.dumps([r['route_id'] for r in top10_trash])},
        datasets: [
          {{
            label: 'Single-Incident Addresses',
            data: {json.dumps([r['single_addrs'] for r in top10_trash])},
            backgroundColor: '#3b82f6',
            borderRadius: 4
          }},
          {{
            label: 'Multi-Day Repeat Addresses',
            data: {json.dumps([r['repeat_addrs'] for r in top10_trash])},
            backgroundColor: '#a855f7',
            borderRadius: 4
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        scales: {{
          x: {{
            stacked: true,
            grid: {{ display: false }},
            ticks: {{ color: '#94a3b8', font: {{ family: "'JetBrains Mono', monospace", size: 11 }} }}
          }},
          y: {{
            stacked: true,
            grid: {{ color: 'rgba(255, 255, 255, 0.08)' }},
            ticks: {{ color: '#94a3b8', font: {{ family: "'JetBrains Mono', monospace", size: 11 }} }}
          }}
        }},
        plugins: {{
          legend: {{
            position: 'top',
            labels: {{ color: '#e2e8f0', font: {{ family: "'Plus Jakarta Sans', sans-serif", size: 11 }} }}
          }},
          tooltip: {{
            callbacks: {{
              afterBody: function(items) {{
                const idx = items[0].dataIndex;
                const routes = {json.dumps(top10_trash)};
                const r = routes[idx];
                return `Total Requests: ${{r.total}}\\nSchedule: ${{r.schedule}} (${{r.service_area}})\\nRepeat Rate: ${{r.repeat_rate}}% (${{r.req_per_addr}} req/addr)`;
              }}
            }}
          }}
        }}
      }}
    }});

    // Chart 2: Top 10 Recycling Routes
    const ctxRec = document.getElementById('chartTopRec').getContext('2d');
    new Chart(ctxRec, {{
      type: 'bar',
      data: {{
        labels: {json.dumps([r['route_id'] for r in top10_rec])},
        datasets: [
          {{
            label: 'Single-Incident Addresses',
            data: {json.dumps([r['single_addrs'] for r in top10_rec])},
            backgroundColor: '#10b981',
            borderRadius: 4
          }},
          {{
            label: 'Multi-Day Repeat Addresses',
            data: {json.dumps([r['repeat_addrs'] for r in top10_rec])},
            backgroundColor: '#a855f7',
            borderRadius: 4
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        scales: {{
          x: {{
            stacked: true,
            grid: {{ display: false }},
            ticks: {{ color: '#94a3b8', font: {{ family: "'JetBrains Mono', monospace", size: 11 }} }}
          }},
          y: {{
            stacked: true,
            grid: {{ color: 'rgba(255, 255, 255, 0.08)' }},
            ticks: {{ color: '#94a3b8', font: {{ family: "'JetBrains Mono', monospace", size: 11 }} }}
          }}
        }},
        plugins: {{
          legend: {{
            position: 'top',
            labels: {{ color: '#e2e8f0', font: {{ family: "'Plus Jakarta Sans', sans-serif", size: 11 }} }}
          }},
          tooltip: {{
            callbacks: {{
              afterBody: function(items) {{
                const idx = items[0].dataIndex;
                const routes = {json.dumps(top10_rec)};
                const r = routes[idx];
                return `Total Requests: ${{r.total}}\\nSchedule: ${{r.schedule}}\\nRepeat Rate: ${{r.repeat_rate}}% (${{r.req_per_addr}} req/addr)`;
              }}
            }}
          }}
        }}
      }}
    }});

    // Chart 3: Day of Week Breakdown
    const ctxDay = document.getElementById('chartDayOfWeek').getContext('2d');
    new Chart(ctxDay, {{
      type: 'bar',
      data: {{
        labels: {json.dumps(day_order)},
        datasets: [
          {{
            label: 'Missed Trash (S0441)',
            data: {json.dumps([trash_by_day[d]['total'] for d in day_order])},
            backgroundColor: '#ef4444',
            borderRadius: 4
          }},
          {{
            label: 'Missed Recycling (S0321)',
            data: {json.dumps([rec_by_day[d]['total'] for d in day_order])},
            backgroundColor: '#10b981',
            borderRadius: 4
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        scales: {{
          x: {{
            grid: {{ display: false }},
            ticks: {{ color: '#94a3b8', font: {{ family: "'Plus Jakarta Sans', sans-serif", size: 11 }} }}
          }},
          y: {{
            grid: {{ color: 'rgba(255, 255, 255, 0.08)' }},
            ticks: {{ color: '#94a3b8', font: {{ family: "'JetBrains Mono', monospace", size: 11 }} }}
          }}
        }},
        plugins: {{
          legend: {{
            position: 'top',
            labels: {{ color: '#e2e8f0', font: {{ family: "'Plus Jakarta Sans', sans-serif", size: 11 }} }}
          }}
        }}
      }}
    }});

    // Chart 4: Chronic Repeat Routes
    const chronicCombined = {json.dumps(sorted(trash_chronic + rec_chronic, key=lambda x: x['repeat_rate'], reverse=True)[:10])};
    const ctxChronic = document.getElementById('chartChronic').getContext('2d');
    new Chart(ctxChronic, {{
      type: 'bar',
      data: {{
        labels: chronicCombined.map(r => `${{r.route_id}} (${{r.type[0]}})`),
        datasets: [
          {{
            label: 'Multi-Day Repeat Rate %',
            data: chronicCombined.map(r => r.repeat_rate),
            backgroundColor: chronicCombined.map(r => r.type === 'Trash' ? '#f87171' : '#34d399'),
            borderRadius: 4
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        scales: {{
          x: {{
            grid: {{ display: false }},
            ticks: {{ color: '#94a3b8', font: {{ family: "'JetBrains Mono', monospace", size: 11 }} }}
          }},
          y: {{
            max: 60,
            grid: {{ color: 'rgba(255, 255, 255, 0.08)' }},
            ticks: {{
              color: '#94a3b8',
              font: {{ family: "'JetBrains Mono', monospace", size: 11 }},
              callback: val => val + '%'
            }}
          }}
        }},
        plugins: {{
          legend: {{ display: false }},
          tooltip: {{
            callbacks: {{
              afterBody: function(items) {{
                const idx = items[0].dataIndex;
                const r = chronicCombined[idx];
                return `Type: ${{r.type}} Route\\nSchedule: ${{r.schedule}}\\nTotal Reqs: ${{r.total}}\\nRepeat Addrs: ${{r.repeat_addrs}} of ${{r.unique_addrs}} (${{r.repeat_rate}}%)`;
              }}
            }}
          }}
        }}
      }}
    }});

    // Table Rendering & Interaction
    let currentFilterType = 'all';
    let searchQuery = '';
    let sortColumnIdx = 4;
    let sortAsc = false;

    function renderTable() {{
      const tbody = document.getElementById('tableBody');
      let filtered = ALL_ROUTES.filter(r => {{
        if (currentFilterType !== 'all' && r.type !== currentFilterType) return false;
        if (searchQuery) {{
          const q = searchQuery.toLowerCase();
          const match = r.route_id.toLowerCase().includes(q) ||
                        r.schedule.toLowerCase().includes(q) ||
                        r.service_area.toLowerCase().includes(q) ||
                        r.classification.toLowerCase().includes(q);
          if (!match) return false;
        }}
        return true;
      }});

      // Sort
      filtered.sort((a, b) => {{
        let vA, vB;
        switch(sortColumnIdx) {{
          case 0: vA = a.route_id; vB = b.route_id; break;
          case 1: vA = a.type; vB = b.type; break;
          case 2: vA = a.schedule; vB = b.schedule; break;
          case 3: vA = a.service_area; vB = b.service_area; break;
          case 4: vA = a.total; vB = b.total; break;
          case 5: vA = a.unique_addrs; vB = b.unique_addrs; break;
          case 6: vA = a.repeat_addrs; vB = b.repeat_addrs; break;
          case 7: vA = a.repeat_rate; vB = b.repeat_rate; break;
          case 8: vA = a.req_per_addr; vB = b.req_per_addr; break;
          case 9: vA = a.classification; vB = b.classification; break;
          default: vA = a.total; vB = b.total;
        }}
        if (vA < vB) return sortAsc ? -1 : 1;
        if (vA > vB) return sortAsc ? 1 : -1;
        return 0;
      }});

      tbody.innerHTML = filtered.map(r => `
        <tr>
          <td><strong style="color: #fff; font-family: var(--font-mono);">${{r.route_id}}</strong></td>
          <td><span class="pill ${{r.type === 'Trash' ? 'pill-trash' : 'pill-rec'}}">${{r.type}}</span></td>
          <td>${{r.schedule}}</td>
          <td style="color: #94a3b8;">${{r.service_area}}</td>
          <td><strong style="color: #fff; font-family: var(--font-mono); font-size: 13px;">${{r.total}}</strong></td>
          <td style="font-family: var(--font-mono);">${{r.unique_addrs}}</td>
          <td style="font-family: var(--font-mono); color: ${{r.repeat_addrs > 0 ? '#c084fc' : '#64748b'}};">${{r.repeat_addrs}}</td>
          <td><strong style="font-family: var(--font-mono); color: ${{r.repeat_rate >= 30 ? '#fbbf24' : '#e2e8f0'}};">${{r.repeat_rate}}%</strong></td>
          <td style="font-family: var(--font-mono);">${{r.req_per_addr}}</td>
          <td><span class="status-badge status-${{r.classification.toLowerCase().replace(/\\s+/g, '-')}}">${{r.classification}}</span></td>
        </tr>
      `).join('');

      document.getElementById('tableRecordCount').innerText = `Showing ${{filtered.length}} of ${{ALL_ROUTES.length}} routes`;
    }}

    function setTableFilter(type, btn) {{
      currentFilterType = type;
      document.querySelectorAll('.filter-tab').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderTable();
    }}

    function handleRouteSearch(val) {{
      searchQuery = val.trim();
      renderTable();
    }}

    function sortTable(colIdx, isNumeric) {{
      if (sortColumnIdx === colIdx) {{
        sortAsc = !sortAsc;
      }} else {{
        sortColumnIdx = colIdx;
        sortAsc = isNumeric ? false : true;
      }}
      renderTable();
    }}

    // Initial render
    renderTable();
  </script>
</body>
</html>
'''

routes_html_path = os.path.join(BASE_DIR, 'routes.html')
with open(routes_html_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"Successfully generated {routes_html_path}")
