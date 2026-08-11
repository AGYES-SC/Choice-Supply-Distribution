# School Choice Program Participation — National Map

An interactive HTML map of K-12 school-choice program participation (ESAs,
tax-credit scholarships, vouchers, correspondence-study programs) and
private-school locations across the United States.

**`index.html` fetches 16 data files (15 geojson + `schools_all.json`) at load
time, so it must be served over HTTP — via GitHub Pages, or locally with
`python3 -m http.server` from the folder holding `index.html` (then open
http://localhost:8000). Opening the file directly with `file://` will not
work, because browsers block those fetches. Those 16 files must sit next to
`index.html` at the site root; the build copies them there automatically (see
"Rebuilding"), so deploying is just uploading `index.html` + those 16 files.**

## What it shows

- **13 states with full program-participation choropleths**, each at that
  program's own reporting geography (zip code, school district, or county):

  | State | Program | Geography | Latest total |
  |---|---|---|---|
  | Arizona | Empowerment Scholarship Account (ESA) | zip code | 286,855 (FY2024, Q1–Q4) and 294,057 (FY2026, Q1–Q3, partial year) — both shown as separate toggleable layers |
  | Florida | Tax Credit Scholarship (FTC) | school district | 100,025 (2022–23) |
  | Texas | Texas Education Freedom Account (TEFA) | school district | 79,753 (2026–27) |
  | New Hampshire | Education Freedom Account (EFA) | county | 10,510 (SY2025–26) |
  | West Virginia | Hope Scholarship | county | 10,530 (2024–25) |
  | North Carolina | Opportunity Scholarship | county | 106,867 (2024–25) |
  | Alaska | Correspondence Study | school district | 22,959 (FY2024) |
  | Indiana | Choice Scholarship | county | 75,930 (2024–25, Period 1+2) |
  | Rhode Island | 5 Scholarship Granting Organizations, combined | zip code | 678 (2025) |
  | Wisconsin | Choice Programs (MPCP/RPCP/WPCP) + SNSP | zip code | 60,927 (2025–26 headcount, crosswalked from a school/system-level enrollment report against the state's private school directory — see Wisconsin's profile for the methodology) |
  | Maryland | BOOST Scholarship (voucher) | county of residence | 2,796 (2025–26; scholarships awarded and accepted, by applicant county of residence). Private-school locations come from the NCES directory (535 schools); the 152 schools that enrolled BOOST students are flagged from the program's own by-school table, 125 of them matched to a directory school. |
  | Missouri | MOScholars (Empowerment Scholarship Accounts) | home public school district | 11,598 (SY2026-27, by student's home public school district; counts below 5 per district are privacy-suppressed and treated as 0). Private-school locations come from the NCES directory; the 287 schools that received MOScholars funds in SY2025-26 ($38.4M) are flagged, 184 matched to a directory school. |
  | Arkansas | LEARNS Education Freedom Account (EFA) | county of the school attended | 9,380 mapped of 10,834 EFA students (2024-25). Reported by school (Table 1), then crosswalked to the state private-school directory and aggregated by the private school's county — not student residence. 88 of 126 participating schools located (81 via the directory + 7 geocoded); ~13% of EFA students could not be placed. |

- **15,852 private schools** geocoded across 35 states (the 13 program states
  above — all now with a private-school directory — plus 22 more with a
  directory but no program-participation data loaded yet), each taggable by
  religious affiliation, level, coed status, and reported enrollment. Seventeen states' schools come from that state's own
  private school directory rather than the NCES Private School Universe
  Survey used elsewhere, since the state's own directory is more current
  and/or more complete: Wisconsin (NCES only covered ~44% of WI's actual
  Choice-program enrollment), North Carolina, Indiana, Florida, Rhode
  Island, New Hampshire, Louisiana, Alabama, Arkansas, Iowa, Idaho, Kansas,
  Kentucky, North Dakota, Ohio, Tennessee, and Utah. Each of those states'
  profile names its directory as the source, and
  `data/profiles/sources.json` documents the specific methodology and any
  data-quality issue found in that state's source file.
- **A click-through profile panel**: the map opens on a national summary
  (total participation across all 13 programs, total schools, demographic
  breakdowns); clicking any state focuses in on that state's own numbers;
  clicking elsewhere on the map returns to the national view. Each state
  drawer has an **Access analysis** section (supply-vs-demand + per-child
  metrics), a **Reported program counts by area** dropdown (the raw
  choropleth values for that state, filterable when a state has more than one
  program layer), and a **School characteristics** breakdown.
- **Layer toggles**: state boundaries; each program's choropleth
  independently; and a single global switch for how private schools are
  drawn — clustered (bubbles that aggregate at low zoom), exact locations
  (every school as its own point, with dot size that shrinks at low zoom so
  a nationwide view doesn't turn solid), or hidden entirely.
- **A source citation under every data point** in the profile panel — which
  report, which year, and any known caveat (a privacy-suppression threshold,
  a reconciliation adjustment, an inconsistency in the source document
  itself) rather than a bare number with no provenance.
- **Three reference pages** reachable from the header:
  - **About** — a plain-language explainer of how to read the map and what the
    headline numbers mean.
  - **Methodology** — the full, reproducible technical method: every data
    source, the by-school crosswalk and geocoding-validation rules, and the
    exact formulas (ACS school-age denominator column set, take-up rate, seats
    per 1,000, access-desert share, the population-weighted access Gini, and
    the supply/demand ratios) — written so the results can be reproduced from
    the raw tables.
  - **Open data** — every raw table, grouped in a collapsible drawer per
    state: each program's reported counts by area and the full private-school
    directory, each **downloadable as CSV** for open-source access.

## Repo layout

```
index.html                   — the map code (generated; do not hand-edit). Fetches the data below at runtime.
data/
  schools_all.json           — all 35 states' private schools, normalized (fetched by the map)
  manifest.json              — lightweight per-state index (states, counts, sources)
  geojson/                   — one file per state/program choropleth + state_boundaries_50.geojson (fetched by the map)
  schools/                   — one schools_<abbr>_final.json per state (35 files); pipeline inputs to schools_all.json
  profiles/                  — state_profiles_by_abbr.json, national_profile.json, sources.json (inlined into index.html)
scripts/
  build_map.py               — reads data/geojson + data/profiles, writes the lean index.html
  pipeline/                  — one script per state/program: PDF/Excel → structured rows →
                                shapefile join → geojson. See scripts/pipeline/README.md.
```

## Rebuilding the map

```
python3 scripts/build_map.py
```

reads the choropleth geojson (for class breaks) and the profile JSONs, and
regenerates `index.html`. The map's large datasets (`schools_all.json`, the
geojson files) are no longer inlined — the generated page fetches them at load
time — so `index.html` stays small. The build then **copies those 16 runtime
files next to `index.html` at the repo root**, producing a flat, upload-ready
bundle (canonical copies stay under `data/`); it prints the exact deploy file
list. To serve from a `data/` subfolder instead, set `FETCH_PREFIX` at the top
of `build_map.py`. No shapefiles or source PDFs are needed for this step; those
are only inputs to the
`scripts/pipeline/` scripts that produced the files already in `data/`.

## Re-running the data pipeline

The original source PDFs/Excel files (state reports, NCES school
directories) and the Census TIGER/Line shapefiles are **not committed to
this repo** — see `.gitignore`. To add a new state or refresh a number:

1. Get the state's own program report from its education department /
   scholarship-granting-organization site, and/or an NCES Private School
   Universe Survey export from https://nces.ed.gov/surveys/pss/privateschoolsearch/.
   (For Wisconsin specifically: NCES only covers ~44% of actual Choice-program
   enrollment there, so this map uses Wisconsin's own state-provided private
   school directory instead - request it from WI DPI's School Directory Search
   at https://dpi.wi.gov/cst/directories/school-directory, or via the private
   school listing on the WI DPI Choice Programs page.)
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
  more than one per student). The national total (786,010, across 13
  programs) sums these as-reported — see each state's profile for its specific
  unit. Arizona
  contributes its FY2026 (Q1–Q3, partial year) figure to this total rather
  than FY2024, since that's the most current period available; its FY2024
  full-year figure remains on the map as a separate toggleable layer for
  comparison but isn't double-counted in the national sum.
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
- **~45 Arizona zip codes, 1 Texas "district"** (Harris County Dept. of
  Education, a service agency rather than a school district), and 1 small
  Wisconsin zip code have no matching Census polygon and are excluded from
  their respective choropleths; the small dollar/count amounts involved are
  noted in-app.
- **Wisconsin's enrollment figure required a school-level crosswalk**, not a
  direct report-to-shapefile join: the state's own enrollment report has no
  addresses, only a school/system name and township, so it was matched
  against Wisconsin's private school directory to get geocodable campus
  locations. Where the report named a multi-campus "system" resolving to
  several directory campuses in the same city, that system's enrollment was
  split evenly across its campuses (an approximation - the true per-campus
  split isn't published anywhere). This crosswalk resolved 100% of the
  state's reported headcount; see Wisconsin's own source citation in the
  map for the full methodology and its one closed-school/one city-alias
  edge case.
- **Maryland, Missouri, and Arkansas use the same by-school crosswalk**, and
  their choropleths are therefore by **school location, not student
  residence** (except Maryland's BOOST county figure, which is reported by
  county of residence). Each participating school from the program's own
  by-school table is matched to the private-school directory (precision-first:
  exact name, then geographic/city disambiguation, containment, and a
  distinctive-word rule — never a partial match), and participating schools
  absent from the directory are geocoded by name+city via Nominatim and kept
  only if they fall inside the state and within 60 km of the claimed city
  (rejecting a same-named school in the wrong metro). Coverage is stated per
  state (e.g. Arkansas maps 88 of 126 schools / 87% of EFA students); schools
  that can't be placed are counted in the state's aggregate but not shown on
  the map. The full procedure and formulas are on the map's **Methodology**
  page.
- **NCES school geocoding**: addresses were run through the Census Bureau's
  batch geocoder, then OpenStreetMap Nominatim as a fallback. A small
  fraction of schools (varies by state, typically under 10%) are placed at
  city/zip-level rather than an exact street address where geocoding
  couldn't resolve the precise location — flagged per-school in the map's
  tooltip and counted in each state's profile.
- **Enrollment ("seats") is mixed-source.** Where a state directory reports
  enrollment (FL, TN, KS, WI) that figure is used; every other school's
  enrollment is borrowed from its matching NCES Private School Universe
  Survey record (2023-24), matched by name + city, and flagged "NCES
  2023-24" in the tooltip. ~85% of schools get a seat figure; the ~15% with
  no match (newer than the NCES snapshot, or unsurveyed) carry none, so
  seats-based totals undercount there. See the `SEATS` note in
  `data/profiles/sources.json` and `scripts/pipeline/backfill_enrollment_from_nces.py`.
  Re-runnable against a newer PSS release.
- **New Hampshire's own directory has no street addresses at all** — only a
  school and its town — so all 133 of its schools are geocoded to their
  town's centroid rather than an exact address; every NH school is flagged
  as approximate for this reason. Indiana's and Rhode Island's own
  directories concatenate a school's street address directly against its
  city with no delimiter in the source PDF's text, and Rhode Island's also
  glues each school's name against its administrator's name; both were
  recovered programmatically (see `extract_in_private_school_directory.py`
  and `extract_ri_private_school_directory.py`) and don't affect location
  accuracy, though a handful of Rhode Island school names still retain a
  trailing contact-name fragment.
