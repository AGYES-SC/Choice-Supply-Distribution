"""
Normalizes and consolidates the per-state private-school files into a single
indexed dataset consumed by build_map.py.

Output:
  data/schools_all.json  -> {"<STATE_ABBR>": [ {record}, ... ], ...}
  data/manifest.json     -> lightweight index of states, counts, sources
  data/profiles/national_profile.json -> refreshes the `schools` block only

TWO COUNTS, DELIBERATELY DIFFERENT (both are reported, never silently mixed):
  * DIRECTORY schools - the state's private-school directory (NCES or the
    state's own). This is the citable "how many private schools are there"
    figure, and the basis for every demographic breakdown and seat total.
  * MAP POINTS - directory schools PLUS the program-only extras: schools that
    appear in a program's own by-school table but not in the state directory,
    geocoded by name+city and shown on the map as approximate program-only
    dots (ids prefixed `moesa`/`arefa`; see build_mo_program.py /
    build_ar_program.py). They carry program participation but are not part of
    the directory, so counting them as directory schools would double-report
    the state's private-school universe.
Nationally: 15,852 directory + 41 program-only extras = 15,893 map points.

The national `schools` block is recomputed here rather than in each
build_<state>_program.py, because only this script sees every state at once -
the per-state scripts each refreshed `national_profile['access']` but left
`national_profile['schools']` untouched, which silently froze that block (and
its religion/level/coed breakdowns) at whatever the state roster was the last
time it happened to be written by hand.

Every record is emitted with the SAME keys in the SAME order, canonical
enum values, an always-present `enroll_source`, and a `state` field:

  id, name, address, city, zip, state, level, type, relig, coed,
  enroll, enroll_source, geo_method, lon, lat

Canonical vocab (values outside these collapse to 'Not reported'):
  level : Elementary | Secondary | Combined | Not reported
  relig : Catholic | Other religious | Nonsectarian | Not reported
  coed  : Coed | All-female | All-male | Not reported
Note: `type` is left as each source reports it (NCES school-type categories
for most states; Indiana's directory reports an instruction mode -
In-Person/Hybrid/Virtual - in this field instead).
"""
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCH_DIR = os.path.join(ROOT, 'data', 'schools')
PROF = os.path.join(ROOT, 'data', 'profiles')

LEVELS = {'Elementary', 'Secondary', 'Combined'}
RELIG = {'Catholic', 'Other religious', 'Nonsectarian'}
COED = {'Coed', 'All-female', 'All-male'}
KEYS = ['id', 'name', 'address', 'city', 'zip', 'state', 'level', 'type',
        'relig', 'coed', 'enroll', 'enroll_source', 'geo_method', 'lon', 'lat']

# id prefixes of program-only extras (in a program's by-school table, absent
# from the state directory) - excluded from every directory-basis count.
PROGRAM_ONLY_PREFIXES = ('moesa', 'arefa')
# geocodes that resolved to a city/zip/town centroid rather than a street
# address (same set as build_ar_program.py / build_mo_program.py)
APPROX = {'nominatim_fallback', 'zcta_centroid_fallback', 'nominatim_zip_fallback',
          'nominatim_town_fallback', 'nominatim_efa_lookup'}


def is_directory(rec):
    return not str(rec.get('id', '')).startswith(PROGRAM_ONLY_PREFIXES)


