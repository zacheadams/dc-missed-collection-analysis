#!/usr/bin/env python3
"""
Compiles the Unified Operational Report (report.html).
Consolidates 180-day Ward, ANC, and SMD address deduplication analysis
with DPW collection route operational analysis and the 223-route performance matrix.
Strictly adheres to:
- No emojis anywhere in UI or code
- American paper standard (US Letter: 8.5" x 11") for print and PDF exports
- Offline operation via local vendored assets in assets/vendor/
"""

import os
import sys
import json
from collections import defaultdict
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load Datasets
addr_stats_path = os.path.join(BASE_DIR, 'data', 'smd_180d_address_stats.json')
route_stats_path = os.path.join(BASE_DIR, 'data', 'route_180d_stats.json')
route_areas_path = os.path.join(BASE_DIR, 'data', 'route_areas.json')

with open(addr_stats_path, 'r', encoding='utf-8') as f:
    addr_data = json.load(f)

with open(route_stats_path, 'r', encoding='utf-8') as f:
    route_data = json.load(f)

route_areas = {}
if os.path.exists(route_areas_path):
    with open(route_areas_path, 'r', encoding='utf-8') as f:
        route_areas = json.load(f)

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
    r_copy['area_sq_mi'] = route_areas.get('trash', {}).get(aid, {}).get('area_sq_mi', 0.0)
    density = round(r_copy['total'] / r_copy['area_sq_mi'], 1) if r_copy['area_sq_mi'] > 0 else 0.0
    r_copy['density'] = density
    all_routes.append(r_copy)

for r in recycle_routes:
    r_copy = dict(r)
    r_copy['stream'] = 'Recycling'
    aid = r_copy['route_id']
    r_copy['area_sq_mi'] = route_areas.get('recycle', {}).get(aid, {}).get('area_sq_mi', 0.0)
    density = round(r_copy['total'] / r_copy['area_sq_mi'], 1) if r_copy['area_sq_mi'] > 0 else 0.0
    r_copy['density'] = density
    all_routes.append(r_copy)

# Sort all routes by total requests descending
all_routes.sort(key=lambda x: x['total'], reverse=True)

# Ward Councilmembers
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

ancs_list = []
for anc, d in anc_dict.items():
    d['repeat_rate'] = round(d['repeat_addrs'] / d['unique_addrs'] * 100, 1) if d['unique_addrs'] > 0 else 0.0
    ancs_list.append(d)

# Sort ANCs by Ward, then ANC ID
ancs_list.sort(key=lambda x: (x['ward'], x['anc_id']))

# Top 10 SMDs by total requests
top10_smds = sorted(smds_list, key=lambda x: x['total'], reverse=True)[:10]

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

