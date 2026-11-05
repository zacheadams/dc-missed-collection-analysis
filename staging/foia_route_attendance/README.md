# FOIA: DPW SWMA Route Attendance, 2026-01-02 to 2026-09-30 (STAGING)

> Status: staging / unanalyzed. Nothing in this folder is linked from, or consumed by,
> `index.html`, `map.html`, `report.html`, `tables.html`, or the `scripts/` pipeline.

## What this is

Daily staffing and attendance counts per DPW Solid Waste Management Administration (SWMA)
trash and recycling route. It was requested under FOIA as structured CSV/JSON but delivered as a
113-page PDF printed from Excel. This folder converts it back into structured data.

Original request:

> A count of the following per day, per recycling route and trash route under DPW SWMA: Staffing
> headcount, report count, late count, total leave count, sick leave count, other leave count.
> Example headers: `date, route_name, trash_or_recycling, employed_count, in_total_count,
> in_late_count, out_total_count, out_sick_count, out_other_count`

Source PDF footer: "Counts are based on 8 hours recorded by status. Some employees might have
their not present time assigned to a different activity. Data Source - SWMA Trak Software System.
Prepared by Public Works Solutions 10/28/2026."

## Files

| Path | Description |
| --- | --- |
| `source/FOIA_Request_...pdf` | Original PDF as received (unmodified) |
| `extract_route_attendance.py` | One-time extractor (needs `pdfplumber`; see below) |
| `output/route_attendance_daily_rows.csv` | One row per line in the PDF (11,935 rows). Requested schema plus provenance and QA columns |
| `output/route_attendance_daily_rows.json` | JSON export of the daily rows with metadata header |
| `output/route_attendance_daily_by_route.csv` | Rows summed to one per `date` + `route_name` + `trash_or_recycling` (10,734 rows) |
| `output/route_crosswalk.csv` | Each FOIA `route_name` mapped (heuristically) to GIS route ids in `data/dc_trash_routes.geojson` / `data/dc_recycle_routes.geojson` |
| `output/qa_report.txt` | Parse checks, totals, and every flagged row |
| `fetch_weather_data.py` | Fetches DC historical temperature and precipitation from Open-Meteo Archive API |
| `data/dc_weather_2026.json` | Daily DC weather observations (April 1 to September 30, 2026) |
| `analyze_hypotheses.py` | Quantitative hypothesis testing engine (attendance, weather, 311 lag) |
| `output/daily_route_attendance_weather_311.csv` | Full joined daily dataset with multi-day lag windows and weather |
| `output/hypothesis_report.html` | Visual HTML hypothesis testing report with interactive Chart.js graphs |

## Columns (`route_attendance_daily_rows.csv`)

| Column | Meaning |
| --- | --- |
| `date` | ISO date |
| `route_name` | `RouteNo` exactly as printed, e.g. `O301-4`, `RO326-(A)4`, `RSP40-4` |
| `trash_or_recycling` | Which table the row was printed in (left = trash, right = recycling) |
| `employed_count` | "# Employees" |
| `in_total_count` | **Derived**: `employed_count - out_total_count`. The PDF has no reported-total column |
| `in_late_count` | "In Late" |
| `out_total_count` / `out_sick_count` / `out_other_count` | "Out-Total" / "Out-Sick" / "Out-Other" |
| `weekday` | Day of week of `date` |
| `route_name_stream` | Stream implied by the route prefix (`O`, `T`, `TTSP`, `TOSP` = trash; `RO`, `RT`, `RSP` = recycling; blank for `MC`, `SP`, and non-route labels) |
| `route_base` / `route_variant` / `route_day_code` | `RO326-(A)4` -> `RO326` / `A` / `4`. Day code is 1 = Mon ... 5 = Fri, the scheduled service day; it can differ from `weekday` during holiday slide weeks |
| `route_category` | Descriptive prefix label (`outer_ring`, `inner_city`, `*_sp`, `mc_unlabeled`, `sp_unlabeled`, `non_route`) |
| `gis_route_id` | Matching id from the repo GIS layers, if found (see crosswalk) |
| `crew_line_index` / `crew_lines_for_route_day` | The same route often has 2+ lines on the same day (likely separate crews or trucks). Index within that group / group size |
| `source_page`, `source_row_number`, `source_sequence` | Provenance. `source_row_number` is the printed "#" (trash table only) |
| `qa_flags` | Pipe-separated, see below |
| `notes` | Parser notes (currently empty) |

## Data caveats to read before analyzing

