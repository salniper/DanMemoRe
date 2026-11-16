#!/usr/bin/env python3
"""Stage 33 APK-authenticated game assets plus 7 exact-repaired phase manifests.

This intentionally does NOT make the 2024 archive importable: 12 mismatched
assets remain unverified. All assets come from the user's own local APK and
contents; no proprietary files are embedded or written to the repository.

Default: dry-run. --apply creates a new, separate overlay folder. It never
writes to extracted contents, existing overlay folders, or the source APK.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
from zipfile import ZipFile

from recover_legacy_apk_assets import (
    KNOWN_APK_SHA256, check_manifest, digest, load_targets, md5,
)
from repair_verified_phase_manifests import REPAIRS, verified_repair

EXPECTED_MISMATCH_COUNT = 19


def _source_file(contents: Path, relative: str) -> Path:
    path = contents
    for part in Path(relative).parts:
        if part in ("", ".", ".."):
            raise ValueError(f"unsafe source file: {relative}")
        path = path / part
        if path.is_symlink():
            raise ValueError(f"source symlink refused: {relative}")
    if not path.is_file():
        raise ValueError(f"source file missing: {relative}")
    if not path.resolve(strict=True).is_relative_to(contents):
        raise ValueError(f"source escapes root: {relative}")
    return path


def prepare(apk: Path, audit: Path, contents: Path, output_dir: Path,
            apply: bool = False) -> dict:
    root = contents.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("contents root is not a directory")
    out = output_dir.resolve(strict=False)
    if out == root or out.is_relative_to(root) or root.is_relative_to(out):
        raise ValueError("overlay must be separate from source contents")
    if out.exists() or output_dir.is_symlink():
        raise ValueError("overlay output already exists; refusing to overwrite")
    if not out.parent.is_dir():
        raise ValueError("overlay parent directory does not exist")

    if digest(apk) != KNOWN_APK_SHA256:
        raise ValueError("original EU APK SHA-256 mismatch")
    targets = load_targets(audit)
    check_manifest(root, targets)
    audit_data = json.loads(audit.read_text(encoding="utf-8"))
    mismatches = {
        item["path"]: item
        for item in audit_data["issues"] if item["status"] == "unverified_bytes"
    }
    if len(mismatches) != EXPECTED_MISMATCH_COUNT:
        raise ValueError("expected exactly 19 unverified original entries")

    prepared = {}
    for name, spec in REPAIRS.items():
        item = mismatches.get(name)
        if (not item or item["reference_md5"] != spec["reference_md5"]
                or item["reference_size"] != spec["size"]):
            raise ValueError(f"phase repair not consistent with audit: {name}")
        raw = _source_file(root, name).read_bytes()
        if md5(raw) != item["actual_md5"]:
            raise ValueError(f"phase file changed since audit: {name}")
        prepared[name] = verified_repair(name, raw, spec)

    with ZipFile(apk) as archive:
        available = set(archive.namelist())
        for name, (size, expected_md5) in targets.items():
            existing = root / name
            if existing.is_symlink():
                raise ValueError(f"source symlink refused: {name}")
            if existing.exists():
                raw_existing = _source_file(root, name).read_bytes()
                if len(raw_existing) != size or md5(raw_existing) != expected_md5:
                    raise ValueError(f"unexpected source file at absent target: {name}")
            relative = name.removeprefix("1/")
            options = (f"assets/common/{relative}", f"assets/{relative}")
            matches = []
            for option in options:
                if option in available:
                    data = archive.read(option)
                    if len(data) == size and md5(data) == expected_md5:
                        matches.append(data)
            if len(matches) != 1:
                raise ValueError(f"EU APK lacks one unique verified copy: {name}")
            prepared[name] = matches[0]

    expected_overlay_count = len(targets) + len(REPAIRS)
    remaining_unverified = EXPECTED_MISMATCH_COUNT - len(REPAIRS)
    if remaining_unverified < 0 or len(prepared) != expected_overlay_count:
        raise ValueError(f"overlay should contain {expected_overlay_count} verified assets, found {len(prepared)}")
    report = {
        "verdict": "PARTIAL_OVERLAY_ONLY_NOT_IMPORTABLE",
        "verified_original_apk_assets": len(targets),
        "verified_repaired_phase_manifests": len(REPAIRS),
        "remaining_unverified_mismatches": remaining_unverified,
        "prepared_files": sorted(prepared),
        "output": str(out),
        "applied": False,
    }
    if not apply:
        return report

    out.mkdir(exist_ok=False)
    try:
        for name, data in prepared.items():
            path = out / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as handle:
                handle.write(data)
            if hashlib.sha256(path.read_bytes()).digest() != hashlib.sha256(data).digest():
                raise ValueError(f"overlay copy verification failed: {name}")
    except BaseException:
        shutil.rmtree(out)
        raise

    report["applied"] = True
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apk", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--contents", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--apply", action="store_true",
                        help="create NEW separate overlay with SHA/MD5 verified files")
    args = parser.parse_args()
    print(json.dumps(
        prepare(args.apk, args.audit, args.contents, args.output_dir, args.apply),
        indent=2, ensure_ascii=False,
    ))


if __name__ == "__main__":
    main()
