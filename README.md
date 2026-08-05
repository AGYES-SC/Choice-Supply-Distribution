# School Choice Program Participation — National Map

An interactive, single-file HTML map of K-12 school-choice program
participation (ESAs, tax-credit scholarships, vouchers, correspondence-study
programs) and private-school locations across the United States.

**Open `index.html` in any browser — no server or build step required.**

## What it shows

- **9 states with full program-participation choropleths**, each at that
  program's own reporting geography (zip code, school district, or county):

  | State | Program | Geography | Latest total |
  |---|---|---|---|
  | Arizona | Empowerment Scholarship Account (ESA) | zip code | 286,855 (FY2024, Q1–Q4 combined) |
  | Florida | Tax Credit Scholarship (FTC) | school district | 100,025 (2022–23) |
  | Texas | Texas Education Freedom Account (TEFA) | school district | 79,753 (2026–27) |
  | New Hampshire | Education Freedom Account (EFA) | county | 10,510 (SY2025–26) |
  | West Virginia | Hope Scholarship | county | 10,530 (2024–25) |
  | North Carolina | Opportunity Scholarship | county | 106,867 (2024–25) |
  | Alaska | Correspondence Study | school district | 22,959 (FY2024) |
  | Indiana | Choice Scholarship | county | 75,930 (2024–25, Period 1+2) |
  | Rhode Island | 5 Scholarship Granting Organizations, combined | zip code | 678 (2025) |

- **13,409 private schools** geocoded from the NCES Private School Universe
  Survey directory across 34 states (the 9 above plus 25 more with a school
  directory but no program-participation data loaded yet), each taggable by
  religious affiliation, level, coed status, and reported enrollment.
- **A click-through profile panel**: the map opens on a national summary
  (total participation across all 9 programs, total schools, demographic
  breakdowns); clicking any state focuses in on that state's own numbers;
  clicking elsewhere on the map returns to the national view.
- **Layer toggles**: state boundaries; each program's choropleth
  independently; and a single global switch for how private schools are
  drawn — clustered (bubbles that aggregate at low zoom), exact locations
  (every school as its own point, with dot size that shrinks at low zoom so
  a nationwide view doesn't turn solid), or hidden entirely.
- **A source citation under every data point** in the profile panel — which
  report, which year, and any known caveat (a privacy-suppression threshold,
  a reconciliation adjustment, an inconsistency in the source document
  itself) rather than a bare number with no provenance.

## Repo layout

```
index.html                   — the map (generated; do not hand-edit)
data/
  geojson/                   — one file per state/program choropleth + state_boundaries_50.geojson
  schools/                   — one schools_<abbr>_final.json per state (34 files)
  profiles/                  — state_profiles_by_abbr.json, national_profile.json, sources.json
scripts/
  build_map.py               — reads data/, writes index.html
  pipeline/                  — one script per state/program: PDF/Excel → structured rows →
                                shapefile join → geojson. See scripts/pipeline/README.md.
```

## Rebuilding the map

```
python3 scripts/build_map.py
```

reads everything in `data/` and regenerates `index.html`. No shapefiles or
source PDFs are needed for this step — those are only inputs to the
`scripts/pipeline/` scripts that produced the files already in `data/`.

## Re-running the data pipeline

The original source PDFs/Excel files (state reports, NCES school
directories) and the Census TIGER/Line shapefiles are **not committed to
this repo** — see `.gitignore`. To add a new state or refresh a number:

1. Get the state's own program report from its education department /
   scholarship-granting-organization site, and/or an NCES Private School
   Universe Survey export from https://nces.ed.gov/surveys/pss/privateschoolsearch/.
2. Get the matching Census TIGER/Line shapefile:
   - ZCTAs (zip-code-level programs): `tl_2024_us_zcta520.zip` (national, ~530MB)
     — https://www2.census.gov/geo/tiger/TIGER2024/ZCTA520/
   - Counties (county-level programs): `tl_2024_us_county.zip` (national, ~84MB)
     — https://www2.census.gov/geo/tiger/TIGER2024/COUNTY/
   - Unified school districts (district-level programs): `tl_2024_<state-fips>_unsd.zip`
     — https://www2.census.gov/geo/tiger/TIGER2024/UNSD/
3. Follow `scripts/pipeline/README.md` — write or reuse an `extract_*.py`
   parser, join it to the shapefile with `match_to_shapefile.py`, geocode any
   new school directory with `geocode_schools.py` + `assemble_schools.py`.
4. Drop the resulting files into `data/`, wire the new state into
   `scripts/build_map.py`, and re-run it.

Every parser script in `scripts/pipeline/` was verified against its actual
source document during this project (see each script's docstring) — the
totals it produces should match the shipped `data/` files exactly if you
re-run it against the same source PDF.

## Data-quality notes worth knowing before citing a number

- **Program totals are not on a common basis.** "Students," "accounts,"
  "scholarships," and "recipients" mean different things depending on the
  program (e.g. Arizona counts *accounts*, which can include siblings on one
  account; Rhode Island counts individual *scholarships*, which can include
  more than one per student). The national total (694,107) sums these
  as-reported — see each state's profile for its specific unit.
- **Several states suppress small counts for privacy.** Indiana asterisks
  any county/period count under 10 (FERPA); this map treats those as 0,
  which undercounts the true total by an unknown amount (documented in
  Indiana's source note). Texas's report only publishes districts with 30+
  participants.
- **A few source documents have internal inconsistencies** (e.g. one Rhode
  Island SGO's own printed subtotal for one school doesn't match its
  own zip-level row detail on the same page) or required a correction to
  reconcile with the report's own stated total (Alaska: one district's count
  was missing from the summary table but present in a companion table). Each
  is flagged in that state's source citation rather than silently absorbed.
- **~45 Arizona zip codes and 1 Texas "district"** (Harris County Dept. of
  Education, a service agency rather than a school district) have no
  matching Census polygon and are excluded from their respective
  choropleths; the small dollar/count amounts involved are noted in-app.
- **NCES school geocoding**: addresses were run through the Census Bureau's
  batch geocoder, then OpenStreetMap Nominatim as a fallback. A small
  fraction of schools (varies by state, typically under 10%) are placed at
  city/zip-level rather than an exact street address where geocoding
  couldn't resolve the precise location — flagged per-school in the map's
  tooltip and counted in each state's profile.
