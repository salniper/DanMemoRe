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
        executable_sec = _unique_executable_section(sections, target)
        if executable_sec is None:
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
            "target_executable_section": executable_sec["name"] if executable_sec else None,
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


# Opcode values independently observed in the owner's *six preserved*
# novelCommand files. A matching immediate in native code is only a
# numerical coincidence until data-flow from slot 2 to a constructor
# is established.
OBSERVED_STORY_CODES = frozenset(
    (1, 4, 5, 6, 7, 10, 11, 12, 15, 16, 18, 19, 20, 22, 23, 24,
     27, 29, 30, 32, 36, 37, 39, 40, 41)
)


def classify_direct_callee_code(blob, report):
    """Inspect EXACT authenticated callee FDE ranges, no adjacent functions.

    Does not decode dataflow or infer opcode dispatch; prints no client
    instructions or decryption keys. Traces BL target *addresses* only.
    """
    import struct
    from inspect_native_novel_executor_flow import _decode_control
    from inspect_native_novel_unwind import _va_to_file, MAX_FDE_RANGE
    if report.get("status") != "ORIGINAL_BL_CALLEE_FDE_ASSOCIATIONS_ONLY":
        raise ValueError("call target analysis requires validated original FDE report")
    sections = parse_sections(blob)
    segments = elf_segments(blob)
    signatures = {}
    for target in report.get("callees", ()):
        if target["fde_status"] != "VALIDATED_EXECUTABLE_CALLEE_FDE":
            continue
        start_va = target["unwind_start_va"]
        stop_va = target["unwind_end_va_exclusive"]
        key = (start_va, stop_va)
        if key in signatures:
            continue
        length = stop_va - start_va
        start_off = _va_to_file(segments, start_va)
        section = _unique_executable_section(sections, start_va)
        if (start_off is None or section is None or length <= 0 or
                length > MAX_FDE_RANGE or length % 4 or
                stop_va > section["addr"] + section["size"]):
            raise ValueError("callee FDE cannot be decoded from original executable code")
        comparisons = Counter()
        classes = Counter()
        calls = Counter()
        for off in range(start_off, start_off + length, 4):
            word = struct.unpack_from("<I", blob, off)[0]
            pc = start_va + off - start_off
            kind, value = _decode_control(word, pc)
            if kind is None:
                continue
            classes[kind] += 1
            if kind == "CMP_IMMEDIATE" and isinstance(value, int) and value <= 256:
                comparisons[value] += 1
            if kind == "CALL_DIRECT":
                calls[value] += 1
        signatures[key] = {
            "fde_start_va": start_va,
            "fde_end_va_exclusive": stop_va,
            "instruction_word_count": length // 4,
            "instruction_class_counts": dict(classes),
            "small_immediate_cmp_histogram": dict(sorted(comparisons.items())),
            "observed_story_opcode_values_also_present_as_cmp_immediates":
                sorted(OBSERVED_STORY_CODES.intersection(comparisons)),
            "unique_second_hop_direct_call_targets": len(calls),
            "second_hop_direct_call_count": sum(calls.values()),
            "second_hop_direct_call_sample": [
                {"to_va": va, "calls": n}
                for va, n in calls.most_common(24)
            ],
            "direct_call_samples_truncated": len(calls) > 24,
            "actual_opcode_dispatch_proven": False,
            "original_constructor_proven": False,
        }
    return {
        "status": "ONE_HOP_ORIGINAL_FDE_CODE_SHAPES_ONLY",
        "verified_callee_fde_regions": len(signatures),
        "callee_regions": [signatures[key] for key in sorted(signatures)],
        "numeric_opcode_handler_mappings_proven": 0,
        "original_import_authorized": False,
        "limitations": (
            "Exact original CIE/FDE code coverage, immediate comparisons "
            "and BL-address targets do not establish which decoded story opcode "
            "is used or which NovelCommand handler is constructed. Register "
            "comparisons, pointer dispatch and indirect calls require SSA/CFG."
        ),
    }


MAX_SECOND_HOP_SITES = 1024
MAX_SECOND_HOP_MATCHES = 120