# HTML Template
html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Operational Report | DC DPW Missed Collection Analysis</title>

  <!-- Google Fonts: Plus Jakarta Sans & JetBrains Mono -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">

  <!-- Local Vendored Assets -->
  <script src="assets/vendor/chartjs/chart.umd.min.js"></script>
  <script src="assets/vendor/jspdf/jspdf.umd.min.js"></script>
  <script src="assets/vendor/jspdf-autotable/jspdf.plugin.autotable.min.js"></script>
  <script src="assets/vendor/html2canvas/html2canvas.min.js"></script>

  <style>
    :root {{
      --bg-dark: #070a12;
      --bg-card: #0d1322;
      --bg-panel: rgba(13, 19, 34, 0.94);
      --border: rgba(255, 255, 255, 0.10);
      --border-focus: #38bdf8;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      --primary: #0284c7;
      --primary-light: #38bdf8;
      --trash-color: #ef4444;
      --recycle-color: #10b981;
      --warning-color: #f59e0b;
      --ward-color: #a855f7;
      --font-sans: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    body {{
      background-color: var(--bg-dark);
      color: var(--text-main);
      font-family: var(--font-sans);
      line-height: 1.5;
      padding-bottom: 80px;
      -webkit-font-smoothing: antialiased;
    }}

    /* Top Navigation Bar */
    .site-nav {{
      background: rgba(7, 10, 18, 0.96);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: 0;
      z-index: 1000;
      padding: 14px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .nav-brand {{
      display: flex;
      flex-direction: column;
    }}

    .nav-title {{
      font-size: 17px;
      font-weight: 800;
      color: #ffffff;
      letter-spacing: -0.02em;
    }}

    .nav-subtitle {{
      font-size: 11px;
      color: var(--text-dim);
      font-family: var(--font-mono);
      margin-top: 1px;
    }}

    .nav-links {{
      display: flex;
      align-items: center;
      gap: 16px;
    }}

    .nav-link {{
      color: var(--text-muted);
      text-decoration: none;
      font-size: 13px;
      font-weight: 600;
      padding: 6px 12px;
      border-radius: 6px;
      transition: all 0.15s ease;
    }}

    .nav-link:hover {{
      color: #ffffff;
      background: rgba(255, 255, 255, 0.05);
    }}

    .nav-link.active {{
      color: #38bdf8;
      background: rgba(56, 189, 248, 0.12);
      border: 1px solid rgba(56, 189, 248, 0.3);
    }}

    .btn-export-global {{
      background: #0284c7;
      color: #ffffff;
      border: none;
      padding: 8px 16px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      font-family: var(--font-sans);
      transition: background 0.15s ease;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}

    .btn-export-global:hover {{
      background: #0369a1;
    }}

    .page-container {{
      max-width: 1400px;
      margin: 0 auto;
      padding: 30px 24px;
    }}

    /* Header Section */
    .report-header {{
      margin-bottom: 32px;
      padding-bottom: 24px;
      border-bottom: 1px solid var(--border);
    }}

    .report-title {{
      font-size: 28px;
      font-weight: 800;
      color: #ffffff;
      letter-spacing: -0.03em;
      margin-bottom: 8px;
    }}

    .report-meta {{
      font-size: 13px;
      color: var(--text-muted);
      display: flex;
      flex-wrap: wrap;
      gap: 18px;
    }}

    .meta-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(255, 255, 255, 0.04);
      padding: 4px 10px;
      border-radius: 4px;
      border: 1px solid var(--border);
      font-family: var(--font-mono);
      font-size: 11px;
    }}

    /* KPI Grid */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 16px;
      margin-bottom: 36px;
    }}

    .kpi-card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 20px;
    }}

    .kpi-label {{
      font-size: 12px;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 6px;
    }}

    .kpi-value {{
      font-size: 32px;
      font-weight: 800;
      font-family: var(--font-mono);
      color: #ffffff;
      line-height: 1.1;
      margin-bottom: 6px;
    }}

    .kpi-subtext {{
      font-size: 12px;
      color: var(--text-dim);
    }}

    /* Section Styling */
    .report-section {{
      margin-bottom: 48px;
    }}

    .section-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      margin-bottom: 18px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--border);
    }}

    .section-title {{
      font-size: 20px;
      font-weight: 800;
      color: #ffffff;
      letter-spacing: -0.02em;
    }}

    .section-description {{
      font-size: 13px;
      color: var(--text-muted);
      margin-top: 4px;
      max-width: 900px;
    }}

    /* Chart Cards */
    .chart-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(600px, 1fr));
      gap: 20px;
      margin-bottom: 24px;
    }}

    @media (max-width: 900px) {{
      .chart-grid {{
        grid-template-columns: 1fr;
      }}
    }}

    .chart-card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 20px;
      position: relative;
    }}

    .chart-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }}

    .chart-title {{
      font-size: 15px;
      font-weight: 700;
      color: #ffffff;
    }}

    .chart-actions {{
      display: flex;
      gap: 6px;
    }}

    .btn-export-sm {{
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border);
      color: var(--text-muted);
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 600;
      cursor: pointer;
      font-family: var(--font-mono);
      transition: all 0.15s ease;
    }}

    .btn-export-sm:hover {{
      color: #ffffff;
      border-color: var(--primary-light);
      background: rgba(56, 189, 248, 0.1);
    }}

    .chart-container {{
      height: 320px;
      position: relative;
    }}

    /* Tables */
    .table-container {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 10px;
      overflow-x: auto;
      margin-bottom: 20px;
    }}

    .table-toolbar {{
      padding: 14px 18px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border);
      flex-wrap: wrap;
      gap: 12px;
    }}

    .toolbar-filters {{
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
    }}

    .input-search {{
      background: rgba(7, 10, 18, 0.7);
      border: 1px solid var(--border);
      color: var(--text-main);
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 13px;
      font-family: var(--font-sans);
      min-width: 220px;
    }}

    .input-search:focus {{
      outline: none;
      border-color: var(--border-focus);
    }}

    .select-filter {{
      background: rgba(7, 10, 18, 0.7);
      border: 1px solid var(--border);
      color: var(--text-main);
      padding: 6px 10px;
      border-radius: 6px;
      font-size: 13px;
      font-family: var(--font-sans);
    }}

    .select-filter:focus {{
      outline: none;
      border-color: var(--border-focus);
    }}

    .data-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      text-align: left;
    }}

    .data-table th {{
      background: rgba(255, 255, 255, 0.02);
      color: var(--text-muted);
      font-weight: 700;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      padding: 12px 16px;
      border-bottom: 1px solid var(--border);
      cursor: pointer;
      user-select: none;
      white-space: nowrap;
    }}

    .data-table th:hover {{
      color: #ffffff;
    }}

    .data-table td {{
      padding: 11px 16px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
      color: var(--text-main);
      font-family: var(--font-sans);
    }}

    .data-table tr:hover td {{
      background: rgba(255, 255, 255, 0.02);
    }}

    .font-num {{
      font-family: var(--font-mono);
    }}

    .badge-trash {{
      background: rgba(239, 68, 68, 0.15);
      color: #fca5a5;
      border: 1px solid rgba(239, 68, 68, 0.3);
      padding: 2px 7px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 700;
      font-family: var(--font-mono);
      display: inline-block;
    }}

    .badge-recycle {{
      background: rgba(16, 185, 129, 0.15);
      color: #6ee7b7;
      border: 1px solid rgba(16, 185, 129, 0.3);
      padding: 2px 7px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 700;
      font-family: var(--font-mono);
      display: inline-block;
    }}

    .badge-hotspot {{
      background: rgba(245, 158, 11, 0.15);
      color: #fcd34d;
      border: 1px solid rgba(245, 158, 11, 0.3);
      padding: 2px 7px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 700;
      font-family: var(--font-mono);
      display: inline-block;
    }}

    .table-pagination {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 18px;
      border-top: 1px solid var(--border);
      font-size: 12px;
      color: var(--text-dim);
    }}

    .pagination-controls {{
      display: flex;
      gap: 6px;
    }}

    .btn-page {{
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border);
      color: var(--text-muted);
      padding: 4px 10px;
      border-radius: 4px;
      font-size: 12px;
      cursor: pointer;
    }}

    .btn-page:hover:not(:disabled) {{
      color: #ffffff;
      border-color: var(--border-focus);
    }}

    .btn-page:disabled {{
      opacity: 0.35;
      cursor: not-allowed;
    }}

    /* Print Stylesheet: US Letter (8.5in x 11in) */
    @media print {{
      @page {{
        size: letter portrait;
        margin: 0.5in;
      }}

      body {{
        background: #ffffff !important;
        color: #0f172a !important;
        font-size: 10pt;
        padding-bottom: 0;
      }}

      .site-nav,
      .table-toolbar,
      .table-pagination,
      .chart-actions,
      .btn-export-global {{
        display: none !important;
      }}

      .page-container {{
        max-width: 100% !important;
        padding: 0 !important;
      }}

      .report-title {{
        color: #0f172a !important;
        font-size: 20pt !important;
      }}

      .report-header {{
        border-bottom: 2px solid #0f172a !important;
        margin-bottom: 16pt !important;
      }}

      .kpi-card,
      .chart-card,
      .table-container {{
        background: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        color: #0f172a !important;
        box-shadow: none !important;
        page-break-inside: avoid;
        margin-bottom: 14pt !important;
      }}

      .kpi-value,
      .section-title,
      .chart-title {{
        color: #0f172a !important;
      }}

      .data-table th {{
        background: #f1f5f9 !important;
        color: #0f172a !important;
        border-bottom: 1.5pt solid #0f172a !important;
      }}

      .data-table td {{
        color: #0f172a !important;
        border-bottom: 0.5pt solid #cbd5e1 !important;
      }}

      .data-table thead {{
        display: table-header-group;
      }}

      .chart-grid {{
        grid-template-columns: 1fr 1fr !important;
        gap: 12pt !important;
      }}

      .chart-container {{
        height: 220pt !important;
      }}

      .badge-trash,
      .badge-recycle,
      .badge-hotspot {{
        border: 1px solid #64748b !important;
        color: #0f172a !important;
        background: transparent !important;
      }}
    }}
  </style>
