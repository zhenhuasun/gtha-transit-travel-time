# Greater Toronto and Hamilton Area (GTHA) Transit Travel Time

Interactive multi-modal transit travel-time map for the GTHA: pick a starting point and the whole region is colored by how long it takes to get there by transit.

👉 **https://zhenhuasun.github.io/gtha-transit-travel-time/**

## Origin

This is a fork of [camilleroux/montpellier-temps-transport](https://github.com/camilleroux/montpellier-temps-transport) by [Camille Roux](https://www.camilleroux.com/) — the concept and the engineering are his work. The original idea comes from Anthony Castrio's [NYC Transit Time Cartogram](https://castrio.me/nyc/), later adapted to Paris by Jules Grandin, then extended by Camille Roux to 20+ networks. This fork borrows that idea and adds a GTHA context: the full GO Transit rail + bus network, UP Express, and nine local transit agencies.

Features: heatmap and isochrones from a draggable start, click-to-destination with detailed itinerary (lines, transfers, walking), address search (Photon / OpenStreetMap) or station search, rail-only or +bus, pan and zoom, share links.

## Coverage

- **GO Transit** (rail + bus) and **UP Express**
- **Local agencies:** TTC, MiWay, York Region Transit, Brampton Transit, Durham Region Transit, Oakville Transit, Burlington Transit, Hamilton Street Railway (Grand River Transit pending — its feed was unreachable at build time)
- **Boundary:** 27 municipalities, from Niagara Falls to Barrie and from Stratford to Peterborough, on a 400 m computation grid

## Run

```
python3 build.py --fetch            # download sources, compute the city, generate pages
python3 build.py --fetch --no-og    # without preview images (no Chrome/ImageMagick needed)

python3 -m http.server 8000 --directory site
```

Then open http://localhost:8000. `build.py` prints a control line at the end (reference day, data size, share of the network within 30 min, farthest station, frequencies).

Separate steps if needed: `fetch_data.py gtha`, `build_data.py gtha`, `build_pages.py`, `tools/render_og.py gtha|home` (Chrome and ImageMagick required), `node tools/check_trips.mjs gtha` probes trips from downtown to the termini and flags abnormal speeds.

Raw sources (`data/gtha/`: GTFS, OSM extracts) are not versioned: they stay local and `fetch_data.py gtha` re-downloads them. Only the computed site data (`site/data/gtha.json`) is versioned.

## Data provenance

Each build writes `sources/gtha.json` (versioned): URL of every source file, download date, size and SHA-256, GTFS validity period, reference day, excluded lines. `fetch_data.py` keeps download details in `data/gtha/manifest.json`. The license / download-date / GTFS-validity table is generated in [sources/README.md](sources/README.md).

City configuration lives in `cities/gtha.json` (GTFS URLs, OpenStreetMap boundary, map center, display options); `cities.py` fills in the defaults.

## Data

- Schedules: GTFS feeds — GO Transit and UP Express via [Metrolinx Open Data](https://www.metrolinx.com/en/about-us/open-data); TTC via [open.toronto.ca](https://open.toronto.ca/dataset/ttc-routes-and-schedules) (Toronto Open Government Licence); MiWay, York Region Transit, Brampton Transit, Durham Region Transit, Oakville Transit, Burlington Transit and Hamilton Street Railway via each agency's open data portal (per-feed licenses in the [legal notice](https://zhenhuasun.github.io/gtha-transit-travel-time/mentions-legales/))
- Municipal boundaries, water and parks: © OpenStreetMap contributors (ODbL), via Overpass
- Address search in the browser: [Photon](https://photon.komoot.io/) (komoot, OpenStreetMap data)

## Model

Times come from GTFS schedules for a typical school-week Tuesday or Thursday, 7 a.m. to 8 p.m.:

- reference day = the most common service pattern among upcoming well-served Tuesdays and Thursdays;
- each inter-station duration = median of the scheduled durations;
- waiting = half the average headway at the stop (bounded between 1 and 15 min);
- transfer = 1.5 min walking + waiting for the next line; walking allowed between close stops (< 450 m);
- platform access time at rail stations (stairs, corridors), counted on entry and exit;
- walking at 75 m/min (4.5 km/h) as the crow flies.

No real-time data or disruptions.

## Credits

GTHA by Transit is based on the Montpellier Temps Transport project created by Camille Roux.

Original repository:
https://github.com/camilleroux/montpellier-temps-transport

The GTHA adaptation includes:

- GO Transit + UP Express GTFS integration
- Nine local agency GTFS feeds merged into one network
- GTHA-wide boundary and 400 m computation grid
- English localization

Additional development and maintenance by Zhenhu Sun.

## Disclaimer
This is an independent personal project created using publicly available open data. Views, analyses, and conclusions presented here are solely those of the author and do not represent the views of any employer, transportation agency, government organization, or affiliated institution.

## Licenses

- Code: MIT license (see [LICENSE](LICENSE)), inherited from the upstream project.
- Computed data (`site/data/*.json`, `sources/*.json`): derived databases published under [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/), as required by OpenStreetMap and the GTFS license.
- Legal notice and license of each source: https://zhenhuasun.github.io/gtha-transit-travel-time/mentions-legales/
