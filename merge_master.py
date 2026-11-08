# Merge all cities into one master dataset with cross-city dedup.
# Usage: py merge_master.py [--dir <dataDir>] [--out <outputDir>]
# Outputs: master_all.csv (every row + city), master_trusted.csv,
#          master_locations.xlsx (trusted pins only, City column, deduped)
import json, os, re, sys, csv, datetime, argparse

XLSX_SKILL_DIR = r"C:\Users\Ankit\.zcode\cli\plugins\cache\zcode-plugins-official\spreadsheets\0.2.1\skills\xlsx"
for sub in [XLSX_SKILL_DIR, os.path.join(XLSX_SKILL_DIR, "templates")]:
    if sub not in sys.path:
        sys.path.insert(0, sub)
from base import (setup_sheet, style_header_row, style_data_row,
                  auto_fit_columns, auto_fit_row_heights,
                  font_caption, align_number, ACCENT_POSITIVE, NEUTRAL_600, FONT_NAME)
from openpyxl import Workbook
from openpyxl.styles import Font

parser = argparse.ArgumentParser()
parser.add_argument("--dir", default=os.path.dirname(os.path.abspath(__file__)))
parser.add_argument("--out", default=None)
a = parser.parse_args()
DATA = os.path.abspath(a.dir)
OUT = os.path.abspath(a.out or a.dir)

TRUSTED = {"high", "good", "duplicate", "verified"}
LABEL = {"high": "Found - exact match", "good": "Found",
         "duplicate": "Verified (same place as name variant)",
         "verified": "Verified manually"}
COLOR = {"high": ACCENT_POSITIVE, "good": ACCENT_POSITIVE,
         "duplicate": NEUTRAL_600, "verified": ACCENT_POSITIVE}

CITY_ORDER = ["jaipur", "delhi", "gurugram", "noida", "kanpur", "agra", "gwalior",
              "varanasi", "lucknow", "faridabad", "ludhiana", "jodhpur",
              "prayagraj", "mohali", "udaipur"]

# collect cities present on disk
found = {}
for f in os.listdir(DATA):
    if f.endswith("_matched.json"):
        found[f[:-len("_matched.json")]] = os.path.join(DATA, f)
    elif f == "matched.json" and "jaipur" not in found:
        found["jaipur"] = os.path.join(DATA, f)
cities = [c for c in CITY_ORDER if c in found] + sorted(c for c in found if c not in CITY_ORDER)

def place_key(o):
    m = re.search(r"!1s(0x[0-9a-f]+:0x[0-9a-f]+)", o.get("mapsLink") or "")
    if m:
        return "pid:" + m.group(1)
    if o.get("lat") and o.get("lng"):
        try:
            return "geo:%.5f,%.5f:%s" % (float(o["lat"]), float(o["lng"]),
                                         (o.get("matchTitle") or "").lower()[:30])
        except ValueError:
            pass
    return "name:%s:%s" % ((o.get("matchTitle") or o.get("name") or "").lower(), o.get("city"))

rows, dupes = [], 0
seen = set()
for city in cities:
    data = json.load(open(found[city], encoding="utf-8"))
    for o in data:
        o["city"] = city
        key = place_key(o)
        if key in seen:
            dupes += 1
            continue
        seen.add(key)
        rows.append(o)

FIELDS = ["city", "company_name", "google_maps_name", "address", "latitude",
          "longitude", "website", "phone", "category", "rating", "reviews",
          "match_status", "google_maps_link"]

def to_row(o):
    return [o["city"], o["name"], o.get("matchTitle", ""), o.get("address", ""),
            o.get("lat", ""), o.get("lng", ""), o.get("website", ""),
            o.get("phone", ""), o.get("category", ""), o.get("rating", ""),
            o.get("reviews", ""), o["status"], o.get("mapsLink", "")]

def write_csv(path_, data):
    with open(path_, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(FIELDS)
        for o in data:
            w.writerow(to_row(o))

write_csv(os.path.join(OUT, "master_all.csv"), rows)
trusted = [o for o in rows if o["status"] in TRUSTED]
write_csv(os.path.join(OUT, "master_trusted.csv"), trusted)

# Excel: trusted pins only
HEADERS = ["#", "City", "Company Name (your list)", "Google Maps Listing", "Full Address",
           "Latitude", "Longitude", "Website", "Phone", "Category", "Rating",
           "Reviews", "Match Status"]
wb = Workbook()
ws = wb.active
ws.title = "Companies"
last_col = len(HEADERS) + 1
setup_sheet(ws, title="Master - Verified Company Pins, All Cities (Google Maps)", last_col=last_col)
for col_idx, h in enumerate(HEADERS, start=2):
    ws.cell(row=4, column=col_idx, value=h)
style_header_row(ws, row_num=4, col_start=2, col_end=last_col)

def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

r = 5
for i, o in enumerate(trusted, 1):
    vals = [i, o["city"].capitalize(), o["name"], o.get("matchTitle", ""), o.get("address", ""),
            fnum(o.get("lat")), fnum(o.get("lng")), o.get("website", ""), o.get("phone", ""),
            o.get("category", ""), fnum(o.get("rating")),
            int(o["reviews"]) if (o.get("reviews") or "").isdigit() else None,
            LABEL.get(o["status"], o["status"])]
    for col_idx, v in enumerate(vals, start=2):
        ws.cell(row=r, column=col_idx, value=v)
    style_data_row(ws, row_num=r, col_start=2, col_end=last_col, row_index=i - 1)
    for col_idx in (7, 8):
        c = ws.cell(row=r, column=col_idx)
        c.number_format = "0.000000"
        c.alignment = align_number()
    for col_idx in (12, 13, 2):
        ws.cell(row=r, column=col_idx).alignment = align_number()
    ws.cell(row=r, column=12).number_format = "0.0"
    ws.cell(row=r, column=13).number_format = "#,##0"
    sc = ws.cell(row=r, column=last_col)
    sc.font = Font(name=FONT_NAME, size=11, color=COLOR.get(o["status"], NEUTRAL_600))
    r += 1

note = ws.cell(row=r + 1, column=2,
               value="All %d cities merged, cross-city duplicates removed (%d dropped). Trusted pins only. "
                     "Removed rows live in master_all.csv / per-city matched files. Exported %s."
                     % (len(cities), dupes, datetime.date.today().isoformat()))
note.font = font_caption()
ws.merge_cells(start_row=r + 1, start_column=2, end_row=r + 1, end_column=last_col)
auto_fit_columns(ws, min_width=8, max_width=42, header_row=4, data_start_row=5)
auto_fit_row_heights(ws, header_row=4, data_start_row=5)
ws.freeze_panes = "E5"
wb.properties.creator = "Z.ai"
dest = os.path.join(OUT, "master_locations.xlsx")
wb.save(dest)

per_city = {}
for o in trusted:
    per_city[o["city"]] = per_city.get(o["city"], 0) + 1
print("cities:", len(cities), "| total rows:", len(rows), "| cross-city dedup dropped:", dupes)
print("trusted pins:", len(trusted), "| per city:", ", ".join(f"{c}:{n}" for c, n in sorted(per_city.items())))
print("saved:", dest, "+ master_all.csv + master_trusted.csv")