</head>
<body>

  <!-- Top Navigation Bar -->
  <nav class="site-nav">
    <div class="nav-brand">
      <span class="nav-title">DC Missed Collection Analysis</span>
      <span class="nav-subtitle">DPW 311 Performance Monitoring</span>
    </div>
    <div class="nav-links">
      <a href="index.html" class="nav-link">Home</a>
      <a href="map.html" class="nav-link">Interactive Map</a>
      <a href="report.html" class="nav-link active">Operational Report</a>
      <a href="https://github.com/zacheadams/dc-missed-collection-analysis" target="_blank" class="nav-link">GitHub</a>
      <button onclick="window.print()" class="btn-export-global">Export Report (PDF)</button>
    </div>
  </nav>

  <main class="page-container">

    <!-- Report Header -->
    <header class="report-header">
      <h1 class="report-title">DPW Missed Collection Operational Report</h1>
      <div class="report-meta">
        <span class="meta-badge">Period: 180-Day Rolling Window</span>
        <span class="meta-badge">Data Sources: Open Data DC 311 (S0441, S0321)</span>
        <span class="meta-badge">Geography: All 8 Wards • 46 ANCs • 345 SMDs • 223 DPW Routes</span>
        <span class="meta-badge">Updated: {datetime.now().strftime('%B %d, %Y')}</span>
      </div>
    </header>

    <!-- Executive Summary KPIs -->
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">Total Service Requests (180d)</div>
        <div class="kpi-value">{citywide['total_requests']:,}</div>
        <div class="kpi-subtext">{wards_stats['1']['total'] + wards_stats['2']['total'] + wards_stats['3']['total'] + wards_stats['4']['total'] + wards_stats['5']['total'] + wards_stats['6']['total'] + wards_stats['7']['total'] + wards_stats['8']['total']:,} cataloged across 8 wards</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Unique Properties Impacted</div>
        <div class="kpi-value">{citywide['unique_addresses']:,}</div>
        <div class="kpi-subtext">{round(citywide['unique_addresses'] / citywide['total_requests'] * 100, 1)}% unique address ratio</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Chronic Repeat Properties</div>
        <div class="kpi-value" style="color: #f59e0b;">{citywide['repeat_addresses']:,}</div>
        <div class="kpi-subtext">Addresses with multiple missed collections</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Citywide Recurrence Rate</div>
        <div class="kpi-value" style="color: #ef4444;">{citywide['repeat_rate']}%</div>
        <div class="kpi-subtext">{round(citywide['requests_per_address'], 2)} avg requests per address</div>
      </div>
    </div>

    <!-- Section 1: Ward Analysis -->
    <section class="report-section" id="section-wards">
      <div class="section-header">
        <div>
          <h2 class="section-title">Ward-Level Operational Analysis</h2>
          <p class="section-description">Comparative evaluation of missed trash versus missed recycling across all 8 Wards, evaluating address deduplication and chronic recurrence rates.</p>
        </div>
      </div>

      <!-- Ward Charts -->
      <div class="chart-grid">
        <div class="chart-card">
          <div class="chart-header">
            <span class="chart-title">Missed Collections by Ward (Trash vs Recycling)</span>
            <div class="chart-actions">
              <button onclick="exportChartPng('chartWardVol', 'ward-collection-volume')" class="btn-export-sm">PNG</button>
              <button onclick="exportChartPdf('chartWardVol', 'Ward Collection Volume', 'ward-collection-volume')" class="btn-export-sm">PDF</button>
            </div>
          </div>
          <div class="chart-container">
            <canvas id="chartWardVol"></canvas>
          </div>
        </div>

        <div class="chart-card">
          <div class="chart-header">
            <span class="chart-title">Address Recurrence by Ward (Single vs Repeat Properties)</span>
            <div class="chart-actions">
              <button onclick="exportChartPng('chartWardRepeat', 'ward-repeat-recurrence')" class="btn-export-sm">PNG</button>
              <button onclick="exportChartPdf('chartWardRepeat', 'Ward Repeat Recurrence', 'ward-repeat-recurrence')" class="btn-export-sm">PDF</button>
            </div>
          </div>
          <div class="chart-container">
            <canvas id="chartWardRepeat"></canvas>
          </div>
        </div>
      </div>

      <!-- Ward Summary Table -->
      <div class="table-container">
        <div class="table-toolbar">
          <span style="font-weight: 700; font-size: 14px; color: #ffffff;">Ward Performance Matrix</span>
          <div>
            <button onclick="exportTableCsv('table-wards', 'dc-wards-performance')" class="btn-export-sm">CSV</button>
            <button onclick="exportTablePdf('table-wards', 'DC Ward Performance Summary', 'dc-wards-performance')" class="btn-export-sm">PDF</button>
          </div>
        </div>
        <table class="data-table" id="table-wards">
          <thead>
            <tr>
              <th>Ward</th>
              <th>Councilmember</th>
              <th>Total Requests</th>
              <th>Missed Trash</th>
              <th>Missed Recycling</th>
              <th>Unique Addrs</th>
              <th>Repeat Addrs</th>
              <th>Repeat Rate</th>
              <th>Req / Addr</th>
            </tr>
          </thead>
          <tbody>
