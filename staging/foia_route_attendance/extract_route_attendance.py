"""
One-time extraction of the DPW FOIA "Trash / Recycling Route Attendance Summary"
PDF (2026-01-02 to 2026-09-30) into structured CSV/JSON.

STAGING ONLY: this script is not part of the scripts/ data pipeline and is not
run by GitHub Actions. Unlike scripts/, it requires one third-party package
(pdfplumber) because the source was delivered as an Excel-printed PDF:

    python3 -m venv .venv && .venv/bin/pip install pdfplumber
    .venv/bin/python staging/foia_route_attendance/extract_route_attendance.py

Layout notes (verified against every page of the source):
  - Each page holds two independent tables side by side: Trash (left half,
    x < 320pt) and Recycling (right half). Only the trash side has a row "#".
  - Header columns are "# Employees", "In Late", "Out-Total", "Out-Sick",
    "Out-Other". "In Late" is ONE column (late arrivals); there is no
    "In"/reported-total column, so in_total_count is derived as
    employed_count - out_total_count.
  - Blank cells mean zero (Excel zero-suppressed formatting).
  - Numbers are centered in each column; tokens are assigned to the column
    whose center is nearest.
"""

import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime

import pdfplumber

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SRC_PDF = os.path.join(HERE, 'source', 'FOIA_Request_-_Trash__Recycling_Route_TA__1-1-1-26_to_9-30-26_.pdf')

SPLIT_X = 320.0
# Column centers (pt) derived from header text extents and value positions.
COLS = {
    'trash': {'employed_count': 142.0, 'in_late_count': 181.0, 'out_total_count': 216.0,
              'out_sick_count': 254.0, 'out_other_count': 292.0},
    'recycling': {'employed_count': 432.0, 'in_late_count': 472.0, 'out_total_count': 506.0,
                  'out_sick_count': 544.0, 'out_other_count': 582.0},
}
MAX_COL_DIST = 12.0
HEADER_BOTTOM = 55.0
FOOTER_TOP = 740.0

DATE_RE = re.compile(r'^\d{1,2}-[A-Z][a-z]{2}-\d{2}$')
ROWNUM_RE = re.compile(r'^\d{1,3}(,\d{3})*$')
# e.g. O301-4, T601-1, TTSP10-4, TOSP30-3, RO326-(A)4, RT613-(B)4, RSP40-4, MC-1, SP-3
ROUTE_RE = re.compile(r'^(?P<base>[A-Z]+\d*)-(?:\((?P<variant>[A-Z])\))?(?P<day>\d)$')

NUM_FIELDS = ['employed_count', 'in_late_count', 'out_total_count', 'out_sick_count', 'out_other_count']
WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


def parse_date(s):
    return datetime.strptime(s, '%d-%b-%y').date()


# RouteNo prefix -> (stream implied by the route name, category label).
# The source tables are NOT perfectly segregated: recycling-named routes
# (RO/RT/RSP) appear in the trash table (mostly February) and a few trash
# special routes (TTSP/TOSP) appear in the recycling table. The table a row
# came from is kept as trash_or_recycling; the name-implied stream is kept
# separately as route_name_stream. Meanings of MC/SP/Admin/Float/ABSENCE are
# not documented in the FOIA response; labels are descriptive only.
PREFIXES = {
    'O': ('trash', 'outer_ring'), 'T': ('trash', 'inner_city'),
    'TTSP': ('trash', 'inner_city_sp'), 'TOSP': ('trash', 'outer_ring_sp'),
    'RO': ('recycling', 'outer_ring'), 'RT': ('recycling', 'inner_city'),
    'RSP': ('recycling', 'sp'),
    'MC': ('', 'mc_unlabeled'), 'SP': ('', 'sp_unlabeled'),
}


def classify_route(base):
    if not base:
        return '', 'non_route'
    return PREFIXES.get(re.match(r'^([A-Z]+)', base).group(1), ('', 'unknown'))


def group_lines(words):
    lines = defaultdict(list)
    for w in words:
        if w['top'] < HEADER_BOTTOM or w['top'] > FOOTER_TOP:
            continue
        key = round(w['top'] * 2) / 2
        # merge with an existing line within 2pt
        for k in list(lines):
            if abs(k - key) <= 2:
                key = k
                break
        lines[key].append(w)
    return [sorted(lines[k], key=lambda w: w['x0']) for k in sorted(lines)]


