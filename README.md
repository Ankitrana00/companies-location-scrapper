# Google Maps Company Scraper — Bundle

Scrapes company names into exact addresses + lat/lng coordinates, matches results
back to the original list, and builds Excel deliverables. Built and battle-tested
across 15 Indian cities (~5,700 companies).

## Getting the scraper binary (not committed)

`gms_linux` / `google_maps_scraper.exe` are prebuilt binaries of the open-source
[gosom/google-maps-scraper](https://github.com/gosom/google-maps-scraper) project
(MIT). Download v1.18.1 from its releases page and drop the binary in this folder:

- Linux (used inside WSL): `google_maps_scraper-1.18.1-linux-amd64` → rename to `gms_linux`, `chmod +x`
- Windows: `google_maps_scraper-1.18.1-windows-amd64.exe`

> Note: the Windows binary has a known bug (Chromium `--single-process` crash);
> the WSL/Linux route is the proven path on Windows machines.

## Contents

| File | Purpose |
|---|---|
| `gms_linux` | The scraper binary (v1.18.1, runs inside WSL Ubuntu) |
| `match.js` | Matching engine: pairs scraped places with your company names (fuzzy match, city bounds, generic-word guard) |
| `make_queries.js` | Turns `<city>_names.txt` into `<city>_queries.txt` |
| `run_scrape.sh` | Launch script for one city (edit the CITY variable) |
| `wsl_fixlibs.sh` | One-time WSL repair: installs Chromium's missing libraries without sudo |
| `build_excel.py` | Builds the full Excel (with "Needs Review" sheet) from `<city>_matched.json` |
| `build_excel_trusted.py` | Builds the trusted-pins-only Excel (auto-discovers all cities in the folder) |
| `review.js` | Interactive review of weak/out-of-area rows: `node review.js --dir <dataDir> <city|all>` — [y] keep / [n] reject / [s] skip / [q] quit. Kept rows become `verified` and join the trusted Excel after re-running build_excel_trusted.py |
| `merge_master.py` | Merges all cities into master_all.csv + master_trusted.csv + master_locations.xlsx (City column, cross-city dedup by Google place ID). Usage: `py merge_master.py --dir <dataDir>` |
| `<city>_names.txt` (15) | Input lists: jaipur, delhi, gurugram, noida, kanpur, agra, gwalior, varanasi, lucknow, faridabad, ludhiana, jodhpur, prayagraj, mohali, udaipur |

## Prerequisites (already set up on this machine)

1. **WSL Ubuntu** installed (`wsl -d Ubuntu` works)
2. Playwright Chromium downloaded (happens automatically on first run, ~300 MB into WSL `~/.cache/ms-playwright/`)
3. Chromium libraries fixed: run once inside the bundle folder:
   `bash wsl_fixlibs.sh` (safe to re-run; no sudo needed)
4. If you MOVE this folder, update the `cd` path inside `run_scrape.sh` to the new location.

## Workflow for a new city (example: indore)

```bash
# 1. Add the input list: indore_names.txt (one company per line) in this folder

# 2. Generate queries (from Windows terminal, in this folder)
node make_queries.js indore

# 3. Edit run_scrape.sh: set CITY=indore, then scrape (from Windows terminal)
bash run_scrape.sh
#    - runs inside WSL, writes indore_results.csv
#    - AUTO-RETRY: re-runs with -resume up to 4 times if the process dies
#      without a clean exit; nothing is lost or re-scraped

# 4. Match results back to your names (city bounds! adjust to the district)
node match.js indore_names.txt indore_results.csv indore_matched.json 22.0 26.5 75.0 77.0 Indore

# 5a. Full Excel with review sheet
py build_excel.py indore_matched.json indore_companies_locations.xlsx Indore
# 5b. Or trusted-pins-only Excel (high/good/duplicate rows only)
py build_excel_trusted.py

# 6. Validate (optional but recommended)
py "C:\Users\Ankit\.zcode\cli\plugins\cache\zcode-plugins-official\spreadsheets\0.2.1\skills\xlsx\xlsx.py" validate indore_companies_locations.xlsx
```

## Match quality legend

- `high` — exact/great name match, coordinates inside city bounds → trust
- `good` — trusted match → trust
- `duplicate` — same real place as another name variant → trust
- `weak` — possible but unverified → check manually
- `not_found` — no Google Maps listing found
- `out_of_area` — exact name, but pinned outside the city bounds

For Delhi/Faridabad, `match.js` also checks the address text (pincode/name evidence)
because their bounding boxes overlap neighboring NCR cities.

## Notes

- `python` is invoked as `py` (Windows launcher). openpyxl must be installed:
  `py -m pip install openpyxl`
- Total pipeline time: ~1 min per 20 companies (`-c 4` concurrency).
- Be gentle with Google: keep concurrency at 4, don't run for days nonstop.
  Scraping Google Maps violates their ToS — this is a gray-area tool.
- First-ever run downloads Chromium inside WSL; do not cancel it.
