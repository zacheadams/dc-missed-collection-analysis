# Washington, DC Missed Collection Analysis

An open spatial analysis and interactive mapping application evaluating Washington, DC Department of Public Works (DPW) missed trash (`S0441`) and missed recycling (`S0321`) 311 service requests.

This resource provides public, aggregated municipal performance insights across all 8 Wards and 345 Single Member Districts (SMDs) to assist Advisory Neighborhood Commissioners (ANCs), Councilmembers, policy analysts, and residents in understanding waste collection reliability, routing bottlenecks, and service recurrence.

---

## Live Web Application

The compiled web application is packaged as a zero-dependency, self-contained single-page application in [`index.html`](index.html).

### Viewing Locally
```bash
# Clone the repository
git clone https://github.com/zacheadams/dc-missed-collection-analysis.git
cd dc-missed-collection-analysis

# Open directly in your browser
open index.html
```

---

## Key Analytical Findings

The report integrates two complementary evaluation windows:
1. **Interactive Map Explorer (Top Canvas)**: Evaluates recent operations over the **past 30 days** (3,301 service requests).
2. **Municipal Performance Report & Charts (Bottom Section)**: Evaluates long-term operational trends over the **past 180 days** (March 24 – September 20, 2026 • 8,823 service requests).

### 1. Address Deduplication & Repeat Incident Analysis
Evaluating raw ticket volumes alone can obscure whether collection failures represent broad neighborhood bypasses or chronic issues at isolated properties. Deduplicating records reveals:
- **Total Requests (180 Days)**: 8,823 service requests.
- **Unique Complaining Properties**: **5,974 distinct physical addresses** (average of **1.48 requests per complaining address**).
- **Single-Incident Properties**: **4,570 addresses (76.5%)** filed only once during the 6 months, representing isolated one-time collection delays.
- **Multi-Day Repeat Properties**: **1,404 addresses (23.5%)** submitted service requests across **two or more distinct collection days**. Because DPW routinely closes 311 tickets following route completion, re-filings across different days indicate that **previous ticket resolutions failed to permanently fix the underlying collection obstacle**.

### 2. Differentiating "Widespread Skips" vs. "Unsuccessful Problem Resolutions"

| Operational Pattern | Definition & Dynamics | Leading Districts |
| :--- | :--- | :--- |
| **Widespread Neighborhood Skips** | High unique address count, moderate repeat rate. Trucks miss entire street segments or alley corridors simultaneously on collection day. | **SMD 5E03** (90 unique properties • 22.2% repeat)<br>**SMD 3/4G02** (74 unique properties • 24.3% repeat)<br>**SMD 4B05** (66 unique properties • 19.7% repeat)<br>**SMD 3/4G03** (63 unique properties • 22.2% repeat) |
| **Unsuccessful Problem Resolutions (Chronic Recurrence)** | High count and percentage of properties filing across multiple distinct collection days. Residents re-filing 3 to 8 times across successive cycles. | **SMD 3/4G04** (30 repeat properties • 37.0% repeat; max 8 distinct days)<br>**SMD 3F06** (22 repeat properties • 32.8% repeat)<br>**SMD 5B06** (20 repeat properties • 35.1% repeat)<br>**SMD 3E03** (18 repeat properties • 38.3% repeat)<br>**SMD 7F04** (15 repeat properties • 34.9%; max 7 distinct days) |

#### Acute Chronic Repeat Pockets (>45% Repeat Rate)
In certain dense historic rowhouse districts, over 45% to 58% of all complaining properties required repeat tickets across multiple collection days:
- **SMD 5C05** (Eckington / Edgewood): **57.9% repeat rate** (11 repeat properties / 19 unique addresses)
- **SMD 1D07** (Mount Pleasant): **52.4% repeat rate** (11 repeat properties / 21 unique addresses)
- **SMD 1A01** (Columbia Heights): **50.0% repeat rate** (5 repeat properties / 10 unique addresses)
- **SMD 5D05** (Trinidad): **47.4% repeat rate** (9 repeat properties / 19 unique addresses)
- **SMD 2B01** (Dupont Circle): **46.4% repeat rate** (13 repeat properties / 28 unique addresses)

---

### 3. Ward-by-Ward Comparison Matrix

