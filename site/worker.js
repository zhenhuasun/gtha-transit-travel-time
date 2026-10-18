// GTHA Transit Worker - Dijkstra + computeGrid off main thread
// KEEP IN SYNC WITH app.js: solveFrom, computeGrid, MinHeap, walkMinutes, walkMeters,
// crossesRiver, hypot, side, riverKeys
// Protocol:
//   main->worker: {type:'init', payload:{...}}
//   worker->main: {type:'ready'} | {type:'init-error', error}
//   main->worker: {type:'solve', gen, point:[x,y], includeBus}
//   worker->main: {type:'result', gen, solution:{...}, grid:{...}} | {type:'solve-error', gen, error}

let G = null; // graph + data

class MinHeap {
  constructor() { this.k = []; this.v = []; }
  get size() { return this.k.length; }
  push(key, val) {
    const k = this.k, v = this.v;
    k.push(key); v.push(val);
    let i = k.length - 1;
    while (i > 0) {
      const p = (i - 1) >> 1;
      if (k[p] <= k[i]) break;
      [k[p], k[i]] = [k[i], k[p]]; [v[p], v[i]] = [v[i], v[p]];
      i = p;
    }
  }
  pop() {
    const k = this.k, v = this.v;
    const top = v[0], lastK = k.pop(), lastV = v.pop();
    if (k.length) {
      k[0] = lastK; v[0] = lastV;
      let i = 0;
      for (;;) {
        const l = i*2+1, r = l+1;
        let m = i;
        if (l < k.length && k[l] < k[m]) m = l;
        if (r < k.length && k[r] < k[m]) m = r;
        if (m === i) break;
        [k[m], k[i]] = [k[i], k[m]]; [v[m], v[i]] = [v[i], v[m]];
        i = m;
      }
    }
    return top;
  }
}

const hypot = (a, b) => Math.hypot(a[0]-b[0], a[1]-b[1]);
function walkMinutes(meters) { return meters / G.meta.walkMetersPerMinute; }
function side(a, b, c) { return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]); }
function riverKeys(a, b, cb) {
  const keys = new Set();
  // Simplified: check bounding box buckets
  const minX = Math.min(a[0], b[0]), maxX = Math.max(a[0], b[0]);
  const minY = Math.min(a[1], b[1]), maxY = Math.max(a[1], b[1]);
  for (let x = Math.floor(minX/1000); x <= Math.floor(maxX/1000); x++)
    for (let y = Math.floor(minY/1000); y <= Math.floor(maxY/1000); y++)
      keys.add(x + "," + y);
  for (const k of keys) if (cb(k)) return true;
  return false;
}
function crossesRiver(a, b) {
  const buckets = G.rivers;
  if (!buckets.size) return false;
  return riverKeys(a, b, (key) =>
    (buckets.get(key) ?? []).some(([c, d]) => side(a,b,c)*side(a,b,d) < 0 && side(c,d,a)*side(c,d,b) < 0)
  );
}
function walkMeters(a, b) {
  const straight = hypot(a, b);
  if (!crossesRiver(a, b)) return straight;
  const detours = [];
  for (const [endA, endB, length] of G.bridges ?? []) {
    detours.push([hypot(a,endA)+length+hypot(endB,b), endA, endB],
                 [hypot(a,endB)+length+hypot(endA,b), endB, endA]);
  }
  detours.sort((x,y) => x[0]-y[0]);
  return detours.length ? detours[0][0] : straight;
}

