#!/usr/bin/env python3
"""Conservative ARM64 indirect-call *syntax* near validated original FDE code.

No dynamic execution and no global CFG/SSA assumptions. A nearest preceding
writer is ONLY a textual instruction-neighborhood candidate: not a reaching
definition across branches, not an actual pointer value, not vtable proof,
not a numeric novel-command opcode -> constructor mapping.

Never exports original machine-code bytes, owner scripts or game keys.
"""
from __future__ import annotations

from collections import Counter
import struct

from inspect_elf_novel_xrefs import elf_segments, sign_extend
from inspect_native_novel_elf_sections import parse_sections
from inspect_native_novel_unwind import _va_to_file

MAX_REGION_BYTES = 1024 * 1024
MAX_SITES = 256
BACKTRACK_WORDS = 24
MAX_CONTEXT_SAMPLES = 9


def _register_writer(word, pc):
    """Whitelist unambiguous common 64-bit AArch64 register definitions."""
    rt = word & 31
    rn = (word >> 5) & 31
    if word & 0xffc00000 == 0xf9400000:  # LDR Xt,[Xn,#unsigned_imm]
        return {"kind": "LOAD_POINTER_FROM_REGISTER", "dest": rt,
                "base": rn, "byte_offset": ((word >> 10) & 0xfff) * 8}
    if word & 0xff000000 == 0x58000000:  # LDR Xt, PC-relative literal
        distance = sign_extend((word >> 5) & 0x7ffff, 19) << 2
        return {"kind": "LOAD_POINTER_FROM_LITERAL", "dest": rt,
                "literal_va": pc + distance}
    if word & 0x9f000000 == 0x90000000:  # ADRP Xd
        imm = (((word >> 5) & 0x7ffff) << 2) | ((word >> 29) & 3)
        value = (pc & ~4095) + (sign_extend(imm, 21) << 12)
        return {"kind": "PAGE_ADDRESS", "dest": rt, "page_va": value}
    if word & 0x9f000000 == 0x10000000:  # ADR Xd
        imm = (((word >> 5) & 0x7ffff) << 2) | ((word >> 29) & 3)
        return {"kind": "PC_RELATIVE_ADDRESS", "dest": rt,
                "address_va": pc + sign_extend(imm, 21)}
    if word & 0xff000000 == 0x91000000:  # ADD Xd,Xn,#imm
        immediate = (word >> 10) & 0xfff
        if (word >> 22) & 1:
            immediate <<= 12
        return {"kind": "ADD_REGISTER_IMMEDIATE", "dest": rt,
                "source": rn, "immediate": immediate}
    if word & 0xffe0ffe0 == 0xaa0003e0:  # MOV Xd,Xm (ORR alias)
        return {"kind": "COPY_REGISTER", "dest": rt,
                "source": (word >> 16) & 31}
    if word & 0xff800000 == 0xd2800000:  # MOVZ Xd,#imm,LSL shift
        return {"kind": "CONSTANT_REGISTER", "dest": rt,
                "immediate": ((word >> 5) & 0xffff) << (((word >> 21) & 3) * 16)}
    return None


def _control_barrier(word):
    # These breaks include BL, BLR, unconditional/conditional branches,
    # CBZ/TBZ family, BR and RET. They make nearest-writer confidence low.
    return bool(
        word & 0xfc000000 in (0x94000000, 0x14000000)
        or word & 0xff000010 == 0x54000000
        or word & 0x7e000000 in (0x34000000, 0x36000000)
        or word & 0xfffffc1f in (0xd63f0000, 0xd61f0000, 0xd65f0000)
    )


def _find_linear_writer(blob, start_off, caller_start, register):
    """Only the first syntactically recognizable earlier writer in 24 words."""
    lower = max(caller_start, start_off - 4 * BACKTRACK_WORDS)
    barriers = 0
    for off in range(start_off - 4, lower - 1, -4):
        word = struct.unpack_from("<I", blob, off)[0]
        if _control_barrier(word):
            barriers += 1
        writer = _register_writer(word, off)
        if writer and writer["dest"] == register:
            return {
                "nearest_writer_file_offset": off,
                "nearest_writer_kind": writer["kind"],
                "nearest_writer_register": register,
                "nearest_writer_source_register":
                    writer.get("base", writer.get("source")),
                "nearest_writer_byte_offset": writer.get("byte_offset"),
                "preceding_control_transfers_since_writer": barriers,
                "evidence_level": "LINEAR_SYNTAX_ONLY_NOT_REACHING_DEFINITION",
            }
    return {
        "nearest_writer_kind": "NONE_IN_BOUNDED_WINDOW",
        "nearest_writer_register": register,
        "preceding_control_transfers_since_writer": barriers,
        "evidence_level": "UNKNOWN_NOT_A_REGISTER_FLOW_PROOF",
    }