"""

for w in range(1, 9):
    ws = wards_stats[str(w)]
    cm = ward_council[w]
    html_content += f"""            <tr>
              <td><strong style="color: #ffffff;">Ward {w}</strong></td>
              <td style="color: #cbd5e1;">{cm}</td>
              <td class="font-num" style="font-weight: 700; color: #ffffff;">{ws['total']:,}</td>
              <td class="font-num" style="color: #fca5a5;">{ws['trash']:,}</td>
              <td class="font-num" style="color: #6ee7b7;">{ws['recycling']:,}</td>
              <td class="font-num">{ws['unique_addresses']:,}</td>
              <td class="font-num" style="color: #fcd34d;">{ws['repeat_addresses']:,}</td>
              <td class="font-num"><span class="badge-hotspot">{ws['repeat_rate']}%</span></td>
              <td class="font-num">{ws['requests_per_address']}</td>
            </tr>
"""

html_content += f"""          </tbody>
        </table>
      </div>
    </section>

    <!-- Section 2: ANC Analysis -->
    <section class="report-section" id="section-ancs">
      <div class="section-header">
        <div>
          <h2 class="section-title">Advisory Neighborhood Commission (ANC) Breakdown</h2>
          <p class="section-description">Hierarchical aggregation across all 46 ANCs. Filter by Ward or search by ANC code to evaluate localized collection reliability.</p>
        </div>
      </div>

      <div class="table-container">
        <div class="table-toolbar">
          <div class="toolbar-filters">
            <input type="text" id="anc-search" class="input-search" placeholder="Search ANC (e.g. 1A, 7B)..." oninput="filterAncTable()">
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
          <div>
            <button onclick="exportTableCsv('table-ancs', 'dc-anc-performance')" class="btn-export-sm">CSV</button>
            <button onclick="exportTablePdf('table-ancs', 'DC ANC Performance Breakdown', 'dc-anc-performance')" class="btn-export-sm">PDF</button>
          </div>
        </div>
        <table class="data-table" id="table-ancs">
          <thead>
            <tr>
              <th onclick="sortAncTable(0)">ANC</th>
              <th onclick="sortAncTable(1)">Ward</th>
              <th onclick="sortAncTable(2)">SMDs</th>
              <th onclick="sortAncTable(3)">Total Requests</th>
              <th onclick="sortAncTable(4)">Missed Trash</th>
              <th onclick="sortAncTable(5)">Missed Recycling</th>
              <th onclick="sortAncTable(6)">Unique Addrs</th>
              <th onclick="sortAncTable(7)">Repeat Addrs</th>
              <th onclick="sortAncTable(8)">Repeat Rate</th>
            </tr>
          </thead>
          <tbody id="anc-table-body">
