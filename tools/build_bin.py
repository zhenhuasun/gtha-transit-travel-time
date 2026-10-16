#!/usr/bin/env python3
"""Convert site/data/<slug>.json to the binary <slug>.bin format.

Binary layout:
  [0:4]   magic "GTH1"
  [4:8]   jsonLen (uint32 LE)
  [8:8+jsonLen]  JSON header: meta, context, boroughs, parks, routes, routeInfo,
                 stations, routeStates, stationStates + "bin" manifest
  [8+jsonLen:]   binary blobs described by the manifest

Blobs (all little-endian):
  water:  waterPolyPtr int32[numPolys+1], waterRingPtr int32[numRings+1],
          waterCoords float32[numCoords*2]
  cells:  cellRow int32[n], cellCol int32[n], cellXY float32[n*2],
          cellAccPtr int32[n+1], cellAccStation uint16[total], cellAccMeters float32[total]
  adjacency (CSR): adjPtr int32[numNodes+1], adjTarget uint16[numEdges],
          adjWeight float32[numEdges]; extras as JSON [[edgeIdx, extra], ...] in header
The "mask" key is dropped (unused by the client).
Water polygons are simplified (Douglas-Peucker, 20m) before encoding.
"""
import json
import math
import struct
import sys

WATER_TOL = 20.0  # meters; invisible at 400m grid, safe for point-in-polygon


def perp_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    if dx == 0 and dy == 0:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)))
    return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))


def simplify_ring(pts, tol):
    if len(pts) <= 2:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        s, e = stack.pop()
        if e - s < 2:
            continue
        dmax, idx = 0, -1
        for i in range(s + 1, e):
            dd = perp_dist(pts[i], pts[s], pts[e])
            if dd > dmax:
                dmax, idx = dd, i
        if dmax > tol:
            keep[idx] = True
            stack.append((s, idx))
            stack.append((idx, e))
    return [p for p, k in zip(pts, keep) if k]


def main(src, dst):
    d = json.load(open(src))
    blobs = []  # (name, bytes)
    manifest = {}

    def add_blob(name, fmt, values):
        raw = struct.pack(f"<{len(values)}{fmt}", *values)
        # 8-byte align
        pad = (-len(raw)) % 8
        manifest[name] = {"offset": None, "count": len(values), "type": fmt}
        blobs.append((name, raw + b"\x00" * pad))

    # --- water: simplify, then flatten ---
    poly_ptr, ring_ptr, coords = [0], [0], []
    for poly in d["water"]:
        for ring in poly:
            simp = simplify_ring(ring, WATER_TOL)
            for x, y in simp:
                coords += [round(x, 1), round(y, 1)]
            ring_ptr.append(len(coords) // 2)
        poly_ptr.append(len(ring_ptr) - 1)
    add_blob("waterPolyPtr", "i", poly_ptr)
    add_blob("waterRingPtr", "i", ring_ptr)
    add_blob("waterCoords", "f", coords)

    # --- cells ---
    cells = d["cells"]
    n = len(cells)
    rows, cols, xy = [], [], []
    acc_ptr, acc_station, acc_meters = [0], [], []
    for c in cells:
        rows.append(c["row"])
        cols.append(c["col"])
        xy += [c["point"][0], c["point"][1]]
        for station, meters in c["access"]:
            assert station <= 65535, "station index overflow uint16"
            acc_station.append(station)
            acc_meters.append(meters)
        acc_ptr.append(len(acc_station))
    add_blob("cellRow", "i", rows)
    add_blob("cellCol", "i", cols)
    add_blob("cellXY", "f", xy)
    add_blob("cellAccPtr", "i", acc_ptr)
    add_blob("cellAccStation", "H", acc_station)
    add_blob("cellAccMeters", "f", acc_meters)

    # --- adjacency: CSR; extras sparse in JSON ---
    adj = d["adjacency"]
    ptr, target, weight = [0], [], []
    extras = []
    for edges in adj:
        for e in edges:
            assert e[0] <= 65535, "adj target overflow uint16"
            target.append(e[0])
            weight.append(e[1])
            if len(e) == 3:
                extras.append([len(target) - 1, e[2]])
        ptr.append(len(target))
    add_blob("adjPtr", "i", ptr)
    add_blob("adjTarget", "H", target)
    add_blob("adjWeight", "f", weight)

    # --- header JSON ---
    header = {k: d[k] for k in ("meta", "context", "boroughs", "parks", "routes", "routeInfo", "stations", "routeStates", "stationStates")}
    header["adjExtras"] = extras
    # assign offsets (relative to blob section start)
    offset = 0
    for name, raw in blobs:
        manifest[name]["offset"] = offset
        offset += len(raw)
    header["bin"] = manifest
    header_json = json.dumps(header, separators=(",", ":")).encode("utf-8")
    # Pad header to 8-byte alignment so binary blob offsets are valid for
    # Int32Array/Float32Array/Uint16Array (RangeError if misaligned).
    pad = (-len(header_json)) % 8
    header_json += b" " * pad

    with open(dst, "wb") as f:
        f.write(b"GTH1")
        f.write(struct.pack("<I", len(header_json)))
        f.write(header_json)
        for _, raw in blobs:
            f.write(raw)

    import os
    print(f"{src} -> {dst}")
    print(f"  json in: {os.path.getsize(src)/1e6:.1f} MB, bin out: {os.path.getsize(dst)/1e6:.1f} MB")
    print(f"  water polys: {len(poly_ptr)-1}, rings: {len(ring_ptr)-1}, coords: {len(coords)//2}")
    print(f"  cells: {n}, access pairs: {len(acc_station)}")
    print(f"  adj nodes: {len(ptr)-1}, edges: {len(target)}, extras: {len(extras)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
