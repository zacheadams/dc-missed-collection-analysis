#!/usr/bin/env python3
"""
Compiles the Dedicated Interactive Map Application (map.html).
Features:
- Local Stamen Toner basemap cached offline for Zooms 11 through 15
- Commented-out U.S. Census TIGERweb basemap layers for contingency reactivation
- High-contrast choropleth and boundary styling optimized for black-and-white Toner cartography
- Cascading Ward, ANC, and SMD selectors plus DPW route overlays
- Context-aware static map export to US Letter (8.5" x 11") PDF and PNG
- Strict No-Emoji policy across UI, code, and comments
- Fully offline operation via assets/vendor/
"""

import os
import sys
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
map_data_path = os.path.join(BASE_DIR, 'data', 'dc_map_data_v2.json')
addr_stats_path = os.path.join(BASE_DIR, 'data', 'smd_180d_address_stats.json')

# 1. Load 30-day map data (for the mapping app)
with open(map_data_path, 'r', encoding='utf-8') as f:
    map_data = json.load(f)

# Ensure each SMD has ward_share_pct precalculated
wards_dict = {f['properties']['ward']: f['properties']['total'] for f in map_data['wards']['features']}
for f in map_data['smds']['features']:
    w = f['properties'].get('ward')
    tot = f['properties'].get('total', 0)
    wtot = wards_dict.get(w, 0)
    f['properties']['ward_share_pct'] = round((tot / wtot * 100), 1) if wtot > 0 else 0.0

json_str = json.dumps(map_data, separators=(',', ':'))

# 2. Load 180-day address-level stats (for deduplication and repeat analysis in inspector)
with open(addr_stats_path, 'r', encoding='utf-8') as f:
    addr_data_180d = json.load(f)

city_180d = addr_data_180d['citywide']
ward_180d_stats = addr_data_180d['wards']
smds_180d = addr_data_180d['smds']

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

