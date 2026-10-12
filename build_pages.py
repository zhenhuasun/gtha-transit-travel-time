#!/usr/bin/env python3
"""Render the home page, one page per city (cities/*.json), the 404 page, sitemap.xml and robots.txt.

Usage: python3 build_pages.py   (run build_data.py <city> first: figures come from sources/<city>.json)
"""

from __future__ import annotations

import hashlib
import html
import json
from datetime import date
from pathlib import Path
from string import Template

from cities import load_cities

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"
SITE_URL = "https://zhenhuasun.github.io/ttc-travel-time/"
GITHUB_URL = "https://github.com/zhenhuasun/ttc-travel-time"
X_URL = "https://x.com/CamilleRoux"
LINKEDIN_URL = "https://www.linkedin.com/in/camilleroux"
BLUESKY_URL = "https://bsky.app/profile/camilleroux.com"
AUTHOR_URL = "https://www.camilleroux.com/"
SITE_NAME = "Within Tram Reach"
PUBLISHER_NAME = "zhenhuasun"
PUBLISHER_URL = "https://github.com/zhenhuasun"
LICENCES = {
    "lo": ("Licence Ouverte 2.0", "https://www.etalab.gouv.fr/licence-ouverte-open-licence/"),
    "odbl": ("ODbL", "https://opendatacommons.org/licenses/odbl/1-0/"),
    "mobilites": ("Licence Mobilités", "https://wiki.lafabriquedesmobilites.fr/wiki/Licence_Mobilit%C3%A9s"),
    "ccby": ("CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/deed.fr"),
    "togl": ("Open Government Licence – Toronto", "https://open.toronto.ca/open-data-licence/"),
}
GEO_CREDITS = {
    "ban": '<a href="https://geo.api.gouv.fr/">municipal boundaries</a>, address search via the\n'
    '          <a href="https://adresse.data.gouv.fr/">Base Adresse Nationale</a>.',
    "photon": 'OpenStreetMap administrative boundaries, address search via\n'
    '          <a href="https://photon.komoot.io/">Photon</a> (komoot, OpenStreetMap data).',
}
ODBL_URL = "https://opendatacommons.org/licenses/odbl/1-0/"
MODE_LABEL_SHORT = {"tram": "Tram", "metro": "Subway", "metro+tram": "Subway and tram"}
MODE_NAMES = {"metro": "Subway", "rer": "RER", "train": "Train", "tram": "Tram", "funicular": "Funicular", "cable": "Cable car", "busway": "Busway", "bhns": "BHNS"}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

esc = html.escape


def text_color(background: str) -> str:
    """Black or white text, whichever reads best on a line colour (yellow lines need black)."""
    value = int(background.lstrip("#")[:6] or "888888", 16)
    luminance = 0.299 * (value >> 16) + 0.587 * ((value >> 8) & 255) + 0.114 * (value & 255)
    return "#111" if luminance > 150 else "#fff"


def line_badge(color: str, name: str) -> str:
    return f'<span class="line-badge" style="background:{color};color:{text_color(color)}">{esc(name)}</span>'


def thousands(value: int) -> str:
    """English thousands separator: 2445 → "2,445"."""
    return f"{value:,}"


def num(value: float) -> str:
    """English decimal point: 4.4 → "4.4"."""
    return f"{value:g}"


