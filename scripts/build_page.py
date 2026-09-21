import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
map_data_path = os.path.join(BASE_DIR, 'data/dc_map_data_v2.json')
if not os.path.exists(map_data_path):
    map_data_path = '/tmp/dc_map_data_v2.json'

addr_stats_path = os.path.join(BASE_DIR, 'data/smd_180d_address_stats.json')
if not os.path.exists(addr_stats_path):
    addr_stats_path = '/tmp/smd_180d_address_stats.json'

# 1. Load 30-day map data (for the mapping app)
with open(map_data_path) as f:
    map_data = json.load(f)

# Ensure each SMD has ward_share_pct precalculated
wards_dict = {f['properties']['ward']: f['properties']['total'] for f in map_data['wards']['features']}
for f in map_data['smds']['features']:
    w = f['properties'].get('ward')
    tot = f['properties'].get('total', 0)
    wtot = wards_dict.get(w, 0)
    f['properties']['ward_share_pct'] = round((tot / wtot * 100), 1) if wtot > 0 else 0.0

json_str = json.dumps(map_data, separators=(',', ':'))

# 2. Load 180-day address-level stats (for deduplication and repeat analysis)
with open(addr_stats_path) as f:
    addr_data_180d = json.load(f)

city_180d = addr_data_180d['citywide']
ward_180d_stats = addr_data_180d['wards'] # keys "1".."8"
smds_180d = addr_data_180d['smds'] # 345 SMDs

# Top 10 SMDs by total requests
top10_180d = sorted(smds_180d, key=lambda x: x['total'], reverse=True)[:10]

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

# Chart Data Preparation
# Chart 1: Missed Collections by Ward (Trash vs Recycling)
chart_180d_ward_labels = [f"Ward {w}" for w in range(1, 9)]
chart_180d_ward_trash = [ward_180d_stats[str(w)]["trash"] for w in range(1, 9)]
chart_180d_ward_rec = [ward_180d_stats[str(w)]["recycling"] for w in range(1, 9)]

# Chart 2: Address Recurrence by Ward (Single-Incident vs Multi-Day Repeat)
chart_180d_ward_single = [ward_180d_stats[str(w)]["unique_addresses"] - ward_180d_stats[str(w)]["repeat_addresses"] for w in range(1, 9)]
chart_180d_ward_repeat = [ward_180d_stats[str(w)]["repeat_addresses"] for w in range(1, 9)]
chart_180d_ward_repeat_pct = [ward_180d_stats[str(w)]["repeat_rate"] for w in range(1, 9)]

# Chart 4: Top 10 SMDs (Single-Incident vs Multi-Day Repeat)
chart_180d_smd_labels = [f"SMD {s['smd_id']}" for s in top10_180d]
chart_180d_smd_single = [s['single_addrs'] for s in top10_180d]
chart_180d_smd_repeat = [s['repeat_addrs'] for s in top10_180d]
chart_180d_smd_totals = [s['total'] for s in top10_180d]
chart_180d_smd_ids = [s['smd_id'] for s in top10_180d]