"""

for a in ancs_list:
    html_content += f"""            <tr data-anc="{a['anc_id']}" data-ward="{a['ward']}">
              <td><strong style="color: #38bdf8;">ANC {a['anc_id']}</strong></td>
              <td>Ward {a['ward']}</td>
              <td class="font-num">{a['smd_count']}</td>
              <td class="font-num" style="font-weight: 700; color: #ffffff;">{a['total']:,}</td>
              <td class="font-num" style="color: #fca5a5;">{a['trash']:,}</td>
              <td class="font-num" style="color: #6ee7b7;">{a['recycling']:,}</td>
              <td class="font-num">{a['unique_addrs']:,}</td>
              <td class="font-num" style="color: #fcd34d;">{a['repeat_addrs']:,}</td>
              <td class="font-num"><span class="badge-hotspot">{a['repeat_rate']}%</span></td>
            </tr>
"""

html_content += f"""          </tbody>
        </table>
      </div>
    </section>

    <!-- Section 3: SMD Analysis -->
    <section class="report-section" id="section-smds">
      <div class="section-header">
        <div>
          <h2 class="section-title">Single Member District (SMD) Rankings & Hot Spots</h2>
          <p class="section-description">High-volume Single Member Districts experiencing severe missed collections and address recurrence over the 180-day evaluation period.</p>
        </div>
      </div>

      <!-- Top 10 SMDs Table -->
      <div class="table-container" style="margin-bottom: 24px;">
        <div class="table-toolbar">
          <span style="font-weight: 700; font-size: 14px; color: #ffffff;">Top 10 High-Volume Single Member Districts</span>
          <div>
            <button onclick="exportTableCsv('table-top-smds', 'dc-top10-smds')" class="btn-export-sm">CSV</button>
            <button onclick="exportTablePdf('table-top-smds', 'Top 10 High-Volume SMDs', 'dc-top10-smds')" class="btn-export-sm">PDF</button>
          </div>
        </div>
        <table class="data-table" id="table-top-smds">
          <thead>
            <tr>
              <th>Rank</th>
              <th>SMD</th>
              <th>ANC</th>
              <th>Ward</th>
              <th>Total Requests</th>
              <th>Missed Trash</th>
              <th>Missed Recycling</th>
              <th>Unique Addrs</th>
              <th>Repeat Addrs</th>
              <th>Repeat Rate</th>
              <th>Max Incident Days</th>
            </tr>
          </thead>
          <tbody>
"""

for idx, smd in enumerate(top10_smds, start=1):
    html_content += f"""            <tr>
              <td class="font-num" style="font-weight: 800; color: #ffffff;">#{idx}</td>
              <td><strong style="color: #facc15;">SMD {smd['smd_id']}</strong></td>
              <td>ANC {smd['anc_id']}</td>
              <td>Ward {smd['ward']}</td>
              <td class="font-num" style="font-weight: 700; color: #ffffff;">{smd['total']}</td>
              <td class="font-num" style="color: #fca5a5;">{smd['trash']}</td>
              <td class="font-num" style="color: #6ee7b7;">{smd['recycling']}</td>
              <td class="font-num">{smd['unique_addrs']}</td>
              <td class="font-num" style="color: #fcd34d;">{smd['repeat_addrs']}</td>
              <td class="font-num"><span class="badge-hotspot">{smd['repeat_rate']}%</span></td>
              <td class="font-num">{smd['max_repeat_days']} days</td>
            </tr>