html_page = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Interactive Map | DC DPW Missed Collection Analysis</title>

  <!-- Local Vendored Leaflet CSS -->
  <link rel="stylesheet" href="assets/vendor/leaflet/leaflet.css" />

  <!-- Google Fonts: Plus Jakarta Sans & JetBrains Mono -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">

  <!-- Local Vendored Export Libraries -->
  <script src="assets/vendor/jspdf/jspdf.umd.min.js"></script>
  <script src="assets/vendor/html2canvas/html2canvas.min.js"></script>

  <style>
    :root {{
      --bg-dark: #070a12;
      --bg-card: #0d1322;
      --bg-panel: rgba(13, 19, 34, 0.94);
      --border: rgba(255, 255, 255, 0.11);
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
      -webkit-font-smoothing: antialiased;
      overflow-x: hidden;
    }}

    /* Top Navigation Bar */
    .site-nav {{
      background: rgba(7, 10, 18, 0.96);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: 0;
      z-index: 1000;
      padding: 12px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .nav-brand {{
      display: flex;
      flex-direction: column;
    }}

    .nav-title {{
      font-size: 16px;
      font-weight: 800;
      color: #ffffff;
      letter-spacing: -0.02em;
    }}

    .nav-subtitle {{
      font-size: 11px;
      color: var(--text-dim);
      font-family: var(--font-mono);
    }}

    .nav-links {{
      display: flex;
      align-items: center;
      gap: 14px;
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

    .btn-export {{
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid var(--border);
      color: #ffffff;
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      font-family: var(--font-mono);
      transition: all 0.15s ease;
    }}

    .btn-export:hover {{
      background: #0284c7;
      border-color: #38bdf8;
    }}

    /* Main Full-Viewport Workspace */
    .map-workspace {{
      position: relative;
      width: 100vw;
      height: calc(100vh - 58px);
      overflow: hidden;
    }}

    #map {{
      width: 100%;
      height: 100%;
      background: #ffffff;
    }}

    /* Floating Left Control Panel */
    .control-panel {{
      position: absolute;
      top: 16px;
      left: 16px;
      width: 320px;
      background: var(--bg-panel);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 16px;
      z-index: 500;
      box-shadow: 0 16px 36px rgba(0, 0, 0, 0.4);
    }}

    .panel-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      padding-bottom: 8px;
      border-bottom: 1px solid var(--border);
    }}

    .panel-title {{
      font-size: 13px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #ffffff;
    }}

    .panel-tag {{
      background: rgba(56, 189, 248, 0.15);
      color: #38bdf8;
      border: 1px solid rgba(56, 189, 248, 0.3);
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 10px;
      font-family: var(--font-mono);
      font-weight: 700;
    }}

    /* Hierarchy Dropdowns */
    .hierarchy-container {{
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-bottom: 12px;
    }}

    .hierarchy-row {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .hierarchy-label {{
      width: 44px;
      font-size: 11px;
      font-weight: 700;
      font-family: var(--font-mono);
      color: var(--text-muted);
      text-transform: uppercase;
    }}

    .hierarchy-select {{
      flex: 1;
      background: rgba(7, 10, 18, 0.8);
      border: 1px solid var(--border);
      color: var(--text-main);
      padding: 6px 10px;
      border-radius: 6px;
      font-size: 12px;
      font-family: var(--font-sans);
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
      margin-bottom: 12px;
    }}

    .search-box input {{
      width: 100%;
      background: rgba(7, 10, 18, 0.8);
      border: 1px solid var(--border);
      color: var(--text-main);
      padding: 6px 10px;
      border-radius: 6px;
      font-size: 12px;
      font-family: var(--font-sans);
    }}

    .search-box input:focus {{
      outline: none;
      border-color: var(--border-focus);
    }}

    /* Metric Switcher */
    .metric-toggle-group {{
      display: flex;
      gap: 4px;
      background: rgba(7, 10, 18, 0.6);
      padding: 3px;
      border-radius: 6px;
      border: 1px solid var(--border);
      margin-bottom: 12px;
    }}

    .metric-btn {{
      flex: 1;
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 6px 4px;
      font-size: 11px;
      font-weight: 700;
      border-radius: 4px;
      cursor: pointer;
      font-family: var(--font-sans);
      transition: all 0.15s ease;
      text-align: center;
    }}

    .metric-btn.active {{
      background: #0284c7;
      color: #ffffff;
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

    /* Floating Breadcrumbs & Quick Reset */
    .breadcrumb-bar {{
      position: absolute;
      top: 16px;
      left: 352px;
      background: var(--bg-panel);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 8px 14px;
      z-index: 500;
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      font-family: var(--font-mono);
      color: var(--text-muted);
    }}

    .breadcrumb-item {{
      cursor: pointer;
      color: #38bdf8;
      font-weight: 600;
    }}

    .breadcrumb-item:hover {{
      text-decoration: underline;
    }}

    .breadcrumb-item.active {{
      color: #ffffff;
      font-weight: 700;
      cursor: default;
      text-decoration: none;
    }}

    /* Floating District Inspector (Right Side) */
    .inspector-panel {{
      position: absolute;
      top: 16px;
      right: 16px;
      width: 330px;
      background: var(--bg-panel);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 16px;
      z-index: 500;
      box-shadow: 0 16px 36px rgba(0, 0, 0, 0.4);
    }}

    .inspector-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 10px;
      padding-bottom: 8px;
      border-bottom: 1px solid var(--border);
    }}

    .inspector-title {{
      font-size: 16px;
      font-weight: 800;
      color: #ffffff;
      letter-spacing: -0.02em;
    }}

    .inspector-sub {{
      font-size: 11px;
      color: var(--text-dim);
      font-family: var(--font-mono);
    }}

    .inspector-stat-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-bottom: 12px;
    }}

    .stat-tile {{
      background: rgba(7, 10, 18, 0.6);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 8px 10px;
    }}

    .stat-tile-lbl {{
      font-size: 10px;
      color: var(--text-muted);
      text-transform: uppercase;
      font-family: var(--font-mono);
    }}

    .stat-tile-val {{
      font-size: 18px;
      font-weight: 800;
      font-family: var(--font-mono);
      color: #ffffff;
    }}

    .inspector-details {{
      font-size: 11px;
      color: var(--text-muted);
      line-height: 1.5;
    }}

    .inspector-route-box {{
      margin-top: 10px;
      padding-top: 8px;
      border-top: 1px solid var(--border);
    }}

    /* Floating Legend */
    .legend-panel {{
      position: absolute;
      bottom: 24px;
      left: 16px;
      background: var(--bg-panel);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 10px 14px;
      z-index: 500;
      font-size: 11px;
    }}

    .legend-title {{
      font-weight: 700;
      color: #ffffff;
      font-family: var(--font-mono);
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 6px;
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
    }}

    .scale-labels {{
      display: flex;
      justify-content: space-between;
      color: var(--text-dim);
      font-family: var(--font-mono);
      font-size: 9px;
      margin-top: 4px;
    }}

    /* Leaflet Tooltips */
    .leaflet-tooltip-smd {{
      background: rgba(13, 19, 34, 0.96) !important;
      border: 1px solid #38bdf8 !important;
      color: #f8fafc !important;
      border-radius: 6px !important;
      padding: 8px 12px !important;
      font-family: var(--font-sans) !important;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.6) !important;
    }}
  </style>