html_page = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DC DPW Missed Trash &amp; Recycling Analysis • Interactive Map &amp; Report</title>
  
  <!-- Leaflet CSS -->
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  
  <!-- Chart.js for Standalone Visualizations -->
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

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

    /* Header */
    .site-header {{
      margin-bottom: 24px;
    }}

    .header-top-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      flex-wrap: wrap;
      gap: 12px;
    }}

    .badge-group {{
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
    }}

    .badge {{
      font-size: 11px;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 6px;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      font-family: var(--font-mono);
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}

    .badge-source {{
      background: rgba(14, 165, 233, 0.15);
      border: 1px solid rgba(56, 189, 248, 0.35);
      color: var(--primary-light);
    }}

    .site-title {{
      font-size: 32px;
      font-weight: 800;
      letter-spacing: -0.02em;
      color: #ffffff;
      line-height: 1.2;
      margin-bottom: 8px;
    }}

    .site-subtitle {{
      font-size: 15px;
      color: var(--text-muted);
      max-width: 980px;
      line-height: 1.6;
    }}

    .site-subtitle code {{
      font-family: var(--font-mono);
      background: rgba(255, 255, 255, 0.08);
      padding: 2px 6px;
      border-radius: 4px;
      color: #cbd5e1;
      font-size: 13px;
    }}

    .site-subtitle strong {{
      color: #e2e8f0;
    }}

    /* Quick Navigation Pills */
    .quick-nav {{
      display: flex;
      gap: 10px;
      margin-top: 16px;
      flex-wrap: wrap;
    }}

    .nav-pill {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      color: var(--text-muted);
      padding: 6px 14px;
      border-radius: 8px;
      font-size: 12px;
      font-weight: 600;
      text-decoration: none;
      transition: all 0.2s ease;
    }}

    .nav-pill:hover {{
      color: #fff;
      border-color: var(--primary-light);
      background: rgba(56, 189, 248, 0.08);
    }}

    /* Interactive Map Section */
    .map-section {{
      position: relative;
      height: 740px;
      border-radius: 16px;
      overflow: hidden;
      border: 1px solid var(--border);
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7);
      margin-bottom: 48px;
      background: #020408;
    }}

    #map {{
      width: 100%;
      height: 100%;
      background: #060911;
    }}

    /* Controls Panel */
    .control-panel {{
      position: absolute;
      top: 16px;
      left: 16px;
      z-index: 1000;
      background: var(--bg-panel);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 14px 16px;
      box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.6);
      width: 380px;
      max-width: calc(100vw - 32px);
      transition: all 0.2s ease;
    }}

    .panel-header-title {{
      font-size: 14px;
      font-weight: 800;
      color: #fff;
      display: flex;
      align-items: center;
      margin-bottom: 10px;
      letter-spacing: -0.01em;
    }}

    .panel-period-tag {{
      background: rgba(56, 189, 248, 0.15);
      border: 1px solid rgba(56, 189, 248, 0.35);
      color: var(--primary-light);
      font-size: 10px;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: 5px;
      margin-left: auto;
      font-family: var(--font-mono);
    }}

    /* 3-Tier Hierarchy Selector Box */
    .hierarchy-container {{
      background: rgba(0, 0, 0, 0.45);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 8px 10px;
      margin-bottom: 10px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}

    .hierarchy-row {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .hierarchy-label {{
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      width: 48px;
      flex-shrink: 0;
      font-family: var(--font-mono);
      letter-spacing: 0.04em;
    }}

    .label-ward {{ color: #c084fc; }}
    .label-anc {{ color: #38bdf8; }}
    .label-smd {{ color: #facc15; }}

    .hierarchy-select {{
      flex: 1;
      background: #111827;
      color: #f8fafc;
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 6px;
      padding: 5px 8px;
      font-size: 12px;
      outline: none;
      cursor: pointer;
      font-family: var(--font-sans);
    }}

    .hierarchy-select:focus {{
      border-color: var(--primary-light);
    }}

    .hierarchy-select:disabled {{
      background: #0b0f19;
      color: #475569;
      border-color: rgba(255, 255, 255, 0.05);
      cursor: not-allowed;
    }}

    /* Search Box */
    .search-box {{
      margin-bottom: 10px;
    }}

    .search-box input {{
      width: 100%;
      background: rgba(0, 0, 0, 0.45);
      border: 1px solid var(--border);
      color: #f8fafc;
      padding: 7px 10px;
      border-radius: 8px;
      font-size: 12px;
      font-family: var(--font-sans);
      outline: none;
      transition: border 0.15s ease;
    }}

    .search-box input:focus {{
      border-color: var(--primary-light);
      background: rgba(0, 0, 0, 0.7);
    }}

    /* Metric Toggle */
    .metric-toggle-group {{
      display: flex;
      background: rgba(0, 0, 0, 0.45);
      padding: 3px;
      border-radius: 8px;
      border: 1px solid var(--border);
      margin-bottom: 10px;
    }}

    .metric-btn {{
      flex: 1;
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 11px;
      font-weight: 700;
      padding: 6px 4px;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.15s ease;
      text-align: center;
    }}

    .metric-btn.active {{
      background: var(--primary);
      color: #fff;
      box-shadow: 0 2px 8px rgba(2, 132, 199, 0.4);
    }}

    /* Layer Controls */
    .layer-controls {{
      display: flex;
      flex-direction: column;
      gap: 5px;
      margin-bottom: 10px;
      background: rgba(0, 0, 0, 0.25);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 8px 10px;
    }}

    .checkbox-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 11.5px;
      color: #cbd5e1;
      cursor: pointer;
      user-select: none;
    }}

    .checkbox-row input {{
      cursor: pointer;
      accent-color: var(--primary-light);
    }}

    .badge-route {{
      display: inline-block;
      width: 9px;
      height: 9px;
      border-radius: 3px;
      margin-right: 5px;
      vertical-align: middle;
    }}

    /* Quick Buttons */
    .quick-buttons {{
      display: flex;
      gap: 6px;
    }}

    .action-btn {{
      flex: 1;
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid var(--border);
      color: #e2e8f0;
      padding: 5px 8px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 600;
      cursor: pointer;
      text-align: center;
      transition: all 0.15s ease;
    }}

    .action-btn:hover {{
      background: rgba(255, 255, 255, 0.16);
      color: #fff;
    }}

    /* Right Inspector Panel */
    .inspector-panel {{
      position: absolute;
      top: 16px;
      right: 16px;
      z-index: 1000;
      width: 320px;
      background: var(--bg-panel);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 14px 16px;
      box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.6);
      transition: all 0.2s ease;
    }}

    .breadcrumb-nav {{
      display: flex;
      align-items: center;
      gap: 5px;
      font-size: 11px;
      margin-bottom: 8px;
      flex-wrap: wrap;
    }}

    .breadcrumb-item {{
      color: var(--primary-light);
      cursor: pointer;
      font-weight: 600;
    }}

    .breadcrumb-item:hover {{
      text-decoration: underline;
    }}

    .breadcrumb-item.active {{
      color: #f8fafc;
      cursor: default;
      text-decoration: none;
    }}

    .inspector-header {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      margin-bottom: 2px;
    }}

    .inspector-title {{
      font-size: 20px;
      font-weight: 800;
      color: #fff;
      letter-spacing: -0.01em;
    }}

    .inspector-anc-tag {{
      font-size: 11px;
      font-family: var(--font-mono);
      background: rgba(56, 189, 248, 0.15);
      color: var(--primary-light);
      border: 1px solid rgba(56, 189, 248, 0.3);
      padding: 2px 6px;
      border-radius: 4px;
    }}

    .rep-name {{
      font-size: 11px;
      color: var(--text-muted);
      margin-bottom: 12px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .stat-grid {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 8px;
      margin-bottom: 12px;
    }}

    .stat-card {{
      background: rgba(0, 0, 0, 0.45);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 8px 10px;
    }}

    .stat-card.featured {{
      grid-column: span 2;
      background: rgba(2, 132, 199, 0.15);
      border-color: rgba(56, 189, 248, 0.35);
    }}

    .stat-value {{
      font-size: 18px;
      font-weight: 800;
      font-family: var(--font-mono);
      color: #fff;
      line-height: 1.1;
      margin-bottom: 2px;
    }}

    .stat-card.featured .stat-value {{
      font-size: 22px;
      color: #fef08a;
    }}

    .stat-label {{
      font-size: 9px;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}

    .rank-bar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 6px 8px;
      background: rgba(0, 0, 0, 0.35);
      border-radius: 6px;
      font-size: 10px;
      color: #cbd5e1;
      margin-bottom: 8px;
      border: 1px solid rgba(255, 255, 255, 0.08);
    }}

    .route-info-box {{
      background: rgba(30, 41, 59, 0.7);
      border-radius: 6px;
      padding: 8px;
      font-size: 10px;
      color: #cbd5e1;
      line-height: 1.4;
      border: 1px solid var(--border);
    }}

    .inspector-footnote {{
      margin-top: 8px;
      padding-top: 6px;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      font-size: 10px;
      color: #94a3b8;
      font-family: var(--font-mono);
      text-align: center;
    }}

    /* Map Legend */
    .legend-panel {{
      position: absolute;
      bottom: 20px;
      right: 16px;
      z-index: 1000;
      background: var(--bg-panel);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 10px 12px;
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
    }}

    .legend-title {{
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      margin-bottom: 6px;
    }}

    .legend-scale {{
      display: flex;
      flex-direction: column;
      gap: 3px;
    }}

    .legend-row {{
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 10px;
      font-family: var(--font-mono);
    }}

    .legend-color {{
      width: 14px;
      height: 10px;
      border-radius: 2px;
      border: 1px solid rgba(255, 255, 255, 0.2);
    }}

    /* Map Standalone Footnote Bar */
    .map-footnote-bar {{
      position: absolute;
      bottom: 16px;
      left: 16px;
      z-index: 1000;
      background: var(--bg-panel);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 6px 12px;
      font-size: 10.5px;
      font-family: var(--font-mono);
      color: #94a3b8;
      box-shadow: 0 4px 14px rgba(0, 0, 0, 0.5);
      display: flex;
      gap: 14px;
      align-items: center;
      flex-wrap: wrap;
      pointer-events: none;
    }}

    /* ULTRA HIGH-CONTRAST TOOLTIP STYLING (WCAG AAA) */
    .leaflet-tooltip.custom-tooltip {{
      background: #090d16 !important;
      color: #f8fafc !important;
      border: 1.5px solid #38bdf8 !important;
      border-radius: 10px !important;
      padding: 10px 14px !important;
      box-shadow: 0 16px 36px rgba(0, 0, 0, 0.85), 0 0 0 1px rgba(56, 189, 248, 0.3) !important;
      font-family: var(--font-sans) !important;
      font-size: 12px !important;
      pointer-events: none !important;
      white-space: nowrap !important;
      transition: none !important;
    }}

    .leaflet-tooltip-top:before,
    .leaflet-tooltip-bottom:before,
    .leaflet-tooltip-left:before,
    .leaflet-tooltip-right:before {{
      display: none !important;
    }}

    /* Analysis Report Section */
    .analysis-report-section {{
      margin-top: 32px;
      padding-top: 32px;
      border-top: 1px solid var(--border);
    }}

    .analysis-header-banner {{
      background: linear-gradient(135deg, rgba(13, 19, 34, 0.95), rgba(7, 10, 18, 0.95));
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 32px;
      margin-bottom: 32px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 20px;
    }}

    .analysis-title-group h2 {{
      font-size: 26px;
      font-weight: 800;
      color: #ffffff;
      letter-spacing: -0.02em;
      margin-bottom: 8px;
    }}

    .analysis-title-group p {{
      font-size: 14.5px;
      color: var(--text-muted);
      max-width: 860px;
      line-height: 1.6;
    }}

    .pill-analysis {{
      display: inline-block;
      font-size: 11px;
      font-weight: 700;
      color: #a855f7;
      background: rgba(168, 85, 247, 0.15);
      border: 1px solid rgba(168, 85, 247, 0.35);
      padding: 3px 10px;
      border-radius: 6px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-family: var(--font-mono);
      margin-bottom: 12px;
    }}

    /* KPI Analysis Grid (6 Cards) */
    .kpi-analysis-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin-bottom: 32px;
    }}

    .kpi-analysis-card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 18px 20px;
      position: relative;
    }}

    .kpi-analysis-card.featured {{
      border-color: rgba(254, 240, 138, 0.4);
      background: rgba(254, 240, 138, 0.03);
    }}

    .kpi-analysis-lbl {{
      font-size: 11px;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 6px;
    }}

    .kpi-analysis-val {{
      font-size: 28px;
      font-weight: 800;
      font-family: var(--font-mono);
      color: #fff;
      line-height: 1.1;
      margin-bottom: 4px;
    }}

    .kpi-analysis-sub {{
      font-size: 11.5px;
      color: #94a3b8;
      line-height: 1.4;
    }}

    /* Analysis Report Cards (Grid) */
    .report-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
      gap: 24px;
      margin-bottom: 48px;
    }}

    .report-card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 26px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      position: relative;
      overflow: hidden;
    }}

    .report-card::before {{
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      width: 4px;
      height: 100%;
      background: var(--primary-light);
    }}

    .report-header {{
      display: flex;
      align-items: center;
      margin-bottom: 14px;
    }}

    .report-title {{
      font-size: 17px;
      font-weight: 700;
      color: #ffffff;
      letter-spacing: -0.01em;
    }}

    .report-content {{
      font-size: 13.5px;
      color: #cbd5e1;
      line-height: 1.65;
    }}

    .report-content p {{
      margin-bottom: 12px;
    }}

    .report-content p:last-child {{
      margin-bottom: 0;
    }}

    .report-tag-list {{
      display: flex;
      gap: 8px;
      margin-top: 16px;
      flex-wrap: wrap;
    }}

    .report-tag {{
      font-size: 11px;
      font-family: var(--font-mono);
      padding: 3px 8px;
      border-radius: 5px;
      background: rgba(255, 255, 255, 0.07);
      color: var(--primary-light);
      border: 1px solid rgba(255, 255, 255, 0.1);
    }}

    /* Section Headings */
    .section-title-wrap {{
      margin-bottom: 24px;
    }}

    .section-eyebrow {{
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--primary-light);
      font-family: var(--font-mono);
      display: block;
      margin-bottom: 4px;
    }}

    .section-title {{
      font-size: 24px;
      font-weight: 800;
      letter-spacing: -0.01em;
      color: #ffffff;
    }}

    .section-desc {{
      font-size: 13.5px;
      color: var(--text-muted);
      margin-top: 4px;
    }}

    /* 4-Chart Grid (2x2) */
    .charts-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
      margin-bottom: 48px;
    }}

    .chart-card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 24px;
      position: relative;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}

    .chart-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 16px;
    }}

    .chart-title {{
      font-size: 16px;
      font-weight: 700;
      color: #fff;
    }}

    .chart-subtitle {{
      font-size: 12px;
      color: var(--text-muted);
      margin-top: 2px;
    }}

    .chart-canvas-wrap {{
      position: relative;
      height: 320px;
      width: 100%;
    }}

    .chart-footnote {{
      margin-top: 14px;
      padding-top: 10px;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      font-size: 11px;
      color: #94a3b8;
      font-family: var(--font-mono);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 6px;
    }}

    /* Table */
    .table-container {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 16px;
      overflow-x: auto;
      margin-bottom: 48px;
    }}

    .data-table {{
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 13px;
    }}

    .data-table th {{
      background: rgba(0, 0, 0, 0.35);
      color: var(--text-muted);
      font-weight: 700;
      text-transform: uppercase;
      font-size: 11px;
      letter-spacing: 0.05em;
      padding: 14px 18px;
      border-bottom: 1px solid var(--border);
      white-space: nowrap;
    }}

    .data-table td {{
      padding: 14px 18px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
      color: #e2e8f0;
      white-space: nowrap;
    }}

    .data-table tr:last-child td {{
      border-bottom: none;
    }}

    .data-table tr:hover td {{
      background: rgba(255, 255, 255, 0.02);
    }}

    .table-btn {{
      background: rgba(56, 189, 248, 0.12);
      border: 1px solid rgba(56, 189, 248, 0.35);
      color: var(--primary-light);
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.15s ease;
    }}

    .table-btn:hover {{
      background: var(--primary);
      color: #fff;
    }}

    .table-footnote {{
      padding: 12px 18px;
      background: rgba(0, 0, 0, 0.35);
      border-top: 1px solid var(--border);
      font-size: 11px;
      color: #94a3b8;
      font-family: var(--font-mono);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 8px;
    }}

    /* Site Footer */
    .site-footer {{
      border-top: 1px solid var(--border);
      padding-top: 32px;
      font-size: 12px;
      color: var(--text-muted);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
    }}

    @media (max-width: 960px) {{
      .charts-grid {{
        grid-template-columns: 1fr;
      }}
      .report-grid {{
        grid-template-columns: 1fr;
      }}
      .control-panel {{
        width: calc(100% - 32px);
      }}
      .inspector-panel {{
        display: none;
      }}
      .map-footnote-bar {{
        display: none;
      }}
    }}
  </style>
