# Chicago Recovery Meetings

A free, mobile-friendly, independent directory of **in-person and hybrid recovery meetings within Chicago city limits**.

**Live website:** https://tonyachicago.github.io/chicago-recovery-meetings/

## What's included (November 21, 2026)

Daily source imports, last verified from the public schedules:

| Program | Source | Weekly physical/hybrid sessions imported |
|---|---|---:|
| Alcoholics Anonymous | Recovery Starts public Chicago AA index (independent, attributes Chicago area AA sources) | 878 |
| Narcotics Anonymous | Chicagoland BMLT | 99 |
| Recovery Dharma | Recovery Dharma Chicago meeting list | 13 |
| Sex and Love Addicts Anonymous | S Meetings Chicago | 10 |
| Cocaine Anonymous | Illinois Area CA directory | 9 |
| Sex Addicts Anonymous | S Meetings Chicago | 6 |
| SMART Recovery | SobaSearch's public Illinois SMART listings (independent factual index) | 6 |
| Adult Children of Alcoholics & Dysfunctional Families (ACA) | SobaSearch Chicago ACA directory, with original ACA WSO finder linked for confirmation | 9 |
| **Total** | | **1,030** |

These are *weekly session listings*, not distinct meeting groups, and have **not been independently field-verified**. Check the linked source before traveling. A source may list a moved or cancelled meeting. The source count is a snapshot and may change with each refresh.

The site's fellowship directory separately includes **31 resources**; unindexed programs appear as official finder links.

## Features

- Search by day, time, address, meeting name, and program.
- **Recovery ideology filter:** Collapsed by default, with All/None shortcuts and individual include/exclude controls. Groups are classified as 12-step, secular/science-based, mindfulness/Buddhist-inspired, or faith-based/Christian based on fellowship philosophy, not on individual attendees.
- **Saved meetings:** Use the ☆ Save / ★ Saved button and *Saved meetings only* filter. Favorites live in the visitor's browser `localStorage`, not in cookies or an account. They persist on the same browser/device unless site data is cleared. Other users of a shared browser may see them.
- Program-specific public directories and correction links to GitHub Issues.
- No user accounts, ads, paid services, or site-operated analytics.

## Daily import pipeline

`.github/workflows/refresh-and-deploy.yml` runs daily and on importer changes:

- `scripts/import_aa.py` → `data/aa.json`: *one* public Recovery Starts Chicago directory request; filter physical Chicago addresses; observe robots policy and preserve the last successful file if an import fails or has too few records.
- `scripts/import_na.py` → `data/na.json`: the official Chicagoland BMLT service.
- `scripts/import_other.py` → `data/ca.json`, `data/rd_live.json`, `data/s_fellowships.json`: public official fellowship meeting directories.
- `scripts/import_smart.py` → `data/smart.json`: public factual SMART meeting fields indexed by independent SobaSearch, not an access workaround to SMART's restricted site. Includes only physical attendance modes; all pages must be reachable or the last successful file stays intact.
- `scripts/import_aca.py` → `data/aca.json`: independent SobaSearch Chicago ACA source list. Imports only physical or hybrid records with valid Chicago street addresses, and never copies contact information. If the source fails or becomes too small, the previous file remains.
- `data/meetings.json` holds the manually sourced original Recovery Dharma fallback data. When `rd_live.json` is populated, the website uses that newer source instead of duplicating the fallback.

On successful imports, data changes are committed back to `main`. GitHub's existing branch-based Pages workflow deploys that revision. A source failure never replaces a working file with an empty array. There is no external API key, database, domain, or server bill.

## Sources, permissions, and accuracy

This is not an official fellowship service or endorsed by any program. Published times and addresses are attributed to the respective source pages. Some third-party catalogs aggregate meeting facts from official directories; their listing doesn't imply permission from each original publisher. If a source's terms change or a legitimate takedown request is received, pause that import and remove disputed records while reviewing.

Chicago AA's own site returned HTTP 403 to cloud automation, so AA is indexed from an independent public AA directory instead of bypassing its protection. SMART Recovery's site prohibits republication without consent; this project does not download from its site. SobaSearch publishes a public meeting index with crawler guidance for search indexing; this project collects factual metadata with direct attribution only, not full text or descriptions. These conditions should be reviewed periodically.

We do not publish attendees' names, contact details, private meeting notes, or recovery histories. GitHub Issues are public: do not disclose personal details in a correction.

**Early directory:** In-person listings may still include source errors. Verify each meeting with the linked publisher before attending.