| Ward | Councilmember | Total Requests | Unique Addrs (Skipped Areas) | Repeat Addrs (&ge;2 Days) | Repeat Rate % | Trash % | Top Volume SMD |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Ward 1** | Brianne Nadeau | 965 | 665 | 150 | 22.6% | 66.7% | SMD 1E01 (51 addrs / 74 reqs) |
| **Ward 2** | Brooke Pinto | 638 | 401 | 104 | 25.9% | 73.4% | SMD 2B08 (64 addrs / 89 reqs) |
| **Ward 3** | Matthew Frumin | 1,268 | 837 | 219 | **26.2%** | 59.1% | SMD 3F06 (67 addrs / 103 reqs) |
| **Ward 4** | Janeese Lewis George | **1,666** | **1,134** | **266** | 23.5% | 72.4% | SMD 3/4G04 (81 addrs / 146 reqs) |
| **Ward 5** | Zachary Parker | 1,354 | 911 | 220 | 24.1% | 69.3% | SMD 5E03 (90 addrs / 136 reqs) |
| **Ward 6** | Charles Allen | 821 | 586 | 125 | 21.3% | 71.0% | SMD 6A01 (32 addrs / 45 reqs) |
| **Ward 7** | Wendell Felder | 1,406 | 979 | 208 | **21.2%** | 81.9% | SMD 7F04 (43 addrs / 75 reqs) |
| **Ward 8** | Trayon White, Sr. | 705 | 461 | 112 | 24.3% | 72.1% | SMD 8B03 (29 addrs / 47 reqs) |

- **Ward 4**: Leads the District in cumulative service requests (1,666), unique skipped properties (1,134), and repeat properties (266).
- **Ward 7**: Has the second-highest unique address count (979), but the lowest repeat rate in DC (21.2%), demonstrating that late-summer volume was broadly dispersed across hundreds of detached single-family blocks rather than recurring repeat callers.
- **Ward 3**: Exhibits the highest ward-wide repeat rate (26.2%), indicating stubborn localized recurrence in Upper Northwest.

---

## Application Architecture & Map Features

- **Public-Domain Census TIGER Basemap**: Uses U.S. Census Bureau TIGERweb Transportation and Hydrography static cached tiles—requiring no third-party API keys or subscription services.
- **Scoped Street Labeling**: Street names remain suppressed at the district-wide level to eliminate visual clutter and render strictly within the focused Ward boundary.
- **Cascading 3-Tier Selectors**: Independent cascading dropdowns for `Ward` > `ANC` > `SMD`, dynamically populated based on parent selection and bidirectionally synchronized with map clicks, the search bar, and breadcrumb trails.
- **WCAG AAA Tooltips**: High-contrast tooltip styling (`#090d16` background, `#38bdf8` border, and bright `#ffffff`/`#facc15` typography) ensuring readability across all basemap contrast levels.
- **Self-Contained Export Capability**: Each visualization contains an explicit time period subtitle and an inline footnote documenting the data source and temporal scope, enabling clean standalone screenshots for policy memos and community communications.
- **Full Smooth Scroll-to-Zoom**: Enabled directly on the map viewport (`scrollWheelZoom: true`).
- **Interactive Route Overlays**: When toggling DPW Trash Routes (140) or DPW Recycling Routes (173), hovering over the map displays route names, collection schedules, and service areas directly within the high-contrast tooltip.

---

## Repository Structure

```
dc-missed-collection-analysis/
├── index.html                     # Primary standalone application (Leaflet + Chart.js)
├── dc_missed_collection_map.html    # Mirror file for local path compatibility
├── README.md                      # Comprehensive analytical report and documentation
├── .gitignore                     # Standard version control ignore rules
├── data/                          # Aggregated datasets and geospatial boundaries
│   ├── smd_180d_address_stats.json  # 180-day address-level deduplication metrics
│   ├── dc_map_data_v2.json         # 30-day map payload with route geometries
│   ├── dc_smds.geojson             # 345 DC Single Member District boundaries
│   ├── dc_wards.geojson            # 8 DC Ward boundaries
│   ├── dc_trash_routes.geojson     # 140 DPW trash collection routes
│   └── dc_recycle_routes.geojson   # 173 DPW recycling collection routes
└── scripts/                       # Reproducible data retrieval and analysis pipelines
    ├── fetch_311_data.py           # Queries DC GIS FeatureServer 13 for 311 tickets
    ├── analyze_repeat_addresses.py # Computes address deduplication and repeat metrics
    └── build_page.py               # Compiles complete standalone HTML application
```

---

## Data Sources & Attribution

- **311 Service Requests**: [Open Data DC](https://opendata.dc.gov/) • DC Department of Public Works (DPW) Service Requests FeatureServer (`S0441`: Missed Trash, `S0321`: Missed Recycling).
- **Geographic Boundaries**: [DC Office of Planning / DC GIS](https://opendata.dc.gov/) • 2023 Single Member District (SMD) and Ward Boundaries.
- **Basemap Imagery**: [U.S. Census Bureau TIGERweb](https://tigerweb.geo.census.gov/) • Transportation and Hydrography Tile Services.

---

## License

This project is licensed under the [MIT License](LICENSE). All underlying government data sources are public domain.
