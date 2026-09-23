#!/usr/bin/env python3
"""
Compiles the Unified Operational Report (report.html).
Consolidates 180-day Ward, ANC, and SMD address deduplication analysis
with DPW collection route operational analysis and the 223-route performance matrix.
Strictly adheres to:
- Target audience: DC Department of Public Works (DPW) SWMA and Collections leadership
- Proof-of-concept operational framing with DC Council Oversight context
- Title: 'Missed Collections' with subhead 'Where—and why—are trash and recycling pickups missed in DC?'
- Primary monospace font (JetBrains Mono)
- Lo-fi black & white design with browser-default light/dark toggle
- Keyword colorization: Trash (Red), Recycling (Green), Combined (Blue)
- No user-facing mentions of paper dimensions (US Letter preserved silently under the hood)
- No emojis anywhere in UI or code
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
  <title>Missed Collections | DC DPW Operational Analysis</title>

  <!-- Google Fonts: JetBrains Mono -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700;800&display=swap" rel="stylesheet">

  <!-- Local Vendored Assets -->
  <script src="assets/vendor/chartjs/chart.umd.min.js"></script>
  <script src="assets/vendor/jspdf/jspdf.umd.min.js"></script>
  <script src="assets/vendor/jspdf-autotable/jspdf.plugin.autotable.min.js"></script>
  <script src="assets/vendor/html2canvas/html2canvas.min.js"></script>

  <style>
    :root {{
      --font-mono: 'JetBrains Mono', monospace;

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

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
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
      align-items: center;
      gap: 10px;
    }}

    .nav-link {{
      color: var(--text-muted);
      text-decoration: none;
      font-size: 12px;
      font-weight: 600;
      padding: 5px 10px;
      border-radius: 4px;
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
      border-radius: 4px;
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

    .page-container {{
      max-width: 1300px;
      margin: 0 auto;
      padding: 24px 20px;
    }}

    /* Header Section */
    .report-header {{
      margin-bottom: 24px;
      padding-bottom: 18px;
      border-bottom: 1px solid var(--border);
    }}

    .report-title {{
      font-size: 26px;
      font-weight: 800;
      color: var(--text-main);
      letter-spacing: -0.02em;
      margin-bottom: 6px;
    }}

    .report-subhed {{
      font-size: 14px;
      font-weight: 600;
      color: var(--text-muted);
      margin-bottom: 12px;
    }}

    .report-meta {{
      font-size: 11px;
      color: var(--text-muted);
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }}

    .meta-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: var(--bg-surface);
      padding: 3px 8px;
      border-radius: 4px;
      border: 1px solid var(--border);
      font-size: 10px;
    }}

    /* Operational Context Box */
    .context-box {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 16px 18px;
      margin-bottom: 28px;
      font-size: 12px;
      color: var(--text-muted);
      line-height: 1.6;
      box-shadow: var(--card-shadow);
    }}

    .context-box a {{
      color: var(--accent);
      text-decoration: underline;
    }}

    .context-box a:hover {{
      color: var(--accent-hover);
    }}

    /* KPI Grid */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
      margin-bottom: 28px;
    }}

    .kpi-card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 16px;
      box-shadow: var(--card-shadow);
    }}

    .kpi-label {{
      font-size: 10px;
      font-weight: 700;
      color: var(--text-dim);
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin-bottom: 4px;
    }}

    .kpi-value {{
      font-size: 26px;
      font-weight: 800;
      color: var(--text-main);
      line-height: 1.1;
      margin-bottom: 4px;
    }}

    .kpi-subtext {{
      font-size: 11px;
      color: var(--text-muted);
    }}

    /* Section Styling */
    .report-section {{
      margin-bottom: 36px;
    }}

    .section-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
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

    .section-description {{
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 3px;
      max-width: 960px;
      line-height: 1.5;
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
      border-radius: 6px;
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
      font-size: 13px;
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
    }}

    /* Tables */
    .table-container {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 6px;
      overflow-x: auto;
      margin-bottom: 18px;
      box-shadow: var(--card-shadow);
    }}

    .table-toolbar {{
      padding: 10px 14px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border);
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
      border-radius: 4px;
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
      border-radius: 4px;
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
    }}

    .data-table th:hover {{
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
      border-radius: 3px;
      font-size: 10px;
      font-weight: 700;
      display: inline-block;
    }}

    .badge-recycle {{
      background: rgba(22, 163, 74, 0.1);
      color: var(--recycle-color);
      border: 1px solid rgba(22, 163, 74, 0.3);
      padding: 1px 6px;
      border-radius: 3px;
      font-size: 10px;
      font-weight: 700;
      display: inline-block;
    }}

    .badge-hotspot {{
      background: rgba(217, 119, 6, 0.12);
      color: var(--warning-color);
      border: 1px solid rgba(217, 119, 6, 0.3);
      padding: 1px 6px;
      border-radius: 3px;
      font-size: 10px;
      font-weight: 700;
      display: inline-block;
    }}

    .table-pagination {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 10px 14px;
      border-top: 1px solid var(--border);
      font-size: 11px;
      color: var(--text-dim);
    }}

    .pagination-controls {{
      display: flex;
      gap: 6px;
    }}

    .btn-page {{
      background: var(--bg-surface);
      border: 1px solid var(--border);
      color: var(--text-main);
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 11px;
      cursor: pointer;
      font-family: var(--font-mono);
    }}

    .btn-page:hover:not(:disabled) {{
      border-color: var(--text-main);
    }}

    .btn-page:disabled {{
      opacity: 0.4;
      cursor: not-allowed;
    }}

    /* Print Formatting */
    @media print {{
      @page {{
        size: letter portrait;
        margin: 0.5in;
      }}

      body {{
        background: #ffffff !important;
        color: #000000 !important;
        padding-bottom: 0 !important;
      }}

      .site-nav,
      .chart-actions,
      .table-toolbar,
      .table-pagination {{
        display: none !important;
      }}

      .chart-card,
      .table-container,
      .kpi-card,
      .context-box {{
        border: 1px solid #cccccc !important;
        box-shadow: none !important;
        break-inside: avoid;
        page-break-inside: avoid;
      }}

      .chart-grid {{
        grid-template-columns: 1fr 1fr !important;
      }}

      .chart-container {{
        height: 240px !important;
      }}
    }}
  </style>
</head>
<body>

  <!-- Top Navigation Bar -->
  <nav class="site-nav">
    <div class="nav-brand">
      <span class="nav-title">DC Missed Collection Analysis</span>
      <span class="nav-subtitle">Operational Analysis • Solid Waste Management</span>
    </div>
    <div class="nav-links">
      <a href="index.html" class="nav-link">Home</a>
      <a href="map.html" class="nav-link">Interactive Map</a>
      <a href="report.html" class="nav-link active">Operational Report</a>
      <a href="https://github.com/zacheadams/dc-missed-collection-analysis" target="_blank" class="nav-link">GitHub</a>
      <button onclick="toggleTheme()" class="btn-action" id="theme-toggle-btn">Theme: Light</button>
      <button onclick="window.print()" class="btn-action">Print Report</button>
    </div>
  </nav>

  <div class="page-container">

    <!-- Report Header -->
    <header class="report-header">
      <h1 class="report-title">Missed Collections</h1>
      <div class="report-subhed">Where—and why—are trash and recycling pickups missed in DC?</div>
      <div class="report-meta">
        <span class="meta-badge">Period: Past 180 Days (March 25, 2026 - September 21, 2026)</span>
        <span class="meta-badge">Source: DC 311 Open Data</span>
        <span class="meta-badge">Scope: 8 Wards • 46 ANCs • 345 SMDs • 223 DPW Routes</span>
        <span class="meta-badge">Audience: DC Department of Public Works (SWMA)</span>
      </div>
    </header>

    <!-- Operational Context & Overview -->
    <div class="context-box">
      This proof-of-concept report analyzes Department of Public Works (DPW) residential missed collections across Washington, DC. Prepared for the <strong>Solid Waste Management Administration (SWMA)</strong>, route supervisors, and the Data Analytics &amp; Research Administration, it provides spatial and operational intelligence to isolate chronic address recurrence, evaluate daily fleet workload imbalances, and support DPW's ongoing <strong>Phase 2 Route Re-Optimization</strong>. Context is grounded in testimony from the DC Council Committee on Public Works and Operations <a href="https://video.oct.dc.gov/VOD/DCC/2026_03/03_04_26_PubWorks.html" target="_blank">2026 Performance Oversight Hearing</a> and DPW's official <a href="https://github.com/user-attachments/files/32541391/dpw.responses.to.performance.oversight.questions.pdf" target="_blank">Written Question Responses</a>, alongside the D.C. Auditor's (ODCA) ongoing discretionary audit of residential collection timeliness.
    </div>

    <!-- KPI Grid -->
    <section class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">Total Missed Collections</div>
        <div class="kpi-value kw-combined">{citywide['total_requests']:,}</div>
        <div class="kpi-subtext">Verified 311 Service Requests</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Unique Properties</div>
        <div class="kpi-value">{citywide['unique_addresses']:,}</div>
        <div class="kpi-subtext">Distinct Serviced Street Addresses</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Repeat Properties</div>
        <div class="kpi-value" style="color: var(--warning-color);">{citywide['repeat_addresses']:,}</div>
        <div class="kpi-subtext">{citywide['repeat_rate']}% Recurrence Rate (2+ Misses)</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Trash Stream (S0441)</div>
        <div class="kpi-value kw-trash">{sum(wards_stats[str(w)]['trash'] for w in range(1, 9)):,}</div>
        <div class="kpi-subtext">{round(sum(wards_stats[str(w)]['trash'] for w in range(1, 9)) / citywide['total_requests'] * 100, 1)}% of Total Volume</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Recycling Stream (S0321)</div>
        <div class="kpi-value kw-recycle">{sum(wards_stats[str(w)]['recycling'] for w in range(1, 9)):,}</div>
        <div class="kpi-subtext">{round(sum(wards_stats[str(w)]['recycling'] for w in range(1, 9)) / citywide['total_requests'] * 100, 1)}% of Total Volume</div>
      </div>
    </section>

    <!-- SECTION 1: WARD BREAKDOWN -->
    <section class="report-section">
      <div class="section-header">
        <div>
          <h2 class="section-title">1. Ward Performance and Address Recurrence Breakdown</h2>
          <p class="section-description">
            Analysis of missed collections across the District's 8 Wards, comparing <span class="kw-trash">Trash</span> vs. <span class="kw-recycle">Recycling</span> volumes and isolating repeat addresses. Under DPW's oversight definition, a "chronic miss" occurs when collection is missed 4 times within a 5-week consecutive period. Across all wards, 75.3% of impacted locations represent isolated single misses, while 24.7% (1,475 properties) face recurring collection failures requiring route supervisor attention.
          </p>
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
              <th>Ward</th>
              <th>Councilmember</th>
              <th style="text-align: right;">Total Requests</th>
              <th style="text-align: right;" class="kw-trash">Trash (S0441)</th>
              <th style="text-align: right;" class="kw-recycle">Recycling (S0321)</th>
              <th style="text-align: right;">Unique Addrs</th>
              <th style="text-align: right;">Repeat Addrs</th>
              <th style="text-align: right;">Repeat Rate</th>
              <th style="text-align: right;">Ward Share</th>
            </tr>
          </thead>
          <tbody>
"""