"""

html_content += f"""          </tbody>
        </table>
      </div>
    </section>

    <!-- Section 4: DPW Route Operational Bottlenecks -->
    <section class="report-section" id="section-routes-ops">
      <div class="section-header">
        <div>
          <h2 class="section-title">DPW Route Operations &amp; Bottlenecks</h2>
          <p class="section-description">Evaluating collection performance across 103 Trash Routes and 120 Recycling Routes by day of week, route geographic scale, and fleet load distribution.</p>
        </div>
      </div>

      <!-- Route Operational Charts -->
      <div class="chart-grid">
        <div class="chart-card">
          <div class="chart-header">
            <span class="chart-title">Missed Collections by Scheduled Day of Week</span>
            <div class="chart-actions">
              <button onclick="exportChartPng('chartDayVol', 'day-collection-volume')" class="btn-export-sm">PNG</button>
              <button onclick="exportChartPdf('chartDayVol', 'Day Collection Volume', 'day-collection-volume')" class="btn-export-sm">PDF</button>
            </div>
          </div>
          <div class="chart-container">
            <canvas id="chartDayVol"></canvas>
          </div>
        </div>

        <div class="chart-card">
          <div class="chart-header">
            <span class="chart-title">Average Requests per Route by Day (Operational Density)</span>
            <div class="chart-actions">
              <button onclick="exportChartPng('chartDayAvg', 'day-route-density')" class="btn-export-sm">PNG</button>
              <button onclick="exportChartPdf('chartDayAvg', 'Day Route Density', 'day-route-density')" class="btn-export-sm">PDF</button>
            </div>
          </div>
          <div class="chart-container">
            <canvas id="chartDayAvg"></canvas>
          </div>
        </div>
      </div>
    </section>

    <!-- Section 5: Comprehensive Route Performance Matrix -->
    <section class="report-section" id="section-matrix">
      <div class="section-header">
        <div>
          <h2 class="section-title">Route Performance Matrix (223 Routes)</h2>
          <p class="section-description">Interactive, searchable matrix evaluating all 103 Trash Routes and 120 Recycling Routes. Filter by day of week, stream type, or geographic coverage.</p>
        </div>
      </div>

      <div class="table-container">
        <div class="table-toolbar">
          <div class="toolbar-filters">
            <input type="text" id="route-search" class="input-search" placeholder="Search route, neighborhood, or ANC..." oninput="filterRouteTable()">
            <select id="route-type-filter" class="select-filter" onchange="filterRouteTable()">
              <option value="">All Streams</option>
              <option value="Trash">Trash</option>
              <option value="Recycling">Recycling</option>
            </select>
            <select id="route-day-filter" class="select-filter" onchange="filterRouteTable()">
              <option value="">All Days</option>
              <option value="Monday">Monday</option>
              <option value="Tuesday">Tuesday</option>
              <option value="Wednesday">Wednesday</option>
              <option value="Thursday">Thursday</option>
              <option value="Friday">Friday</option>
            </select>
          </div>
          <div>
            <button onclick="exportTableCsv('table-routes', 'dc-route-performance-matrix')" class="btn-export-sm">CSV</button>
            <button onclick="exportTablePdf('table-routes', 'DPW Route Performance Matrix', 'dc-route-performance-matrix')" class="btn-export-sm">PDF</button>
          </div>
        </div>
        <table class="data-table" id="table-routes">
          <thead>
            <tr>
              <th onclick="sortRouteTable(0)">Route ID</th>
              <th onclick="sortRouteTable(1)">Stream</th>
              <th onclick="sortRouteTable(2)">Scheduled Day</th>
              <th onclick="sortRouteTable(3)">Total Requests</th>
              <th onclick="sortRouteTable(4)">Unique Addrs</th>
              <th onclick="sortRouteTable(5)">Repeat Addrs</th>
              <th onclick="sortRouteTable(6)">Repeat Rate</th>
              <th onclick="sortRouteTable(7)">Area (sq mi)</th>
              <th onclick="sortRouteTable(8)">Density (req/mi²)</th>
              <th>Coverage (Neighborhoods &amp; ANCs)</th>
            </tr>
          </thead>
          <tbody id="route-table-body">
"""

for r in all_routes:
    stream_badge = f'<span class="badge-trash">Trash</span>' if r['stream'] == 'Trash' else f'<span class="badge-recycle">Recycling</span>'
    html_content += f"""            <tr data-stream="{r['stream']}" data-day="{r['schedule']}" data-search="{r['route_id'].lower()} {r['area_desc'].lower()}">
              <td><strong style="color: #ffffff;">{r['route_id']}</strong></td>
              <td>{stream_badge}</td>
              <td style="color: #cbd5e1;">{r['schedule']}</td>
              <td class="font-num" style="font-weight: 700; color: #ffffff;">{r['total']:,}</td>
              <td class="font-num">{r['unique_addrs']:,}</td>
              <td class="font-num" style="color: #fcd34d;">{r['repeat_addrs']:,}</td>
              <td class="font-num"><span class="badge-hotspot">{r['repeat_rate']}%</span></td>
              <td class="font-num">{r['area_sq_mi']}</td>
              <td class="font-num" style="font-weight: 600;">{r['density']}</td>
              <td style="font-size: 12px; color: #94a3b8; max-width: 320px;">{r['area_desc']}</td>
            </tr>
