# Repository Standards & Agent Instructions

This document codifies development standards, operational conventions, and architectural guidelines for automated agents and developers contributing to `dc-missed-collection-analysis`.

---

## 1. Strict No-Emoji Standard

- **No Emojis Anywhere**: Absolutely no emojis may be used anywhere in the codebase or application.
  - No emojis in HTML markup, navigation bars, buttons, page titles, section headings, or tooltips.
  - No emojis in Chart.js legends, axis titles, or tooltips.
  - No emojis in Python script strings, log outputs, or error messages.
  - No emojis in documentation (`README.md`, `Agents.md`, markdown artifacts), commit messages, or PR descriptions.
- **Iconography**: Use clean, semantic text labels, standard typography, or inline SVG icons when visual indicators are needed.

---

## 2. Typography & Lo-Fi Monochrome Design

- **Primary Monospace Font**:
  - The primary typeface for all applications (`index.html`, `map.html`, `report.html`) must be `JetBrains Mono`.
  - Body text, navigation elements, KPI cards, buttons, dropdowns, inputs, data tables, and chart labels must use monospace typography.
- **Lo-Fi Black & White Aesthetic**:
  - A clean, technical, lo-fi aesthetic with 1px borders and high contrast.
  - Browser-default light/dark mode detected via `prefers-color-scheme` with manual toggle button in navigation (`[Theme: Light]` / `[Theme: Dark]`) persisted in `localStorage`.
- **Keyword Colorization**:
  - Stream names in body text, metrics, badges, and tables must be color-coded consistently:
    - **Trash**: Red (`#dc2626` / `#ef4444`, CSS class `.kw-trash`)
    - **Recycling**: Green (`#16a34a` / `#22c55e`, CSS class `.kw-recycle`)
    - **Combined / All 311**: Blue (`#2563eb` / `#38bdf8`, CSS class `.kw-combined`)

---

## 3. Map Cartography & Single-Hue Choropleths

- **Local Basemap Tiles (`tiles/light/` & `tiles/blacklite/`)**:
  - Basemap tiles are Stamen Toner, hosted on Stadia Maps, downloaded and stored locally.
  - **Light Mode**: Uses native `stamen_toner` tiles (`tiles/light/{z}/{x}/{y}.png`).
  - **Dark Mode**: Uses native `stamen_toner_blacklite` tiles (`tiles/blacklite/{z}/{x}/{y}.png`).
  - Tiles are strictly subsetted to the District of Columbia boundary polygon for Zooms 11 through 15 (351 tiles per variant, ~8 MB each).
- **Single-Hue Relative Intensity Color Ramps**:
  - Choropleth fills must use single-hue intensity gradients (light tint to deep dark shade) rather than multi-hue spectral scales:
    - **Trash Stream**: Light red (`#fecaca`) to deep crimson (`#7f1d1d`).
    - **Recycling Stream**: Light green (`#bbf7d0`) to deep forest green (`#14532d`).
    - **Combined Stream**: Light blue (`#bfdbfe`) to deep navy blue (`#172554`).
- **Permanent Ward Boundaries**:
  - Ward boundaries must remain permanently visible on the map with crisp contrast and dashed outlines (`#7c3aed` / `#c084fc`) at all times.
- **Dual Analytic Period Toggle**:
  - The map supports switching between **180-Day** (default) and **30-Day** analysis windows with instantaneous choropleth and inspector metric updates.
- **Census TIGERweb Fallback**:
  - A commented-out configuration block for U.S. Census Bureau TIGERweb transportation and hydrography tile layers must be preserved in `map.html` and `scripts/build_page.py` for contingency use.

---

## 4. Vendored Third-Party Dependencies

- **Local Storage (`assets/vendor/`)**: To ensure complete offline capability and prevent runtime external CDN failures or tracking dependencies, all client-side JavaScript and CSS libraries must be stored locally in `assets/vendor/`.
- **Footprint Budget**: Total vendored script and style payload must remain strictly below 5 MB.
- **Current Vendored Libraries**:
  - `Leaflet` (v1.9.4): Mapping engine (`assets/vendor/leaflet/`)
  - `Chart.js` (v4.4.1): Charting library (`assets/vendor/chartjs/`)
  - `jsPDF` (v2.5.1): Client-side PDF generation (`assets/vendor/jspdf/`)
  - `html2canvas` (v1.4.1): Canvas capture for static exports (`assets/vendor/html2canvas/`)
  - `jsPDF-AutoTable` (v3.8.2): Table formatting for PDF exports (`assets/vendor/jspdf-autotable/`)
- **Maintenance**: Automated agents or maintainers updating these libraries in future revisions must verify compatibility, test offline loading, and record version bumps in this document.

---

## 5. Paper Standards & Clean UI

- **US Letter Under the Hood**: All exportable reports, printable views, and generated PDFs must conform strictly to standard American paper dimensions:
  - **US Letter**: 8.5 in x 11.0 in (215.9 mm x 279.4 mm).
  - Do NOT use international A4 (8.27 in x 11.69 in).
  - `@media print` stylesheets must explicitly specify `@page { size: letter portrait; margin: 0.5in; }` or `letter landscape`.
- **Silent Defaults (No UI Sizing Mentions)**:
  - Do not clutter user-facing UI elements, button labels, badges, or headers with paper size mentions (e.g., use "Print Report" rather than "Print (US Letter)"). US Letter is the default standard and operates silently.

---

## 6. Target Audience & Operational Grounding

- **Primary Audience**: DC Department of Public Works (DPW), specifically the Solid Waste Management Administration (SWMA), route supervisors, and data analytics teams.
- **Operational Proof of Concept**: The application acts as a technical proof-of-concept for route optimization and recurrence tracking, ready for manual review and operational extension.
- **Oversight Grounding**: Analysis integrates DPW's official definition of chronic misses (4 misses in 5 consecutive weeks), route workload balancing (Phase 2 Route Re-Optimization), alley obstruction factors, and the active Office of the District of Columbia Auditor (ODCA) timeliness audit.

---

## 7. Application Architecture

The repository serves three dedicated applications without backward-compatibility bloat:
1. `index.html`: Central portal and executive hub displaying citywide KPIs and directing users to the map and operational report.
2. `map.html`: Dedicated, full-viewport interactive map explorer with cascading Ward/ANC/SMD filters, period toggle, and contextual SMD export.
3. `report.html`: Dedicated operational report with hierarchical Ward, ANC, and SMD sections plus DPW route performance analysis and searchable matrix.

Legacy duplicate files (`dc_missed_collection_map.html` and `routes.html`) are deprecated and deleted.

---

## 8. Data Pipeline & Zero External Infrastructure

- All pipeline scripts in `scripts/` must rely solely on the Python 3 standard library (`urllib`, `json`, `datetime`, `collections`, `os`, `sys`, `time`, `math`).
- Do not introduce Python pip dependencies (e.g. `pandas`, `requests`, `geopandas`) to maintain automated compatibility with zero-setup GitHub Actions runners.
