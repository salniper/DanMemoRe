#!/usr/bin/env python3
"""Read-only ELF64/AArch64 literal-to-virtual-address and ADRP+ADD candidates.

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


def find_references(blob, segments, target, limit=MAX_HITS):
    """Only adjacent ADRP Xn / ADD Xd,Xn,#imm candidates in executable segments."""
    matches = []
    total = 0
    for segment in segments:
        if not segment["executable"]:
            continue
        low = segment["offset"]
        high = low + segment["size"]
        first = low + ((-segment["vaddr"]) % 4)
        for off in range(first, high - 7, 4):
            adrp, add = struct.unpack_from("<II", blob, off)
            if (adrp & 0x9f000000) != 0x90000000:
                continue
            if (add & 0xff000000) != 0x91000000:
                continue
            reg = adrp & 31
            if ((add >> 5) & 31) != reg:
                continue
            imm21 = (((adrp >> 5) & 0x7ffff) << 2) | ((adrp >> 29) & 3)
            pc = segment["vaddr"] + off - low
            page = (pc & ~4095) + (sign_extend(imm21, 21) << 12)
            imm12 = (add >> 10) & 0xfff
            shift = 12 if (add >> 22) & 1 else 0
            if page + (imm12 << shift) != target:
                continue
            total += 1
            if len(matches) < limit:
                matches.append({"instruction_file_offset": off,
                                "instruction_virtual_address": pc})
    return {"candidate_count": total, "candidates": matches,
            "truncated": total > len(matches)}


def inspect(blob):
    segments = elf_segments(blob)
    result = []
    for marker in MARKERS:
        start, count, locations = 0, 0, []
        while True:
            offset = blob.find(marker.encode("ascii"), start)
            if offset < 0:
                break
            count += 1
            va = map_offset(segments, offset)
            if len(locations) < MAX_HITS:
                locations.append({
                    "file_offset": offset, "virtual_address": va,
                    "adrp_add": find_references(blob, segments, va) if va is not None else None,
                })
            start = offset + 1
        result.append({"marker": marker, "literal_hits": count,
                       "locations": locations, "truncated": count > len(locations)})
    return {"status": "CANDIDATE_STATIC_REFERENCES_ONLY", "markers": result,
            "limitations": "Adjacent ADRP+ADD does not establish a loader, control-flow, decryption, or compatibility."}


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