for w in range(1, 9):
    st = wards_stats[str(w)]
    tot = st['total']
    share = round(tot / citywide['total_requests'] * 100, 1)
    rep_rate = st['repeat_rate']
    html_content += f"""
            <tr>
              <td><strong>Ward {w}</strong></td>
              <td>{ward_council[w]}</td>
              <td style="text-align: right;" class="kw-combined"><strong>{tot:,}</strong></td>
              <td style="text-align: right;" class="kw-trash">{st['trash']:,}</td>
              <td style="text-align: right;" class="kw-recycle">{st['recycling']:,}</td>
              <td style="text-align: right;">{st['unique_addresses']:,}</td>
              <td style="text-align: right;">{st['repeat_addresses']:,}</td>
              <td style="text-align: right;">
                <span class="{ 'badge-hotspot' if rep_rate >= 24 else '' }">{rep_rate}%</span>
              </td>
              <td style="text-align: right;">{share}%</td>
            </tr>
"""

html_content += f"""
          </tbody>
        </table>
      </div>
    </section>

    <!-- SECTION 2: TOP 10 SMDs -->
    <section class="report-section">
      <div class="section-header">
        <div>
          <h2 class="section-title">2. Top 10 High-Incident Single Member Districts (SMDs)</h2>
          <p class="section-description">
            Micro-districts experiencing disproportionate missed collection frequency. In oversight testimony, DPW noted that physical alley obstructions (construction, parked vehicles), route complexity, and crew unfamiliarity cluster in specific dense corridors.
          </p>
        </div>
        <button onclick="exportTableCsv('top10-smd-table', 'dc-top10-smds')" class="btn-action">Export CSV</button>
      </div>

      <div class="table-container">
        <table class="data-table" id="top10-smd-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>SMD</th>
              <th>ANC</th>
              <th>Ward</th>
              <th>Councilmember</th>
              <th style="text-align: right;">Total Requests</th>
              <th style="text-align: right;" class="kw-trash">Trash</th>
              <th style="text-align: right;" class="kw-recycle">Recycling</th>
              <th style="text-align: right;">Unique Addrs</th>
              <th style="text-align: right;">Repeat Addrs</th>
              <th style="text-align: right;">Repeat Rate</th>
            </tr>
          </thead>
          <tbody>
"""

