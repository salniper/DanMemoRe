#!/usr/bin/env python3
"""Find original AArch64 executor code regions using exact .eh_frame FDE ranges.

Both .eh_frame_hdr index and matching .eh_frame FDE/CIE are validated.
An FDE is unwind coverage, not necessarily a C++ semantic function boundary.
Only metadata is emitted. No native bytes, story text or crypto materials.
"""
from __future__ import annotations
from bisect import bisect_right
import struct

from inspect_elf_novel_xrefs import elf_segments, map_offset
from inspect_native_novel_elf_sections import parse_sections
from inspect_native_novel_executor_flow import _is_executor_label, _decode_control

MAX_FDE_ENTRIES = 350000
MAX_FDE_RANGE = 4 * 1024 * 1024


def _section(sections, name):
    hits = [s for s in sections if s["name"] == name]
    if len(hits) != 1:
        raise ValueError("missing or duplicate " + name)
    return hits[0]


def _va_to_file(segments, va):
    hits = [seg["offset"] + va - seg["vaddr"] for seg in segments
            if seg["vaddr"] <= va < seg["vaddr"] + seg["size"]]
    return hits[0] if len(hits) == 1 else None


def _encoded(blob, off, encoding, header):
    if encoding == 0xff or encoding & 0x80:
        raise ValueError("unsupported omitted or indirect EH encoding")
    form = encoding & 0xf
    types = {2: "<H", 3: "<I", 4: "<Q", 10: "<h", 11: "<i", 12: "<q"}
    if form not in types:
        raise ValueError("unsupported fixed EH encoding format")
    fmt = types[form]
    size = struct.calcsize(fmt)
    if off < 0 or off + size > len(blob):
        raise ValueError("EH encoded field outside file")
    value = struct.unpack_from(fmt, blob, off)[0]
    application = encoding & 0x70
    if application == 0x10:  # pcrel
        value += header["addr"] + off - header["offset"]
    elif application == 0x30:  # datarel
        value += header["addr"]
    elif application != 0:
        raise ValueError("unsupported relative EH encoding")
    return value, off + size


def _uleb(blob, at, stop):
    value, shift = 0, 0
    for _ in range(10):
        if at >= stop:
            raise ValueError("truncated LEB128")
        char = blob[at]
        at += 1
        value |= (char & 0x7f) << shift
        if not char & 0x80:
            return value, at
        shift += 7
    raise ValueError("oversized LEB128")


def _sleb(blob, at, stop):
    value, shift = 0, 0
    for _ in range(10):
        if at >= stop:
            raise ValueError("truncated signed LEB128")
        char = blob[at]
        at += 1
        value |= (char & 0x7f) << shift
        shift += 7
        if not char & 0x80:
            if char & 0x40:
                value -= 1 << shift
            return value, at
    raise ValueError("oversized signed LEB128")


def parse_hdr(blob, sections):
    header = _section(sections, ".eh_frame_hdr")
    start, limit = header["offset"], header["offset"] + header["size"]
    if start < 0 or start + 4 > limit:
        raise ValueError("short .eh_frame_hdr")
    version, frame_encoding, count_encoding, table_encoding = blob[start:start+4]
    if version != 1:
        raise ValueError("unsupported .eh_frame_hdr version")
    if (frame_encoding & 0x80 or count_encoding & 0x80 or
            table_encoding & 0x80):
        raise ValueError("unsupported indirect EH frame table")
    frame_va, at = _encoded(blob, start + 4, frame_encoding, header)
    count, at = _encoded(blob, at, count_encoding, header)
    if count < 1 or count > MAX_FDE_ENTRIES:
        raise ValueError("unexpected EH frame table size")
    starts, fdes = [], []
    for _ in range(count):
        loc, at = _encoded(blob, at, table_encoding, header)
        fde, at = _encoded(blob, at, table_encoding, header)
        if loc < 0 or fde < 0 or (starts and loc <= starts[-1]):
            raise ValueError("unordered or invalid FDE table")
        starts.append(loc)
        fdes.append(fde)
    if at > limit:
        raise ValueError("EH frame index exceeds section")
    return {"start_vas": starts, "fde_vas": fdes,
            "eh_frame_pointer_va": frame_va, "fde_entries": count,
            "header_encodings": [frame_encoding, count_encoding, table_encoding]}


