#!/usr/bin/env python3
"""Trim a city's GTFS feeds to a window around today, before the build.

Usage: python3 tools/trim_gtfs.py <city> [--days-before 7] [--days-after 75]

Rewrites data/<city>/gtfs*.zip in place (they are re-downloadable with
fetch_data.py): calendar.txt / calendar_dates.txt keep only the services
active at least once in [today - days_before, today + days_after], and
trips.txt keeps only those services' trips. Everything else (stops, routes,
stop_times, shapes, …) is copied byte-for-byte: the build streams
stop_times.txt and filters it to the reference day on its own.

The build always picks its reference date inside that window (a plain
school-term Tuesday or Thursday, at most ~60 days out), so the trimmed
build yields the same network as the full one, while extract_network holds
far fewer trip rows in memory and the merged feed is smaller.

Re-run if the build happens more than ~2 months after trimming.
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
import tempfile
import zipfile
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cities import load_city  # noqa: E402
from fetch_data import record  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TRIMMED_TABLES = ("calendar.txt", "calendar_dates.txt", "trips.txt")
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def parse_ymd(value: str) -> date:
    return date(int(value[:4]), int(value[4:6]), int(value[6:8]))


def read_table(archive: zipfile.ZipFile, name: str) -> tuple[list[str], list[dict]]:
    """Header + row dicts of a GTFS table (([], []) when the file is absent)."""
    if name not in archive.namelist():
        return [], []
    with archive.open(name) as handle:
        reader = csv.reader(io.TextIOWrapper(handle, encoding="utf-8-sig"))
        header = next(reader)
        return header, [dict(zip(header, row)) for row in reader]


def services_in_window(archive: zipfile.ZipFile, start: date, end: date) -> set[str]:
    """Service ids active at least once in [start, end]."""
    _, calendar = read_table(archive, "calendar.txt")
    _, date_rows = read_table(archive, "calendar_dates.txt")
    active: dict[str, set[date]] = defaultdict(set)
    for row in calendar:
        service = row["service_id"]
        day, last = max(parse_ymd(row["start_date"]), start), min(parse_ymd(row["end_date"]), end)
        while day <= last:
            if row[WEEKDAYS[day.weekday()]] == "1":
                active[service].add(day)
            day += timedelta(days=1)
    for row in date_rows:
        day = parse_ymd(row["date"])
        if start <= day <= end:
            if row["exception_type"] == "1":
                active[row["service_id"]].add(day)
            else:
                active[row["service_id"]].discard(day)
    return {service for service, days in active.items() if days}


def trim_feed(path: Path, start: date, end: date) -> tuple[int, int] | None:
    """Rewrite the feed zip trimmed to the window. Returns (trips before, trips after),
    or None when the feed carries no usable service calendar (left untouched)."""
    with zipfile.ZipFile(path) as archive:
        kept_services = services_in_window(archive, start, end)
        headers = {}
        rows: dict[str, list[dict]] = {}
        for name in TRIMMED_TABLES:
            headers[name], rows[name] = read_table(archive, name)
        others = {name: archive.read(name) for name in archive.namelist() if name not in TRIMMED_TABLES}
    if not kept_services:
        return None
    trips_before = len(rows["trips.txt"])
    rows["trips.txt"] = [row for row in rows["trips.txt"] if row["service_id"] in kept_services]
    rows["calendar.txt"] = [row for row in rows["calendar.txt"] if row["service_id"] in kept_services]
    rows["calendar_dates.txt"] = [row for row in rows["calendar_dates.txt"] if start <= parse_ymd(row["date"]) <= end]
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
        with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as out:
            for name in others:
                out.writestr(name, others[name])
            for name in TRIMMED_TABLES:
                if not headers[name]:
                    continue
                buffer = io.StringIO()
                writer = csv.writer(buffer, lineterminator="\n")
                writer.writerow(headers[name])
                for row in rows[name]:
                    writer.writerow([row.get(column, "") for column in headers[name]])
                out.writestr(name, buffer.getvalue().encode("utf-8"))
    Path(tmp.name).replace(path)
    return trips_before, len(rows["trips.txt"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("city")
    parser.add_argument("--days-before", type=int, default=7)
    parser.add_argument("--days-after", type=int, default=75)
    args = parser.parse_args()
    city = load_city(args.city)
    out = ROOT / "data" / city["slug"]
    today = date.today()
    start, end = today - timedelta(days=args.days_before), today + timedelta(days=args.days_after)
    feeds = [("gtfs.zip", city["gtfsUrl"])] + [
        (f"gtfs_{extra['slug']}.zip", extra["url"]) for extra in city.get("gtfsExtra", [])
    ]
    for name, url in feeds:
        path = out / name
        if not path.exists():
            print(f"{name}: missing, run fetch_data.py first — skipped")
            continue
        result = trim_feed(path, start, end)
        if result is None:
            print(f"{name}: no usable service calendar — left untouched")
            continue
        before, after = result
        print(f"{name}: {before} → {after} trips ({after / before:.0%} kept)")
        record(out, name, url)


if __name__ == "__main__":
    main()
