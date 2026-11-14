#!/usr/bin/env python3
"""Read-only owner archive check for 1,544 Phase-3 gacha background references.

Reference-only catalog entries do not prove physical bytes are missing.
Use the exact owner's preserved audit JSON and a separately supplied
contents root to check each file's *actual* size and MD5. The source
folder is never changed and no image payloads are printed/exported.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

REFERENCE_COUNT = 1544
PREFIX = "3/files/lottery/background/"
MAX_FILE_SIZE = 8 * 1024 * 1024
MAX_SAMPLES = 24
MD5 = re.compile(r"^[0-9a-f]{32}$")


def load_reference(audit: Path):
    data = json.loads(audit.read_text(encoding="utf-8"))
    matches = [i for i in data.get("issues", []) if
               i.get("status") == "missing_from_historical_catalog"]
    if len(matches) != REFERENCE_COUNT:
        raise ValueError("audit must contain exactly 1544 reference-only entries")
    seen = set()
    for entry in matches:
        path = entry.get("path")
        size = entry.get("reference_size")
        md5 = entry.get("reference_md5")
        if (entry.get("phase") != 3 or not isinstance(path, str)
            or not path.startswith(PREFIX) or
            not re.fullmatch(r"3/files/lottery/background/[0-9]+\.png", path)
            or path in seen or not isinstance(size, int)
            or isinstance(size, bool) or not 0 < size <= MAX_FILE_SIZE
            or not isinstance(md5, str) or not MD5.fullmatch(md5)):
            raise ValueError("unsafe or inconsistent reference-only lottery entry")
        seen.add(path)
    return matches


def _safe_file(root: Path, relative: str):
    target = root
    parts = relative.split("/")
    if any(x in ("", ".", "..") for x in parts):
        raise ValueError("unsafe audit filename")
    for part in parts:
        target = target / part
        if target.is_symlink():
            return None, "SYMLINK_PATH_REFUSED"
    if not target.exists():
        return None, "NOT_PRESENT_AT_REFERENCE_PATH"
    if not target.is_file():
        return None, "NOT_REGULAR_FILE"
    return target, None


def audit_phase3_files(audit: Path, contents: Path) -> dict:
    reference = load_reference(audit)
    root = contents.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("owner contents root must be a directory")
    if contents.is_symlink():
        raise ValueError("symlinked contents root refused")
    summary = {
        "REFERENCE_EXACT_ON_DISK": 0,
        "NOT_PRESENT_AT_REFERENCE_PATH": 0,
        "REFERENCE_SIZE_MISMATCH": 0,
        "REFERENCE_MD5_MISMATCH": 0,
        "SYMLINK_PATH_REFUSED": 0,
        "NOT_REGULAR_FILE": 0,
        "INACCESSIBLE_FILE": 0,
    }
    samples = {key: [] for key in summary if key != "REFERENCE_EXACT_ON_DISK"}
    for row in reference:
        path = row["path"]
        file, issue = _safe_file(root, path)
        if issue is None:
            try:
                if file.stat().st_size != row["reference_size"]:
                    issue = "REFERENCE_SIZE_MISMATCH"
                else:
                    digest = hashlib.md5()
                    with file.open("rb") as stream:
                        for block in iter(lambda: stream.read(65536), b""):
                            digest.update(block)
                    issue = ("REFERENCE_EXACT_ON_DISK"
                             if digest.hexdigest() == row["reference_md5"]
                             else "REFERENCE_MD5_MISMATCH")
            except (OSError, PermissionError):
                issue = "INACCESSIBLE_FILE"
        summary[issue] += 1
        if issue in samples and len(samples[issue]) < MAX_SAMPLES:
            samples[issue].append(path)
    if sum(summary.values()) != REFERENCE_COUNT:
        raise ValueError("Phase-3 reference count not conserved")
    return {
        "status": "PHASE3_REFERENCE_ONLY_PHYSICAL_READ_ONLY_AUDIT",
        "reference_catalogue_only_count": REFERENCE_COUNT,
        "actual_reference_exact_file_count": summary["REFERENCE_EXACT_ON_DISK"],
        "known_absent_at_reference_path_count":
            summary["NOT_PRESENT_AT_REFERENCE_PATH"],
        "result_counts": summary,
        "diagnostic_path_samples": samples,
        "owner_files_modified": False,
        "game_assets_import_authorized": False,
        "limitations": (
            "A missing expected path does not exclude the same game resource "
            "in a different directory, APK split, OBB or asset pack. "
            "An exact on-disk MD5 proves only that byte sequence, not game "
            "runtime, copyright permission or full archive consistency."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--contents", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit_phase3_files(args.audit, args.contents),
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
