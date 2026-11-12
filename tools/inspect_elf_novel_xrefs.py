#!/usr/bin/env python3
"""Read-only ELF64/AArch64 literal mapping and bounded single-pass ADR/ADRP+ADD candidates.

Do not treat data-address candidates as call sites, decryptors, or parser proof.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

PINNED_SHA256 = "e49a8cc7991f8946365a28aebad605ce566b034826dd4b34a982ab18b38303b3"
MARKERS = ("divide_novel_command_enc", "novelCommand", "NovelCommand", "novel_command")
MAX_SIZE = 1024 * 1024 * 1024
MAX_HITS = 40


def elf_segments(blob):
    if len(blob) < 64 or blob[:4] != b"\x7fELF" or blob[4:6] != b"\x02\x01":
        raise ValueError("requires little-endian ELF64")
    if struct.unpack_from("<H", blob, 18)[0] != 183:
        raise ValueError("requires AArch64 ELF")
    phoff = struct.unpack_from("<Q", blob, 32)[0]
    entsize, count = struct.unpack_from("<HH", blob, 54)
    if (entsize < 56 or not 1 <= count <= 512 or phoff > len(blob)
            or count * entsize > len(blob) - phoff):
        raise ValueError("malformed program header table")
    segments = []
    for i in range(count):
        off = phoff + i * entsize
        kind, flags = struct.unpack_from("<II", blob, off)
        if kind != 1:
            continue
        file_offset = struct.unpack_from("<Q", blob, off + 8)[0]
        vaddr = struct.unpack_from("<Q", blob, off + 16)[0]
        size = struct.unpack_from("<Q", blob, off + 32)[0]
        memsize = struct.unpack_from("<Q", blob, off + 40)[0]
        if size > memsize or file_offset > len(blob) or size > len(blob) - file_offset:
            raise ValueError("invalid load segment extent")
        if size:
            segments.append(dict(offset=file_offset, vaddr=vaddr, size=size,
                                 executable=bool(flags & 1)))
    if not segments:
        raise ValueError("no file-backed PT_LOAD segments")
    return segments


def map_offset(segments, offset):
    matches = [s["vaddr"] + offset - s["offset"] for s in segments
               if s["offset"] <= offset < s["offset"] + s["size"]]
    return matches[0] if len(matches) == 1 else None


def sign_extend(value, bits):
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


MAX_LITERAL_OCCURRENCES = 8192


def find_references_multi(blob, segments, targets, limit=MAX_HITS):
    """Scan executable segments ONCE for direct ADR / adjacent ADRP+ADD targets.

    Does not disassemble control flow, pointer-indirect references, GOT or
    register aliases. Report locations only; this is not a decryption proof.
    """
    references = {
        target: {"candidate_count": 0, "candidates": [], "truncated": False}
        for target in targets
    }
    for segment in segments:
        if not segment["executable"]:
            continue
        low = segment["offset"]
        high = low + segment["size"]
        first = low + ((-segment["vaddr"]) % 4)
        for off in range(first, high - 3, 4):
            word = struct.unpack_from("<I", blob, off)[0]
            pc = segment["vaddr"] + off - low
            target = None
            kind = None
            if (word & 0x9f000000) == 0x10000000:
                imm21 = (((word >> 5) & 0x7ffff) << 2) | ((word >> 29) & 3)
                target = pc + sign_extend(imm21, 21)
                kind = "ADR"
            elif (word & 0x9f000000) == 0x90000000 and off + 8 <= high:
                add = struct.unpack_from("<I", blob, off + 4)[0]
                if (add & 0xff000000) == 0x91000000:
                    reg = word & 31
                    if ((add >> 5) & 31) == reg:
                        imm21 = (((word >> 5) & 0x7ffff) << 2) | ((word >> 29) & 3)
                        page = (pc & ~4095) + (sign_extend(imm21, 21) << 12)
                        imm12 = (add >> 10) & 0xfff
                        shift = 12 if (add >> 22) & 1 else 0
                        target = page + (imm12 << shift)
                        kind = "ADRP_ADD"
            entry = references.get(target)
            if entry is None:
                continue
            entry["candidate_count"] += 1
            if len(entry["candidates"]) < limit:
                entry["candidates"].append({
                    "instruction_file_offset": off,
                    "instruction_virtual_address": pc,
                    "instruction_pattern": kind,
                })
    for entry in references.values():
        entry["truncated"] = entry["candidate_count"] > len(entry["candidates"])
    return references


def find_references(blob, segments, target, limit=MAX_HITS):
    """Compatibility helper for a single target; same evidence limitations."""
    return find_references_multi(blob, segments, (target,), limit)[target]


def inspect(blob):
    segments = elf_segments(blob)
    all_locations = {}
    targets = set()
    for marker in MARKERS:
        needle = marker.encode("ascii")
        offsets = []
        start = 0
        while True:
            offset = blob.find(needle, start)
            if offset < 0:
                break
            if len(offsets) >= MAX_LITERAL_OCCURRENCES:
                raise ValueError("too many marker occurrences to inspect safely")
            va = map_offset(segments, offset)
            offsets.append((offset, va))
            if va is not None:
                targets.add(va)
            start = offset + 1
        all_locations[marker] = offsets

    references = find_references_multi(blob, segments, targets)
    result = []
    for marker, offsets in all_locations.items():
        # Prioritize referenced literals so a relevant reference beyond the
        # first 40 same-name strings remains visible in the bounded report.
        referenced = [(off, va) for off, va in offsets
                      if va is not None and references[va]["candidate_count"]]
        selected = referenced[:MAX_HITS]
        chosen = {off for off, _ in selected}
        for off, va in offsets:
            if len(selected) >= MAX_HITS:
                break
            if off not in chosen:
                selected.append((off, va))
                chosen.add(off)
        locations = [{
            "file_offset": off, "virtual_address": va,
            "address_references": references[va] if va is not None else None,
        } for off, va in selected]
        result.append({
            "marker": marker,
            "literal_hits": len(offsets),
            "referenced_literal_hits": len(referenced),
            "locations": locations,
            "truncated": len(offsets) > len(locations),
        })
    return {
        "status": "CANDIDATE_STATIC_REFERENCES_ONLY",
        "markers": result,
        "scan_scope": "ALL_BOUNDED_LITERAL_OCCURRENCES_ONE_EXECUTABLE_PASS",
        "limitations": (
            "ADR/adjacent ADRP+ADD only; neither references nor missing references "
            "establish control flow, decryption, asset identity, or compatibility."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    args = parser.parse_args()
    binary = args.binary
    if (binary.is_symlink() or not binary.is_file() or
            not 0 < binary.stat().st_size <= MAX_SIZE):
        parser.error("refusing invalid, oversized or symlinked binary")
    blob = binary.read_bytes()
    if hashlib.sha256(blob).hexdigest() != PINNED_SHA256:
        parser.error("pristine 15.1.0 ARM64 SHA-256 mismatch")
    report = inspect(blob)
    report["binary_sha256"] = PINNED_SHA256
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