def parse_half(words, stream, page_no, line_top, issues):
    """words: tokens from one half of one line."""
    if not words:
        return None
    toks = list(words)
    src_row = None
    if stream == 'trash' and ROWNUM_RE.match(toks[0]['text']) and toks[0]['x1'] < 30:
        src_row = int(toks.pop(0)['text'].replace(',', ''))
    if not toks or not DATE_RE.match(toks[0]['text']):
        issues.append(f'p{page_no} y{line_top:.0f} {stream}: no date in {[w["text"] for w in words]}')
        return None
    date_tok = toks.pop(0)
    route_tok = toks.pop(0)
    rec = {
        'date': parse_date(date_tok['text']).isoformat(),
        'route_name': route_tok['text'],
        'trash_or_recycling': stream,
        **{f: 0 for f in NUM_FIELDS},
        'source_page': page_no,
        'source_row_number': src_row,
        'notes': '',
    }
    notes = []
    for w in toks:
        cx = (w['x0'] + w['x1']) / 2
        if not w['text'].isdigit():
            notes.append(f'non-numeric token "{w["text"]}" in count columns')
            # find column for reporting purposes
            continue
        col, dist = min(((c, abs(cx - x)) for c, x in COLS[stream].items()), key=lambda t: t[1])
        if dist > MAX_COL_DIST:
            issues.append(f'p{page_no} y{line_top:.0f} {stream}: token {w["text"]} at x{cx:.1f} unassigned')
            continue
        if rec[col]:
            issues.append(f'p{page_no} y{line_top:.0f} {stream}: duplicate value for {col}')
        rec[col] = int(w['text'])
    rec['notes'] = '; '.join(notes)
    return rec


def extract():
    issues = []
    rows = []
    with pdfplumber.open(SRC_PDF) as pdf:
        n_pages = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            page_no = i + 1
            for line in group_lines(page.extract_words()):
                left = [w for w in line if w['x0'] < SPLIT_X]
                right = [w for w in line if w['x0'] >= SPLIT_X]
                top = line[0]['top']
                for half, stream in ((left, 'trash'), (right, 'recycling')):
                    rec = parse_half(half, stream, page_no, top, issues)
                    if rec:
                        rec['_y'] = top
                        rows.append(rec)
    return rows, issues, n_pages


def enrich(rows):
    # Order within stream preserved from document (page, then y)
    for stream in ('trash', 'recycling'):
        seq = 0
        for r in rows:
            if r['trash_or_recycling'] == stream:
                seq += 1
                r['source_sequence'] = seq
    rows.sort(key=lambda r: (r['trash_or_recycling'] != 'trash', r['source_sequence']))

    dup_counter = Counter((r['date'], r['route_name'], r['trash_or_recycling']) for r in rows)
    dup_index = Counter()
    for r in rows:
        key = (r['date'], r['route_name'], r['trash_or_recycling'])
        dup_index[key] += 1
        r['crew_line_index'] = dup_index[key]
        r['crew_lines_for_route_day'] = dup_counter[key]

        m = ROUTE_RE.match(r['route_name'])
        if m:
            r['route_base'] = m.group('base')
            r['route_variant'] = m.group('variant') or ''
            r['route_day_code'] = int(m.group('day'))
        else:
            r['route_base'] = ''
            r['route_variant'] = ''
            r['route_day_code'] = ''
        r['route_name_stream'], r['route_category'] = classify_route(r['route_base'])
        d = datetime.strptime(r['date'], '%Y-%m-%d').date()
        r['weekday'] = WEEKDAYS[d.weekday()]
        r['in_total_count'] = r['employed_count'] - r['out_total_count']

        flags = []
        if r['out_total_count'] != r['out_sick_count'] + r['out_other_count']:
            flags.append('out_total_ne_sick_plus_other')
        if r['in_total_count'] < 0:
            flags.append('negative_in_total')
        if r['in_late_count'] > max(r['in_total_count'], 0):
            flags.append('late_exceeds_in_total')
        if r['employed_count'] == 0:
            flags.append('zero_employed')
        if r['notes']:
            flags.append('non_numeric_token')
        if r['route_category'] in ('non_route', 'unknown'):
            flags.append('non_route_label')
        if r['route_name_stream'] and r['route_name_stream'] != r['trash_or_recycling']:
            flags.append('table_route_prefix_mismatch')
        r['_flags'] = flags
        r.pop('_y', None)

    # Same date + route_name listed in BOTH tables (possible double entry)
    by_key = defaultdict(set)
    for r in rows:
        by_key[(r['date'], r['route_name'])].add(r['trash_or_recycling'])
    for r in rows:
        if len(by_key[(r['date'], r['route_name'])]) > 1:
            r['_flags'].append('listed_in_both_tables')
        r['qa_flags'] = '|'.join(r.pop('_flags'))
    return rows


