#!/usr/bin/env python3
"""Read-only, bounded ARM64 code-context metadata for authenticated novel xrefs.

This does not reconstruct functions or call paths. It emits NO native code,
decoded text, secret material, offsets to decrypted data, or game assets.
Only invoke after the pinned original ARM64 library SHA-256 matches.
"""
from __future__ import annotations

import struct

from inspect_elf_novel_xrefs import elf_segments, sign_extend

WINDOW_BYTES = 192
BOUNDARY_BYTES = 2048
MAX_SITES = 24
MAX_EDGES = 16


def classify_literal(blob, position, marker):
    """Classify where a marker occurs inside a printable string, without emitting it."""
    if not 0 <= position <= len(blob) - len(marker):
        raise ValueError("invalid literal offset")
    prefix = position and 32 <= blob[position - 1] <= 126
    suffix = (position + len(marker) < len(blob) and
              32 <= blob[position + len(marker)] <= 126)
    return ("EMBEDDED_PRINTABLE_STRING" if prefix or suffix
            else "DELIMITED_OR_NONPRINTABLE_STRING")


def decode_metadata(word, pc):
    """Decode only control-flow/prologue instruction classes, not disassembly text."""
    if word & 0xfc000000 == 0x94000000:  # BL imm26
        delta = sign_extend(word & 0x03ffffff, 26) << 2
        return "CALL_DIRECT", pc + delta
    if word & 0xfc000000 == 0x14000000:  # B imm26
        delta = sign_extend(word & 0x03ffffff, 26) << 2
        return "BRANCH_DIRECT", pc + delta
    if word & 0xfffffc1f == 0xd63f0000:  # BLR Xn
        return "CALL_INDIRECT", None
    if word & 0xfffffc1f == 0xd65f0000:  # RET Xn
        return "RETURN", None
    if word & 0xffc07fff == 0xa9807bfd:  # STP x29,x30,[sp,#-imm]!
        return "FRAME_PROLOGUE_CANDIDATE", None
    return None, None


def executable_segment(segments, offset, vaddr):
    matches = [
        segment for segment in segments
        if segment["executable"] and
        segment["offset"] <= offset < segment["offset"] + segment["size"] and
        segment["vaddr"] + offset - segment["offset"] == vaddr
    ]
    return matches[0] if len(matches) == 1 else None


def context_at(blob, segments, literal_offset, marker, site, radius=WINDOW_BYTES):
    off = site["instruction_file_offset"]
    pc = site["instruction_virtual_address"]
    segment = executable_segment(segments, off, pc)
    if segment is None or radius < 4 or radius > BOUNDARY_BYTES:
        raise ValueError("invalid or unmapped executable site")
    low = segment["offset"]
    high = low + segment["size"]
    if (pc & 3) or (off - low) % 4:
        raise ValueError("non-aligned instruction address")
    start = max(low, off - radius)
    stop = min(high, off + radius + 4)
    events = []
    for at in range(start, stop - 3, 4):
        word = struct.unpack_from("<I", blob, at)[0]
        va = segment["vaddr"] + at - low
        kind, dest = decode_metadata(word, va)
        if kind is not None:
            events.append({"offset": at, "kind": kind, "target_va": dest})
    near_left = [event["offset"] for event in events
                 if event["kind"] == "FRAME_PROLOGUE_CANDIDATE"
                 and event["offset"] <= off]
    # Search a bounded window for the nearest conventional frame marker,
    # without asserting it actually delimits the function.
    left_bound = max(low, off - BOUNDARY_BYTES)
    best = None
    for at in range(off, left_bound - 1, -4):
        word = struct.unpack_from("<I", blob, at)[0]
        if decode_metadata(word, segment["vaddr"] + at - low)[0] == "FRAME_PROLOGUE_CANDIDATE":
            best = at
            break
    next_return = None
    for at in range(off, min(high - 3, off + BOUNDARY_BYTES + 4), 4):
        word = struct.unpack_from("<I", blob, at)[0]
        if decode_metadata(word, segment["vaddr"] + at - low)[0] == "RETURN":
            next_return = at
            break
    return {
        "marker": marker,
        "literal_file_offset": literal_offset,
        "literal_form": classify_literal(blob, literal_offset, marker),
        "xref_file_offset": off,
        "xref_va": pc,
        "xref_pattern": site["instruction_pattern"],
        "possible_frame_start_offset": best,
        "first_following_return_offset": next_return,
        "window_control_flow_event_count": len(events),
        "window_control_flow_events": events[:MAX_EDGES],
        "window_events_truncated": len(events) > MAX_EDGES,
        "function_boundary_status": "HEURISTIC_ONLY_NOT_VALIDATED",
    }


def inspect_context(blob, scan):
    segments = elf_segments(blob)
    results = []
    total = 0
    for row in scan["markers"]:
        marker = row["marker"]
        for location in row["locations"]:
            references = location.get("address_references")
            if references is None:
                continue
            total += references["candidate_count"]
            for site in references["candidates"]:
                if len(results) >= MAX_SITES:
                    raise ValueError("too many code sites for bounded contextual analysis")
                results.append(context_at(blob, segments, location["file_offset"],
                                          marker, site))
    return {
        "status": "STATIC_NEIGHBORHOOD_ONLY_NOT_LOADER_PROOF",
        "candidate_site_count": total,
        "sites": results,
        "limitations": (
            "Frame markers and nearby branches do not establish function membership "
            "or a data-flow path. Paths may be constructed dynamically. "
            "No decryption compatibility or import authorization is inferred."
        ),
    }
