# Trail Enrichment

Adds nearest hiking trail information to each summit in `summits.json`.

## What it does

For each of the 379 summits, the script finds the closest marked hiking trail
(within 500 m) using OpenStreetMap data and writes four fields:

| Field | Example | Description |
|-------|---------|-------------|
| `tr`  | `8`     | Distance to nearest trail in meters (omitted if > 500 m) |
| `tn`  | `"2407"` | Trail name or KST route reference number |
| `tc`  | `"blue"` | Trail blaze color: red / blue / green / yellow |
| `ti`  | `571354` | OSM relation ID (link: `openstreetmap.org/relation/{ti}`) |

Result: **248 / 379 summits** have a marked trail within 500 m.

## How it works

### 1. Overpass API query

The script requests all hiking route relations in Slovakia from the
[Overpass API](https://overpass-api.de):

```
[out:json][timeout:300][maxsize:134217728];
(
  relation["route"="hiking"](47.73,16.83,49.61,22.57);
);
out body;
>;
out skel qt;
```

- `relation["route"="hiking"]` -- all hiking routes tagged in OSM
- `(47.73,16.83,49.61,22.57)` -- Slovakia bounding box (south, west, north, east)
- `out body; >; out skel qt;` -- fetch relation tags, then recurse down to get
  all member ways and their node coordinates

The response contains ~3000+ hiking route relations with full geometry.

### 2. Trail geometry reconstruction

The script indexes all nodes (lat/lon) and ways (ordered node lists) from the
response, then builds trail segments by resolving each relation's member ways
into coordinate arrays.

### 3. Distance computation

For each summit, the script:
1. Pre-filters trails using a bounding box check (fast reject)
2. Computes point-to-segment distance for each trail way segment using
   Haversine formula with flat-earth projection for the closest-point calculation
3. Keeps the nearest trail within 500 m

Trail color is extracted from OSM tags: `osmc:symbol` (primary), `colour`, or
`color` (fallbacks). Only standard KST colors are recognized: red, blue, green,
yellow.

## How to run

**Prerequisites:** `pip install requests` (only external dependency).

### Dry run (no changes to summits.json)

```bash
python3 scripts/enrich_trails.py
```

Reads summits from `summits.json`, queries Overpass API (or uses cache), writes
results to `scripts/trail_enrichment.json`.

### With merge into summits.json

```bash
python3 scripts/enrich_trails.py --merge
```

Same as above, plus updates trail fields (tr, tn, tc, ti) directly in
`summits.json`. Summits without a nearby trail get their stale trail fields
removed.

### Force fresh data (delete cache first)

```bash
rm scripts/trails_cache.json
python3 scripts/enrich_trails.py --merge
```

## Cache

On first run, the Overpass API response is saved to `scripts/trails_cache.json`
(~155 MB). Subsequent runs load from cache automatically, skipping the 1-3
minute API call. The cache file is gitignored.

To refresh trail data from OSM, delete the cache and re-run.

**Rate limit note:** The Overpass API is a shared public resource. Avoid
running the uncached query repeatedly. One query per enrichment cycle is
sufficient.
