#!/usr/bin/env python3
"""Locate direct original ARM64 call sites entering the executor-source FDE.

The target is a SHA-pinned original ELF CFI/FDE region containing
NovelCommandExecuter C++ source-name xrefs, NOT a proven C++ symbol.
Scan only SHF_EXECINSTR AArch64 instructions for BL or tail B entering
the *exact start* of that independently validated unwind region.
For callers with their own verified FDE, examine modeled CFG predecessors
for recognized incoming X1 register assignments. No runtime pointer values,
vtable identity, command opcode mapping, original bytes, keys or assets.
"""
from __future__ import annotations

from bisect import bisect_right
import struct

from inspect_elf_novel_xrefs import elf_segments, sign_extend
from inspect_native_novel_elf_sections import parse_sections
from inspect_native_novel_unwind import parse_hdr, fde_coverage, _section, _va_to_file
from inspect_native_novel_cfg_paths import _cfg, _first_writers_on_cfg_paths

MAX_EXTERNAL_CALL_SITES = 160
MAX_CALLER_FDE_BYTES = 40000
MAX_WRITERS_PER_SITE = 12


def inspect_direct_original_executor_callers(blob, frames):
    if frames.get("status") != "ORIGINAL_CFI_FDE_COVERAGE_ONLY_NOT_DISPATCH_PROOF":
        raise ValueError("original executor CIE/FDE reference proof is required")
    valid = [r["unwind_coverage"] for r in frames.get("sites", [])
             if r.get("status") == "VALIDATED_ORIGINAL_UNWIND_COVERAGE"]
    if not valid or len({(r["start_va"],r["end_va_exclusive"]) for r in valid}) != 1:
        raise ValueError("expected exactly one original executor-source unwind region")
    exact_start = valid[0]["start_va"]
    exact_stop = valid[0]["end_va_exclusive"]
    segments,sections=elf_segments(blob),parse_sections(blob)
    text_sections=[s for s in sections if s["type"]==1 and s["flags"]&4
                   and s["size"]>0]
    if not text_sections:
        raise ValueError("missing executable code section in original ELF")
    hits=[]
    words_checked=0
    for sec in text_sections:
        if sec["offset"]%4 or sec["addr"]%4 or sec["size"]%4:
            raise ValueError("unaligned AArch64 executable section")
        for off in range(sec["offset"],sec["offset"]+sec["size"],4):
            word=struct.unpack_from("<I",blob,off)[0]
            opcode=word & 0xfc000000
            if opcode not in (0x94000000,0x14000000):
                continue
            source=sec["addr"]+off-sec["offset"]
            target=source+(sign_extend(word&0x3ffffff,26)<<2)
            if target != exact_start or exact_start <= source < exact_stop:
                continue
            hits.append({"site_va":source,
                         "kind":"DIRECT_BL" if opcode==0x94000000
                                else "DIRECT_B_TAIL_JUMP_CANDIDATE"})
            if len(hits)>MAX_EXTERNAL_CALL_SITES:
                raise ValueError("unbounded original external call-site count")
        words_checked+=sec["size"]//4
    index=parse_hdr(blob,sections)
    eh=_section(sections,".eh_frame")
    if index["eh_frame_pointer_va"]!=eh["addr"]:
        raise ValueError("original header does not point to verified .eh_frame")
    candidates=[]
    for hit in hits:
        va=hit["site_va"]
        position=bisect_right(index["start_vas"],va)-1
        record={"site_va":va,"kind":hit["kind"],
                "original_executor_fde_entry_va":exact_start,
                "caller_elf_unwind_status":"NO_VERIFIED_CALLER_FDE",
                "caller_fde_start_va":None,
                "recognized_X1_writer_candidates":[],
                "incoming_X1_value_verified":False}
        if position < 0:
            candidates.append(record)
            continue
        try:
            caller=fde_coverage(blob,sections,segments,index,position)
        except ValueError:
            record["caller_elf_unwind_status"]="CALLER_FDE_INVALID"
            candidates.append(record)
            continue
        a,b=caller["start_va"],caller["end_va_exclusive"]
        matches=[s for s in text_sections if s["addr"]<=a and b<=s["addr"]+s["size"]]
        if not(a<=va<b) or len(matches)!=1:
            record["caller_elf_unwind_status"]="CALLER_NOT_WITHIN_EXECUTABLE_FDE"
            candidates.append(record)
            continue
        record["caller_fde_start_va"]=a
        record["caller_fde_end_va_exclusive"]=b
        length=b-a
        if length>MAX_CALLER_FDE_BYTES:
            record["caller_elf_unwind_status"]="VERIFIED_FDE_TOO_LARGE_FOR_BOUNDED_CFG"
            candidates.append(record)
            continue
        start_off=_va_to_file(segments,a)
        if start_off is None or length%4:
            raise ValueError("verified original caller code is not aligned")
        graph=_cfg(blob,matches[0],a,b,start_off)
        index_at=(va-a)//4
        if index_at not in graph["entry_reachable_indices"]:
            record["caller_elf_unwind_status"]="CALLER_SITE_NOT_MODELED_ENTRY_REACHABLE"
            candidates.append(record)
            continue
        sources=_first_writers_on_cfg_paths(blob,start_off,graph,index_at,1)
        record["caller_elf_unwind_status"]="ORIGINAL_CALLER_FDE_AND_CFG_VERIFIED"
        record["recognized_X1_writer_candidates"]=[{
            "writer_va":a+i*4,"writer_kind":w["kind"],
            "from_register":w.get("source",w.get("base")),
            "immediate":w.get("immediate"),
            "byte_offset":w.get("byte_offset"),
        } for i,w in sources["first_writers"][:MAX_WRITERS_PER_SITE]]
        record["more_X1_writers_not_displayed"]=len(sources["first_writers"])>MAX_WRITERS_PER_SITE
        record["entry_path_without_recognized_X1_writer"]=sources[
            "reached_entry_without_recognized_writer"]
        # Exactly one additional syntactic copy-source hop. An incoming
        # argument register without an earlier recognized write remains
        # an unknown original parameter, not a concrete game object.
        secondary=[]
        for i,writer in sources["first_writers"][:MAX_WRITERS_PER_SITE]:
            source_reg=writer.get("source")
            if writer.get("kind")!="COPY_REGISTER" or not isinstance(source_reg,int) or not 0<=source_reg<=30:
                continue
            prior=_first_writers_on_cfg_paths(blob,start_off,graph,i,source_reg)
            secondary.append({
                "X1_copy_va":a+i*4,
                "copied_from_register":source_reg,
                "prior_register_writers":[{
                    "writer_va":a+j*4,"kind":w["kind"],
                    "source_register":w.get("source",w.get("base")),
                    "byte_offset":w.get("byte_offset"),
                    "immediate":w.get("immediate"),
                } for j,w in prior["first_writers"][:MAX_WRITERS_PER_SITE]],
                "more_prior_writers_not_displayed":
                    len(prior["first_writers"])>MAX_WRITERS_PER_SITE,
                "possible_incoming_argument_without_prior_writer":
                    prior["reached_entry_without_recognized_writer"],
                "actual_register_value_verified":False,
            })
        record["copied_X1_source_register_traces"]=secondary
        candidates.append(record)
    return {
        "status":"ORIGINAL_EXECUTOR_FDE_DIRECT_CALLER_X1_SYNTAX_ONLY",
        "source_code_words_checked":words_checked,
        "original_executor_source_fde_entry_va":exact_start,
        "direct_external_call_or_tail_jump_sites":len(candidates),
        "direct_bl_sites":sum(x["kind"]=="DIRECT_BL" for x in candidates),
        "tail_b_candidate_sites":sum(x["kind"]=="DIRECT_B_TAIL_JUMP_CANDIDATE"
                                     for x in candidates),
        "call_sites_with_original_fde_and_cfg":sum(
            x["caller_elf_unwind_status"]=="ORIGINAL_CALLER_FDE_AND_CFG_VERIFIED"
            for x in candidates),
        "candidate_callers":candidates,
        "original_X1_runtime_object_verified":False,
        "original_vtable_targets_verified":0,
        "original_opcode_handler_mappings_verified":0,
        "original_import_authorized":False,
        "limitations":(
            "An external BL/B to the original FDE start is code-address evidence, "
            "not a verified named C++ createNovel call. X1 writers are modeled "
            "CFG candidates and may be invalidated by unrecognized register "
            "writes or non-modeled control paths. No runtime object or opcode "
            "handler identity is established."
        )
    }
