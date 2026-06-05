"""Split the big SOTA summitslist.csv into one CSV per association.

Each summit's association is the prefix of its SummitCode (the part before the
first "/", e.g. "OM/BA-001" -> "OM"). Output files are written to the
summitslist/ folder, one per association, each keeping the banner + header.

A checksum of the source CSV is stored in summitslist/manifest.json. If the
source is unchanged since the last run the split is skipped (use --force to
regenerate anyway). This lets the Claude web chat cheaply tell whether the
per-association files are still in sync with the big list.

Example:
    python scripts/split_summitslist.py
    python scripts/split_summitslist.py --input summitslist.csv --force
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def fix_mojibake(text: str) -> str:
    """Repair UTF-8 text that was mis-decoded as Latin-1 and re-saved as UTF-8.

    Signature of the damage: "ý" (U+00FD, bytes C3 BD) shows up as "Ã½". The
    cure is to re-encode as Latin-1 and decode as UTF-8. Only applied when the
    mojibake markers ("Ã"/"Â") are present and the round-trip succeeds, so clean
    text is left untouched.
    """
    if "Ã" not in text and "Â" not in text:
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except UnicodeError:
        out = []
        for ln in text.splitlines():
            try:
                out.append(ln.encode("latin-1").decode("utf-8"))
            except UnicodeError:
                out.append(ln)
        return "\n".join(out)


def split_lines(text: str) -> tuple[str | None, str, list[str]]:
    """Return (banner, header, data_lines) from the raw CSV text.

    The first line is a banner ("SOTA Summits List (Date=DD/MM/YYYY)"); the
    real header is on line 2. Some lists ship without a banner, so handle both.
    """
    lines = text.splitlines()
    banner = None
    if lines and lines[0].lower().startswith("sota summits list"):
        banner = lines[0]
        lines = lines[1:]
    if not lines:
        raise SystemExit("error: no header/data rows found in input")
    header = lines[0]
    data = [ln for ln in lines[1:] if ln.strip()]
    return banner, header, data


def association_of(row: str) -> str | None:
    code = row.split(",", 1)[0].strip()
    if "/" not in code:
        return None
    return code.split("/", 1)[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="summitslist.csv", help="source CSV (default: summitslist.csv)")
    parser.add_argument("--outdir", default="summitslist", help="output folder (default: summitslist)")
    parser.add_argument("--force", action="store_true", help="regenerate even if the checksum is unchanged")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    src = (repo_root / args.input) if not Path(args.input).is_absolute() else Path(args.input)
    outdir = (repo_root / args.outdir) if not Path(args.outdir).is_absolute() else Path(args.outdir)

    if not src.exists():
        raise SystemExit(f"error: input not found: {src}")

    checksum = sha256_of(src)
    manifest_path = outdir / "manifest.json"

    if manifest_path.exists() and not args.force:
        try:
            prev = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            prev = {}
        if prev.get("checksum") == checksum:
            print(f"unchanged (sha256={checksum[:12]}…), skipping. Use --force to regenerate.")
            return 0

    text = src.read_text(encoding="utf-8")
    fixed = fix_mojibake(text)
    if fixed != text:
        src.write_text(fixed, encoding="utf-8")
        checksum = sha256_of(src)
        print(f"repaired mojibake in {src.name} (re-checksummed)")
        text = fixed
    banner, header, data = split_lines(text)

    buckets: dict[str, list[str]] = {}
    skipped = 0
    for row in data:
        assoc = association_of(row)
        if assoc is None:
            skipped += 1
            continue
        buckets.setdefault(assoc, []).append(row)

    outdir.mkdir(parents=True, exist_ok=True)
    # Clear stale per-association files so removed associations don't linger.
    for old in outdir.glob("*.csv"):
        old.unlink()

    associations: dict[str, dict] = {}
    for assoc in sorted(buckets):
        rows = buckets[assoc]
        out_path = outdir / f"{assoc}.csv"
        lines = ([banner] if banner else []) + [header] + rows
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        associations[assoc] = {"file": out_path.name, "count": len(rows)}

    manifest = {
        "source": args.input,
        "checksum": checksum,
        "algorithm": "sha256",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "banner": banner,
        "total_summits": sum(len(v) for v in buckets.values()),
        "association_count": len(buckets),
        "associations": associations,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"wrote {len(buckets)} association file(s) to {outdir}")
    print(f"  total summits: {manifest['total_summits']}" + (f", skipped {skipped} row(s) without a /code" if skipped else ""))
    print(f"  sha256: {checksum}")
    print(f"  manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