</head>
<body>

  <!-- Top Navigation Bar -->
  <nav class="site-nav">
    <div class="nav-brand">
      <span class="nav-title">DC Missed Collection Analysis</span>
      <span class="nav-subtitle">Interactive Map Application • Stamen Toner</span>
    </div>
    <div class="nav-links">
      <a href="index.html" class="nav-link">Home</a>
      <a href="map.html" class="nav-link active">Interactive Map</a>
      <a href="report.html" class="nav-link">Operational Report</a>
      <a href="https://github.com/zacheadams/dc-missed-collection-analysis" target="_blank" class="nav-link">GitHub</a>
      <button onclick="exportMapPdf()" class="btn-export">Export Map (PDF)</button>
      <button onclick="exportMapPng()" class="btn-export">Export Map (PNG)</button>
    </div>
  </nav>

  <!-- Full Viewport Map Workspace -->
  <div class="map-workspace" id="map-interactive">
    <div id="map"></div>

    <!-- Floating Breadcrumbs -->
    <div class="breadcrumb-bar" id="breadcrumb-bar">
      <span>Context:</span>
      <span class="breadcrumb-item active" id="breadcrumb-citywide" onclick="resetToCitywide()">Citywide (District)</span>
      <span id="breadcrumb-crumbs"></span>
    </div>

    <!-- Floating Left Control Panel -->
    <div class="control-panel">
      <div class="panel-header">
        <span class="panel-title">District Hierarchy</span>
        <span class="panel-tag">Past 30 Days</span>
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

      <div class="search-box">
        <input type="text" id="smd-search" placeholder="Search SMD (e.g. 5E03), ANC, or Ward..." oninput="handleSearch(this.value)">
      </div>

      <div class="metric-toggle-group">
        <button class="metric-btn active" id="btn-total" onclick="setMetric('total')">All 311</button>
        <button class="metric-btn" id="btn-trash" onclick="setMetric('trash')">Trash Only</button>
        <button class="metric-btn" id="btn-recycling" onclick="setMetric('recycling')">Recycling Only</button>
      </div>

      <div class="layer-controls">
        <label class="checkbox-row">
          <span><span class="badge-route" style="background: #0284c7;"></span>SMD Request Layer (345)</span>
          <input type="checkbox" id="chk-smd" checked onchange="toggleSMDLayer(this.checked)">
        </label>
        <label class="checkbox-row">
          <span><span class="badge-route" style="background: #a855f7;"></span>Ward Boundaries (8)</span>
          <input type="checkbox" id="chk-wards" checked onchange="toggleWardLayer(this.checked)">
        </label>
        <label class="checkbox-row">
          <span><span class="badge-route" style="background: #dc2626; border: 1px dashed #ef4444;"></span>DPW Trash Routes (103)</span>
          <input type="checkbox" id="chk-trash-routes" onchange="toggleTrashRoutes(this.checked)">
        </label>
        <label class="checkbox-row">
          <span><span class="badge-route" style="background: #059669; border: 1px dashed #10b981;"></span>DPW Recycling Routes (120)</span>
          <input type="checkbox" id="chk-recycle-routes" onchange="toggleRecycleRoutes(this.checked)">
        </label>
      </div>
    </div>

    <!-- Floating Right Inspector Panel -->
    <div class="inspector-panel" id="inspector-panel">
      <div class="inspector-header">
        <div>
          <div class="inspector-title" id="insp-title">District of Columbia</div>
          <div class="inspector-sub" id="insp-sub">Citywide Performance Summary</div>
        </div>
      </div>

      <div class="inspector-stat-grid">
        <div class="stat-tile">
          <div class="stat-tile-lbl">Selected Requests</div>
          <div class="stat-tile-val" id="insp-stat-total">3,301</div>
        </div>
        <div class="stat-tile">
          <div class="stat-tile-lbl">Share of Volume</div>
          <div class="stat-tile-val" id="insp-stat-share">100%</div>
        </div>
        <div class="stat-tile">
          <div class="stat-tile-lbl">Trash (S0441)</div>
          <div class="stat-tile-val" style="color: #fca5a5;" id="insp-stat-trash">2,284</div>
        </div>
        <div class="stat-tile">
          <div class="stat-tile-lbl">Recycling (S0321)</div>
          <div class="stat-tile-val" style="color: #6ee7b7;" id="insp-stat-rec">1,017</div>
        </div>
      </div>

      <div class="inspector-details" id="insp-details">
        Select any Single Member District or Ward on the map or use the dropdowns on the left to inspect localized performance, repeat rates, and DPW collection schedules.
      </div>

      <div class="inspector-route-box" id="insp-route-box" style="display: none;">
        <!-- Filled dynamically -->
      </div>
    </div>

    <!-- Floating Legend Panel -->
    <div class="legend-panel">
      <div class="legend-title" id="legend-title">Total Requests (30 Days)</div>
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
    const MAP_DATA = {json_str};

    // State
    let selectedWardNum = null;
    let selectedAncId = null;
    let selectedSmdId = null;
    let currentMetric = 'total';

    // Initialize Map
    const map = L.map('map', {{
      center: [38.9072, -77.01],
      zoom: 12,
      zoomControl: false,
      minZoom: 11,
      maxZoom: 18,
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

    map.createPane('routePane');
    map.getPane('routePane').style.zIndex = 340;

    map.createPane('smdPane');
    map.getPane('smdPane').style.zIndex = 400;

    // Basemap: Local Stamen Toner (Zooms 11 to 15)
    L.tileLayer('tiles/{{z}}/{{x}}/{{y}}.png', {{
      pane: 'tonerBasePane',
      minZoom: 11,
      maxNativeZoom: 15,
      maxZoom: 18,
      bounds: [[38.7916, -77.1198], [38.9960, -76.9091]],
      attribution: 'Map tiles by Stamen Design, under CC BY 3.0. Data by OpenStreetMap, under ODbL.'
    }}).addTo(map);

    /*
     * CENSUS TIGERWEB ALTERNATIVE BASEMAP:
     * To revert to U.S. Census TIGERweb basemaps, uncomment the two layers below:
     *
     * L.tileLayer('https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Transportation/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
     *   pane: 'tonerBasePane',
     *   maxZoom: 18,
     *   opacity: 0.95,
     *   attribution: 'U.S. Census Bureau TIGERweb'
     * }}).addTo(map);
     *
     * L.tileLayer('https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Hydro/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
     *   pane: 'tonerBasePane',
     *   maxZoom: 18,
     *   opacity: 0.75,
     *   interactive: false
     * }}).addTo(map);
     */

    let smdLayer = null;
    let wardLayer = null;
    let trashRoutesLayer = null;
    let recycleRoutesLayer = null;
    let wardMaskLayer = null;
    let activeHoverLayer = null;

    // Tooltip
    const smdTooltip = L.tooltip({{
      sticky: true,
      direction: 'top',
      className: 'leaflet-tooltip-smd',
      offset: [0, -10]
    }});

    // Choropleth Scales (Optimized for black-and-white Toner)
    const THRESHOLDS = {{
      total:     [0, 3, 7, 12, 18, 26, 36],
      trash:     [0, 2, 5,  9, 14, 20, 28],
      recycling: [0, 1, 3,  6,  9, 13, 18]
    }};

    const PALETTES = {{
      total:     ['rgba(241, 245, 249, 0.45)', '#38bdf8', '#0284c7', '#eab308', '#f97316', '#ef4444', '#991b1b'],
      trash:     ['rgba(241, 245, 249, 0.45)', '#fef08a', '#fb923c', '#f97316', '#ea580c', '#dc2626', '#7f1d1d'],
      recycling: ['rgba(241, 245, 249, 0.45)', '#a7f3d0', '#34d399', '#10b981', '#059669', '#0d9488', '#0f766e']
    }};

    function getColor(val, metric) {{
      if (val === 0) return 'rgba(241, 245, 249, 0.45)';
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
      const isSelected = selectedSmdId === p.smd_id;
      const inAnc = selectedAncId === p.anc_id;
      const inWard = selectedWardNum === p.ward;

      if (selectedSmdId) {{
        if (isSelected) {{
          return {{
            fillColor: getColor(val, currentMetric),
            weight: 3.5,
            opacity: 1,
            color: '#facc15',
            fillOpacity: 0.92
          }};
        }} else if (inWard) {{
          return {{
            fillColor: getColor(val, currentMetric),
            weight: 0.8,
            opacity: 0.5,
            color: '#38bdf8',
            fillOpacity: 0.35
          }};
        }} else {{
          return {{
            fillColor: getColor(val, currentMetric),
            weight: 0.4,
            opacity: 0.15,
            color: 'rgba(100, 116, 139, 0.2)',
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
            color: '#0284c7',
            fillOpacity: val === 0 ? 0.35 : 0.78
          }};
        }} else {{
          return {{
            fillColor: getColor(val, currentMetric),
            weight: 0.4,
            opacity: 0.2,
            color: 'rgba(100, 116, 139, 0.2)',
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
            color: '#38bdf8',
            fillOpacity: val === 0 ? 0.35 : 0.78
          }};
        }} else {{
          return {{
            fillColor: getColor(val, currentMetric),
            weight: 0.4,
            opacity: 0.2,
            color: 'rgba(100, 116, 139, 0.2)',
            fillOpacity: 0.08
          }};
        }}
      }}

      return {{
        fillColor: getColor(val, currentMetric),
        weight: 0.9,
        opacity: 0.85,
        color: 'rgba(30, 41, 59, 0.65)',
        fillOpacity: val === 0 ? 0.35 : 0.72
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

    function updateWardMask() {{
      if (wardMaskLayer) {{
        map.removeLayer(wardMaskLayer);
        wardMaskLayer = null;
      }}
      if (!selectedWardNum) return;

      const wardFeat = MAP_DATA.wards.features.find(f => f.properties.ward === selectedWardNum);
      if (!wardFeat) return;

      const outerRing = [[-85, -180], [-85, 180], [85, 180], [85, -180]];
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
        fillOpacity: 0.85,
        stroke: false,
        interactive: false
      }}).addTo(map);
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
          area_desc: f.properties.area_desc
        }});
      }});
    }}

    function findRouteAtLatLng(index, latlng) {{
      const x = latlng.lng;
      const y = latlng.lat;
      for (let i = 0; i < index.length; i++) {{
        const item = index[i];
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
              layer.setStyle({{ weight: 3.5, color: '#38bdf8', fillOpacity: 0.88 }});
              smdTooltip.setContent(`
                <div style="font-weight: 800; font-size: 13px; color: #ffffff;">SMD ${{p.smd_id}}</div>
                <div style="font-size: 11px; color: #94a3b8;">ANC ${{p.anc_id}} • Ward ${{p.ward}}</div>
                <div style="margin-top: 4px; font-size: 12px; font-weight: 700; color: #38bdf8;">
                  ${{p[currentMetric] || 0}} ${{currentMetric.toUpperCase()}} Requests
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

    function initTrashRoutesLayer() {{
      trashRoutesLayer = L.geoJSON(MAP_DATA.trash_routes, {{
        pane: 'routePane',
        style: {{ color: '#dc2626', weight: 2.2, dashArray: '4, 5', fillColor: '#ef4444', fillOpacity: 0.12 }}
      }});
    }}

    function initRecycleRoutesLayer() {{
      recycleRoutesLayer = L.geoJSON(MAP_DATA.recycle_routes, {{
        pane: 'routePane',
        style: {{ color: '#059669', weight: 2.2, dashArray: '4, 5', fillColor: '#10b981', fillOpacity: 0.12 }}
      }});
    }}

    // Selection Handling
    function selectHierarchy(smdId) {{
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
      )).sort();

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
        .sort();

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
      }}
    }}

    function updateBreadcrumbs() {{
      const bar = document.getElementById('breadcrumb-crumbs');
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

    function updateInspectorCitywide() {{
      document.getElementById('insp-title').innerText = 'District of Columbia';
      document.getElementById('insp-sub').innerText = 'Citywide Performance Summary (Past 30 Days)';
      document.getElementById('insp-stat-total').innerText = '3,301';
      document.getElementById('insp-stat-share').innerText = '100%';
      document.getElementById('insp-stat-trash').innerText = '2,284';
      document.getElementById('insp-stat-rec').innerText = '1,017';
      document.getElementById('insp-details').innerText = 'Evaluating 3,301 311 missed collection service requests across all 8 Wards, 46 ANCs, and 345 Single Member Districts.';
      document.getElementById('insp-route-box').style.display = 'none';
    }}

    function updateInspectorWard(p) {{
      document.getElementById('insp-title').innerText = `Ward ${{p.ward}}`;
      document.getElementById('insp-sub').innerText = `Councilmember: ${{p.rep || ''}}`;
      document.getElementById('insp-stat-total').innerText = p.total.toLocaleString();
      document.getElementById('insp-stat-share').innerText = `${{p.share_pct}}%`;
      document.getElementById('insp-stat-trash').innerText = p.trash.toLocaleString();
      document.getElementById('insp-stat-rec').innerText = p.recycling.toLocaleString();
      document.getElementById('insp-details').innerText = `Ward ${{p.ward}} accounts for ${{p.total}} missed collections (${{p.share_pct}}% of citywide volume) over the past 30 days.`;
      document.getElementById('insp-route-box').style.display = 'none';
    }}

    function updateInspectorANC(ancId) {{
      const smdsInAnc = MAP_DATA.smds.features.filter(f => f.properties.anc_id === ancId);
      const total = smdsInAnc.reduce((sum, f) => sum + (f.properties.total || 0), 0);
      const trash = smdsInAnc.reduce((sum, f) => sum + (f.properties.trash || 0), 0);
      const rec = smdsInAnc.reduce((sum, f) => sum + (f.properties.recycling || 0), 0);
      const ward = smdsInAnc[0]?.properties.ward;

      document.getElementById('insp-title').innerText = `ANC ${{ancId}}`;
      document.getElementById('insp-sub').innerText = `Ward ${{ward}} • ${{smdsInAnc.length}} Single Member Districts`;
      document.getElementById('insp-stat-total').innerText = total.toLocaleString();
      document.getElementById('insp-stat-share').innerText = `${{round((total / 3301 * 100), 1)}}%`;
      document.getElementById('insp-stat-trash').innerText = trash.toLocaleString();
      document.getElementById('insp-stat-rec').innerText = rec.toLocaleString();
      document.getElementById('insp-details').innerText = `ANC ${{ancId}} contains ${{smdsInAnc.length}} Single Member Districts with ${{total}} missed requests over the past 30 days.`;
      document.getElementById('insp-route-box').style.display = 'none';
    }}

    function updateInspectorSMD(p, centerLatLng) {{
      document.getElementById('insp-title').innerText = `SMD ${{p.smd_id}}`;
      document.getElementById('insp-sub').innerText = `ANC ${{p.anc_id}} • Ward ${{p.ward}} (Councilmember: ${{ward_council[p.ward]}})`;
      document.getElementById('insp-stat-total').innerText = p.total || 0;
      document.getElementById('insp-stat-share').innerText = `${{p.ward_share_pct || 0}}%`;
      document.getElementById('insp-stat-trash').innerText = p.trash || 0;
      document.getElementById('insp-stat-rec').innerText = p.recycling || 0;
      document.getElementById('insp-details').innerText = `SMD ${{p.smd_id}} represents ${{p.ward_share_pct}}% of Ward ${{p.ward}}'s total missed collections over the past 30 days.`;

      // Find route overlaps
      const tr = findRouteAtLatLng(trashRouteIndex, centerLatLng);
      const rr = findRouteAtLatLng(recycleRouteIndex, centerLatLng);
      let rHtml = '';
      if (tr) {{
        rHtml += `<div style="color: #fca5a5; font-size: 11px;">Trash Route: <strong>${{tr.route}}</strong> (${{tr.day}})</div>`;
      }}
      if (rr) {{
        rHtml += `<div style="color: #6ee7b7; font-size: 11px; margin-top: 2px;">Recycling Route: <strong>${{rr.route}}</strong> (${{rr.day}})</div>`;
      }}
      if (rHtml) {{
        const rBox = document.getElementById('insp-route-box');
        rBox.innerHTML = '<div style="font-weight: 700; color: #ffffff; font-size: 11px; margin-bottom: 4px;">Assigned DPW Routes:</div>' + rHtml;
        rBox.style.display = 'block';
      }}
    }}

    function setMetric(metric) {{
      currentMetric = metric;
      document.getElementById('btn-total').classList.toggle('active', metric === 'total');
      document.getElementById('btn-trash').classList.toggle('active', metric === 'trash');
      document.getElementById('btn-recycling').classList.toggle('active', metric === 'recycling');
      updateLegend();
      if (smdLayer) smdLayer.setStyle(smdStyle);
    }}

    function updateLegend() {{
      const pal = PALETTES[currentMetric];
      const th = THRESHOLDS[currentMetric];
      const scaleEl = document.getElementById('legend-scale');
      scaleEl.innerHTML = pal.map(c => `<div class="scale-box" style="background: ${{c}};"></div>`).join('');
      document.getElementById('legend-title').innerText = `${{currentMetric.toUpperCase()}} Requests (30 Days)`;
      document.getElementById('legend-labels').innerHTML = `
        <span>0</span>
        <span>${{th[1]}}</span>
        <span>${{th[3]}}</span>
        <span>${{th[5]}}+</span>
      `;
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

    // Static Contextual Exports (US Letter: 8.5in x 11in)
    function getExportMetadata() {{
      if (selectedSmdId) {{
        const feat = MAP_DATA.smds.features.find(f => f.properties.smd_id === selectedSmdId);
        const p = feat ? feat.properties : {{}};
        return {{
          title: `Single Member District Report: SMD ${{selectedSmdId}}`,
          subtitle: `ANC ${{p.anc_id || selectedAncId}} • Ward ${{p.ward || selectedWardNum}} • Councilmember: ${{ward_council[p.ward] || ''}}`,
          metrics: `30-Day Missed Requests: Total: ${{p.total || 0}} | Trash: ${{p.trash || 0}} | Recycling: ${{p.recycling || 0}} (Ward Share: ${{p.ward_share_pct || 0}}%)`,
          filename: `dc-map-smd-${{selectedSmdId}}`
        }};
      }} else if (selectedAncId) {{
        return {{
          title: `Advisory Neighborhood Commission Report: ANC ${{selectedAncId}}`,
          subtitle: `Ward ${{selectedWardNum || ''}}`,
          metrics: `Active Metric: ${{currentMetric.toUpperCase()}} Missed Collection Requests (Past 30 Days)`,
          filename: `dc-map-anc-${{selectedAncId}}`
        }};
      }} else if (selectedWardNum) {{
        return {{
          title: `Ward Operational Report: Ward ${{selectedWardNum}}`,
          subtitle: `Councilmember: ${{ward_council[selectedWardNum] || ''}}`,
          metrics: `Active Metric: ${{currentMetric.toUpperCase()}} Missed Collection Requests (Past 30 Days)`,
          filename: `dc-map-ward-${{selectedWardNum}}`
        }};
      }} else {{
        return {{
          title: 'Washington, DC Missed Collection Analysis',
          subtitle: 'Citywide Spatial Explorer • Past 30 Days',
          metrics: `Active Metric: ${{currentMetric.toUpperCase()}} Requests across all 8 Wards and 345 SMDs`,
          filename: 'dc-map-citywide'
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
      doc.setFont('Helvetica', 'bold');
      doc.setFontSize(16);
      doc.setTextColor(15, 23, 42);
      doc.text(meta.title, 0.5, 0.6);

      doc.setFont('Helvetica', 'normal');
      doc.setFontSize(10);
      doc.setTextColor(51, 65, 85);
      doc.text(meta.subtitle, 0.5, 0.82);

      doc.setFontSize(9);
      doc.setTextColor(100, 116, 139);
      doc.text(meta.metrics, 0.5, 1.02);
      doc.text(`Generated: ${{new Date().toLocaleDateString()}} • Stamen Toner Basemap (US Letter)`, 10.5, 1.02, {{ align: 'right' }});

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

    // Initialization
    buildRouteSpatialIndex();
    initSMDLayer();
    initWardLayer();
    initTrashRoutesLayer();
    initRecycleRoutesLayer();
    updateLegend();
    resetToCitywide();

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
