#!/usr/bin/env python3
"""
Compiles the Dedicated Tables and Graphs Application (tables.html).
Presents citywide and district operational charts, Ward and ANC breakdown tables,
and the complete 223-route performance matrix with sorting, filtering, and exports.

Strict standards:
- All table columns are sortable ascending/descending
- Rank columns omitted
- Chart 4 (Average Requests per Route by Day) rendered as a bar chart
- Primary monospace font (IBM Plex Mono)
- Lo-fi black & white aesthetic with light/dark theme toggle
- Strictly zero emojis across code, markup, and UI
- Zero third-party pip dependencies (standard library only)
- Offline-first vendored assets from assets/vendor/
"""

import os
import sys
import json
import re
from collections import defaultdict
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load Datasets
addr_stats_path = os.path.join(BASE_DIR, 'data', 'smd_180d_address_stats.json')
route_stats_path = os.path.join(BASE_DIR, 'data', 'route_180d_stats.json')
route_areas_path = os.path.join(BASE_DIR, 'data', 'route_areas.json')
config_path = os.path.join(BASE_DIR, 'data', 'config.json')

with open(addr_stats_path, 'r', encoding='utf-8') as f:
    addr_data = json.load(f)

with open(route_stats_path, 'r', encoding='utf-8') as f:
    route_data = json.load(f)

route_areas = {}
if os.path.exists(route_areas_path):
    with open(route_areas_path, 'r', encoding='utf-8') as f:
        route_areas = json.load(f)

# Load Ward Councilmembers
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
if os.path.exists(config_path):
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
            if 'ward_councilmembers' in cfg:
                ward_council = {int(k): v for k, v in cfg['ward_councilmembers'].items()}
    except Exception:
        pass

citywide = addr_data['citywide']
wards_stats = addr_data['wards'] # keys "1".."8"
smds_list = addr_data['smds']     # 345 SMDs

trash_routes = route_data['trash_routes']
recycle_routes = route_data['recycle_routes']
all_routes = []
for r in trash_routes:
    r_copy = dict(r)
    r_copy['stream'] = 'Trash'
    aid = r_copy['route_id']
    r_copy['area_sq_mi'] = route_areas.get('trash_routes', {}).get(aid, {}).get('area_sq_mi', 0.0)
    density = round(r_copy['total'] / r_copy['area_sq_mi'], 1) if r_copy['area_sq_mi'] > 0 else 0.0
    r_copy['density'] = density
    all_routes.append(r_copy)

for r in recycle_routes:
    r_copy = dict(r)
    r_copy['stream'] = 'Recycling'
    aid = r_copy['route_id']
    r_copy['area_sq_mi'] = route_areas.get('recycle_routes', {}).get(aid, {}).get('area_sq_mi', 0.0)
    density = round(r_copy['total'] / r_copy['area_sq_mi'], 1) if r_copy['area_sq_mi'] > 0 else 0.0
    r_copy['density'] = density
    all_routes.append(r_copy)

# Sort all routes by total requests descending initially
all_routes.sort(key=lambda x: x['total'], reverse=True)

# Aggregate ANC Stats
anc_dict = defaultdict(lambda: {
    'anc_id': '',
    'ward': 0,
    'total': 0,
    'trash': 0,
    'recycling': 0,
    'unique_addrs': 0,
    'repeat_addrs': 0,
    'smd_count': 0
})

for smd in smds_list:
    anc = smd['anc_id']
    w = smd['ward']
    anc_dict[anc]['anc_id'] = anc
    anc_dict[anc]['ward'] = w
    anc_dict[anc]['total'] += smd['total']
    anc_dict[anc]['trash'] += smd['trash']
    anc_dict[anc]['recycling'] += smd['recycling']
    anc_dict[anc]['unique_addrs'] += smd['unique_addrs']
    anc_dict[anc]['repeat_addrs'] += smd['repeat_addrs']
    anc_dict[anc]['smd_count'] += 1

def anc_sort_key(anc):
    anc = anc.strip().replace('ANC', '').strip()
    if not anc:
        return (99, '', '')
    if anc.startswith('3/4G'):
        return (3, '4G', '')
    m = re.match(r'^(\d+)([A-Z]+)?(.*)$', anc)
    if m:
        return (int(m.group(1)), m.group(2) or '', m.group(3) or '')
    return (99, anc, '')

ancs_list = []
for anc, d in anc_dict.items():
    d['repeat_rate'] = round(d['repeat_addrs'] / d['unique_addrs'] * 100, 1) if d['unique_addrs'] > 0 else 0.0
    ancs_list.append(d)

ancs_list.sort(key=lambda x: anc_sort_key(x['anc_id']))

# Chart 1 Data: Ward Breakdown (Trash vs Recycling)
chart_ward_labels = [f"Ward {w}" for w in range(1, 9)]
chart_ward_trash = [wards_stats[str(w)]['trash'] for w in range(1, 9)]
chart_ward_rec = [wards_stats[str(w)]['recycling'] for w in range(1, 9)]

# Chart 2 Data: Ward Address Recurrence
chart_ward_single = [wards_stats[str(w)]['unique_addresses'] - wards_stats[str(w)]['repeat_addresses'] for w in range(1, 9)]
chart_ward_repeat = [wards_stats[str(w)]['repeat_addresses'] for w in range(1, 9)]
chart_ward_repeat_pct = [wards_stats[str(w)]['repeat_rate'] for w in range(1, 9)]

# Chart 3 Data: Day of Week Collection Volumes
days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
trash_by_day = defaultdict(int)
for r in trash_routes:
    trash_by_day[r['schedule']] += r['total']

rec_by_day = defaultdict(int)
for r in recycle_routes:
    rec_by_day[r['schedule']] += r['total']