def _cie_encoding(blob, offset, sec):
    lo, hi = sec["offset"], sec["offset"] + sec["size"]
    if not lo <= offset < hi - 12:
        raise ValueError("CIE outside .eh_frame")
    length = struct.unpack_from("<I", blob, offset)[0]
    if length in (0, 0xffffffff) or length > 4096 or offset+4+length > hi:
        raise ValueError("invalid CIE length")
    if struct.unpack_from("<I", blob, offset+4)[0] != 0:
        raise ValueError("FDE does not reference a CIE")
    end = offset + 4 + length
    version = blob[offset+8]
    if version not in (1, 3, 4):
        raise ValueError("unsupported CIE version")
    at = offset + 9
    zero = blob.find(b"\0", at, min(end, at + 48))
    if zero < 0:
        raise ValueError("unterminated CIE augmentation")
    augmentation = blob[at:zero].decode("ascii")
    at = zero + 1
    _, at = _uleb(blob, at, end)  # code alignment
    _, at = _sleb(blob, at, end)  # data alignment
    if version == 1:
        at += 1
    else:
        _, at = _uleb(blob, at, end)
    if at > end:
        raise ValueError("invalid CIE return-address register")
    if not augmentation.startswith("z"):
        return 0x00  # DW_EH_PE_absptr, handled separately if needed.
    aug_len, at = _uleb(blob, at, end)
    aug_end = at + aug_len
    if aug_end > end:
        raise ValueError("invalid CIE augmentation bounds")
    encoding = 0x00
    for character in augmentation[1:]:
        if character in ("R", "L"):
            if at >= aug_end:
                raise ValueError("truncated CIE augmentation encoding")
            if character == "R":
                encoding = blob[at]
            at += 1
        elif character == "P":
            if at >= aug_end:
                raise ValueError("truncated CIE personality")
            personality = blob[at]
            at += 1
            # An indirect personality encoding still has the same encoded
            # field width. Never dereference the personality pointer.
            _, at = _encoded(blob, at, personality & 0x7f, {
                "addr":sec["addr"], "offset":sec["offset"]
            })
        elif character == "S":
            pass
        else:
            raise ValueError("unsupported CIE augmentation character")
    return encoding


def fde_coverage(blob, sections, segments, index, position):
    frame = _section(sections, ".eh_frame")
    fde_va = index["fde_vas"][position]
    if not frame["addr"] <= fde_va < frame["addr"] + frame["size"]:
        raise ValueError("FDE pointer outside .eh_frame")
    off = frame["offset"] + fde_va - frame["addr"]
    if off + 16 > frame["offset"] + frame["size"]:
        raise ValueError("truncated FDE record")
    length = struct.unpack_from("<I", blob, off)[0]
    if length == 0 or length == 0xffffffff or length > MAX_FDE_RANGE or \
            off + 4 + length > frame["offset"] + frame["size"]:
        raise ValueError("invalid FDE length")
    pointer_field = off + 4
    delta = struct.unpack_from("<I", blob, pointer_field)[0]
    if not delta or delta > pointer_field - frame["offset"]:
        raise ValueError("invalid CIE delta")
    cie = pointer_field - delta
    encoding = _cie_encoding(blob, cie, frame)
    if (encoding & 0xf) not in (2, 3, 4, 10, 11, 12):
        raise ValueError("unsupported original FDE encoding")
    initial, at = _encoded(blob, off + 8, encoding, frame)
    # In .eh_frame, address_range uses the same integer format as the
    # FDE initial_location but no relative base.
    range_value, at = _encoded(blob, at, encoding & 0x0f, frame)
    if initial != index["start_vas"][position] or not 0 < range_value <= MAX_FDE_RANGE:
        raise ValueError("FDE boundaries disagree with .eh_frame_hdr")
    if _va_to_file(segments, initial) is None:
        raise ValueError("unmapped original FDE start")
    return {"start_va":initial, "end_va_exclusive": initial+range_value,
            "fde_va": fde_va, "range_bytes":range_value,
            "original_unwind_encoding":encoding}


def _original_code_anchor_sites(reference_report):
    return sorted({
        ref["site_instruction_va"]
        for row in reference_report.get("labels", [])
        if _is_executor_label(row)
        for ref in row["instruction_sites"]
    })


def find_executor_unwind_frames(blob, reference_report):
    sections = parse_sections(blob)
    segments = elf_segments(blob)
    if not sections:
        return {"status":"ORIGINAL_UNWIND_SECTION_HEADERS_MISSING",
                "exact_fde_coverage_count":0,"mapped_opcodes":0}
    anchors = _original_code_anchor_sites(reference_report)
    if len(anchors) > 12:
        raise ValueError("too many original executor source anchors")
    index = parse_hdr(blob, sections)
    frame = _section(sections, ".eh_frame")
    if index["eh_frame_pointer_va"] != frame["addr"]:
        raise ValueError("EH index points to unexpected frame section")
    results = []
    for anchor in anchors:
        position = bisect_right(index["start_vas"], anchor) - 1
        if position < 0:
            results.append({"source_instruction_va":anchor,
                            "status":"NO_PRECEDING_UNWIND_FDE"})
            continue
        try:
            coverage = fde_coverage(blob,sections,segments,index,position)
        except ValueError as exc:
            results.append({"source_instruction_va":anchor,
                            "status":"UNWIND_RECORD_NOT_VERIFIED",
                            "reason":str(exc)})
            continue
        inside = coverage["start_va"] <= anchor < coverage["end_va_exclusive"]
        results.append({
            "source_instruction_va":anchor,
            "status":"VALIDATED_ORIGINAL_UNWIND_COVERAGE" if inside else
                     "NOT_WITHIN_PRECEDING_FDE",
            "unwind_coverage":coverage,
        })
    return {
        "status":"ORIGINAL_CFI_FDE_COVERAGE_ONLY_NOT_DISPATCH_PROOF",
        "fde_index_entries":index["fde_entries"],
        "eh_frame_hdr_encodings":index["header_encodings"],
        "executor_source_anchors":len(results),
        "exact_fde_coverage_count":sum(
            row["status"]=="VALIDATED_ORIGINAL_UNWIND_COVERAGE"
            for row in results),
        "sites":results,
        "mapped_opcodes":0,
        "original_import_authorized":False,
        "limitations": (
            "CIE/FDE-covered code ranges are authenticated unwinding regions, "
            "not independent proof of a C++ method name, constructor dispatch, "
            "or numeric opcode-to-handler semantics."
        ),
    }