def short_hash(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()[:8] if path.exists() else "0"


def french_date(value: str, weekday: bool = False) -> str:
    day = date.fromisoformat(value[:10])
    text = f"{day.day} {MONTHS[day.month - 1]} {day.year}"
    return f"{WEEKDAYS[day.weekday()]} {text}" if weekday else text


def load_built_cities() -> list[dict]:
    """Cities whose data has been built, with their figures (sources/<city>.json)."""
    cities = []
    for city in load_cities():
        sources = ROOT / "sources" / f"{city['slug']}.json"
        if not sources.exists() or not (SITE / "data" / f"{city['slug']}.json").exists():
            print(f"  {city['slug']} skipped: run build_data.py {city['slug']} first")
            continue
        city["sources"] = json.loads(sources.read_text(encoding="utf-8"))
        city["stats"] = city["sources"]["stats"]
        cities.append(city)
    return cities


def json_ld(data: dict) -> str:
    body = json.dumps(data, ensure_ascii=False, indent=2).replace("</", "<\\/")
    return '    <script type="application/ld+json">\n    ' + body.replace("\n", "\n    ") + "\n    </script>"


def head(*, title: str, description: str, url: str, base: str, image: str | None, image_alt: str, published: str, graph: list,
         author_name: str = "Camille Roux", author_url: str = AUTHOR_URL) -> str:
    """<head> content shared by every page: SEO, social previews, structured data."""
    title_text = esc(title.split(" · ")[0])
    image_tags = (
        [
            f'    <meta property="og:image" content="{image}" />',
            '    <meta property="og:image:width" content="1200" />',
            '    <meta property="og:image:height" content="630" />',
            f'    <meta property="og:image:alt" content="{esc(image_alt)}" />',
            f'    <meta name="twitter:image" content="{image}" />',
        ]
        if image
        else []
    )
    return "\n".join(
        [
            '    <meta charset="utf-8" />',
            '    <meta name="viewport" content="width=device-width, initial-scale=1" />',
            f"    <title>{esc(title)}</title>",
            f'    <meta name="description" content="{esc(description)}" />',
            f'    <link rel="canonical" href="{url}" />',
            '    <meta name="theme-color" content="#3aa70b" />',
            f'    <link rel="icon" href="{base}favicon.svg" type="image/svg+xml" />',
            f'    <link rel="icon" href="{base}favicon-32.png" type="image/png" sizes="32x32" />',
            f'    <link rel="apple-touch-icon" href="{base}apple-touch-icon.png" />',
            f'    <meta name="author" content="{esc(author_name)}" />',
            f'    <link rel="author" href="{author_url}" />',
            '    <meta property="og:type" content="website" />',
            '    <meta property="og:locale" content="en_US" />',
            f'    <meta property="og:site_name" content="{SITE_NAME}" />',
            f'    <meta property="og:title" content="{title_text}" />',
            f'    <meta property="og:description" content="{esc(description)}" />',
            f'    <meta property="og:url" content="{url}" />',
            *image_tags,
            f'    <meta property="article:author" content="{author_url}" />',
            f'    <meta property="article:published_time" content="{published}T08:00:00+02:00" />',
            '    <meta name="twitter:card" content="summary_large_image" />',
            f'    <meta name="twitter:title" content="{title_text}" />',
            f'    <meta name="twitter:description" content="{esc(description)}" />',
            json_ld({"@context": "https://schema.org", "@graph": graph}),
            '    <link rel="preconnect" href="https://fonts.bunny.net" />',
            '    <link rel="stylesheet" href="https://fonts.bunny.net/css?family=inter:400,500,600,700,800" />',
        ]
    )


def header(base: str) -> str:
    return f"""    <header class="topbar">
      <nav class="topbar-inner" aria-label="Main navigation">
        <a class="brand" href="{base}"><img src="{base}favicon.svg" width="22" height="22" alt="" /> {SITE_NAME}</a>
      </nav>
    </header>"""


def footer(base: str, data_credit: str, geocoder: str = "ban") -> str:
    return f"""    <footer class="site-footer">
      <div class="footer-inner">
        <p class="footer-author">
          Forked from <a href="https://github.com/camilleroux/montpellier-temps-transport">montpellier-temps-transport</a>
          by Camille Roux — the concept and engineering are his work, based on the idea by Anthony Castrio and
          Jules Grandin. This Toronto edition is published by <a href="{PUBLISHER_URL}" rel="author">zhenhuasun</a>.
        </p>
        <p class="footer-links">
          <a href="{GITHUB_URL}" rel="noopener">Source code on GitHub</a> ·
          <a href="{GITHUB_URL}/issues" rel="noopener">Report an error</a> ·
          <a href="{base}mentions-legales/">Legal notice and licenses</a>
        </p>
        <p class="footer-credits">
          Original idea: Anthony Castrio's <a href="https://castrio.me/nyc/">NYC Transit Time Cartogram</a>,
          later adapted to Paris by Jules Grandin
          (<a href="https://julesgrandin.github.io/paris-temps-transport/">C'est encore loin&nbsp;?</a>).
          {data_credit} Basemap © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>,
          {GEO_CREDITS[geocoder]}
          Computed data published under the <a href="{ODBL_URL}">ODbL</a> license, code under the MIT license.
        </p>
      </div>
    </footer>"""


def faq_block(entries: list[tuple]) -> str:
    """Entries are (question, answer) or (question, answer, answer_html) when the visible answer carries links."""
    return "\n".join(
        f'        <details class="faq"><summary>{esc(entry[0])}</summary><p>{entry[2] if len(entry) > 2 else esc(entry[1])}</p></details>'
        for entry in entries
    )


def faq_schema(entries: list[tuple]) -> dict:
    return {
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": entry[0], "acceptedAnswer": {"@type": "Answer", "text": entry[1]}} for entry in entries
        ],
    }