for rank, s in enumerate(top10_smds, 1):
    w = s['ward']
    html_content += f"""
            <tr>
              <td><strong>#{rank}</strong></td>
              <td><strong>SMD {s['smd_id']}</strong></td>
              <td>ANC {s['anc_id']}</td>
              <td>Ward {w}</td>
              <td>{ward_council[w]}</td>
              <td style="text-align: right;" class="kw-combined"><strong>{s['total']:,}</strong></td>
              <td style="text-align: right;" class="kw-trash">{s['trash']:,}</td>
              <td style="text-align: right;" class="kw-recycle">{s['recycling']:,}</td>
              <td style="text-align: right;">{s['unique_addrs']:,}</td>
              <td style="text-align: right;">{s['repeat_addrs']:,}</td>
              <td style="text-align: right;">
                <span class="badge-hotspot">{s['repeat_rate']}%</span>
              </td>
            </tr>
"""

html_content += f"""
          </tbody>
        </table>
      </div>
    </section>

    <!-- SECTION 3: ANC PERFORMANCE TABLE -->
    <section class="report-section">
      <div class="section-header">
        <div>
          <h2 class="section-title">3. Advisory Neighborhood Commission (ANC) Operational Summary</h2>
          <p class="section-description">
            Full breakdown across all 46 ANCs. Filter by Ward or search by ANC identifier to evaluate local service trends.
          </p>
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
        </div>

        <table class="data-table" id="anc-table">
          <thead>
            <tr>
              <th>ANC</th>
              <th>Ward</th>
              <th>SMD Count</th>
              <th style="text-align: right;">Total Requests</th>
              <th style="text-align: right;" class="kw-trash">Trash</th>
              <th style="text-align: right;" class="kw-recycle">Recycling</th>
              <th style="text-align: right;">Unique Addrs</th>
              <th style="text-align: right;">Repeat Addrs</th>
              <th style="text-align: right;">Repeat Rate</th>
            </tr>
          </thead>
          <tbody id="anc-table-body">
"""

