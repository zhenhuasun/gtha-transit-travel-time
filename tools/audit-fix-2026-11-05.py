"""One-off audit fixes for the GTHA site pages (2026-11-05).

Ground truth: sources/gtha.json (ref 2026-11-05), sources/toronto.json (ref 2026-10-08),
data/gtha/manifest.json (all feeds fetched 2026-11-05), cities/*.json.
Every replacement asserts its expected count; the script aborts on mismatch.
Does NOT touch site/data/* or app.js/styles.css.
"""
import json
import re
from pathlib import Path

ROOT = Path("/home/hatch/workspace/gtha-push4")
SITE = ROOT / "site"


def replace_once(path: Path, old: str, new: str, count: int = 1):
    text = path.read_text()
    n = text.count(old)
    assert n == count, f"{path.name}: expected {count} x {old[:70]!r}, found {n}"
    path.write_text(text.replace(old, new))
    print(f"  {path.name}: replaced {count}x {old[:60]!r}")


def replace_re(path: Path, pattern: str, repl, count: int):
    text = path.read_text()
    new, n = re.subn(pattern, repl, text)
    assert n == count, f"{path.name}: pattern {pattern[:70]!r} expected {count}, found {n}"
    path.write_text(new)
    print(f"  {path.name}: regex replaced {n}x {pattern[:60]!r}")


gtha_stats = json.loads((ROOT / "sources" / "gtha.json").read_text())["stats"]
tor_stats = json.loads((ROOT / "sources" / "toronto.json").read_text())["stats"]

# ---------------------------------------------------------------- GTHA page
gtha = SITE / "gtha" / "index.html"

# 1. Lines table: stations/headway/colors from the new build; drop 508.
#    Badge -> (stations, headway, color). ION is the first '301' in stats (32 st, #006bb7).
TABLE = {
    "BR": (11, 30.0, "#003767"), "KI": (14, 30.0, "#00853e"),
    "LE": (10, 24.2, "#ff0d00"), "LW": (16, 28.9, "#98002e"),
    "MI": (9, 30.0, "#f57f25"), "RH": (7, 30.0, "#0099c7"),
    "ST": (10, 30.0, "#794500"), "UP": (5, 15.0, "#0075D2"),
    "1": (76, 3.2, "#D5C82B"), "2": (62, 2.8, "#008000"),
    "4": (10, 5.5, "#B300B3"), "5": (48, 4.5, "#FF8000"),
    "6": (34, 7.0, "#808080"), "ION": (32, 10.3, "#006bb7"),
    "301": (144, 10.0, "#0054A6"), "304": (103, 10.0, "#0054A6"),
    "305": (47, 10.0, "#0054A6"), "306": (100, 10.0, "#0054A6"),
    "310": (30, 10.0, "#0054A6"), "312": (39, 10.0, "#0054A6"),
    "501": (142, 10.0, "#ED1C24"), "503": (78, 6.9, "#ED1C24"),
    "504": (103, 9.6, "#ED1C24"), "505": (48, 5.1, "#ED1C24"),
    "506": (100, 10.0, "#ED1C24"), "507": (35, 10.0, "#ED1C24"),
    "509": (21, 9.2, "#ED1C24"), "510": (31, 5.1, "#ED1C24"),
    "511": (22, 6.2, "#ED1C24"), "512": (51, 6.0, "#ED1C24"),
}
text = gtha.read_text()
row_re = re.compile(
    r'(<tr><td><span class="line-cell"><span class="line-badge" style="background:)'
    r'(#[0-9A-Fa-f]+)(;color:#[0-9A-Fa-f]+">)([^<]+)(</span><span class="line-name">[^<]+</span></span></td><td>)'
    r'(\d+)(</td><td>~)([\d.]+)( min</td></tr>)'
)


def fix_row(m):
    badge = m.group(4)
    if badge == "508":
        return m.group(0)  # deleted right after; route has 0 trips in the new feed
    assert badge in TABLE, f"unexpected badge {badge}"
    st, hw, color = TABLE[badge]
    return (
        f"{m.group(1)}{color}{m.group(3)}{badge}{m.group(5)}"
        f"{st}{m.group(7)}{hw:.1f}{m.group(9)}"
    )


