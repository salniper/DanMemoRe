#!/usr/bin/env python3
"""One-hop FDE provenance for BL targets of the original novel executor.

Only examines the SHA-verified original ELF via the guarded caller.
The output associates executable call targets with independently checked
CIE/FDE unwind ranges and possible original source-label xrefs.
A label inside an FDE does NOT prove C++ symbol/function identity,
constructor invocation, numeric opcode dispatch, or story compatibility.
No native code bytes, client text, assets or keys are ever emitted.
"""
from __future__ import annotations
from bisect import bisect_right
from collections import Counter

from inspect_elf_novel_xrefs import elf_segments
from inspect_native_novel_elf_sections import parse_sections
from inspect_native_novel_unwind import parse_hdr, fde_coverage, _section

MAX_CALL_SITES = 128
MAX_CALLEES = 80
MAX_LABEL_SAMPLES = 8


def _unique_executable_section(sections, va):
    matches = [
        sec for sec in sections if sec["flags"] & 4 and sec["type"] == 1
        and sec["addr"] <= va < sec["addr"] + sec["size"]
    ]
    return matches[0] if len(matches) == 1 else None


def _maybe_fde(blob, sections, segments, index, target):
    starts = index["start_vas"]
    position = bisect_right(starts, target) - 1
    if position < 0:
        return "NO_PRECEDING_FDE", None
    try:
        frame = fde_coverage(blob, sections, segments, index, position)
    except ValueError:
        return "UNVERIFIED_CALLEE_FDE", None
    if not frame["start_va"] <= target < frame["end_va_exclusive"]:
        return "NO_FDE_COVERAGE_AT_TARGET", None
    sec = _unique_executable_section(sections, target)
    if sec is None or not (
            sec["addr"] <= frame["start_va"]
            and frame["end_va_exclusive"] <= sec["addr"] + sec["size"]):
        return "FDE_NOT_UNIQUELY_EXECUTABLE", None
    return "VALIDATED_EXECUTABLE_CALLEE_FDE", frame


def inspect_direct_callees(blob, source_references, frames, precise):
    if precise.get("status") != "EXACT_CFI_REGION_INSTRUCTION_CLASS_METADATA_NO_OPCODE_PROOF":
        raise ValueError("direct BL evidence requires verified exact CFI code region")
    if frames.get("status") != "ORIGINAL_CFI_FDE_COVERAGE_ONLY_NOT_DISPATCH_PROOF":
        raise ValueError("missing independently verified caller FDE")
    if not precise.get("regions") or not frames.get("sites"):
        raise ValueError("no original caller FDE or BL evidence")
    caller_ranges = {
        (x["unwind_coverage"]["start_va"], x["unwind_coverage"]["end_va_exclusive"])
        for x in frames["sites"]
        if x["status"] == "VALIDATED_ORIGINAL_UNWIND_COVERAGE"
    }
    calls = []
    for region in precise["regions"]:
        caller = (region["validated_unwind_start_va"],
                  region["validated_unwind_end_va_exclusive"])
        if caller not in caller_ranges or region.get("direct_call_sites_truncated"):
            raise ValueError("unverified or truncated original caller instruction range")
        sites = region.get("direct_call_sites", [])
        if len(sites) != region.get("direct_call_count"):
            raise ValueError("incomplete original direct-call evidence")
        for site in sites:
            if not (caller[0] <= site["from_va"] < caller[1]
                    and site["from_va"] % 4 == 0
                    and site["to_va"] % 4 == 0):
                raise ValueError("out-of-range original direct BL site")
            calls.append(site)
    if len(calls) > MAX_CALL_SITES:
        raise ValueError("too many original BL sites")

    targets = sorted({call["to_va"] for call in calls})
    if len(targets) > MAX_CALLEES:
        raise ValueError("too many original direct-call destinations")
    sections, segments = parse_sections(blob), elf_segments(blob)
    index = parse_hdr(blob, sections)
    eh = _section(sections, ".eh_frame")
    if index["eh_frame_pointer_va"] != eh["addr"]:
        raise ValueError("original unwind header does not point to .eh_frame")
    # These are code xref *candidates* restricted by the source scanner to
    # .text and exact label starts; do not present them as symbol bindings.
    source_refs = []
    for row in source_references.get("labels", ()):
        for site in row.get("instruction_sites", ()):
            source_refs.append({
                "label_kind": row["kind"], "label": row["label"],
                "site_va": site["site_instruction_va"],
                "site_pattern": site["pattern"],
            })
    result, verdicts = [], Counter()
    for target in targets:
        if _unique_executable_section(sections, target) is None:
            state, unwind = "TARGET_NOT_EXECUTABLE_ELF_SECTION", None
        else:
            state, unwind = _maybe_fde(blob, sections, segments, index, target)
        verdicts[state] += 1
        inbound = [site["from_va"] for site in calls if site["to_va"] == target]
        associated = []
        if unwind is not None:
            associated = [
                x for x in source_refs if
                unwind["start_va"] <= x["site_va"] < unwind["end_va_exclusive"]
            ]
        result.append({
            "target_va": target,
            "source_call_sites": inbound,
            "source_call_count": len(inbound),
            "fde_status": state,
            "unwind_start_va": unwind["start_va"] if unwind else None,
            "unwind_end_va_exclusive": unwind["end_va_exclusive"] if unwind else None,
            "target_is_fde_entry": bool(unwind and target == unwind["start_va"]),
            "novel_source_label_candidates_in_same_fde": len(associated),
            "novel_source_label_samples": associated[:MAX_LABEL_SAMPLES],
            "label_samples_truncated": len(associated) > MAX_LABEL_SAMPLES,
            "constructor_or_dispatch_proven": False,
        })
    return {
        "status": "ORIGINAL_BL_CALLEE_FDE_ASSOCIATIONS_ONLY",
        "original_caller_direct_bl_sites": len(calls),
        "unique_direct_bl_targets": len(result),
        "callee_fde_status_totals": dict(verdicts),
        "callees": result,
        "numeric_opcode_to_native_handler_proven": 0,
        "original_import_authorized": False,
        "limitations": (
            "An original BL target and unwind range are verified addresses, "
            "not a semantic C++ symbol. Source metadata within a callee FDE "
            "does not establish a handler constructor or numeric dispatch. "
            "Indirect BLR targets and dynamic dispatch remain unresolved."
        )
    }