1. **Blank cells were read as 0.** The source uses zero-suppressed formatting; a handful of rows print explicit `0`s.
2. **No reported (in) count was provided.** The header is "In Late" (one column), not "In" + "Late". `in_total_count` is derived.
3. **Late counts are almost never recorded:** 12 late arrivals total (10 trash, 2 recycling) over 9 months. Treat `in_late_count` as unreliable, not as evidence that crews are punctual.
4. **`out_total_ne_sick_plus_other` (56 rows):** sick + other is greater than out-total in the source. This is consistent with one person splitting an 8-hour day between sick and other leave. Left as printed.
5. **Tables are not cleanly separated by stream:**
   - `table_route_prefix_mismatch` (109 rows): recycling-named routes in the trash table (85 of these fall on 2026-02-02, -03, -13, -17, possibly recycling crews moved to trash during a disruption) and a few `TTSP`/`TOSP` routes in the recycling table. `trash_or_recycling` keeps DPW's table placement; use `route_name_stream` if you want the route's nominal stream.
   - `listed_in_both_tables` (61 rows): same `date` + `route_name` appears in both tables. Some have identical counts (possible double entry). Check these before summing across streams.
6. **Non-route labels** (`non_route_label`, 7 rows): `Admin-BW`, `Float-I`, `ABSENCE`. `MC-n` and `SP-n` routes are unexplained in the response and have no GIS match.
7. **Coverage:** 2026-01-02 to 2026-09-30, weekdays plus 3 Saturday rows. 2026-01-01 (holiday) is absent.
8. **Multiple crew lines:** 1,098 route-days have more than one line. The `daily_by_route` file sums them. Whether these are separate crews or the same crew split is not stated.

## GIS crosswalk

The heuristic used in `route_crosswalk.csv`:
- Trash: `O###` -> `OR###`, `T###` -> `IC###`, `TTSP##` -> `IC##`, `TOSP##` -> `OR##` (the GIS trash ids have no day code).
- Recycling: `RO###-(V)D` / `RT###-(V)D` -> `R###_DV`, `RSP##-D` -> `RSP##_D`.
- `match_method`: `exact`, `gis_has_no_variant` (FOIA splits A/B but GIS does not), `gis_split_into_variants` (GIS has A/B, FOIA does not; all candidates listed with `|`), `no_match`.

Results: trash 170 exact / 9 no match; recycling 118 exact, 22 + 12 partial, 18 no match; 18 `MC`/`SP`/non-route labels unmatched. Review the crosswalk before you join to 311 route stats.

## Re-running

The repo pipeline (`scripts/`) is standard-library only (Agents.md section 9). This extractor sits
outside it and needs `pdfplumber`:

```
python3 -m venv .venv
.venv/bin/pip install pdfplumber
.venv/bin/python staging/foia_route_attendance/extract_route_attendance.py
```

The parser gives each number to a column by its x-position, because blank cells collapse in
plain-text extraction. Checks: all 113 pages parsed, printed trash row numbers 1 to 6,982 are
contiguous with no gaps or duplicates, and no tokens were left unassigned.

## Empirical Hypothesis Testing (`analyze_hypotheses.py`)

Run hypothesis testing using Python 3 standard library:
```bash
python3 staging/foia_route_attendance/analyze_hypotheses.py
```
This joins 7,183 FOIA route-days with 20,184 spatially matched 311 complaints and daily Open-Meteo observations over the 180-day window (2026-04-04 to 2026-09-30). It tests:
- **H1 (Call-Outs & Multi-Day Lag)**: Validates call-out impacts (Lag +1 peak, +46.6% 3-day surge on any leave, +102.3% on >=2 leave).
- **H2 (Crew Resilience)**: Validates small route fragility (9.31x surge on 1-2 person routes vs 1.28x on standard crews).
- **H3 (Day-of-Week Effect)**: Evaluates Monday vs Thursday unreliability (attendance is 16.0% vs 11.0%, but complaint volume is 44% higher on Mondays, driven by weekend accumulation).
- **H4a (Ambient Heat, DoW Controlled)**: Rejects the premise that severe heat waves drove workforce absenteeism. Severe heat (>=95F) happened only on Tue-Fri (never on a Monday); when controlling for day-of-week, leave rate remains -2.6 pp below expected (10.2% adjusted vs 12.9% baseline; OLS fixed-effects beta = -2.30 pp). In the 90-95F range, a modest excess leave (+1.9 pp, p = 0.024) and next-day complaints (+0.15 misses, p = 0.013) were detected.
- **H4b (Precipitation, DoW Controlled)**: Confirms heavy rainfall (>=0.50 in) produces a statistically significant surge in absenteeism even after controlling for day-of-week fixed effects (adjusted leave: 15.8% vs 11.8% dry baseline, excess anomaly +2.9 pp; OLS fixed-effects beta = +3.07 pp, t = +3.65, p = 0.0003).
- **H4c (Compound Interaction, DoW Controlled)**: Confirms synergistic disruption under Hot (>=85F) + Heavy Rain (>=0.50 in) conditions after day-of-week normalization, yielding the highest excess absenteeism anomaly (+3.0 pp, 15.9% adjusted leave) and elevated next-day complaints (0.92 adjusted misses vs 0.68 on Hot + Dry days).