def load_gis_ids():
    def ids(path, prop):
        with open(path, encoding='utf-8') as f:
            return {feat['properties'][prop] for feat in json.load(f)['features']}
    return (ids(os.path.join(REPO, 'data', 'dc_trash_routes.geojson'), 'TrashRouteArea'),
            ids(os.path.join(REPO, 'data', 'dc_recycle_routes.geojson'), 'Route'))


def crosswalk(rows):
    """Heuristic map from FOIA RouteNo to the GIS route ids used elsewhere in
    the repo. Trash GIS ids carry no day code (OR301, IC601); recycling GIS
    ids do (R419_3B, RSP40_4)."""
    trash_ids, rec_ids = load_gis_ids()
    trash_prefix = {'O': 'OR', 'T': 'IC', 'TTSP': 'IC', 'TOSP': 'OR'}
    out = {}
    for r in rows:
        key = r['route_name']
        if key in out:
            continue
        base, var, day = r['route_base'], r['route_variant'], r['route_day_code']
        stream = r['route_name_stream']
        gis, method = '', 'no_match'
        if base:
            m = re.match(r'^([A-Z]+)(\d*)$', base)
            pfx, num = m.group(1), m.group(2)
            if stream == 'trash':
                if pfx in trash_prefix and num:
                    cand = trash_prefix[pfx] + num
                    if cand in trash_ids:
                        gis, method = cand, 'exact'
            elif stream == 'recycling':
                if num and pfx in ('RO', 'RT'):
                    stem = f'R{num}_{day}'
                elif num and pfx == 'RSP':
                    stem = f'RSP{num}_{day}'
                else:
                    stem = None
                if stem:
                    if stem + var in rec_ids:
                        gis, method = stem + var, 'exact'
                    elif var and stem in rec_ids:
                        gis, method = stem, 'gis_has_no_variant'
                    elif not var and any(i.startswith(stem) and len(i) == len(stem) + 1 for i in rec_ids):
                        gis = '|'.join(sorted(i for i in rec_ids if i.startswith(stem) and len(i) == len(stem) + 1))
                        method = 'gis_split_into_variants'
        out[key] = {'route_name': key, 'route_name_stream': stream, 'route_base': base,
                    'route_variant': var, 'route_day_code': day, 'route_category': r['route_category'],
                    'gis_route_id': gis, 'match_method': method,
                    'rows_in_trash_table': 0, 'rows_in_recycling_table': 0}
    for r in rows:
        out[r['route_name']][f'rows_in_{r["trash_or_recycling"]}_table'] += 1
    return out


def aggregate(rows):
    agg = {}
    for r in rows:
        key = (r['date'], r['route_name'], r['trash_or_recycling'])
        a = agg.setdefault(key, {'date': key[0], 'route_name': key[1], 'trash_or_recycling': key[2],
                                 **{f: 0 for f in ['employed_count', 'in_total_count'] + NUM_FIELDS[1:]},
                                 'crew_lines': 0, '_flags': set()})
        a['_flags'].update(fl for fl in r['qa_flags'].split('|') if fl)
        for f in ['employed_count', 'in_total_count'] + NUM_FIELDS[1:]:
            a[f] += r[f]
        a['crew_lines'] += 1
    for a in agg.values():
        a['qa_flags'] = '|'.join(sorted(a.pop('_flags')))
    return list(agg.values())


ROW_FIELDS = ['date', 'route_name', 'trash_or_recycling', 'employed_count', 'in_total_count',
              'in_late_count', 'out_total_count', 'out_sick_count', 'out_other_count',
              'weekday', 'route_name_stream', 'route_base', 'route_variant', 'route_day_code',
              'route_category', 'gis_route_id', 'crew_line_index', 'crew_lines_for_route_day',
              'source_page', 'source_row_number', 'source_sequence', 'qa_flags', 'notes']
AGG_FIELDS = ['date', 'route_name', 'trash_or_recycling', 'employed_count', 'in_total_count',
              'in_late_count', 'out_total_count', 'out_sick_count', 'out_other_count',
              'crew_lines', 'route_name_stream', 'gis_route_id', 'qa_flags']


