# TTC Travel Time — Toronto

Interactive travel-time map for **Toronto's subway and streetcars** (plus optional **bus**): pick a starting point and the whole city is colored by how long it takes to get there, from the TTC's official scheduled timetables. TTC only — no GO Transit.

👉 **https://zhenhuasun.github.io/ttc-travel-time/**

## Origin

This is a fork of [camilleroux/montpellier-temps-transport](https://github.com/camilleroux/montpellier-temps-transport) by [Camille Roux](https://www.camilleroux.com/) — the concept and the engineering are his work. The original idea comes from Anthony Castrio's [NYC Transit Time Cartogram](https://castrio.me/nyc/), later adapted to Paris by Jules Grandin, then extended by Camille Roux to 27 French, Belgian and Canadian networks.

This fork borrows that idea and adds a Toronto context: TTC schedules, translated to English, reduced to a single city.

Features: heatmap and isochrones from a draggable start, click-to-destination with detailed itinerary (lines, transfers, walking), address search (Photon / OpenStreetMap) or station search, subway+streetcar or +bus, pan and zoom, share links.

## Run

```
python3 build.py --fetch            # download sources, compute the city, generate pages
python3 build.py --fetch --no-og    # without preview images (no Chrome/ImageMagick needed)

python3 -m http.server 8000 --directory site
```

Then open http://localhost:8000. `build.py` prints a control line at the end (reference day, data size, share of the network within 30 min, farthest station, frequencies).

Separate steps if needed: `fetch_data.py toronto`, `build_data.py toronto`, `build_pages.py`, `tools/render_og.py toronto|home` (Chrome and ImageMagick required), `node tools/check_trips.mjs toronto` probes trips from downtown to the termini and flags abnormal speeds.

Raw sources (`data/toronto/`: GTFS, OSM extracts) are not versioned: they stay local and `fetch_data.py toronto` re-downloads them. Only the computed site data (`site/data/toronto.json`) is versioned.

## Data provenance

Each build writes `sources/toronto.json` (versioned): URL of every source file, download date, size and SHA-256, GTFS validity period, reference day, excluded lines. `fetch_data.py` keeps download details in `data/toronto/manifest.json`. The license / download-date / GTFS-validity table is generated in [sources/README.md](sources/README.md).

City configuration lives in `cities/toronto.json` (GTFS URL, OpenStreetMap boundary, map center, display options); `cities.py` fills in the defaults.

## Data

- Schedules: TTC GTFS feed via [open.toronto.ca](https://open.toronto.ca/dataset/ttc-routes-and-schedules) (Toronto Open Government Licence)
- Municipal boundary, water and parks: © OpenStreetMap contributors (ODbL), via Overpass
- Address search in the browser: [Photon](https://photon.komoot.io/) (komoot, OpenStreetMap data)

## Model

Times come from GTFS schedules for a typical school-week Tuesday or Thursday, 7 a.m. to 8 p.m.:

- reference day = the most common service pattern among upcoming well-served Tuesdays and Thursdays;
- each inter-station duration = median of the scheduled durations;
- waiting = half the average headway at the stop (bounded between 1 and 15 min);
- transfer = 1.5 min walking + waiting for the next line; walking allowed between close stops (< 450 m);
- walking at 75 m/min (4.5 km/h) as the crow flies, no access penalty (surface stops).

No real-time data or disruptions.

## Credits

Toronto by Transit is based on the Montpellier Temps Transport project created by Camille Roux.

Original repository:
https://github.com/camilleroux/montpellier-temps-transport

The Toronto adaptation includes:

- TTC GTFS integration
- Toronto-specific travel-time datasets
- English localization
- Toronto-focused branding and visual design
- GitHub Pages deployment

Additional development and maintenance by Zhenhu Sun.

## Disclaimer
This is an independent personal project created using publicly available open data. Views, analyses, and conclusions presented here are solely those of the author and do not represent the views of any employer, transportation agency, government organization, or affiliated institution.

## Licenses

- Code: MIT license (see [LICENSE](LICENSE)), inherited from the upstream project.
- Computed data (`site/data/*.json`, `sources/*.json`): derived databases published under [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/), as required by OpenStreetMap and the GTFS license.
- Legal notice and license of each source: https://zhenhuasun.github.io/ttc-travel-time/mentions-legales/
