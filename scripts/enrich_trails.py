#!/usr/bin/env python3
"""
Enrich SOTA summit data with nearest hiking trail information from OpenStreetMap.

Queries Overpass API for all hiking route relations in Slovakia,
reconstructs trail geometries, computes distance to each summit,
and writes trail fields (tr, tn, tc, ti) into summits.json.

Usage:
    python3 scripts/enrich_trails.py [--cache trails_cache.json] [--merge]

Options:
    --cache FILE   Cache Overpass response to FILE (default: scripts/trails_cache.json)
    --merge        Merge results into summits.json
"""

import json
import math
import os
import sys
import time
import argparse
import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Slovakia bounding box
SK_BBOX = "47.73,16.83,49.61,22.57"

# Search radius in meters
SEARCH_RADIUS_M = 500

OVERPASS_QUERY = f"""
[out:json][timeout:300][maxsize:134217728];
(
  relation["route"="hiking"]({{bbox}});
);
out body;
>;
out skel qt;
""".replace("{bbox}", SK_BBOX)


def haversine_m(lat1, lon1, lat2, lon2):
    """Haversine distance in meters between two points."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def point_to_segment_distance_m(plat, plon, alat, alon, blat, blon):
    """
    Approximate distance from point P to line segment A-B in meters.
    Projects P onto AB, clamps to segment, returns haversine distance.
    """
    # Use flat-earth approximation for projection (good enough at this scale)
    cos_lat = math.cos(math.radians(plat))
    ax, ay = alon * cos_lat, alat
    bx, by = blon * cos_lat, blat
    px, py = plon * cos_lat, plat

    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return haversine_m(plat, plon, alat, alon)

    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0, min(1, t))

    closest_lon = (ax + t * dx) / cos_lat
    closest_lat = ay + t * dy

    return haversine_m(plat, plon, closest_lat, closest_lon)


def parse_trail_color(tags):
    """Extract trail color from OSM tags."""
    # Check osmc:symbol first (e.g., "red:white:red_bar")
    osmc = tags.get("osmc:symbol", "")
    if osmc:
        color = osmc.split(":")[0].lower()
        if color in ("red", "blue", "green", "yellow"):
            return color

    # Check colour tag
    colour = tags.get("colour", "").lower()
    if colour in ("red", "blue", "green", "yellow"):
        return colour

    # Check color tag (American spelling)
    color = tags.get("color", "").lower()
    if color in ("red", "blue", "green", "yellow"):
        return color

    return ""


def query_overpass(cache_file):
    """Query Overpass API or load from cache."""
    if cache_file and os.path.exists(cache_file):
        print(f"Loading cached Overpass data from {cache_file}...")
        with open(cache_file, "r") as f:
            return json.load(f)

    print("Querying Overpass API for hiking routes in Slovakia...")
    print("(This may take 1-3 minutes...)")

    resp = requests.post(
        OVERPASS_URL,
        data={"data": OVERPASS_QUERY},
        headers={"User-Agent": "sota-om-summits trail enrichment"},
        timeout=360,
    )
    resp.raise_for_status()
    data = resp.json()

    print(f"Received {len(data['elements'])} elements")

    if cache_file:
        print(f"Caching to {cache_file}...")
        with open(cache_file, "w") as f:
            json.dump(data, f)

    return data


def build_trail_segments(data):
    """
    Parse Overpass response into trail segments.
    Returns list of (relation_id, name, color, [(lat, lon), ...]) for each way in each relation.
    """
    # Index nodes by ID
    nodes = {}
    for el in data["elements"]:
        if el["type"] == "node":
            nodes[el["id"]] = (el["lat"], el["lon"])

    # Index ways by ID
    ways = {}
    for el in data["elements"]:
        if el["type"] == "way":
            coords = []
            for nid in el.get("nodes", []):
                if nid in nodes:
                    coords.append(nodes[nid])
            if len(coords) >= 2:
                ways[el["id"]] = coords

    # Build trail segments from relations
    trails = []
    rel_count = 0
    for el in data["elements"]:
        if el["type"] != "relation":
            continue
        tags = el.get("tags", {})
        if tags.get("route") != "hiking":
            continue

        rel_id = el["id"]
        name = tags.get("name", "") or tags.get("ref", "")
        color = parse_trail_color(tags)
        rel_count += 1

        for member in el.get("members", []):
            if member["type"] == "way" and member.get("role", "") in ("", "forward", "backward"):
                wid = member["ref"]
                if wid in ways:
                    trails.append((rel_id, name, color, ways[wid]))

    print(f"Found {rel_count} hiking route relations, {len(trails)} trail way segments")
    return trails


def load_summits(summits_path):
    """Load summit data from summits.json."""
    with open(summits_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    summits = data["summits"]
    print(f"Loaded {len(summits)} summits from {summits_path}")
    return data, summits


def find_nearest_trails(summits, trails):
    """For each summit, find the nearest trail within SEARCH_RADIUS_M."""
    results = {}
    total = len(summits)

    # Pre-filter: build a rough bounding box index for trail segments
    # to avoid checking every segment for every summit
    print(f"Computing nearest trail for {total} summits (radius: {SEARCH_RADIUS_M}m)...")

    for idx, summit in enumerate(summits):
        code = summit["c"]
        slat, slon = summit["la"], summit["lo"]

        best_dist = float("inf")
        best_rel_id = None
        best_name = ""
        best_color = ""

        # Rough degree radius for pre-filtering (~500m ≈ 0.0045°)
        deg_radius = SEARCH_RADIUS_M / 111000.0 * 1.5  # with margin

        for rel_id, name, color, coords in trails:
            # Quick bounding box check on the way
            lats = [c[0] for c in coords]
            lons = [c[1] for c in coords]
            if (min(lats) - deg_radius > slat or max(lats) + deg_radius < slat or
                    min(lons) - deg_radius > slon or max(lons) + deg_radius < slon):
                continue

            # Check each segment in this way
            for j in range(len(coords) - 1):
                d = point_to_segment_distance_m(
                    slat, slon,
                    coords[j][0], coords[j][1],
                    coords[j + 1][0], coords[j + 1][1],
                )
                if d < best_dist:
                    best_dist = d
                    best_rel_id = rel_id
                    best_name = name
                    best_color = color

        if best_dist <= SEARCH_RADIUS_M:
            dist_rounded = round(best_dist)
            results[code] = {
                "tr": dist_rounded,
                "tn": best_name,
                "tc": best_color,
                "ti": best_rel_id,
            }

        if (idx + 1) % 50 == 0 or idx == total - 1:
            print(f"  Processed {idx + 1}/{total} summits, {len(results)} with trails so far")

    return results


def merge_into_summits(data, summits, results, summits_path):
    """Merge trail data into summit records in summits.json."""
    merged = 0
    cleared = 0
    for s in summits:
        code = s["c"]
        if code in results:
            r = results[code]
            s["tr"] = r["tr"]
            if r["tn"]:
                s["tn"] = r["tn"]
            elif "tn" in s:
                del s["tn"]
            if r["tc"]:
                s["tc"] = r["tc"]
            elif "tc" in s:
                del s["tc"]
            s["ti"] = r["ti"]
            merged += 1
        else:
            # Remove stale trail fields if summit no longer has a nearby trail
            had = any(k in s for k in ("tr", "tn", "tc", "ti"))
            for key in ("tr", "tn", "tc", "ti"):
                s.pop(key, None)
            if had:
                cleared += 1

    with open(summits_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Merged trail data for {merged} summits into {summits_path}")
    if cleared:
        print(f"Cleared stale trail fields from {cleared} summits")


def main():
    parser = argparse.ArgumentParser(description="Enrich SOTA summits with hiking trail data")
    parser.add_argument("--cache", default="scripts/trails_cache.json",
                        help="Cache file for Overpass response")
    parser.add_argument("--merge", action="store_true",
                        help="Merge results into summits.json")
    args = parser.parse_args()

    # Resolve paths relative to repo root
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    summits_path = os.path.join(repo_root, "summits.json")
    cache_path = os.path.join(repo_root, args.cache) if args.cache else None
    output_path = os.path.join(repo_root, "scripts", "trail_enrichment.json")

    # Step 1: Load summits
    summits_data, summits = load_summits(summits_path)

    # Step 2: Get Overpass data
    overpass_data = query_overpass(cache_path)

    # Step 3: Build trail segments
    trails = build_trail_segments(overpass_data)

    # Step 4: Find nearest trails
    results = find_nearest_trails(summits, trails)

    # Step 5: Output results
    print(f"\n=== RESULTS ===")
    print(f"Summits with trail within {SEARCH_RADIUS_M}m: {len(results)} / {len(summits)}")

    # Summary stats
    on_trail = sum(1 for r in results.values() if r["tr"] <= 25)
    near_trail = sum(1 for r in results.values() if 25 < r["tr"] <= 200)
    far_trail = sum(1 for r in results.values() if r["tr"] > 200)
    print(f"  On trail (≤25m):     {on_trail}")
    print(f"  Near trail (≤200m):  {near_trail}")
    print(f"  Nearby (200-500m):   {far_trail}")

    # Show some interesting findings for verification
    print(f"\n=== NOTABLE SUMMITS ===")
    for code in ["OM/BB-001", "OM/PO-001", "OM/ZA-014", "OM/ZA-017", "OM/BA-001"]:
        if code in results:
            r = results[code]
            print(f"  {code}: {r['tr']}m to '{r['tn']}' ({r['tc']})")
        else:
            print(f"  {code}: NO trail within {SEARCH_RADIUS_M}m")

    # Save enrichment JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nSaved enrichment data to {output_path}")

    # Step 6: Optionally merge into summits.json
    if args.merge:
        merge_into_summits(summits_data, summits, results, summits_path)

    return results


if __name__ == "__main__":
    main()