def credits_entry(question: str) -> tuple:
    """« Who made this? »: the original authors first, then the author of these maps."""
    text = (
        "The idea comes from Anthony Castrio's NYC Transit Time Cartogram, later adapted to Paris by Jules Grandin "
        '("C\'est encore loin ?"), then extended by Camille Roux \u2014 the concept and engineering are his work. '
        "This Toronto edition is a fork by zhenhuasun, using TTC schedules. The code is open on GitHub."
    )
    html_text = (
        'The idea comes from <a href="https://castrio.me/nyc/">NYC Transit Time Cartogram</a> by Anthony Castrio, later '
        'adapted to Paris by Jules Grandin (<a href="https://julesgrandin.github.io/paris-temps-transport/">C\'est encore '
        f'loin&nbsp;?</a>), then extended by <a href="https://github.com/camilleroux/montpellier-temps-transport">Camille Roux</a> '
        '\u2014 the concept and engineering are his work. This Toronto edition is a fork by '
        f'<a href="{PUBLISHER_URL}">zhenhuasun</a>, using TTC schedules. The code is open on '
        f'<a href="{GITHUB_URL}">GitHub</a>.'
    )
    return (question, text, html_text)


def author_schema() -> dict:
    return {
        "@type": "Person",
        "@id": PUBLISHER_URL + "#me",
        "name": PUBLISHER_NAME,
        "url": PUBLISHER_URL,
        "sameAs": [PUBLISHER_URL],
    }


# « in France, in Belgium and in Quebec »: where the cities are, for the home page.
COUNTRY_IN = {"FR": "in France", "BE": "in Belgium", "CA": "in Quebec", "CH": "in Switzerland", "LU": "in Luxembourg"}


def city_faq(city: dict) -> list[tuple]:
    stats, sources = city["stats"], city["sources"]
    name, rail = city["name"], city["railNoun"]
    lines = stats["lines"]
    headways = ", ".join(f"{MODE_NAMES.get(line['mode'], 'line').lower()} {line['name']}: {num(line['headway'])} min" for line in lines)
    fastest = min(lines, key=lambda line: line["headway"])
    period = sources["gtfs"].get("servicePeriod") or [None, None]
    fetched = sources["gtfs"].get("fetchedAt")
    return [
        (
            f"How long does it take to cross {name} by {rail}?",
            f"From downtown ({stats['center']}), {stats['within15']}% of {city['railStations']} are within 15 minutes and "
            f"{stats['within30']}% within 30 minutes, walking and waiting included. The farthest, {stats['farthestStation']}, "
            f"is about {stats['farthestMinutes']} minutes away.",
        ),
        (
            f"How frequent are the {rail} lines in {name}?",
            f"On a weekday during the day, the average interval between two services is {headways}. The most frequent "
            f"line is {fastest['name']}, with a service about every {num(fastest['headway'])} minutes.",
        ),
        (
            "Where do the timetables used come from?",
            f"From the scheduled timetables published by the {city['network']} network (GTFS format, {LICENCES[city['gtfsLicence']][0]})"
            + (f", downloaded on {french_date(fetched)}" if fetched else "")
            + (f" and valid until {french_date(period[1])}" if period[1] else "")
            + f". Travel times are for {french_date(sources['referenceDate'], weekday=True)}, between 7 a.m. and 8 p.m.",
        ),
        (
            f"Are buses included in {name}?",
            f"Yes, optionally: check \"{city['busLabel']}\" under the map. By default, only {rail} are shown. "
            "Waiting time at infrequent bus stops is capped at 15 minutes.",
        ),
        (
            "How are travel times calculated?",
            "For each trip: walk to the stop at 4.5 km/h, waiting time equal to half the interval between two "
            "services, scheduled time between stops, transfers with 1.5 minutes of walking"
            + (", plus 1 minute to reach the subway platform" if any(line["mode"] == "metro" for line in lines) else "")
            + '. No real-time data or disruptions: this is the city "on paper".',
        ),
        credits_entry(f"Who made this map of {name}?"),
    ]


