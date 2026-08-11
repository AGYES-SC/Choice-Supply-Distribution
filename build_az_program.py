"""
Builds Arizona's two ESA choropleth layers from the quarterly ESA reports and
updates AZ's profile + the national aggregate.

Each fiscal year is represented by ONE quarter - its last available one - not
by a sum of its quarters, because Arizona's quarterly reports restate the
program's current enrollment each quarter rather than reporting that quarter's
new sign-ups. See extract_az_esa_zips.py for the evidence and the arithmetic;
in short, the previous summed figures (FY2024 287,551 / FY2026 295,918) counted
most students up to four times, against true levels of 74,578 and 102,891.

Layers:
  data/geojson/az_zip.geojson        FY2024, year-end (Q4)      -> 74,578
  data/geojson/az_zip_fy2026.geojson FY2026, as of Q3 (partial) -> 102,891

Each feature carries `total` (that year's level) plus `q1`..`q4` (the within-year
trajectory, for the tooltip - these are levels at successive points in time and
must never be added together).

Only FY2026 - the most current period - enters the national total; FY2024 stays
on the map as a separate toggleable layer for comparison, not double-counted.

Unit is STUDENTS, per the reports' own headings ("Section 1: Number of ESA
students...", "Table 7: Number of students enrolled in ESA program by zip code").

Run: build_az_program -> compute_acs_access -> build_map.
Needs tl_2024_us_zcta520.zip at the repo root (~530MB, not committed; see README).
"""
import json
import os
import sys

import numpy as np
from shapely.geometry import Point, shape
from shapely.prepared import prep

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extract_az_esa_zips import QUARTERS_FY2024, QUARTERS_FY2026, fiscal_year_totals
from match_to_shapefile import match_zctas

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROF = os.path.join(ROOT, 'data', 'profiles')
GEO = os.path.join(ROOT, 'data', 'geojson')
SCH = os.path.join(ROOT, 'data', 'schools')
ZCTA = os.path.join(ROOT, 'tl_2024_us_zcta520.zip')

# (fiscal year, quarter set, output file, profile label, sources.json key, counts nationally)
YEARS = [
    ('FY2024', QUARTERS_FY2024, 'az_zip.geojson',
     'ESA students (FY2024, year-end Q4)', 'AZ', False),
    ('FY2026', QUARTERS_FY2026, 'az_zip_fy2026.geojson',
     'ESA students (FY2026, as of Q3, partial year)', 'AZ_FY2026', True),
]
UNIT = 'students'


def build_layer(year_label, quarters, out_name):
    """Extracts the year's zip table, joins it to ZCTA polygons and writes the
    layer. Returns (geojson, totals, by_quarter, last_label, unmatched)."""
    totals, by_quarter, last = fiscal_year_totals(quarters, year_label, base_dir=ROOT)

    rows = [{'zip': z, 'total': n} for z, n in sorted(totals.items())]
    geo, unmatched = match_zctas(ZCTA, rows, name_key='zip', value_key='total')

    # match_zctas emits a generic {zip, name, students}; this layer's schema is
    # {zip, total, q1..qN} - `total` is the year's level, the quarters are the
    # trajectory behind it.
    for f in geo['features']:
        zc = f['properties']['zip']
        props = {'zip': zc, 'total': f['properties']['students']}
        for q in sorted(by_quarter):
            if zc in by_quarter[q]:
                props[q.lower()] = by_quarter[q][zc]
        f['properties'] = props

    geo['features'].sort(key=lambda f: f['properties']['zip'])
    json.dump(geo, open(os.path.join(GEO, out_name), 'w'))
    return geo, totals, by_quarter, last, unmatched


def _corr(x, y, rank=False):
    if rank:
        x, y = _ranks(x), _ranks(y)
    if len(x) < 2 or not np.std(x) or not np.std(y):
        return None
    return round(float(np.corrcoef(x, y)[0, 1]), 2)


def _ranks(v):
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    for pos, i in enumerate(order):
        r[i] = float(pos)
    return r


def build_access(geo, participation, unit_label):
    """Supply-vs-demand for AZ: ESA participation per zip against private-school
    seats in that zip. Basis is the FY2024 layer - the last COMPLETE fiscal year,
    which is also the vintage the ACS 2024 5-year denominators in
    compute_acs_access.py are matched to. (The national headline uses the more
    current FY2026 partial year; both are labelled with their period.)

    Seats are joined by point-in-polygon rather than by the school's printed zip
    string, matching every other program state's method."""
    schools = json.load(open(os.path.join(SCH, 'schools_az_final.json')))
    with_seats = [s for s in schools if s.get('enroll') is not None]

    polys = [{'val': float(f['properties']['total']),
              'prep': prep(shape(f['geometry'])), 'seats': 0} for f in geo['features']]
    for s in with_seats:
        pt = Point(s['lon'], s['lat'])
        for p in polys:
            if p['prep'].covers(pt):
                p['seats'] += s['enroll']
                break

    seats = sum(s['enroll'] for s in with_seats)
    n = len(schools)
    no_supply = [p for p in polys if p['val'] > 0 and p['seats'] == 0]
    corr = _corr([p['val'] for p in polys], [p['seats'] for p in polys])
    pps = round(participation / seats, 2) if seats else None
    return {
        'hasProgram': True, 'schools': n, 'seats': seats, 'schoolsWithSeats': len(with_seats),
        'seatsCoveragePct': round(100 * len(with_seats) / n) if n else None,
        'seatsPerSchool': round(seats / len(with_seats)) if with_seats else None,
        'participation': participation, 'unit': unit_label,
        'areaUnit': 'zip code', 'areas': len(polys),
        'participantsPerSeat': pps, 'participantsPerSchool': round(participation / n) if n else None,
        'areasNoSupply': len(no_supply),
        'pctPartNoSupply': round(100 * sum(p['val'] for p in no_supply) / participation) if participation else None,
        'corr': corr, 'corrStrength': ('strong' if corr and abs(corr) >= 0.7 else
                                       'moderate' if corr and abs(corr) >= 0.4 else 'weak'),
        'spearman': _corr([p['val'] for p in polys], [p['seats'] for p in polys], rank=True),
        'capacitySignal': ('program use is far below private-school capacity' if pps and pps < 0.5 else
                           'program use is roughly balanced with private-school capacity' if pps and pps < 1.2 else
                           'demand exceeds local private-school capacity — much of the program is used '
                           'outside brick-and-mortar private schools (home, micro, or online)'),
    }


