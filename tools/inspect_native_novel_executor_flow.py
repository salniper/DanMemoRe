"""Bounded ARM64 dispatch-neighborhood *metadata*, never a command map.

Seeds come ONLY from source-path/name references validated in ELF .text
of the SHA-256-pinned original client. Classifies immediate comparisons,
direct/indirect branches and their addresses. Nearby instructions do NOT
establish function ownership, a recovered switch table, constructor linkage,
or a real opcode -> handler mapping. No original bytes are printed.
"""
from __future__ import annotations

from collections import Counter
import struct

from inspect_elf_novel_xrefs import sign_extend
from inspect_native_novel_elf_sections import parse_sections

NEIGHBORHOOD_BYTES = 4096
MAX_EXECUTOR_SITES = 12
MAX_EVENTS_PER_SITE = 48


def _decode_control(word, pc):
    # Only return instruction-class metadata and numeric immediate/target,
    # not a full disassembly. Most variants of dataflow are unsupported.
    if word & 0x7f00001f == 0x7100001f:  # CMP (SUBS WZR) immediate
        immediate = (word >> 10) & 0xfff
        if (word >> 22) & 1:
            immediate <<= 12
        return "CMP_IMMEDIATE", immediate
    if word & 0xfc000000 == 0x94000000:  # BL
        return "CALL_DIRECT", pc + (sign_extend(word & 0x3ffffff, 26) << 2)
    if word & 0xfc000000 == 0x14000000:  # B
        return "BRANCH_DIRECT", pc + (sign_extend(word & 0x3ffffff, 26) << 2)
    if word & 0xff000010 == 0x54000000:  # B.cond
        delta = sign_extend((word >> 5) & 0x7ffff, 19) << 2
        return "BRANCH_CONDITIONAL", pc + delta
    if word & 0x7e000000 == 0x34000000:  # CBZ/CBNZ
        delta = sign_extend((word >> 5) & 0x7ffff, 19) << 2
        return "BRANCH_COMPARE_ZERO", pc + delta
    if word & 0x7e000000 == 0x36000000:  # TBZ/TBNZ
        delta = sign_extend((word >> 5) & 0x3fff, 14) << 2
        return "BRANCH_BIT_TEST", pc + delta
    if word & 0xfffffc1f == 0xd61f0000:
        return "BRANCH_INDIRECT", None
    if word & 0xfffffc1f == 0xd63f0000:
        return "CALL_INDIRECT", None
    if word & 0xfffffc1f == 0xd65f0000:
        return "RETURN", None
    return None, None


def _executable_site(sections, off):
    hits = [
        section for section in sections
        if section["flags"] & 4 and section["type"] == 1
        and section["offset"] <= off < section["offset"] + section["size"]
    ]
    return hits[0] if len(hits) == 1 else None


def _is_executor_label(row):
    name = row.get("label", "")
    return ("NovelCommandExecuter::createNovel(" in name or
            name.endswith("/NovelCommandExecuter.cpp"))


def analyze_executor_neighborhoods(blob, source_references):
    sections = parse_sections(blob)
    if not sections:
        raise ValueError("missing executable-section evidence")
    anchors = sorted({
        ref["site_instruction_file_offset"]
        for row in source_references.get("labels", [])
        if _is_executor_label(row)
        for ref in row["instruction_sites"]
    })
    if len(anchors) > MAX_EXECUTOR_SITES:
        raise ValueError("too many original executor source anchors")
    if not anchors:
        return {
            "status": "NO_AUTHENTICATED_EXECUTOR_CODE_ANCHORS",
            "executor_site_count": 0,
            "native_opcode_handler_mapping_count": 0,
            "original_import_authorized": False,
        }
    sites = []
    for seed in anchors:
        section = _executable_site(sections, seed)
        if section is None or seed % 4 or section["addr"] % 4:
            raise ValueError("seed not mapped to unique aligned executable section")
        left = max(section["offset"], seed - NEIGHBORHOOD_BYTES)
        right = min(section["offset"] + section["size"], seed + NEIGHBORHOOD_BYTES + 4)
        left += (-left) % 4
        kinds = Counter()
        comparisons = Counter()
        events = []
        for off in range(left, right - 3, 4):
            word = struct.unpack_from("<I", blob, off)[0]
            va = section["addr"] + off - section["offset"]
            kind, value = _decode_control(word, va)
            if kind is None:
                continue
            kinds[kind] += 1
            if kind == "CMP_IMMEDIATE" and isinstance(value, int) and 0 <= value <= 128:
                comparisons[value] += 1
            if len(events) < MAX_EVENTS_PER_SITE and (
                    kind in ("CALL_INDIRECT", "BRANCH_INDIRECT", "RETURN")
                    or kind == "CMP_IMMEDIATE" and isinstance(value, int) and 0 <= value <= 128
                    or kind.startswith("BRANCH_")):
                events.append({
                    "instruction_file_offset": off,
                    "kind": kind,
                    "immediate_or_target": value,
                })
        sites.append({
            "anchor_file_offset": seed,
            "window_file_offset_start": left,
            "window_file_offset_end": right,
            "instruction_classes": dict(kinds),
            "small_immediate_cmp_histogram": dict(sorted(comparisons.items())),
            "bounded_control_flow_events": events,
            "events_truncated": sum(kinds.values()) > len(events),
        })
    return {
        "status": "ORIGINAL_EXECUTOR_CODE_NEIGHBORHOOD_METADATA_NOT_DISPATCH_PROOF",
        "executor_site_count": len(anchors),
        "sites": sites,
        "native_opcode_handler_mapping_count": 0,
        "original_import_authorized": False,
        "limitations": (
            "Overlapping +/-4 KiB neighborhoods from validated executor-source "
            "string references are not precise function boundaries. Branch "
            "targets, opcode-sized comparisons and indirect calls are NOT "
            "a verified numerical dispatch relationship or constructor chain."
        ),
    }