def original_map(city: dict) -> str:
    """Paris had a map before this site: Jules Grandin's, which inspired it. It comes first, above this one."""
    original = city.get("originalMap")
    if not original:
        return ""
    return f"""        <aside class="original-map">
          <p>
            <strong>The original map is {esc(original["author"])}'s:</strong>
            <a href="{esc(original["url"])}">{esc(original["title"]).replace(" ?", "&nbsp;?")}</a>, in {esc(original["modes"])}, which
            inspired this whole site (itself part of Anthony Castrio's <a href="https://castrio.me/nyc/">NYC Transit Time Cartogram</a>).
            Go see it! This version starts from the {esc(city["network"])} timetables and adds
            {esc(original["adds"])}.
          </p>
        </aside>
"""


def render_city(template: Template, cities: list[dict], city: dict) -> str:
    url = SITE_URL + city["path"]
    base = "../"
    stats = city["stats"]
    rail_noun = city["railNoun"]
    description = (
        f"{rail_noun} travel-time map of {city['name']}: pick a starting point and the whole city is colored "
        f"by how long it takes to get there ({city['network']} network)."
    )
    faq = city_faq(city)
    graph = [
        {
            "@type": "WebApplication",
            "name": city["title"],
            "url": url,
            "description": description,
            "inLanguage": "en",
            "applicationCategory": "TravelApplication",
            "operatingSystem": "Web",
            "isAccessibleForFree": True,
            "author": {"@id": PUBLISHER_URL + "#me"},
            "spatialCoverage": {"@type": "Place", "name": city["metropole"]},
            "isBasedOn": ["https://castrio.me/nyc/", "https://julesgrandin.github.io/paris-temps-transport/"],
            "datePublished": city["published"],
            "dateModified": city["sources"]["builtAt"][:10],
        },
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": SITE_NAME, "item": SITE_URL},
                {"@type": "ListItem", "position": 2, "name": city["name"], "item": url},
            ],
        },
        faq_schema(faq),
        author_schema(),
    ]
    fastest = min(stats["lines"], key=lambda line: line["headway"])
    tiles = [
        (f"{stats['within30']}%", f"of {city['railStations']} within 30 min of downtown ({stats['center']})"),
        (str(stats["railStations"]), city["railStations"]),
        (f"{num(fastest['headway'])} min", f"between services on line {fastest['name']}, the most frequent"),
        (f"{stats['farthestMinutes']} min", f"from downtown to {stats['farthestStation']}, the farthest station"),
    ]
    stat_tiles = "\n".join(f'          <div class="stat"><strong>{esc(value)}</strong><span>{esc(label)}</span></div>' for value, label in tiles)
    line_rows = "\n".join(
        f'            <tr><td>{line_badge(line["color"], line["name"])} '
        f'{esc(MODE_NAMES.get(line["mode"], ""))}</td><td>{line["stations"]}</td><td>~{num(line["headway"])} min</td></tr>'
        for line in stats["lines"]
    )
    # Single city: plain title, no city switcher.
    rest = esc(city["title"][len(city["name"]):])
    headline = esc(city["name"]) + "&nbsp;".join(rest.rsplit(" ", 1))
    config = {
        "slug": city["slug"],
        "name": city["name"],
        "dataVersion": short_hash(SITE / "data" / f"{city['slug']}.json"),
        "defaultFrom": city["defaultFrom"],
        "railNoun": rail_noun,
        "railStations": city["railStations"],
        "busNoun": city["busNoun"],
        "geocoder": city["geocoder"],
        "searchBbox": city["osmBbox"],
    }
    feeds = " and ".join(f'<a href="{esc(feed["dataset"])}">GTFS {esc(feed["network"])}</a>' for feed in gtfs_feeds(city))
    data_credit = f'Timetables: {feeds} ({esc(city["metropole"])}).'

    values = {
        "head": head(
            title=f"{city['title']} · {city['titleSuffix']}",
            description=description,
            url=url,
            base=base,
            image=None,
            image_alt=city["ogAlt"],
            published=city["published"],
            graph=graph,
            author_name=PUBLISHER_NAME,
            author_url=PUBLISHER_URL,
        ),
        "header": header(base),
        "footer": footer(base, data_credit, city["geocoder"]),
        "base": base,
        "city_config": json.dumps(config, ensure_ascii=False).replace("</", "<\\/"),
        "original_map": original_map(city),
        "headline": headline,
        "name": esc(city["name"]),
        "area": esc(city.get("area", "of the metro area")),
        "rail_noun": esc(rail_noun),
        "rail_label": esc(city["railLabel"]),
        "bus_label": esc(city["busLabel"]),
        "search_example": esc(city["searchExample"]),
        "network": esc(city["network"]),
        "stat_tiles": stat_tiles,
        "line_rows": line_rows,
        "faq_html": faq_block(faq),
        "styles_version": short_hash(SITE / "styles.css"),
        "app_version": short_hash(SITE / "app.js"),
    }
    return template.substitute(values)


