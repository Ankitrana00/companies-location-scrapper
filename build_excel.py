# Build the Jaipur companies locations workbook from matched.json
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
_args = sys.argv[1:]
IN_JSON = _args[0] if len(_args) > 0 else os.path.join(DIR, "matched.json")
DEST = _args[1] if len(_args) > 1 else os.path.join(DIR, "jaipur_companies_locations.xlsx")
CITY = _args[2] if len(_args) > 2 else "Jaipur"
out = json.load(open(IN_JSON, encoding="utf-8"))

STATUS_LABEL = {
    "high": "Found - exact match",
    "good": "Found",
    "weak": "Found - CHECK NAME",
    "duplicate": "Same place as above-listed variant",
    "out_of_area": "Exact name but pinned OUTSIDE Jaipur - verify",
    "not_found": "Not found on Google Maps",
}
STATUS_COLOR = {
    "high": ACCENT_POSITIVE, "good": ACCENT_POSITIVE,
    "weak": ACCENT_WARNING, "duplicate": NEUTRAL_600,
    "out_of_area": ACCENT_WARNING, "not_found": ACCENT_NEGATIVE,
}

def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

HEADERS = ["#", "Company Name (your list)", "Google Maps Listing", "Full Address",
           "Latitude", "Longitude", "Website", "Phone", "Category", "Rating",
           "Reviews", "Match Status"]

wb = Workbook()
ws = wb.active
ws.title = "Companies"
last_col = len(HEADERS) + 1
setup_sheet(ws, title=f"{CITY} Companies - Addresses & Coordinates (Google Maps)", last_col=last_col)

for col_idx, h in enumerate(HEADERS, start=2):
    ws.cell(row=4, column=col_idx, value=h)
style_header_row(ws, row_num=4, col_start=2, col_end=last_col)

r = 5
for i, o in enumerate(out, 1):
    vals = [i, o["name"], o.get("matchTitle", ""), o.get("address", ""),
            fnum(o.get("lat")), fnum(o.get("lng")),
            o.get("website", ""), o.get("phone", ""), o.get("category", ""),
            fnum(o.get("rating")),
            int(o["reviews"]) if (o.get("reviews") or "").isdigit() else None,
            STATUS_LABEL[o["status"]]]
    for col_idx, v in enumerate(vals, start=2):
        ws.cell(row=r, column=col_idx, value=v)
    style_data_row(ws, row_num=r, col_start=2, col_end=last_col, row_index=i - 1)
    # numeric alignment + formats
    for col_idx in (6, 7):  # lat/lng
        c = ws.cell(row=r, column=col_idx)
        c.number_format = "0.000000"
        c.alignment = align_number()
    for col_idx in (11, 12):  # rating, reviews
        c = ws.cell(row=r, column=col_idx)
        c.alignment = align_number()
        if col_idx == 11:
            c.number_format = "0.0"
        else:
            c.number_format = "#,##0"
    ws.cell(row=r, column=2).alignment = align_number()
    # status color
    sc = ws.cell(row=r, column=last_col)
    sc.font = Font(name=FONT_NAME, size=11, color=STATUS_COLOR[o["status"]])
    r += 1

last_data_row = r - 1
note = ws.cell(row=last_data_row + 2, column=2,
               value="Source: Google Maps (scraped via google-maps-scraper v1.18.1), matched back to the "
                     "original list automatically. VERIFY 'CHECK NAME' rows before use. Blank coordinates = "
                     "listing found without a usable pin. Exported %s." % __import__("datetime").date.today().isoformat())
note.font = font_caption()
ws.merge_cells(start_row=last_data_row + 2, start_column=2, end_row=last_data_row + 2, end_column=last_col)

auto_fit_columns(ws, min_width=8, max_width=42, header_row=4, data_start_row=5)
auto_fit_row_heights(ws, header_row=4, data_start_row=5)
ws.freeze_panes = "D5"

# --- second sheet: needs review ---
ws2 = wb.create_sheet("Needs Review")
HEADERS2 = ["#", "Company Name (your list)", "Issue", "Google Maps Listing", "Best Match Score"]
last_col2 = len(HEADERS2) + 1
setup_sheet(ws2, title="Rows To Review Manually", last_col=last_col2)
for col_idx, h in enumerate(HEADERS2, start=2):
    ws2.cell(row=4, column=col_idx, value=h)
style_header_row(ws2, row_num=4, col_start=2, col_end=last_col2)

review = [o for o in out if o["status"] in ("weak", "not_found", "duplicate", "out_of_area")]
r2 = 5
for i, o in enumerate(review, 1):
    issue = STATUS_LABEL[o["status"]]
    if o["status"] == "duplicate":
        issue += ": " + o.get("dupOfName", "")
    vals = [i, o["name"], issue, o.get("matchTitle", ""), o.get("score", 0)]
    for col_idx, v in enumerate(vals, start=2):
        ws2.cell(row=r2, column=col_idx, value=v)
    style_data_row(ws2, row_num=r2, col_start=2, col_end=last_col2, row_index=i - 1)
    ws2.cell(row=r2, column=2).alignment = align_number()
    ws2.cell(row=r2, column=6).number_format = "0.00"
    ws2.cell(row=r2, column=6).alignment = align_number()
    r2 += 1

if review:
    auto_fit_columns(ws2, min_width=8, max_width=42, header_row=4, data_start_row=5)
    auto_fit_row_heights(ws2, header_row=4, data_start_row=5)
ws2.freeze_panes = "D5"

wb.properties.creator = "Z.ai"
wb.save(DEST)
print("saved:", DEST, "| companies:", len(out), "| review rows:", len(review))