text, n = row_re.subn(fix_row, text)
assert n == 31, f"GTHA table rows expected 31, got {n}"
# drop the 508 row (route has 0 trips in the new feed)
old508 = re.search(r'\s*<tr><td><span class="line-cell"><span class="line-badge"[^>]*>508</span>.*?</tr>', text)
assert old508, "508 row not found"
text = text.replace(old508.group(0), "", 1)
rows = re.findall(r'<tr><td><span class="line-cell">', text)
assert len(rows) == 30, f"GTHA table should have 30 rows after dropping 508, got {len(rows)}"
gtha.write_text(text)
print(f"  gtha/index.html: table fixed to 30 rows, 508 removed")

# 2. JSON-LD "How frequent" answer -> identical to the (already corrected) visible FAQ answer.
#    (The two questions also differ in word order; sync the visible one to the LD/caption order.)
text = gtha.read_text()
vis = re.search(
    r'<details class="faq"><summary>How frequent are the train, subway, LRT and streetcar lines in Greater Toronto and Hamilton Area\?</summary><p>(.*?)</p></details>',
    text,
)
assert vis, "visible headways FAQ not found"
visible_hw = vis.group(1)
text = text.replace(
    "<summary>How frequent are the train, subway, LRT and streetcar lines in Greater Toronto and Hamilton Area?</summary>",
    "<summary>How frequent are the train, subway, streetcar and LRT lines in Greater Toronto and Hamilton Area?</summary>",
    1,
)
ld_hw = re.search(
    r'("name": "How frequent are the train, subway, streetcar and LRT lines in Greater Toronto and Hamilton Area\?",\s*"acceptedAnswer": \{\s*"@type": "Answer",\s*"text": ")(.*?)("\s*\}\s*\})',
    text,
    re.S,
)
assert ld_hw, "LD headways FAQ not found"
assert "508" in ld_hw.group(2), "LD headways unexpectedly already fixed"
text = text[: ld_hw.start(2)] + visible_hw + text[ld_hw.end(2):]
gtha.write_text(text)
print("  gtha/index.html: LD headways answer synced to visible FAQ (508 gone)")

# 3. Buses answer (visible + JSON-LD): buses are ON by default for GTHA (defaultBus: true).
BUSES_VIS = (
    "Yes. Buses are included by default; use &quot;Bus&quot; under the map to hide them. "
    "Waiting time at infrequent bus stops is capped at 15 minutes."
)
BUSES_LD = (
    'Yes. Buses are included by default; use \\"Bus\\" under the map to hide them. '
    "Waiting time at infrequent bus stops is capped at 15 minutes."
)
replace_once(
    gtha,
    '<details class="faq"><summary>Are buses included in Greater Toronto and Hamilton Area?</summary><p>Yes, optionally. Waiting time at infrequent bus stops is capped at 15 minutes.</p></details>',
    f'<details class="faq"><summary>Are buses included in Greater Toronto and Hamilton Area?</summary><p>{BUSES_VIS}</p></details>',
)
replace_once(gtha, '"text": "Yes, optionall. Waiting time at infrequent bus stops is capped at 15 minutes."',
             f'"text": "{BUSES_LD}"')

# 4. "Who made this map of Toronto?" -> GTHA wording, and TTC-only -> GO + municipal.
replace_once(
    gtha,
    '<details class="faq"><summary>Who made this map of Toronto?</summary>',
    '<details class="faq"><summary>Who made this map of Greater Toronto and Hamilton Area?</summary>',
)
replace_once(
    gtha,
    'The GTHA by Transit was created by <a href="https://github.com/zhenhuasun">Joshua Sun</a>, using TTC schedules.',
    'The GTHA by Transit was created by <a href="https://github.com/zhenhuasun">Joshua Sun</a>, using GO Transit and municipal transit schedules.',
)

