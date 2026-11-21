# Chicago Recovery Meetings — v0.3

Free, static, independent Chicago in-person recovery meeting finder. **Not an official fellowship website.**

## Changes in this release

- Meeting records no longer live inside `index.html`.
- `data/meetings.json`: 10 previously sourced Recovery Dharma weekly sessions.
- `data/na.json`: begins empty. **No live NA data was imported in this offline build.**
- `scripts/import_na.py`: queries the official Chicagoland NA BMLT root, checks municipality, physical/hybrid venue type, street address, Chicago geolocation bounds (where present), and validation threshold. No virtual-only meetings.
- `.github/workflows/refresh-and-deploy.yml`: scheduled daily refresh + GitHub Pages deployment. Keeps last successful NA JSON file if the fetch fails.
- Program filter, dynamic coverage counts, and clear partial-source warnings.

## Deploy v0.3 to existing repository

Repository: https://github.com/TonyAChicago/chicago-recovery-meetings

1. Upload the CONTENTS of this ZIP into the existing repository (not the ZIP itself). Retain folder paths exactly. You are **updating** the existing project, not creating another repo.
2. In existing repository **Settings → Pages → Build and deployment → Source**, switch **Deploy from a branch** to **GitHub Actions**. This is a NEW change for automated deployment, not a repeat of your original Pages setup. Note: repo Actions permissions may need workflow read/write access if GitHub requests it.
3. In repository **Actions**, open **Refresh recovery meetings and deploy site** and choose **Run workflow**. The first import happens there (not in this ZIP), followed by deployment. Inspect action logs for the final imported count. If the upstream API cannot be fetched, the action reports a failed import and deploys the original Recovery Dharma pilot rather than publish nonexistent NA records.
4. Check the live site, filter by **Narcotics Anonymous**, and confirm several results against https://chicagona.org/meetings/ before relying on it. If the source reports fewer than 10 valid Chicago in-person/hybrid sessions, no new records are published.

**Important:** GitHub Pages will not always rebuild in response to a commit authored by `GITHUB_TOKEN`. The new workflow deploys the generated site itself, using `actions/deploy-pages`. This is why the Pages source must be **GitHub Actions**, not branch deployment.

The public correction system links to GitHub Issues and requires a free GitHub account for reporters. The site itself requires no account and has no analytics/ads.

## Data format

`data/meetings.json` and `data/na.json` are arrays of objects containing `id`, `program`, `title`, `day` (0=Sunday), `start` (24-hour HH:MM), optional `end`, `venue`, `address`, `city`, `state`, `postal_code`, `mode` (`in-person` or `hybrid`), optional `is_open`, optional `wheelchair_access`, `source_url`, `source_name`, and `last_checked`. Only records with a Chicago city field, an explicit physical meeting mode, a valid time, and an address render on the website.

## Limitations

- The ten Recovery Dharma meetings were sourced previously but not independently field-verified; they are not automatically updated in v0.3.
- City filtering relies on the BMLT municipality field (plus coarse lat/lon bounds where present), not a precise city-boundary polygon; some incomplete source records may be excluded.
- BMLT source may change or throttle; failures preserve prior meeting data, but old records can become stale. The website warns after 45 days.
- NA access and terms should be periodically reviewed; links/attribution remain visible. The project removes disputed listings on request.
- Daily scheduled GitHub Actions may be disabled by GitHub after prolonged repository inactivity. Periodically inspect Actions and refresh status.
- This site provides directory information, not crisis response or medical guidance.
- No domain, database, paid service, API key, or third-party npm package is required.