def write_csv(path, fields, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore', lineterminator='\n')
        w.writeheader()
        for r in rows:
            w.writerow({k: ('' if r.get(k) is None else r.get(k)) for k in fields})


def main():
    rows, issues, n_pages = extract()
    rows = enrich(rows)
    xw = crosswalk(rows)
    for r in rows:
        r['gis_route_id'] = xw[r['route_name']]['gis_route_id']
    agg = aggregate(rows)
    for a in agg:
        a['gis_route_id'] = xw[a['route_name']]['gis_route_id']
        a['route_name_stream'] = xw[a['route_name']]['route_name_stream']

    out_dir = os.path.join(HERE, 'output')
    os.makedirs(out_dir, exist_ok=True)
    write_csv(os.path.join(out_dir, 'route_attendance_daily_rows.csv'), ROW_FIELDS, rows)
    write_csv(os.path.join(out_dir, 'route_attendance_daily_by_route.csv'), AGG_FIELDS, agg)
    write_csv(os.path.join(out_dir, 'route_crosswalk.csv'),
              ['route_name', 'route_name_stream', 'route_base', 'route_variant', 'route_day_code',
               'route_category', 'gis_route_id', 'match_method', 'rows_in_trash_table',
               'rows_in_recycling_table'],
              sorted(xw.values(), key=lambda x: (x['route_name_stream'] or 'z', x['route_name'])))
    with open(os.path.join(out_dir, 'route_attendance_daily_rows.json'), 'w', encoding='utf-8') as f:
        json.dump({'metadata': {
            'source_file': os.path.basename(SRC_PDF),
            'source_pages': n_pages,
            'source_prepared': '2026-10-28 by Public Works Solutions; data source SWMA Trak Software System',
            'source_footnote': 'Counts are based on 8 hours recorded by status. Some employees might have '
                               'their not present time assigned to a different activity',
            'derived_fields': {'in_total_count': 'employed_count - out_total_count (no In column in source)'},
            'blank_cells': 'interpreted as 0',
        }, 'rows': [{k: r.get(k) for k in ROW_FIELDS} for r in rows]}, f, indent=1)

    # ---- QA report ----
    rep = []
    by_stream = Counter(r['trash_or_recycling'] for r in rows)
    rep.append(f'pages parsed: {n_pages}')
    rep.append(f'rows: {len(rows)} ({dict(by_stream)})')
    trash_rownums = [r['source_row_number'] for r in rows if r['trash_or_recycling'] == 'trash']
    missing = sorted(set(range(1, max(trash_rownums) + 1)) - set(trash_rownums))
    rep.append(f'trash source row numbers 1..{max(trash_rownums)}; missing: {missing[:20]}; '
               f'duplicates: {[k for k, v in Counter(trash_rownums).items() if v > 1][:20]}')
    for s in ('trash', 'recycling'):
        ds = sorted({r['date'] for r in rows if r['trash_or_recycling'] == s})
        rep.append(f'{s}: dates {ds[0]} .. {ds[-1]}, {len(ds)} distinct dates, '
                   f'{len({r["route_name"] for r in rows if r["trash_or_recycling"] == s})} distinct route_names')
        rep.append(f'{s}: totals ' + str({f: sum(r[f] for r in rows if r['trash_or_recycling'] == s)
                                          for f in ['employed_count', 'in_total_count'] + NUM_FIELDS[1:]}))
    flags = Counter(fl for r in rows for fl in r['qa_flags'].split('|') if fl)
    rep.append(f'qa flag counts: {dict(flags)}')
    rep.append(f'route_day keys with >1 crew line: '
               f'{sum(1 for a in agg if a["crew_lines"] > 1)} of {len(agg)}')
    rep.append(f'crosswalk match methods: {dict(Counter((v["route_name_stream"] or "unlabeled", v["match_method"]) for v in xw.values()))}')
    rep.append('parse issues:')
    rep.extend('  ' + i for i in issues) if issues else rep.append('  none')
    rep.append('flagged rows:')
    for r in rows:
        if r['qa_flags'] and r['qa_flags'] != 'non_route_label':
            rep.append(f'  p{r["source_page"]} {r["trash_or_recycling"]} {r["date"]} {r["route_name"]} '
                       f'emp={r["employed_count"]} late={r["in_late_count"]} out={r["out_total_count"]} '
                       f'sick={r["out_sick_count"]} other={r["out_other_count"]} [{r["qa_flags"]}] {r["notes"]}')
    text = '\n'.join(rep) + '\n'
    with open(os.path.join(out_dir, 'qa_report.txt'), 'w', encoding='utf-8') as f:
        f.write(text)
    print(text)


if __name__ == '__main__':
    sys.exit(main())