def _hist(recs, key):
    counts = {}
    for r in recs:
        counts[r.get(key) or 'Not reported'] = counts.get(r.get(key) or 'Not reported', 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


def _abbr(path):
    base = os.path.basename(path).replace('schools_', '').replace('_final.json', '')
    return base.replace('_choice', '').upper()


def normalize(rec, abbr):
    out = {k: rec.get(k) for k in KEYS}
    out['state'] = abbr
    out['level'] = rec.get('level') if rec.get('level') in LEVELS else 'Not reported'
    out['relig'] = rec.get('relig') if rec.get('relig') in RELIG else 'Not reported'
    out['coed'] = rec.get('coed') if rec.get('coed') in COED else 'Not reported'
    out['type'] = rec.get('type') or 'Not reported'
    if 'enroll_source' not in rec:
        out['enroll_source'] = 'state_directory' if rec.get('enroll') is not None else None
    if rec.get('boost'):  # MD: BOOST voucher participation (students + award $) on this school
        out['boost'] = rec['boost']
    if rec.get('scholarship'):  # MO: MOScholars funds ($) received by this school
        out['scholarship'] = rec['scholarship']
    if rec.get('efa'):  # AR: LEARNS EFA participation (EFA + total enrollment) at this school
        out['efa'] = rec['efa']
    return out


def consolidate():
    profiles = json.load(open(os.path.join(PROF, 'state_profiles_by_abbr.json')))
    all_schools, manifest = {}, []
    for path in sorted(glob.glob(os.path.join(SCH_DIR, 'schools_*_final.json'))):
        abbr = _abbr(path)
        recs = [normalize(r, abbr) for r in json.load(open(path))]
        all_schools[abbr] = recs
        prof = profiles.get(abbr, {})
        n_dir = sum(1 for r in recs if is_directory(r))
        manifest.append({
            'abbr': abbr,
            'name': prof.get('name', abbr),
            'schools': n_dir,               # directory schools (the citable count)
            'mapPoints': len(recs),         # directory + program-only extras (what the map draws)
            'programExtras': len(recs) - n_dir,
            'program': bool(prof.get('program') or prof.get('programs')),
            'schoolsSource': (prof.get('schools') or {}).get('sourceLabel', 'NCES directory'),
        })
    json.dump(all_schools, open(os.path.join(ROOT, 'data', 'schools_all.json'), 'w'), indent=1)
    json.dump({'states': sorted(manifest, key=lambda m: m['abbr']),
               'totalStates': len(manifest),
               'totalSchools': sum(m['schools'] for m in manifest),
               'totalMapPoints': sum(m['mapPoints'] for m in manifest),
               'totalProgramExtras': sum(m['programExtras'] for m in manifest)},
              open(os.path.join(ROOT, 'data', 'manifest.json'), 'w'), indent=2)
    return all_schools, manifest


def recompute_national_schools(all_schools):
    """Rewrites national_profile['schools'], plus the two school-derived fields
    of ['access'] (schools, seats), from every state's records - so the national
    drawer can never drift out of sync with the state roster. It previously did,
    twice over: `schools` was stale by one whole state (Maryland), and
    `access.seats` was stale by one enrichment pass (the NCES enrollment
    backfill), because each build_<state>_program.py wrote them from whatever
    schools_all.json happened to look like when that state was last built.
    Everything here is on the DIRECTORY basis; program-only extras are reported
    alongside rather than folded in."""
    nat = json.load(open(os.path.join(PROF, 'national_profile.json')))
    recs = [r for v in all_schools.values() for r in v]
    dirs = [r for r in recs if is_directory(r)]
    with_enroll = [r for r in dirs if r.get('enroll') is not None]

    src = lambda name: sum(1 for r in dirs if r.get('enroll_source') == name)
    nat['schools'] = {
        'count': len(dirs),
        'approx': sum(1 for r in dirs if r.get('geo_method') in APPROX),
        'stateCount': len(all_schools),
        'religion': _hist(dirs, 'relig'),
        'level': _hist(dirs, 'level'),
        'coed': _hist(dirs, 'coed'),
        'totalEnrollment': sum(r['enroll'] for r in with_enroll),
        'schoolsWithEnrollment': len(with_enroll),
        'sourceLabel': 'NCES + state directories',
        'seatsStateReported': src('state_directory'),
        'seatsNces': src('nces_2023_24'),
        # seats taken from a program's own by-school table (AR EFA) - neither
        # directory nor NCES, so it needs its own bucket for the four seat
        # buckets to still reconcile to `count`.
        'seatsProgramReported': len(with_enroll) - src('state_directory') - src('nces_2023_24'),
        'schoolsNoSeats': len(dirs) - len(with_enroll),
        # the map draws these too; they are program participants geocoded from a
        # by-school table, not part of any state's private-school directory.
        'programOnlyExtras': len(recs) - len(dirs),
        'mapPoints': len(recs),
    }
    nat['access']['schools'] = nat['schools']['count']
    nat['access']['seats'] = nat['schools']['totalEnrollment']
    nat['access']['seatsCoveragePct'] = round(100 * len(with_enroll) / len(dirs)) if dirs else None

    buckets = sum(nat['schools'][k] for k in
                  ('seatsStateReported', 'seatsNces', 'seatsProgramReported', 'schoolsNoSeats'))
    assert buckets == len(dirs), f'seat buckets {buckets} != directory schools {len(dirs)}'
    assert nat['schools']['count'] == sum(1 for r in recs if is_directory(r))
    json.dump(nat, open(os.path.join(PROF, 'national_profile.json'), 'w'), indent=2)
    return nat


if __name__ == '__main__':
    all_schools, manifest = consolidate()
    extras = sum(m['programExtras'] for m in manifest)
    print(f'Consolidated {len(manifest)} states, '
          f'{sum(m["schools"] for m in manifest):,} directory schools '
          f'+ {extras} program-only extras = '
          f'{sum(m["mapPoints"] for m in manifest):,} map points -> data/schools_all.json')
    print('Wrote data/manifest.json')
    s = recompute_national_schools(all_schools)['schools']
    print(f'National schools block: {s["count"]:,} directory schools across '
          f'{s["stateCount"]} states, {s["approx"]:,} approx-geocoded, '
          f'{s["totalEnrollment"]:,} seats -> data/profiles/national_profile.json')
