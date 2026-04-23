#!/usr/bin/env python3
"""Generate neighbor_summits.json from the SOTA summitslist.csv.

Emits a compact JSON of currently-valid summits for SOTA associations
bordering OM (Slovakia): OK, SP, HA, OE, UT. Used by the map UI as an
optional "Nearby SOTA" overlay (2m VHF link range).

Example:
    python scripts/gen_neighbor_summits.py --fetch
    python scripts/gen_neighbor_summits.py --input summitslist.csv
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import io
import json
import sys
from datetime import date, datetime
from pathlib import Path

import aiohttp

SUMMITSLIST_URL = "https://www.sotadata.org.uk/summitslist.csv"
PREFIXES = ("OK", "SP", "HA", "OE", "UT")


def parse_date(s: str) -> date | None:
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


async def fetch_csv(url: str) -> str:
    print(f"Fetching {url} ...", file=sys.stderr)
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as resp:
            resp.raise_for_status()
            raw = await resp.read()
    for enc in ("utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def load_rows(text: str) -> list[dict]:
    lines = text.splitlines()
    if lines and lines[0].lower().startswith("sota summits list"):
        lines = lines[1:]
    reader = csv.DictReader(io.StringIO("\n".join(lines)))
    return list(reader)


def to_record(r: dict) -> dict:
    code = r["SummitCode"].strip()
    assoc = code.split("/", 1)[0]
    try:
        alt_m = int(float(r["AltM"]))
    except (ValueError, KeyError):
        alt_m = 0
    try:
        pts = int(float(r["Points"]))
    except (ValueError, KeyError):
        pts = 0
    try:
        act = int(float(r.get("ActivationCount", "") or 0))
    except ValueError:
        act = 0
    return {
        "c": code,
        "n": r["SummitName"].strip(),
        "la": round(float(r["Latitude"]), 5),
        "lo": round(float(r["Longitude"]), 5),
        "e": alt_m,
        "p": pts,
        "a": act,
        "as": assoc,
    }


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--input", default="summitslist.csv", help="Path to SOTA summitslist.csv"
    )
    ap.add_argument(
        "--output", default="neighbor_summits.json", help="Output JSON path"
    )
    ap.add_argument(
        "--fetch",
        action="store_true",
        help="Download the CSV from sotadata.org.uk (overrides --input)",
    )
    ap.add_argument(
        "--as-of",
        default=None,
        help="Reference date YYYY-MM-DD for validity (default: today)",
    )
    args = ap.parse_args()

    output = Path(args.output)

    if args.as_of:
        try:
            as_of = datetime.strptime(args.as_of, "%Y-%m-%d").date()
        except ValueError:
            print(f"Invalid --as-of: {args.as_of}", file=sys.stderr)
            return 2
    else:
        as_of = date.today()

    if args.fetch or not Path(args.input).exists():
        text = await fetch_csv(SUMMITSLIST_URL)
    else:
        text = Path(args.input).read_text(encoding="utf-8", errors="replace")

    rows = load_rows(text)

    prefix_set = tuple(f"{p}/" for p in PREFIXES)
    matched = [r for r in rows if (r.get("SummitCode") or "").startswith(prefix_set)]
    total = len(matched)

    per_assoc_total: dict[str, int] = {p: 0 for p in PREFIXES}
    per_assoc_kept: dict[str, int] = {p: 0 for p in PREFIXES}
    kept: list[dict] = []
    expired = 0
    not_yet = 0
    for r in matched:
        assoc = (r.get("SummitCode") or "").split("/", 1)[0]
        per_assoc_total[assoc] = per_assoc_total.get(assoc, 0) + 1
        vf = parse_date(r.get("ValidFrom", ""))
        vt = parse_date(r.get("ValidTo", ""))
        if vt is not None and as_of > vt:
            expired += 1
            continue
        if vf is not None and as_of < vf:
            not_yet += 1
            continue
        kept.append(r)
        per_assoc_kept[assoc] = per_assoc_kept.get(assoc, 0) + 1

    kept.sort(key=lambda r: r["SummitCode"])
    records = [to_record(r) for r in kept]

    payload = {
        "_fields": {
            "c": "SOTA summit code",
            "n": "Name",
            "la": "Latitude",
            "lo": "Longitude",
            "e": "Elevation (m)",
            "p": "SOTA points",
            "a": "Activation count",
            "as": "Association prefix",
        },
        "_associations": {
            "OK": "Czechia",
            "SP": "Poland",
            "HA": "Hungary",
            "OE": "Austria",
            "UT": "Ukraine",
        },
        "_generated": as_of.isoformat(),
        "summits": records,
    }

    output.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    breakdown = ", ".join(
        f"{p}={per_assoc_kept[p]}/{per_assoc_total[p]}" for p in PREFIXES
    )
    print(
        f"Neighbors: {total} total -> {expired} expired, {not_yet} not-yet-valid "
        f"-> {len(records)} emitted ({output})",
        file=sys.stderr,
    )
    print(f"Per-association kept/total: {breakdown}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