def find_second_hop_handler_source_candidates(blob, source_references, direct_report,
                                              flow_report):
    """One further BL edge, validated against source-linked FDE and ELF .text.

    A handler .cpp provenance string inside a callee's FDE is *not* proof
    of a constructor or opcode->handler mapping. These are leads only.
    """
    import struct
    from inspect_native_novel_unwind import _va_to_file, MAX_FDE_RANGE
    from inspect_native_novel_executor_flow import _decode_control
    if (direct_report.get("status") != "ORIGINAL_BL_CALLEE_FDE_ASSOCIATIONS_ONLY"
            or flow_report.get("status") != "ONE_HOP_ORIGINAL_FDE_CODE_SHAPES_ONLY"):
        raise ValueError("second hop requires independently verified original caller/callee FDE")
    sections, segments = parse_sections(blob), elf_segments(blob)
    hdr = parse_hdr(blob, sections)
    eh = _section(sections, ".eh_frame")
    if hdr["eh_frame_pointer_va"] != eh["addr"]:
        raise ValueError("original EH header does not agree with frame section")
    firsthop_frames = {
        (x["unwind_start_va"],x["unwind_end_va_exclusive"])
        for x in direct_report["callees"]
        if x["fde_status"] == "VALIDATED_EXECUTABLE_CALLEE_FDE"
    }
    # Original xrefs to an exact original class source-file path. NOT symbols.
    labels = []
    for row in source_references.get("labels", []):
        if row["kind"] != "ORIGINAL_HANDLER_CPP_PATH":
            continue
        for ref in row.get("instruction_sites", []):
            labels.append({
                "handler_cpp_path":row["label"],
                "source_site_va":ref["site_instruction_va"],
                "reference_pattern":ref["pattern"],
            })
    cached = {}
    results = []
    total_bl = 0
    for frame in flow_report["callee_regions"]:
        start, end = frame["fde_start_va"], frame["fde_end_va_exclusive"]
        if (start,end) not in firsthop_frames:
            raise ValueError("unproven first-hop FDE region in second-hop input")
        length = end - start
        source_off = _va_to_file(segments, start)
        sec = _unique_executable_section(sections, start)
        if (source_off is None or sec is None or length < 4
                or length > MAX_FDE_RANGE or length % 4
                or end > sec["addr"] + sec["size"]):
            raise ValueError("first-hop function not uniquely executable")
        branches = []
        for off in range(source_off, source_off + length, 4):
            va = start + off - source_off
            kind, target = _decode_control(struct.unpack_from("<I", blob, off)[0], va)
            if kind == "CALL_DIRECT":
                branches.append(target)
        if len(branches) != frame["second_hop_direct_call_count"]:
            raise ValueError("second-hop call count disagrees with validated source")
        total_bl += len(branches)
        if total_bl > MAX_SECOND_HOP_SITES:
            raise ValueError("second-hop BL safety bound exceeded")
        exact = []
        target_unique = sorted(set(branches))
        for target in target_unique:
            if target not in cached:
                if _unique_executable_section(sections, target) is None:
                    cached[target] = ("NOT_EXECUTABLE", None, [])
                else:
                    state, coverage = _maybe_fde(blob, sections, segments, hdr, target)
                    matching = []
                    if coverage is not None:
                        matching = [x for x in labels if
                                    coverage["start_va"] <= x["source_site_va"]
                                    < coverage["end_va_exclusive"]]
                    cached[target] = (state, coverage, matching)
            state, coverage, matching = cached[target]
            if matching:
                exact.append({
                    "called_va":target,
                    "same_fde_original_cpp_labels":matching[:MAX_LABEL_SAMPLES],
                    "handler_source_label_candidates":len(matching),
                    "source_label_samples_truncated":len(matching)>MAX_LABEL_SAMPLES,
                    "callee_fde_start_va":coverage["start_va"],
                    "callee_fde_end_va_exclusive":coverage["end_va_exclusive"],
                    "callee_target_is_fde_entry":target==coverage["start_va"],
                    "opcode_or_handler_constructor_verified":False,
                })
        results.append({
            "firsthop_fde_start_va":start,
            "firsthop_fde_end_va_exclusive":end,
            "second_hop_bl_sites":len(branches),
            "second_hop_distinct_targets":len(target_unique),
            "target_functions_with_novel_handler_cpp_labels":len(exact),
            "handler_source_candidates":exact[:MAX_SECOND_HOP_MATCHES],
            "handler_candidates_truncated":len(exact)>MAX_SECOND_HOP_MATCHES,
        })
    state_counts = Counter(state for state,_,_ in cached.values())
    return {
        "status":"ORIGINAL_TWO_HOP_NATIVE_HANDLER_CPP_METADATA_ONLY",
        "firsthop_fde_regions":len(results),
        "total_second_hop_bl_sites":total_bl,
        "distinct_second_hop_targets":len(cached),
        "second_hop_target_fde_status_counts":dict(state_counts),
        "candidate_callees_with_handler_source_cpp":sum(
            row["target_functions_with_novel_handler_cpp_labels"] for row in results),
        "firsthop_regions":results,
        "numeric_opcode_to_native_handler_mappings_verified":0,
        "original_import_authorized":False,
        "limitations":(
            "Same FDE as a C++ source-path xref does not identify the called "
            "target as the class constructor. Does not prove original opcode "
            "numeric dispatch, actual playback, or reference asset hashes."
        ),
    }