for a in ancs_list:
    html_content += f"""
            <tr data-anc="{a['anc_id']}" data-ward="{a['ward']}">
              <td><strong>ANC {a['anc_id']}</strong></td>
              <td>Ward {a['ward']}</td>
              <td>{a['smd_count']} SMDs</td>
              <td style="text-align: right;" class="kw-combined"><strong>{a['total']:,}</strong></td>
              <td style="text-align: right;" class="kw-trash">{a['trash']:,}</td>
              <td style="text-align: right;" class="kw-recycle">{a['recycling']:,}</td>
              <td style="text-align: right;">{a['unique_addrs']:,}</td>
              <td style="text-align: right;">{a['repeat_addrs']:,}</td>
              <td style="text-align: right;">
                <span class="{ 'badge-hotspot' if a['repeat_rate'] >= 25 else '' }">{a['repeat_rate']}%</span>
              </td>
            </tr>
"""

html_content += f"""
          </tbody>
        </table>
      </div>
    </section>

    <!-- SECTION 4: ROUTE ANALYSIS & MATRIX -->
    <section class="report-section">
      <div class="section-header">
        <div>
          <h2 class="section-title">4. DPW Collection Route Operational Performance Matrix</h2>
          <p class="section-description">
            Analysis of all 223 DPW collection routes (103 <span class="kw-trash">Trash</span>, 120 <span class="kw-recycle">Recycling</span>)
            evaluating total missed requests, day-of-week collection schedules, geographic area, and request density.
            This matrix directly informs DPW's Phase 2 Route Re-Optimization project, which focuses on realigning route workloads and balancing heavy Monday and Tuesday volume surges across the fleet.
          </p>
        </div>
        <button onclick="exportTableCsv('route-table', 'dc-dpw-routes-matrix')" class="btn-action">Export All Routes (CSV)</button>
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
          </div>
          <div class="font-num" style="font-size: 11px; color: var(--text-dim);" id="route-page-info">
            Showing 1 to 25 of 223 routes
          </div>
        </div>

        <table class="data-table" id="route-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Route ID</th>
              <th>Stream</th>
              <th>Day</th>
              <th>Primary Ward</th>
              <th>Covered Area / ANCs</th>
              <th style="text-align: right;">Area (sq mi)</th>
              <th style="text-align: right;">Total Requests</th>
              <th style="text-align: right;">Density (req/sq mi)</th>
            </tr>
          </thead>
          <tbody id="route-table-body">
"""

