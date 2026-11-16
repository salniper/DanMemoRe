#!/usr/bin/env python3
"""Read-only provenance scan for the 33 missing Phase-1 bootstrap resources.

This does NOT extract or distribute copyrighted APK resource bytes, nor make
the original archive importable. The original EU 15.1.0 XAPK is authenticated
by independent pinned archive SHA1 + ARM64 native SHA256 before checking
only safe ZIP members in nested APKs against reference size + MD5.

An exact digest at a different location is only a candidate, never auto-import.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
from io import BytesIO
import json
from pathlib import Path, PurePosixPath
import stat
import zipfile

from verify_pristine_arm64_xapk import inspect_xapk, MAX_SPLIT_SIZE

MAX_APKS = 48
MAX_TARGET_SIZE = 4 * 1024 * 1024
MAX_HITS = 4000
MAX_LOCATIONS = 8


def load_index(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("format") != "DANMEMORE_LEGACY_BOOTSTRAP_33_REFERENCE_V1":
        raise ValueError("unexpected original-bootstrap reference index")
    entries = data.get("targets")
    if not isinstance(entries, list) or len(entries) != 33:
        raise ValueError("expected exactly 33 original bootstrap targets")
    found = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("invalid original reference target")
        name, size, md5 = entry.get("path"), entry.get("size"), entry.get("md5")
        if (not isinstance(name, str) or not name.startswith("1/files/")
                or "\\" in name or ".." in PurePosixPath(name).parts
                or name in found or not isinstance(size, int)
                or isinstance(size, bool) or not 0 < size < MAX_TARGET_SIZE
                or not isinstance(md5, str) or len(md5) != 32
                or any(x not in "0123456789abcdef" for x in md5)):
            raise ValueError("unsafe or duplicate bootstrap reference")
        found.add(name)
    return entries


def member_safe(info: zipfile.ZipInfo) -> bool:
    name = info.filename
    parts = PurePosixPath(name).parts
    return (not info.is_dir() and not name.startswith("/")
            and "\\" not in name and ".." not in parts
            and not stat.S_ISLNK(info.external_attr >> 16))


def scan_original_xapk_members(xapk: Path, targets: list[dict]) -> dict:
    by_basename = defaultdict(list)
    result = {}
    for entry in targets:
        path = entry["path"]
        by_basename[PurePosixPath(path).name].append(entry)
        result[path] = {
            "target": path,
            "expected_size": entry["size"],
            "expected_md5": entry["md5"],
            "same_basename_entries": 0,
            "wrong_size_entries": 0,
            "same_size_wrong_md5_entries": 0,
            "exact_md5_at_expected_apk_path": [],
            "exact_md5_at_alternate_apk_path": [],
        }
    nested_count = 0
    with zipfile.ZipFile(xapk) as bundle:
        apk_infos = [i for i in bundle.infolist()
                     if member_safe(i) and i.filename.lower().endswith(".apk")]
        if not apk_infos or len(apk_infos) > MAX_APKS:
            raise ValueError("unexpected number of nested original APKs")
        for apk_info in apk_infos:
            if not 0 < apk_info.file_size <= MAX_SPLIT_SIZE:
                raise ValueError("nested APK outside size bound")
            with bundle.open(apk_info) as source:
                blob = source.read(MAX_SPLIT_SIZE + 1)
            if len(blob) != apk_info.file_size:
                raise ValueError("invalid nested APK source length")
            with zipfile.ZipFile(BytesIO(blob)) as apk:
                for info in apk.infolist():
                    if not member_safe(info):
                        continue
                    relevant = by_basename.get(PurePosixPath(info.filename).name, ())
                    if not relevant:
                        continue
                    max_needed = max(x["size"] for x in relevant)
                    candidate_size = info.file_size
                    candidate = None
                    if candidate_size in {x["size"] for x in relevant}:
                        if not 0 < candidate_size <= MAX_TARGET_SIZE:
                            raise ValueError("oversized matching original resource")
                        with apk.open(info) as stream:
                            candidate = stream.read(candidate_size + 1)
                        if len(candidate) != candidate_size:
                            raise ValueError("nested APK member size mismatch")
                        candidate_md5 = hashlib.md5(candidate).hexdigest()
                    for target in relevant:
                        row = result[target["path"]]
                        row["same_basename_entries"] += 1
                        if row["same_basename_entries"] > MAX_HITS:
                            raise ValueError("too many matching basename entries")
                        if candidate_size != target["size"]:
                            row["wrong_size_entries"] += 1
                            continue
                        if candidate_md5 != target["md5"]:
                            row["same_size_wrong_md5_entries"] += 1
                            continue
                        target_relative = target["path"][2:]
                        recognized = {
                            "assets/common/" + target_relative,
                            "assets/" + target_relative,
                        }
                        key = ("exact_md5_at_expected_apk_path"
                               if info.filename in recognized
                               else "exact_md5_at_alternate_apk_path")
                        if len(row[key]) < MAX_LOCATIONS:
                            row[key].append({
                                "apk": apk_info.filename,
                                "zip_member_path": info.filename,
                            })
            nested_count += 1
    return {
        "status": "ORIGINAL_XAPK_BOOTSTRAP_FINGERPRINT_SCAN_NOT_RECOVERY",
        "verified_reference_index_count": len(targets),
        "nested_apks_scanned": nested_count,
        "expected_path_exact_count": sum(
            bool(row["exact_md5_at_expected_apk_path"]) for row in result.values()),
        "alternate_path_exact_count": sum(
            bool(row["exact_md5_at_alternate_apk_path"]) for row in result.values()),
        "any_md5_exact_count": sum(
            bool(row["exact_md5_at_expected_apk_path"] or
                 row["exact_md5_at_alternate_apk_path"])
            for row in result.values()),
        "targets": result,
        "original_asset_bytes_written": False,
        "original_import_authorized": False,
        "limitations": (
            "Only ordinary uncompressed/decompressed nested APK ZIP members "
            "matching the requested basenames were checked. A missing match "
            "does not exclude encrypted resources, asset databases, remote "
            "content, OBBs or other independently pinned 2023 APK versions. "
            "Matches at alternate paths require independent provenance checks."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xapk", required=True, type=Path)
    parser.add_argument("--index", required=True, type=Path)
    args = parser.parse_args()
    authenticated = inspect_xapk(args.xapk)
    targets = load_index(args.index)
    report = scan_original_xapk_members(args.xapk, targets)
    report["original_xapk_sha1"] = authenticated["source_archive_sha1"]
    report["original_arm64_native_sha256"] = authenticated["native_sha256"]
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
