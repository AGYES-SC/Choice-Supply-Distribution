import filecmp
import json
import os
import shutil

# Repo layout: scripts/build_map.py, data/{geojson,schools,profiles}/, output at repo root.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEOJSON_DIR = os.path.join(ROOT, 'data', 'geojson')
PROFILES_DIR = os.path.join(ROOT, 'data', 'profiles')

# Runtime fetch base for the map's data files, relative to index.html. '' = FLAT:
# every fetched file sits at the site root next to index.html (matches the flat
# GitHub Pages repo). After writing index.html the build copies those files to
# this location so the output is a self-contained, upload-ready bundle. Set to
# 'data/' etc. if you instead serve the data from a subfolder.
FETCH_PREFIX = ''
# the files the map fetches at runtime: 13 geojson + the consolidated schools file
RUNTIME_GEOJSON = ['az_zip.geojson', 'az_zip_fy2026.geojson', 'fl_districts.geojson',
                   'tx_districts.geojson', 'nh_counties.geojson', 'wv_counties.geojson',
                   'nc_counties.geojson', 'md_counties.geojson', 'ak_districts.geojson',
                   'ri_zip.geojson', 'in_counties.geojson', 'wi_zip.geojson',
                   'mo_districts.geojson', 'ar_counties.geojson', 'state_boundaries_50.geojson']

def load_geo(name):
    with open(os.path.join(GEOJSON_DIR, name)) as f:
        return json.load(f)

def load_profile(name):
    with open(os.path.join(PROFILES_DIR, name)) as f:
        return json.load(f)

# Only the choropleth geometry is loaded at build time, solely to compute each
# layer's class breaks below; the geojson itself (and all school data) is
# fetched in the browser, never inlined.
az_geo = load_geo('az_zip.geojson')
az_geo_fy2026 = load_geo('az_zip_fy2026.geojson')
fl_geo = load_geo('fl_districts.geojson')
tx_geo = load_geo('tx_districts.geojson')
nh_geo = load_geo('nh_counties.geojson')
wv_geo = load_geo('wv_counties.geojson')
nc_geo = load_geo('nc_counties.geojson')
md_geo = load_geo('md_counties.geojson')
ak_geo = load_geo('ak_districts.geojson')
ri_geo = load_geo('ri_zip.geojson')
in_geo = load_geo('in_counties.geojson')
wi_geo = load_geo('wi_zip.geojson')
mo_geo = load_geo('mo_districts.geojson')
ar_geo = load_geo('ar_counties.geojson')
state_profiles = load_profile('state_profiles_by_abbr.json')
fips_to_abbr = load_profile('fips_to_abbr.json')
national_profile = load_profile('national_profile.json')
sources = load_profile('sources.json')

# wave 2/3: schools-only states, no program/reporting data yet (AK, RI now have program data too, handled separately below)
WAVE2_STATES = [
    ('GA', 'Georgia', '#933c1f'),
    ('WY', 'Wyoming', '#1f935e'),
    ('AR', 'Arkansas', '#801f93'),
    ('OK', 'Oklahoma', '#85931f'),
    ('UT', 'Utah', '#931f41'),
    ('OH', 'Ohio', '#1f931f'),
    ('IN', 'Indiana', '#411f93'),
    ('AL', 'Alabama', '#93631f'),
    ('TN', 'Tennessee', '#1f9385'),
    ('AK', 'Alaska', '#931f80'),
    ('ID', 'Idaho', '#5e931f'),
    ('SC', 'South Carolina', '#1f3c93'),
    ('IA', 'Iowa', '#93241f'),
    ('LA', 'Louisiana', '#1f9346'),
    ('RI', 'Rhode Island', '#681f93'),
    ('MT', 'Montana', '#938a1f'),
    ('SD', 'South Dakota', '#1f7b93'),
    ('NV', 'Nevada', '#931f59'),
    ('PA', 'Pennsylvania', '#37931f'),
    ('VA', 'Virginia', '#291f93'),
    ('KS', 'Kansas', '#934b1f'),
    ('MS', 'Mississippi', '#1f936d'),
    ('KY', 'Kentucky', '#8f1f93'),
    ('ND', 'North Dakota', '#76931f'),
    ('CO', 'Colorado', '#1f5493'),
    ('NE', 'Nebraska', '#931f32'),
    ('MO', 'Missouri', '#1f932e'),
]
WAVE2_COLOR = {code: color for code, _, color in WAVE2_STATES}

def quantile_breaks(values, n=7):
    vals = sorted(values)
    m = len(vals)
    def q(p):
        idx = min(m - 1, int(p * m))
        return vals[idx]
    return [q(p) for p in [i/n for i in range(n)] + [1.0]]

AZ_RAMP = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b']
AZ_FY2026_RAMP = ['#d0ebf1', '#a0e0ee', '#5fd8f2', '#14d6ff', '#00b0d6', '#0086a3', '#005c70']  # cyan, distinct from FY2024's blue
FL_RAMP = ['#d4ede4', '#aae4cf', '#72deb8', '#34e0a2', '#19bd82', '#109364', '#096746']  # aqua
TX_RAMP = ['#f1e6d0', '#eed5a0', '#f2c35f', '#ffb414', '#d69200', '#a36f00', '#704c00']  # yellow
NH_RAMP = ['#dbd8e9', '#b9b4da', '#8f85cc', '#6251c3', '#4535a2', '#33267d', '#221957']  # violet
WV_RAMP = ['#edd4d4', '#e4aaaa', '#de7372', '#e03534', '#be1a18', '#941110', '#670909']  # red
NC_RAMP = ['#d0f1d0', '#a0eea0', '#5ff25f', '#14ff14', '#00d600', '#00a300', '#007000']  # green
MD_RAMP = ['#f3d9e6', '#e9b3cd', '#df8cb4', '#d55f99', '#c23a7e', '#98285f', '#6b1a42']  # rose
AK_RAMP = ['#ecd5dd', '#e3abc0', '#dc749b', '#dc3775', '#ba1c58', '#911242', '#650b2d']  # magenta
RI_RAMP = ['#d3eeee', '#a7e7e7', '#6ce5e5', '#29eaea', '#0fc7c7', '#089b9b', '#036d6d']  # teal
IN_RAMP = ['#dcd5eb', '#bcade0', '#9478d8', '#6a3dd6', '#4d22b4', '#39178c', '#270e62']  # indigo
WI_RAMP = ['#d5e2eb', '#adcbe0', '#78b1d8', '#3d97d6', '#2278b4', '#175c8c', '#0e3f62']  # steel blue
MO_RAMP = ['#ece0d0', '#d9c1a0', '#c39d6d', '#ad7a3c', '#8c5d22', '#6a4518', '#482e0f']  # bronze
AR_RAMP = ['#ffe2c7', '#ffc08a', '#ff9b4d', '#f6760f', '#cc5c00', '#9a4500', '#6b3000']  # orange

AZ_MARKER = '#eb6834'
FL_MARKER = '#0f7a56'
TX_MARKER = '#8a5a00'
NH_MARKER = '#33267d'
WV_MARKER = '#7a0f0f'
NC_MARKER = '#0a5c0a'
WI_MARKER = '#1f6393'

# per-state private-school dot color (used to rebuild ALL_SCHOOL_SETS in the
# browser from the fetched schools_all.json)
MD_MARKER = MD_RAMP[-1]  # rose, matching MD's BOOST choropleth accent
SCHOOL_COLORS = {code: color for code, _, color in WAVE2_STATES}
SCHOOL_COLORS.update({'AZ': AZ_MARKER, 'FL': FL_MARKER, 'TX': TX_MARKER, 'NH': NH_MARKER,
                      'WV': WV_MARKER, 'NC': NC_MARKER, 'WI': WI_MARKER, 'MD': MD_MARKER})

# choropleth class breaks (7-quantile per program layer) — the only build-time
# use of the loaded geojson
az_edges = quantile_breaks([f['properties']['total'] for f in az_geo['features']])
az_fy2026_edges = quantile_breaks([f['properties']['total'] for f in az_geo_fy2026['features']])
fl_edges = quantile_breaks([f['properties']['students'] for f in fl_geo['features']])
tx_edges = quantile_breaks([f['properties']['students'] for f in tx_geo['features']])
nh_edges = quantile_breaks([f['properties']['students'] for f in nh_geo['features']])
wv_edges = quantile_breaks([f['properties']['students'] for f in wv_geo['features']])
nc_edges = quantile_breaks([f['properties']['students'] for f in nc_geo['features']])
md_edges = quantile_breaks([f['properties']['students'] for f in md_geo['features']])
ak_edges = quantile_breaks([f['properties']['students'] for f in ak_geo['features']])
ri_edges = quantile_breaks([f['properties']['students'] for f in ri_geo['features']])
in_edges = quantile_breaks([f['properties']['students'] for f in in_geo['features']])
wi_edges = quantile_breaks([f['properties']['students'] for f in wi_geo['features']])
mo_edges = quantile_breaks([f['properties']['students'] for f in mo_geo['features']])
ar_edges = quantile_breaks([f['properties']['students'] for f in ar_geo['features']])

# ---- accent color per state, for the profile panel header ----
STATE_ACCENT = {
    'AZ': AZ_RAMP[-1], 'FL': FL_RAMP[-1], 'TX': TX_RAMP[-1], 'NH': NH_RAMP[-1],
    'WV': WV_RAMP[-1], 'NC': NC_RAMP[-1], 'AK': AK_RAMP[-1], 'RI': RI_RAMP[-1], 'IN': IN_RAMP[-1],
    'WI': WI_RAMP[-1], 'MD': MD_RAMP[-1], 'MO': MO_RAMP[-1], 'AR': AR_RAMP[-1],
}
for code, color in WAVE2_COLOR.items():
    if code not in STATE_ACCENT:
        STATE_ACCENT[code] = color

def j(obj):
    return json.dumps(obj, separators=(',', ':'))

