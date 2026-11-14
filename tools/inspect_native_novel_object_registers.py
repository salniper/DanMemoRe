#!/usr/bin/env python3
"""Inspect possible object-register sources for authenticated original BLR calls.

This is conservative, bounded linear *syntax*, NOT CFG dominance, SSA,
actual pointer resolution, a verified vtable, or opcode-handler mapping.
Only works on caller FDE ranges established in the SHA-pinned original.
No client bytes, cipher, decoded text, or keys are emitted.
"""
from __future__ import annotations

import struct

from inspect_elf_novel_xrefs import elf_segments
from inspect_native_novel_elf_sections import parse_sections
from inspect_native_novel_indirect_calls import _register_writer, _control_barrier
from inspect_native_novel_unwind import _va_to_file

MAX_ORIGIN_SCAN_WORDS = 384
MAX_ORIGINAL_CALLS = 32


def inspect_object_register_origins(blob, frame_report, precise_report, indirect_report):
    if (frame_report.get("status") !=
            "ORIGINAL_CFI_FDE_COVERAGE_ONLY_NOT_DISPATCH_PROOF" or
            precise_report.get("status") !=
            "EXACT_CFI_REGION_INSTRUCTION_CLASS_METADATA_NO_OPCODE_PROOF" or
            indirect_report.get("status") !=
            "ORIGINAL_CFI_BLR_REGISTER_LOAD_HINTS_NO_DISPATCH_PROOF"):
        raise ValueError("all original CFI and BLR evidence is required")
    valid = {
        (frame["unwind_coverage"]["start_va"],
         frame["unwind_coverage"]["end_va_exclusive"])
        for frame in frame_report.get("sites", [])
        if frame.get("status") == "VALIDATED_ORIGINAL_UNWIND_COVERAGE"
    }
    ranges = [
        (region["validated_unwind_start_va"],
         region["validated_unwind_end_va_exclusive"])
        for region in precise_report.get("regions", [])
    ]
    if not ranges or len(ranges) > 12 or any(x not in valid for x in ranges):
        raise ValueError("unverified original executable regions")
    sites = indirect_report.get("sites", [])
    if not isinstance(sites, list) or len(sites) > MAX_ORIGINAL_CALLS:
        raise ValueError("unexpected indirect site count")
    if len(sites) != indirect_report.get("original_blr_call_sites"):
        raise ValueError("inconsistent original indirect call report")
    segments, sections = elf_segments(blob), parse_sections(blob)
    results = []
    for call in sites:
        call_va = call.get("call_instruction_va")
        if not isinstance(call_va, int):
            raise ValueError("bad original call address")
        candidates = [(a,b) for a,b in ranges if a <= call_va < b]
        if len(candidates) != 1:
            raise ValueError("call lies outside unique proven FDE")
        start_va, end_va = candidates[0]
        sec = [s for s in sections if s["type"] == 1 and s["flags"] & 4
               and s["addr"] <= start_va and end_va <= s["addr"] + s["size"]]
        origin_off = _va_to_file(segments, start_va)
        if len(sec) != 1 or origin_off is None:
            raise ValueError("proven FDE not executable")
        call_off = origin_off + call_va - start_va
        if call_off % 4 or call_off + 4 > len(blob):
            raise ValueError("unaligned original call")
        word = struct.unpack_from("<I", blob, call_off)[0]
        reg = (word >> 5) & 31
        if ((word & 0xfffffc1f) != 0xd63f0000 or
                reg != call.get("call_target_register")):
            raise ValueError("original BLR instruction changed or not authenticated")
        initial_load = call.get("earlier_register_writer_file_offset")
        source_reg = call.get("earlier_register_writer_source")
        if initial_load is None or not isinstance(source_reg,int) or not 0 <= source_reg <= 30:
            results.append({
                "call_instruction_va":call_va,
                "object_source_register":None,
                "origin_status":"OBJECT_REGISTER_UNAVAILABLE",
                "origin_writer":None,
                "register_flow_proven":False,
            })
            continue
        if not origin_off <= initial_load < call_off or initial_load % 4:
            raise ValueError("first original object load outside authenticated FDE")
        first = _register_writer(struct.unpack_from("<I",blob,initial_load)[0],
                                 start_va + initial_load - origin_off)
        if (first is None or first["kind"]!="LOAD_POINTER_FROM_REGISTER"
                or first["dest"]!=reg or first["base"]!=source_reg
                or first["byte_offset"]!=0):
            raise ValueError("original first object pointer load not verified")
        # Find nearest *recognized* earlier writer; no promise that arbitrary
        # unrecognized instructions preserve it, no CFG reachability proof.
        lower = max(origin_off, initial_load-4*MAX_ORIGIN_SCAN_WORDS)
        barrier_count=0
        candidate=None
        for off in range(initial_load-4,lower-1,-4):
            raw=struct.unpack_from("<I",blob,off)[0]
            if _control_barrier(raw):
                barrier_count+=1
            hint=_register_writer(raw, start_va + off - origin_off)
            if hint and hint["dest"]==source_reg:
                candidate={
                    "instruction_va":start_va + off - origin_off,
                    "recognized_writer_kind":hint["kind"],
                    "source_register":hint.get("base",hint.get("source")),
                    "source_byte_offset":hint.get("byte_offset"),
                    "source_immediate":hint.get("immediate"),
                    "distance_in_instructions":(initial_load-off)//4,
                    "control_transfers_between_writer_and_first_load":barrier_count,
                }
                break
        results.append({
            "call_instruction_va":call_va,
            "object_source_register":source_reg,
            "first_load_instruction_va":start_va + initial_load-origin_off,
            "origin_status":"LINEAR_WRITER_CANDIDATE_NOT_CFG_PROOF" if candidate else
                            "NO_RECOGNIZED_WRITER_IN_ORIGINAL_FDE",
            "origin_writer":candidate,
            "register_flow_proven":False,
            "resolved_object_pointer":None,
            "verified_vtable_va":None,
        })
    return {
        "status":"ORIGINAL_OBJECT_REGISTER_LINEAR_PROVENANCE_ONLY",
        "indirect_call_count":len(results),
        "object_register_sources":results,
        "recognized_origin_writer_count":sum(x["origin_writer"] is not None
                                             for x in results),
        "verified_object_pointer_count":0,
        "verified_vtable_function_count":0,
        "verified_opcode_handler_mappings":0,
        "original_import_authorized":False,
        "limitations":(
            "Nearest whitelisted AArch64 register writer is a linear text "
            "candidate only. Across branches and calls, register values can "
            "differ. Other unsupported register definitions may intervene. "
            "No original runtime vtable contents or command dispatch proven."
        ),
    }
