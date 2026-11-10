"""Search the local remote-source catalog without making network requests."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
DATABASE = ROOT / "resources/fish-database"


def search(query: str, kind: str = "all", source: str = "", license_code: str = "") -> list[dict]:
    manifest = json.loads((DATABASE / "manifest.json").read_text(encoding="utf-8"))
    index = manifest["remote_3d_sources"]
    paths = []
    if kind in ("all", "source"):
        paths.append(index["platform_catalog"])
    if kind in ("all", "model"):
        paths.extend(index["model_catalogs"])
    terms = query.casefold().split()
    matches = []
    for relative in paths:
        path = (DATABASE / relative).resolve()
        if not path.is_relative_to(DATABASE.resolve()):
            raise ValueError(f"Catalog outside database: {relative}")
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if source and source.casefold() not in record["source_id"].casefold():
                continue
            if license_code and record.get("license_code") != license_code:
                continue
            # Search explicit discovery fields. Do not turn license restrictions,
            # URL strings or negative coverage notes into positive animal hits.
            searchable = " ".join(str(record.get(key, "")) for key in (
                "title", "scientific_name_label", "keywords", "groups", "coverage"
            )).casefold()
            if all(term in searchable for term in terms):
                matches.append(record)
    return matches


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", default="", help="Chinese/English keywords or scientific name; terms are ANDed")
    parser.add_argument("--kind", choices=("all", "source", "model"), default="all")
    parser.add_argument("--source", default="", help="Source ID fragment, for example ffishasia")
    parser.add_argument("--license", dest="license_code", choices=("cc0", "cc_by", "cc_by_sa", "cc_by_nc", "cc_by_nc_sa", "other", "unknown", "mixed"))
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be positive")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        records = search(args.query, args.kind, args.source, args.license_code or "")
    except (OSError, ValueError, KeyError) as exc:
        if args.json:
            print(json.dumps({"ok": False, "status": "failed", "failures": [str(exc)]}, ensure_ascii=False))
        else:
            print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
    result = {"ok": True, "status": "done", "query": args.query,
              "matched_count": len(records), "returned_count": min(len(records), args.limit),
              "network_requests": 0, "model_downloads": 0,
              "scope": "Remote metadata only; a hit is not a downloaded/validated model or commercial approval.",
              "records": records[:args.limit]}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{len(records)} matches; remote metadata only; no network requests")
        for record in records[:args.limit]:
            print(f"[{record['source_id']}] {record['title']}")
            print(f"  {record['url']} | {record['license_code']} | not downloaded")


if __name__ == "__main__":
    main()