</head>
<body>

  <div class="page-container">
    
    <!-- Site Header -->
    <header class="site-header">
      <div class="header-top-row">
        <div class="badge-group">
          <span class="badge badge-source">U.S. Census Bureau TIGERweb</span>
          <span class="badge badge-source">Open Data DC 311</span>
          <span class="badge badge-source">Public Aggregated Data</span>
        </div>
      </div>
      <h1 class="site-title">Washington, DC Missed Collection Analysis</h1>
      <p class="site-subtitle">
        Spatial analysis of Department of Public Works (DPW) missed trash (<code>S0441</code>) and recycling (<code>S0321</code>) collection service requests. The interactive map directly below covers the <strong>past 30 days</strong>, while the report and charts further down evaluate long-term trends across all 345 Single Member Districts (SMDs) and 8 Wards.
      </p>

      <nav class="quick-nav">
        <a href="#map-interactive" class="nav-pill">Interactive Map</a>
        <a href="#report-analysis" class="nav-pill">Analysis &amp; Findings</a>
        <a href="#visualizations" class="nav-pill">Visualizations &amp; Charts</a>
        <a href="#table-ward" class="nav-pill">Ward Comparison Matrix</a>
      </nav>
    </header>

    <!-- Interactive Map Section -->
    <section class="map-section" id="map-interactive">
      <div id="map"></div>

      <!-- Left Control & Search Panel -->
      <div class="control-panel">
        <div class="panel-header-title">
          <span>Map Controls &amp; Filters</span>
          <span class="panel-period-tag">Past 30 Days</span>
        </div>

        <!-- 3-Tier Hierarchy Selectors: Ward > ANC > SMD -->
        <div class="hierarchy-container">
          <div class="hierarchy-row">
            <span class="hierarchy-label label-ward">Ward</span>
            <select class="hierarchy-select" id="ward-select" onchange="handleWardDropdown(this.value)">
              <option value="all">All Wards (District-Wide)</option>
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
            <span class="hierarchy-label label-anc">ANC</span>
            <select class="hierarchy-select" id="anc-select" onchange="handleAncDropdown(this.value)" disabled>
              <option value="all">— Select Ward First —</option>
            </select>
          </div>

          <div class="hierarchy-row">
            <span class="hierarchy-label label-smd">SMD</span>
            <select class="hierarchy-select" id="smd-select" onchange="handleSmdDropdown(this.value)" disabled>
              <option value="all">— Select ANC First —</option>
            </select>
          </div>
        </div>

        <!-- Search Box -->
        <div class="search-box">
          <input type="text" id="smd-search" placeholder="Search SMD (e.g. 5E03), ANC (e.g. 5E), or Ward..." oninput="handleSearch(this.value)">
        </div>

        <!-- Metric Switcher -->
        <div class="metric-toggle-group">
          <button class="metric-btn active" id="btn-total" onclick="setMetric('total')">All Requests</button>
          <button class="metric-btn" id="btn-trash" onclick="setMetric('trash')">Trash Only</button>
          <button class="metric-btn" id="btn-recycling" onclick="setMetric('recycling')">Recycling Only</button>
        </div>

        <!-- Layer Toggles -->
        <div class="layer-controls">
          <label class="checkbox-row">
            <span><span class="badge-route" style="background: #f59e0b;"></span>SMD 311 Request Layer</span>
            <input type="checkbox" id="chk-smd" checked onchange="toggleSMDLayer(this.checked)">
          </label>
          <label class="checkbox-row">
            <span><span class="badge-route" style="background: #c084fc; border: 1px solid #e9d5ff;"></span>Ward Outlines (8 Wards)</span>
            <input type="checkbox" id="chk-wards" checked onchange="toggleWardLayer(this.checked)">
          </label>
          <label class="checkbox-row">
            <span><span class="badge-route" style="background: #2563eb; border: 1px dashed #60a5fa;"></span>DPW Trash Routes (140)</span>
            <input type="checkbox" id="chk-trash-routes" onchange="toggleTrashRoutes(this.checked)">
          </label>
          <label class="checkbox-row">
            <span><span class="badge-route" style="background: #059669; border: 1px dashed #34d399;"></span>DPW Recycling Routes (173)</span>
            <input type="checkbox" id="chk-recycle-routes" onchange="toggleRecycleRoutes(this.checked)">
          </label>
        </div>

        <!-- Quick Action Buttons -->
        <div class="quick-buttons">
          <button class="action-btn" onclick="resetToCitywide()">Reset Citywide</button>
          <button class="action-btn" onclick="zoomToTopHotspot()">Top District (5E03)</button>
          <button class="action-btn" onclick="selectWard(4)">Top Ward (Ward 4)</button>
        </div>
      </div>

      <!-- Right Inspector Panel -->
      <div class="inspector-panel" id="inspector">
        <div class="breadcrumb-nav" id="breadcrumb-nav">
          <span class="breadcrumb-item active" onclick="resetToCitywide()">District-Wide</span>
        </div>

        <div class="inspector-header">
          <div class="inspector-title" id="insp-smd-id">District Overview</div>
          <div class="inspector-anc-tag" id="insp-anc-tag">Washington, DC</div>
        </div>
        <div class="rep-name" id="insp-rep-name">Select or hover over any SMD tile to inspect</div>

        <div class="stat-grid">
          <div class="stat-card featured">
            <div class="stat-value" id="insp-total">3,301</div>
            <div class="stat-label" id="insp-total-label">Citywide Missed Collections</div>
          </div>
          <div class="stat-card">
            <div class="stat-value" id="insp-trash" style="color: #f87171;">2,286</div>
            <div class="stat-label">Missed Trash</div>
          </div>
          <div class="stat-card">
            <div class="stat-value" id="insp-recycling" style="color: #34d399;">1,015</div>
            <div class="stat-label">Missed Recycling</div>
          </div>
        </div>

        <div class="rank-bar" id="insp-rank-bar">
          <span>Unit: <strong>345 SMDs / 8 Wards</strong></span>
          <span>Average: <strong>9.6 requests / SMD</strong></span>
        </div>

        <div class="route-info-box" id="insp-route-note">
          Street names from Census TIGER render within the selected Ward to maintain visual clarity. Select any SMD or Ward from the controls to examine localized data.
        </div>
        <div class="inspector-footnote">
          Source: Open Data DC 311 • Past 30 Days
        </div>
      </div>

      <!-- Legend -->
      <div class="legend-panel" id="legend">
        <div class="legend-title" id="legend-title">Missed Collection Requests</div>
        <div class="legend-scale" id="legend-scale"></div>
      </div>

      <!-- Map Standalone Footnote -->
      <div class="map-footnote-bar">
        <span>Source: Open Data DC 311 (Trash S0441, Recycling S0321) &amp; U.S. Census Bureau TIGERweb</span>
        <span>Time Period: Past 30 Days (August 21 – September 20, 2026)</span>
      </div>
    </section>

    <!-- ========================================================= -->
    <!-- IN-DEPTH ANALYSIS TEXT & FINDINGS SECTION                 -->
    <!-- ========================================================= -->
    <section class="analysis-report-section" id="report-analysis">
      <div class="analysis-header-banner">
        <div class="analysis-title-group">
          <span class="pill-analysis">Long-Term Analysis</span>
          <h2>Spatial Distribution &amp; Operational Patterns</h2>
          <p>
            This analysis evaluates <strong>8,823 missed collection service requests across the last 180 days (March 24 – September 20, 2026)</strong>. Examining this period helps distinguish recurring routing patterns and persistent service variations from short-term schedule adjustments or weather delays.
          </p>
        </div>
      </div>

      <!-- Analysis KPI Banners (6 Cards) -->
      <div class="kpi-analysis-grid">
        <div class="kpi-analysis-card featured">
          <div class="kpi-analysis-lbl">Total Service Requests</div>
          <div class="kpi-analysis-val" style="color: #fef08a;">8,823</div>
          <div class="kpi-analysis-sub">Trash: 6,248 (70.8%) • Rec: 2,575 (29.2%)</div>
        </div>
        <div class="kpi-analysis-card">
          <div class="kpi-analysis-lbl">Unique Complaining Addresses</div>
          <div class="kpi-analysis-val" style="color: #38bdf8;">5,974</div>
          <div class="kpi-analysis-sub">Deduplicated; avg 1.48 requests / address</div>
        </div>
        <div class="kpi-analysis-card">
          <div class="kpi-analysis-lbl">Multi-Day Repeat Addresses</div>
          <div class="kpi-analysis-val" style="color: #f59e0b;">1,404</div>
          <div class="kpi-analysis-sub">23.5% of properties filed across &ge;2 distinct days</div>
        </div>
        <div class="kpi-analysis-card">
          <div class="kpi-analysis-lbl">Single-Incident Addresses</div>
          <div class="kpi-analysis-val" style="color: #34d399;">4,570</div>
          <div class="kpi-analysis-sub">76.5% of properties experienced an isolated miss</div>
        </div>
        <div class="kpi-analysis-card">
          <div class="kpi-analysis-lbl">Most Unique Addresses Skipped</div>
          <div class="kpi-analysis-val" style="color: #a855f7;">SMD 5E03</div>
          <div class="kpi-analysis-sub">90 distinct properties skipped (Bloomingdale)</div>
        </div>
        <div class="kpi-analysis-card">
          <div class="kpi-analysis-lbl">Most Chronic Repeat Failures</div>
          <div class="kpi-analysis-val" style="color: #fbbf24;">SMD 3/4G04</div>
          <div class="kpi-analysis-sub">30 repeat properties; max 8 distinct collection days</div>
        </div>
      </div>

      <!-- In-Depth Narrative Report Cards (6 Cards) -->
      <div class="report-grid">
        
        <!-- Narrative Card 1: Address Deduplication & Repeat Analysis (CORE REQUEST) -->
        <div class="report-card">
          <div>
            <div class="report-header">
              <h3 class="report-title">Address Recurrence: Widespread Skips vs. Unsuccessful Resolutions</h3>
            </div>
            <div class="report-content">
              <p>
                Evaluating raw ticket volumes alone can obscure whether collection failures represent broad neighborhood bypasses or chronic issues at isolated properties. Deduplicating records reveals that the District's 8,823 requests originated from <strong>5,974 unique physical addresses</strong> (an average of 1.48 requests per complaining address).
              </p>
              <p>
                Citywide, <strong>76.5% of complaining addresses (4,570 properties)</strong> filed only once during the period, representing isolated service delays. However, <strong>23.5% of complaining addresses (1,404 properties)</strong> submitted requests across <strong>two or more distinct collection days</strong>. Because 311 tickets are routinely marked "Closed" or "Resolved" following route completion, repeat filings across separate days indicate that previous closures failed to permanently correct underlying service delivery issues.
              </p>
              <p>
                This metric differentiates two distinct operational challenges:
              </p>
              <p>
                1. <strong>Widespread Neighborhood Skips</strong>: Districts like SMD 5E03 in Bloomingdale lead the city in total unique properties skipped (<strong>90 unique addresses</strong>), but exhibit a moderate repeat rate (22.2%). Collection crews periodically miss whole alley blocks simultaneously, affecting many residences at once rather than the same homes repeatedly.
              </p>
              <p>
                2. <strong>Unsuccessful Resolutions &amp; Chronic Recurrence</strong>: Conversely, districts like SMD 3/4G04 in Chevy Chase record <strong>30 multi-day repeat addresses</strong> (37.0% repeat rate), with individual properties filing up to <strong>8 separate times</strong> across different collection cycles. In pockets like SMD 5C05 (57.9% repeat rate) and SMD 1D07 (52.4%), over half of all reporting properties required repeated tickets, pointing to recurring physical alley blockages or persistent driver bypasses that standard ticket resolution protocols fail to remediate.
              </p>
            </div>
          </div>
          <div class="report-tag-list">
            <span class="report-tag" style="cursor: pointer;" onclick="selectHierarchy('5E03'); document.getElementById('map-interactive').scrollIntoView({{ behavior: 'smooth' }});">SMD 5E03: 90 Unique Addrs</span>
            <span class="report-tag" style="cursor: pointer;" onclick="selectHierarchy('3/4G04'); document.getElementById('map-interactive').scrollIntoView({{ behavior: 'smooth' }});">SMD 3/4G04: 30 Repeat Addrs</span>
            <span class="report-tag">Citywide Repeat Rate: 23.5%</span>
          </div>
        </div>

        <!-- Narrative Card 2: Ward-Level Comparison -->
        <div class="report-card">
          <div>
            <div class="report-header">
              <h3 class="report-title">Ward-Level Comparison: Cumulative Reach and Repeat Proportions</h3>
            </div>
            <div class="report-content">
              <p>
                Over the six-month evaluation period, Ward 4 recorded the highest cumulative report volume in the District, with 1,666 service requests spanning <strong>1,134 unique addresses</strong> (18.9% of the city total). Ward 4 also recorded the highest volume of multi-day repeat addresses (266 properties, 23.5% repeat rate), confirming broad-based geographic impact across northern residential corridors.
              </p>
              <p>
                Ward 7 followed with 1,406 requests across <strong>979 unique addresses</strong>. Notably, Ward 7 exhibited the lowest repeat address rate in the District at <strong>21.2%</strong> (78.8% single-incident addresses). This indicates that Ward 7's elevated summer request volume was widely distributed across hundreds of distinct single-family curbside blocks rather than concentrated re-filings from a few addresses.
              </p>
              <p>
                In contrast, Ward 3 recorded the District's highest ward-wide repeat rate at <strong>26.2%</strong> (219 of 837 complaining addresses filed on multiple distinct days), driven by recurring missed collections in Forest Hills (SMD 3F06) and Tenleytown (SMD 3E03). Ward 5 recorded 1,354 requests across 911 unique addresses (24.1% repeat rate), reflecting persistent alley navigation friction.
              </p>
            </div>
          </div>
          <div class="report-tag-list">
            <span class="report-tag" style="cursor: pointer;" onclick="selectWard(4); document.getElementById('map-interactive').scrollIntoView({{ behavior: 'smooth' }});">Ward 4: 1,134 Unique Addrs</span>
            <span class="report-tag" style="cursor: pointer;" onclick="selectWard(7); document.getElementById('map-interactive').scrollIntoView({{ behavior: 'smooth' }});">Ward 7: 979 Unique Addrs</span>
            <span class="report-tag" style="cursor: pointer;" onclick="selectWard(3); document.getElementById('map-interactive').scrollIntoView({{ behavior: 'smooth' }});">Ward 3: 26.2% Repeat Rate</span>
          </div>
        </div>

        <!-- Narrative Card 3: Upper NW & The Chevy Chase Cluster -->
        <div class="report-card">
          <div>
            <div class="report-header">
              <h3 class="report-title">Upper Northwest: Concentration in ANC 3/4G</h3>
            </div>
            <div class="report-content">
              <p>
                Single Member Districts in ANC 3/4G (Chevy Chase) and adjacent sectors of northern Ward 4 display an elevated frequency of missed collection inquiries. SMD 3/4G04 recorded 146 total requests across 81 unique addresses, with 30 properties reporting multiple missed collections across different days.
              </p>
              <p>
                Neighboring districts along the Maryland border reflect similar patterns, including SMD 3/4G02 (74 unique addresses; 18 repeat), SMD 3/4G03 (63 unique addresses; 14 repeat), SMD 4B05 (66 unique addresses; 13 repeat), and SMD 4A02 (58 unique addresses; 15 repeat). Combined, these contiguous boundary districts account for over 280 distinct skipped properties.
              </p>
              <p>
                Because these neighborhoods sit at the outer boundary of collection zones originating from central transfer stations, trucks reaching capacity or encountering early-route delays can lead to recurring route cutoffs at the periphery.
              </p>
            </div>
          </div>
          <div class="report-tag-list">
            <span class="report-tag" style="cursor: pointer;" onclick="selectHierarchy('3/4G04'); document.getElementById('map-interactive').scrollIntoView({{ behavior: 'smooth' }});">SMD 3/4G04: 146 Requests</span>
            <span class="report-tag" style="cursor: pointer;" onclick="selectHierarchy('3/4G02'); document.getElementById('map-interactive').scrollIntoView({{ behavior: 'smooth' }});">SMD 3/4G02: 74 Unique Addrs</span>
            <span class="report-tag">Perimeter Route Context</span>
          </div>
        </div>

        <!-- Narrative Card 4: Ward 5 Bloomingdale Alley Labyrinth -->
        <div class="report-card">
          <div>
            <div class="report-header">
              <h3 class="report-title">Ward 5 (SMD 5E03): Equal Distribution Between Trash and Recycling</h3>
            </div>
            <div class="report-content">
              <p>
                SMD 5E03 in Bloomingdale/Truxton Circle recorded 136 total requests across <strong>90 unique addresses</strong>, representing the highest number of distinct properties skipped in any Single Member District citywide.
              </p>
              <p>
                Unlike outer residential districts where missed trash requests predominate, SMD 5E03 recorded near-perfect parity between streams: 69 trash requests and 67 recycling requests. The area is characterized by dense rowhouse blocks and narrow 10-foot historic alley networks. 
              </p>
              <p>
                Physical access barriers—such as delivery vehicles, commercial dumpsters, and parked cars obstructing alley mouths—consistently prevent both trash and recycling collection vehicles from completing their scheduled runs, resulting in entire blocks being missed simultaneously.
              </p>
            </div>
          </div>
          <div class="report-tag-list">
            <span class="report-tag" style="cursor: pointer;" onclick="selectHierarchy('5E03'); document.getElementById('map-interactive').scrollIntoView({{ behavior: 'smooth' }});">SMD 5E03: 90 Unique Addrs</span>
            <span class="report-tag">Trash: 69 | Recycling: 67</span>
            <span class="report-tag">Alley Clearance Obstacles</span>
          </div>
        </div>

        <!-- Narrative Card 5: Ward 7 Trash Dominance -->
        <div class="report-card">
          <div>
            <div class="report-header">
              <h3 class="report-title">Ward 7: High Proportion of Trash Collection Requests</h3>
            </div>
            <div class="report-content">
              <p>
                In Ward 7, 81.9% of all service requests (1,152 of 1,406) pertained to trash collection, compared to 254 for recycling. This represents the highest trash-to-recycling ratio among all wards.
              </p>
              <p>
                In several individual districts, such as SMD 7F04 (75 total requests across 43 unique addresses), over 85% of complaints involved missed trash pickup. SMD 7F04 also recorded 15 multi-day repeat addresses (34.9% repeat rate), with one address filing complaints across 7 distinct days.
              </p>
              <p>
                Factors contributing to this distribution include a higher proportion of detached and semi-detached single-family homes with curbside municipal service, where holiday or staffing delays during early-week collection routes generate immediate resident inquiries.
              </p>
            </div>
          </div>
          <div class="report-tag-list">
            <span class="report-tag" style="cursor: pointer;" onclick="selectWard(7); document.getElementById('map-interactive').scrollIntoView({{ behavior: 'smooth' }});">Ward 7 Trash: 1,152 (81.9%)</span>
            <span class="report-tag">Recycling: 254 (18.1%)</span>
            <span class="report-tag">Curbside Service Volume</span>
          </div>
        </div>

        <!-- Narrative Card 6: Root Causes & Strategic Interventions -->
        <div class="report-card">
          <div>
            <div class="report-header">
              <h3 class="report-title">Operational Factors and Proposed Measures</h3>
            </div>
            <div class="report-content">
              <p>
                Address-level analysis and service logs identify three targeted interventions to prevent recurrent service failure:
              </p>
              <p>
                1. <strong>Supervisory Review for Repeat Addresses</strong>: Implement an automated rule in the municipal CRM that flags any address filing a second missed collection request within 30 days. Rather than closing tickets upon standard route completion, flagged addresses should require supervisory sign-off and driver confirmation.
              </p>
              <p>
                2. <strong>Verification of Closed Requests</strong>: Incorporate GPS breadcrumb traversal checks to verify that collection vehicles physically entered assigned alley segments before service requests are closed.
              </p>
              <p>
                3. <strong>Perimeter Circuit Re-Balancing &amp; Alley Sizing</strong>: Alternate start and end points for outer boundary circuits (e.g. ANC 3/4G) so perimeter blocks are not chronically subject to end-of-shift capacity cutoffs. Deploy smaller-profile collection trucks in narrow rowhouse corridors (Bloomingdale, Capitol Hill, Shaw) to prevent access delays caused by parked cars and construction dumpsters.
              </p>
            </div>
          </div>
          <div class="report-tag-list">
            <span class="report-tag">Repeat Complaint Triggers</span>
            <span class="report-tag">GPS Traversal Confirmation</span>
            <span class="report-tag">Vehicle Sizing for Alleys</span>
          </div>
        </div>

      </div>

      <!-- Visualizations Grid (4 Charts in 2x2 Grid) -->
      <div class="section-title-wrap" id="visualizations">
        <span class="section-eyebrow">Data Visualizations</span>
        <h3 class="section-title" style="font-size: 22px;">Cumulative Report Visualizations</h3>
        <p class="section-desc">Visual summary of cumulative 311 missed collection service requests, unique property reach, and address recurrence across Wards and top reporting districts.</p>
      </div>

      <div class="charts-grid">
        <!-- Chart 1: Ward Stacked Bar (Trash vs Rec) -->
        <div class="chart-card">
          <div class="chart-header">
            <div>
              <div class="chart-title">Missed Collections by Ward</div>
              <div class="chart-subtitle">Cumulative service requests across all 8 Wards • Past 180 Days</div>
            </div>
          </div>
          <div class="chart-canvas-wrap">
            <canvas id="ward180Chart"></canvas>
          </div>
          <div class="chart-footnote">
            <span>Source: Open Data DC 311 (Trash S0441 &amp; Recycling S0321)</span>
            <span>Time Period: Past 180 Days (March 24 – September 20, 2026)</span>
          </div>
        </div>

        <!-- Chart 2: Address Recurrence by Ward (Single vs Multi-Day Repeat) -->
        <div class="chart-card">
          <div class="chart-header">
            <div>
              <div class="chart-title">Address Recurrence Profile by Ward</div>
              <div class="chart-subtitle">Single-incident vs. multi-day repeat complaining properties • Past 180 Days</div>
            </div>
          </div>
          <div class="chart-canvas-wrap">
            <canvas id="wardRepeatChart"></canvas>
          </div>
          <div class="chart-footnote">
            <span>Source: Open Data DC 311 (Trash S0441 &amp; Recycling S0321)</span>
            <span>Time Period: Past 180 Days (March 24 – September 20, 2026)</span>
          </div>
        </div>

        <!-- Chart 3: Ratio Doughnut -->
        <div class="chart-card">
          <div class="chart-header">
            <div>
              <div class="chart-title">Collection Stream Breakdown</div>
              <div class="chart-subtitle">Trash (70.8%) vs. Recycling (29.2%) • Past 180 Days</div>
            </div>
          </div>
          <div class="chart-canvas-wrap">
            <canvas id="ratio180Chart"></canvas>
          </div>
          <div class="chart-footnote">
            <span>Source: Open Data DC 311 (Trash S0441 &amp; Recycling S0321)</span>
            <span>Time Period: Past 180 Days (March 24 – September 20, 2026)</span>
          </div>
        </div>

        <!-- Chart 4: Top 10 SMD Hotspots (Single vs Repeat Addresses) -->
        <div class="chart-card">
          <div class="chart-header">
            <div>
              <div class="chart-title">Top 10 Reporting SMDs: Address Recurrence</div>
              <div class="chart-subtitle">Unique properties vs. multi-day repeat complaints in top districts • Past 180 Days</div>
            </div>
          </div>
          <div class="chart-canvas-wrap">
            <canvas id="hotspot180Chart"></canvas>
          </div>
          <div class="chart-footnote">
            <span>Source: Open Data DC 311 (Trash S0441 &amp; Recycling S0321)</span>
            <span>Time Period: Past 180 Days (March 24 – September 20, 2026)</span>
          </div>
        </div>
      </div>

      <!-- Ward Comparison Table -->
      <div class="section-title-wrap" id="table-ward">
        <span class="section-eyebrow">Summary Table</span>
        <h3 class="section-title" style="font-size: 22px;">Ward-by-Ward Performance Summary</h3>
        <p class="section-desc">Cumulative service request totals, unique address reach, and repeat recurrence across all eight wards • Past 180 Days. Click "Focus on Map" to navigate the interactive viewer above.</p>
      </div>

      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>Ward</th>
              <th>Councilmember</th>
              <th>Total Requests</th>
              <th>Unique Addrs</th>
              <th>Repeat Addrs (&ge;2 Days)</th>
              <th>Repeat %</th>
              <th>Trash (S0441)</th>
              <th>Recycling (S0321)</th>
              <th>Trash %</th>
              <th>Top SMD (Addrs / Reqs)</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>'''

# Generate table rows dynamically
for w in range(1, 9):
    st = ward_180d_stats[str(w)]
    smds_in_ward = [s for s in smds_180d if s['ward'] == w]
    top_smd = sorted(smds_in_ward, key=lambda x: x['total'], reverse=True)[0]
    trash_pct = (st["trash"] / st["total"] * 100) if st["total"] > 0 else 0
    council = ward_council.get(w, "")
    html_page += f'''
            <tr>
              <td><strong style="color: #c084fc;">Ward {w}</strong></td>
              <td>{council}</td>
              <td><strong style="font-family: var(--font-mono); color: #fff;">{st['total']:,}</strong></td>
              <td style="color: #38bdf8; font-family: var(--font-mono); font-weight: 700;">{st['unique_addresses']:,}</td>
              <td style="color: #f59e0b; font-family: var(--font-mono); font-weight: 700;">{st['repeat_addresses']:,}</td>
              <td style="font-family: var(--font-mono);">{st['repeat_rate']:.1f}%</td>
              <td style="color: #f87171; font-family: var(--font-mono);">{st['trash']:,}</td>
              <td style="color: #34d399; font-family: var(--font-mono);">{st['recycling']:,}</td>
              <td>{trash_pct:.1f}%</td>
              <td><span class="report-tag" style="cursor: pointer;" onclick="selectHierarchy('{top_smd['smd_id']}'); document.getElementById('map-interactive').scrollIntoView({{ behavior: 'smooth' }});">SMD {top_smd['smd_id']} ({top_smd['unique_addrs']} addrs / {top_smd['total']} reqs)</span></td>
              <td><button class="table-btn" onclick="selectWard({w}); document.getElementById('map-interactive').scrollIntoView({{ behavior: 'smooth' }});">Focus on Map</button></td>
            </tr>'''

html_page += f'''
          </tbody>
        </table>
        <div class="table-footnote">
          <span>Source: Open Data DC 311 (Trash S0441 &amp; Recycling S0321)</span>
          <span>Time Period: Past 180 Days (March 24 – September 20, 2026)</span>
        </div>
      </div>
    </section>

    <!-- Site Footer -->
    <footer class="site-footer">
      <div>
        <strong>DC Missed Collection Analysis &amp; Open Map</strong> • Public community and ANC resource.
      </div>
      <div>
        Data: Open Data DC (311 Requests) • Basemap: U.S. Census Bureau TIGERweb (Transportation &amp; Hydrography)
      </div>
    </footer>

  </div>

  <!-- Leaflet JS -->
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

  <script>
    const MAP_DATA = {json_str};

    // State (Map uses 30-day data as specified)
    let selectedWardNum = null;   // null = All Wards, or 1..8
    let selectedAncId = null;     // null or e.g. '5E'
    let selectedSmdId = null;     // null or e.g. '5E03'
    let currentMetric = 'total';  // 'total' | 'trash' | 'recycling'

    // Initialize Map with clean neutral canvas
    const map = L.map('map', {{
      center: [38.9072, -77.01],
      zoom: 12,
      zoomControl: false,
      minZoom: 11,
      maxZoom: 18,
      scrollWheelZoom: true
    }});

    L.control.zoom({{ position: 'bottomright' }}).addTo(map);

    // Layer Panes
    map.createPane('tigerStreetPane');
    map.getPane('tigerStreetPane').style.zIndex = 220;

    map.createPane('maskPane');
    map.getPane('maskPane').style.zIndex = 260;

    map.createPane('hydroPane');
    map.getPane('hydroPane').style.zIndex = 280;

    map.createPane('wardPane');
    map.getPane('wardPane').style.zIndex = 320;

    map.createPane('routePane');
    map.getPane('routePane').style.zIndex = 340;

    map.createPane('smdPane');
    map.getPane('smdPane').style.zIndex = 400;

    // Basemap Layer 1: U.S. Census TIGERweb Transportation
    L.tileLayer('https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Transportation/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
      pane: 'tigerStreetPane',
      maxZoom: 18,
      opacity: 0.95,
      attribution: '&copy; U.S. Census Bureau TIGERweb'
    }}).addTo(map);

    // Basemap Layer 2: Hydrography
    L.tileLayer('https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Hydro/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
      pane: 'hydroPane',
      maxZoom: 18,
      opacity: 0.75,
      interactive: false
    }}).addTo(map);

    // Variables for layers
    let smdLayer = null;
    let wardLayer = null;
    let trashRoutesLayer = null;
    let recycleRoutesLayer = null;
    let wardMaskLayer = null;

    // Inverted Ward Mask for Scoping Street Labels Strictly to Active Ward
    function updateWardMask() {{
      if (wardMaskLayer) {{
        map.removeLayer(wardMaskLayer);
        wardMaskLayer = null;
      }}

      if (!selectedWardNum) {{
        const fullWorld = [
          [-85, -180],
          [-85, 180],
          [85, 180],
          [85, -180]
        ];
        wardMaskLayer = L.polygon(fullWorld, {{
          pane: 'maskPane',
          fillColor: '#070a13',
          fillOpacity: 0.94,
          stroke: false,
          interactive: false
        }}).addTo(map);
        return;
      }}

      const wardFeat = MAP_DATA.wards.features.find(f => f.properties.ward === selectedWardNum);
      if (!wardFeat) return;

      const outerRing = [
        [-85, -180],
        [-85, 180],
        [85, 180],
        [85, -180]
      ];

      function convertCoords(coords) {{
        return coords.map(pt => [pt[1], pt[0]]);
      }}

      let polygonCoords = [outerRing];
      const g = wardFeat.geometry;
      if (g.type === 'Polygon') {{
        for (const ring of g.coordinates) {{
          polygonCoords.push(convertCoords(ring));
        }}
      }} else if (g.type === 'MultiPolygon') {{
        for (const poly of g.coordinates) {{
          for (const ring of poly) {{
            polygonCoords.push(convertCoords(ring));
          }}
        }}
      }}

      wardMaskLayer = L.polygon(polygonCoords, {{
        pane: 'maskPane',
        fillColor: '#070a13',
        fillOpacity: 0.94,
        stroke: false,
        interactive: false
      }}).addTo(map);
    }}

    // Metric thresholds
    const THRESHOLDS = {{
      total:     [0, 3, 7, 12, 18, 26, 36],
      trash:     [0, 2, 5,  9, 14, 20, 28],
      recycling: [0, 1, 3,  6,  9, 13, 18]
    }};

    const PALETTES = {{
      total:     ['#1e293b', '#3b82f6', '#0284c7', '#eab308', '#f97316', '#ef4444', '#b91c1c'],
      trash:     ['#1e293b', '#fb923c', '#f97316', '#ea580c', '#dc2626', '#b91c1c', '#7f1d1d'],
      recycling: ['#1e293b', '#34d399', '#10b981', '#059669', '#0d9488', '#0f766e', '#115e59']
    }};

    function getColor(val, metric) {{
      if (val === 0) return '#1e293b';
      const th = THRESHOLDS[metric];
      const pal = PALETTES[metric];
      for (let i = th.length - 1; i >= 0; i--) {{
        if (val >= th[i]) return pal[i];
      }}
      return pal[0];
    }}

    function smdStyle(feature) {{
      const p = feature.properties;
      const val = p[currentMetric] || 0;
      const isSelectedSMD = selectedSmdId === p.smd_id;
      const isInSelectedAnc = selectedAncId === p.anc_id;
      const isInSelectedWard = selectedWardNum === p.ward;

      if (selectedSmdId) {{
        if (isSelectedSMD) {{
          return {{
            fillColor: getColor(val, currentMetric),
            weight: 3.5,
            opacity: 1,
            color: '#facc15',
            fillOpacity: 0.92
          }};
        }} else if (isInSelectedWard) {{
          return {{
            fillColor: getColor(val, currentMetric),
            weight: 0.8,
            opacity: 0.6,
            color: '#38bdf8',
            fillOpacity: 0.35
          }};
        }} else {{
          return {{
            fillColor: getColor(val, currentMetric),
            weight: 0.5,
            opacity: 0.20,
            color: 'rgba(100, 116, 139, 0.2)',
            fillOpacity: 0.08
          }};
        }}
      }}

      if (selectedAncId) {{
        if (isInSelectedAnc) {{
          return {{
            fillColor: getColor(val, currentMetric),
            weight: 2.2,
            opacity: 0.95,
            color: '#0284c7',
            fillOpacity: val === 0 ? 0.35 : 0.78
          }};
        }} else {{
          return {{
            fillColor: getColor(val, currentMetric),
            weight: 0.5,
            opacity: 0.25,
            color: 'rgba(100, 116, 139, 0.25)',
            fillOpacity: 0.10
          }};
        }}
      }}

      if (selectedWardNum) {{
        if (isInSelectedWard) {{
          return {{
            fillColor: getColor(val, currentMetric),
            weight: 1.2,
            opacity: 0.95,
            color: 'rgba(15, 23, 42, 0.65)',
            fillOpacity: val === 0 ? 0.20 : 0.68
          }};
        }} else {{
          return {{
            fillColor: getColor(val, currentMetric),
            weight: 0.6,
            opacity: 0.35,
            color: 'rgba(100, 116, 139, 0.3)',
            fillOpacity: 0.12
          }};
        }}
      }}

      return {{
        fillColor: getColor(val, currentMetric),
        weight: 0.8,
        opacity: 0.85,
        color: 'rgba(15, 23, 42, 0.6)',
        fillOpacity: val === 0 ? 0.25 : 0.65
      }};
    }}

    function wardStyle(feature) {{
      const isSelected = selectedWardNum === feature.properties.ward;
      return {{
        color: isSelected ? '#a855f7' : '#9333ea',
        weight: isSelected ? 3.5 : 1.8,
        dashArray: isSelected ? null : '4, 6',
        fill: false,
        interactive: false
      }};
    }}

    // Dropdown Synchronization
    function updateDropdowns(wardVal, ancVal, smdVal) {{
      const wardSelect = document.getElementById('ward-select');
      const ancSelect = document.getElementById('anc-select');
      const smdSelect = document.getElementById('smd-select');

      wardSelect.value = wardVal ? String(wardVal) : 'all';

      if (!wardVal) {{
        ancSelect.disabled = true;
        ancSelect.innerHTML = '<option value="all">— Select Ward First —</option>';
        smdSelect.disabled = true;
        smdSelect.innerHTML = '<option value="all">— Select ANC First —</option>';
        return;
      }}

      const ancsInWard = Array.from(new Set(
        MAP_DATA.smds.features
          .filter(f => f.properties.ward === parseInt(wardVal))
          .map(f => f.properties.anc_id)
      )).sort();

      let ancHtml = `<option value="all">All ANCs in Ward ${{wardVal}}</option>`;
      for (const anc of ancsInWard) {{
        ancHtml += `<option value="${{anc}}">ANC ${{anc}}</option>`;
      }}
      ancSelect.innerHTML = ancHtml;
      ancSelect.disabled = false;
      ancSelect.value = ancVal || 'all';

      if (!ancVal || ancVal === 'all') {{
        smdSelect.disabled = true;
        smdSelect.innerHTML = '<option value="all">— Select ANC First —</option>';
        return;
      }}

      const smdsInAnc = MAP_DATA.smds.features
        .filter(f => f.properties.anc_id === ancVal && (!wardVal || f.properties.ward === parseInt(wardVal)))
        .sort((a, b) => a.properties.smd_id.localeCompare(b.properties.smd_id));

      let smdHtml = `<option value="all">All SMDs in ANC ${{ancVal}}</option>`;
      for (const smd of smdsInAnc) {{
        const p = smd.properties;
        smdHtml += `<option value="${{p.smd_id}}">SMD ${{p.smd_id}} (${{p.total}} requests)</option>`;
      }}
      smdSelect.innerHTML = smdHtml;
      smdSelect.disabled = false;
      smdSelect.value = smdVal || 'all';
    }}

    function handleWardDropdown(val) {{
      if (val === 'all') {{
        resetToCitywide();
      }} else {{
        selectWard(parseInt(val));
      }}
    }}

    function handleAncDropdown(val) {{
      if (val === 'all') {{
        if (selectedWardNum) {{
          selectWard(selectedWardNum);
        }} else {{
          resetToCitywide();
        }}
      }} else {{
        selectANC(val);
      }}
    }}

    function handleSmdDropdown(val) {{
      if (val === 'all') {{
        if (selectedAncId) {{
          selectANC(selectedAncId);
        }} else if (selectedWardNum) {{
          selectWard(selectedWardNum);
        }} else {{
          resetToCitywide();
        }}
      }} else {{
        selectHierarchy(val);
      }}
    }}

    function selectHierarchy(smdId) {{
      hideSmdTooltip();
      let targetLayer = null;
      smdLayer.eachLayer(function(l) {{
        if (l.feature.properties.smd_id === smdId) {{
          targetLayer = l;
        }}
      }});
      if (!targetLayer) return;

      const props = targetLayer.feature.properties;
      selectedSmdId = props.smd_id;
      selectedAncId = props.anc_id;
      selectedWardNum = props.ward;

      updateDropdowns(selectedWardNum, selectedAncId, selectedSmdId);

      updateWardMask();
      smdLayer.setStyle(smdStyle);
      if (wardLayer) wardLayer.setStyle(wardStyle);

      targetLayer.bringToFront();
      map.fitBounds(targetLayer.getBounds(), {{ maxZoom: 16, padding: [60, 60] }});

      updateInspectorSMD(props);
      updateBreadcrumbs();
    }}

    function selectWard(wNum) {{
      hideSmdTooltip();
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
      hideSmdTooltip();
      selectedAncId = ancId;
      selectedSmdId = null;

      const smdInAnc = MAP_DATA.smds.features.find(f => f.properties.anc_id === ancId);
      if (smdInAnc) {{
        selectedWardNum = smdInAnc.properties.ward;
      }}

      updateDropdowns(selectedWardNum, selectedAncId, null);

      updateWardMask();
      smdLayer.setStyle(smdStyle);
      if (wardLayer) wardLayer.setStyle(wardStyle);

      const matchingSMDs = MAP_DATA.smds.features.filter(f => f.properties.anc_id === ancId);
      if (matchingSMDs.length > 0) {{
        const group = L.featureGroup(matchingSMDs.map(f => L.geoJSON(f)));
        map.fitBounds(group.getBounds(), {{ padding: [40, 40] }});
      }}

      updateInspectorANC(ancId);
      updateBreadcrumbs();
    }}

    function resetToCitywide() {{
      hideSmdTooltip();
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

    function updateBreadcrumbs() {{
      const nav = document.getElementById('breadcrumb-nav');
      let html = `<span class="breadcrumb-item ${{!selectedWardNum ? 'active' : ''}}" onclick="resetToCitywide()">District-Wide</span>`;
      
      if (selectedWardNum) {{
        html += ` <span style="color: #64748b;">&rsaquo;</span> `;
        html += `<span class="breadcrumb-item ${{!selectedAncId ? 'active' : ''}}" onclick="selectWard(${{selectedWardNum}})">Ward ${{selectedWardNum}}</span>`;
      }}
      if (selectedAncId) {{
        html += ` <span style="color: #64748b;">&rsaquo;</span> `;
        html += `<span class="breadcrumb-item ${{!selectedSmdId ? 'active' : ''}}" onclick="selectANC('${{selectedAncId}}')">ANC ${{selectedAncId}}</span>`;
      }}
      if (selectedSmdId) {{
        html += ` <span style="color: #64748b;">&rsaquo;</span> `;
        html += `<span class="breadcrumb-item active">SMD ${{selectedSmdId}}</span>`;
      }}
      nav.innerHTML = html;
    }}

    function updateInspectorSMD(p) {{
      document.getElementById('insp-smd-id').innerText = `SMD ${{p.smd_id}}`;
      document.getElementById('insp-anc-tag').innerText = `Ward ${{p.ward}} • ANC ${{p.anc_id}}`;
      document.getElementById('insp-rep-name').innerText = p.rep_name ? `Commissioner ${{p.rep_name}}` : 'Single Member District';

      document.getElementById('insp-total').innerText = p.total;
      document.getElementById('insp-total-label').innerText = 'Missed Collections (30d)';
      document.getElementById('insp-trash').innerText = p.trash;
      document.getElementById('insp-recycling').innerText = p.recycling;

      let wardShare = p.ward_share_pct;
      if (wardShare === undefined || wardShare === null) {{
        const wf = MAP_DATA && MAP_DATA.wards && MAP_DATA.wards.features
          ? MAP_DATA.wards.features.find(f => String(f.properties.ward) === String(p.ward))
          : null;
        const wardTotal = wf && wf.properties ? wf.properties.total : 0;
        wardShare = (wardTotal > 0 && p.total) ? ((p.total / wardTotal) * 100).toFixed(1) : '0.0';
      }}

      const rankEl = document.getElementById('insp-rank-bar');
      rankEl.innerHTML = `
        <span>City Rank: <strong style="color: #fff;">#${{p.city_rank}}</strong> of 345</span>
        <span>Share of Ward: <strong>${{wardShare}}%</strong></span>
      `;

      const note = document.getElementById('insp-route-note');
      note.innerHTML = `
        TIGER basemap street names are rendered strictly within Ward ${{p.ward}} for visual focus.
      `;
    }}

    function updateInspectorANC(ancId) {{
      const smdsInAnc = MAP_DATA.smds.features.filter(f => f.properties.anc_id === ancId);
      const total = smdsInAnc.reduce((sum, f) => sum + f.properties.total, 0);
      const trash = smdsInAnc.reduce((sum, f) => sum + f.properties.trash, 0);
      const rec = smdsInAnc.reduce((sum, f) => sum + f.properties.recycling, 0);
      const ward = smdsInAnc[0]?.properties.ward || '';

      document.getElementById('insp-smd-id').innerText = `ANC ${{ancId}}`;
      document.getElementById('insp-anc-tag').innerText = `Ward ${{ward}} • ${{smdsInAnc.length}} SMDs`;
      document.getElementById('insp-rep-name').innerText = `Advisory Neighborhood Commission ${{ancId}}`;

      document.getElementById('insp-total').innerText = total;
      document.getElementById('insp-total-label').innerText = 'ANC Total Requests (30d)';
      document.getElementById('insp-trash').innerText = trash;
      document.getElementById('insp-recycling').innerText = rec;

      const rankEl = document.getElementById('insp-rank-bar');
      rankEl.innerHTML = `
        <span>Scope: <strong>ANC ${{ancId}}</strong></span>
        <span>Avg/SMD: <strong>${{(total / smdsInAnc.length).toFixed(1)}}</strong></span>
      `;

      const note = document.getElementById('insp-route-note');
      note.innerHTML = `Streets for Ward ${{ward}} are rendered on the TIGER basemap. Select an individual SMD tile to inspect representative data.`;
    }}

    function updateInspectorWard(p) {{
      document.getElementById('insp-smd-id').innerText = `Ward ${{p.ward}}`;
      document.getElementById('insp-anc-tag').innerText = `${{p.smd_count}} SMDs`;
      document.getElementById('insp-rep-name').innerText = `Councilmember ${{p.councilmember || p.rep_name || ''}}`;

      document.getElementById('insp-total').innerText = p.total;
      document.getElementById('insp-total-label').innerText = 'Ward Total Requests (30d)';
      document.getElementById('insp-trash').innerText = p.trash;
      document.getElementById('insp-recycling').innerText = p.recycling;

      const shareOfCity = ((p.total / 3301) * 100).toFixed(1);
      const rankEl = document.getElementById('insp-rank-bar');
      rankEl.innerHTML = `
        <span>Top SMD: <strong style="color: #facc15;">${{p.top_smd_id}}</strong> (${{p.top_smd_total}} reqs)</span>
        <span>Share of City: <strong>${{shareOfCity}}%</strong></span>
      `;

      const note = document.getElementById('insp-route-note');
      note.innerHTML = `TIGER street names are rendered strictly within Ward ${{p.ward}}'s boundary. Select any individual SMD within Ward ${{p.ward}} to focus.`;
    }}

    function updateInspectorCitywide() {{
      document.getElementById('insp-smd-id').innerText = 'District Overview';
      document.getElementById('insp-anc-tag').innerText = 'Washington, DC';
      document.getElementById('insp-rep-name').innerText = 'Select or hover over any SMD tile to inspect';

      document.getElementById('insp-total').innerText = '3,301';
      document.getElementById('insp-total-label').innerText = 'Citywide Missed Collections (30d)';
      document.getElementById('insp-trash').innerText = '2,286';
      document.getElementById('insp-recycling').innerText = '1,015';

      const rankEl = document.getElementById('insp-rank-bar');
      rankEl.innerHTML = `
        <span>Unit: <strong>345 SMDs / 8 Wards</strong></span>
        <span>Average: <strong>9.6 requests / SMD</strong></span>
      `;

      const note = document.getElementById('insp-route-note');
      note.innerHTML = `Street names are hidden in district-wide view to maintain visual clarity. Select any Ward or SMD to display streets in that area.`;
    }}

    // Single shared tooltip instance to prevent trailing / duplicate tooltips ("solitaire" effect)
    const smdTooltip = L.tooltip({{
      className: 'custom-tooltip',
      direction: 'top',
      offset: [0, -10],
      opacity: 1
    }});

    let activeHoverLayer = null;

    function hideSmdTooltip() {{
      if (activeHoverLayer) {{
        if (!selectedSmdId || selectedSmdId !== activeHoverLayer.feature?.properties?.smd_id) {{
          smdLayer.resetStyle(activeHoverLayer);
        }}
        activeHoverLayer = null;
      }}
      smdTooltip.close();
    }}

    // Initialize SMD Layer with ULTRA-HIGH CONTRAST TOOLTIPS (NO EMOJIS)
    function initSMDLayer() {{
      if (smdLayer) map.removeLayer(smdLayer);
      smdLayer = L.geoJSON(MAP_DATA.smds, {{
        pane: 'smdPane',
        style: smdStyle,
        onEachFeature: function (feature, layer) {{
          const p = feature.properties;

          layer.on({{
            mouseover: function (e) {{
              if (activeHoverLayer && activeHoverLayer !== layer) {{
                if (!selectedSmdId || selectedSmdId !== activeHoverLayer.feature?.properties?.smd_id) {{
                  smdLayer.resetStyle(activeHoverLayer);
                }}
              }}
              activeHoverLayer = layer;
              layer.setStyle({{ weight: 3.5, color: '#38bdf8', fillOpacity: 0.88 }});
              if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) {{
                layer.bringToFront();
              }}

              smdTooltip.setContent(`
                <div style="font-weight: 800; font-size: 14px; color: #ffffff; letter-spacing: -0.01em; margin-bottom: 3px;">
                  SMD ${{p.smd_id}}
                </div>
                <div style="color: #38bdf8; font-size: 11px; font-weight: 700; margin-bottom: 6px;">
                  Ward ${{p.ward}} • ANC ${{p.anc_id}} • Comm. ${{p.rep_name || 'Vacant'}}
                </div>
                <div style="font-size: 12px; color: #e2e8f0; margin-bottom: 3px;">
                  Total Missed: <strong style="color: #facc15; font-size: 14px;">${{p.total}}</strong>
                  <span style="color: #94a3b8; font-size: 11px; margin-left: 4px;">
                    (Trash: <strong style="color: #f87171;">${{p.trash}}</strong>, Rec: <strong style="color: #34d399;">${{p.recycling}}</strong>)
                  </span>
                </div>
                <div style="color: #94a3b8; font-size: 11px;">
                  Citywide Rank: <strong style="color: #ffffff;">#${{p.city_rank}}</strong> of 345 in DC
                </div>
              `);
              smdTooltip.setLatLng(e.latlng);
              if (!map.hasLayer(smdTooltip)) {{
                smdTooltip.openOn(map);
              }}

              if (!selectedSmdId) {{
                updateInspectorSMD(p);
              }}
            }},
            mousemove: function (e) {{
              smdTooltip.setLatLng(e.latlng);
            }},
            mouseout: function () {{
              if (!selectedSmdId || selectedSmdId !== p.smd_id) {{
                smdLayer.resetStyle(layer);
              }}
              if (activeHoverLayer === layer) {{
                activeHoverLayer = null;
                smdTooltip.close();
              }}
              if (!selectedSmdId) {{
                if (selectedAncId) {{
                  updateInspectorANC(selectedAncId);
                }} else if (selectedWardNum) {{
                  const wf = MAP_DATA.wards.features.find(f => f.properties.ward === selectedWardNum);
                  if (wf) updateInspectorWard(wf.properties);
                }} else {{
                  updateInspectorCitywide();
                }}
              }}
            }},
            click: function (e) {{
              L.DomEvent.stopPropagation(e);
              hideSmdTooltip();
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
        style: wardStyle,
        interactive: false
      }}).addTo(map);
    }}

    function initTrashRoutesLayer() {{
      trashRoutesLayer = L.geoJSON(MAP_DATA.trash_routes, {{
        pane: 'routePane',
        style: {{
          color: '#1d4ed8',
          weight: 2.2,
          dashArray: '6, 6',
          fillColor: '#3b82f6',
          fillOpacity: 0.06
        }},
        interactive: false
      }});
    }}

    function initRecycleRoutesLayer() {{
      recycleRoutesLayer = L.geoJSON(MAP_DATA.recycle_routes, {{
        pane: 'routePane',
        style: {{
          color: '#047857',
          weight: 2.2,
          dashArray: '4, 5',
          fillColor: '#10b981',
          fillOpacity: 0.06
        }},
        interactive: false
      }});
    }}

    function setMetric(metric) {{
      currentMetric = metric;
      document.getElementById('btn-total').classList.toggle('active', metric === 'total');
      document.getElementById('btn-trash').classList.toggle('active', metric === 'trash');
      document.getElementById('btn-recycling').classList.toggle('active', metric === 'recycling');
      
      updateLegend();
      if (smdLayer) smdLayer.setStyle(smdStyle);
    }}

    function toggleSMDLayer(show) {{
      if (show) map.addLayer(smdLayer);
      else map.removeLayer(smdLayer);
    }}

    function toggleWardLayer(show) {{
      if (show) map.addLayer(wardLayer);
      else map.removeLayer(wardLayer);
    }}

    function toggleTrashRoutes(show) {{
      if (show) map.addLayer(trashRoutesLayer);
      else map.removeLayer(trashRoutesLayer);
    }}

    function toggleRecycleRoutes(show) {{
      if (show) map.addLayer(recycleRoutesLayer);
      else map.removeLayer(recycleRoutesLayer);
    }}

    function zoomToTopHotspot() {{
      selectHierarchy('5E03');
    }}

    function handleSearch(query) {{
      const q = query.trim().toUpperCase();
      if (!q) return;
      
      const wardMatch = q.match(/^(?:WARD\\s*|W)?([1-8])$/);
      if (wardMatch) {{
        selectWard(parseInt(wardMatch[1]));
        return;
      }}

      const foundSMD = MAP_DATA.smds.features.find(f => f.properties.smd_id === q);
      if (foundSMD) {{
        selectHierarchy(q);
        return;
      }}

      const foundANC = MAP_DATA.smds.features.filter(f => f.properties.anc_id === q);
      if (foundANC.length > 0) {{
        selectANC(q);
      }}
    }}

    function updateLegend() {{
      const th = THRESHOLDS[currentMetric];
      const pal = PALETTES[currentMetric];
      const title = currentMetric === 'trash' ? 'Missed Trash (30d)' :
                    currentMetric === 'recycling' ? 'Missed Recycling (30d)' : 'Missed Collections (30d)';

      document.getElementById('legend-title').innerText = title;
      let html = `
        <div class="legend-row">
          <div class="legend-color" style="background: #1e293b; border-color: rgba(255,255,255,0.1);"></div>
          <span>0 requests</span>
        </div>
      `;
      for (let i = 1; i < th.length; i++) {{
        const low = th[i];
        const high = (i < th.length - 1) ? (th[i + 1] - 1) : '+';
        const label = high === '+' ? `${{low}}+` : `${{low}}–${{high}}`;
        html += `
          <div class="legend-row">
            <div class="legend-color" style="background: ${{pal[i]}}"></div>
            <span>${{label}}</span>
          </div>
        `;
      }}
      document.getElementById('legend-scale').innerHTML = html;
    }}

    // ==========================================
    // INITIALIZE 4 STANDALONE CHARTS
    // ==========================================
    function initCharts() {{
      Chart.defaults.color = '#94a3b8';
      Chart.defaults.font.family = "'Plus Jakarta Sans', system-ui, sans-serif";

      // Chart 1: Wards Stacked Bar (Trash vs Recycling)
      const ctxWard = document.getElementById('ward180Chart').getContext('2d');
      new Chart(ctxWard, {{
        type: 'bar',
        data: {{
          labels: {json.dumps(chart_180d_ward_labels)},
          datasets: [
            {{
              label: 'Missed Trash',
              data: {json.dumps(chart_180d_ward_trash)},
              backgroundColor: '#ef4444',
              borderRadius: 4
            }},
            {{
              label: 'Missed Recycling',
              data: {json.dumps(chart_180d_ward_rec)},
              backgroundColor: '#10b981',
              borderRadius: 4
            }}
          ]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          scales: {{
            x: {{ stacked: true, grid: {{ color: 'rgba(255,255,255,0.06)' }} }},
            y: {{ stacked: true, grid: {{ color: 'rgba(255,255,255,0.06)' }}, title: {{ display: true, text: 'Total Service Requests' }} }}
          }},
          plugins: {{
            legend: {{ position: 'top', labels: {{ boxWidth: 12 }} }},
            tooltip: {{
              backgroundColor: '#090d16',
              titleColor: '#ffffff',
              borderColor: '#38bdf8',
              borderWidth: 1,
              padding: 10
            }}
          }},
          onClick: (e, elements) => {{
            if (elements.length > 0) {{
              const idx = elements[0].index;
              selectWard(idx + 1);
              document.getElementById('map-interactive').scrollIntoView({{ behavior: 'smooth' }});
            }}
          }}
        }}
      }});

      // Chart 2: Ward Address Recurrence Stacked Bar (Single vs Multi-Day Repeat)
      const ctxWardRep = document.getElementById('wardRepeatChart').getContext('2d');
      new Chart(ctxWardRep, {{
        type: 'bar',
        data: {{
          labels: {json.dumps(chart_180d_ward_labels)},
          datasets: [
            {{
              label: 'Single-Incident Addresses',
              data: {json.dumps(chart_180d_ward_single)},
              backgroundColor: '#0284c7',
              borderRadius: 4
            }},
            {{
              label: 'Multi-Day Repeat Addresses',
              data: {json.dumps(chart_180d_ward_repeat)},
              backgroundColor: '#f59e0b',
              borderRadius: 4
            }}
          ]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          scales: {{
            x: {{ stacked: true, grid: {{ color: 'rgba(255,255,255,0.06)' }} }},
            y: {{ stacked: true, grid: {{ color: 'rgba(255,255,255,0.06)' }}, title: {{ display: true, text: 'Unique Complaining Addresses' }} }}
          }},
          plugins: {{
            legend: {{ position: 'top', labels: {{ boxWidth: 12 }} }},
            tooltip: {{
              backgroundColor: '#090d16',
              titleColor: '#ffffff',
              borderColor: '#38bdf8',
              borderWidth: 1,
              padding: 10,
              callbacks: {{
                afterBody: (tooltipItems) => {{
                  const idx = tooltipItems[0].dataIndex;
                  const rates = {json.dumps(chart_180d_ward_repeat_pct)};
                  return `Repeat Address Rate: ${{rates[idx]}}%`;
                }}
              }}
            }}
          }},
          onClick: (e, elements) => {{
            if (elements.length > 0) {{
              const idx = elements[0].index;
              selectWard(idx + 1);
              document.getElementById('map-interactive').scrollIntoView({{ behavior: 'smooth' }});
            }}
          }}
        }}
      }});

      // Chart 3: Doughnut Ratio
      const ctxRatio = document.getElementById('ratio180Chart').getContext('2d');
      new Chart(ctxRatio, {{
        type: 'doughnut',
        data: {{
          labels: ['Missed Trash (70.8%)', 'Missed Recycling (29.2%)'],
          datasets: [{{
            data: [6248, 2575],
            backgroundColor: ['#ef4444', '#10b981'],
            borderColor: '#131d31',
            borderWidth: 3
          }}]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{
            legend: {{ position: 'bottom', labels: {{ boxWidth: 12, padding: 14 }} }},
            tooltip: {{
              backgroundColor: '#090d16',
              borderColor: '#38bdf8',
              borderWidth: 1
            }}
          }},
          cutout: '68%'
        }}
      }});

      // Chart 4: Top 10 SMD Hotspots (Single-Incident vs Multi-Day Repeat)
      const ctxHotspot = document.getElementById('hotspot180Chart').getContext('2d');
      new Chart(ctxHotspot, {{
        type: 'bar',
        data: {{
          labels: {json.dumps(chart_180d_smd_labels)},
          datasets: [
            {{
              label: 'Single-Incident Addresses',
              data: {json.dumps(chart_180d_smd_single)},
              backgroundColor: '#0284c7',
              borderRadius: 4
            }},
            {{
              label: 'Multi-Day Repeat Addresses',
              data: {json.dumps(chart_180d_smd_repeat)},
              backgroundColor: '#f59e0b',
              borderRadius: 4
            }}
          ]
        }},
        options: {{
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          scales: {{
            x: {{ stacked: true, grid: {{ color: 'rgba(255,255,255,0.06)' }}, title: {{ display: true, text: 'Unique Complaining Addresses' }} }},
            y: {{ stacked: true, grid: {{ display: false }} }}
          }},
          plugins: {{
            legend: {{ position: 'top', labels: {{ boxWidth: 12 }} }},
            tooltip: {{
              backgroundColor: '#090d16',
              titleColor: '#ffffff',
              borderColor: '#38bdf8',
              borderWidth: 1,
              padding: 10,
              callbacks: {{
                afterBody: (tooltipItems) => {{
                  const idx = tooltipItems[0].dataIndex;
                  const totals = {json.dumps(chart_180d_smd_totals)};
                  return `Total Service Requests: ${{totals[idx]}}`;
                }}
              }}
            }}
          }},
          onClick: (e, elements) => {{
            if (elements.length > 0) {{
              const idx = elements[0].index;
              const smdIds = {json.dumps(chart_180d_smd_ids)};
              const targetSmd = smdIds[idx];
              selectHierarchy(targetSmd);
              document.getElementById('map-interactive').scrollIntoView({{ behavior: 'smooth' }});
            }}
          }}
        }}
      }});
    }}

    // Initial Setup
    initSMDLayer();
    initWardLayer();
    initTrashRoutesLayer();
    initRecycleRoutesLayer();
    updateLegend();
    resetToCitywide();

    map.on('mouseout movestart zoomstart', hideSmdTooltip);

    // Load Charts on page load
    window.addEventListener('DOMContentLoaded', () => {{
      initCharts();
    }});

  </script>
</body>
</html>
'''

# Write to repository index.html and dc_missed_collection_map.html
out_index = os.path.join(BASE_DIR, 'index.html')
out_map = os.path.join(BASE_DIR, 'dc_missed_collection_map.html')

with open(out_index, 'w', encoding='utf-8') as f:
    f.write(html_page)

with open(out_map, 'w', encoding='utf-8') as f:
    f.write(html_page)

home_map = '/Users/zacheadams/dc_missed_collection_map.html'
if os.path.exists(home_map):
    with open(home_map, 'w', encoding='utf-8') as f:
        f.write(html_page)

print(f"Successfully compiled:\n - {out_index}\n - {out_map}")