def render_home(template: Template, cities: list[dict]) -> str:
    """Single-city site: the home page is a splash screen for the one city map."""
    city = cities[0]
    description = (
        f"{city['railNoun']} travel-time map of {city['name']}: pick a starting point and the whole city is colored "
        f"by how long it takes to get there ({city['network']} network)."
    )
    faq = [
        (
            "Where do the travel times come from?",
            f"From the official scheduled timetables of the {city['network']} network, published as open data "
            "in GTFS format. They cover an ordinary weekday, between 7 a.m. and 8 p.m.",
        ),
        (
            "Are the displayed times reliable?",
            'These are "on paper" averages: walk to the stop, waiting time equal to half the interval between '
            "two services, scheduled time between stops, and transfers. No real-time data or disruptions.",
        ),
        (
            "Are buses included?",
            "Yes, optionally on the map. By default, only subways and trams are shown, "
            "to highlight the backbone of the network.",
        ),
        credits_entry("Who made this site?"),
    ]
    graph = [
        {
            "@type": "WebSite",
            "@id": SITE_URL + "#site",
            "name": SITE_NAME,
            "url": SITE_URL,
            "description": description,
            "inLanguage": "en",
            "author": {"@id": PUBLISHER_URL + "#me"},
        },
        faq_schema(faq),
        author_schema(),
    ]
    values = {
        "head": head(
            title=f"{SITE_NAME} · {city['title']}",
            description=description,
            url=SITE_URL,
            base="./",
            image=None,
            image_alt="",
            published=city["published"],
            graph=graph,
            author_name=PUBLISHER_NAME,
            author_url=PUBLISHER_URL,
        ),
        "header": header("./"),
        "footer": footer("./", ""),
        "city_name": esc(city["name"]),
        "city_title": esc(city["title"]),
        "city_path": esc(city["path"]),
        "rail_noun": esc(city["railNoun"]),
        "network": esc(city["network"]),
        "faq_html": faq_block(faq),
        "styles_version": short_hash(SITE / "styles.css"),
    }
    return template.substitute(values)