"""

html_content += f"""          </tbody>
        </table>
        <div class="table-pagination">
          <span id="route-page-info">Showing 1 to 25 of {len(all_routes)} routes</span>
          <div class="pagination-controls">
            <button id="btn-prev-route" onclick="prevRoutePage()" class="btn-page" disabled>Previous</button>
            <button id="btn-next-route" onclick="nextRoutePage()" class="btn-page">Next</button>
          </div>
        </div>
      </div>
    </section>

  </main>

  <script>
    // ----------------------------------------------------
    // Chart 1: Missed Collections by Ward (Trash vs Recycling)
    // ----------------------------------------------------
    const ctxWardVol = document.getElementById('chartWardVol').getContext('2d');
    const chartWardVol = new Chart(ctxWardVol, {{
      type: 'bar',
      data: {{
        labels: {json.dumps(chart_ward_labels)},
        datasets: [
          {{
            label: 'Missed Trash',
            data: {json.dumps(chart_ward_trash)},
            backgroundColor: '#ef4444',
            borderRadius: 4
          }},
          {{
            label: 'Missed Recycling',
            data: {json.dumps(chart_ward_rec)},
            backgroundColor: '#10b981',
            borderRadius: 4
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{
            position: 'top',
            labels: {{ color: '#cbd5e1', font: {{ family: 'Plus Jakarta Sans', size: 12 }} }}
          }}
        }},
        scales: {{
          x: {{
            stacked: true,
            ticks: {{ color: '#94a3b8' }},
            grid: {{ color: 'rgba(255, 255, 255, 0.05)' }}
          }},
          y: {{
            stacked: true,
            ticks: {{ color: '#94a3b8' }},
            grid: {{ color: 'rgba(255, 255, 255, 0.05)' }}
          }}
        }}
      }}
    }});

    // ----------------------------------------------------
    // Chart 2: Address Recurrence by Ward
    // ----------------------------------------------------
    const ctxWardRepeat = document.getElementById('chartWardRepeat').getContext('2d');
    const chartWardRepeat = new Chart(ctxWardRepeat, {{
      type: 'bar',
      data: {{
        labels: {json.dumps(chart_ward_labels)},
        datasets: [
          {{
            label: 'Single-Incident Properties',
            data: {json.dumps(chart_ward_single)},
            backgroundColor: '#0284c7',
            borderRadius: 4
          }},
          {{
            label: 'Repeat Properties',
            data: {json.dumps(chart_ward_repeat)},
            backgroundColor: '#f59e0b',
            borderRadius: 4
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{
            position: 'top',
            labels: {{ color: '#cbd5e1', font: {{ family: 'Plus Jakarta Sans', size: 12 }} }}
          }}
        }},
        scales: {{
          x: {{
            stacked: true,
            ticks: {{ color: '#94a3b8' }},
            grid: {{ color: 'rgba(255, 255, 255, 0.05)' }}
          }},
          y: {{
            stacked: true,
            ticks: {{ color: '#94a3b8' }},
            grid: {{ color: 'rgba(255, 255, 255, 0.05)' }}
          }}
        }}
      }}
    }});

    // ----------------------------------------------------
    // Chart 3: Requests by Collection Day
    // ----------------------------------------------------
    const ctxDayVol = document.getElementById('chartDayVol').getContext('2d');
    const chartDayVol = new Chart(ctxDayVol, {{
      type: 'bar',
      data: {{
        labels: {json.dumps(days_order)},
        datasets: [
          {{
            label: 'Trash',
            data: {json.dumps(chart_day_trash)},
            backgroundColor: '#ef4444',
            borderRadius: 4
          }},
          {{
            label: 'Recycling',
            data: {json.dumps(chart_day_rec)},
            backgroundColor: '#10b981',
            borderRadius: 4
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{
            position: 'top',
            labels: {{ color: '#cbd5e1', font: {{ family: 'Plus Jakarta Sans', size: 12 }} }}
          }}
        }},
        scales: {{
          x: {{
            ticks: {{ color: '#94a3b8' }},
            grid: {{ color: 'rgba(255, 255, 255, 0.05)' }}
          }},
          y: {{
            ticks: {{ color: '#94a3b8' }},
            grid: {{ color: 'rgba(255, 255, 255, 0.05)' }}
          }}
        }}
      }}
    }});

    // ----------------------------------------------------
    // Chart 4: Daily Route Average Density
    // ----------------------------------------------------
    const ctxDayAvg = document.getElementById('chartDayAvg').getContext('2d');
    const chartDayAvg = new Chart(ctxDayAvg, {{
      type: 'line',
      data: {{
        labels: {json.dumps(days_order)},
        datasets: [
          {{
            label: 'Trash Avg Req/Route',
            data: {json.dumps(chart_day_avg_trash)},
            borderColor: '#ef4444',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            fill: true,
            tension: 0.3
          }},
          {{
            label: 'Recycling Avg Req/Route',
            data: {json.dumps(chart_day_avg_rec)},
            borderColor: '#10b981',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            fill: true,
            tension: 0.3
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{
            position: 'top',
            labels: {{ color: '#cbd5e1', font: {{ family: 'Plus Jakarta Sans', size: 12 }} }}
          }}
        }},
        scales: {{
          x: {{
            ticks: {{ color: '#94a3b8' }},
            grid: {{ color: 'rgba(255, 255, 255, 0.05)' }}
          }},
          y: {{
            ticks: {{ color: '#94a3b8' }},
            grid: {{ color: 'rgba(255, 255, 255, 0.05)' }}
          }}
        }}
      }}
    }});

    // ----------------------------------------------------
    // Static Export Handlers (US Letter: 8.5in x 11in)
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
      const imgData = canvas.toDataURL('image/png', 2.0);

      // Title Banner
      doc.setFont('Helvetica', 'bold');
      doc.setFontSize(16);
      doc.setTextColor(15, 23, 42);
      doc.text(title, 0.75, 0.75);

      doc.setFont('Helvetica', 'normal');
      doc.setFontSize(10);
      doc.setTextColor(100, 116, 139);
      doc.text('District of Columbia DPW Missed Collection Analysis', 0.75, 1.0);
      doc.text(`Generated: ${{new Date().toLocaleDateString()}} • US Letter Format`, 0.75, 1.2);

      // Insert Chart Image
      doc.addImage(imgData, 'PNG', 0.75, 1.4, 9.5, 5.5);
      doc.save(`${{filename}}.pdf`);
    }}

    function exportTableCsv(tableId, filename) {{
      const table = document.getElementById(tableId);
      const rows = Array.from(table.querySelectorAll('tr')).filter(r => r.style.display !== 'none');
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

    function exportTablePdf(tableId, title, filename) {{
      const {{ jsPDF }} = window.jspdf;
      const doc = new jsPDF({{ orientation: 'portrait', format: 'letter', unit: 'in' }});

      doc.setFont('Helvetica', 'bold');
      doc.setFontSize(14);
      doc.setTextColor(15, 23, 42);
      doc.text(title, 0.5, 0.6);

      doc.setFont('Helvetica', 'normal');
      doc.setFontSize(9);
      doc.setTextColor(100, 116, 139);
      doc.text(`District of Columbia DPW Missed Collection Analysis • ${{new Date().toLocaleDateString()}}`, 0.5, 0.8);

      doc.autoTable({{
        html: `#${{tableId}}`,
        startY: 0.95,
        margin: {{ top: 0.5, bottom: 0.5, left: 0.5, right: 0.5 }},
        theme: 'striped',
        styles: {{ fontSize: 8, cellPadding: 0.05, font: 'Helvetica' }},
        headStyles: {{ fillColor: [15, 23, 42], textColor: [255, 255, 255], fontStyle: 'bold' }},
        alternateRowStyles: {{ fillColor: [248, 250, 252] }}
      }});

      doc.save(`${{filename}}.pdf`);
    }}

    // ----------------------------------------------------
    // ANC Table Filtering & Sorting
    // ----------------------------------------------------
    function filterAncTable() {{
      const q = document.getElementById('anc-search').value.toLowerCase();
      const w = document.getElementById('anc-ward-filter').value;
      const rows = document.querySelectorAll('#anc-table-body tr');

      rows.forEach(r => {{
        const anc = r.getAttribute('data-anc').toLowerCase();
        const ward = r.getAttribute('data-ward');
        const matchQ = !q || anc.includes(q);
        const matchW = !w || ward === w;
        r.style.display = (matchQ && matchW) ? '' : 'none';
      }});
    }}

    // ----------------------------------------------------
    // Route Table Filtering & Pagination
    // ----------------------------------------------------
    let currentRoutePage = 1;
    const routesPerPage = 25;

    function getFilteredRouteRows() {{
      const q = document.getElementById('route-search').value.toLowerCase();
      const stream = document.getElementById('route-type-filter').value;
      const day = document.getElementById('route-day-filter').value;
      const allRows = Array.from(document.querySelectorAll('#route-table-body tr'));

      return allRows.filter(r => {{
        const rowStream = r.getAttribute('data-stream');
        const rowDay = r.getAttribute('data-day');
        const rowSearch = r.getAttribute('data-search');

        const matchQ = !q || rowSearch.includes(q);
        const matchStream = !stream || rowStream === stream;
        const matchDay = !day || rowDay === day;

        return matchQ && matchStream && matchDay;
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

    // Initial setup on DOM ready
    window.addEventListener('DOMContentLoaded', () => {{
      updateRoutePagination();
    }});
  </script>
</body>
</html>
"""

out_report = os.path.join(BASE_DIR, 'report.html')
with open(out_report, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"Successfully compiled Unified Operational Report: {out_report}")

if __name__ == '__main__':
    pass