for rank, r in enumerate(all_routes, 1):
    stream = r['stream']
    badge_cls = 'badge-trash' if stream == 'Trash' else 'badge-recycle'
    search_text = f"{r['route_id']} {stream} {r['schedule']} {r.get('ward', '')} {r.get('area_desc', '')}".lower()
    html_content += f"""
            <tr data-stream="{stream}" data-day="{r['schedule']}" data-search="{search_text}">
              <td><strong>#{rank}</strong></td>
              <td><strong>{r['route_id']}</strong></td>
              <td><span class="{badge_cls}">{stream}</span></td>
              <td>{r['schedule']}</td>
              <td>{r.get('ward', 'N/A')}</td>
              <td style="max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{r.get('area_desc', '')}">
                {r.get('area_desc', 'Citywide DPW service route')}
              </td>
              <td style="text-align: right;">{r['area_sq_mi']}</td>
              <td style="text-align: right;" class="{ 'kw-trash' if stream == 'Trash' else 'kw-recycle' }"><strong>{r['total']:,}</strong></td>
              <td style="text-align: right;">
                <span class="{ 'badge-hotspot' if r['density'] >= 75 else '' }">{r['density']}</span>
              </td>
            </tr>
"""

html_content += f"""
          </tbody>
        </table>

        <div class="table-pagination">
          <span>25 routes per page</span>
          <div class="pagination-controls">
            <button class="btn-page" id="btn-prev-route" onclick="prevRoutePage()" disabled>Previous</button>
            <button class="btn-page" id="btn-next-route" onclick="nextRoutePage()">Next</button>
          </div>
        </div>
      </div>
    </section>

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
    // Chart 1: Ward Volume by Stream
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
            borderRadius: 3
          }},
          {{
            label: 'Recycling (S0321)',
            data: {json.dumps(chart_ward_rec)},
            backgroundColor: '#16a34a',
            borderRadius: 3
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{
            position: 'top',
            labels: {{ font: {{ family: 'JetBrains Mono', size: 11 }} }}
          }}
        }},
        scales: {{
          x: {{
            grid: {{ color: 'rgba(0, 0, 0, 0.06)' }},
            ticks: {{ font: {{ family: 'JetBrains Mono', size: 10 }} }}
          }},
          y: {{
            grid: {{ color: 'rgba(0, 0, 0, 0.06)' }},
            ticks: {{ font: {{ family: 'JetBrains Mono', size: 10 }} }}
          }}
        }}
      }}
    }});

    // ----------------------------------------------------
    // Chart 2: Ward Address Recurrence
    // ----------------------------------------------------
    const ctxWardRep = document.getElementById('chartWardRep').getContext('2d');
    const chartWardRep = new Chart(ctxWardRep, {{
      type: 'bar',
      data: {{
        labels: {json.dumps(chart_ward_labels)},
        datasets: [
          {{
            label: 'Single Properties',
            data: {json.dumps(chart_ward_single)},
            backgroundColor: '#2563eb',
            borderRadius: 3
          }},
          {{
            label: 'Repeat Properties',
            data: {json.dumps(chart_ward_repeat)},
            backgroundColor: '#d97706',
            borderRadius: 3
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{
            position: 'top',
            labels: {{ font: {{ family: 'JetBrains Mono', size: 11 }} }}
          }}
        }},
        scales: {{
          x: {{
            stacked: true,
            grid: {{ color: 'rgba(0, 0, 0, 0.06)' }},
            ticks: {{ font: {{ family: 'JetBrains Mono', size: 10 }} }}
          }},
          y: {{
            stacked: true,
            grid: {{ color: 'rgba(0, 0, 0, 0.06)' }},
            ticks: {{ font: {{ family: 'JetBrains Mono', size: 10 }} }}
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
            backgroundColor: '#dc2626',
            borderRadius: 3
          }},
          {{
            label: 'Recycling',
            data: {json.dumps(chart_day_rec)},
            backgroundColor: '#16a34a',
            borderRadius: 3
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{
            position: 'top',
            labels: {{ font: {{ family: 'JetBrains Mono', size: 11 }} }}
          }}
        }},
        scales: {{
          x: {{
            grid: {{ color: 'rgba(0, 0, 0, 0.06)' }},
            ticks: {{ font: {{ family: 'JetBrains Mono', size: 10 }} }}
          }},
          y: {{
            grid: {{ color: 'rgba(0, 0, 0, 0.06)' }},
            ticks: {{ font: {{ family: 'JetBrains Mono', size: 10 }} }}
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
            borderColor: '#dc2626',
            backgroundColor: 'rgba(220, 38, 38, 0.1)',
            fill: true,
            tension: 0.3
          }},
          {{
            label: 'Recycling Avg Req/Route',
            data: {json.dumps(chart_day_avg_rec)},
            borderColor: '#16a34a',
            backgroundColor: 'rgba(22, 163, 74, 0.1)',
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
            labels: {{ font: {{ family: 'JetBrains Mono', size: 11 }} }}
          }}
        }},
        scales: {{
          x: {{
            grid: {{ color: 'rgba(0, 0, 0, 0.06)' }},
            ticks: {{ font: {{ family: 'JetBrains Mono', size: 10 }} }}
          }},
          y: {{
            grid: {{ color: 'rgba(0, 0, 0, 0.06)' }},
            ticks: {{ font: {{ family: 'JetBrains Mono', size: 10 }} }}
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
          chart.options.plugins.legend.labels.font = {{ family: 'JetBrains Mono', size: 11 }};
        }}
        if (chart.options.scales?.x) {{
          chart.options.scales.x.ticks.color = tickColor;
          chart.options.scales.x.ticks.font = {{ family: 'JetBrains Mono', size: 10 }};
          chart.options.scales.x.grid.color = gridColor;
        }}
        if (chart.options.scales?.y) {{
          chart.options.scales.y.ticks.color = tickColor;
          chart.options.scales.y.ticks.font = {{ family: 'JetBrains Mono', size: 10 }};
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
      const imgData = canvas.toDataURL('image/png', 2.0);

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
