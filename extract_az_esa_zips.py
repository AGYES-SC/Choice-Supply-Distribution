"""
Extracts the "Zip codes" table (Table 7: Number of students enrolled in ESA
program by zip code) from Arizona's quarterly ESA reporting PDFs and takes
the LAST available quarter of a fiscal year as that year's total per zip code.

WHY THE LAST QUARTER, NOT THE SUM OF QUARTERS: each quarterly report restates
the program's enrollment as of that quarter - it is a point-in-time census of
students currently enrolled, not that quarter's new sign-ups. Arizona's own
FY2024 headline totals run 66,457 (Q1) -> 71,520 (Q2) -> 74,996 (Q3) ->
74,578 (Q4): a running level that rises and can fall, not four disjoint
cohorts. Adding the quarters together therefore counts most students up to
four times. This module previously summed them, which reported FY2024 as
287,551 students against an actual year-end 74,578 (a ~3.85x overcount), and
FY2026 as 295,918 against 102,891.

The last available quarter is the year-end level for a complete fiscal year
(Q4) and the most recent level for a year still in progress (FY2026 -> Q3).
Both figures are cross-checked below against the "Total" row the report prints
for itself, so the extracted zip table has to reconcile to Arizona's own
published number or the extraction fails loudly.

Earlier quarters are still returned per zip, for the map's quarter-by-quarter
tooltip - they show the enrollment trajectory within the year, and must not be
added up.

The table itself is laid out in a three-column, two-value-per-row grid
(zip, count, zip, count, zip, count) which breaks naive top-to-bottom text
extraction - pdfplumber reads words in roughly left-to-right, top-to-bottom
order across the whole page, which interleaves the three columns. This
script instead clusters words by x-position into the three column pairs,
sorts each pair top-to-bottom by its vertical position, and pairs them off
positionally rather than trusting reading order.

Each quarter's page range (the "Zip codes" section start/end) was located by
searching extracted text for the section heading and the next section's
heading; those ranges are hardcoded below since the report layout is stable
within a fiscal year but has shifted slightly between FY2024 and FY2026
(different page counts per report). Re-locate the range for any new fiscal
year by searching for "g. Zip codes" (start) and "Section 2: Annual award
amounts" (end, exclusive - but include the page *before* it, since that page
usually holds the table's own "Total" row).
"""
import re
from collections import defaultdict

import pdfplumber

ZIP_RE = re.compile(r'^8\d{4}$')
NUM_RE = re.compile(r'^[\d,]+$')
GROUP_BOUNDS = [(0, 200), (200, 400), (400, 600)]

# (filename, start_page, end_page) - end_page is exclusive and includes the page
# where the "Total" row appears, even if that page also starts the next section.
QUARTERS_FY2024 = {
    'Q1': ('AZ 2024 Q1 ESA Reporting.pdf', 23, 27),
    'Q2': ('AZ 2024 Q2 ESA Reporting.pdf', 26, 31),
    'Q3': ('AZ 2024 Q3 ESA Reporting.pdf', 23, 28),
    'Q4': ('AZ 2024 Q4 ESA Reporting.pdf', 23, 28),
}

# FY2026 Q4 is not yet published as of this writing - fiscal_year_totals()
# takes Q3 as the year's most recent enrollment level and flags it partial.
QUARTERS_FY2026 = {
    'Q1': ('AZ 2026 Q1 ESA Reporting.pdf', 26, 31),
    'Q2': ('AZ 2026 Q2 ESA Reporting.pdf', 27, 32),
    'Q3': ('AZ 2026 Q3 ESA Reporting.pdf', 27, 32),
}

# Each report's own printed "Total" row for its zip table (Table 7), used to
# verify the extraction. Add a row when adding a quarter; read it off the PDF.
REPORTED_TOTALS = {
    'FY2024': {'Q1': 66457, 'Q2': 71520, 'Q3': 74996, 'Q4': 74578},
    'FY2026': {'Q1': 93993, 'Q2': 99034, 'Q3': 102891},
}


def extract_zip_table(pdf_path, start_page, end_page):
    """Returns {zip: count} for one quarter's Table 7."""
    totals = defaultdict(int)
    with pdfplumber.open(pdf_path) as pdf:
        for page_num in range(start_page, end_page):
            words = pdf.pages[page_num].extract_words()
            digit_words = [w for w in words if NUM_RE.match(w['text'])]
            for lo, hi in GROUP_BOUNDS:
                group = [w for w in digit_words if lo <= w['x0'] < hi]
                group.sort(key=lambda w: (round(w['top'], 1), w['x0']))
                idx = 0
                while idx < len(group):
                    if ZIP_RE.match(group[idx]['text']):
                        has_pair = (
                            idx + 1 < len(group)
                            and NUM_RE.match(group[idx + 1]['text'])
                            and not ZIP_RE.match(group[idx + 1]['text'])
                        )
                        if has_pair:
                            zip_code, count = group[idx], group[idx + 1]
                            totals[zip_code['text']] += int(count['text'].replace(',', ''))
                            idx += 2
                            continue
                    idx += 1
    return dict(totals)


def fiscal_year_totals(quarters, year_label=None, base_dir='.', verify=True):
    """quarters: dict like QUARTERS_FY2024/QUARTERS_FY2026 (whatever subset of
    quarters is available - a fiscal year in progress just has fewer entries).

    Returns (totals, by_quarter, last_label) where `totals` is {zip: students}
    taken from the LAST available quarter - the year's enrollment level, NOT a
    sum across quarters (see the module docstring). `by_quarter` keeps every
    quarter's table for the map's trajectory tooltip.

    With verify=True each quarter's extracted zip table must reconcile to the
    total that report prints for itself (REPORTED_TOTALS), so a layout shift in
    a future report surfaces as an error instead of a silently wrong map."""
    by_quarter = {}
    for label in sorted(quarters):
        filename, start, end = quarters[label]
        by_quarter[label] = extract_zip_table(f'{base_dir}/{filename}', start, end)

    if verify and year_label:
        for label, table in by_quarter.items():
            expected = REPORTED_TOTALS.get(year_label, {}).get(label)
            got = sum(table.values())
            if expected is not None and got != expected:
                raise ValueError(
                    f'{year_label} {label}: extracted zip table sums to {got:,}, but the '
                    f"report's own Total row says {expected:,}. The zip-table page range "
                    'or column layout has probably shifted - re-locate it (see docstring).')

    last_label = sorted(by_quarter)[-1]
    return dict(by_quarter[last_label]), by_quarter, last_label


if __name__ == '__main__':
    for year_label, quarters in [('FY2024', QUARTERS_FY2024), ('FY2026', QUARTERS_FY2026)]:
        totals, by_quarter, last = fiscal_year_totals(quarters, year_label)
        print(f'=== {year_label} ({"/".join(by_quarter)}) ===')
        for label, d in by_quarter.items():
            print(f'  {label}: {len(d):4d} zips, {sum(d.values()):>8,} students'
                  f'{"   <- taken as the FY total" if label == last else ""}')
        print(f'  {year_label} total: {sum(totals.values()):,} across {len(totals)} zip codes '
              f'(from {last}; summing the quarters would have reported '
              f'{sum(sum(d.values()) for d in by_quarter.values()):,})')
