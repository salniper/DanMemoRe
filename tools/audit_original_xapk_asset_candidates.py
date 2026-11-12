#!/usr/bin/env python3
"""Check a SHA-verified original EU 15.1.0 XAPK for exact legacy asset candidates.

Only SHA/size/path metadata is returned; game bytes are never written or emitted.
Negative results concern visible ZIP members, NOT bundled Unity asset databases,
runtime downloads, compressed sub-archives, or original server content.
"""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path, PurePosixPath
import stat
import zipfile

from verify_pristine_arm64_xapk import inspect_xapk, MAX_SPLIT_SIZE

# Authoritative current 15.1.0 reference catalog size/MD5 for 12 blocked assets.
# These are expected public-content fingerprints; NOT user-provided actual bytes.
REFERENCE = {
    "1/files/font/number.png": (7381, "dbb56ed73f24fa93d17aadbac316732e"),
    "1/master/divide_enc/adventureMission.enc": (3264, "fdbf79b512f1240282f829036a373181"),
    "1/master/divide_enc/downloadVoicePhase.enc": (480, "35dd590aaa510290f3287404b9dc137d"),
    "1/master/divide_enc/lotteryWeightGroup.enc": (1824, "a8ce9c3529fc6c502cc6ffb8e141a58b"),
    "1/master/divide_enc/subscription.enc": (8272, "a8e7106d12d687f7a6f4bc82448fed59"),
    "1/master/divide_novel_command_enc/novelCommand751040548.enc":
        (8464, "f2bba2336a28c37728253e54407e80f8"),
    "1/master/divide_novel_command_enc/novelCommand751040550.enc":
        (17376, "72c522229ce23165df33f896c7c30fa9"),
    "1/master/divide_novel_command_enc/novelCommand751040806.enc":
        (7632, "beaec5d485d0515d0085cc620cc0e45e"),
    "1/master/divide_novel_command_enc/novelCommand751040815.enc":
        (17600, "eb767c085ff9c1d8f2fbee6cbe8168a5"),
    "1/master/divide_novel_command_enc/novelCommand751041273.enc":
        (8464, "af65edc37e2ae9fecaa41da96b7f9fa9"),
    "1/master/divide_novel_command_enc/novelCommand751041275.enc":
        (17376, "f2d12bbee005788a3cd61f8cf022e69a"),
    "3/files/ui_atlas/home_gacha/gacha_top_move_parts_text.json":
        (4267, "4896a18db1be1b85eb581d039701681a"),
}
MAX_APK_MEMBERS = 48
MAX_BASENAME_HITS = 4096
MAX_RESULT_SAMPLES = 12
MAX_CANDIDATE_BYTES = 32 * 1024 * 1024


def member_path_safe(info: zipfile.ZipInfo) -> bool:
    value = PurePosixPath(info.filename)
    return (
        not info.is_dir()
        and not stat.S_ISLNK(info.external_attr >> 16)
        and not info.filename.startswith("/")
        and "\\" not in info.filename
        and ".." not in value.parts
    )


def audit_member(blob: bytes, package: str, details: dict):
    with zipfile.ZipFile(BytesIO(blob)) as apk:
        for info in apk.infolist():
            if not member_path_safe(info):
                continue
            # Check exact final names as candidates; placement may differ by split.
            name = PurePosixPath(info.filename).name
            relevant = [(target, expected) for target, expected in REFERENCE.items()
                        if name == PurePosixPath(target).name]
            if not relevant:
                continue
            for target, (expected_size, expected_md5) in relevant:
                row = details[target]
                row["basename_occurrences"] += 1
                if row["basename_occurrences"] > MAX_BASENAME_HITS:
                    raise ValueError("too many repeated candidate filenames")
                if info.file_size != expected_size:
                    row["wrong_size_occurrences"] += 1
                    continue
                if not 0 < info.file_size <= MAX_CANDIDATE_BYTES:
                    raise ValueError("unexpected oversized candidate")
                with apk.open(info) as reader:
                    candidate = reader.read(expected_size + 1)
                if len(candidate) != expected_size:
                    raise ValueError("candidate decompressed size mismatch")
                digest = hashlib.md5(candidate).hexdigest()
                if digest == expected_md5:
                    row["reference_exact_occurrences"] += 1
                    if len(row["reference_exact_locations"]) < MAX_RESULT_SAMPLES:
                        row["reference_exact_locations"].append({
                            "apk": package, "entry": info.filename
                        })
                else:
                    row["same_size_nonmatching_occurrences"] += 1


def scan_members(path: Path) -> dict:
    details = {
        target: {
            "reference_size": expected_size,
            "reference_md5": expected_md5,
            "basename_occurrences": 0,
            "wrong_size_occurrences": 0,
            "same_size_nonmatching_occurrences": 0,
            "reference_exact_occurrences": 0,
            "reference_exact_locations": [],
        } for target, (expected_size, expected_md5) in REFERENCE.items()
    }
    nested = []
    with zipfile.ZipFile(path) as outer:
        candidates = [entry for entry in outer.infolist()
                      if member_path_safe(entry) and entry.filename.endswith(".apk")]
        if not candidates or len(candidates) > MAX_APK_MEMBERS:
            raise ValueError("unknown XAPK nested APK count")
        for item in candidates:
            if not 0 < item.file_size <= MAX_SPLIT_SIZE:
                raise ValueError("nested APK exceeds safety bound")
            with outer.open(item) as reader:
                apk = reader.read(MAX_SPLIT_SIZE + 1)
            if len(apk) != item.file_size:
                raise ValueError("invalid nested APK contents")
            audit_member(apk, item.filename, details)
            nested.append(item.filename)
    return {
        "status": "ZIP_MEMBER_PROVENANCE_ONLY_NOT_IMPORT_AUTHORIZATION",
        "nested_apk_count": len(nested),
        "checked_apks": nested,
        "reference_exact_target_count": sum(bool(row["reference_exact_occurrences"])
                                            for row in details.values()),
        "targets": details,
        "limitations": (
            "Matches establish candidate bytes in verified original XAPK ZIP entries only; "
            "path mapping and source entitlement must still be checked before any use. "
            "No match does not exclude assets in other data containers or remote caches."
        ),
        "legacy_import_authorized": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xapk", required=True, type=Path)
    args = parser.parse_args()
    # Mandatory independently pinned archive AND nested native hash verification.
    source = inspect_xapk(args.xapk)
    result = scan_members(args.xapk)
    result["authenticated_original_native_sha256"] = source["native_sha256"]
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