# ---------------------------------------------------------------- Toronto page
tor = SITE / "toronto" / "index.html"
# 5. Overnight streetcar badge colors: map/data uses #0054A6, table had all-red #ED1C24.
text = tor.read_text()
for badge in ("301", "304", "305", "306", "310", "312"):
    old = f'<span class="line-badge" style="background:#ED1C24;color:#fff">{badge}</span>'
    new = f'<span class="line-badge" style="background:#0054A6;color:#fff">{badge}</span>'
    assert text.count(old) == 1, f"toronto badge {badge} not found once"
    text = text.replace(old, new)
tor.write_text(text)
print("  toronto/index.html: 6 overnight-route badges #ED1C24 -> #0054A6")

# ---------------------------------------------------------------- Legal notice
legal = SITE / "mentions-legales" / "index.html"
# 6. GTHA download dates: 15 October 2026 -> 5 November 2026 (16 rows; Toronto stays 7 Oct).
replace_re(legal, r"15 October 2026", "5 November 2026", 16)
# 7. Computed data also ships as .bin now.
replace_once(
    legal,
    "(<code>data/*.json</code>) are derived databases",
    "(<code>data/*.json</code> and <code>data/*.bin</code>) are derived databases",
)
# 8. Site-wide timetables line named only TTC -> point to the table.
replace_once(
    legal,
    "Timetables: TTC GTFS,\n        <a href=\"https://open.toronto.ca/open-data-licence/\">Open Government Licence – Toronto</a>.",
    "Timetables: see the table below for the source and licence of each feed.",
)
# 9. Privacy: saved places live in the user's own browser (localStorage), not on a server.
replace_once(
    legal,
    "Trips are\n        computed in your browser: no location or address is stored.",
    "Trips are\n        computed in your browser: no location or address is stored on any server. Places you save stay in your own browser.",
)
# 10. Stale CSS cache-buster.
replace_once(legal, "styles.css?v=b0171719", "styles.css?v=d7b95465")

# ---------------------------------------------------------------- Home page
home = SITE / "index.html"
# 11. JSON-LD buses answer was the template default (wrong: buses ARE on by default for GTHA).
replace_once(
    home,
    '"text": "Yes, optionally on the map. By default, only subways and trams are shown, to highlight the backbone of the network."',
    '"text": "Yes. Train, subway, streetcar, and bus services can all be included in travel-time calculations."',
)
# 12. Meta/WebSite description: template default "(GO Transit network)" -> map-page wording.
OLD_DESC = "train travel-time map of Greater Toronto and Hamilton Area: pick a starting point and the whole city is colored by how long it takes to get there (GO Transit network)."
NEW_DESC = "Transit travel-time map of Greater Toronto and Hamilton Area: pick a starting point and the whole city is colored by how long it takes to get there."
replace_re(home, re.escape(OLD_DESC), NEW_DESC, 4)
# 13. Stale CSS cache-buster.
replace_once(home, "styles.css?v=5aa9a911", "styles.css?v=d7b95465")

# ---------------------------------------------------------------- 404 page
p404 = SITE / "404.html"
PREFIX = "/gtha-transit-travel-time"
replace_once(p404, "<title>Page not found · Within Tram Reach</title>",
             "<title>Page not found · GTHA by Transit</title>")
replace_once(p404, "Within Tram Reach", "GTHA by Transit")
replace_once(p404, '<a class="brand" href="/">', f'<a class="brand" href="{PREFIX}/">')
replace_once(p404, '<link rel="icon" href="/favicon.svg" type="image/svg+xml" />',
             f'<link rel="icon" href="{PREFIX}/favicon.svg" type="image/svg+xml" />')
replace_once(p404, '<link rel="stylesheet" href="/styles.css?v=b0171719" />',
             f'<link rel="stylesheet" href="{PREFIX}/styles.css?v=d7b95465" />')
replace_once(p404, '<a class="chip" href="/gtha/">', f'<a class="chip" href="{PREFIX}/gtha/">')
replace_once(p404, '<a class="chip" href="/toronto/">', f'<a class="chip" href="{PREFIX}/toronto/">')

print("ALL PAGE FIXES APPLIED")
