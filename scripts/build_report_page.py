#!/usr/bin/env python3
"""
Compiles the Unified Operational Report (report.html).
Consolidates 180-day Ward, ANC, and SMD address deduplication analysis
with DPW collection route operational analysis and the 223-route performance matrix.
Strictly adheres to:
- Target audience: DC Department of Public Works (DPW) and Collections leadership
- Proof-of-concept operational framing with DC Council Oversight context
- Title: 'Missed Collections' with subhead 'Where—and why—are trash and recycling pickups missed in DC?'
- Primary monospace font (IBM Plex Mono)
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
  <title>Missed Collections • The Report</title>

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
      margin-bottom: 0;
    }}

    /* Report Narrative */
    .report-narrative {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 2px;
      padding: 24px 28px;
      margin-bottom: 32px;
      font-size: 13px;
      line-height: 1.7;
      color: var(--text-main);
      box-shadow: var(--card-shadow);
    }}

    .report-narrative p {{
      margin: 0 0 16px 0;
    }}

    .report-narrative p:last-child {{
      margin-bottom: 0;
    }}

    .report-narrative ul {{
      margin: 0 0 16px 24px;
      padding: 0;
    }}

    .report-narrative li {{
      margin-bottom: 8px;
      line-height: 1.6;
    }}

    .report-narrative a {{
      color: var(--accent);
      text-decoration: underline;
      text-underline-offset: 2px;
    }}

    .report-narrative a:hover {{
      color: var(--accent-hover);
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
      border-radius: 2px;
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

    .badge-hotspot {{
      background: rgba(217, 119, 6, 0.12);
      color: var(--warning-color);
      border: 1px solid rgba(217, 119, 6, 0.3);
      padding: 1px 6px;
      border-radius: 2px;
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
      border-radius: 2px;
      font-size: 11px;
      cursor: pointer;
      font-family: var(--font-mono);
    }}

    .btn-page:hover:not(:disabled) {{
      border-color: var(--text-main);
    }}

    /* Footer */
    .site-footer {{
      text-align: center;
      padding-top: 24px;
      margin-top: 32px;
      margin-bottom: 24px;
      border-top: 1px solid var(--border);
      font-size: 11px;
      color: var(--text-dim);
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
      <span class="nav-title">Missed Collections</span>
      <span class="nav-subtitle">Where—and why—are <span class="kw-trash">trash</span> and <span class="kw-recycle">recycling</span> pickups missed in DC?</span>
    </div>
    <div class="nav-links">
      <a href="index.html" class="nav-link">Index</a>
      <a href="map.html" class="nav-link">The Map</a>
      <a href="report.html" class="nav-link active">The Report</a>
      <button onclick="toggleTheme()" class="btn-action" id="theme-toggle-btn">Theme: Light</button>
      <button onclick="window.print()" class="btn-action">Export Report (PDF)</button>
    </div>
  </nav>

  <div class="page-container">

    <!-- Report Header -->
    <header class="report-header">
      <h1 class="report-title">The Report</h1>
    </header>

    <!-- Report Narrative -->
    <div class="report-narrative">
      <p>If you don’t care about my editorialization, and just care about the charts, you’re wrong (*unless you’ve already read this), but feel free to keep scrolling to the charts below.</p>

      <p>Last Friday, the DC Department of Public Works (DPW) launched a <a href="https://dpw.dc.gov/collection-status-map" target="_blank" rel="noopener">Status Collection Map</a>, so that residents serviced by DPW could see when they could expect their <span class="kw-trash">trash</span> or <span class="kw-recycle">recycling</span> to be picked up.</p>

      <p>Like the actual solid waste service, as of 9 PM on Wednesday, September 23rd, 2026, that website was not working as intended.</p>

      <div style="margin: 20px 0;">
        <img src="assets/dpw-status-map-error.png" onerror="this.onerror=null; this.src='https://github.com/user-attachments/assets/9d52cd97-cd17-40c9-a0fa-72882378bbee'" alt="DPW Status Collection Map Error" style="max-width: 100%; height: auto; border: 1px solid var(--border); border-radius: 2px; display: block;" />
      </div>

      <p>And so, inspired by some of <a href="https://www.axios.com/local/washington-dc/2026/07/31/311-app-alternatives-josh-jacobson-civic-tech-government-tools" target="_blank" rel="noopener">Josh Jacobson’s work</a> creating dashboards to supplant insufficient trackers for kiddie pools and rat treatment, I was motivated to make something better.</p>

      <p>What I built (with substantial coding assistance from my robot) is a dashboard of 311 requests for missed <span class="kw-trash">trash</span> and missed <span class="kw-recycle">recycling</span> pickup. It offers two time periods to choose from: the last 30 days and the last 180 days (which, notably, entirely falls after the <a href="https://51st.news/dc-spent-67-million-cleaning-up-after-januarys-snowstorm/" target="_blank" rel="noopener">Snowcrete debacle</a> and the March 4th Performance Oversight Hearing - <a href="https://video.oct.dc.gov/VOD/DCC/2026_03/03_04_26_PubWorks.html" target="_blank" rel="noopener">VOD</a> + <a href="https://github.com/user-attachments/files/32541391/dpw.responses.to.performance.oversight.questions.pdf" target="_blank" rel="noopener">written responses</a>). It allows you to look citywide, at your Ward, at your Advisory Neighborhood Commission (ANC), or even at your Single Member District (SMD). You want to see what the actual route the pickup drivers are driving? You betcha, that’s there.</p>

      <p>311 requests are an imperfect measure, but I suspect they underestimate missed pickups, because it’s dependent on the individuals reporting them missed. 311 itself has had a <a href="https://51st.news/311-app-dc-ouc/" target="_blank" rel="noopener">smattering of issues</a> this year, many have started using <a href="https://snap311.app/" target="_blank" rel="noopener">Snap311</a> instead of the official app, but I digress.</p>

      <p>So what does the dashboard show, what stories do the data tell? I can’t figure out all of this, but here are some of my takeaways from a few days of manic panic:</p>
      <ul>
        <li>DPW services <a href="https://washingtonian.com/2023/04/21/dcs-new-curbside-composting-program-everything-you-need-to-know/" target="_blank" rel="noopener">over 100,000 households</a> in DC.</li>
        <li>~6,000 of them in the last 6 months reported missed service, a total of ~9,000 times.</li>
        <li>~1 in 4 households who reported a missed collection in the last 6 months reported another. Many reported numerous times.</li>
        <li>Mondays were the least reliable day. Thursday was the most reliable day. Maybe sanitation workers are like Garfield.</li>
        <li>Wards 5, 7, and especially 4, had the most tickets filed. All Wards, by law, have about the same number of people, though they don’t have the same number of DPW-served addresses, and I suspect that there’s significant association between the number of served addresses and number of tickets (a few quick searches off-hand support that hypothesis).</li>
      </ul>

      <p>The clearest overall theme is that DPW is ignoring their massive service problem. Service across all 8 Wards, all 46 ANCs, all 345 SMDs, and all 223 (103 <span class="kw-trash">trash</span> and 120 <span class="kw-recycle">recycling</span>) routes deserve scrutiny. Ask DPW and they might tell you that there are frequent call-outs, which were more intense in the <a href="https://grist.org/extreme-heat/yes-this-summer-really-was-as-hot-as-you-think-it-was/" target="_blank" rel="noopener">hottest summer on record</a>, but they have the historical data (or just intuitive knowledge) to predict this, and they could, they should, they must hire more people. Less staff leads to more overtime, which leads to more expenditure, which leads to less staff. It’s a vicious cycle.</p>

      <p>DPW has not had a good year. But it’s hard to look at the <a href="https://github.com/user-attachments/files/32562927/FY26.Plan.-.DPW.pdf" target="_blank" rel="noopener">FY2026 Performance Plan</a> and think key performance indicators have been met. Sure, residential <span class="kw-trash">trash</span> and <span class="kw-recycle">recycling</span> pickup under the Solid Waste Management Administration isn’t <em>all</em> of what DPW does, but it certainly is one of the most salient touchpoints to the District government. If people don’t get routine service—and worse, if people can no longer depend on reporting missed service—faith in basic functions of local government start to erode pretty quickly. My neighbors have had repeat misses and have been frankly gaslit by absurd responses from DPW and their community relations team, and something’s got to give. We need a real plan, and solid, material change, sooner rather than later.</p>

      <p>If you’re reading this and you’re a resident who’s missed service: keep reporting to 311, you’re not alone. Write to your ANC, Councilmember, and DPW.</p>

      <p>If you’re reading this and you’re in Council: demand answers from DPW and budget them accordingly for fixes. Make sure leadership is held accountable.</p>

      <p>If you’re reading this and you’re in DPW leadership: figure out route issues (you can use my tool to find the problems!) and adjust accordingly. Hire more people. Get it right, the city depends on you.</p>
    </div>

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
        </div>

        <table class="data-table" id="anc-table">
          <thead>
            <tr>
              <th>Ward</th>
              <th>ANC</th>
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
              <td>Ward {a['ward']}</td>
              <td><strong>ANC {a['anc_id']}</strong></td>
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

    <!-- SECTION 3: ROUTE ANALYSIS & MATRIX -->
    <section class="report-section">
      <div class="section-header">
        <div>
          <h2 class="section-title">Performance by Schedule and Route</h2>
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
            borderRadius: 2
          }},
          {{
            label: 'Repeat Properties',
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
            borderRadius: 2
          }},
          {{
            label: 'Recycling',
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