chart_day_trash = [trash_by_day[d] for d in days_order]
chart_day_rec = [rec_by_day[d] for d in days_order]

# Chart 4 Data: Daily Average Requests per Route
trash_counts_by_day = defaultdict(int)
for r in trash_routes:
    trash_counts_by_day[r['schedule']] += 1

rec_counts_by_day = defaultdict(int)
for r in recycle_routes:
    rec_counts_by_day[r['schedule']] += 1

chart_day_avg_trash = [round(trash_by_day[d] / trash_counts_by_day[d], 1) if trash_counts_by_day[d] else 0 for d in days_order]
chart_day_avg_rec = [round(rec_by_day[d] / rec_counts_by_day[d], 1) if rec_counts_by_day[d] else 0 for d in days_order]

day_sort_map = {'Monday': 1, 'Tuesday': 2, 'Wednesday': 3, 'Thursday': 4, 'Friday': 5}

# HTML Template
html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Missed Collections • Tables and Graphs</title>

  <!-- Google Fonts: IBM Plex Mono -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">

  <!-- Local Vendored Assets -->
  <script src="assets/vendor/chartjs/chart.umd.min.js"></script>
  <script src="assets/vendor/jspdf/jspdf.umd.min.js"></script>
  <script src="assets/vendor/jspdf-autotable/jspdf.plugin.autotable.min.js"></script>
  <script src="assets/vendor/html2canvas/html2canvas.min.js"></script>

  <style>
    :root {{
      --font-mono: 'IBM Plex Mono', monospace;

      /* Light Theme (Default) */
      --bg-page: #f8fafc;
      --bg-surface: #ffffff;
      --bg-card: #ffffff;
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
      --warning-color: #d97706;
      --ward-boundary: #7c3aed;
      --card-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
      --badge-bg: rgba(37, 99, 235, 0.08);
      --badge-border: rgba(37, 99, 235, 0.25);
    }}

    [data-theme="dark"] {{
      /* Dark Theme */
      --bg-page: #09090b;
      --bg-surface: #121215;
      --bg-card: #121215;
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
      --warning-color: #f59e0b;
      --ward-boundary: #c084fc;
      --card-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
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

    body {{
      background-color: var(--bg-page);
      color: var(--text-main);
      font-family: var(--font-mono);
      line-height: 1.5;
      padding-bottom: 80px;
      -webkit-font-smoothing: antialiased;
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
      gap: 10px;
      align-items: center;
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
      background: var(--bg-surface);
    }}

    .nav-link.active {{
      color: var(--text-main);
      border-color: var(--border-dark);
      background: var(--bg-surface);
    }}

    .btn-action {{
      background: var(--bg-surface);
      border: 1px solid var(--border);
      color: var(--text-main);
      padding: 5px 10px;
      font-size: 11px;
      font-weight: 600;
      border-radius: 2px;
      cursor: pointer;
      font-family: var(--font-mono);
      transition: all 0.15s ease;
    }}

    .btn-action:hover {{
      border-color: var(--border-dark);
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }}

    .btn-action:disabled {{
      opacity: 0.4;
      cursor: not-allowed;
    }}

    /* Layout Containers */
    .page-container {{
      max-width: 1400px;
      margin: 0 auto;
      padding: 24px 20px;
    }}

    .report-header {{
      margin-bottom: 24px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--border);
    }}

    .report-title {{
      font-size: 20px;
      font-weight: 800;
      color: var(--text-main);
      letter-spacing: -0.02em;
    }}

    .report-lead {{
      font-size: 12px;
      color: var(--text-muted);
      margin-top: 6px;
    }}

    /* Section Styling */
    .report-section {{
      margin-bottom: 36px;
    }}

    .section-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
      padding-bottom: 8px;
      border-bottom: 1px solid var(--border);
    }}

    .section-title {{
      font-size: 16px;
      font-weight: 800;
      color: var(--text-main);
      letter-spacing: -0.01em;
    }}

    /* Chart Cards */
    .chart-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(560px, 1fr));
      gap: 16px;
      margin-bottom: 20px;
    }}

    @media (max-width: 900px) {{
      .chart-grid {{
        grid-template-columns: 1fr;
      }}
    }}

    .chart-card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 2px;
      padding: 16px;
      position: relative;
      box-shadow: var(--card-shadow);
    }}

    .chart-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }}

    .chart-title {{
      font-size: 12px;
      font-weight: 700;
      color: var(--text-main);
    }}

    .chart-actions {{
      display: flex;
      gap: 6px;
    }}

    .chart-container {{
      height: 280px;
      position: relative;
      width: 100%;
    }}

    /* Table Containers */
    .table-container {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 2px;
      overflow-x: auto;
      box-shadow: var(--card-shadow);
      margin-bottom: 20px;
    }}

    .table-toolbar {{
      padding: 10px 14px;
      border-bottom: 1px solid var(--border);
      background: var(--bg-panel);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 10px;
    }}

    .toolbar-filters {{
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
    }}

    .input-search {{
      background: var(--bg-input);
      border: 1px solid var(--border);
      color: var(--text-main);
      padding: 5px 10px;
      border-radius: 2px;
      font-size: 11px;
      font-family: var(--font-mono);
      min-width: 200px;
    }}

    .input-search:focus {{
      outline: none;
      border-color: var(--border-focus);
    }}

    .select-filter {{
      background: var(--bg-input);
      border: 1px solid var(--border);
      color: var(--text-main);
      padding: 5px 8px;
      border-radius: 2px;
      font-size: 11px;
      font-family: var(--font-mono);
    }}

    .select-filter:focus {{
      outline: none;
      border-color: var(--border-focus);
    }}

    .data-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 11px;
      text-align: left;
    }}

    .data-table th {{
      background: var(--bg-input);
      color: var(--text-dim);
      font-weight: 700;
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      padding: 9px 12px;
      border-bottom: 1px solid var(--border);
      cursor: pointer;
      user-select: none;
      white-space: nowrap;
      transition: color 0.15s ease, background 0.15s ease;
    }}

    .data-table th:hover {{
      color: var(--text-main);
      background: var(--border);
    }}

    .sort-indicator {{
      display: inline-block;
      margin-left: 4px;
      font-size: 10px;
      color: var(--text-main);
    }}

    .data-table td {{
      padding: 8px 12px;
      border-bottom: 1px solid var(--border);
      color: var(--text-main);
    }}

    .data-table tr:hover td {{
      background: var(--bg-input);
    }}

    .badge-trash {{
      background: rgba(220, 38, 38, 0.1);
      color: var(--trash-color);
      border: 1px solid rgba(220, 38, 38, 0.3);
      padding: 1px 6px;
      border-radius: 2px;
      font-size: 10px;
      font-weight: 700;
      display: inline-block;
    }}

    .badge-recycle {{
      background: rgba(22, 163, 74, 0.1);
      color: var(--recycle-color);
      border: 1px solid rgba(22, 163, 74, 0.3);
      padding: 1px 6px;
      border-radius: 2px;
      font-size: 10px;
      font-weight: 700;
      display: inline-block;
    }}

    .val-highlight {{
      color: var(--combined-color);
      font-weight: 700;
    }}

    .font-num {{
      font-variant-numeric: tabular-nums;
    }}

    /* Footer */
    .site-footer {{
      margin-top: 48px;
      padding-top: 16px;
      border-top: 1px solid var(--border);
      font-size: 11px;
      color: var(--text-dim);
      text-align: center;
    }}

    @media print {{
      @page {{
        size: letter landscape;
        margin: 0.5in;
      }}
      body {{
        background: #ffffff !important;
        color: #000000 !important;
      }}
      .site-nav, .table-toolbar, .chart-actions, .site-footer {{
        display: none !important;
      }}
      .chart-grid {{
        grid-template-columns: 1fr 1fr !important;
      }}
      .chart-card {{
        border: 1px solid #000000 !important;
        box-shadow: none !important;
      }}
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
      <a href="map.html" class="nav-link">The Map</a>
      <a href="report.html" class="nav-link">The Report</a>
      <a href="tables.html" class="nav-link active">Tables and Graphs</a>
      <button onclick="toggleTheme()" class="btn-action" id="theme-toggle-btn">Theme: Light</button>
      <button onclick="window.print()" class="btn-action">Export (PDF)</button>
    </div>
  </nav>

  <div class="page-container">

    <!-- Page Header -->
    <header class="report-header">
      <h1 class="report-title">Tables and Graphs</h1>
      <p class="report-lead">Citywide operational charts, Ward and ANC summaries, and the complete 223-route performance matrix across the 180-day evaluation window. Click any column header to sort ascending or descending.</p>
    </header>

    <!-- SECTION 1: WARD BREAKDOWN -->
    <section class="report-section">
      <div class="section-header">
        <div>
          <h2 class="section-title">Performance by Ward</h2>
        </div>
        <button onclick="exportTableCsv('ward-table', 'dc-ward-summary')" class="btn-action">Export CSV</button>
      </div>

      <div class="chart-grid">
        <div class="chart-card">
          <div class="chart-header">
            <span class="chart-title">Ward Volume by Stream (<span class="kw-trash">Trash</span> vs <span class="kw-recycle">Recycling</span>)</span>
            <div class="chart-actions">
              <button onclick="exportChartPng('chartWardReq', 'dc-ward-volume')" class="btn-action">PNG</button>
              <button onclick="exportChartPdf('chartWardReq', 'Ward Missed Collections by Stream', 'dc-ward-volume')" class="btn-action">PDF</button>
            </div>
          </div>
          <div class="chart-container">
            <canvas id="chartWardReq"></canvas>
          </div>
        </div>

        <div class="chart-card">
          <div class="chart-header">
            <span class="chart-title">Single vs. Repeat Addresses by Ward</span>
            <div class="chart-actions">
              <button onclick="exportChartPng('chartWardRep', 'dc-ward-repeat-addrs')" class="btn-action">PNG</button>
              <button onclick="exportChartPdf('chartWardRep', 'Ward Single vs Repeat Address Volume', 'dc-ward-repeat-addrs')" class="btn-action">PDF</button>
            </div>
          </div>
          <div class="chart-container">
            <canvas id="chartWardRep"></canvas>
          </div>
        </div>
      </div>

      <div class="table-container">
        <table class="data-table" id="ward-table">
          <thead>
            <tr>
              <th data-col="0">Ward</th>
              <th data-col="1">Councilmember</th>
              <th data-col="2" style="text-align: right;">Total Requests</th>
              <th data-col="3" style="text-align: right;" class="kw-trash">Trash (S0441)</th>
              <th data-col="4" style="text-align: right;" class="kw-recycle">Recycling (S0321)</th>
              <th data-col="5" style="text-align: right;">Unique Addrs</th>
              <th data-col="6" style="text-align: right;">Repeat Addrs</th>
              <th data-col="7" style="text-align: right;">Repeat Rate</th>
              <th data-col="8" style="text-align: right;">Ward Share</th>
            </tr>
          </thead>
          <tbody>
"""

total_citywide_requests = citywide['total_requests']

for w in range(1, 9):
    ws = wards_stats[str(w)]
    share_pct = round(ws['total'] / total_citywide_requests * 100, 1) if total_citywide_requests > 0 else 0.0
    rep_display = f'<span class="val-highlight">{ws["repeat_rate"]}%</span>' if ws['repeat_rate'] >= 26.0 else f"{ws['repeat_rate']}%"
    html_content += f"""
            <tr>
              <td data-sort="{w}"><strong>Ward {w}</strong></td>
              <td data-sort="{ward_council.get(w, '')}">{ward_council.get(w, '')}</td>
              <td data-sort="{ws['total']}" style="text-align: right;" class="kw-combined font-num"><strong>{ws['total']:,}</strong></td>
              <td data-sort="{ws['trash']}" style="text-align: right;" class="kw-trash font-num">{ws['trash']:,}</td>
              <td data-sort="{ws['recycling']}" style="text-align: right;" class="kw-recycle font-num">{ws['recycling']:,}</td>
              <td data-sort="{ws['unique_addresses']}" style="text-align: right;" class="font-num">{ws['unique_addresses']:,}</td>
              <td data-sort="{ws['repeat_addresses']}" style="text-align: right;" class="font-num">{ws['repeat_addresses']:,}</td>
              <td data-sort="{ws['repeat_rate']}" style="text-align: right;" class="font-num">{rep_display}</td>
              <td data-sort="{share_pct}" style="text-align: right;" class="font-num">{share_pct}%</td>
            </tr>
"""

html_content += f"""
          </tbody>
        </table>
      </div>
    </section>

    <!-- SECTION 2: ANC PERFORMANCE TABLE -->
    <section class="report-section">
      <div class="section-header">
        <div>
          <h2 class="section-title">Performance by ANC</h2>
        </div>
        <button onclick="exportTableCsv('anc-table', 'dc-anc-summary')" class="btn-action">Export CSV</button>
      </div>

      <div class="table-container">
        <div class="table-toolbar">
          <div class="toolbar-filters">
            <input type="text" id="anc-search" class="input-search" placeholder="Search ANC (e.g. 5E, 7B)..." oninput="filterAncTable()">
            <select id="anc-ward-filter" class="select-filter" onchange="filterAncTable()">
              <option value="">All Wards</option>
              <option value="1">Ward 1</option>
              <option value="2">Ward 2</option>
              <option value="3">Ward 3</option>
              <option value="4">Ward 4</option>
              <option value="5">Ward 5</option>
              <option value="6">Ward 6</option>
              <option value="7">Ward 7</option>
              <option value="8">Ward 8</option>
            </select>
          </div>
          <div class="font-num" style="font-size: 11px; color: var(--text-dim);" id="anc-count-info">
            Showing {len(ancs_list)} ANCs
          </div>
        </div>

        <table class="data-table" id="anc-table">
          <thead>
            <tr>
              <th data-col="0">Ward</th>
              <th data-col="1">ANC</th>
              <th data-col="2" style="text-align: right;">Total Requests</th>
              <th data-col="3" style="text-align: right;" class="kw-trash">Trash</th>
              <th data-col="4" style="text-align: right;" class="kw-recycle">Recycling</th>
              <th data-col="5" style="text-align: right;">Unique Addrs</th>
              <th data-col="6" style="text-align: right;">Repeat Addrs</th>
              <th data-col="7" style="text-align: right;">Repeat Rate</th>
            </tr>
          </thead>
          <tbody id="anc-table-body">
"""

for anc in ancs_list:
    anc_rep_display = f'<span class="val-highlight">{anc["repeat_rate"]}%</span>' if anc['repeat_rate'] >= 30.0 else f"{anc['repeat_rate']}%"
    html_content += f"""
            <tr data-anc="{anc['anc_id']}" data-ward="{anc['ward']}">
              <td data-sort="{anc['ward']}">Ward {anc['ward']}</td>
              <td data-sort="{anc['anc_id']}" data-type="anc"><strong>ANC {anc['anc_id']}</strong></td>
              <td data-sort="{anc['total']}" style="text-align: right;" class="kw-combined font-num"><strong>{anc['total']:,}</strong></td>
              <td data-sort="{anc['trash']}" style="text-align: right;" class="kw-trash font-num">{anc['trash']:,}</td>
              <td data-sort="{anc['recycling']}" style="text-align: right;" class="kw-recycle font-num">{anc['recycling']:,}</td>
              <td data-sort="{anc['unique_addrs']}" style="text-align: right;" class="font-num">{anc['unique_addrs']:,}</td>
              <td data-sort="{anc['repeat_addrs']}" style="text-align: right;" class="font-num">{anc['repeat_addrs']:,}</td>
              <td data-sort="{anc['repeat_rate']}" style="text-align: right;" class="font-num">{anc_rep_display}</td>
            </tr>
"""

html_content += f"""
          </tbody>
        </table>
      </div>
    </section>

    <!-- SECTION 3: ROUTE ANALYSIS & MATRIX -->
    <section class="report-section">
      <div class="section-header">
        <div>
          <h2 class="section-title">Performance by Schedule and Route</h2>
        </div>
        <button onclick="exportTableCsv('route-table', 'dc-route-performance')" class="btn-action">Export CSV</button>
      </div>

      <div class="chart-grid">
        <div class="chart-card">
          <div class="chart-header">
            <span class="chart-title">Requests by Scheduled Collection Day (<span class="kw-trash">Trash</span> vs <span class="kw-recycle">Recycling</span>)</span>
            <div class="chart-actions">
              <button onclick="exportChartPng('chartDayVol', 'dc-routes-by-day')" class="btn-action">PNG</button>
              <button onclick="exportChartPdf('chartDayVol', 'Requests by Scheduled Collection Day', 'dc-routes-by-day')" class="btn-action">PDF</button>
            </div>
          </div>
          <div class="chart-container">
            <canvas id="chartDayVol"></canvas>
          </div>
        </div>

        <div class="chart-card">
          <div class="chart-header">
            <span class="chart-title">Average Requests per Route by Day</span>
            <div class="chart-actions">
              <button onclick="exportChartPng('chartDayAvg', 'dc-routes-avg-density')" class="btn-action">PNG</button>
              <button onclick="exportChartPdf('chartDayAvg', 'Average Requests per Route by Day', 'dc-routes-avg-density')" class="btn-action">PDF</button>
            </div>
          </div>
          <div class="chart-container">
            <canvas id="chartDayAvg"></canvas>
          </div>
        </div>
      </div>

      <div class="table-container">
        <div class="table-toolbar">
          <div class="toolbar-filters">
            <input type="text" id="route-search" class="input-search" placeholder="Search route, area, or ANC..." oninput="filterRouteTable()">
            <select id="route-type-filter" class="select-filter" onchange="filterRouteTable()">
              <option value="">All Streams</option>
              <option value="Trash">Trash (103)</option>
              <option value="Recycling">Recycling (120)</option>
            </select>
            <select id="route-day-filter" class="select-filter" onchange="filterRouteTable()">
              <option value="">All Schedule Days</option>
              <option value="Monday">Monday</option>
              <option value="Tuesday">Tuesday</option>
              <option value="Wednesday">Wednesday</option>
              <option value="Thursday">Thursday</option>
              <option value="Friday">Friday</option>
            </select>
            <select id="route-ward-filter" class="select-filter" onchange="filterRouteTable()">
              <option value="">All Wards</option>
              <option value="Ward 1">Ward 1</option>
              <option value="Ward 2">Ward 2</option>
              <option value="Ward 3">Ward 3</option>
              <option value="Ward 4">Ward 4</option>
              <option value="Ward 5">Ward 5</option>
              <option value="Ward 6">Ward 6</option>
              <option value="Ward 7">Ward 7</option>
              <option value="Ward 8">Ward 8</option>
            </select>
          </div>
          <div style="display: flex; gap: 8px; align-items: center;">
            <button id="btn-prev-route" onclick="prevRoutePage()" class="btn-action">&laquo; Prev</button>
            <button id="btn-next-route" onclick="nextRoutePage()" class="btn-action">Next &raquo;</button>
          </div>
          <div class="font-num" style="font-size: 11px; color: var(--text-dim);" id="route-page-info">
            Showing 1 to 25 of {len(all_routes)} routes
          </div>
        </div>

        <table class="data-table" id="route-table">
          <thead>
            <tr>
              <th data-col="0">Route ID</th>
              <th data-col="1">Stream</th>
              <th data-col="2">Day</th>
              <th data-col="3">Primary Ward</th>
              <th data-col="4">Covered Area / ANCs</th>
              <th data-col="5" style="text-align: right;">Area (sq mi)</th>
              <th data-col="6" style="text-align: right;">Total Requests</th>
              <th data-col="7" style="text-align: right;">Density (req/sq mi)</th>
            </tr>
          </thead>
          <tbody id="route-table-body">
"""

for r in all_routes:
    stream = r['stream']
    badge_cls = 'badge-trash' if stream == 'Trash' else 'badge-recycle'
    search_text = f"{r['route_id']} {stream} {r['schedule']} {r.get('ward', '')} {r.get('area_desc', '')}".lower()
    day_num = day_sort_map.get(r['schedule'], 99)
    ward_str = r.get('ward', 'N/A')
    m_ward = re.search(r'\d+', ward_str)
    ward_num = int(m_ward.group(0)) if m_ward else 99
    density_display = f'<span class="val-highlight">{r["density"]}</span>' if r['density'] >= 350.0 else f"{r['density']}"
    html_content += f"""
            <tr data-stream="{stream}" data-day="{r['schedule']}" data-ward="{ward_str}" data-search="{search_text}">
              <td data-sort="{r['route_id']}"><strong>{r['route_id']}</strong></td>
              <td data-sort="{stream}"><span class="{badge_cls}">{stream}</span></td>
              <td data-sort="{day_num}">{r['schedule']}</td>
              <td data-sort="{ward_num}">{ward_str}</td>
              <td data-sort="{r.get('area_desc', '')}" style="max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{r.get('area_desc', '')}">
                {r.get('area_desc', 'Citywide DPW service route')}
              </td>
              <td data-sort="{r['area_sq_mi']}" style="text-align: right;" class="font-num">{r['area_sq_mi']}</td>
              <td data-sort="{r['total']}" style="text-align: right;" class="{ 'kw-trash' if stream == 'Trash' else 'kw-recycle' } font-num"><strong>{r['total']:,}</strong></td>
              <td data-sort="{r['density']}" style="text-align: right;" class="font-num">{density_display}</td>
            </tr>
"""

html_content += f"""
          </tbody>
        </table>
      </div>
    </section>

    <!-- Footer -->
    <footer class="site-footer">
      <p>Last Updated {datetime.now().strftime('%B %d, %Y')}</p>
    </footer>

  </div>

  <script>
    // Theme Management
    let currentTheme = 'light';
    const savedTheme = localStorage.getItem('dc_map_theme');
    if (savedTheme) {{
      currentTheme = savedTheme;
    }} else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {{
      currentTheme = 'dark';
    }}
    document.documentElement.setAttribute('data-theme', currentTheme);
    const themeBtn = document.getElementById('theme-toggle-btn');
    if (themeBtn) themeBtn.innerText = currentTheme === 'dark' ? 'Theme: Dark' : 'Theme: Light';

    function toggleTheme() {{
      const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
      setTheme(nextTheme);
    }}

    function setTheme(theme) {{
      currentTheme = theme;
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('dc_map_theme', theme);
      const btn = document.getElementById('theme-toggle-btn');
      if (btn) btn.innerText = theme === 'dark' ? 'Theme: Dark' : 'Theme: Light';
      updateChartsTheme(theme);
    }}

    // ----------------------------------------------------
    // Chart 1: Ward Volume by Stream (Stacked Bar)
    // ----------------------------------------------------
    const ctxWardReq = document.getElementById('chartWardReq').getContext('2d');
    const chartWardReq = new Chart(ctxWardReq, {{
      type: 'bar',
      data: {{
        labels: {json.dumps(chart_ward_labels)},
        datasets: [
          {{
            label: 'Trash (S0441)',
            data: {json.dumps(chart_ward_trash)},
            backgroundColor: '#dc2626',
            borderRadius: 2
          }},
          {{
            label: 'Recycling (S0321)',
            data: {json.dumps(chart_ward_rec)},
            backgroundColor: '#16a34a',
            borderRadius: 2
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{
            position: 'top',
            labels: {{ font: {{ family: 'IBM Plex Mono', size: 11 }} }}
          }}
        }},
        scales: {{
          x: {{
            stacked: true,
            grid: {{ color: 'rgba(0, 0, 0, 0.06)' }},
            ticks: {{ font: {{ family: 'IBM Plex Mono', size: 10 }} }}
          }},
          y: {{
            stacked: true,
            grid: {{ color: 'rgba(0, 0, 0, 0.06)' }},
            ticks: {{ font: {{ family: 'IBM Plex Mono', size: 10 }} }}
          }}
        }}
      }}
    }});

    // ----------------------------------------------------
    // Chart 2: Single vs Repeat Addresses by Ward (Grouped Bar)
    // ----------------------------------------------------
    const ctxWardRep = document.getElementById('chartWardRep').getContext('2d');
    const chartWardRep = new Chart(ctxWardRep, {{
      type: 'bar',
      data: {{
        labels: {json.dumps(chart_ward_labels)},
        datasets: [
          {{
            label: 'Single-Incident Addrs',
            data: {json.dumps(chart_ward_single)},
            backgroundColor: '#2563eb',
            borderRadius: 2
          }},
          {{
            label: 'Repeat Addrs (>= 2 Days)',
            data: {json.dumps(chart_ward_repeat)},
            backgroundColor: '#d97706',
            borderRadius: 2
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{
            position: 'top',
            labels: {{ font: {{ family: 'IBM Plex Mono', size: 11 }} }}
          }}
        }},
        scales: {{
          x: {{
            grid: {{ color: 'rgba(0, 0, 0, 0.06)' }},
            ticks: {{ font: {{ family: 'IBM Plex Mono', size: 10 }} }}
          }},
          y: {{
            grid: {{ color: 'rgba(0, 0, 0, 0.06)' }},
            ticks: {{ font: {{ family: 'IBM Plex Mono', size: 10 }} }}
          }}
        }}
      }}
    }});

    // ----------------------------------------------------
    // Chart 3: Day of Week Collection Volumes (Grouped Bar)
    // ----------------------------------------------------
    const ctxDayVol = document.getElementById('chartDayVol').getContext('2d');
    const chartDayVol = new Chart(ctxDayVol, {{
      type: 'bar',
      data: {{
        labels: {json.dumps(days_order)},
        datasets: [
          {{
            label: 'Trash Requests',
            data: {json.dumps(chart_day_trash)},
            backgroundColor: '#dc2626',
            borderRadius: 2
          }},
          {{
            label: 'Recycling Requests',
            data: {json.dumps(chart_day_rec)},
            backgroundColor: '#16a34a',
            borderRadius: 2
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{
            position: 'top',
            labels: {{ font: {{ family: 'IBM Plex Mono', size: 11 }} }}
          }}
        }},
        scales: {{
          x: {{
            grid: {{ color: 'rgba(0, 0, 0, 0.06)' }},
            ticks: {{ font: {{ family: 'IBM Plex Mono', size: 10 }} }}
          }},
          y: {{
            grid: {{ color: 'rgba(0, 0, 0, 0.06)' }},
            ticks: {{ font: {{ family: 'IBM Plex Mono', size: 10 }} }}
          }}
        }}
      }}
    }});

    // ----------------------------------------------------
    // Chart 4: Daily Route Average Density (Bar Chart)
    // ----------------------------------------------------
    const ctxDayAvg = document.getElementById('chartDayAvg').getContext('2d');
    const chartDayAvg = new Chart(ctxDayAvg, {{
      type: 'bar',
      data: {{
        labels: {json.dumps(days_order)},
        datasets: [
          {{
            label: 'Trash Avg Req/Route',
            data: {json.dumps(chart_day_avg_trash)},
            backgroundColor: '#dc2626',
            borderRadius: 2
          }},
          {{
            label: 'Recycling Avg Req/Route',
            data: {json.dumps(chart_day_avg_rec)},
            backgroundColor: '#16a34a',
            borderRadius: 2
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{
            position: 'top',
            labels: {{ font: {{ family: 'IBM Plex Mono', size: 11 }} }}
          }}
        }},
        scales: {{
          x: {{
            grid: {{ color: 'rgba(0, 0, 0, 0.06)' }},
            ticks: {{ font: {{ family: 'IBM Plex Mono', size: 10 }} }}
          }},
          y: {{
            grid: {{ color: 'rgba(0, 0, 0, 0.06)' }},
            ticks: {{ font: {{ family: 'IBM Plex Mono', size: 10 }} }}
          }}
        }}
      }}
    }});

    function updateChartsTheme(theme) {{
      const isDark = theme === 'dark';
      const textColor = isDark ? '#f4f4f5' : '#09090b';
      const gridColor = isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.06)';
      const tickColor = isDark ? '#a1a1aa' : '#52525b';

      [chartWardReq, chartWardRep, chartDayVol, chartDayAvg].forEach(chart => {{
        if (!chart) return;
        if (chart.options.plugins?.legend?.labels) {{
          chart.options.plugins.legend.labels.color = textColor;
          chart.options.plugins.legend.labels.font = {{ family: 'IBM Plex Mono', size: 11 }};
        }}
        if (chart.options.scales?.x) {{
          chart.options.scales.x.ticks.color = tickColor;
          chart.options.scales.x.ticks.font = {{ family: 'IBM Plex Mono', size: 10 }};
          chart.options.scales.x.grid.color = gridColor;
        }}
        if (chart.options.scales?.y) {{
          chart.options.scales.y.ticks.color = tickColor;
          chart.options.scales.y.ticks.font = {{ family: 'IBM Plex Mono', size: 10 }};
          chart.options.scales.y.grid.color = gridColor;
        }}
        chart.update();
      }});
    }}

    // Apply initial chart theme
    updateChartsTheme(currentTheme);

    // ----------------------------------------------------
    // Static Export Handlers
    // ----------------------------------------------------
    function exportChartPng(canvasId, filename) {{
      const canvas = document.getElementById(canvasId);
      const url = canvas.toDataURL('image/png', 2.0);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${{filename}}.png`;
      a.click();
    }}

    function exportChartPdf(canvasId, title, filename) {{
      const {{ jsPDF }} = window.jspdf;
      const doc = new jsPDF({{ orientation: 'landscape', format: 'letter', unit: 'in' }});
      const canvas = document.getElementById(canvasId);
      
      const tmpCanvas = document.createElement('canvas');
      tmpCanvas.width = canvas.width;
      tmpCanvas.height = canvas.height;
      const tmpCtx = tmpCanvas.getContext('2d');
      const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      tmpCtx.fillStyle = isDark ? '#121215' : '#ffffff';
      tmpCtx.fillRect(0, 0, tmpCanvas.width, tmpCanvas.height);
      tmpCtx.drawImage(canvas, 0, 0);
      const imgData = tmpCanvas.toDataURL('image/png', 2.0);

      // Title Banner
      doc.setFont('Courier', 'bold');
      doc.setFontSize(15);
      doc.setTextColor(15, 23, 42);
      doc.text(title, 0.75, 0.75);

      doc.setFont('Courier', 'normal');
      doc.setFontSize(10);
      doc.setTextColor(100, 116, 139);
      doc.text('District of Columbia DPW Missed Collection Analysis', 0.75, 1.0);
      doc.text(`Generated: ${{new Date().toLocaleDateString()}}`, 0.75, 1.2);

      // Insert Chart Image
      doc.addImage(imgData, 'PNG', 0.75, 1.4, 9.5, 5.5);
      doc.save(`${{filename}}.pdf`);
    }}

    function exportTableCsv(tableId, filename) {{
      const table = document.getElementById(tableId);
      let rows;
      if (tableId === 'route-table') {{
        rows = [table.querySelector('thead tr'), ...getFilteredRouteRows()];
      }} else {{
        rows = Array.from(table.querySelectorAll('tr')).filter(r => r.style.display !== 'none');
      }}
      const csv = rows.map(r => {{
        const cells = Array.from(r.querySelectorAll('th, td'));
        return cells.map(c => `"${{c.innerText.replace(/"/g, '""').trim()}}"`).join(',');
      }}).join('\\n');

      const blob = new Blob([csv], {{ type: 'text/csv;charset=utf-8;' }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${{filename}}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    }}

    // ----------------------------------------------------
    // ANC Sorting & Filtering
    // ----------------------------------------------------
    function compareAnc(a, b) {{
      const cleanA = (a || '').replace(/^ANC\\s*/i, '').trim();
      const cleanB = (b || '').replace(/^ANC\\s*/i, '').trim();
      if (cleanA === cleanB) return 0;
      if (cleanA === '3/4G') {{
        if (cleanB.startsWith('3') && cleanB !== '3/4G') return 1;
        if (cleanB.startsWith('4')) return -1;
      }}
      if (cleanB === '3/4G') {{
        if (cleanA.startsWith('3') && cleanA !== '3/4G') return -1;
        if (cleanA.startsWith('4')) return 1;
      }}
      const matchA = cleanA.match(/^(\\d+)([A-Z]+)?/);
      const matchB = cleanB.match(/^(\\d+)([A-Z]+)?/);
      if (matchA && matchB) {{
        const numA = parseInt(matchA[1], 10);
        const numB = parseInt(matchB[1], 10);
        if (numA !== numB) return numA - numB;
        const letA = matchA[2] || '';
        const letB = matchB[2] || '';
        return letA.localeCompare(letB);
      }}
      return cleanA.localeCompare(cleanB, undefined, {{ numeric: true }});
    }}

    function filterAncTable() {{
      const q = document.getElementById('anc-search').value.toLowerCase().trim();
      const w = document.getElementById('anc-ward-filter').value;
      const rows = document.querySelectorAll('#anc-table-body tr');
      let visibleCount = 0;

      rows.forEach(r => {{
        const anc = r.getAttribute('data-anc').toLowerCase();
        const ward = r.getAttribute('data-ward');
        const matchQ = !q || anc.includes(q);
        const matchW = !w || ward === w;
        const isVisible = matchQ && matchW;
        r.style.display = isVisible ? '' : 'none';
        if (isVisible) visibleCount++;
      }});

      const info = document.getElementById('anc-count-info');
      if (info) {{
        info.innerText = `Showing ${{visibleCount}} of ${{rows.length}} ANCs`;
      }}
    }}

    // ----------------------------------------------------
    // Route Table Filtering & Pagination
    // ----------------------------------------------------
    let currentRoutePage = 1;
    const routesPerPage = 25;

    function getFilteredRouteRows() {{
      const q = document.getElementById('route-search').value.toLowerCase().trim();
      const stream = document.getElementById('route-type-filter').value;
      const day = document.getElementById('route-day-filter').value;
      const ward = document.getElementById('route-ward-filter').value;
      const allRows = Array.from(document.querySelectorAll('#route-table-body tr'));

      return allRows.filter(r => {{
        const rowStream = r.getAttribute('data-stream');
        const rowDay = r.getAttribute('data-day');
        const rowWard = r.getAttribute('data-ward');
        const rowSearch = r.getAttribute('data-search');

        const matchQ = !q || rowSearch.includes(q);
        const matchStream = !stream || rowStream === stream;
        const matchDay = !day || rowDay === day;
        const matchWard = !ward || rowWard.includes(ward);

        return matchQ && matchStream && matchDay && matchWard;
      }});
    }}

    function updateRoutePagination() {{
      const filtered = getFilteredRouteRows();
      const total = filtered.length;
      const totalPages = Math.ceil(total / routesPerPage) || 1;
      if (currentRoutePage > totalPages) currentRoutePage = totalPages;
      if (currentRoutePage < 1) currentRoutePage = 1;

      const allRows = document.querySelectorAll('#route-table-body tr');
      allRows.forEach(r => r.style.display = 'none');

      const startIdx = (currentRoutePage - 1) * routesPerPage;
      const endIdx = startIdx + routesPerPage;

      filtered.slice(startIdx, endIdx).forEach(r => r.style.display = '');

      document.getElementById('route-page-info').innerText = total === 0 
        ? 'No matching routes' 
        : `Showing ${{startIdx + 1}} to ${{Math.min(endIdx, total)}} of ${{total}} routes`;

      document.getElementById('btn-prev-route').disabled = currentRoutePage === 1;
      document.getElementById('btn-next-route').disabled = currentRoutePage >= totalPages;
    }}

    function filterRouteTable() {{
      currentRoutePage = 1;
      updateRoutePagination();
    }}

    function prevRoutePage() {{
      if (currentRoutePage > 1) {{
        currentRoutePage--;
        updateRoutePagination();
      }}
    }}

    function nextRoutePage() {{
      currentRoutePage++;
      updateRoutePagination();
    }}

    // ----------------------------------------------------
    // Universal Ascending / Descending Table Sorter
    // ----------------------------------------------------
    const tableSortState = {{
      'ward-table': {{ col: null, asc: true }},
      'anc-table': {{ col: null, asc: true }},
      'route-table': {{ col: null, asc: true }}
    }};

    function sortTable(tableId, colIndex, onSortedCallback) {{
      const table = document.getElementById(tableId);
      if (!table) return;
      const tbody = table.querySelector('tbody');
      const rows = Array.from(tbody.querySelectorAll('tr'));
      const state = tableSortState[tableId];

      if (state.col === colIndex) {{
        state.asc = !state.asc;
      }} else {{
        state.col = colIndex;
        state.asc = true;
      }}

      // Update column header sort indicators
      const ths = table.querySelectorAll('thead th');
      ths.forEach((th, idx) => {{
        const oldInd = th.querySelector('.sort-indicator');
        if (oldInd) oldInd.remove();
        if (idx === colIndex) {{
          const ind = document.createElement('span');
          ind.className = 'sort-indicator';
          ind.innerText = state.asc ? '▴' : '▾';
          th.appendChild(ind);
        }}
      }});

      rows.sort((rowA, rowB) => {{
        const cellA = rowA.children[colIndex];
        const cellB = rowB.children[colIndex];
        if (!cellA || !cellB) return 0;

        const valA = cellA.getAttribute('data-sort') !== null ? cellA.getAttribute('data-sort') : cellA.innerText.trim();
        const valB = cellB.getAttribute('data-sort') !== null ? cellB.getAttribute('data-sort') : cellB.innerText.trim();

        // Check for ANC sort
        if (cellA.getAttribute('data-type') === 'anc') {{
          const cmp = compareAnc(valA, valB);
          return state.asc ? cmp : -cmp;
        }}

        // Check for numeric sort
        const cleanA = valA.replace(/,/g, '').replace(/%/g, '');
        const cleanB = valB.replace(/,/g, '').replace(/%/g, '');
        const numA = parseFloat(cleanA);
        const numB = parseFloat(cleanB);
        if (!isNaN(numA) && !isNaN(numB) && !isNaN(Number(cleanA)) && !isNaN(Number(cleanB))) {{
          return state.asc ? (numA - numB) : (numB - numA);
        }}

        // Text locale comparison
        const cmp = valA.localeCompare(valB, undefined, {{ numeric: true, sensitivity: 'base' }});
        return state.asc ? cmp : -cmp;
      }});

      // Re-append in sorted order
      rows.forEach(r => tbody.appendChild(r));

      if (onSortedCallback) {{
        onSortedCallback();
      }}
    }}

    function initSortableTable(tableId, onSortedCallback) {{
      const table = document.getElementById(tableId);
      if (!table) return;
      const ths = table.querySelectorAll('thead th');
      ths.forEach((th, idx) => {{
        th.title = 'Click to sort ascending / descending';
        th.addEventListener('click', () => {{
          sortTable(tableId, idx, onSortedCallback);
        }});
      }});
    }}

    // Initialize sortable tables
    initSortableTable('ward-table');
    initSortableTable('anc-table', filterAncTable);
    initSortableTable('route-table', () => {{
      currentRoutePage = 1;
      updateRoutePagination();
    }});

    // Initialize pagination
    updateRoutePagination();

  </script>
</body>
</html>
"""

out_tables = os.path.join(BASE_DIR, 'tables.html')
with open(out_tables, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"Successfully compiled Tables and Graphs: {out_tables}")

if __name__ == '__main__':
    pass