def gtfs_feeds(city: dict) -> list[dict]:
    """The feeds of a city: its main GTFS, then the extra ones merged into it (the REM next to the STM in Montréal)."""
    main = {
        "network": city.get("gtfsNetwork", city["network"]),
        "dataset": city["gtfsDataset"],
        "licence": city["gtfsLicence"],
        "fetchedAt": city["sources"]["gtfs"].get("fetchedAt"),
    }
    fetched = {extra["network"]: extra.get("fetchedAt") for extra in city["sources"].get("gtfsExtra", [])}
    extras = [{**extra, "fetchedAt": fetched.get(extra["network"])} for extra in city.get("gtfsExtra", [])]
    return [main, *extras]


def render_legal(cities: list[dict]) -> str:
    """Legal notice and the licence of every source."""
    rows = "\n".join(
        f'          <tr><td>{esc(city["name"])}</td><td><a href="{esc(feed["dataset"])}">GTFS {esc(feed["network"])}</a></td>'
        f'<td><a href="{LICENCES[feed["licence"]][1]}">{LICENCES[feed["licence"]][0]}</a></td>'
        f'<td>{french_date(feed["fetchedAt"]) if feed["fetchedAt"] else "—"}</td></tr>'
        for city in sorted(cities, key=lambda item: item["name"])
        for feed in gtfs_feeds(city)
    )
    graph = [
        {
            "@type": "Person",
            "@id": PUBLISHER_URL + "#me",
            "name": PUBLISHER_NAME,
            "url": PUBLISHER_URL,
            "sameAs": [PUBLISHER_URL],
        }
    ]
    return f"""<!doctype html>
<html lang="en">
  <head>
{head(title=f"Legal notice and licenses · {SITE_NAME}", description="Publisher, hosting, privacy and data licenses used by Within Tram Reach.", url=SITE_URL + "mentions-legales/", base="../", image=None, image_alt="", published="2026-10-05", graph=graph, author_name=PUBLISHER_NAME, author_url=PUBLISHER_URL)}
    <link rel="stylesheet" href="../styles.css?v={short_hash(SITE / 'styles.css')}" />
  </head>
  <body>
{header('../')}
    <main class="page">
      <nav class="breadcrumb" aria-label="Breadcrumb">
        <a href="../">{SITE_NAME}</a> <span aria-hidden="true">›</span> <span aria-current="page">Legal notice</span>
      </nav>
      <section class="section">
        <h1 class="page-title">Legal notice and licenses</h1>
        <h2>Publisher</h2>
        <p>This site is published personally by <a href="{PUBLISHER_URL}" rel="author">{PUBLISHER_NAME}</a>.
        Contact: via the project's <a href="{GITHUB_URL}/issues">GitHub issues</a>.</p>
        <h2>About this site</h2>
        <p>This site is a fork of <a href="https://github.com/camilleroux/montpellier-temps-transport">montpellier-temps-transport</a>
        by <a href="https://github.com/camilleroux/montpellier-temps-transport">Camille Roux</a>. The concept and the engineering are his work: the original idea
        comes from Anthony Castrio's <a href="https://castrio.me/nyc/">NYC Transit Time Cartogram</a>, later adapted to Paris
        by Jules Grandin, then extended by Camille Roux. This fork borrows that idea, keeps his build pipeline and map engine,
        and adds a Toronto context — TTC schedules, translated to English and reduced to a single city.</p>
        <h2>Hosting</h2>
        <p>GitHub, Inc. (GitHub Pages), 88 Colin P. Kelly Jr. Street, San Francisco, CA 94107, United States.</p>
        <h2>Personal data</h2>
        <p>No audience measurement, no cookies, no personal identifiers. Trips are
        computed in your browser: no location or address is stored. Address search queries
        komoot's Photon API (photon.komoot.io, OpenStreetMap data).</p>
        <h2>Licenses</h2>
        <p>The code is published under the MIT license on <a href="{GITHUB_URL}">GitHub</a>. The computed data
        (<code>data/*.json</code>) are derived databases, published under the <a href="{ODBL_URL}">ODbL</a> license.
        Basemap and routes: © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>
        (ODbL); municipal boundary: OpenStreetMap administrative boundary (ODbL). Timetables: TTC GTFS,
        <a href="https://open.toronto.ca/open-data-licence/">Open Government Licence – Toronto</a>.</p>
        <table class="lines-table">
          <caption>Timetables used for each city</caption>
          <thead><tr><th scope="col">City</th><th scope="col">Source</th><th scope="col">License</th><th scope="col">Downloaded on</th></tr></thead>
          <tbody>
{rows}
          </tbody>
        </table>
      </section>
    </main>
{footer("../", "", "photon")}
  </body>
</html>
"""


