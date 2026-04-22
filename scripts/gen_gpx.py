#!/usr/bin/env python3
"""Generate a SOTA association GPX file from the SOTA summitslist.csv.

Example:
    python scripts/gen_gpx.py --association Z3 --fetch
    python scripts/gen_gpx.py --association OM --input summitslist.csv
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import io
import sys
import xml.sax.saxutils as sx
from datetime import date, datetime
from pathlib import Path

import aiohttp

SUMMITSLIST_URL = "https://www.sotadata.org.uk/summitslist.csv"


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
    # SOTA csv is latin-1-ish; try utf-8 first, fallback to latin-1
    for enc in ("utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def load_rows(text: str) -> list[dict]:
    # First line is a banner: "SOTA Summits List (Date=DD/MM/YYYY)"
    # Real header starts on line 2.
    lines = text.splitlines()
    if lines and lines[0].lower().startswith("sota summits list"):
        lines = lines[1:]
    reader = csv.DictReader(io.StringIO("\n".join(lines)))
    return list(reader)


def escape(s: str) -> str:
    return sx.escape(s or "", {'"': "&quot;"})


def build_gpx(rows: list[dict], assoc: str) -> str:
    out = io.StringIO()
    out.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    out.write('<gpx xmlns="http://www.topografix.com/GPX/1/1"\n')
    out.write('     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n')
    out.write(
        '     xsi:schemaLocation="http://www.topografix.com/GPX/1/1 '
        'http://www.topografix.com/GPX/1/1/gpx.xsd"\n'
    )
    out.write('     version="1.1"\n')
    out.write('     creator="SOTA-GPX-Converter">\n')
    out.write(f"<name>SOTA_{assoc}</name>\n")

    for r in rows:
        code = r["SummitCode"].strip()
        name = r["SummitName"].strip()
        lat = r["Latitude"].strip()
        lon = r["Longitude"].strip()
        alt_m = r["AltM"].strip()
        alt_ft = r["AltFt"].strip()
        pts = r["Points"].strip()
        assoc_name = r["AssociationName"].strip()
        region = r["RegionName"].strip()
        act_raw = (r.get("ActivationCount") or "").strip()

        try:
            act_n = int(act_raw)
        except ValueError:
            act_n = 0

        desc = f"{assoc_name} | {region} | {alt_m}m / {alt_ft}ft | {pts} pts"
        if act_n > 0:
            desc += f" | {act_n} activations"

        out.write(f'<wpt lat="{lat}" lon="{lon}">\n')
        out.write(f"<ele>{alt_m}.0</ele>\n")
        out.write(f"<name>{escape(code)} {escape(name)}</name>\n")
        out.write(f"<cmt>{escape(code)}</cmt>\n")
        out.write(f"<desc>{escape(desc)}</desc>\n")
        out.write("<sym>Flag, Blue</sym>\n")
        out.write("</wpt>\n")

    out.write("</gpx>\n")
    return out.getvalue()


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--association", required=True, help="SOTA association prefix (e.g. Z3, OM)"
    )
    ap.add_argument(
        "--input", default="summitslist.csv", help="Path to SOTA summitslist.csv"
    )
    ap.add_argument(
        "--output", default=None, help="Output GPX path (default: SOTA_<ASSOC>.gpx)"
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
    ap.add_argument(
        "--include-expired",
        action="store_true",
        help="Do not filter by ValidFrom/ValidTo",
    )
    args = ap.parse_args()

    assoc = args.association.strip().upper()
    output = Path(args.output) if args.output else Path(f"SOTA_{assoc}.gpx")

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

    prefix = f"{assoc}/"
    assoc_rows = [r for r in rows if (r.get("SummitCode") or "").startswith(prefix)]
    total = len(assoc_rows)

    expired = 0
    not_yet = 0
    bad_dates = 0
    kept: list[dict] = []
    for r in assoc_rows:
        if args.include_expired:
            kept.append(r)
            continue
        vf = parse_date(r.get("ValidFrom", ""))
        vt = parse_date(r.get("ValidTo", ""))
        if vf is None and vt is None:
            bad_dates += 1
            kept.append(r)  # fail-open
            continue
        if vt is not None and as_of > vt:
            expired += 1
            continue
        if vf is not None and as_of < vf:
            not_yet += 1
            continue
        kept.append(r)

    kept.sort(key=lambda r: r["SummitCode"])

    gpx = build_gpx(kept, assoc)
    output.write_text(gpx, encoding="utf-8")

    print(
        f"{assoc}: {total} total -> {expired} expired, {not_yet} not-yet-valid"
        f"{', ' + str(bad_dates) + ' bad-dates' if bad_dates else ''}"
        f" -> {len(kept)} emitted ({output})",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