# Full reproducible methodology page (its own overlay, separate from About).
# Content is static HTML with no braces so it can be injected into the main
# f-string template via {METHODOLOGY_HTML}. Figures are stamped from the current
# build's national profile so the prose stays in sync.
_NP = national_profile
_M_TOTAL = f"{_NP.get('totalParticipation', 0):,}"
_M_PROGS = _NP.get('access', {}).get('programStates', '')
_M_SCHOOLS = f"{_NP.get('access', {}).get('schools', 0):,}"
METHODOLOGY_HTML = """
<div id="methodology-page" class="doc-page">
  <button class="about-close" type="button" onclick="closeMethod()">&times; Close</button>
  <div class="about-inner">
    <h2>Methodology</h2>
    <div class="about-sub">Every data source, transformation, and formula behind the numbers on this map &mdash; written so the results can be reproduced. Headline figures below are stamped from the current build: __M_TOTAL__ program participants across __M_PROGS__ program states, and __M_SCHOOLS__ private schools across 35 states.</div>

    <p class="about-lead">For each state we measure two things and combine them: <b>program participation</b> (demand &mdash; the colored areas) and <b>private-school supply</b> (the dots, each with an enrollment &ldquo;seat&rdquo; count). Census survey denominators turn raw counts into per-child rates. The whole pipeline is deterministic: the committed <code>data/</code> files plus <code>scripts/build_map.py</code> regenerate the map exactly; the raw inputs (state reports, NCES, Census shapefiles, ACS) regenerate <code>data/</code> via the one-script-per-source parsers in <code>scripts/pipeline/</code>.</p>

    <div class="toc">
      <a href="#m-pipeline">1. Pipeline &amp; reproducibility</a>
      <a href="#m-sources">2. Data sources</a>
      <a href="#m-participation">3. Program participation</a>
      <a href="#m-geography">4. Choropleth geography &amp; crosswalks</a>
      <a href="#m-directories">5. Directories &amp; geocoding</a>
      <a href="#m-seats">6. Enrollment (&ldquo;seats&rdquo;)</a>
      <a href="#m-acs">7. Per-child access metrics (ACS)</a>
      <a href="#m-supply">8. Supply-vs-demand &amp; disparity</a>
      <a href="#m-gold">9. Supply-side concentration</a>
      <a href="#m-national">10. National aggregate</a>
      <a href="#m-limits">11. Limitations</a>
    </div>

    <h3 id="m-pipeline">1. Pipeline &amp; reproducibility</h3>
    <p>Nothing is hand-entered. Each state/program has a parser in <code>scripts/pipeline/</code> that reads the official source file and emits structured rows; those are joined to Census geography and written to <code>data/</code>. <code>scripts/build_map.py</code> then reads <code>data/</code> and writes <code>index.html</code>. Re-running a parser against the same source reproduces its <code>data/</code> file byte-for-byte (each script's docstring states the exact verification check).</p>
    <p>Typical order for a program state: <code>extract_*</code> (parse the report) &rarr; geography join (shapefile match or crosswalk) &rarr; <code>build_&lt;state&gt;_program</code> / profile builder (participation + supply/demand + concentration blocks, national update) &rarr; <code>consolidate_schools.py</code> (normalize + merge all schools into <code>schools_all.json</code>) &rarr; <code>compute_acs_access.py</code> (layer on per-child ACS metrics) &rarr; <code>build_map.py</code>.</p>

    <h3 id="m-sources">2. Data sources</h3>
    <table class="method">
      <tr><th>Layer</th><th>Source</th><th>Notes</th></tr>
      <tr><td>Program participation</td><td>Each state's own official program report (education department or scholarship-granting organization), most current year available.</td><td>Geography and unit differ by program (see &sect;3). Per-state citation in <code>data/profiles/sources.json</code>.</td></tr>
      <tr><td>Private schools</td><td>17 states: that state's own private-school directory. All others: NCES Private School Universe Survey (PSS).</td><td>State directory used where more current/complete (e.g. NCES covered only ~44% of WI Choice enrollment).</td></tr>
      <tr><td>Enrollment (&ldquo;seats&rdquo;)</td><td>State report where given (FL, TN, KS, WI, AR); otherwise NCES PSS 2023&ndash;24.</td><td>~85% of schools get a figure; the rest carry none (see &sect;6).</td></tr>
      <tr><td>Child population</td><td>U.S. Census ACS 2024 5-year, table B14003 (school enrollment by type/age/sex), at ZCTA, county, and unified-school-district geographies.</td><td>The denominator for all per-child rates (&sect;7).</td></tr>
      <tr><td>Geography</td><td>Census TIGER/Line 2024: ZCTA520 (ZIP), county, and unified-school-district shapefiles.</td><td>Not committed (size); download links in the repo README.</td></tr>
    </table>

    <h3 id="m-participation">3. Program participation (the choropleth)</h3>
    <p>Each program's report is parsed into <code>(area, count)</code> rows at the geography the state reports:</p>
    <table class="method">
      <tr><th>Geography</th><th>Programs</th></tr>
      <tr><td>ZIP code</td><td>AZ ESA, RI SGOs, WI Choice</td></tr>
      <tr><td>County</td><td>NH EFA, WV Hope, NC Opportunity, IN Choice, MD BOOST (of residence), AR EFA (of school)</td></tr>
      <tr><td>School district</td><td>FL FTC, TX TEFA, AK Correspondence, MO MOScholars (home district)</td></tr>
    </table>
    <p><b>Suppression.</b> Where a state masks small counts for privacy, the masked cell is treated as <b>0</b>, which makes the mapped total a floor: Indiana asterisks any county/period under 10; Missouri masks any district under 5 (&ldquo;&lt; 5&rdquo;); Texas publishes only districts with 30+. Each is stated in that state's source note, and the number of suppressed areas is recorded.</p>
    <p><b>Reporting periods: levels vs. flows.</b> Where a program reports more than once a year, we first establish whether each report is a <i>level</i> (the program's enrollment as of that date) or a <i>flow</i> (new participants added since the last report). Arizona's quarterly ESA reports are levels &mdash; FY2024 runs 66,457 &rarr; 71,520 &rarr; 74,996 &rarr; 74,578 across Q1&ndash;Q4 &mdash; so a fiscal year is represented by its <b>last available quarter</b>, never by a sum of quarters, which would count most students once per quarter they were enrolled. Each extracted table is reconciled to the total the report prints for itself before it is mapped.</p>
    <p><b>Arizona</b> is shown as two separate toggleable layers (FY2024, taken from the year-end Q4 report; and FY2026, taken from Q3, the most recent published quarter of a year still in progress). Only the FY2026 figure enters the national total, so the two aren't double-counted. Its unit is <b>students</b>, per the reports' own headings (&ldquo;Number of ESA students&hellip;&rdquo;).</p>

    <h3 id="m-geography">4. Choropleth geography &amp; crosswalks</h3>
    <h4>Direct joins</h4>
    <p>Where the report is already by geography, rows join straight to Census polygons: ZIP &rarr; ZCTA code; county by name within state; school district by name, or by NCES district id = TIGER <code>GEOID</code> (Missouri, an exact key join). Geometry is simplified (tolerance 0.001&deg;) for the web.</p>
    <h4>By-school reports (Wisconsin-style crosswalk)</h4>
    <p>Some programs report participation <b>by school</b>, not by area (WI, MD BOOST participating-schools, MO scholarship recipients, AR EFA). To place these we crosswalk each participating school to the private-school directory for its location, then aggregate to the mapped geography. The matcher is <b>precision-first</b> &mdash; it accepts only a unique match, in this order:</p>
    <ol>
      <li><b>Normalize</b> both names: lowercase; <code>&amp;</code>&rarr;<code>and</code>; <code>saint/ss</code>&rarr;<code>st/saints</code>; drop punctuation, a trailing &ldquo;(City)&rdquo; or &ldquo;- Location&rdquo; suffix, and filler words (the, inc, llc).</li>
      <li><b>Exact</b> normalized-name match.</li>
      <li>If several candidates, <b>disambiguate by geography</b> &mdash; county via point-in-polygon (MD) or city (MO, AR).</li>
      <li><b>Unique substring containment</b> (one normalized name contains the other, &ge;8&ndash;9 chars).</li>
      <li><b>Distinctive-token</b> match: identical distinctive-word set (MD), or one name's distinctive words a subset of the other's sharing &ge;2 words including at least one non-common word (AR) &mdash; so &ldquo;Trinity <b>Catholic</b>&rdquo; never matches &ldquo;Trinity <b>Christian</b>&rdquo;. Accepted only if it resolves to exactly one school.</li>
    </ol>
    <p><b>Supplementary geocoding.</b> Participating schools not in the directory are looked up by name (+ city where the report gives one) via OpenStreetMap Nominatim, and kept only if the point falls <b>inside the state bounding box AND within 60&nbsp;km of the claimed city's centroid</b> &mdash; which rejects a same-named school matched in the wrong metro (e.g. a Kansas City parish resolving to St.&nbsp;Louis). Survivors are shown as approximate dots. Schools that neither match nor geocode are counted in the state's aggregate but not placed; each state's coverage (e.g. AR: 88 of 126 schools / 87% of EFA students) is stated in its source note.</p>
    <div class="method-note">For these programs the choropleth is by <b>school location</b>, not student residence (Maryland BOOST is the exception &mdash; it is reported by county of residence). This is stated in-app.</div>

    <h3 id="m-directories">5. Private-school directories &amp; geocoding</h3>
    <p>NCES PSS numeric codes are decoded to labels (type, religious affiliation, level, coed) and grade ranges to a level (Elementary / Secondary / Combined). Every school is geocoded in two passes:</p>
    <ol>
      <li><b>U.S. Census Bureau batch geocoder</b> (street-level, benchmark <code>Public_AR_Current</code>), in chunks to avoid timeouts.</li>
      <li><b>OpenStreetMap Nominatim</b> fallback for addresses Census can't resolve &mdash; address-level, then city/ZIP-level, rate-limited to 1&nbsp;request/sec.</li>
    </ol>
    <p>Every resolved point is validated against a generous <b>per-state bounding box</b>; points landing outside are dropped (this caught real cross-state mismatches). Any school placed at city/ZIP level rather than an exact street address is flagged <b>approximate</b> in its tooltip and counted per state. A school's <code>geo_method</code> field records exactly how it was placed.</p>
    <p>All schools are then normalized into one file (<code>schools_all.json</code>) with an identical key order and canonical enum values (level &isin; Elementary/Secondary/Combined/Not&nbsp;reported; relig &isin; Catholic/Other&nbsp;religious/Nonsectarian/Not&nbsp;reported; coed &isin; Coed/All-female/All-male/Not&nbsp;reported).</p>

    <h3 id="m-seats">6. Enrollment (&ldquo;seats&rdquo;)</h3>
    <p>A school's &ldquo;seats&rdquo; is its total enrollment. Provenance is recorded in <code>enroll_source</code>:</p>
    <ul>
      <li><b>State-reported</b> where the directory or report gives it (FL, TN, KS, WI; AR uses the EFA report's total enrollment for participating schools, tagged <code>ar_efa_2024_25</code>).</li>
      <li><b>NCES PSS 2023&ndash;24</b> otherwise, matched to each school conservatively by name + city (tagged <code>nces_2023_24</code>).</li>
      <li><b>None</b> for the ~15% of schools too new or unsurveyed to match &mdash; seats-based totals undercount there by construction.</li>
    </ul>

    <h3 id="m-acs">7. Per-child access metrics (ACS)</h3>
    <p>Denominators come from ACS 2024 5-year table <b>B14003</b> (school enrollment by type, age, and sex), pulled at the geography that matches each program (ZCTA, county, or unified school district) and joined to the choropleth areas.</p>
    <p><b>School-age (K&ndash;12 proxy) population</b> of an area = sum of the B14003 estimate columns for both sexes, ages 5&ndash;9 / 10&ndash;14 / 15&ndash;17, across all three enrollment statuses:</p>
    <div class="formula">school-age pop = &Sigma; B14003 cols {005,006,007, 033,034,035}   (public,  M/F)
                    + {014,015,016, 042,043,044}   (private, M/F)
                    + {023,024,025, 051,052,053}   (not enrolled, M/F)
ACS private attendance = &Sigma; {014,015,016, 042,043,044}</div>
    <p>With <code>P</code> = program participants in an area, <code>seats</code> = private-school seats in it, and <code>pop</code> = its school-age population, each state metric sums the parts across the state's areas and then:</p>
    <div class="formula">take-up rate (%)          = 100 &times; &Sigma;P    / &Sigma;pop
seats per 1,000 children  = 1000 &times; &Sigma;seats / &Sigma;pop
ACS private attendance (%)= 100 &times; &Sigma;(private) / &Sigma;pop
% children with no private school = 100 &times; &Sigma;(pop of areas with seats = 0) / &Sigma;pop
area coverage (%)         = 100 &times; (areas matched to ACS) / (total areas)</div>
    <p>County joins fall back to the ACS lower-case spelling for independent cities (e.g. &ldquo;Baltimore city&rdquo;). Areas that fail to join ACS are excluded from these rates, and the coverage % reports how complete the join was.</p>

    <h3 id="m-supply">8. Supply-vs-demand &amp; geographic disparity</h3>
    <p>Supply/demand ratios (state level):</p>
    <div class="formula">seats per school          = &Sigma;seats / (schools with a seat figure)
participants per seat     = &Sigma;P / &Sigma;seats
participants per school   = &Sigma;P / (school count)</div>
    <p>An <b>access desert</b> is an area with participation but <b>zero</b> private-school seats; the map reports the share of children living in such areas (formula in &sect;7).</p>
    <p><b>Population-weighted access Gini</b> measures how evenly private-school seats are spread relative to where children live. Let each area have access rate <code>r = seats / pop</code> and weight <code>w = pop</code>. Sort areas ascending by <code>r</code>; let <code>x</code> = cumulative share of children and <code>y</code> = cumulative share of seats. Then:</p>
    <div class="formula">Gini = 1 &minus; &Sigma; (x_i &minus; x_(i-1)) &middot; (y_i + y_(i-1))</div>
    <p><b>0</b> means every child has the same seats-per-child; values approaching <b>1</b> mean seats are concentrated in a few areas while most children have few or none. Areas with zero children are excluded.</p>
    <p><b>Correlation</b> between an area's participation and its private-school seats is reported as Pearson <code>r</code> (and a Spearman rank check), labeled <b>strong</b> (|r| &ge; 0.7), <b>moderate</b> (&ge; 0.4), or <b>weak</b>. The one-line <b>capacity signal</b> is set from participants-per-seat: <b>&lt; 0.5</b> &ldquo;far below capacity&rdquo;, <b>0.5&ndash;1.2</b> &ldquo;roughly balanced&rdquo;, <b>&gt; 1.2</b> &ldquo;exceeds nearby private-school capacity.&rdquo;</p>
    <div class="method-note">For a by-school program whose only enrollment data is the participating schools themselves (e.g. Arkansas), area participation and area seats are collinear by construction, so no correlation is reported &mdash; only the share of participating-school seats that are program-funded.</div>

    <h3 id="m-gold">9. Supply-side concentration (participating schools)</h3>
    <p>Where a program publishes a by-school table (MD BOOST, MO MOScholars, AR EFA), each private school in the directory is flagged with its program figure (BOOST students + award $, MOScholars $ received, or EFA + total enrollment), and the map computes: the count and share of the state's private schools that participate, the average award / EFA share, and a <b>concentration</b> measure &mdash; the share of all program students (or dollars) at the <b>top 5</b> schools. The count matched to a dot vs. counted only in aggregate is reported per state (see &sect;4).</p>

    <h3 id="m-national">10. National aggregate</h3>
    <p>The national summary sums each program's most-current reported total (<code>programBreakdown</code>, curated so each state contributes one vintage &mdash; Arizona contributes FY2026, not FY2024). Because programs count different units (students vs. recipients vs. scholarships), this total is an as-reported sum, not a like-for-like headcount. <code>programStates</code> is the count of programs; the national private-school and seat totals count directory schools only (excluding approximate supplementary dots); the tightest/loosest and median participants-per-seat and the correlation range are taken across the program states; and the U.S. private-attendance share is ACS private &divide; school-age population over the national district file (excluding Puerto Rico).</p>

    <h3 id="m-limits">11. Limitations</h3>
    <ul>
      <li><b>Estimates, not a census.</b> ACS and NCES figures are survey estimates a couple of years old &mdash; good for comparing places, not exact head-counts.</li>
      <li><b>Suppression undercounts.</b> Masked small counts are treated as 0 (&sect;3), so mapped totals are floors.</li>
      <li><b>Crosswalk coverage.</b> By-school programs place only the schools that match the directory or geocode cleanly; the unplaced share is stated per state and excluded from the choropleth (but kept in aggregates).</li>
      <li><b>Approximate geocoding.</b> Where a directory lacks street addresses (about half of some state directories), schools sit at a city/ZIP centroid, flagged approximate; this is why some states are mapped at county rather than ZIP level.</li>
      <li><b>School location vs. residence.</b> By-school programs are mapped where the school is, not where families live (MD BOOST excepted).</li>
      <li><b>Units differ.</b> Program totals are not on a common basis, so state-to-state totals are not apples-to-apples.</li>
    </ul>
    <p style="margin-top:22px;font-size:12.5px;color:var(--text-muted);">Per-number source citations live in <code>data/profiles/sources.json</code>; every raw table is downloadable as CSV from the <b>Open data</b> page; and the parsers that produced each figure are in <code>scripts/pipeline/</code> (see its README).</p>
  </div>
</div>
""".replace('__M_TOTAL__', _M_TOTAL).replace('__M_PROGS__', str(_M_PROGS)).replace('__M_SCHOOLS__', _M_SCHOOLS)

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>School Choice Program Distribution &mdash; National Map</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" />
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" />
<script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
<style>
  :root {{
    --surface-1: #fcfcfb;
    --page-plane: #f9f9f7;
    --text-primary: #0b0b0b;
    --text-secondary: #52514e;
    --text-muted: #898781;
    --gridline: #e1e0d9;
    --border: rgba(11,11,11,0.10);
    --accent: #eb6834;
    --accent-dark: #b8481c;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{
    margin: 0; padding: 0; height: 100%;
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    background: var(--page-plane);
    color: var(--text-primary);
  }}
  #app {{ display: flex; flex-direction: column; height: 100vh; }}
  header {{
    padding: 9px 20px;
    background: var(--surface-1);
    border-bottom: 1px solid var(--gridline);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
  }}
  header .hd-titles {{ display: flex; align-items: baseline; gap: 12px; min-width: 0; }}
  header h1 {{ font-size: 16px; font-weight: 700; margin: 0; color: var(--text-primary); letter-spacing: -0.01em; white-space: nowrap; }}
  header .subtitle {{ font-size: 12px; color: var(--text-muted); }}
  @media (max-width: 720px) {{ header .subtitle {{ display: none; }} }}
  #addr-search {{ display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }}
  #addr-input {{
    width: 320px; max-width: 46vw; padding: 8px 11px; font-size: 13px;
    border: 1px solid var(--border); border-radius: 7px; background: var(--page-plane);
    color: var(--text-primary); outline: none;
  }}
  #addr-input:focus {{ border-color: var(--accent); box-shadow: 0 0 0 2px rgba(235,104,52,0.18); }}
  #addr-search button {{
    padding: 8px 15px; font-size: 13px; font-weight: 600; cursor: pointer;
    background: var(--accent); color: #fff; border: none; border-radius: 7px;
  }}
  #addr-search button:hover {{ background: var(--accent-dark); }}
  #addr-search button:disabled {{ opacity: 0.6; cursor: default; }}
  #addr-status {{ font-size: 11.5px; color: var(--text-muted); flex-basis: 100%; min-height: 0; }}
  #addr-status.error {{ color: var(--accent-dark); }}
  .search-pin {{ font-size: 24px; line-height: 1; text-align: center; filter: drop-shadow(0 1px 2px rgba(0,0,0,0.4)); }}
  #map {{ flex: 1; min-height: 0; position: relative; }}
  /* water-toned fill so any area past the tile edge (e.g. west of Alaska) reads
     as ocean rather than blank gray */
  .leaflet-container {{ background: #d3dde0; font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }}
  .region-map {{ position: absolute; overflow: hidden; }}
  .region-map.active {{ inset: 0; z-index: 400; border: none; border-radius: 0; }}
  .region-map.inset {{
    z-index: 1000; border: 1px solid var(--border); border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.15); background: var(--surface-1);
  }}
  .region-map.slot-a {{ left: 12px; bottom: 14px; width: 232px; height: 146px; }}
  .region-map.slot-b {{ left: 254px; bottom: 14px; width: 188px; height: 120px; }}
  .region-canvas {{ position: absolute; inset: 0; }}
  .region-map .inset-label {{
    position: absolute; top: 5px; left: 6px; z-index: 690; font-size: 11px; font-weight: 700;
    color: var(--text-primary); background: rgba(252,252,251,0.9); padding: 1px 7px;
    border-radius: 4px; pointer-events: none;
  }}
  .region-map.active .inset-label {{ display: none; }}
  .region-map .promote-overlay {{ position: absolute; inset: 0; z-index: 680; cursor: pointer; display: none; }}
  .region-map.inset .promote-overlay {{ display: block; }}
  .region-map.inset .promote-overlay:hover {{ background: rgba(235,104,52,0.10); }}
  .region-map.inset .leaflet-control-zoom, .region-map.inset .leaflet-control-layers {{ display: none; }}
  @media (max-width: 640px) {{ .region-map.slot-b {{ display: none; }} }}
  #region-switch {{
    position: absolute; left: 12px; bottom: 14px; z-index: 1000; display: flex;
    background: var(--surface-1); border: 1px solid var(--border); border-radius: 8px;
    overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.15);
  }}
  #region-switch button {{
    background: var(--surface-1); border: none; padding: 7px 13px; font-size: 12px;
    font-weight: 600; color: var(--text-secondary); cursor: pointer;
  }}
  #region-switch button + button {{ border-left: 1px solid var(--border); }}
  #region-switch button.active {{ background: var(--accent); color: #fff; }}
  #region-switch button:hover:not(.active) {{ background: var(--page-plane); }}
  .zip-tooltip, .school-tooltip, .poly-tooltip {{ font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }}
  .zip-tooltip .zt-head, .school-tooltip .zt-head, .poly-tooltip .zt-head {{
    font-weight: 700; font-size: 13px; color: var(--text-primary); margin-bottom: 3px;
  }}
  .zip-tooltip .zt-total, .poly-tooltip .zt-total {{ font-size: 12.5px; color: var(--text-primary); margin-bottom: 5px; }}
  .zip-tooltip .zt-total b, .poly-tooltip .zt-total b {{ font-variant-numeric: tabular-nums; }}
  .zip-tooltip table {{ border-collapse: collapse; font-size: 11.5px; color: var(--text-secondary); }}
  .zip-tooltip td {{ padding: 1px 6px 1px 0; font-variant-numeric: tabular-nums; }}
  .zip-tooltip td.q-label {{ color: var(--text-muted); padding-right: 8px; }}
  .zip-tooltip .zt-foot, .poly-tooltip .zt-foot {{ font-size: 10.5px; color: var(--text-muted); margin-top: 4px; }}
  .school-tooltip {{ font-size: 12px; color: var(--text-secondary); max-width: 240px; }}
  .school-tooltip .zt-sub {{ color: var(--text-muted); font-size: 11.5px; margin-bottom: 4px; }}
  .school-tooltip .zt-row {{ display: flex; justify-content: space-between; gap: 10px; }}
  .school-tooltip .zt-approx {{ color: var(--accent-dark); font-size: 10.5px; margin-top: 4px; font-style: italic; }}
  .school-tooltip .zt-boost {{ color: {MD_MARKER}; font-size: 11px; margin-top: 4px; font-weight: 600; }}
  .school-tooltip .zt-scholarship {{ color: {MO_RAMP[-1]}; font-size: 11px; margin-top: 4px; font-weight: 600; }}
  .school-tooltip .zt-efa {{ color: {AR_RAMP[-1]}; font-size: 11px; margin-top: 4px; font-weight: 600; }}
  .leaflet-tooltip.zip-tt, .leaflet-tooltip.school-tt, .leaflet-tooltip.poly-tt {{
    background: var(--surface-1); border: 1px solid var(--border);
    box-shadow: 0 2px 8px rgba(0,0,0,0.15); border-radius: 6px; padding: 8px 10px;
  }}
  .cluster-icon {{
    border: 2px solid #ffffff; border-radius: 50%; color: #ffffff;
    font-weight: 700; font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    display: flex; align-items: center; justify-content: center; box-shadow: 0 1px 4px rgba(0,0,0,0.35);
  }}
  .leaflet-control-layers {{
    background: var(--surface-1); border: 1px solid var(--border); border-radius: 8px;
    font-size: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.12);
  }}
  .leaflet-control-layers-expanded {{ max-height: 78vh; overflow-y: auto; max-width: 292px; padding: 12px 14px; }}
  .leaflet-control-layers-list::before {{
    content: "Map layers"; display: block; font-weight: 700; font-size: 13px;
    color: var(--text-primary); margin-bottom: 2px;
  }}
  .leaflet-control-layers-base::before {{
    content: "Private-school overlay"; display: block; font-size: 10px; text-transform: uppercase;
    letter-spacing: 0.04em; color: var(--text-muted); font-weight: 600; margin: 10px 0 5px;
  }}
  .leaflet-control-layers-overlays::before {{
    content: "Program distribution"; display: block; font-size: 10px; text-transform: uppercase;
    letter-spacing: 0.04em; color: var(--text-muted); font-weight: 600; margin: 10px 0 5px;
  }}
  .leaflet-control-layers-separator {{ display: none; }}
  .leaflet-control-layers label {{ margin-bottom: 4px; line-height: 1.3; }}
  .leaflet-control-layers label span {{ display: inline-flex; align-items: flex-start; gap: 6px; }}
  .leaflet-control-layers-toggle {{ width: 36px; height: 36px; }}

  /* ---- state profile panel ---- */
  #state-profile {{
    position: absolute;
    top: 56px;
    right: 12px;
    bottom: 12px;
    width: 320px;
    max-width: calc(100vw - 24px);
    background: var(--surface-1);
    border: 1px solid var(--border);
    border-radius: 10px;
    box-shadow: 0 4px 18px rgba(0,0,0,0.18);
    z-index: 1000;
    display: none;
    flex-direction: column;
    overflow: hidden;
  }}
  #state-profile.open {{ display: flex; }}
  #state-profile .sp-header {{
    padding: 14px 16px;
    border-bottom: 1px solid var(--gridline);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    border-top: 5px solid var(--accent);
  }}
  #state-profile .sp-title {{ font-size: 16px; font-weight: 700; color: var(--text-primary); }}
  #state-profile .sp-close {{
    background: none; border: none; cursor: pointer; font-size: 20px; line-height: 1;
    color: var(--text-muted); padding: 2px 6px; border-radius: 4px;
  }}
  #state-profile .sp-close:hover {{ background: var(--gridline); color: var(--text-primary); }}
  #state-profile .sp-body {{ padding: 14px 16px; overflow-y: auto; flex: 1; }}
  #state-profile .sp-section {{ margin-bottom: 16px; }}
  #state-profile .sp-section:last-child {{ margin-bottom: 0; }}
  #state-profile .sp-label {{
    font-size: 10.5px; text-transform: uppercase; letter-spacing: 0.04em;
    color: var(--text-muted); font-weight: 600; margin-bottom: 4px;
  }}
  #state-profile .sp-stat {{ font-size: 24px; font-weight: 700; color: var(--text-primary); font-variant-numeric: tabular-nums; }}
  #state-profile .sp-stat-sub {{ font-size: 12px; color: var(--text-secondary); margin-top: 2px; }}
  #state-profile .sp-subhead {{
    font-size: 12.5px; font-weight: 700; color: var(--text-primary); margin: 10px 0 6px;
  }}
  #state-profile .sp-bar-row {{ margin-bottom: 6px; }}
  #state-profile .sp-bar-label {{
    display: flex; justify-content: space-between; font-size: 11.5px; color: var(--text-secondary); margin-bottom: 2px;
  }}
  #state-profile .sp-bar-label b {{ color: var(--text-primary); font-variant-numeric: tabular-nums; }}
  #state-profile .sp-bar-track {{ height: 6px; border-radius: 3px; background: var(--gridline); overflow: hidden; }}
  #state-profile .sp-bar-fill {{ height: 100%; background: var(--accent); border-radius: 3px; }}
  #state-profile .sp-note {{ font-size: 10.5px; color: var(--text-muted); margin-top: 8px; line-height: 1.4; }}
  #state-profile .sp-source {{ font-size: 10px; color: var(--text-muted); margin-top: 6px; line-height: 1.4; font-style: italic; }}
  #state-profile .sp-empty {{ font-size: 13px; color: var(--text-secondary); line-height: 1.5; }}
  #state-profile .sp-callout {{
    background: #fff4ee; border: 1px solid rgba(235,104,52,0.35);
    border-radius: 8px; padding: 12px 14px; margin-bottom: 16px;
  }}
  #state-profile .sp-callout p {{ margin: 0 0 9px; font-size: 12px; color: var(--text-secondary); line-height: 1.45; }}
  #state-profile .sp-callout p:last-child {{ margin-bottom: 0; }}
  #state-profile .sp-callout button {{
    background: var(--accent); color: #fff; border: none; border-radius: 6px;
    padding: 7px 13px; font-size: 12px; font-weight: 600; cursor: pointer;
  }}
  #state-profile .sp-callout button:hover {{ background: var(--accent-dark); }}
  #state-profile .sp-callout .sp-toggle-row {{ margin: 2px 0 9px; }}
  #state-profile .sp-callout button.ghost {{ background: none; color: var(--accent-dark); border: 1px solid var(--border); }}
  #state-profile .sp-callout button.ghost:hover {{ background: var(--page-plane); }}
  #state-profile .sp-callout .sp-seg {{
    display: inline-flex; border: 1px solid var(--border); border-radius: 6px;
    overflow: hidden; margin-bottom: 9px;
  }}
  #state-profile .sp-callout .sp-seg button {{
    background: var(--surface-1); color: var(--text-secondary); border: none;
    border-radius: 0; padding: 6px 13px; font-size: 11.5px; font-weight: 600;
  }}
  #state-profile .sp-callout .sp-seg button + button {{ border-left: 1px solid var(--border); }}
  #state-profile .sp-callout .sp-seg button.active {{ background: var(--accent); color: #fff; }}
  #state-profile .sp-callout .sp-seg button:hover:not(.active) {{ background: var(--page-plane); }}
  #state-profile .sp-callout .sp-callout-note {{ font-size: 11px; color: var(--text-muted); margin: 0; }}
  #sp-reopen {{
    position: absolute; top: 12px; right: 12px; z-index: 1000;
    background: var(--surface-1); border: 1px solid var(--border); border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.12); cursor: pointer; padding: 8px 13px;
    font-size: 12px; font-weight: 600; color: var(--text-primary); display: none;
  }}
  #sp-reopen:hover {{ background: var(--gridline); }}
  #sp-reopen.show {{ display: block; }}
  #state-profile .sp-schoollist {{
    margin-top: 8px; max-height: 300px; overflow-y: auto;
    border: 1px solid var(--gridline); border-radius: 6px;
  }}
  #state-profile .sp-school-row {{
    display: flex; flex-direction: column; gap: 1px;
    padding: 6px 9px; border-bottom: 1px solid var(--gridline);
  }}
  #state-profile .sp-school-row:last-child {{ border-bottom: none; }}
  #state-profile .sp-school-name {{ font-size: 12px; color: var(--text-primary); font-weight: 600; }}
  #state-profile .sp-school-meta {{ font-size: 11px; color: var(--text-muted); font-variant-numeric: tabular-nums; }}
  #state-profile .sp-linkbtn {{
    background: none; border: 1px solid var(--border); border-radius: 6px;
    padding: 9px 12px; font-size: 12px; font-weight: 600; color: var(--accent-dark);
    cursor: pointer; width: 100%; text-align: left;
  }}
  #state-profile .sp-linkbtn:hover {{ background: var(--page-plane); border-color: var(--accent); }}
  #state-profile .sp-drawer {{ border: 1px solid var(--gridline); border-radius: 8px; margin-bottom: 12px; overflow: hidden; }}
  #state-profile .sp-drawer > summary {{
    list-style: none; cursor: pointer; padding: 11px 14px; font-size: 12.5px; font-weight: 700;
    color: var(--text-primary); background: var(--page-plane);
    display: flex; align-items: center; justify-content: space-between;
  }}
  #state-profile .sp-drawer > summary::-webkit-details-marker {{ display: none; }}
  #state-profile .sp-drawer > summary::after {{ content: '\\25B8'; color: var(--text-muted); font-size: 12px; transition: transform .15s; }}
  #state-profile .sp-drawer[open] > summary::after {{ transform: rotate(90deg); }}
  #state-profile .sp-drawer-body {{ padding: 12px 14px; }}
  #state-profile .sp-prog-filter {{ margin-bottom: 8px; font-size: 12.5px; color: var(--text-secondary); }}
  #state-profile .sp-prog-filter select {{ font-size: 12.5px; padding: 3px 7px; border: 1px solid var(--border); border-radius: 5px; background: var(--surface-1); color: var(--text-primary); max-width: 100%; }}
  #state-profile .sp-prog-head {{ font-size: 12px; color: var(--text-muted); margin-bottom: 6px; }}
  #state-profile .sp-prog-list {{ max-height: 340px; overflow-y: auto; padding-right: 4px; }}
  #state-profile .sp-area-row {{ cursor: pointer; border-radius: 5px; padding-left: 4px; padding-right: 4px; }}
  #state-profile .sp-area-row:hover {{ background: var(--page-plane); }}
  #state-profile .sp-area-row .v {{ color: var(--accent-dark); font-weight: 600; }}
  #state-profile .sp-metric-big {{ text-align: center; padding: 4px 0 2px; }}
  #state-profile .sp-metric-num {{ font-size: 34px; font-weight: 800; color: var(--accent-dark); font-variant-numeric: tabular-nums; line-height: 1; }}
  #state-profile .sp-metric-lbl {{ font-size: 11px; color: var(--text-secondary); margin-top: 4px; line-height: 1.3; }}
  #state-profile .sp-interpret {{
    font-size: 12px; color: var(--text-primary); background: #fff4ee;
    border: 1px solid rgba(235,104,52,0.3); border-radius: 6px; padding: 8px 10px; margin: 10px 0; line-height: 1.4;
  }}
  #state-profile .sp-kv-row {{ display: flex; justify-content: space-between; gap: 12px; font-size: 12px; padding: 6px 0; border-bottom: 1px solid var(--gridline); }}
  #state-profile .sp-kv-row:last-child {{ border-bottom: none; }}
  #state-profile .sp-kv-row .k {{ color: var(--text-secondary); }}
  #state-profile .sp-kv-row .v {{ color: var(--text-primary); font-weight: 700; font-variant-numeric: tabular-nums; text-align: right; }}
  #state-profile .sp-lead {{ font-size: 13.5px; line-height: 1.5; color: var(--text-primary); margin: 4px 0 12px; }}
  #state-profile .sp-cards {{ display: flex; gap: 8px; margin-bottom: 10px; }}
  #state-profile .sp-card {{ flex: 1; background: var(--page-plane); border: 1px solid var(--gridline); border-radius: 8px; padding: 11px 8px; text-align: center; }}
  #state-profile .sp-card .num {{ font-size: 21px; font-weight: 800; color: var(--accent-dark); font-variant-numeric: tabular-nums; line-height: 1.05; }}
  #state-profile .sp-card .lbl {{ font-size: 10.5px; color: var(--text-secondary); margin-top: 5px; line-height: 1.25; }}
  #state-profile .sp-howlink {{ background: none; border: none; color: var(--accent-dark); font-size: 12px; font-weight: 600; cursor: pointer; padding: 4px 0; }}
  #state-profile .sp-howlink:hover {{ text-decoration: underline; }}
  header .hd-btn {{ background: none; border: 1px solid var(--border); border-radius: 6px; padding: 5px 10px; font-size: 11.5px; font-weight: 600; color: var(--text-secondary); cursor: pointer; white-space: nowrap; }}
  header .hd-btn:hover {{ background: var(--page-plane); color: var(--text-primary); }}
  #data-page {{ position: fixed; inset: 0; z-index: 3000; background: var(--surface-1); overflow-y: auto; display: none; }}
  #data-page.open {{ display: block; }}
  #data-page .data-inner {{ max-width: 1000px; margin: 0 auto; padding: 40px 24px 80px; }}
  #data-page h2 {{ font-size: 25px; margin: 0 0 6px; color: var(--text-primary); letter-spacing: -0.01em; }}
  #data-page .data-close {{ position: fixed; top: 16px; right: 20px; background: var(--surface-1); border: 1px solid var(--border); border-radius: 8px; padding: 8px 14px; font-size: 13px; font-weight: 600; cursor: pointer; z-index: 3001; box-shadow: 0 2px 10px rgba(0,0,0,0.12); }}
  #data-page .data-close:hover {{ background: var(--gridline); }}
  details.data-state {{ border: 1px solid var(--gridline); border-radius: 8px; margin-bottom: 10px; overflow: hidden; }}
  details.data-state > summary {{ list-style: none; cursor: pointer; padding: 13px 16px; font-weight: 600; font-size: 14.5px; color: var(--text-primary); display: flex; justify-content: space-between; align-items: center; gap: 10px; background: var(--page-plane); }}
  details.data-state > summary::-webkit-details-marker {{ display: none; }}
  details.data-state > summary::after {{ content: '\\25B8'; color: var(--text-muted); font-size: 12px; transition: transform .15s; }}
  details.data-state[open] > summary::after {{ transform: rotate(90deg); }}
  .data-badge {{ font-weight: 500; font-size: 12px; color: var(--text-muted); margin-left: auto; }}
  .data-state-body {{ padding: 6px 16px 18px; }}
  .data-subhead {{ display: flex; justify-content: space-between; align-items: center; gap: 12px; font-weight: 700; font-size: 13px; color: var(--text-primary); margin: 16px 0 6px; }}
  .data-dl {{ font-size: 11px; font-weight: 600; color: var(--text-secondary); cursor: pointer; border: 1px solid var(--border); border-radius: 5px; padding: 3px 9px; background: none; white-space: nowrap; }}
  .data-dl:hover {{ background: var(--page-plane); color: var(--text-primary); }}
  .data-table-wrap {{ max-height: 400px; overflow: auto; border: 1px solid var(--gridline); border-radius: 6px; }}
  table.data-tbl {{ border-collapse: collapse; width: 100%; font-size: 12px; }}
  table.data-tbl th {{ position: sticky; top: 0; background: var(--page-plane); text-align: left; padding: 6px 9px; font-weight: 700; color: var(--text-secondary); border-bottom: 1px solid var(--border); white-space: nowrap; }}
  table.data-tbl td {{ padding: 4px 9px; border-bottom: 1px solid var(--gridline); color: var(--text-secondary); }}
  table.data-tbl td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  table.data-tbl tr:hover td {{ background: var(--page-plane); }}
  .doc-page {{ position: fixed; inset: 0; z-index: 3000; background: var(--surface-1); overflow-y: auto; display: none; }}
  .doc-page.open {{ display: block; }}
  .doc-page .about-inner {{ max-width: 820px; margin: 0 auto; padding: 40px 24px 90px; }}
  .doc-page h2 {{ font-size: 25px; margin: 0 0 6px; color: var(--text-primary); letter-spacing: -0.01em; }}
  .doc-page .about-sub {{ color: var(--text-muted); font-size: 13px; margin-bottom: 8px; }}
  .doc-page h3 {{ font-size: 17px; margin: 30px 0 8px; color: var(--text-primary); border-bottom: 1px solid var(--gridline); padding-bottom: 5px; }}
  .doc-page h4 {{ font-size: 14px; margin: 18px 0 5px; color: var(--text-primary); }}
  .doc-page p, .doc-page li {{ font-size: 14px; line-height: 1.62; color: var(--text-secondary); }}
  .doc-page b {{ color: var(--text-primary); }}
  .doc-page ul, .doc-page ol {{ padding-left: 20px; margin: 6px 0; }}
  .doc-page li {{ margin-bottom: 7px; }}
  .doc-page .about-lead {{ font-size: 15.5px; line-height: 1.55; color: var(--text-primary); border-left: 3px solid var(--accent); padding-left: 14px; margin: 18px 0 4px; }}
  .doc-page .about-close {{ position: fixed; top: 16px; right: 20px; background: var(--surface-1); border: 1px solid var(--border); border-radius: 8px; padding: 8px 14px; font-size: 13px; font-weight: 600; cursor: pointer; z-index: 3001; box-shadow: 0 2px 10px rgba(0,0,0,0.12); }}
  .doc-page .about-close:hover {{ background: var(--gridline); }}
  .doc-page .formula {{ font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 12.5px; background: var(--page-plane); border: 1px solid var(--gridline); border-radius: 6px; padding: 9px 12px; margin: 8px 0; color: var(--text-primary); white-space: pre-wrap; line-height: 1.5; }}
  .doc-page code {{ font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 12px; background: var(--page-plane); border: 1px solid var(--gridline); border-radius: 4px; padding: 1px 4px; color: var(--text-primary); }}
  .doc-page table.method {{ border-collapse: collapse; width: 100%; font-size: 12.5px; margin: 8px 0; }}
  .doc-page table.method th {{ text-align: left; padding: 6px 9px; background: var(--page-plane); border: 1px solid var(--gridline); color: var(--text-secondary); font-weight: 700; }}
  .doc-page table.method td {{ padding: 5px 9px; border: 1px solid var(--gridline); color: var(--text-secondary); vertical-align: top; }}
  .doc-page .method-note {{ font-size: 12.5px; color: var(--text-muted); border-left: 3px solid var(--gridline); padding-left: 12px; margin: 10px 0; }}
  .doc-page .toc {{ columns: 2; font-size: 13px; margin: 6px 0 4px; }}
  .doc-page .toc a {{ color: var(--accent-dark); text-decoration: none; }}
  .doc-page .toc a:hover {{ text-decoration: underline; }}
  .gap-verdict {{ display: inline-block; font-size: 12px; font-weight: 700; padding: 3px 11px; border-radius: 20px; margin: 4px 0 9px; }}
  .gap-verdict.gap-good {{ background: #e6f4ea; color: #137333; }}
  .gap-verdict.gap-mid {{ background: #fef7e0; color: #8a6100; }}
  .gap-verdict.gap-bad {{ background: #fce8e6; color: #c5221f; }}
  .gap-list {{ font-size: 12.5px; color: var(--text-secondary); margin-top: 8px; }}
  .gap-list ul {{ margin: 4px 0 0; padding-left: 18px; }}
  .gap-list li {{ margin-bottom: 3px; }}
  #tool-launch {{ position: absolute; left: 50%; transform: translateX(-50%); bottom: 20px; z-index: 620; display: flex; gap: 10px; }}
  .tool-btn {{ background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; padding: 9px 15px; cursor: pointer; box-shadow: 0 2px 14px rgba(0,0,0,0.18); display: flex; flex-direction: column; align-items: flex-start; line-height: 1.3; text-align: left; }}
  .tool-btn:hover {{ border-color: var(--accent); }}
  .tool-btn .tb-title {{ font-weight: 700; font-size: 12.5px; color: var(--text-primary); }}
  .tool-btn .tb-sub {{ font-size: 11px; color: var(--text-muted); font-weight: 500; }}
  @media (max-width: 620px) {{ #tool-launch {{ flex-direction: column; bottom: 12px; }} }}
  #wizard {{ position: fixed; inset: 0; z-index: 3200; background: rgba(20,18,16,0.45); display: none; align-items: center; justify-content: center; padding: 20px; }}
  #wizard.open {{ display: flex; }}
  .wiz-card {{ background: var(--surface-1); border-radius: 14px; width: min(560px, 100%); max-height: 88vh; overflow-y: auto; box-shadow: 0 8px 40px rgba(0,0,0,0.3); }}
  .wiz-head {{ display: flex; justify-content: space-between; align-items: center; padding: 15px 20px; border-bottom: 1px solid var(--gridline); position: sticky; top: 0; background: var(--surface-1); z-index: 1; }}
  .wiz-head h3 {{ margin: 0; font-size: 16px; color: var(--text-primary); }}
  .wiz-close {{ background: none; border: none; font-size: 22px; cursor: pointer; color: var(--text-muted); line-height: 1; }}
  .wiz-body {{ padding: 18px 20px 24px; }}
  .wiz-progress {{ font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 7px; }}
  .wiz-q {{ font-size: 16px; font-weight: 600; color: var(--text-primary); margin-bottom: 15px; line-height: 1.4; }}
  .wiz-opts {{ display: flex; flex-direction: column; gap: 8px; }}
  .wiz-opt {{ text-align: left; background: var(--page-plane); border: 1px solid var(--border); border-radius: 8px; padding: 11px 14px; font-size: 13.5px; color: var(--text-primary); cursor: pointer; }}
  .wiz-opt:hover {{ border-color: var(--accent); background: var(--surface-1); }}
  .wiz-select, .wiz-input {{ width: 100%; padding: 10px 12px; font-size: 14px; border: 1px solid var(--border); border-radius: 8px; background: var(--surface-1); color: var(--text-primary); box-sizing: border-box; }}
  .wiz-go {{ margin-top: 11px; background: var(--accent); color: #fff; border: none; border-radius: 8px; padding: 10px 16px; font-size: 13.5px; font-weight: 600; cursor: pointer; }}
  .wiz-back {{ background: none; border: none; color: var(--text-muted); font-size: 12px; cursor: pointer; margin-top: 14px; padding: 0; }}
  .wiz-res-verdict {{ font-size: 14.5px; font-weight: 500; color: var(--text-primary); border-left: 3px solid var(--accent); padding-left: 12px; margin: 10px 0 14px; line-height: 1.5; }}
  .wiz-row {{ display: flex; justify-content: space-between; gap: 12px; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--gridline); font-size: 13px; }}
  .wiz-row .r-main {{ color: var(--text-primary); font-weight: 500; }}
  .wiz-row .r-sub {{ color: var(--text-muted); font-size: 11.5px; }}
  .wiz-row .r-val {{ color: var(--text-secondary); white-space: nowrap; text-align: right; }}
  .wiz-note {{ font-size: 12px; color: var(--text-muted); margin-top: 13px; line-height: 1.55; }}
</style>
</head>
<body>
<div id="app">
  <header>
    <div class="hd-titles">
      <h1>Choice Supply Distribution Map</h1>
      <span class="subtitle">School-choice program participation &amp; private-school supply across the U.S.</span>
      <button class="hd-btn" type="button" onclick="openAbout()">About</button>
      <button class="hd-btn" type="button" onclick="openMethod()">Methodology</button>
      <button class="hd-btn" type="button" onclick="openData()">Open data</button>
    </div>
    <form id="addr-search" autocomplete="off">
      <input id="addr-input" type="text" placeholder="Search any U.S. address, city, or ZIP&hellip;" aria-label="Search an address" />
      <button type="submit">Go</button>
      <span id="addr-status" role="status"></span>
    </form>
  </header>
  <div id="map">
    <div class="region-map active" id="region-conus"><div class="region-canvas" id="map-conus"></div></div>
    <div id="region-switch" role="group" aria-label="Jump to region">
      <button type="button" data-region="conus" class="active">U.S.</button>
      <button type="button" data-region="ak">Alaska</button>
      <button type="button" data-region="hi">Hawaii</button>
    </div>
    <button id="sp-reopen" aria-label="Show summary">&#9776;&nbsp; Summary</button>
    <div id="tool-launch">
      <button class="tool-btn" type="button" onclick="openWizard('entrepreneur')"><span class="tb-title">&#127919; I want to start a school</span><span class="tb-sub">Find the biggest access gaps &amp; opportunities</span></button>
      <button class="tool-btn" type="button" onclick="openWizard('parent')"><span class="tb-title">&#127891; I'm a parent</span><span class="tb-sub">Find a private school near me</span></button>
    </div>
    <div id="state-profile">
      <div class="sp-header">
        <div class="sp-title" id="sp-title">State</div>
        <button class="sp-close" id="sp-close" aria-label="Close">&times;</button>
      </div>
      <div class="sp-body" id="sp-body"></div>
    </div>
  </div>
</div>
<div id="about-page" class="doc-page">
  <button class="about-close" type="button" onclick="closeAbout()">&times; Close</button>
  <div class="about-inner">
    <h2>About this map</h2>
    <div class="about-sub">How to read it, where the numbers come from, and what they mean &mdash; in plain terms. For the full, reproducible technical method, see the <b>Methodology</b> page.</div>

    <p class="about-lead">This map puts two things side by side for each state: how many families use its school-choice program, and where private schools actually are. Together they answer one question &mdash; <b>when families get school-choice funding, is there a private school near them to use it?</b></p>

    <h3>The two things being measured</h3>
    <ul>
      <li><b>Participation (the demand).</b> How many students, recipients, or scholarships a program has &mdash; the colored areas on the map. Straight from each state's official program report.</li>
      <li><b>Private schools (the supply).</b> Where private schools are and how many students they hold &mdash; the dots on the map.</li>
    </ul>

    <h3>Where the numbers come from</h3>
    <ul>
      <li><b>Private-school lists:</b> 17 states publish their own official private-school directory &mdash; we use those. For every other state we use the U.S. Department of Education's national private-school survey (NCES).</li>
      <li><b>School size (seats):</b> a few states report enrollment directly; for the rest we borrow it from the NCES survey (2023&ndash;24). About 1 in 7 schools is too new to appear in that survey and shows no seat count.</li>
      <li><b>Program participation:</b> each state's own school-choice program report.</li>
      <li><b>Number of children:</b> the U.S. Census Bureau's American Community Survey (ACS), used to turn raw counts into per-child rates.</li>
    </ul>

    <h3>What the headline stats mean</h3>
    <ul>
      <li><b>Take-up</b> &mdash; the share of a state's school-age children who use the program. Higher means the program reaches more families.</li>
      <li><b>Participants per private-school seat</b> &mdash; program users divided by private-school seats. Below&nbsp;1 means there are more seats than users (room to spare). Well above&nbsp;1 means far more users than local private seats &mdash; a sign the money is going to homeschooling, microschools, or online, not brick-and-mortar private schools.</li>
      <li><b>"No private school nearby"</b> &mdash; the share of children who live in an area (zip, county, or district) that has no private school at all. This is the clearest measure of whether access is spread evenly or concentrated in a few places.</li>
    </ul>

    <h3>Things to keep in mind</h3>
    <ul>
      <li>Census and NCES figures are <b>estimates</b> and a <b>couple of years old</b> &mdash; good for comparing places, not exact head-counts.</li>
      <li>Programs count different things (students vs. recipients vs. scholarships), so <b>state totals aren't apples-to-apples</b>.</li>
      <li>A few areas are missing data, which can nudge access to look slightly better or worse than it is; we flag these where they matter.</li>
      <li>Alaska and Hawaii sit in their own boxes (bottom-left) &mdash; click either to view it full-screen, and click the U.S. box to return.</li>
    </ul>

    <h3>Contact</h3>
    <p>Questions, corrections, or data requests about this platform are welcome:<br>
      <b>Alex Graff</b> &mdash; Legislative Analyst, yes. every. kid.<br>
      <a href="mailto:agraff@yeseverykid.com" style="color:var(--accent-dark);font-weight:600;">agraff@yeseverykid.com</a></p>

    <p style="margin-top:24px;font-size:12.5px;color:var(--text-muted);">For the exact formulas, data sources, and step-by-step procedure behind every number &mdash; enough to reproduce these results &mdash; open the <b>Methodology</b> page. Per-number source citations are also in <b>data/profiles/sources.json</b>, and the <b>Open data</b> page exports every raw table as CSV.</p>
  </div>
</div>
{METHODOLOGY_HTML}
<div id="wizard">
  <div class="wiz-card">
    <div class="wiz-head"><h3 id="wiz-title">Guided tool</h3><button class="wiz-close" type="button" onclick="closeWizard()">&times;</button></div>
    <div class="wiz-body" id="wiz-body"></div>
  </div>
</div>
<div id="data-page">
  <button class="data-close" type="button" onclick="closeData()">&times; Close</button>
  <div class="data-inner">
    <h2>Open data &mdash; raw tables by state</h2>
    <div class="about-sub">Every figure on the map in its source form: each program's reported counts by area, and the full private-school directory for each state. Expand a state; download any table as CSV.</div>
    <div id="data-states"></div>
  </div>
</div>
<script type="module">
// Big datasets are FETCHED at runtime (served by GitHub Pages / any static host)
// rather than inlined, keeping index.html lean. These files must sit next to
// index.html at the site root. Preview via the Pages URL or a local server
// (python3 -m http.server from the folder holding index.html) — file:// blocks
// these fetches.
const _fj = async (p) => (await fetch(p)).json();
const [
  azGeo, azGeoFy2026, flGeo, txGeo, nhGeo, wvGeo, ncGeo, mdGeo, akGeo, riGeo, inGeo, wiGeo,
  moGeo, arGeo, stateBoundariesGeo, SCHOOLS_ALL
] = await Promise.all([
  _fj('{FETCH_PREFIX}az_zip.geojson'), _fj('{FETCH_PREFIX}az_zip_fy2026.geojson'),
  _fj('{FETCH_PREFIX}fl_districts.geojson'), _fj('{FETCH_PREFIX}tx_districts.geojson'),
  _fj('{FETCH_PREFIX}nh_counties.geojson'), _fj('{FETCH_PREFIX}wv_counties.geojson'),
  _fj('{FETCH_PREFIX}nc_counties.geojson'), _fj('{FETCH_PREFIX}md_counties.geojson'),
  _fj('{FETCH_PREFIX}ak_districts.geojson'), _fj('{FETCH_PREFIX}ri_zip.geojson'),
  _fj('{FETCH_PREFIX}in_counties.geojson'), _fj('{FETCH_PREFIX}wi_zip.geojson'),
  _fj('{FETCH_PREFIX}mo_districts.geojson'), _fj('{FETCH_PREFIX}ar_counties.geojson'),
  _fj('{FETCH_PREFIX}state_boundaries_50.geojson'), _fj('{FETCH_PREFIX}schools_all.json')
]);
const SCHOOL_COLORS = {j(SCHOOL_COLORS)};

const azEdges = {j(az_edges)};
const azRamp = {j(AZ_RAMP)};
const azFy2026Edges = {j(az_fy2026_edges)};
const azFy2026Ramp = {j(AZ_FY2026_RAMP)};
const flEdges = {j(fl_edges)};
const flRamp = {j(FL_RAMP)};
const txEdges = {j(tx_edges)};
const txRamp = {j(TX_RAMP)};
const nhEdges = {j(nh_edges)};
const nhRamp = {j(NH_RAMP)};
const wvEdges = {j(wv_edges)};
const wvRamp = {j(WV_RAMP)};
const ncEdges = {j(nc_edges)};
const ncRamp = {j(NC_RAMP)};
const mdEdges = {j(md_edges)};
const mdRamp = {j(MD_RAMP)};
const akEdges = {j(ak_edges)};
const akRamp = {j(AK_RAMP)};
const riEdges = {j(ri_edges)};
const riRamp = {j(RI_RAMP)};
const inEdges = {j(in_edges)};
const inRamp = {j(IN_RAMP)};
const wiEdges = {j(wi_edges)};
const wiRamp = {j(WI_RAMP)};
const moEdges = {j(mo_edges)};
const moRamp = {j(MO_RAMP)};
const arEdges = {j(ar_edges)};
const arRamp = {j(AR_RAMP)};

const STATE_PROFILES = {j(state_profiles)};
const FIPS_TO_ABBR = {j(fips_to_abbr)};
const STATE_ACCENT = {j(STATE_ACCENT)};
const NATIONAL_PROFILE = {j(national_profile)};
const SOURCES = {j(sources)};

function fmt(n) {{ return n.toLocaleString('en-US'); }}

function colorFor(v, edges, ramp) {{
  for (let i = 0; i < edges.length - 1; i++) {{
    if (v <= edges[i+1] || i === edges.length - 2) return ramp[i];
  }}
  return ramp[ramp.length - 1];
}}

// ---- state profile panel logic ----
const spPanel = document.getElementById('state-profile');
const spTitle = document.getElementById('sp-title');
const spBody = document.getElementById('sp-body');
const spReopen = document.getElementById('sp-reopen');
let profileClosed = false;

// The X genuinely closes the panel (and reveals a "Summary" button to bring it
// back), rather than just resetting to the national view as it did before.
function openPanel() {{ profileClosed = false; spReopen.classList.remove('show'); spPanel.classList.add('open'); }}
function closeProfile() {{ profileClosed = true; spPanel.classList.remove('open'); spReopen.classList.add('show'); }}
document.getElementById('sp-close').addEventListener('click', closeProfile);
spReopen.addEventListener('click', showNationalProfile);

// Used by the address search: if the whole map is currently hidden, turn on the
// clustered overlay for every state so nearby supply is visible.
function enableSchoolsLayer() {{
  if (aggregateSchoolMode() === 'none') setAllSchoolMode('clustered');
}}
// Re-render whichever profile view is open so its toggle reflects the map.
function refreshCurrentView() {{
  if (currentView === 'national') showNationalProfile();
  else if (currentView === 'area' && currentArea) showAreaDetail(currentArea.abbr, currentArea.layerIdx, currentArea.fi, true);
  else if (currentView === 'state' && currentAbbr) showStateProfile(currentAbbr);
}}
// scope = null  -> whole map (national summary + the left-side layers control)
// scope = abbr  -> that ONE state (program schools live in per-state layers, so
//                  a state panel toggles only its own dots).
function calloutToggleSchools(scope) {{
  const cur = scope ? SCHOOL[scope].mode : aggregateSchoolMode();
  const target = (cur === 'none') ? 'clustered' : 'none';
  if (scope) setStateSchoolMode(scope, target); else setAllSchoolMode(target);
  refreshCurrentView();
}}
function calloutSetMode(scope, mode) {{
  if (scope) setStateSchoolMode(scope, mode); else setAllSchoolMode(mode);
  refreshCurrentView();
}}
// Shared toggle block. scope null = national summary (whole map); scope = abbr =
// a state panel (that state only).
function schoolToggleCallout(scope) {{
  const mode = scope ? (SCHOOL[scope] ? SCHOOL[scope].mode : 'none') : aggregateSchoolMode();
  const shown = mode !== 'none';
  const scopeArg = scope ? "'" + scope + "'" : 'null';
  const stName = scope && STATE_PROFILES[scope] ? STATE_PROFILES[scope].name : 'this state';
  const note = scope
    ? 'Affects <b>' + stName + '</b> only. Use the national summary or the top-left Map layers control for the whole map.'
    : 'Toggles the whole map. Open a state to control just that state &mdash; also in the top-left Map layers control.';
  return `
    <div class="sp-callout">
      <p><b>Private schools ${{shown ? 'shown' : 'hidden'}}${{scope ? ' \\u2014 ' + stName : ''}}.</b> ${{shown
        ? 'Switch how they&rsquo;re drawn, or hide them.'
        : 'Overlay them to see supply alongside participation.'}}</p>
      <div class="sp-toggle-row">
        <button class="${{shown ? 'ghost' : ''}}" onclick="calloutToggleSchools(${{scopeArg}})">${{shown ? 'Hide' : 'Show'}} ${{scope ? 'these schools' : 'all schools'}}</button>
      </div>
      <div class="sp-seg" role="group" aria-label="Private-school display mode">
        <button class="${{mode === 'clustered' ? 'active' : ''}}" onclick="calloutSetMode(${{scopeArg}}, 'clustered')">Clustered</button>
        <button class="${{mode === 'exact' ? 'active' : ''}}" onclick="calloutSetMode(${{scopeArg}}, 'exact')">Exact locations</button>
      </div>
      <p class="sp-callout-note">${{note}}</p>
    </div>`;
}}

let currentAbbr = null;
let currentView = 'national';  // 'national' | 'state' | 'area' | 'search'
let currentArea = null;        // {{abbr, layerIdx, fi}} while drilled into one choropleth area
let preDrillView = null;       // map view to restore when leaving that area

function barRows(dict, total) {{
  const entries = Object.entries(dict).sort((a,b) => b[1]-a[1]);
  return entries.map(([label, count]) => {{
    const pct = total > 0 ? Math.round((count/total)*100) : 0;
    return `
      <div class="sp-bar-row">
        <div class="sp-bar-label"><span>${{label}}</span><b>${{fmt(count)}} (${{pct}}%)</b></div>
        <div class="sp-bar-track"><div class="sp-bar-fill" style="width:${{pct}}%"></div></div>
      </div>`;
  }}).join('');
}}

function sourceNote(abbr) {{
  const src = SOURCES[abbr];
  return src ? `<div class="sp-source">${{src}}</div>` : '';
}}

function drawer(title, body, open) {{
  return `<details class="sp-drawer"${{open ? ' open' : ''}}><summary>${{title}}</summary><div class="sp-drawer-body">${{body}}</div></details>`;
}}
function kv(k, v) {{ return `<div class="sp-kv-row"><span class="k">${{k}}</span><span class="v">${{v}}</span></div>`; }}

// ---- Reported program counts by area (the raw choropleth values, per state) ----
// One entry per program layer; states with more than one layer (e.g. Arizona's
// two ESA vintages) are filterable in the drawer. nameKey/key are the geojson
// feature properties holding the area name and the reported count.
const PROGRAM_LAYERS = [
  {{ abbr:'AZ', label:'ESA students &mdash; FY2024 (year-end)', geo: azGeo, key:'total', nameKey:'zip', unit:'ZIP code' }},
  {{ abbr:'AZ', label:'ESA students &mdash; FY2026 (as of Q3)', geo: azGeoFy2026, key:'total', nameKey:'zip', unit:'ZIP code' }},
  {{ abbr:'FL', label:'FTC scholarships (2022&ndash;23)', geo: flGeo, key:'students', nameKey:'name', unit:'school district' }},
  {{ abbr:'TX', label:'TEFA participants (2026&ndash;27)', geo: txGeo, key:'students', nameKey:'name', unit:'school district' }},
  {{ abbr:'NH', label:'EFA enrollees (SY2025&ndash;26)', geo: nhGeo, key:'students', nameKey:'name', unit:'county' }},
  {{ abbr:'WV', label:'Hope recipients (2024&ndash;25)', geo: wvGeo, key:'students', nameKey:'name', unit:'county' }},
  {{ abbr:'NC', label:'Opportunity Scholarship (2024&ndash;25)', geo: ncGeo, key:'students', nameKey:'name', unit:'county' }},
  {{ abbr:'MD', label:'BOOST scholarships (2025&ndash;26)', geo: mdGeo, key:'students', nameKey:'name', unit:'county of residence' }},
  {{ abbr:'AK', label:'Correspondence Study (FY2024)', geo: akGeo, key:'students', nameKey:'name', unit:'school district' }},
  {{ abbr:'RI', label:'SGO scholarships (2025)', geo: riGeo, key:'students', nameKey:'name', unit:'ZIP code' }},
  {{ abbr:'IN', label:'Choice Scholarship (2024&ndash;25)', geo: inGeo, key:'students', nameKey:'name', unit:'county' }},
  {{ abbr:'WI', label:'Choice Programs (2025&ndash;26)', geo: wiGeo, key:'students', nameKey:'name', unit:'ZIP code' }},
  {{ abbr:'MO', label:'MOScholars ESA (SY2026&ndash;27)', geo: moGeo, key:'students', nameKey:'name', unit:'school district' }},
  {{ abbr:'AR', label:'LEARNS EFA (2024&ndash;25, by school county)', geo: arGeo, key:'students', nameKey:'name', unit:'county' }},
];

function programCountsTable(abbr, idx) {{
  const layers = PROGRAM_LAYERS.filter(function(l) {{ return l.abbr === abbr; }});
  const li = layers[idx] ? idx : 0;
  const l = layers[li];
  const rows = l.geo.features.map(function(f, fi) {{ return {{ n: f.properties[l.nameKey], v: +f.properties[l.key] || 0, fi: fi }}; }})
    .filter(function(r) {{ return r.v > 0; }}).sort(function(a, b) {{ return b.v - a.v; }});
  const total = rows.reduce(function(s, r) {{ return s + r.v; }}, 0);
  const head = `<div class="sp-prog-head">${{fmt(total)}} across ${{fmt(rows.length)}} ${{l.unit}}${{rows.length === 1 ? '' : 's'}} with participants &mdash; click any ${{l.unit}} for its full metrics</div>`;
  const list = rows.map(function(r) {{ return `<div class="sp-kv-row sp-area-row" onclick="showAreaDetail('${{abbr}}',${{li}},${{r.fi}})"><span class="k">${{r.n}}</span><span class="v">${{fmt(r.v)}} &rsaquo;</span></div>`; }}).join('');
  return head + `<div class="sp-prog-list">${{list}}</div>`;
}}

// Resolves a clicked map polygon back to its PROGRAM_LAYERS entry + feature
// index, then drills in. Identity comparison on the geo object is what ties a
// Leaflet layer to its PROGRAM_LAYERS row (states can have several layers, e.g.
// Arizona's two fiscal years). Falls back to the state profile if the layer
// isn't a program layer (so a click can never dead-end).
function drillToArea(abbr, geo, feature) {{
  const layers = PROGRAM_LAYERS.filter(function(l) {{ return l.abbr === abbr; }});
  let li = -1;
  for (let i = 0; i < layers.length; i++) {{ if (layers[i].geo === geo) {{ li = i; break; }} }}
  const fi = geo.features.indexOf(feature);
  if (li < 0 || fi < 0) {{ showStateProfile(abbr); return; }}
  showAreaDetail(abbr, li, fi);
}}

// Returns from an area drill-down to its state, restoring the pre-drill map view.
function backToState(abbr) {{
  // Only restore the remembered view if we're still in the region it was taken
  // in - the region switcher locks the map to that region's bounds, so a stale
  // CONUS view would just be clamped somewhere arbitrary.
  if (preDrillView && preDrillView.region === activeRegion) {{
    map.setView(preDrillView.center, preDrillView.zoom);
  }}
  showStateProfile(abbr);
}}

// Drill-down: all metrics/analytics for a single choropleth area (e.g. one county).
// `keepView` re-renders in place (used when a layer toggle changes) instead of
// re-framing the map, so toggling schools doesn't re-zoom under the user.
function showAreaDetail(abbr, layerIdx, fi, keepView) {{
  const layers = PROGRAM_LAYERS.filter(function(l) {{ return l.abbr === abbr; }});
  const l = layers[layerIdx]; if (!l) return;
  const f = l.geo.features[fi]; if (!f) return;

  // Zoom to the area so "drilling in" actually moves the map in on it. Remember
  // where we came from only on the FIRST drill, so hopping between areas still
  // returns to the original view rather than the previous area's frame.
  if (!keepView) {{
    if (!preDrillView) {{ preDrillView = {{ center: map.getCenter(), zoom: map.getZoom(), region: activeRegion }}; }}
    try {{ map.fitBounds(L.geoJSON(f).getBounds(), {{ padding: [40, 40], maxZoom: 11 }}); }} catch (err) {{}}
  }}
  currentView = 'area';
  currentAbbr = abbr;
  currentArea = {{ abbr: abbr, layerIdx: layerIdx, fi: fi }};
  const p = f.properties, name = p[l.nameKey], part = +p[l.key] || 0;
  const pop = p.pop, acsPriv = p.acsPriv;
  const prof = STATE_PROFILES[abbr], prog = primaryProgram(prof);
  const inArea = (SCHOOLS_ALL[abbr] || []).filter(function(s) {{ return pointInFeature(s.lon, s.lat, f.geometry); }});
  const seats = inArea.reduce(function(t, s) {{ return t + (s.enroll || 0); }}, 0);
  const lvl = {{ Elementary: 0, Combined: 0, Secondary: 0 }}, rel = {{ Catholic: 0, 'Other religious': 0, Nonsectarian: 0 }};
  inArea.forEach(function(s) {{ if (lvl[s.level] != null) lvl[s.level]++; if (rel[s.relig] != null) rel[s.relig]++; }});
  const desert = part > 0 && inArea.length === 0;
  const pps = seats ? (part / seats).toFixed(2) : null;

  document.documentElement.style.setProperty('--accent', STATE_ACCENT[abbr] || '#898781');
  spTitle.textContent = name;
  let html = `<button class="sp-linkbtn" onclick="backToState('${{abbr}}')">&larr; Back to ${{prof.name}}</button>
    <div class="sp-section"><div class="sp-label">${{name}} &mdash; ${{l.unit}} in ${{prof.name}}</div>${{layers.length > 1 ? `<div class="sp-note" style="margin-top:2px;">${{l.label}}</div>` : ''}}</div>`;

  html += drawer('Program participation', `
    <div class="sp-stat">${{fmt(part)}}</div>
    <div class="sp-stat-sub">${{prog ? prog.unit : 'participants'}}${{prog ? ' &mdash; ' + prog.label : ''}}</div>`, true);

  html += drawer('Private-school supply here', `
    ${{desert ? '<div class="gap-verdict gap-bad">Access desert &mdash; program demand, no private school located here</div>' : ''}}
    <div class="sp-kv-row"><span class="k">Private schools in this ${{l.unit}}</span><span class="v">${{fmt(inArea.length)}}</span></div>
    <div class="sp-kv-row"><span class="k">Private-school seats</span><span class="v">${{fmt(seats)}}</span></div>
    <div class="sp-kv-row"><span class="k">Participants per seat</span><span class="v">${{pps != null ? pps : 'n/a (no seats)'}}</span></div>
    <div class="sp-kv-row"><span class="k">By level</span><span class="v">Elem ${{lvl.Elementary}} &middot; K&ndash;12 ${{lvl.Combined}} &middot; High ${{lvl.Secondary}}</span></div>
    <div class="sp-kv-row"><span class="k">By type</span><span class="v">Cath ${{rel.Catholic}} &middot; Other rel. ${{rel['Other religious']}} &middot; Nonsect. ${{rel.Nonsectarian}}</span></div>`, true);

  let acsBody;
  if (pop != null && pop > 0) {{
    acsBody = `
      <div class="sp-kv-row"><span class="k">School-age children (ACS)</span><span class="v">${{fmt(pop)}}</span></div>
      <div class="sp-kv-row"><span class="k">Take-up rate</span><span class="v">${{(100 * part / pop).toFixed(1)}}%</span></div>
      <div class="sp-kv-row"><span class="k">Seats per 1,000 children</span><span class="v">${{Math.round(1000 * seats / pop)}}</span></div>
      <div class="sp-kv-row"><span class="k">ACS private-school share</span><span class="v">${{acsPriv != null ? (100 * acsPriv / pop).toFixed(1) + '%' : 'n/a'}}</span></div>`;
  }} else {{
    acsBody = `<div class="sp-note" style="padding:6px 0;">This ${{l.unit}} couldn't be matched to the ACS, so per-child rates aren't available here.</div>`;
  }}
  html += drawer('Per-child access (ACS denominators)', acsBody, false);

  const schoolList = inArea.slice().sort(function(a, b) {{ return (b.enroll || 0) - (a.enroll || 0); }}).map(function(s) {{
    return `<div class="sp-school-row"><span class="sp-school-name">${{s.name}}</span><span class="sp-school-meta">${{s.city}} &middot; ${{s.level}}${{s.enroll ? ' &middot; ' + fmt(s.enroll) : ''}}</span></div>`;
  }}).join('');
  html += drawer(`Private schools located here (${{fmt(inArea.length)}})`,
    schoolList ? `<div class="sp-schoollist">${{schoolList}}</div>` : '<div class="sp-note" style="padding:6px 0;">None in our directory for this ' + l.unit + '.</div>', false);

  html += `<div class="sp-note">Participation is reported by ${{(prog && prog.areaLabel) || l.unit}}; the private schools shown are those physically located in this ${{l.unit}}${{(prog && prog.areaLabel && prog.areaLabel.indexOf('residence') >= 0) ? ' &mdash; note these differ, since counts are by where families live, not where schools are' : ''}}.</div>`;
  spBody.innerHTML = html;
  spBody.scrollTop = 0;
  openPanel();
}}

function programCountsBody(abbr) {{
  const layers = PROGRAM_LAYERS.filter(function(l) {{ return l.abbr === abbr; }});
  if (!layers.length) return '';
  let head;
  if (layers.length > 1) {{
    head = `<div class="sp-prog-filter">Program: <select onchange="programCountsSelect('${{abbr}}', this.value)">`
      + layers.map(function(l, i) {{ return `<option value="${{i}}">${{l.label}}</option>`; }}).join('')
      + `</select></div>`;
  }} else {{
    head = `<div class="sp-prog-filter one">${{layers[0].label}}</div>`;
  }}
  return head + `<div id="prog-counts-table">${{programCountsTable(abbr, 0)}}</div>`;
}}

function programCountsSelect(abbr, i) {{
  const el = document.getElementById('prog-counts-table');
  if (el) el.innerHTML = programCountsTable(abbr, parseInt(i, 10) || 0);
}}

// ---- Access analysis (the actionable supply-vs-demand synthesis) ----
function card(num, lbl) {{ return `<div class="sp-card"><div class="num">${{num}}</div><div class="lbl">${{lbl}}</div></div>`; }}
function openAbout() {{ document.getElementById('about-page').classList.add('open'); }}
function closeAbout() {{ document.getElementById('about-page').classList.remove('open'); }}
function openMethod() {{ document.getElementById('methodology-page').classList.add('open'); }}
function closeMethod() {{ document.getElementById('methodology-page').classList.remove('open'); }}

// ---- Open-data page: raw tables per state, with CSV export ----
function openData() {{ document.getElementById('data-page').classList.add('open'); buildDataPageOnce(); }}
function closeData() {{ document.getElementById('data-page').classList.remove('open'); }}
function _stateName(abbr) {{ return (STATE_PROFILES[abbr] && STATE_PROFILES[abbr].name) || abbr; }}
function _cap(s) {{ return s.charAt(0).toUpperCase() + s.slice(1); }}

let dataPageBuilt = false;
function buildDataPageOnce() {{
  if (dataPageBuilt) return;
  dataPageBuilt = true;
  const abbrs = Array.from(new Set(Object.keys(SCHOOLS_ALL).concat(PROGRAM_LAYERS.map(function(l) {{ return l.abbr; }}))));
  abbrs.sort(function(a, b) {{ return _stateName(a).localeCompare(_stateName(b)); }});
  const host = document.getElementById('data-states');
  host.innerHTML = abbrs.map(function(abbr) {{
    const n = (SCHOOLS_ALL[abbr] || []).length;
    const prog = PROGRAM_LAYERS.some(function(l) {{ return l.abbr === abbr; }});
    const badge = `<span class="data-badge">${{fmt(n)}} schools${{prog ? ' &middot; program data' : ''}}</span>`;
    return `<details class="data-state" data-abbr="${{abbr}}"><summary>${{_stateName(abbr)}} ${{badge}}</summary><div class="data-state-body"></div></details>`;
  }}).join('');
  host.querySelectorAll('details.data-state').forEach(function(d) {{
    d.addEventListener('toggle', function() {{
      if (d.open && !d.dataset.filled) {{ d.dataset.filled = '1'; d.querySelector('.data-state-body').innerHTML = dataStateBody(d.dataset.abbr); }}
    }});
  }});
}}

function _schoolFlag(abbr) {{
  const s = SCHOOLS_ALL[abbr] || [];
  if (s.some(function(x) {{ return x.efa; }})) return 'efa';
  if (s.some(function(x) {{ return x.boost; }})) return 'boost';
  if (s.some(function(x) {{ return x.scholarship; }})) return 'scholarship';
  return null;
}}

function dataStateBody(abbr) {{
  let html = '';
  PROGRAM_LAYERS.filter(function(l) {{ return l.abbr === abbr; }}).forEach(function(l, li) {{
    const rows = l.geo.features.map(function(f) {{ return [f.properties[l.nameKey], +f.properties[l.key] || 0]; }})
      .filter(function(r) {{ return r[1] > 0; }}).sort(function(a, b) {{ return b[1] - a[1]; }});
    const total = rows.reduce(function(s, r) {{ return s + r[1]; }}, 0);
    html += `<div class="data-subhead"><span>Program participation &mdash; ${{l.label}} (${{fmt(total)}} across ${{fmt(rows.length)}} ${{l.unit}}${{rows.length === 1 ? '' : 's'}})</span><button class="data-dl" onclick="downloadTable('${{abbr}}','prog',${{li}})">Download CSV</button></div>`;
    html += `<div class="data-table-wrap"><table class="data-tbl"><thead><tr><th>${{_cap(l.unit)}}</th><th>Reported count</th></tr></thead><tbody>`
      + rows.map(function(r) {{ return `<tr><td>${{r[0]}}</td><td class="num">${{fmt(r[1])}}</td></tr>`; }}).join('') + `</tbody></table></div>`;
  }});
  const schools = SCHOOLS_ALL[abbr] || [];
  const flag = _schoolFlag(abbr);
  const flagHead = flag === 'efa' ? '<th>EFA / total</th>' : flag === 'boost' ? '<th>BOOST (award)</th>' : flag === 'scholarship' ? '<th>MOScholars $</th>' : '';
  html += `<div class="data-subhead"><span>Private schools (${{fmt(schools.length)}})</span><button class="data-dl" onclick="downloadTable('${{abbr}}','schools',0)">Download CSV</button></div>`;
  html += `<div class="data-table-wrap"><table class="data-tbl"><thead><tr><th>Name</th><th>City</th><th>ZIP</th><th>Level</th><th>Religion</th><th>Coed</th><th>Enroll</th>${{flagHead}}<th>Geocode</th></tr></thead><tbody>`;
  html += schools.map(function(s) {{
    let fc = '';
    if (flag === 'efa') fc = `<td class="num">${{s.efa ? s.efa.efa + ' / ' + s.efa.total : ''}}</td>`;
    else if (flag === 'boost') fc = `<td class="num">${{s.boost ? fmt(s.boost.students) + ' ($' + fmt(s.boost.award) + ')' : ''}}</td>`;
    else if (flag === 'scholarship') fc = `<td class="num">${{s.scholarship ? '$' + fmt(s.scholarship.amount) : ''}}</td>`;
    return `<tr><td>${{s.name}}</td><td>${{s.city || ''}}</td><td>${{s.zip || ''}}</td><td>${{s.level}}</td><td>${{s.relig}}</td><td>${{s.coed}}</td><td class="num">${{s.enroll == null ? '' : fmt(s.enroll)}}</td>${{fc}}<td>${{s.geo_method || ''}}</td></tr>`;
  }}).join('') + `</tbody></table></div>`;
  return html;
}}

function _csv(headers, rows) {{
  const esc = function(v) {{ v = (v == null ? '' : String(v)); return /[",\\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; }};
  return [headers.join(',')].concat(rows.map(function(r) {{ return r.map(esc).join(','); }})).join('\\n');
}}
function _downloadCSV(filename, csv) {{
  const blob = new Blob([csv], {{ type: 'text/csv;charset=utf-8' }});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(function() {{ URL.revokeObjectURL(url); }}, 1500);
}}
function downloadTable(abbr, kind, idx) {{
  if (kind === 'prog') {{
    const l = PROGRAM_LAYERS.filter(function(x) {{ return x.abbr === abbr; }})[idx];
    const rows = l.geo.features.map(function(f) {{ return [f.properties[l.nameKey], +f.properties[l.key] || 0]; }})
      .filter(function(r) {{ return r[1] > 0; }}).sort(function(a, b) {{ return b[1] - a[1]; }});
    _downloadCSV(abbr + '_' + l.label.replace(/[^a-z0-9]+/gi, '_').replace(/^_|_$/g, '') + '.csv', _csv([l.unit, 'reported_count'], rows));
  }} else {{
    const schools = SCHOOLS_ALL[abbr] || [];
    const base = ['id', 'name', 'address', 'city', 'zip', 'state', 'level', 'type', 'relig', 'coed', 'enroll', 'enroll_source', 'geo_method', 'lon', 'lat'];
    const flag = _schoolFlag(abbr);
    const extra = flag === 'efa' ? ['efa_students', 'efa_total'] : flag === 'boost' ? ['boost_students', 'boost_award'] : flag === 'scholarship' ? ['scholarship_amount'] : [];
    const rows = schools.map(function(s) {{
      const r = base.map(function(c) {{ return s[c]; }});
      if (flag === 'efa') r.push(s.efa ? s.efa.efa : '', s.efa ? s.efa.total : '');
      else if (flag === 'boost') r.push(s.boost ? s.boost.students : '', s.boost ? s.boost.award : '');
      else if (flag === 'scholarship') r.push(s.scholarship ? s.scholarship.amount : '');
      return r;
    }});
    _downloadCSV('schools_' + abbr + '.csv', _csv(base.concat(extra), rows));
  }}
}}

// Gold-standard supply-side view for programs with a by-school breakdown (MD BOOST):
// which private schools actually enroll voucher students, and how concentrated.
function boostSection(b) {{
  if (!b) return '';
  return `<div class="sp-subhead">Where the scholarships actually go</div>
    <p class="sp-lead" style="font-size:12.5px;">${{fmt(b.participatingSchools)}} of the state's ${{fmt(b.privateSchoolsInState)}} private schools (${{b.pctPrivateSchoolsParticipating}}%) enrolled a BOOST student, across ${{b.countiesWithParticipation}} counties &mdash; but the <b>top 5 schools take ${{b.top5SharePct}}%</b> of all recipients.</p>
    <div class="sp-cards">
      ${{card(fmt(b.participatingSchools), 'private schools enroll BOOST students')}}
      ${{card('$' + fmt(b.avgAwardPerStudent), 'average award per student')}}
      ${{card(b.top5SharePct + '%', 'of recipients at the top 5 schools')}}
    </div>
    <div class="sp-note">Largest: ${{b.topSchoolName}} (${{fmt(b.topSchoolStudents)}} students). Award total ${{'$' + fmt(b.totalAward)}}.</div>`;
}}

// Gold-standard supply-side view for MOScholars: which private schools received
// scholarship dollars in SY2025-26, and how concentrated the funding is.
function scholarshipSection(b) {{
  if (!b) return '';
  return `<div class="sp-subhead">Where the scholarship funds go</div>
    <p class="sp-lead" style="font-size:12.5px;">${{fmt(b.schoolsFunded)}} private schools received MOScholars funds in ${{b.year}} (${{b.pctPrivateSchoolsFunded}}% of the state's ${{fmt(b.privateSchoolsInState)}}), and the <b>top 5 took ${{b.top5SharePct}}%</b> of the ${{'$' + fmt(b.totalFunds)}} awarded.</p>
    <div class="sp-cards">
      ${{card(fmt(b.schoolsFunded), 'private schools funded')}}
      ${{card('$' + fmt(b.avgFundsPerSchool), 'average funds per school')}}
      ${{card(b.top5SharePct + '%', 'of funds at the top 5 schools')}}
    </div>
    <div class="sp-note">Largest: ${{b.topSchoolName}} (${{'$' + fmt(b.topSchoolFunds)}}).</div>`;
}}

// Gold-standard supply-side view for AR LEARNS EFA: which private schools enroll
// EFA students, how much of their capacity is EFA, and how concentrated it is.
function efaSection(b) {{
  if (!b) return '';
  return `<div class="sp-subhead">Where EFA students attend</div>
    <p class="sp-lead" style="font-size:12.5px;">${{fmt(b.participatingSchools)}} private schools enrolled ${{fmt(b.efaStudents)}} EFA students in ${{b.year}} &mdash; on average <b>${{b.avgEfaSharePct}}% of their seats</b>; the top 5 hold ${{b.top5SharePct}}% of all EFA students.</p>
    <div class="sp-cards">
      ${{card(fmt(b.participatingSchools), 'private schools enroll EFA students')}}
      ${{card(b.avgEfaSharePct + '%', 'of participating-school seats are EFA')}}
      ${{card(b.top5SharePct + '%', 'of EFA students at the top 5 schools')}}
    </div>
    <div class="sp-note">Largest: ${{b.topSchoolName}} (${{fmt(b.topSchoolEfa)}} EFA students). ${{fmt(b.shownOnMap)}} of ${{fmt(b.participatingSchools)}} schools located on the map (${{fmt(b.matchedToDirectory)}} via the directory + ${{fmt(b.geocodedExtras)}} geocoded); the rest are counted here but not shown as dots.</div>`;
}}

function accessBody(profile, abbr) {{
  const a = profile.access;
  const programList = profile.programs || (profile.program ? [profile.program] : []);
  const demand = programList.map(function(p) {{
    return `<div class="sp-kv-row"><span class="k">${{p.label}}</span><span class="v">${{fmt(p.total)}} ${{p.unit}}</span></div>`;
  }}).join('');
  if (!a) return demand || '<div class="sp-empty">No data loaded.</div>';

  if (a.hasProgram && a.takeUpRatePct != null) {{
    let lead;
    if (a.pctChildrenInDesert >= 25)
      lead = `Access is <b>uneven</b> &mdash; about <b>${{a.pctChildrenInDesert}}%</b> of ${{profile.name}}'s school-age kids live where there's no private school to use the program.`;
    else if (a.participantsPerSeat >= 1.5)
      lead = `<b>Demand outstrips</b> local private schools &mdash; roughly ${{a.participantsPerSeat}} participants for every private-school seat, so much of the funding is used outside private schools.`;
    else if (a.participantsPerSeat <= 0.75)
      lead = `${{profile.name}} has <b>ample</b> private-school capacity &mdash; well under one participant per seat, and access is spread widely.`;
    else
      lead = `In ${{profile.name}}, program use is <b>roughly in line</b> with private-school capacity, and access is fairly widespread.`;
    return `${{demand}}
      <p class="sp-lead">${{lead}}</p>
      <div class="sp-cards">
        ${{card(a.takeUpRatePct + '%', 'of school-age kids use it')}}
        ${{card(a.participantsPerSeat, 'participants per private-school seat')}}
        ${{card(a.pctChildrenInDesert + '%', 'of kids have no private school nearby')}}
      </div>
      ${{boostSection(profile.boost)}}
      ${{scholarshipSection(profile.scholarship)}}
      ${{efaSection(profile.efa)}}
      <button class="sp-howlink" onclick="openAbout()">How we measure this &rarr;</button>`;
  }}
  return `${{demand}}
    <p class="sp-lead">${{profile.name}} has <b>${{fmt(a.schools)}}</b> private schools${{a.seats ? ' (about ' + fmt(a.seats) + ' seats)' : ''}}. No school-choice program is loaded here yet, so this is the supply picture only.</p>
    <div class="sp-cards">
      ${{card(fmt(a.schools), 'private schools')}}
      ${{card(a.seats ? fmt(a.seats) : 'n/a', 'private-school seats')}}
      ${{card(a.seatsPerSchool ? fmt(a.seatsPerSchool) : 'n/a', 'avg seats per school')}}
    </div>
    <button class="sp-howlink" onclick="openAbout()">How we measure this &rarr;</button>`;
}}

function nationalAccessBody(n) {{
  const a = n.access;
  return `
    <p class="sp-lead">Nationwide, <b>${{fmt(n.totalParticipation)}}</b> students use a tracked school-choice program &mdash; but whether there's a private school to use it <b>varies enormously</b> by state.</p>
    <div class="sp-cards">
      ${{card(a.usPrivatePct != null ? a.usPrivatePct + '%' : 'n/a', 'of U.S. kids attend private school')}}
      ${{card(a.ppsMax[1], 'participants/seat in ' + a.ppsMax[0] + ' (tightest)')}}
      ${{card(a.ppsMin[1], 'participants/seat in ' + a.ppsMin[0] + ' (loosest)')}}
    </div>
    <p class="sp-lead" style="font-size:12.5px;color:var(--text-secondary);">Tuition-scholarship states (Florida, Texas, Rhode Island) have room to spare; ESA &amp; correspondence states (Arizona, Alaska) have far more users than local private seats &mdash; a sign the money goes to home, micro, or online schooling.</p>
    <button class="sp-howlink" onclick="openAbout()">How we measure this &rarr;</button>
    <div class="sp-note">Click any state on the map for its own numbers &mdash; then click any shaded area (ZIP code, county or school district) to drill into that area's own participation, private-school supply and per-child access.</div>`;
}}

// ---- School characteristics (the collapsed "additional data from the states") ----
function characteristicsBody(s) {{
  let html = `
    <div class="sp-stat">${{fmt(s.count)}}</div>
    <div class="sp-stat-sub">private schools (${{s.sourceLabel || 'NCES directory'}})`;
  if (s.totalEnrollment) {{
    html += ` &middot; ${{fmt(s.totalEnrollment)}} enrolled seats${{s.seatsNces ? ` (${{fmt(s.seatsStateReported || 0)}} state-reported + ${{fmt(s.seatsNces)}} NCES 2023&ndash;24)` : ''}}`;
  }}
  html += `</div>
    <div class="sp-subhead">Religious affiliation</div>${{barRows(s.religion, s.count)}}
    <div class="sp-subhead">School level</div>${{barRows(s.level, s.count)}}
    <div class="sp-subhead">Coed status</div>${{barRows(s.coed, s.count)}}`;
  const typeKeys = s.type ? Object.keys(s.type) : [];
  if (typeKeys.length && !(typeKeys.length === 1 && s.type['Not reported'])) {{
    html += `<div class="sp-subhead">School type</div>${{barRows(s.type, s.count)}}`;
  }}
  if (s.approx > 0) html += `<div class="sp-note">${{s.approx}} of ${{fmt(s.count)}} schools geocoded at city/zip level (exact street address could not be resolved).</div>`;
  // The directory count above is the citable one; the map also draws program-only
  // extras (schools in a program's by-school table but absent from the directory),
  // so state the difference rather than leaving two counts unexplained.
  if (s.programOnlyExtras > 0) {{
    html += `<div class="sp-note">Counts above are directory schools. The map draws ${{fmt(s.mapPoints)}} points in total &mdash; the ${{s.programOnlyExtras}} extra are schools named in a program's own by-school report but absent from the directory, geocoded by name + city and shown as approximate program-only dots.</div>`;
  }}
  html += sourceNote(s.sourceKey || 'SCHOOLS');
  return html;
}}

// ---- Guided tools: entrepreneur gap-finder + parent school-finder ----
const WIZ = {{ mode: null, step: 0, ans: {{}}, loc: null }};
const WIZ_CFG = {{
  entrepreneur: {{
    title: 'Find an access gap to fill',
    steps: [
      {{ key: 'scope', q: 'Where do you want to look for opportunity?', type: 'state', all: 'Compare all program states' }},
      {{ key: 'level', q: 'Which grade level are you thinking about serving?', opts: [['any', 'Any / not sure'], ['Elementary', 'Elementary'], ['Combined', 'K–12 (combined)'], ['Secondary', 'High school']] }},
      {{ key: 'model', q: 'What kind of school model?', opts: [['any', 'Any'], ['faith', 'Faith-based'], ['secular', 'Secular / nonsectarian']] }},
      {{ key: 'radius', q: 'How far will families travel to reach a new school? (your catchment area)', opts: [['10', 'About 10 miles'], ['25', 'About 25 miles'], ['40', 'About 40 miles']] }},
      {{ key: 'priority', q: 'Rank the opportunities by what matters most to you.', opts: [['balance', 'Best balance of demand vs. nearby competition'], ['demand', 'Biggest markets (most program students)'], ['whitespace', 'Least competition (fewest nearby schools)']] }},
    ],
  }},
  parent: {{
    title: 'Find a private school for your child',
    steps: [
      {{ key: 'loc', q: 'Where do you live? Enter an address, city, or ZIP.', type: 'address' }},
      {{ key: 'level', q: 'What grade level is your child?', opts: [['any', 'Any / not sure'], ['Elementary', 'Elementary'], ['Combined', 'K–12 (combined)'], ['Secondary', 'High school']] }},
      {{ key: 'faith', q: 'Any preference on school type?', opts: [['any', 'No preference'], ['Catholic', 'Catholic'], ['Other religious', 'Other religious'], ['Nonsectarian', 'Nonsectarian / secular']] }},
      {{ key: 'radius', q: 'How far are you willing to travel?', opts: [['10', 'Within 10 miles'], ['25', 'Within 25 miles'], ['50', 'Within 50 miles']] }},
    ],
  }},
}};

function openWizard(mode) {{ WIZ.mode = mode; WIZ.step = 0; WIZ.ans = {{}}; WIZ.loc = null; WIZ.partOnly = false; document.getElementById('wizard').classList.add('open'); renderWizard(); }}
function closeWizard() {{ document.getElementById('wizard').classList.remove('open'); }}
function wizBack() {{ if (WIZ.step > 0) {{ WIZ.step--; renderWizard(); }} }}
function wizAnswer(key, val) {{ WIZ.ans[key] = val; WIZ.step++; renderWizard(); }}

function renderWizard() {{
  const cfg = WIZ_CFG[WIZ.mode];
  document.getElementById('wiz-title').textContent = cfg.title;
  const body = document.getElementById('wiz-body');
  if (WIZ.step >= cfg.steps.length) {{ body.innerHTML = (WIZ.mode === 'entrepreneur' ? entrepreneurResults() : parentResults()); return; }}
  const st = cfg.steps[WIZ.step];
  let inner = `<div class="wiz-progress">Step ${{WIZ.step + 1}} of ${{cfg.steps.length}}</div><div class="wiz-q">${{st.q}}</div>`;
  if (st.type === 'state') {{
    const progs = Array.from(new Set(PROGRAM_LAYERS.map(function(l) {{ return l.abbr; }}))).sort(function(a, b) {{ return _stateName(a).localeCompare(_stateName(b)); }});
    inner += `<select class="wiz-select" id="wiz-state"><option value="all">${{st.all}}</option>` + progs.map(function(a) {{ return `<option value="${{a}}">${{_stateName(a)}}</option>`; }}).join('') + `</select><button class="wiz-go" onclick="wizAnswer('${{st.key}}', document.getElementById('wiz-state').value)">Continue</button>`;
  }} else if (st.type === 'address') {{
    inner += `<input class="wiz-input" id="wiz-addr" type="text" placeholder="e.g. 123 Main St, Springfield, MO" /><div id="wiz-addr-status" class="wiz-note"></div><button class="wiz-go" onclick="wizGeocode()">Find my area</button>`;
  }} else {{
    inner += `<div class="wiz-opts">` + st.opts.map(function(o) {{ return `<button class="wiz-opt" onclick="wizAnswer('${{st.key}}','${{o[0]}}')">${{o[1]}}</button>`; }}).join('') + `</div>`;
  }}
  if (WIZ.step > 0) inner += `<button class="wiz-back" onclick="wizBack()">&larr; Back</button>`;
  body.innerHTML = inner;
  const ai = document.getElementById('wiz-addr'); if (ai) ai.focus();
}}

function wizGeocode() {{
  const q = document.getElementById('wiz-addr').value.trim();
  if (!q) return;
  const stEl = document.getElementById('wiz-addr-status'); stEl.textContent = 'Searching…';
  const url = 'https://nominatim.openstreetmap.org/search?' + new URLSearchParams({{ q: q, format: 'json', limit: '1', countrycodes: 'us', addressdetails: '1' }});
  fetch(url, {{ headers: {{ 'Accept': 'application/json' }} }}).then(function(r) {{ return r.json(); }}).then(function(d) {{
    if (!d || !d.length) {{ stEl.textContent = 'No match — add a city and state, or a ZIP.'; return; }}
    const h = d[0]; let abbr = null;
    const iso = h.address && h.address['ISO3166-2-lvl4']; if (iso && iso.indexOf('US-') === 0) abbr = iso.slice(3);
    if (!abbr && h.address && h.address.state) abbr = STATE_ABBR[h.address.state];
    WIZ.loc = {{ lat: parseFloat(h.lat), lon: parseFloat(h.lon), abbr: abbr, name: (h.display_name || q).split(',').slice(0, 3).join(',') }};
    WIZ.ans.loc = WIZ.loc.name; WIZ.step++; renderWizard();
  }}).catch(function() {{ stEl.textContent = 'Search failed — check your connection.'; }});
}}

function _schoolMatches(s, level, model) {{
  if (level && level !== 'any' && s.level !== level && s.level !== 'Combined') return false;
  if (model === 'faith' && !(s.relig === 'Catholic' || s.relig === 'Other religious')) return false;
  if (model === 'secular' && s.relig !== 'Nonsectarian') return false;
  return true;
}}
function featureCentroid(geom) {{
  let sx = 0, sy = 0, n = 0;
  const rings = geom.type === 'Polygon' ? [geom.coordinates[0]]
    : geom.type === 'MultiPolygon' ? geom.coordinates.map(function(p) {{ return p[0]; }}) : [];
  rings.forEach(function(r) {{ r.forEach(function(pt) {{ sx += pt[0]; sy += pt[1]; n++; }}); }});
  return n ? [sx / n, sy / n] : [0, 0];
}}
function _reportedPct(schools, field) {{
  if (!schools.length) return 0;
  return schools.filter(function(s) {{ return s[field] && s[field] !== 'Not reported'; }}).length / schools.length;
}}

function entrepreneurResults() {{
  const a = WIZ.ans, level = a.level, model = a.model;
  const radius = parseInt(a.radius, 10) || 25, priority = a.priority || 'balance';
  const modelLbl = model === 'faith' ? 'faith-based ' : model === 'secular' ? 'secular ' : '';
  const levelLbl = level && level !== 'any' ? level.toLowerCase() + ' ' : '';
  let html = `<button class="wiz-back" onclick="wizBack()">&larr; Change answers</button>`;
  if (a.scope === 'all') {{
    let rows = Object.keys(STATE_PROFILES).filter(function(x) {{ const c = STATE_PROFILES[x].access; return c && c.hasProgram && c.participantsPerSeat != null; }})
      .map(function(x) {{ const c = STATE_PROFILES[x].access, pg = primaryProgram(STATE_PROFILES[x]); return {{ x: x, name: STATE_PROFILES[x].name, pps: c.participantsPerSeat, desert: c.pctChildrenInDesert || 0, seatsK: c.seatsPer1000Kids, total: pg ? pg.total : 0 }}; }});
    if (priority === 'demand') rows.sort(function(p, q) {{ return q.total - p.total; }});
    else if (priority === 'whitespace') rows.sort(function(p, q) {{ return (p.seatsK || 0) - (q.seatsK || 0); }});
    else rows.sort(function(p, q) {{ return ((q.pps * 8) + q.desert) - ((p.pps * 8) + p.desert); }});
    rows = rows.slice(0, 6);
    const by = priority === 'demand' ? 'total program demand' : priority === 'whitespace' ? 'fewest private-school seats per child' : 'demand outstripping ' + modelLbl + 'private-school supply';
    html += `<div class="wiz-res-verdict">Program states ranked by ${{by}} &mdash; the biggest openings for a new ${{levelLbl}}school.</div>`;
    html += rows.map(function(r) {{ return `<div class="wiz-row"><div><div class="r-main">${{r.name}}</div><div class="r-sub">${{fmt(r.total)}} program students &middot; ${{r.pps}} per seat &middot; ${{r.desert}}% of kids in a desert &middot; ${{r.seatsK}} seats / 1,000 kids</div></div><div class="r-val"><button class="wiz-opt" style="padding:5px 10px;" onclick="closeWizard();showStateProfile('${{r.x}}')">Open</button></div></div>`; }}).join('');
    html += `<div class="wiz-note">Pick a single state to see the specific ZIPs, counties, or districts with the most demand and least competition within your catchment radius. &ldquo;Per seat&rdquo; above 1 means more program users than local private-school seats.</div>`;
    return html;
  }}
  const abbr = a.scope, lk = CHOROPLETH_LOOKUP[abbr], prof = STATE_PROFILES[abbr];
  const allStateSchools = SCHOOLS_ALL[abbr] || [];
  const relOk = _reportedPct(allStateSchools, 'relig') >= 0.3;
  const useModel = (model === 'any' || relOk) ? model : 'any';
  const schools = allStateSchools.filter(function(s) {{ return _schoolMatches(s, level, useModel); }});
  const areas = lk.geo.features.map(function(f) {{
    const ctr = featureCentroid(f.geometry);
    let comp = 0;
    schools.forEach(function(s) {{ if (milesBetween(ctr[1], ctr[0], s.lat, s.lon) <= radius) comp++; }});
    return {{ name: f.properties.name || ('ZIP ' + f.properties.zip), part: +f.properties[lk.valueKey] || 0, comp: comp }};
  }}).filter(function(z) {{ return z.part > 0; }});
  if (priority === 'demand') areas.sort(function(p, q) {{ return q.part - p.part; }});
  else if (priority === 'whitespace') areas.sort(function(p, q) {{ return (p.comp - q.comp) || (q.part - p.part); }});
  else areas.sort(function(p, q) {{ return (q.part / (q.comp + 1)) - (p.part / (p.comp + 1)); }});
  const c = prof.access || {{}};
  html += `<div class="wiz-res-verdict">In ${{prof.name}}, these ${{lk.geoUnit}}s have the most program demand with the fewest ${{modelLbl}}${{levelLbl}}private schools within ${{radius}} miles &mdash; the strongest openings for a new school.</div>`;
  if (model !== 'any' && !relOk) html += `<div class="wiz-note" style="margin-top:0;">Note: ${{prof.name}}'s directory doesn't report religious affiliation, so the ${{modelLbl}}filter couldn't be applied here &mdash; competition counts all private schools.</div>`;
  html += areas.slice(0, 10).map(function(z) {{ return `<div class="wiz-row"><div class="r-main">${{z.name}}</div><div class="r-val">${{fmt(z.part)}} students &middot; ${{z.comp}} school${{z.comp === 1 ? '' : 's'}} within ${{radius}} mi</div></div>`; }}).join('') || '<div class="wiz-note">No areas with participation found for this filter.</div>';
  html += `<div class="wiz-note">Statewide: ${{c.participantsPerSeat != null ? c.participantsPerSeat + ' participants per private-school seat, ' : ''}}${{c.pctChildrenInDesert != null ? c.pctChildrenInDesert + '% of children in an access desert. ' : ''}}Competition counts existing ${{modelLbl}}${{levelLbl}}private schools within ${{radius}} miles of each ${{lk.geoUnit}}'s center.</div>`;
  return html;
}}

function wizTogglePart() {{ WIZ.partOnly = !WIZ.partOnly; renderWizard(); }}

function parentResults() {{
  const a = WIZ.ans, level = a.level, faith = a.faith, loc = WIZ.loc;
  const radius = parseInt(a.radius, 10) || 50;
  let html = `<button class="wiz-back" onclick="wizBack()">&larr; Change answers</button>`;
  if (!loc) return html + '<div class="wiz-note">Please go back and enter a location.</div>';
  let near = nearbySchools(loc.lat, loc.lon, radius).filter(function(x) {{
    if (level !== 'any' && x.s.level !== level && x.s.level !== 'Combined') return false;
    if (faith !== 'any' && x.s.relig !== faith) return false;
    return true;
  }});
  const anyPart = near.some(function(x) {{ return x.s.efa || x.s.boost || x.s.scholarship; }});
  if (WIZ.partOnly) near = near.filter(function(x) {{ return x.s.efa || x.s.boost || x.s.scholarship; }});
  const prof = loc.abbr && STATE_PROFILES[loc.abbr], prog = prof && primaryProgram(prof);
  const faithLbl = faith !== 'any' ? faith.toLowerCase() + ' ' : '', levelLbl = level !== 'any' ? level.toLowerCase() + ' ' : '';
  if (prog) html += `<div class="wiz-res-verdict">${{prof.name}} offers <b>${{prog.label}}</b> &mdash; ${{fmt(prog.total)}} ${{prog.unit}} statewide. Your family may be eligible for funding toward private-school tuition. <button class="wiz-opt" style="display:inline-block;padding:3px 9px;margin-top:6px;" onclick="closeWizard();showStateProfile('${{loc.abbr}}')">See the program &rarr;</button></div>`;
  else html += `<div class="wiz-res-verdict">${{prof ? prof.name : 'Your state'}} has no school-choice program loaded here yet &mdash; the schools below would be private-pay unless a program applies.</div>`;
  if (anyPart) html += `<button class="wiz-opt" style="margin-bottom:11px;${{WIZ.partOnly ? 'border-color:var(--accent);' : ''}}" onclick="wizTogglePart()">${{WIZ.partOnly ? '\\u2713 Only schools that accept the scholarship &mdash; show all' : 'Show only schools that accept the scholarship'}}</button>`;
  html += `<div class="wiz-progress" style="margin-top:2px;">${{fmt(near.length)}} matching ${{faithLbl}}${{levelLbl}}private school${{near.length === 1 ? '' : 's'}} within ${{radius}} miles of ${{loc.name}}</div>`;
  html += near.slice(0, 15).map(function(x) {{
    const badge = (x.s.efa || x.s.boost || x.s.scholarship) ? ' <span style="color:var(--accent-dark);font-weight:600;">&middot; accepts funding</span>' : '';
    return `<div class="wiz-row"><div><div class="r-main">${{x.s.name}}${{badge}}</div><div class="r-sub">${{x.s.city}}, ${{x.abbr}} &middot; ${{x.s.level}}${{x.s.relig !== 'Not reported' ? ' &middot; ' + x.s.relig : ''}}${{x.s.enroll ? ' &middot; ' + fmt(x.s.enroll) + ' students' : ''}}</div></div><div class="r-val">${{x.d.toFixed(1)}} mi</div></div>`;
  }}).join('') || '<div class="wiz-note">No matching private schools within ' + radius + ' miles &mdash; an access desert for your criteria. Try a wider radius or fewer filters.</div>';
  if (near.length > 15) html += `<div class="wiz-note">Showing the 15 nearest of ${{fmt(near.length)}}. Search this address on the map for the full list and gap analysis.</div>`;
  return html;
}}

function showNationalProfile() {{
  currentAbbr = null;
  currentView = 'national';
  currentArea = null; preDrillView = null;
  document.documentElement.style.setProperty('--accent', '#eb6834');
  spTitle.textContent = NATIONAL_PROFILE.name;

  const n = NATIONAL_PROFILE;
  let html = schoolToggleCallout();
  html += drawer('Access analysis &mdash; supply vs. demand', nationalAccessBody(n), true);
  html += drawer('School characteristics (from directories)', characteristicsBody(n.schools), false);
  html += `<div class="sp-note" style="margin-top:12px;">Click any state on the map for its full profile. Click empty ocean/land to return here, or the &times; to close this panel.</div>`;
  spBody.innerHTML = html;
  openPanel();
}}

function showStateProfile(abbr) {{
  const profile = STATE_PROFILES[abbr];
  if (!profile) return;
  currentAbbr = abbr;
  currentView = 'state';
  currentArea = null; preDrillView = null;
  document.documentElement.style.setProperty('--accent', STATE_ACCENT[abbr] || '#898781');
  spTitle.textContent = profile.name;

  if (!profile.program && !profile.programs && !profile.schools) {{
    spBody.innerHTML = schoolToggleCallout(abbr) + `<div class="sp-empty">No school-choice program participation data or private-school directory has been loaded yet for ${{profile.name}}.</div>`;
    openPanel();
    return;
  }}

  // Same toggle as the national summary, but scoped to THIS state; then the
  // access analysis (open) and school characteristics (collapsed).
  let html = schoolToggleCallout(abbr);
  html += drawer('Access analysis &mdash; supply vs. demand', accessBody(profile, abbr), true);
  const progCounts = programCountsBody(abbr);
  if (progCounts) {{
    html += drawer('Reported program counts by area', progCounts, false);
  }}
  if (profile.schools) {{
    html += drawer('School characteristics (from directories)', characteristicsBody(profile.schools), false);
  }}
  spBody.innerHTML = html;
  openPanel();
}}

// The main canvas is locked to the continental US; Alaska and Hawaii are shown
// in their own inset maps (bottom-left) so they aren't lost off in the ocean.
const CONUS_BOUNDS = L.latLngBounds([[23.5, -130.5], [50.0, -65.5]]);
const map = L.map('map-conus', {{ zoomControl: true, minZoom: 4, maxZoom: 15, maxBounds: CONUS_BOUNDS, maxBoundsViscosity: 1.0 }});

// Pane stack, bottom -> top:
//   base tiles (tilePane 200, no labels) < choropleth fills (overlayPane 400)
//   < place-name labels (labelsPane 500) < school dots (schoolsPane 625).
// This keeps roads/water and place names legible ON TOP of the colored heatmaps
// instead of being tinted/obscured by them.
map.createPane('labelsPane');
map.getPane('labelsPane').style.zIndex = 500;
map.getPane('labelsPane').style.pointerEvents = 'none';
map.createPane('schoolsPane');
map.getPane('schoolsPane').style.zIndex = 625;

// Base map WITHOUT labels so the choropleths color the land/water/roads only;
// the label tiles are re-applied on top (labelsPane) so names stay crisp.
L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_nolabels/{{z}}/{{x}}/{{y}}{{r}}.png', {{
  attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
  subdomains: 'abcd', maxZoom: 19
}}).addTo(map);
L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_only_labels/{{z}}/{{x}}/{{y}}{{r}}.png', {{
  subdomains: 'abcd', maxZoom: 19, pane: 'labelsPane'
}}).addTo(map);

// ---- State boundary layer: click target for every state (Hawaii included).
// Alaska's raw outline crosses the antimeridian (a stray world-spanning sliver
// if drawn), so AK is excluded here and represented by its district choropleth
// instead, which carries the same click-to-profile behavior. ----
const stateBoundaryLayer = L.geoJSON(stateBoundariesGeo, {{
  filter: function(feature) {{ return feature.properties.statefp !== '02'; }},
  style: {{ fillColor: '#ffffff', fillOpacity: 0.01, color: '#6b6a63', weight: 1.8, opacity: 1, lineJoin: 'round' }},
  onEachFeature: function(feature, layer) {{
    const abbr = FIPS_TO_ABBR[feature.properties.statefp];
    layer.on('click', function(e) {{ L.DomEvent.stop(e); showStateProfile(abbr); }});
  }}
}});
stateBoundaryLayer.addTo(map);

// ---- AZ ESA zip choropleth (one instance per fiscal year/period) ----
function makeAzLayer(geo, edges, ramp, fiscalYearLabel, quarterKeys) {{
  return L.geoJSON(geo, {{
    style: function(feature) {{
      return {{ fillColor: colorFor(feature.properties.total, edges, ramp), weight: 0.6, color: '#ffffff', opacity: 1, fillOpacity: 0.72 }};
    }},
    onEachFeature: function(feature, layer) {{
      const p = feature.properties;
      // Each quarter is the enrollment LEVEL as of that quarter, not that
      // quarter's new sign-ups - the last one IS the year's figure, and adding
      // them together would multiply-count the same students.
      const lastKey = quarterKeys[quarterKeys.length - 1];
      const quarterRows = quarterKeys.map(function(qk, i) {{
        const isLast = qk === lastKey;
        return `<td class="q-label">Q${{i+1}}${{isLast ? ' &bull;' : ''}}</td><td>${{fmt(p[qk] || 0)}}</td>`;
      }});
      // lay quarters out two per row, same as the original Q1-Q4 layout
      let rows = '';
      for (let i = 0; i < quarterRows.length; i += 2) {{
        rows += `<tr>${{quarterRows[i]}}${{quarterRows[i+1] || ''}}</tr>`;
      }}
      const html = `
        <div class="zip-tooltip">
          <div class="zt-head">Zip ${{p.zip}} &mdash; Arizona</div>
          <div class="zt-total">${{fiscalYearLabel}}: <b>${{fmt(p.total)}}</b> ESA students</div>
          <table>${{rows}}</table>
          <div class="zt-foot">Enrollment as of each quarter &bull; not cumulative</div>
          <div class="zt-foot">Click for this ZIP code's full metrics &rsaquo;</div>
        </div>`;
      layer.bindTooltip(html, {{ sticky: true, className: 'zip-tt', direction: 'top' }});
      layer.on('mouseover', function() {{ layer.setStyle({{ weight: 2, color: '#0b0b0b' }}); layer.bringToFront(); }});
      layer.on('mouseout', function() {{ layer.setStyle({{ weight: 0.6, color: '#ffffff' }}); }});
      layer.on('click', function(e) {{ L.DomEvent.stop(e); drillToArea('AZ', geo, feature); }});
    }}
  }});
}}

const azLayer = makeAzLayer(azGeo, azEdges, azRamp, 'FY2024 (year-end Q4)', ['q1', 'q2', 'q3', 'q4']);
const azLayerFy2026 = makeAzLayer(azGeoFy2026, azFy2026Edges, azFy2026Ramp, 'FY2026 (as of Q3, partial year)', ['q1', 'q2', 'q3']);

// ---- Generic polygon choropleth builder for FL/TX/NH/WV/NC/AK/RI ----
function makeChoropleth(geo, edges, ramp, stateLabel, unitLabel, stateAbbr) {{
  // area noun comes from this layer's PROGRAM_LAYERS row, so the tooltip and the
  // drill-down panel always call the geography the same thing
  const entry = PROGRAM_LAYERS.filter(function(l) {{ return l.abbr === stateAbbr && l.geo === geo; }})[0];
  const areaNoun = (entry ? entry.unit : 'area').replace(' of residence', '');
  return L.geoJSON(geo, {{
    style: function(feature) {{
      return {{ fillColor: colorFor(feature.properties.students, edges, ramp), weight: 0.7, color: '#ffffff', opacity: 1, fillOpacity: 0.72 }};
    }},
    onEachFeature: function(feature, layer) {{
      const p = feature.properties;
      const html = `
        <div class="poly-tooltip">
          <div class="zt-head">${{p.name}}</div>
          <div class="zt-total">${{stateLabel}}: <b>${{fmt(p.students)}}</b> ${{unitLabel}}</div>
          <div class="zt-foot">Click for this ${{areaNoun}}'s full metrics &rsaquo;</div>
        </div>`;
      layer.bindTooltip(html, {{ sticky: true, className: 'poly-tt', direction: 'top' }});
      layer.on('mouseover', function() {{ layer.setStyle({{ weight: 2.2, color: '#0b0b0b' }}); layer.bringToFront(); }});
      layer.on('mouseout', function() {{ layer.setStyle({{ weight: 0.7, color: '#ffffff' }}); }});
      layer.on('click', function(e) {{ L.DomEvent.stop(e); drillToArea(stateAbbr, geo, feature); }});
    }}
  }});
}}

const flLayer = makeChoropleth(flGeo, flEdges, flRamp, 'FL FTC (2022-23)', 'scholarship students', 'FL');
const txLayer = makeChoropleth(txGeo, txEdges, txRamp, 'TX TEFA (2026-27)', 'participating students', 'TX');
const nhLayer = makeChoropleth(nhGeo, nhEdges, nhRamp, 'NH EFA (SY2025-26)', 'EFA enrollees', 'NH');
const wvLayer = makeChoropleth(wvGeo, wvEdges, wvRamp, 'WV Hope (2024-25)', 'Hope Scholarship recipients', 'WV');
const ncLayer = makeChoropleth(ncGeo, ncEdges, ncRamp, 'NC Opportunity Scholarship (2024-25)', 'recipients', 'NC');
const mdLayer = makeChoropleth(mdGeo, mdEdges, mdRamp, 'MD BOOST scholarships (2025-26)', 'BOOST students', 'MD');
const akLayer = makeChoropleth(akGeo, akEdges, akRamp, 'AK Correspondence Study (FY2024)', 'students enrolled', 'AK');
const riLayer = makeChoropleth(riGeo, riEdges, riRamp, 'RI SGO Scholarships (2025, 5 SGOs combined)', 'scholarships', 'RI');
const inLayer = makeChoropleth(inGeo, inEdges, inRamp, 'IN Choice Scholarship (2024-25, P1+P2)', 'students', 'IN');
const wiLayer = makeChoropleth(wiGeo, wiEdges, wiRamp, 'WI Choice Programs (2025-26)', 'students', 'WI');
const moLayer = makeChoropleth(moGeo, moEdges, moRamp, 'MO MOScholars ESA (SY2026-27, school district)', 'students', 'MO');
const arLayer = makeChoropleth(arGeo, arEdges, arRamp, 'AR LEARNS EFA (2024-25, by school county)', 'students', 'AR');

// ---- Exact-locations dots shrink at low zoom so a busy nationwide view stays readable;
// the clustered layer doesn't need this since it already bubbles nearby points together. ----
function radiusForZoom(zoom) {{
  if (zoom <= 4) return 1.5;
  if (zoom <= 6) return 2.5;
  if (zoom <= 8) return 3.5;
  if (zoom <= 10) return 4.5;
  return 5;
}}

// ---- Shared marker builder: one L.circleMarker per school, tooltip + click bound ----
function buildSchoolMarkers(schools, color, stateAbbr, radius) {{
  return schools.map(function(s) {{
    const marker = L.circleMarker([s.lat, s.lon], {{ radius: radius, fillColor: color, color: '#ffffff', weight: 1.5, fillOpacity: 0.9, pane: 'schoolsPane' }});
    const approx = ['nominatim_fallback','zcta_centroid_fallback','nominatim_zip_fallback','nominatim_town_fallback','nominatim_scholarship_lookup'].includes(s.geo_method);
    let enrollStr;
    if (s.enroll === null || s.enroll === undefined) {{ enrollStr = 'enrollment not reported'; }}
    else if (s.enroll_source === 'state_directory') {{ enrollStr = fmt(s.enroll) + ' students'; }}
    else {{ enrollStr = fmt(s.enroll) + ' students (NCES 2023&ndash;24)'; }}
    const html = `
      <div class="school-tooltip">
        <div class="zt-head">${{s.name}}</div>
        <div class="zt-sub">${{s.address}}, ${{s.city}} ${{s.zip}}</div>
        <div class="zt-row"><span>${{s.relig}}</span><span>${{s.coed}}</span></div>
        <div class="zt-row"><span>${{s.level}} &middot; ${{s.type}}</span></div>
        <div class="zt-row"><span>${{enrollStr}}</span></div>
        ${{s.boost ? `<div class="zt-boost">BOOST: ${{fmt(s.boost.students)}} scholarship students &middot; ${{'$' + fmt(s.boost.award)}}</div>` : ''}}
        ${{s.scholarship ? `<div class="zt-scholarship">MOScholars: ${{'$' + fmt(s.scholarship.amount)}} in scholarship funds (SY2025-26)</div>` : ''}}
        ${{s.efa ? `<div class="zt-efa">EFA: ${{fmt(s.efa.efa)}} of ${{fmt(s.efa.total)}} students (${{Math.round(100 * s.efa.efa / s.efa.total)}}%, 2024-25)</div>` : ''}}
        ${{approx ? '<div class="zt-approx">Approximate location (city/zip-level)</div>' : ''}}
      </div>`;
    marker.bindTooltip(html, {{ sticky: true, className: 'school-tt', direction: 'top' }});
    marker.on('click', function(e) {{ L.DomEvent.stop(e); showStateProfile(stateAbbr); }});
    return marker;
  }});
}}

// ---- Clustered view: aggregates nearby points into count bubbles when zoomed out ----
function makeClusterGroup() {{
  return L.markerClusterGroup({{
    maxClusterRadius: 45,
    clusterPane: 'schoolsPane',
    iconCreateFunction: function(c) {{
      const count = c.getChildCount();
      let size = 20;
      if (count >= 250) size = 34;
      else if (count >= 50) size = 28;
      else if (count >= 10) size = 24;
      return L.divIcon({{
        html: `<div class="cluster-icon" style="background:{AZ_MARKER};width:${{size}}px;height:${{size}}px;font-size:${{size >= 28 ? 11 : 9.5}}px;">${{count}}</div>`,
        className: 'school-cluster-wrapper',
        iconSize: L.point(size, size)
      }});
    }}
  }});
}}

// ---- All private schools nationwide, combined into ONE cluster group and ONE exact-point group ----
// (per-state color is preserved on each marker; only the aggregation behavior differs between the two)
const ALL_SCHOOL_SETS = Object.keys(SCHOOLS_ALL).map(function(abbr) {{
  return [SCHOOLS_ALL[abbr], SCHOOL_COLORS[abbr] || '#888888', abbr];
}});

// Program-participation choropleths, all on the ONE map at real geography.
// Alaska's district choropleth sits at its true location (far top-left); Hawaii
// is an outline in the boundary layer. azLayerFy2026 is off by default (same zip
// geography as FY2024).
azLayer.addTo(map);
flLayer.addTo(map);
txLayer.addTo(map);
nhLayer.addTo(map);
wvLayer.addTo(map);
ncLayer.addTo(map);
mdLayer.addTo(map);
akLayer.addTo(map);
riLayer.addTo(map);
inLayer.addTo(map);
wiLayer.addTo(map);
moLayer.addTo(map);
arLayer.addTo(map);

// ---- Per-state private-school layers (all on the one map) ----
// Each state's schools get their own clustered + exact-point groups. Default
// mode 'none' = hidden, so the map (Alaska & Hawaii included) boots on the clean
// choropleth view; each state can be toggled on its own, and the national
// summary / left control toggle every state at once.
const SCHOOL = {{}};
ALL_SCHOOL_SETS.forEach(function([schools, color, abbr]) {{
  const cluster = makeClusterGroup();
  const points = L.layerGroup();
  buildSchoolMarkers(schools, color, abbr, 5).forEach(function(m) {{ cluster.addLayer(m); }});
  buildSchoolMarkers(schools, color, abbr, 5).forEach(function(m) {{ points.addLayer(m); }});
  SCHOOL[abbr] = {{ cluster: cluster, points: points, map: map, mode: 'none' }};
}});

function applyStateSchools(abbr) {{
  const s = SCHOOL[abbr];
  if (!s) return;
  if (s.map.hasLayer(s.cluster)) s.map.removeLayer(s.cluster);
  if (s.map.hasLayer(s.points)) s.map.removeLayer(s.points);
  if (s.mode === 'clustered') s.cluster.addTo(s.map);
  else if (s.mode === 'exact') {{ s.points.addTo(s.map); rescaleSchoolPoints(); }}
}}
function setStateSchoolMode(abbr, mode) {{ if (SCHOOL[abbr]) {{ SCHOOL[abbr].mode = mode; applyStateSchools(abbr); }} }}
function aggregateSchoolMode() {{
  const modes = Object.keys(SCHOOL).map(function(a) {{ return SCHOOL[a].mode; }});
  if (modes.every(function(m) {{ return m === 'none'; }})) return 'none';
  if (modes.every(function(m) {{ return m === 'clustered'; }})) return 'clustered';
  if (modes.every(function(m) {{ return m === 'exact'; }})) return 'exact';
  return 'mixed';
}}

// Exact-location dots shrink at low zoom so a nationwide view isn't a solid mass.
function rescaleSchoolPoints() {{
  const r = radiusForZoom(map.getZoom());
  Object.keys(SCHOOL).forEach(function(a) {{
    const s = SCHOOL[a];
    if (s.map === map) s.points.eachLayer(function(m) {{ m.setRadius(r); }});
  }});
}}
map.on('zoomend', rescaleSchoolPoints);

// Left-control school radios drive the GLOBAL (all-states) mode via empty
// sentinel layers; radioNone is default so the map boots clean.
const radioClustered = L.layerGroup(), radioExact = L.layerGroup(), radioNone = L.layerGroup();
radioNone.addTo(map);
function syncLeftControl(mode) {{
  [radioClustered, radioExact, radioNone].forEach(function(l) {{ if (map.hasLayer(l)) map.removeLayer(l); }});
  (mode === 'clustered' ? radioClustered : mode === 'exact' ? radioExact : radioNone).addTo(map);
}}
function setAllSchoolMode(mode, fromControl) {{
  Object.keys(SCHOOL).forEach(function(a) {{ SCHOOL[a].mode = mode; applyStateSchools(a); }});
  if (!fromControl) syncLeftControl(mode);
}}

map.fitBounds(CONUS_BOUNDS, {{ padding: [8, 8] }});
rescaleSchoolPoints();

// clicking empty map returns to the national view unless the panel was closed.
map.on('click', function() {{ if (!profileClosed) showNationalProfile(); }});
showNationalProfile();

L.control.layers({{
  'Private schools &mdash; clustered (whole map)': radioClustered,
  'Private schools &mdash; exact locations (whole map)': radioExact,
  'Private schools &mdash; none (hide all)': radioNone
}}, {{
  'State boundaries': stateBoundaryLayer,
  'Arizona &mdash; ESA students, FY2024 year-end (zip)': azLayer,
  'Arizona &mdash; ESA students, FY2026 as of Q3 (zip)': azLayerFy2026,
  'Florida &mdash; FTC scholarships (district)': flLayer,
  'North Carolina &mdash; Opportunity Scholarship (county)': ncLayer,
  'Maryland &mdash; BOOST scholarships (county of residence)': mdLayer,
  'Rhode Island &mdash; SGO Scholarships (zip)': riLayer,
  'Indiana &mdash; Choice Scholarship (county)': inLayer,
  'Wisconsin &mdash; Choice Programs (zip)': wiLayer,
  'Missouri &mdash; MOScholars ESA (school district)': moLayer,
  'Arkansas &mdash; LEARNS EFA (school county)': arLayer,
  'Texas &mdash; TEFA participants (district)': txLayer,
  'New Hampshire &mdash; EFA enrollees (county)': nhLayer,
  'West Virginia &mdash; Hope recipients (county)': wvLayer
}}, {{ collapsed: true, position: 'topleft' }}).addTo(map);

// Left-control school radios -> whole-map mode; keep the open panel's toggle in sync.
map.on('baselayerchange', function(e) {{
  if (e.layer === radioClustered) setAllSchoolMode('clustered', true);
  else if (e.layer === radioExact) setAllSchoolMode('exact', true);
  else if (e.layer === radioNone) setAllSchoolMode('none', true);
  refreshCurrentView();
}});

// ---- Region view switcher (ONE map): fly to a region and lock the view there,
// while the whole built map (tiles, boundaries, choropleths) stays underneath. ----
const REGION_VIEW = {{
  conus: {{ bounds: CONUS_BOUNDS, minZoom: 4 }},
  ak:    {{ bounds: L.latLngBounds([[52.0, -179.9], [71.6, -129.9]]), minZoom: 4 }},
  hi:    {{ bounds: L.latLngBounds([[18.7, -160.6], [22.4, -154.6]]), minZoom: 6 }}
}};
let activeRegion = 'conus';
function viewRegion(region) {{
  const v = REGION_VIEW[region];
  if (!v) return;
  activeRegion = region;
  map.setMaxBounds(null);
  map.setMinZoom(v.minZoom);
  map.fitBounds(v.bounds, {{ padding: [10, 10] }});
  map.setMaxBounds(v.bounds);   // lock the view over this region
  document.querySelectorAll('#region-switch button').forEach(function(b) {{
    b.classList.toggle('active', b.dataset.region === region);
  }});
}}
document.querySelectorAll('#region-switch button').forEach(function(b) {{
  b.addEventListener('click', function() {{ viewRegion(b.dataset.region); }});
}});
viewRegion('conus');

// ---- address search ----
// Client-side geocode via OpenStreetMap Nominatim (no API key, CORS-enabled,
// restricted to the US). On a hit: fly to the point, drop a pin, turn on the
// private-school overlay so nearby access is visible, and open that state's
// profile so the user sees their own participation/supply picture.
const STATE_ABBR = {{
  'Alabama':'AL','Alaska':'AK','Arizona':'AZ','Arkansas':'AR','California':'CA','Colorado':'CO',
  'Connecticut':'CT','Delaware':'DE','District of Columbia':'DC','Florida':'FL','Georgia':'GA',
  'Hawaii':'HI','Idaho':'ID','Illinois':'IL','Indiana':'IN','Iowa':'IA','Kansas':'KS','Kentucky':'KY',
  'Louisiana':'LA','Maine':'ME','Maryland':'MD','Massachusetts':'MA','Michigan':'MI','Minnesota':'MN',
  'Mississippi':'MS','Missouri':'MO','Montana':'MT','Nebraska':'NE','Nevada':'NV','New Hampshire':'NH',
  'New Jersey':'NJ','New Mexico':'NM','New York':'NY','North Carolina':'NC','North Dakota':'ND','Ohio':'OH',
  'Oklahoma':'OK','Oregon':'OR','Pennsylvania':'PA','Rhode Island':'RI','South Carolina':'SC',
  'South Dakota':'SD','Tennessee':'TN','Texas':'TX','Utah':'UT','Vermont':'VT','Virginia':'VA',
  'Washington':'WA','West Virginia':'WV','Wisconsin':'WI','Wyoming':'WY'
}};

// Which program choropleth + value field to read for each program state, so we
// can report the choice-student count for the specific area an address falls in.
// AZ uses its FY2026 (most current) layer, matching the national-total convention.
const CHOROPLETH_LOOKUP = {{
  'AZ': {{ geo: azGeoFy2026, valueKey: 'total', geoUnit: 'ZIP code' }},
  'FL': {{ geo: flGeo, valueKey: 'students', geoUnit: 'school district' }},
  'TX': {{ geo: txGeo, valueKey: 'students', geoUnit: 'school district' }},
  'NH': {{ geo: nhGeo, valueKey: 'students', geoUnit: 'county' }},
  'WV': {{ geo: wvGeo, valueKey: 'students', geoUnit: 'county' }},
  'NC': {{ geo: ncGeo, valueKey: 'students', geoUnit: 'county' }},
  'AK': {{ geo: akGeo, valueKey: 'students', geoUnit: 'school district' }},
  'RI': {{ geo: riGeo, valueKey: 'students', geoUnit: 'ZIP code' }},
  'IN': {{ geo: inGeo, valueKey: 'students', geoUnit: 'county' }},
  'WI': {{ geo: wiGeo, valueKey: 'students', geoUnit: 'ZIP code' }},
  'MO': {{ geo: moGeo, valueKey: 'students', geoUnit: 'school district' }},
  'AR': {{ geo: arGeo, valueKey: 'students', geoUnit: 'county' }}
}};

function milesBetween(lat1, lon1, lat2, lon2) {{
  const R = 3958.8, toRad = d => d * Math.PI / 180;
  const dLat = toRad(lat2 - lat1), dLon = toRad(lon2 - lon1);
  const a = Math.sin(dLat/2)**2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon/2)**2;
  return R * 2 * Math.asin(Math.sqrt(a));
}}
function pointInRing(lon, lat, ring) {{
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {{
    const xi = ring[i][0], yi = ring[i][1], xj = ring[j][0], yj = ring[j][1];
    if (((yi > lat) !== (yj > lat)) && (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi)) inside = !inside;
  }}
  return inside;
}}
function pointInFeature(lon, lat, geom) {{
  if (geom.type === 'Polygon') return pointInRing(lon, lat, geom.coordinates[0]);
  if (geom.type === 'MultiPolygon') return geom.coordinates.some(poly => pointInRing(lon, lat, poly[0]));
  return false;
}}
function findContainingFeature(geo, lon, lat) {{
  for (const f of geo.features) if (pointInFeature(lon, lat, f.geometry)) return f;
  return null;
}}
function nearbySchools(lat, lon, maxMi) {{
  const out = [];
  ALL_SCHOOL_SETS.forEach(function([schools, color, abbr]) {{
    schools.forEach(function(s) {{
      const d = milesBetween(lat, lon, s.lat, s.lon);
      if (d <= maxMi) out.push({{ s: s, abbr: abbr, d: d }});
    }});
  }});
  out.sort((a, b) => a.d - b.d);
  return out;
}}
function primaryProgram(profile) {{
  if (!profile) return null;
  if (profile.programs && profile.programs.length) return profile.programs[profile.programs.length - 1];
  return profile.program || null;
}}

// Access gap analysis for a searched point: is this area well-served by private
// schools, and if not, what's missing (level / faith / distance)?
function searchGapAnalysis(near) {{
  const w25 = near.filter(function(x) {{ return x.d <= 25; }});
  const w10 = near.filter(function(x) {{ return x.d <= 10; }});
  const lvl = {{ Elementary: 0, Combined: 0, Secondary: 0 }};
  const rel = {{ Catholic: 0, 'Other religious': 0, Nonsectarian: 0 }};
  let seats = 0;
  w25.forEach(function(x) {{
    if (lvl[x.s.level] != null) lvl[x.s.level]++;
    if (rel[x.s.relig] != null) rel[x.s.relig]++;
    if (x.s.enroll) seats += x.s.enroll;
  }});
  const nearest = near[0];
  const gaps = [];
  if (!near.length) {{
    gaps.push('No private school at all within 50 miles &mdash; a severe access desert.');
  }} else {{
    if (!w10.length) gaps.push('No private school within 10 miles (nearest is ' + Math.round(nearest.d) + ' mi away).');
    if (lvl.Secondary + lvl.Combined === 0) gaps.push('No high-school option (grades 9&ndash;12) within 25 miles.');
    if (lvl.Elementary + lvl.Combined === 0) gaps.push('No elementary option within 25 miles.');
    if (rel.Nonsectarian === 0) gaps.push('No nonsectarian / secular private school within 25 miles.');
    if (rel.Catholic + rel['Other religious'] === 0) gaps.push('No faith-based private school within 25 miles.');
  }}
  let verdict, cls;
  if (!w10.length) {{ verdict = 'Access gap'; cls = 'gap-bad'; }}
  else if (w10.length >= 5 && !gaps.length) {{ verdict = 'Well served'; cls = 'gap-good'; }}
  else {{ verdict = 'Partial coverage'; cls = 'gap-mid'; }}
  const lvlLine = 'Elementary ' + lvl.Elementary + ' &middot; K&ndash;12 ' + lvl.Combined + ' &middot; High ' + lvl.Secondary;
  const relLine = 'Catholic ' + rel.Catholic + ' &middot; Other religious ' + rel['Other religious'] + ' &middot; Nonsectarian ' + rel.Nonsectarian;
  return `
    <div class="sp-section">
      <div class="sp-label">Access gap analysis</div>
      <div class="gap-verdict ${{cls}}">${{verdict}}</div>
      <div class="sp-kv-row"><span class="k">Nearest private school</span><span class="v">${{near.length ? nearest.d.toFixed(1) + ' mi' : 'none &lt; 50 mi'}}</span></div>
      <div class="sp-kv-row"><span class="k">Seats within 25 mi</span><span class="v">${{fmt(seats)}}</span></div>
      <div class="sp-kv-row"><span class="k">By level (&le; 25 mi)</span><span class="v">${{lvlLine}}</span></div>
      <div class="sp-kv-row"><span class="k">By type (&le; 25 mi)</span><span class="v">${{relLine}}</span></div>
      ${{gaps.length ? '<div class="gap-list"><b>Gaps near here:</b><ul>' + gaps.map(function(g) {{ return '<li>' + g + '</li>'; }}).join('') + '</ul></div>' : '<div class="sp-note" style="padding:6px 0;">Good coverage: schools nearby across levels and types.</div>'}}
      <button class="sp-howlink" onclick="openWizard('entrepreneur')">See where the biggest gaps are &rarr;</button>
    </div>`;
}}

// The post-search "window": choice-student count for the area + private schools
// within 50 miles, rendered into the profile panel.
const NEARBY_RADIUS_MI = 50;
function showSearchResult(lat, lon, displayName, abbr) {{
  currentAbbr = abbr || null;
  currentView = 'search';
  document.documentElement.style.setProperty('--accent', '#eb6834');
  spTitle.textContent = 'Near this location';
  const shortName = displayName.split(',').slice(0, 3).join(',').trim();

  const near = nearbySchools(lat, lon, NEARBY_RADIUS_MI);
  const b10 = near.filter(x => x.d <= 10).length;
  const b25 = near.filter(x => x.d > 10 && x.d <= 25).length;
  const b50 = near.filter(x => x.d > 25 && x.d <= 50).length;

  const lk = abbr && CHOROPLETH_LOOKUP[abbr];
  const prof = abbr && STATE_PROFILES[abbr];
  const prog = primaryProgram(prof);
  let choiceHtml = '';
  if (lk) {{
    const f = findContainingFeature(lk.geo, lon, lat);
    if (f) {{
      const v = f.properties[lk.valueKey] || 0;
      const nm = f.properties.name || ('ZIP ' + f.properties.zip);
      choiceHtml = `<div class="sp-stat">${{fmt(v)}}</div>
        <div class="sp-stat-sub">choice students in ${{nm}} (${{lk.geoUnit}})</div>`;
      if (prog) choiceHtml += `<div class="sp-stat-sub">Statewide: ${{fmt(prog.total)}} ${{prog.unit}} &mdash; ${{prog.label}}</div>`;
    }}
  }}
  if (!choiceHtml) {{
    if (prog) {{
      choiceHtml = `<div class="sp-stat">${{fmt(prog.total)}}</div>
        <div class="sp-stat-sub">${{prog.unit}} statewide &mdash; ${{prog.label}}</div>`;
    }} else {{
      choiceHtml = `<div class="sp-stat-sub">No school-choice program participation data is loaded` +
        (prof ? ' for ' + prof.name : '') + ` yet &mdash; only the private-school directory is mapped here.</div>`;
    }}
  }}

  const CAP = 60;
  const listRows = near.slice(0, CAP).map(x => `
      <div class="sp-school-row">
        <span class="sp-school-name">${{x.s.name}}</span>
        <span class="sp-school-meta">${{x.s.city}}, ${{x.abbr}} &middot; ${{x.d.toFixed(1)}} mi</span>
      </div>`).join('');
  const moreNote = near.length > CAP
    ? `<div class="sp-note">Showing the nearest ${{CAP}} of ${{fmt(near.length)}} within ${{NEARBY_RADIUS_MI}} miles.</div>` : '';

  let html = `
    <div class="sp-section">
      <div class="sp-label">Searched location</div>
      <div class="sp-stat-sub" style="color:var(--text-secondary);">${{shortName}}</div>
    </div>
    <div class="sp-section">
      <div class="sp-label">Choice program participation</div>
      ${{choiceHtml}}
    </div>
    <div class="sp-section">
      <div class="sp-label">Private schools within ${{NEARBY_RADIUS_MI}} miles</div>
      <div class="sp-stat">${{fmt(near.length)}}</div>
      <div class="sp-stat-sub">${{b10}} within 10 mi &middot; ${{b25}} at 10&ndash;25 mi &middot; ${{b50}} at 25&ndash;50 mi</div>
      <div class="sp-schoollist">${{listRows || '<div class="sp-note" style="padding:8px 9px;">No private schools in our data within 50 miles.</div>'}}</div>
      ${{moreNote}}
    </div>`;
  html += searchGapAnalysis(near);
  if (prof) {{
    html += `<div class="sp-section"><button class="sp-linkbtn" onclick="showStateProfile('${{abbr}}')">View full ${{prof.name}} profile &rarr;</button></div>`;
  }}
  spBody.innerHTML = html;
  openPanel();
}}

const addrForm = document.getElementById('addr-search');
const addrInput = document.getElementById('addr-input');
const addrStatus = document.getElementById('addr-status');
const addrBtn = addrForm.querySelector('button');
let searchMarker = null;

function setAddrStatus(msg, isError) {{
  addrStatus.textContent = msg || '';
  addrStatus.classList.toggle('error', !!isError);
}}

addrForm.addEventListener('submit', function(e) {{
  e.preventDefault();
  const q = addrInput.value.trim();
  if (!q) return;
  addrBtn.disabled = true;
  setAddrStatus('Searching…', false);

  const url = 'https://nominatim.openstreetmap.org/search?' + new URLSearchParams({{
    q: q, format: 'json', limit: '1', countrycodes: 'us', addressdetails: '1'
  }});

  fetch(url, {{ headers: {{ 'Accept': 'application/json' }} }})
    .then(function(r) {{ return r.json(); }})
    .then(function(data) {{
      if (!data || !data.length) {{
        setAddrStatus('No match found — try adding a city and state, or a ZIP code.', true);
        return;
      }}
      const hit = data[0];
      const lat = parseFloat(hit.lat), lon = parseFloat(hit.lon);
      setAddrStatus('', false);

      if (searchMarker) map.removeLayer(searchMarker);
      searchMarker = L.marker([lat, lon], {{
        icon: L.divIcon({{ className: 'search-pin', html: '📍', iconSize: [24, 24], iconAnchor: [12, 22], popupAnchor: [0, -20] }})
      }}).addTo(map);
      searchMarker.bindPopup('<b>Searched location</b><br>' + (hit.display_name || q)).openPopup();

      enableSchoolsLayer();  // so nearby private-school access is visible
      const wasConus = (activeRegion === 'conus');
      if (!wasConus) viewRegion('conus');  // search is CONUS-focused; snap back to the full US
      const flyThere = function() {{ map.invalidateSize(); map.flyTo([lat, lon], 10, {{ duration: 1.1 }}); }};
      if (wasConus) flyThere(); else setTimeout(flyThere, 160);

      let abbr = null;
      const iso = hit.address && hit.address['ISO3166-2-lvl4'];
      if (iso && iso.indexOf('US-') === 0) abbr = iso.slice(3);
      if (!abbr && hit.address && hit.address.state) abbr = STATE_ABBR[hit.address.state];
      showSearchResult(lat, lon, hit.display_name || q, abbr);
    }})
    .catch(function() {{
      setAddrStatus('Search failed — check your connection and try again.', true);
    }})
    .finally(function() {{ addrBtn.disabled = false; }});
}});

// Under type="module" the top-level scope isn't global, so expose the handlers
// referenced by inline onclick="" attributes in the profile panel / About page.
Object.assign(window, {{ calloutToggleSchools, calloutSetMode, openAbout, closeAbout, openMethod, closeMethod, showStateProfile, showAreaDetail, drillToArea, backToState, programCountsSelect, openData, closeData, downloadTable, openWizard, closeWizard, wizBack, wizAnswer, wizGeocode, wizTogglePart }});
</script>
</body>
</html>
"""

out_path = os.path.join(ROOT, 'index.html')
with open(out_path, 'w') as f:
    f.write(html)
print('wrote', out_path, len(html), 'bytes')

# Mirror the runtime-fetched data files next to index.html (at FETCH_PREFIX) so
# the output is a self-contained bundle: index.html + these files upload straight
# to the site root. Sources stay canonical under data/. Only files whose CONTENT
# changed are re-written, so a rebuild doesn't needlessly touch (or make you
# re-upload) data that didn't change - "modified" then means "actually changed".
dest_dir = os.path.join(ROOT, FETCH_PREFIX)
os.makedirs(dest_dir, exist_ok=True)
runtime_srcs = ([os.path.join(GEOJSON_DIR, fn) for fn in RUNTIME_GEOJSON]
                + [os.path.join(ROOT, 'data', 'schools_all.json')])
changed = []
for src in runtime_srcs:
    dst = os.path.join(dest_dir, os.path.basename(src))
    if os.path.abspath(src) == os.path.abspath(dst):
        continue
    if os.path.exists(dst) and filecmp.cmp(src, dst, shallow=False):
        continue  # identical -> leave it (keeps timestamps honest)
    shutil.copyfile(src, dst)
    changed.append(os.path.basename(src))
print(f'flat bundle: {len(changed)} data file(s) updated' + (f' ({", ".join(changed)})' if changed else ''))
print('DEPLOY: re-upload index.html' + (f' + {len(changed)} changed data file(s): {", ".join(changed)}'
                                        if changed else ' (no data files changed this build)'))
