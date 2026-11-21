# Chicago Recovery Meetings

A **free, independent, noncommercial** directory of in-person and hybrid recovery meetings **within Chicago city limits**.

**Website:** https://tonyachicago.github.io/chicago-recovery-meetings/

## Coverage

The website combines source-listed weekly meeting schedules with a broader fellowship directory:

- Automated in-person/hybrid meeting records: Narcotics Anonymous (Chicagoland BMLT), Cocaine Anonymous (Illinois Area), Recovery Dharma Chicago, and selected Sex and Love Addicts Anonymous / Sex Addicts Anonymous records from S Meetings Chicago.
- 31 fellowship links in `data/fellowships.json`, including fellowships without an imported schedule.
- Alcoholics Anonymous is linked to the official meeting finder. Automated requests to Chicago AA were answered with HTTP 403, so no AA data is copied.
- SMART Recovery is linked to its official meeting finder rather than republished because of source restrictions.
- Searchable listings are **not field-verified**. Always check the original fellowship's meeting page before travelling.

## Data update workflow

`.github/workflows/refresh-and-deploy.yml` refreshes the directory daily (GitHub Actions, free public repository).

- `scripts/import_na.py` imports official BMLT data to `data/na.json`.
- `scripts/import_other.py` parses source directories with Python's standard library, saving `data/ca.json`, `data/rd_live.json` and `data/s_fellowships.json`.
- `data/meetings.json` holds the original manually curated Recovery Dharma pilot as a fallback if `rd_live.json` becomes unavailable.
- Each import **preserves the previously published file when a source fails**, checks city and physical attendance, and requires a minimum record count. Import success is **not** independent verification.
- The scheduled workflow commits changed JSON to `main`. The repository's existing branch-based Pages deployment publishes it.
- The site is static, requires no accounts and does not use analytics.

## Corrections and restrictions

Readers can report incorrect meeting information through GitHub Issues. Do not post attendee identities, personal recovery history, or private contact information. Requests to remove disputed listings will be handled promptly.

The site isn't affiliated with, sponsored by, or endorsed by any listed fellowship. Published meeting details are source-linked. No blanket permission is asserted for reuse of proprietary schedules.

## Scope and limitations

- Weekly sessions, not unique groups or individual meeting occurrences.
- Chicago municipality is required; geometry/address filtering is approximate, and sources may have mistakes.
- Some directory links may not currently have local in-person meetings.
- Recurring source imports may temporarily fail or be rate-limited; old records can become stale.
- The site deliberately remains in pilot mode until coverage is broader and quality checks improve.
