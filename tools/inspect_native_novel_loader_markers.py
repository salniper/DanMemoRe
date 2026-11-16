#!/usr/bin/env python3
"""Inspect a *pinned* pristine ARM64 client for literal novel-command path markers.

This is read-only static reconnaissance, not decryption or proof of a call path.
Reports FILE offsets (not ARM64 virtual addresses). Never outputs original bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mmap
from pathlib import Path

# The same untouched 15.1.0 ARM64 image pinned by decode_master_data.cjs.
PINNED_SHA256 = "e49a8cc7991f8946365a28aebad605ce566b034826dd4b34a982ab18b38303b3"
MAX_BINARY_SIZE = 1024 * 1024 * 1024
MAX_OFFSETS_PER_MARKER = 20
MARKERS = (
    "divide_novel_command_enc", "divideNovelCommand", "novelCommand",
    "novel_command", "NovelCommand", "novelCommandEnc",
    "divide_enc", "master/", ".enc",
)


def sha256_file(target: Path) -> str:
    digest = hashlib.sha256()
    with target.open("rb") as source:
        while block := source.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def scan(blob, markers=MARKERS) -> dict:
    """Pure static literal match; no ELF symbol inference or disassembly."""
    results = []
    for marker in markers:
        needle = marker.encode("ascii")
        offsets = []
        at = 0
        total = 0
        while True:
            at = blob.find(needle, at)
            if at < 0:
                break
            total += 1
            if len(offsets) < MAX_OFFSETS_PER_MARKER:
                offsets.append(at)
            at += 1
        results.append({
            "marker": marker, "literal_count": total,
            "file_offsets_decimal": offsets,
            "offset_list_truncated": total > len(offsets),
        })
    return {
        "inspection": "PINNED_NATIVE_LITERAL_SCAN",
        "results": results,
        "warning": (
            "Literal offsets are file offsets, not virtual addresses or call sites. "
            "No match does not prove absence of a native loader. Neither a hit nor "
            "a miss authenticates any legacy asset or permits import."
        ),
    }


def inspect_binary(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("refusing symlink or non-file binary")
    size = path.stat().st_size
    if size <= 0 or size > MAX_BINARY_SIZE:
        raise ValueError("binary outside bounded size range")
    digest = sha256_file(path)
    if digest != PINNED_SHA256:
        raise ValueError("not the independently pinned pristine 15.1.0 ARM64 image")
    with path.open("rb") as source:
        with mmap.mmap(source.fileno(), 0, access=mmap.ACCESS_READ) as mapping:
            report = scan(mapping)
    report["binary_sha256"] = digest
    report["binary_bytes"] = size
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path,
                        help="local untouched 15.1.0 ARM64 ELF; never uploaded")
    args = parser.parse_args()
    print(json.dumps(inspect_binary(args.binary), indent=2))


if __name__ == "__main__":
    main()
