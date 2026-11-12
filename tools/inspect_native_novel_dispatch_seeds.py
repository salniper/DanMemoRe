#!/usr/bin/env python3
"""Locate original novel-command source-path/function-string cross-references.

Find only AArch64 ADR or ADRP ... ADD references whose instruction sites
are within ELF SHF_EXECINSTR sections and whose targets are the **start**
of a zero-terminated original source-path or function name string.
Does not infer function entry, opcode dispatch, instruction semantics, or
ownership of an indirect call. Never dumps original native bytes.
"""
from __future__ import annotations

from collections import defaultdict
import json
import struct

from inspect_elf_novel_xrefs import elf_segments, map_offset, sign_extend
from inspect_native_novel_elf_sections import parse_sections

MAX_LABELS = 400
MAX_LABEL_SIZE = 384
MAX_REFERENCES_PER_LABEL = 32
ADRP_LOOKBACK_INSTRUCTIONS = 12


def _label_kind(text):
    if "/NovelCommand/Command/" in text and text.endswith(".cpp"):
        return "ORIGINAL_HANDLER_CPP_PATH"
    if "/NovelCommand/" in text and text.endswith(".cpp"):
        return "ORIGINAL_NOVEL_CPP_PATH"
    if ("NovelCommandExecuter::" in text
            or "DomainNovelCommand::" in text
            or "NovelCommandParam::" in text):
        return "ORIGINAL_PRETTY_FUNCTION_NAME"
    return None


def collect_original_labels(blob, segments, sections):
    found = {}
    for section in sections:
        if section["flags"] & 4 or section["type"] != 1:
            continue
        lo, hi = section["offset"], section["offset"] + section["size"]
        cursor = lo
        while True:
            match = blob.find(b"NovelCommand", cursor, hi)
            if match < 0:
                break
            cursor = match + len(b"NovelCommand")
            left = blob.rfind(b"\0", lo, match)
            right = blob.find(b"\0", match, min(hi, match + MAX_LABEL_SIZE + 1))
            if left < 0 or right < 0 or right - left - 1 > MAX_LABEL_SIZE:
                continue
            start = left + 1
            if start in found:
                continue
            raw = blob[start:right]
            if not raw or not all(32 <= byte <= 126 for byte in raw):
                continue
            label = raw.decode("ascii")
            kind = _label_kind(label)
            if kind is None:
                continue
            virtual = map_offset(segments, start)
            if virtual is None:
                continue
            if len(found) >= MAX_LABELS:
                raise ValueError("too many original source labels")
            found[start] = {
                "label": label, "kind": kind,
                "string_file_offset": start, "string_va": virtual,
            }
    return found


def _emit_reference(events, label, site, instruction, register, gap):
    events[label].append({
        "site_instruction_file_offset": site,
        "site_instruction_va": instruction,
        "pattern": register,
        "adrp_add_instruction_gap": gap,
    })


def scan_verified_code_references(blob, sections, labels):
    target_index = defaultdict(list)
    for row in labels.values():
        target_index[row["string_va"]].append(row["string_file_offset"])
    events = defaultdict(list)
    # Explicit ELF SHF_EXECINSTR sections, not broad PT_LOAD PF_X flags.
    executables = [sec for sec in sections
                   if sec["flags"] & 4 and sec["type"] == 1 and sec["size"] > 0]
    if not executables:
        raise ValueError("no original executable section")
    checked = 0
    for sec in executables:
        if (sec["offset"] % 4 or sec["addr"] % 4 or sec["size"] % 4):
            raise ValueError("unaligned executable section")
        # Most original Android text is contiguous. Keep ADRP per register
        # only for the last 12 instructions; this is *candidate* dataflow,
        # not a register-SSA or CFG proof.
        last_adrp = {}
        lo, hi = sec["offset"], sec["offset"] + sec["size"]
        for off in range(lo, hi, 4):
            word = struct.unpack_from("<I", blob, off)[0]
            pc = sec["addr"] + off - lo
            checked += 1
            if (word & 0x9f000000) == 0x10000000:  # ADR Xd, literal
                imm21 = (((word >> 5) & 0x7ffff) << 2) | ((word >> 29) & 3)
                target = pc + sign_extend(imm21, 21)
                for idx in target_index.get(target, ()):
                    _emit_reference(events, idx, off, pc, "ADR_DIRECT", 0)
            elif (word & 0x9f000000) == 0x90000000:  # ADRP Xd,page
                imm21 = (((word >> 5) & 0x7ffff) << 2) | ((word >> 29) & 3)
                page = (pc & ~4095) + (sign_extend(imm21, 21) << 12)
                last_adrp[word & 31] = (page, off)
            elif (word & 0xff000000) == 0x91000000:  # ADD Xd,Xn,#imm12
                rn = (word >> 5) & 31
                origin = last_adrp.get(rn)
                if origin is None:
                    continue
                page, adr_off = origin
                gap = (off - adr_off) // 4
                if not 1 <= gap <= ADRP_LOOKBACK_INSTRUCTIONS:
                    continue
                imm12 = (word >> 10) & 0xfff
                shift = 12 if ((word >> 22) & 1) else 0
                target = page + (imm12 << shift)
                for idx in target_index.get(target, ()):
                    _emit_reference(events, idx, off, pc, "ADRP_ADD_CANDIDATE", gap)
            # Ignore stale ADRP values beyond the bounded lookback.
            for reg, (_, site) in tuple(last_adrp.items()):
                if off - site >= 4 * ADRP_LOOKBACK_INSTRUCTIONS:
                    del last_adrp[reg]
    report = []
    for row in sorted(labels.values(), key=lambda item: item["string_file_offset"]):
        hits = events.get(row["string_file_offset"], [])
        report.append({
            **row,
            "instruction_site_count": len(hits),
            "instruction_sites": hits[:MAX_REFERENCES_PER_LABEL],
            "sites_truncated": len(hits) > MAX_REFERENCES_PER_LABEL,
        })
    return {
        "status": "ORIGINAL_EXECUTABLE_TO_NOVEL_METADATA_CANDIDATES_ONLY",
        "labels_checked": len(labels),
        "instruction_words_checked": checked,
        "original_source_labels_with_instruction_candidates":
            sum(bool(row["instruction_site_count"]) for row in report),
        "original_code_site_candidate_count":
            sum(row["instruction_site_count"] for row in report),
        "labels": report,
        "original_integer_opcode_dispatch_verified": False,
        "original_import_authorized": False,
        "limitations": (
            "Identifies potential code references to original source path and "
            "function-name literals; separated ADRP+ADD is register-heuristic "
            "without SSA, CFG or constructor linkage. Does NOT map numeric "
            "opcodes to handler constructors or prove playback."
        ),
    }


def inspect_original_dispatch_seeds(blob):
    segments = elf_segments(blob)
    sections = parse_sections(blob)
    if not sections:
        raise ValueError("missing original ELF section headers")
    labels = collect_original_labels(blob, segments, sections)
    if not labels:
        raise ValueError("no original NovelCommand source metadata")
    return scan_verified_code_references(blob, sections, labels)
