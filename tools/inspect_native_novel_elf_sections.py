#!/usr/bin/env python3
"""Read-only ELF section/symbol provenance for authenticated novel-command markers.

Never outputs source code, binary bytes, decrypted resources, or a game library.
This is structural classification only, not an executable call graph.
"""
from __future__ import annotations
from collections import Counter
import struct

from inspect_elf_novel_xrefs import elf_segments

MAX_SECTIONS = 2048
MAX_SYMBOLS_PER_TABLE = 1_000_000
MAX_SYMBOL_TABLES = 8
MAX_SAMPLES = 16
MAX_NAME = 512


def _u64(data, off):
    return struct.unpack_from("<Q", data, off)[0]


def _ascii_at(blob, start, size, index):
    if index >= size:
        return ""
    initial = start + index
    final = blob.find(b"\x00", initial, min(start + size, initial + MAX_NAME + 1))
    if final < 0:
        return ""
    return blob[initial:final].decode("utf-8", errors="replace")


def parse_sections(blob):
    # Reuse the original strict ELF64 little-endian AArch64 header checks.
    elf_segments(blob)
    shoff = _u64(blob, 40)
    shentsize, count, names_index = struct.unpack_from("<HHH", blob, 58)
    if shoff == 0 or count == 0:
        return []   # Stripped section headers; cannot infer section membership.
    if (shentsize < 64 or count > MAX_SECTIONS or names_index >= count
            or shoff > len(blob) or shentsize * count > len(blob) - shoff):
        raise ValueError("malformed ELF section header table")
    sections = []
    for index in range(count):
        at = shoff + index * shentsize
        fields = struct.unpack_from("<IIQQQQIIQQ", blob, at)
        name_index, typ, flags, va, start, size, link, info, align, stride = fields
        if typ != 8 and (start > len(blob) or size > len(blob) - start):
            raise ValueError("ELF section outside file")
        sections.append({
            "index": index, "name_offset": name_index, "type": typ,
            "flags": flags, "addr": va, "offset": start, "size": size,
            "link": link, "entry_size": stride,
        })
    strings = sections[names_index]
    if strings["type"] != 3:
        raise ValueError("ELF section name table must be STRTAB")
    for section in sections:
        section["name"] = _ascii_at(
            blob, strings["offset"], strings["size"], section.pop("name_offset")
        )
    return sections


def containing_sections(sections, offset):
    hits = [
        section for section in sections
        if section["type"] not in (0, 8)
        and section["size"] > 0
        and section["offset"] <= offset < section["offset"] + section["size"]
    ]
    if not hits:
        return {"name": "UNMAPPED_OR_STRIPPED", "executable": False,
                "ambiguous": False}
    hits.sort(key=lambda section: section["size"])
    return {
        "name": hits[0]["name"] or "UNNAMED",
        "executable": bool(hits[0]["flags"] & 4),
        "ambiguous": len(hits) > 1,
    }


def matching_symbols(blob, sections):
    totals = Counter()
    sample = []
    table_count = 0
    symbols_checked = 0
    for section in sections:
        if section["type"] not in (2, 11):
            continue
        table_count += 1
        if table_count > MAX_SYMBOL_TABLES:
            raise ValueError("too many ELF symbol tables")
        stride = section["entry_size"]
        if stride < 24 or section["size"] % stride or section["link"] >= len(sections):
            raise ValueError("invalid ELF symbol table dimensions")
        strings = sections[section["link"]]
        if strings["type"] != 3:
            raise ValueError("ELF symbol table must link STRTAB")
        count = section["size"] // stride
        if count > MAX_SYMBOLS_PER_TABLE:
            raise ValueError("too many ELF symbols")
        symbols_checked += count
        for i in range(count):
            at = section["offset"] + i * stride
            name_offset = struct.unpack_from("<I", blob, at)[0]
            name = _ascii_at(blob, strings["offset"], strings["size"], name_offset)
            if not any(word in name for word in
                       ("NovelCommand", "novelCommand", "novel_command", "divide_novel_command")):
                continue
            info = blob[at + 4]
            va = _u64(blob, at + 8)
            size = _u64(blob, at + 16)
            kind = ("FUNCTION" if (info & 15) == 2 else
                    "OBJECT" if (info & 15) == 1 else "OTHER")
            totals[kind] += 1
            if len(sample) < MAX_SAMPLES:
                sample.append({
                    "name": name[:180], "kind": kind,
                    "symbol_address": va, "symbol_size": size,
                    "table": section["name"],
                })
    return {
        "symtab_count": table_count,
        "symbols_checked": symbols_checked,
        "matching_symbol_count": sum(totals.values()),
        "matching_symbol_types": dict(totals),
        "matching_symbol_samples": sample,
        "samples_truncated": sum(totals.values()) > len(sample),
    }


def inspect_sections(blob, scan):
    sections = parse_sections(blob)
    by_marker = {}
    locations = []
    for entry in scan["markers"]:
        section_counts = Counter()
        for loc in entry["locations"]:
            literal = containing_sections(sections, loc["file_offset"])
            section_counts[literal["name"]] += 1
            refs = loc.get("address_references")
            if refs is None:
                continue
            for ref in refs["candidates"]:
                location = {
                    "marker": entry["marker"],
                    "string_offset": loc["file_offset"],
                    "string_section": literal,
                    "candidate_instruction_offset": ref["instruction_file_offset"],
                    "candidate_section": containing_sections(
                        sections, ref["instruction_file_offset"]),
                    "candidate_kind": ref["instruction_pattern"],
                }
                locations.append(location)
        by_marker[entry["marker"]] = {
            "sampled_literal_section_counts": dict(section_counts),
            "total_literals": entry["literal_hits"],
            "reported_locations": len(entry["locations"]),
            "sampling_caveat": "Section totals cover reported locations only",
        }
    return {
        "status": "ELF_SECTION_SYMBOL_EVIDENCE_ONLY",
        "section_table_present": bool(sections),
        "section_count": len(sections),
        "marker_sections": by_marker,
        "candidate_locations": locations[:32],
        "candidate_locations_truncated": len(locations) > 32,
        "named_symbols": matching_symbols(blob, sections),
        "limitations": (
            "Section offsets and matching named symbols do NOT prove runtime usage, "
            "file I/O, decryption, or original game asset compatibility. "
            "No valid import or gameplay acceptance is implied."
        ),
    }
