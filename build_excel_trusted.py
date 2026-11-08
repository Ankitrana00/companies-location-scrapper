# Rebuild city workbooks keeping only trusted pins (high / good / duplicate)
import json, os, sys

XLSX_SKILL_DIR = r"C:\Users\Ankit\.zcode\cli\plugins\cache\zcode-plugins-official\spreadsheets\0.2.1\skills\xlsx"
for sub in [XLSX_SKILL_DIR, os.path.join(XLSX_SKILL_DIR, "templates")]:
    if sub not in sys.path:
        sys.path.insert(0, sub)
from base import (setup_sheet, style_header_row, style_data_row,
                  auto_fit_columns, auto_fit_row_heights,
                  font_caption, align_number, ACCENT_POSITIVE, ACCENT_NEGATIVE,
                  ACCENT_WARNING, NEUTRAL_600, FONT_NAME)
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment

DIR = os.path.dirname(os.path.abspath(__file__))
TRUSTED = {"high", "good", "duplicate", "verified"}
LABEL = {"high": "Found - exact match", "good": "Found",
         "duplicate": "Verified (same place as name variant)",
         "verified": "Verified manually"}
COLOR = {"high": ACCENT_POSITIVE, "good": ACCENT_POSITIVE,
         "duplicate": NEUTRAL_600, "verified": ACCENT_POSITIVE}

def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

HEADERS = ["#", "Company Name (your list)", "Google Maps Listing", "Full Address",
           "Latitude", "Longitude", "Website", "Phone", "Category", "Rating",
           "Reviews", "Match Status"]

CITIES = []
for _f in sorted(os.listdir(DIR)):
    if _f.endswith("_matched.json"):
        CITIES.append((_f[:-len("_matched.json")], _f[:-len("_matched.json")].capitalize()))
if os.path.exists(os.path.join(DIR, "matched.json")) and "jaipur" not in [t for t, _ in CITIES]:
    CITIES.insert(0, ("jaipur", "Jaipur"))
if not CITIES:
    sys.exit("no *_matched.json files found in " + DIR)

for tag, city in CITIES:
    src = os.path.join(DIR, ("matched.json" if tag == "jaipur" else tag + "_matched.json"))
    data = json.load(open(src, encoding="utf-8"))
    trusted = [o for o in data if o["status"] in TRUSTED]

    wb = Workbook()
    ws = wb.active
    ws.title = "Companies"
    last_col = len(HEADERS) + 1
    setup_sheet(ws, title=f"{city} Companies - Verified Pins Only (Google Maps)", last_col=last_col)
    for col_idx, h in enumerate(HEADERS, start=2):
        ws.cell(row=4, column=col_idx, value=h)
    style_header_row(ws, row_num=4, col_start=2, col_end=last_col)

    r = 5
    for i, o in enumerate(trusted, 1):
        vals = [i, o["name"], o.get("matchTitle", ""), o.get("address", ""),
                fnum(o.get("lat")), fnum(o.get("lng")),
                o.get("website", ""), o.get("phone", ""), o.get("category", ""),
                fnum(o.get("rating")),
                int(o["reviews"]) if (o.get("reviews") or "").isdigit() else None,
                LABEL[o["status"]]]
        for col_idx, v in enumerate(vals, start=2):
            ws.cell(row=r, column=col_idx, value=v)
        style_data_row(ws, row_num=r, col_start=2, col_end=last_col, row_index=i - 1)
        for col_idx in (6, 7):
            c = ws.cell(row=r, column=col_idx)
            c.number_format = "0.000000"
            c.alignment = align_number()
        for col_idx in (11, 12, 2):
            ws.cell(row=r, column=col_idx).alignment = align_number()
        ws.cell(row=r, column=11).number_format = "0.0"
        ws.cell(row=r, column=12).number_format = "#,##0"
        sc = ws.cell(row=r, column=last_col)
        sc.font = Font(name=FONT_NAME, size=11, color=COLOR[o["status"]])
        r += 1

    note = ws.cell(row=r + 1, column=2,
                   value="Trusted pins only (exact/good/verified-duplicate matches). Rows removed from this "
                         "file: needs-check, not-found, out-of-area - kept in the CSV/JSON sources. "
                         "Exported %s." % __import__("datetime").date.today().isoformat())
    note.font = font_caption()
    ws.merge_cells(start_row=r + 1, start_column=2, end_row=r + 1, end_column=last_col)

    auto_fit_columns(ws, min_width=8, max_width=42, header_row=4, data_start_row=5)
    auto_fit_row_heights(ws, header_row=4, data_start_row=5)
    ws.freeze_panes = "D5"
    wb.properties.creator = "Z.ai"
    dest = os.path.join(DIR, tag + "_companies_locations.xlsx")
    wb.save(dest)
    print(f"{tag}: {len(trusted)}/{len(data)} trusted pins -> {os.path.basename(dest)}")
