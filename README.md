# Washington, DC Missed Collection Analysis

An open spatial analysis and interactive mapping application evaluating Washington, DC Department of Public Works (DPW) missed trash (`S0441`) and missed recycling (`S0321`) 311 service requests.

This resource provides public, aggregated municipal performance insights across all 8 Wards, 345 Single Member Districts (SMDs), and DPW collection routes to assist Advisory Neighborhood Commissioners (ANCs), Councilmembers, policy analysts, and residents in understanding waste collection reliability, routing bottlenecks, and service recurrence.

---

## Live Applications

- **Ward & SMD Analysis ([`index.html`](https://zacheadams.github.io/dc-missed-collection-analysis/))**: Interactive Census TIGER basemap with cascading Ward/ANC/SMD selectors, street-level labeling, 30-day spatial hot spots, and 180-day district deduplication metrics. Hovering over Single Member Districts or DPW routes displays route IDs, collection days, and physical neighborhood coverage.
- **DPW Route-Level Report ([`routes.html`](https://zacheadams.github.io/dc-missed-collection-analysis/routes.html))**: Dedicated operational route analysis evaluating 103 Trash Routes and 120 Recycling Routes, featuring Chart.js visual breakdowns, schedule bottleneck comparisons, and a searchable 223-route performance matrix identifying neighborhoods and ANCs.

### Viewing Locally
```bash
# Clone the repository
git clone https://github.com/zacheadams/dc-missed-collection-analysis.git
cd dc-missed-collection-analysis

# Open the primary map application
open index.html

# Open the DPW route-level report
open routes.html
```

---

## Key Analytical Findings: Ward & SMD Level

The primary application integrates two complementary evaluation windows:
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

## DPW Route-Level Analysis ([`routes.html`](https://zacheadams.github.io/dc-missed-collection-analysis/routes.html))

While SMD and Ward boundaries represent political representation, DPW trucks operate along designated operational route corridors. Evaluating collection data at the route level matches municipal operations directly to truck dispatch boundaries, isolating structural logistics challenges from political boundaries.

Across the 180-day evaluation window (March 24 – September 20, 2026), spatial join algorithms matched **8,751 out of 8,823 service requests (99.2%)** directly to official DPW route polygons:
- **Trash Routes**: 6,197 requests matched across **103 distinct DPW Trash Routes**.
- **Recycling Routes**: 2,554 requests matched across **120 distinct DPW Recycling Routes**.
- *72 requests (0.8%) fell in commercial, industrial, or federal jurisdictions outside residential DPW collection boundaries.*

Every route is mapped to its underlying physical DC neighborhoods, Wards, and Advisory Neighborhood Commissions (ANCs) using spatial intersection against official DC GIS boundary layers.

### Core Operational Patterns

#### Pattern 1: Extreme Pareto Concentration
Collection failures are heavily concentrated in a small minority of truck routes:
- The **top 10 trash routes (9.7% of routes) account for 23.1% of all missed trash complaints** (1,432 requests).
- The **top 10 recycling routes (8.3% of routes) account for 21.9% of all missed recycling complaints** (558 requests).
- The highest-volume corridors—**Route OR304** (Ward 3/4 • Tenleytown / Spring Valley / Hawthorne • 220 requests) and **Route IC203** (Ward 2/1 • Dupont Circle / Connecticut Ave / Cardozo • 198 requests)—generate more than **4x the median route volume** (51 requests).
- In contrast, 26.4% of trash routes and 30.6% of recycling routes registered zero complaints over the 180-day period.

#### Pattern 2: Day-of-Week Schedule Bottlenecks
Analyzing route service schedules exposes significant weekly operational imbalances:
- **Trash Bottleneck**: Wednesday collection routes generate the highest complaint volume in the District (1,369 requests / 982 unique addresses), driven by major corridors like **Route OR504** in Brookland/Brentwood (122 reqs), followed by Tuesday/Friday twice-weekly routes (1,047 requests). Thursday once-weekly routes exhibit the lowest failure count (521 requests).
- **Recycling Bottleneck**: Early-week operations account for **48.7% of all missed recycling complaints** across the District (Monday: 636 requests; Tuesday: 609 requests), led by **Route R323_1** in Chevy Chase/Barnaby Woods (83 reqs) and **Route R209_2** in Dupont Circle (71 reqs). Route performance improves steadily through the week, culminating in a low of 368 requests on Friday.

#### Pattern 3: Failure Typology — Widespread Skips vs. Resolution Failures
Cross-referencing unique complaining properties against repeat properties reveals two distinct failure modes:
- **Widespread Corridor Bypasses**: Routes such as **OR706** (Ward 7 • Burrville, Deanwood, NE Boundary) and **OR708** (Ward 7 • River Terrace, Twining, Dupont Park) exhibit high unique address counts (96 to 98 properties) but modest repeat rates (18.4% to 21.9%). Collection crews missed entire street blocks simultaneously, but follow-up re-servicing resolved the missed pickups.
- **Chronic Resolution Failures**: Routes such as **R209_2** (Ward 2 • Dupont Circle, Connecticut Ave, K St) exhibit a **50.0% repeat rate** (14 repeat addresses out of 28 unique properties) with an average of **2.54 requests per complaining property**. In these dense corridors, closing 311 tickets failed to address persistent physical obstacles (e.g., narrow alley access, construction scaffolding, or parking obstructions), forcing residents into repeated filing cycles.

#### Pattern 4: The Twice-Weekly Inner City Paradox
Inner City routes receive twice-weekly collection (`Tuesday/Friday` or `Monday/Thursday`) intended to provide higher service frequency in dense rowhouse neighborhoods. However:
- Inner City routes average **61.5 missed trash requests per route**, virtually identical to the 59.7 requests per route experienced in once-weekly Outer Ring routes.
- Corridors such as **Route IC203** (Ward 2/1 • Dupont Circle / Connecticut Ave / Cardozo • 198 reqs, 32.0% repeat rate) and **Route IC104** (Ward 1 • Cardozo/Shaw / Le Droit Park • 143 reqs, 20.2% repeat rate) show that added collection frequency does not compensate for alleyway congestion, illegal parking, and narrow clearance constraints.

---

### Top 10 DPW Trash Collection Routes (180 Days)

| Route | Ward | Primary Neighborhoods & ANCs | Schedule | Total Requests | Unique Addresses | Repeat Addresses | Repeat Rate % |
| :--- | :---: | :--- | :--- | :---: | :---: | :---: | :---: |
| **OR304** | Ward 3 / Ward 4 | Tenleytown, Spring Valley, Hawthorne (ANC 3E, 3/4G, 3D) | Monday | **220** | 138 | 41 | 29.7% |
| **IC203** | Ward 2 / Ward 1 | Dupont Circle, Connecticut Avenue/K Street, Howard University (ANC 2B, 1B, 1C) | Tuesday/Friday | **198** | 125 | 40 | 32.0% |
| **OR710** | Ward 7 / Ward 8 | Hillcrest, Skyland, Woodland (ANC 8B, 7B, 7F) | Friday | **180** | 117 | 35 | 29.9% |
| **IC104** | Ward 1 | Cardozo/Shaw, Le Droit Park, Howard University (ANC 1B, 2G, 1E) | Tuesday/Friday | **143** | 109 | 22 | 20.2% |
| **OR708** | Ward 7 | River Terrace, Twining, Dupont Park (ANC 7B, 7D) | Friday | **131** | 96 | 21 | 21.9% |
| **OR706** | Ward 7 | Burrville, NE Boundary, Fairfax Village (ANC 7B, 7C) | Friday | **131** | 98 | 18 | 18.4% |
| **OR403** | Ward 4 | Takoma, Manor Park, Petworth (ANC 4B, 4C, 4A) | Monday | **127** | 86 | 20 | 23.3% |
| **OR401** | Ward 4 | North Portal Estates, Colonial Village, Brightwood (ANC 4E, 4A, 4B) | Monday | **124** | 88 | 15 | 17.0% |
| **OR504** | Ward 5 | Brookland, Brentwood, Langdon (ANC 5B) | Wednesday | **122** | 78 | 22 | 28.2% |
| **OR309** | Ward 3 | Friendship Heights, American University Park, Tenleytown (ANC 3E, 3/4G) | Monday | **116** | 76 | 27 | 35.5% |

---

### Top 10 DPW Recycling Collection Routes (180 Days)

| Route | Ward | Primary Neighborhoods & ANCs | Schedule | Total Requests | Unique Addresses | Repeat Addresses | Repeat Rate % |
| :--- | :---: | :--- | :--- | :---: | :---: | :---: | :---: |
| **R321_4** | Ward 3 | American University Park, Tenleytown, Friendship Heights (ANC 3E, 3A) | Thursday | **86** | 56 | 15 | 26.8% |
| **R323_1** | Ward 4 | Chevy Chase, Hawthorne, Barnaby Woods (ANC 3/4G) | Monday | **83** | 67 | 11 | 16.4% |
| **R209_2** | Ward 2 | Dupont Circle, Connecticut Avenue/K Street, Howard University (ANC 2B, 2F, 1B) | Tuesday | **71** | 28 | 14 | 50.0% |
| **R526_3** | Ward 5 | Stronghold, Edgewood, Bloomingdale (ANC 5F, 5E) | Wednesday | **64** | 52 | 7 | 13.5% |
| **R527_3** | Ward 5 | Truxton Circle, Edgewood, Bloomingdale (ANC 5E, 5F) | Wednesday | **60** | 48 | 6 | 12.5% |
| **R320_1** | Ward 3 | Friendship Heights, American University Park, Tenleytown (ANC 3E, 3A, 3F) | Monday | **56** | 42 | 10 | 23.8% |
| **R424_3** | Ward 4 | Fort Totten, Takoma, Brightwood (ANC 4B, 4D, 5A) | Wednesday | **52** | 44 | 8 | 18.2% |
| **R508_2B** | Ward 5 | Langdon, Brookland, Brentwood (ANC 5C) | Tuesday | **50** | 42 | 7 | 16.7% |
| **R321_1A** | Ward 3 | North Cleveland Park, Forest Hills, Van Ness (ANC 3F) | Monday | **50** | 36 | 12 | 33.3% |
| **R110_2** | Ward 1 | Columbia Heights, Mt. Pleasant, Pleasant Plains (ANC 1A, 1B, 1D) | Tuesday | **50** | 41 | 5 | 12.2% |

---

## Application Architecture & Map Features

- **Public-Domain Census TIGER Basemap**: Uses U.S. Census Bureau TIGERweb Transportation and Hydrography static cached tiles—requiring no third-party API keys or subscription services.
- **Scoped Street Labeling**: Street names remain suppressed at the district-wide level to eliminate visual clutter and render strictly within the focused Ward boundary.
- **Cascading 3-Tier Selectors**: Independent cascading dropdowns for `Ward` > `ANC` > `SMD`, dynamically populated based on parent selection and bidirectionally synchronized with map clicks, the search bar, and breadcrumb trails.
- **WCAG AAA Tooltips**: High-contrast tooltip styling (`#090d16` background, `#38bdf8` border, and bright `#ffffff`/`#facc15` typography) ensuring readability across all basemap contrast levels.
- **Self-Contained Export Capability**: Each visualization contains an explicit time period subtitle and an inline footnote documenting the data source and temporal scope, enabling clean standalone screenshots for policy memos and community communications.
- **Full Smooth Scroll-to-Zoom**: Enabled directly on the map viewport (`scrollWheelZoom: true`).
- **Interactive Route Overlays**: When toggling DPW Trash Routes (140) or DPW Recycling Routes (173), hovering over the map displays route names, collection schedules, and physical neighborhood coverage directly within the high-contrast tooltip.

---

## Repository Structure

```
dc-missed-collection-analysis/
├── index.html                         # Primary standalone application (Ward & SMD Leaflet Map + Performance Report)
├── routes.html                        # Standalone DPW route-level performance report & interactive matrix
├── dc_missed_collection_map.html        # Mirror file for local path compatibility
├── README.md                          # Comprehensive analytical report and documentation
├── .gitignore                         # Standard version control ignore rules
├── data/                              # Aggregated datasets and geospatial boundaries
│   ├── dc_180d_service_requests.json   # Full 180-day 311 missed collection records (8,823 requests)
│   ├── route_180d_stats.json           # Precomputed DPW route-level performance and repeat metrics
│   ├── route_areas.json                # Precomputed spatial intersections mapping routes to neighborhoods & ANCs
│   ├── smd_180d_address_stats.json     # 180-day SMD address-level deduplication metrics
│   ├── dc_map_data_v2.json            # 30-day map payload with route geometries and area annotations
│   ├── dc_neighborhood_clusters.geojson # 46 official DC Neighborhood Cluster boundaries
│   ├── dc_neighborhoods.geojson       # 132 DC Neighborhood point locations
│   ├── dc_smds.geojson                # 345 DC Single Member District boundaries
│   ├── dc_wards.geojson               # 8 DC Ward boundaries
│   ├── dc_trash_routes.geojson        # 140 DPW trash collection routes
│   └── dc_recycle_routes.geojson      # 173 DPW recycling collection routes
└── scripts/                           # Reproducible data retrieval and analysis pipelines
    ├── fetch_311_data.py              # Queries DC GIS FeatureServer 13 for 311 tickets
    ├── analyze_repeat_addresses.py    # Computes address deduplication and repeat metrics for SMDs
    ├── compute_route_areas.py         # Performs spatial intersection to map routes to neighborhoods/ANCs
    ├── generate_route_report.py       # Aggregates DPW route statistics and builds routes.html
    └── build_page.py                  # Compiles complete standalone HTML application
```

---

## Data Sources & Attribution

- **311 Service Requests**: [Open Data DC](https://opendata.dc.gov/) • DC Department of Public Works (DPW) Service Requests FeatureServer (`S0441`: Missed Trash, `S0321`: Missed Recycling).
- **Geographic Boundaries**: [DC Office of Planning / DC GIS](https://opendata.dc.gov/) • 2023 Single Member District (SMD), Ward, and Neighborhood Cluster Boundaries.
- **DPW Collection Routes**: [Open Data DC](https://opendata.dc.gov/) • Department of Public Works Trash and Recycling Routes.
- **Basemap Imagery**: [U.S. Census Bureau TIGERweb](https://tigerweb.geo.census.gov/) • Transportation and Hydrography Tile Services.

---

## License

This project is licensed under the [MIT License](LICENSE). All underlying government data sources are public domain.