def inspect_original_indirect_calls(blob, frame_report, precise_report):
    if (frame_report.get("status") !=
            "ORIGINAL_CFI_FDE_COVERAGE_ONLY_NOT_DISPATCH_PROOF"
            or precise_report.get("status") !=
            "EXACT_CFI_REGION_INSTRUCTION_CLASS_METADATA_NO_OPCODE_PROOF"):
        raise ValueError("original CFI-backed code evidence mandatory")
    regions = precise_report.get("regions", [])
    if not 1 <= len(regions) <= 12:
        raise ValueError("invalid original executor regions")
    validated = {
        (item["unwind_coverage"]["start_va"],
         item["unwind_coverage"]["end_va_exclusive"])
        for item in frame_report.get("sites", [])
        if item.get("status") == "VALIDATED_ORIGINAL_UNWIND_COVERAGE"
    }
    sections = parse_sections(blob)
    segments = elf_segments(blob)
    sites = []
    kindcounts = Counter()
    for region in regions:
        first = region["validated_unwind_start_va"]
        last = region["validated_unwind_end_va_exclusive"]
        if (first, last) not in validated:
            raise ValueError("unverified original executor FDE region")
        length = last - first
        sect = [item for item in sections if item["type"] == 1
                and item["flags"] & 4 and item["addr"] <= first
                and last <= item["addr"] + item["size"]]
        offset = _va_to_file(segments, first)
        if (len(sect) != 1 or offset is None or offset % 4 or
                length <= 0 or length > MAX_REGION_BYTES or length % 4):
            raise ValueError("original indirect call region not exact executable")
        for at in range(offset, offset + length, 4):
            word = struct.unpack_from("<I", blob, at)[0]
            # BLR Xn only; BR and RET are not function calls.
            if word & 0xfffffc1f != 0xd63f0000:
                continue
            reg = (word >> 5) & 31
            if len(sites) >= MAX_SITES:
                raise ValueError("too many original indirect BLR sites")
            hint = _find_linear_writer(blob, at, offset, reg)
            # Syntactic two-load pattern only: LDR X8,[X8,#16]; BLR X8.
            # Query the nearest earlier observed writer of the *same* X8,
            # without claiming CFG reachability or identifying a vtable.
            prior = None
            two_load_shape = False
            if (hint["nearest_writer_kind"] == "LOAD_POINTER_FROM_REGISTER"
                    and hint["nearest_writer_source_register"] == reg
                    and hint.get("nearest_writer_file_offset") is not None):
                prior = _find_linear_writer(blob,
                                            hint["nearest_writer_file_offset"],
                                            offset, reg)
                two_load_shape = (
                    prior["nearest_writer_kind"] == "LOAD_POINTER_FROM_REGISTER"
                    and prior["preceding_control_transfers_since_writer"] == 0
                    and hint["preceding_control_transfers_since_writer"] == 0
                )
            kindcounts[hint["nearest_writer_kind"]] += 1
            sites.append({
                "call_instruction_va": first + at - offset,
                "call_target_register": reg,
                **hint,
                "earlier_register_writer_kind":
                    prior["nearest_writer_kind"] if prior else None,
                "earlier_register_writer_source":
                    prior.get("nearest_writer_source_register") if prior else None,
                "earlier_register_writer_byte_offset":
                    prior.get("nearest_writer_byte_offset") if prior else None,
                "two_pointer_loads_syntactically_adjacent_in_register":
                    two_load_shape,
                "resolved_function_target_va": None,
                "proven_virtual_dispatch": False,
                "original_novel_handler_verified": False,
            })
    total = sum(
        r["instruction_class_counts"].get("CALL_INDIRECT", 0)
        for r in regions
    )
    if total != len(sites):
        raise ValueError("original indirect-call counts disagree with code evidence")
    return {
        "status": "ORIGINAL_CFI_BLR_REGISTER_LOAD_HINTS_NO_DISPATCH_PROOF",
        "original_blr_call_sites": len(sites),
        "call_target_nearest_writer_kinds": dict(kindcounts),
        "two_load_virtual_call_shaped_sites": sum(
            x["two_pointer_loads_syntactically_adjacent_in_register"] for x in sites),
        "sites": sites,
        "verified_vtable_targets": 0,
        "verified_numeric_opcode_handler_mappings": 0,
        "original_import_authorized": False,
        "limitations": (
            "ARM64 BLR register and a preceding syntactic writer are NOT a "
            "reaching definition. The bounded scan does not follow CFG, "
            "relocations, memory, pointers, vtables, exceptions or register "
            "clobbers. Target and handler identity remain unproven."
        ),
    }