def build_profiles(layers):
    profiles = json.load(open(os.path.join(PROF, 'state_profiles_by_abbr.json')))
    programs = []
    for year_label, geo, totals, last, unmatched, label, source_key, _national in layers:
        feats = geo['features']
        with_part = [f for f in feats if f['properties']['total'] > 0]
        top = max(feats, key=lambda f: f['properties']['total'])
        programs.append({
            'label': label,
            'total': sum(f['properties']['total'] for f in feats),
            'unit': UNIT,
            'areaCount': len(with_part),
            'areaLabel': 'zip code',
            'topName': top['properties']['zip'],
            'topValue': top['properties']['total'],
            'sourceKey': source_key,
            # reported statewide vs. what landed on the map (zips with no ZCTA polygon)
            'reportedTotal': sum(totals.values()),
            'unmappedAreas': len(unmatched),
        })
    profiles['AZ']['programs'] = programs

    # Access analysis is anchored to the last complete fiscal year (FY2024).
    # compute_acs_access.py then layers the ACS per-child metrics on top of the
    # same layer, so every number in the drawer describes one period.
    base_year, base_geo = next((y, g) for y, g, *_ in layers if y == 'FY2024')
    base = next(p for p in programs if p['sourceKey'] == 'AZ')
    prior = profiles['AZ'].get('access', {})
    access = build_access(base_geo, base['total'], f'ESA students ({base_year}, year-end)')
    # keep the ACS-derived fields compute_acs_access.py owns; it reruns after this
    for k in ('schoolAgePop', 'popCoveragePct', 'takeUpRatePct', 'seatsPer1000Kids',
              'acsPrivatePct', 'pctChildrenInDesert', 'accessGini', 'rateCorr'):
        if k in prior:
            access[k] = prior[k]
    profiles['AZ']['access'] = access

    json.dump(profiles, open(os.path.join(PROF, 'state_profiles_by_abbr.json'), 'w'), indent=2)
    return profiles


def recompute_national(profiles):
    """AZ contributes its most current period (FY2026) to the national total."""
    nat = json.load(open(os.path.join(PROF, 'national_profile.json')))
    current = next(p for p in profiles['AZ']['programs'] if p['sourceKey'] == 'AZ_FY2026')
    bd = [e for e in nat['programBreakdown'] if e['abbr'] != 'AZ']  # idempotent
    bd.append({'abbr': 'AZ', 'name': 'Arizona', 'total': current['total'],
               'unit': current['unit'], 'label': current['label']})
    bd.sort(key=lambda e: -e['total'])
    nat['programBreakdown'] = bd
    nat['totalParticipation'] = sum(e['total'] for e in bd)
    nat['access']['programStates'] = len(bd)
    json.dump(nat, open(os.path.join(PROF, 'national_profile.json'), 'w'), indent=2)
    return nat


if __name__ == '__main__':
    layers = []
    for year_label, quarters, out_name, label, source_key, national in YEARS:
        geo, totals, by_quarter, last, unmatched = build_layer(year_label, quarters, out_name)
        mapped = sum(f['properties']['total'] for f in geo['features'])
        naive = sum(sum(d.values()) for d in by_quarter.values())
        print(f'{out_name}: {len(geo["features"])} zips, {mapped:,} students '
              f'(from {last}; {sum(totals.values()):,} reported, {len(unmatched)} zips '
              f'with no ZCTA polygon). Summing quarters would have said {naive:,}.')
        layers.append((year_label, geo, totals, last, unmatched, label, source_key, national))

    profiles = build_profiles(layers)
    for p in profiles['AZ']['programs']:
        print(f'  AZ profile: {p["label"]} -> {p["total"]:,} {p["unit"]} '
              f'across {p["areaCount"]} zips (top {p["topName"]}: {p["topValue"]:,})')
    nat = recompute_national(profiles)
    az = next(e for e in nat['programBreakdown'] if e['abbr'] == 'AZ')
    print(f'National: {nat["totalParticipation"]:,} across '
          f'{nat["access"]["programStates"]} programs (AZ contributes {az["total"]:,})')