function solveFrom(point, includeBus) {
  const graph = G.graph, stations = G.stations;
  const dist = new Float64Array(graph.count).fill(Infinity);
  const prev = new Int32Array(graph.count).fill(-1);
  const seedWalk = new Float64Array(graph.count);
  const heap = new MinHeap();
  const seeds = stations
    .map((st, index) => ({ index, walk: walkMinutes(hypot(point, st)) }))
    .filter(s => s.index < G.stationUsable.length ? G.stationUsable[s.index] : true)
    .sort((a,b) => a.walk - b.walk)
    .slice(0, G.meta.originStationCount * 4)
    .map(s => ({ index: s.index, walk: walkMinutes(walkMeters(point, stations[s.index])) }))
    .filter(s => Number.isFinite(s.walk))
    .sort((a,b) => a.walk - b.walk)
    .slice(0, G.meta.originStationCount);
  for (const seed of seeds) {
    for (const state of G.stationStates[seed.index] ?? []) {
      if (!includeBus && graph.isBus[state]) continue;
      const walk = seed.walk + graph.access[state];
      const time = walk + graph.wait[state];
      if (time < dist[state]) { dist[state] = time; prev[state] = -1; seedWalk[state] = walk; heap.push(time, state); }
    }
  }
  while (heap.size) {
    const u = heap.pop(), du = dist[u];
    for (let e = graph.offsets[u]; e < graph.offsets[u+1]; e++) {
      const v = graph.targets[e];
      if (!includeBus && graph.isBus[v]) continue;
      const nd = du + graph.weights[e];
      if (nd < dist[v]) { dist[v] = nd; prev[v] = u; seedWalk[v] = seedWalk[u]; heap.push(nd, v); }
    }
  }
  const stationTime = new Float64Array(stations.length).fill(Infinity);
  const stationBest = new Int32Array(stations.length).fill(-1);
  for (let s = 0; s < graph.count; s++) {
    const st = graph.station[s];
    const t = dist[s] + graph.access[s];
    if (t < stationTime[st]) { stationTime[st] = t; stationBest[st] = s; }
  }
  return { point, dist, prev, seedWalk, stationTime, stationBest };
}

function computeGrid(solution) {
  const { cellRow, cellCol, cellXY, cellAccPtr, cellAccStation, cellAccMeters } = G.cells;
  const { gridCols: cols, gridRows: rows } = G.meta;
  const times = new Float32Array(cols * rows).fill(NaN);
  const n = cellRow.length;
  for (let c = 0; c < n; c++) {
    let best = Infinity;
    for (let k = cellAccPtr[c]; k < cellAccPtr[c+1]; k++) {
      const t = solution.stationTime[cellAccStation[k]] + walkMinutes(cellAccMeters[k]);
      if (t < best) best = t;
    }
    const px = cellXY[2*c], py = cellXY[2*c+1];
    const direct = walkMinutes(walkMeters(solution.point, [px, py]));
    if (direct < best) best = direct;
    times[cellRow[c] * cols + cellCol[c]] = Math.min(best, 180);
  }
  return { times, cols, rows };
}

self.onmessage = (ev) => {
  const msg = ev.data;
  try {
    if (msg.type === 'init') {
      const p = msg.payload;
      G = {
        graph: p.graph,
        stations: p.stations,
        stationStates: p.stationStates,
        stationUsable: p.stationUsable,
        cells: p.cells,
        meta: p.meta,
        rivers: new Map(p.rivers),
        bridges: p.bridges,
      };
      self.postMessage({ type: 'ready' });
    } else if (msg.type === 'solve') {
      if (!G) { self.postMessage({ type: 'solve-error', gen: msg.gen, error: 'not-initialized' }); return; }
      const solution = solveFrom(msg.point, msg.includeBus);
      const grid = computeGrid(solution);
      self.postMessage({
        type: 'result', gen: msg.gen,
        solution: { point: solution.point, dist: solution.dist, prev: solution.prev,
                    seedWalk: solution.seedWalk, stationTime: solution.stationTime,
                    stationBest: solution.stationBest },
        grid: { times: grid.times, cols: grid.cols, rows: grid.rows },
      }, [solution.dist.buffer, solution.prev.buffer, solution.seedWalk.buffer,
          solution.stationTime.buffer, solution.stationBest.buffer, grid.times.buffer]);
    }
  } catch (err) {
    if (msg.type === 'init') self.postMessage({ type: 'init-error', error: String(err?.message || err) });
    else self.postMessage({ type: 'solve-error', gen: msg.gen, error: String(err?.message || err) });
  }
};
