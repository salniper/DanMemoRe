#!/usr/bin/env python3
"""Read-only provenance lookup for names and hashes in exported DanMemoRe master.

Only the compact sources object near the start of the large JSON is parsed.
No gameplay records, decryption keys, or proprietary source bytes are printed.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

DEFAULT_NAMES = ("adventureMission", "downloadVoicePhase", "lotteryWeightGroup", "subscription")
MAX_PREFIX_BYTES = 1024 * 1024


def load_sources(master_path: Path) -> dict:
    with master_path.open("rb") as handle:
        prefix = handle.read(MAX_PREFIX_BYTES)
    match = re.search(rb'"sources"\s*:\s*', prefix)
    if match is None:
        raise ValueError("no exported sources field within first 1 MiB")
    try:
        sources, _ = json.JSONDecoder().raw_decode(
            prefix[match.end():].decode("utf-8", errors="ignore").lstrip()
        )
    except (UnicodeError, ValueError) as exc:
        raise ValueError("incomplete or malformed sources object") from exc
    if not isinstance(sources, dict):
        raise ValueError("exported sources is not an object")
    return sources


def report(master_path: Path, names=DEFAULT_NAMES) -> dict:
    sources = load_sources(master_path)
    result = []
    for name in names:
        item = sources.get(name)
        if item is None:
            result.append({"name": name, "status": "NOT_IN_MASTER_EXPORT"})
            continue
        if not isinstance(item, dict):
            raise ValueError(f"malformed master source: {name}")
        sha = item.get("sha256")
        source_path = item.get("path")
        count = item.get("rows")
        if not (isinstance(sha, str) and len(sha) == 64 and
                all(x in "0123456789abcdef" for x in sha) and
                isinstance(source_path, str) and
                source_path == f"1/master/divide_enc/{name}.enc" and
                isinstance(count, int) and count >= 0):
            raise ValueError(f"invalid source metadata: {name}")
        result.append({"name": name, "status": "DECODED_IN_MASTER_EXPORT",
                       "source_sha256": sha, "rows": count})
    return {"checked": len(result), "total_export_sources": len(sources), "results": result,
            "warning": "A source hash links exported data to exact input bytes, not necessarily to launcher-version compatibility."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path, required=True)
    parser.add_argument("--names", nargs="*", default=list(DEFAULT_NAMES))
    args = parser.parse_args()
    print(json.dumps(report(args.master, args.names), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
