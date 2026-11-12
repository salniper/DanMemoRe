#!/usr/bin/env python3
"""Verify a pristine EU 15.1.0 ARM64 XAPK, optionally scan native story references.

This only reads a local source archive; never extracts files, patches an APK,
writes proprietary bytes, changes asset-validation policy, or enables import.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile

from inspect_elf_novel_xrefs import PINNED_SHA256, inspect

# Publicly listed original APKPure EU 15.1.0 split variant, versionCode 170316722.
PINNED_XAPK_SHA1 = "37894ddb200914278a5f8780e0c6e3da2d750b7c"
BASE_APK = "com.eu.danmemo.apk"
ARM64_SPLIT = "config.arm64_v8a.apk"
LIBAPP_PATH = "lib/arm64-v8a/libapp.so"
MAX_XAPK_SIZE = 256 * 1024 * 1024
MAX_SPLIT_SIZE = 256 * 1024 * 1024
MAX_LIBAPP_SIZE = 512 * 1024 * 1024


def file_sha(path: Path, name: str) -> str:
    value = hashlib.new(name)
    with path.open("rb") as source:
        for data in iter(lambda: source.read(1024 * 1024), b""):
            value.update(data)
    return value.hexdigest()


def one_member(archive: zipfile.ZipFile, exact_name: str,
               maximum: int) -> zipfile.ZipInfo:
    candidates = [row for row in archive.infolist() if row.filename == exact_name]
    if len(candidates) != 1:
        raise ValueError(f"requires exactly one {exact_name}")
    info = candidates[0]
    if (info.is_dir() or stat.S_ISLNK(info.external_attr >> 16) or
            not 0 < info.file_size <= maximum):
        raise ValueError(f"invalid or oversized {exact_name}")
    return info


def inspect_xapk(path: Path, *, archive_sha1: str = PINNED_XAPK_SHA1,
                 library_sha256: str = PINNED_SHA256,
                 scan: bool = False) -> dict:
    if (path.is_symlink() or not path.is_file() or
            not 0 < path.stat().st_size <= MAX_XAPK_SIZE):
        raise ValueError("invalid, symlinked or oversized source XAPK")
    digest = file_sha(path, "sha1")
    if digest != archive_sha1:
        raise ValueError("XAPK fingerprint mismatch; do not inspect unknown variant")
    with zipfile.ZipFile(path) as bundle:
        one_member(bundle, BASE_APK, MAX_SPLIT_SIZE)
        split = one_member(bundle, ARM64_SPLIT, MAX_SPLIT_SIZE)
        with bundle.open(split) as handle:
            split_bytes = handle.read(MAX_SPLIT_SIZE + 1)
        if len(split_bytes) != split.file_size or len(split_bytes) > MAX_SPLIT_SIZE:
            raise ValueError("invalid split APK size")
    from io import BytesIO
    with zipfile.ZipFile(BytesIO(split_bytes)) as apk:
        native = one_member(apk, LIBAPP_PATH, MAX_LIBAPP_SIZE)
        with apk.open(native) as handle:
            blob = handle.read(MAX_LIBAPP_SIZE + 1)
        if len(blob) != native.file_size or len(blob) > MAX_LIBAPP_SIZE:
            raise ValueError("invalid original native binary size")
    native_digest = hashlib.sha256(blob).hexdigest()
    if native_digest != library_sha256:
        raise ValueError("ARM64 libapp.so SHA-256 does not match pinned original")
    result = {
        "status": "PINNED_ARM64_NATIVE_VERIFIED_NOT_GAMEPLAY_ACCEPTANCE",
        "source_archive_sha1": digest,
        "archive_path": str(path),
        "native_sha256": native_digest,
        "native_bytes": len(blob),
        "native_split": ARM64_SPLIT,
        "read_only": True,
        "import_authorized": False,
        "remaining_legacy_mismatches": 12,
    }
    if scan:
        result["story_address_candidates"] = inspect(blob)
        result["warning"] = (
            "Static literal references are NOT a proven loader, parser or decryption path; "
            "the twelve asset mismatches remain blocked."
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xapk", type=Path, required=True,
                        help="untouched APKPure EU 15.1.0 XAPK, kept outside Git")
    parser.add_argument("--scan", action="store_true",
                        help="also scan native ADR/ADRP+ADD story marker candidates")
    args = parser.parse_args()
    try:
        report = inspect_xapk(args.xapk, scan=args.scan)
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
