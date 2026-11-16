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


def require_matches(export: dict, requirements: dict[str, str]) -> dict:
    """Fail closed unless each named export records an exact expected source SHA-256.

    A match proves which bytes the committed export used; it does not make
    that file acceptable to the Launcher's separate strict manifest gate.
    """
    found = {r["name"]: r for r in export["results"]}
    for name, expected in requirements.items():
        if name not in DEFAULT_NAMES:
            raise ValueError(f"unsupported required source name: {name}")
        if not isinstance(expected, str) or len(expected) != 64 or any(
            x not in "0123456789abcdef" for x in expected
        ):
            raise ValueError(f"invalid expected SHA-256 for {name}")
        record = found.get(name)
        if record is None or record["status"] != "DECODED_IN_MASTER_EXPORT":
            raise ValueError(f"required source absent from exported gameplay data: {name}")
        if record["source_sha256"] != expected:
            raise ValueError(f"source SHA-256 mismatch: {name}")
    return {"verified_source_names": sorted(requirements),
            "source_byte_match_count": len(requirements),
            "note": "Export provenance verified; launcher reference MD5 is a separate requirement."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path, required=True)
    parser.add_argument("--names", nargs="*", default=list(DEFAULT_NAMES))
    parser.add_argument("--require-source-sha", action="append", default=[],
                        metavar="NAME=SHA256",
                        help="fail unless exported original-source SHA-256 matches exactly")
    args = parser.parse_args()
    requirements = {}
    for pair in args.require_source_sha:
        name, separator, sha = pair.partition("=")
        if not separator or not name or name in requirements:
            parser.error("invalid or duplicate --require-source-sha NAME=SHA256")
        requirements[name] = sha
    result = report(args.master, sorted(set(args.names) | set(requirements)))
    if requirements:
        result["verification"] = require_matches(result, requirements)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