def summarize_verified_fde_instructions(blob, frame_report):
    """Analyze EXACT original unwind-covered executable bytes, not +/-4KiB.

    Counts classes, branches, and small comparisons only. A CFI covered range
    is not proof of a native handler name, constructor or opcode meaning.
    """
    sections = parse_sections(blob)
    segments = elf_segments(blob)
    distinct = {}
    for row in frame_report.get("sites", ()):
        if row.get("status") != "VALIDATED_ORIGINAL_UNWIND_COVERAGE":
            continue
        coverage = row["unwind_coverage"]
        distinct[(coverage["start_va"], coverage["end_va_exclusive"])] = coverage
    if len(distinct) > 12:
        raise ValueError("too many distinct original executor FDE code regions")
    code = []
    for (start_va, end_va), coverage in sorted(distinct.items()):
        start = _va_to_file(segments, start_va)
        length = end_va - start_va
        if start is None or length <= 0 or length > MAX_FDE_RANGE or length % 4:
            raise ValueError("unmapped or unaligned FDE code range")
        exec_sections = [x for x in sections
                         if x["flags"] & 4 and x["type"] == 1
                         and x["addr"] <= start_va and
                         end_va <= x["addr"] + x["size"]]
        if len(exec_sections) != 1:
            raise ValueError("unwind FDE range is not uniquely in ELF executable code")
        from collections import Counter
        kinds, small_comparisons = Counter(), Counter()
        calls = []
        conditional = []
        indirect = []
        internal_branches = 0
        outside_branches = 0
        for off in range(start, start + length, 4):
            word = struct.unpack_from("<I", blob, off)[0]
            va = start_va + off - start
            kind, value = _decode_control(word, va)
            if kind is None:
                continue
            kinds[kind] += 1
            if kind == "CMP_IMMEDIATE" and isinstance(value, int) and 0 <= value <= 256:
                small_comparisons[value] += 1
            if kind == "CALL_DIRECT":
                if len(calls) < 60:
                    calls.append({"from_va":va,"to_va":value})
            if kind in ("BRANCH_DIRECT", "BRANCH_CONDITIONAL",
                        "BRANCH_COMPARE_ZERO", "BRANCH_BIT_TEST"):
                if start_va <= value < end_va:
                    internal_branches += 1
                else:
                    outside_branches += 1
                if kind != "BRANCH_DIRECT" and len(conditional) < 48:
                    conditional.append({"source_va":va,"target_va":value,
                                        "kind":kind})
            if kind in ("CALL_INDIRECT", "BRANCH_INDIRECT") and len(indirect) < 32:
                indirect.append({"instruction_va":va,"kind":kind})
        code.append({
            "validated_unwind_start_va":start_va,
            "validated_unwind_end_va_exclusive":end_va,
            "instruction_word_count":length // 4,
            "instruction_class_counts":dict(kinds),
            "immediate_comparisons_up_to_256":dict(sorted(small_comparisons.items())),
            "direct_call_count":kinds.get("CALL_DIRECT",0),
            "direct_call_sites":calls,
            "direct_call_sites_truncated":kinds.get("CALL_DIRECT",0)>len(calls),
            "conditional_branch_sites":conditional,
            "conditional_branch_sites_truncated":
                sum(kinds.get(k,0) for k in ("BRANCH_CONDITIONAL",
                     "BRANCH_COMPARE_ZERO","BRANCH_BIT_TEST"))>len(conditional),
            "indirect_call_or_branch_sites":indirect,
            "branches_within_region":internal_branches,
            "branches_outside_region":outside_branches,
            "original_native_opcode_mapping_proven":False,
        })
    return {
        "status":"EXACT_CFI_REGION_INSTRUCTION_CLASS_METADATA_NO_OPCODE_PROOF",
        "distinct_verified_unwind_regions":len(code),
        "regions":code,
        "verified_numeric_opcode_handler_pairs":0,
        "import_authorized":False,
        "limitations":(
            "Only decoded instruction-class, comparison and branch-target metadata "
            "within exact FDE coverage. No def-use/SSA, original factory path "
            "validation, constructor symbols or executable story playback proof."
        ),
    }