def write_sources_readme(cities: list[dict]) -> None:
    lines = [
        "# Data provenance",
        "",
        "Generated by `build_pages.py` from the `sources/<city>.json` records.",
        "",
        "| City | Network | License | GTFS downloaded on | GTFS validity | Reference day |",
        "|---|---|---|---|---|---|",
    ]
    for city in sorted(cities, key=lambda item: item["name"]):
        gtfs = city["sources"]["gtfs"]
        period = gtfs.get("servicePeriod") or ["?", "?"]
        how = " (manual)" if gtfs.get("how") == "manual" else ""
        lines.append(
            f"| [{city['name']}]({city['slug']}.json) | {city['network']} | {LICENCES[city['gtfsLicence']][0]} | "
            f"{gtfs.get('fetchedAt', '?')[:10]}{how} | {period[0]} → {period[1]} | {city['sources']['referenceDate']} |"
        )
    (ROOT / "sources" / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_404(cities: list[dict]) -> str:
    links = "\n".join(f'          <a class="chip" href="/{city["path"]}">{esc(city["name"])}</a>' for city in cities)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Page not found · {SITE_NAME}</title>
    <meta name="robots" content="noindex" />
    <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
    <link rel="stylesheet" href="https://fonts.bunny.net/css?family=inter:400,500,600,700,800" />
    <link rel="stylesheet" href="/styles.css?v={short_hash(SITE / 'styles.css')}" />
  </head>
  <body>
{header('/')}
    <main class="page">
      <section class="hero">
        <h1>End of the line!</h1>
        <p class="lede">This page doesn't exist. Pick a city to get back on track.</p>
        <nav class="city-switch" aria-label="Cities">
{links}
        </nav>
      </section>
    </main>
  </body>
</html>
"""


def main() -> None:
    cities = load_built_cities()
    city_template = Template((ROOT / "templates" / "city.html").read_text(encoding="utf-8"))
    for city in cities:
        page = SITE / city["path"] / "index.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(render_city(city_template, cities, city), encoding="utf-8")
        print(f"Wrote {page.relative_to(ROOT)}")

    home_template = Template((ROOT / "templates" / "home.html").read_text(encoding="utf-8"))
    (SITE / "index.html").write_text(render_home(home_template, cities), encoding="utf-8")
    (SITE / "404.html").write_text(render_404(cities), encoding="utf-8")
    (SITE / "mentions-legales").mkdir(exist_ok=True)
    (SITE / "mentions-legales" / "index.html").write_text(render_legal(cities), encoding="utf-8")
    write_sources_readme(cities)
    print("Wrote site/index.html, site/404.html")

    today = date.today().isoformat()
    urls = [f"  <url><loc>{SITE_URL}</loc><lastmod>{today}</lastmod></url>"]
    urls += [
        f"  <url><loc>{SITE_URL}{city['path']}</loc><lastmod>{city['sources']['builtAt'][:10]}</lastmod></url>" for city in cities
    ]
    urls += [f"  <url><loc>{SITE_URL}mentions-legales/</loc><lastmod>{today}</lastmod></url>"]
    (SITE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>\n",
        encoding="utf-8",
    )
    (SITE / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}sitemap.xml\n", encoding="utf-8")
    print("Wrote site/sitemap.xml, site/robots.txt")


if __name__ == "__main__":
    main()
