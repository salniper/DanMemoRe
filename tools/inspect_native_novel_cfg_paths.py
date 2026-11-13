#!/usr/bin/env python3
"""Path-aware *candidate* reaching-writer evidence in original ARM64 executor.

Builds an internal bounded CFG from recognized AArch64 B/B.cond/CBZ/TBZ,
fallthrough, BL/BLR, RET and BR inside SHA-pinned original ELF FDE ranges.
Per original BLR object-source register, walks predecessor edges backwards
until the first recognized writer on each path. Does not cover unrecognized
register writes, memory aliases, indirect computed jumps, external incoming
edges, exceptional control flow, or actual runtime register values.

No graph result can approve asset import, original vtable identity or map
the owner's numeric story opcode to a constructor.
"""
from __future__ import annotations

from collections import Counter, deque
import struct

from inspect_elf_novel_xrefs import elf_segments
from inspect_native_novel_elf_sections import parse_sections
from inspect_native_novel_executor_flow import _decode_control
from inspect_native_novel_indirect_calls import _register_writer
from inspect_native_novel_unwind import _va_to_file

MAX_CFG_INSTRUCTIONS = 12000
MAX_REACHABLE_WRITERS_PER_SITE = 48


def _cfg(blob, section, start_va, end_va, start_off):
    n = (end_va - start_va) // 4
    if not 0 < n <= MAX_CFG_INSTRUCTIONS:
        raise ValueError("original FDE CFG is outside instruction safety bounds")
    successor = [set() for _ in range(n)]
    calls = 0
    external_edges = 0
    branch_types = Counter()
    for idx in range(n):
        off = start_off + idx * 4
        word = struct.unpack_from("<I", blob, off)[0]
        pc = start_va + idx * 4
        kind, target = _decode_control(word, pc)
        if kind in ("CALL_DIRECT", "CALL_INDIRECT"):
            calls += 1
        if kind in ("RETURN", "BRANCH_INDIRECT"):
            continue
        if kind in ("BRANCH_DIRECT", "BRANCH_CONDITIONAL",
                    "BRANCH_COMPARE_ZERO", "BRANCH_BIT_TEST"):
            branch_types[kind] += 1
            if isinstance(target, int) and start_va <= target < end_va and (target-start_va) % 4 == 0:
                successor[idx].add((target-start_va)//4)
            else:
                external_edges += 1
            if kind == "BRANCH_DIRECT":
                continue
        if idx + 1 < n:
            successor[idx].add(idx+1)
    predecessor = [set() for _ in range(n)]
    for i, targets in enumerate(successor):
        for j in targets:
            predecessor[j].add(i)
    # Which instructions are reachable from the first word of the FDE?
    # An FDE may cover multiple entry points; absence here is NOT proof
    # original runtime cannot reach an instruction via an external edge.
    reached = set()
    pending = [0]
    while pending:
        idx = pending.pop()
        if idx in reached:
            continue
        reached.add(idx)
        pending.extend(successor[idx] - reached)
    return {
        "successor": successor,
        "predecessor": predecessor,
        "entry_reachable_indices": reached,
        "recognized_control_transfers": sum(branch_types.values()),
        "recognized_calls": calls,
        "edges_leaving_verified_FDE": external_edges,
        "reachable_instruction_words": len(reached),
        "instruction_word_count": n,
    }


def _first_writers_on_cfg_paths(blob, start_off, graph, target_index, register):
    if target_index <= 0 or not 0 <= register <= 30:
        return {"first_writers": [], "reached_entry_without_recognized_writer": True,
                "backward_visited_instructions": 0}
    reachable = graph["entry_reachable_indices"]
    if target_index not in reachable:
        return {"first_writers": [], "reached_entry_without_recognized_writer": True,
                "backward_visited_instructions": 0}
    pending = list(graph["predecessor"][target_index] & reachable)
    checked = set()
    results = []
    reached_entry = False
    while pending:
        i = pending.pop()
        if i in checked:
            continue
        checked.add(i)
        word = struct.unpack_from("<I", blob, start_off + i*4)[0]
        writer = _register_writer(word, start_off + i*4)
        if writer and writer["dest"] == register:
            if len(results) >= MAX_REACHABLE_WRITERS_PER_SITE:
                raise ValueError("too many original reaching-writer candidates")
            results.append((i, writer))
            continue
        if i == 0:
            reached_entry = True
        pending.extend((graph["predecessor"][i] & reachable)-checked)
    return {
        "first_writers": sorted(results,key=lambda x:x[0]),
        "reached_entry_without_recognized_writer": reached_entry,
        "backward_visited_instructions": len(checked),
    }


def inspect_cfg_object_paths(blob, frame_report, precise_report,
                             indirect_report, origin_report):
    if (frame_report.get("status") !=
            "ORIGINAL_CFI_FDE_COVERAGE_ONLY_NOT_DISPATCH_PROOF"
            or precise_report.get("status") !=
            "EXACT_CFI_REGION_INSTRUCTION_CLASS_METADATA_NO_OPCODE_PROOF"
            or indirect_report.get("status") !=
            "ORIGINAL_CFI_BLR_REGISTER_LOAD_HINTS_NO_DISPATCH_PROOF"
            or origin_report.get("status") !=
            "ORIGINAL_OBJECT_REGISTER_LINEAR_PROVENANCE_ONLY"):
        raise ValueError("authenticated original unwind and object metadata required")
    proven_ranges = {
        (s["unwind_coverage"]["start_va"],s["unwind_coverage"]["end_va_exclusive"])
        for s in frame_report.get("sites", [])
        if s.get("status") == "VALIDATED_ORIGINAL_UNWIND_COVERAGE"
    }
    indirect = indirect_report.get("sites", [])
    originals = origin_report.get("object_register_sources", [])
    if not isinstance(indirect,list) or not isinstance(originals,list) or len(indirect)>32 or len(indirect)!=len(originals):
        raise ValueError("invalid seven-call source-report shape")
    if origin_report.get("indirect_call_count") != len(indirect):
        raise ValueError("mismatched original source-report count")
    segments, sections = elf_segments(blob),parse_sections(blob)
    regions = {}
    for r in precise_report.get("regions", []):
        start,end=r["validated_unwind_start_va"],r["validated_unwind_end_va_exclusive"]
        if (start,end) not in proven_ranges:
            raise ValueError("unverified original executable FDE")
        executable=[s for s in sections if s["type"]==1 and s["flags"]&4
                    and s["addr"]<=start and end<=s["addr"]+s["size"]]
        start_off=_va_to_file(segments,start)
        if len(executable)!=1 or start_off is None or (end-start)%4:
            raise ValueError("CFG not uniquely within executable ELF section")
        regions[(start,end)] = (start_off, _cfg(blob,executable[0],start,end,start_off))
    rows=[]
    for call,original in zip(indirect,originals):
        va=call["call_instruction_va"]
        if va!=original.get("call_instruction_va"):
            raise ValueError("inconsistent original call addresses")
        match=[(a,b) for a,b in regions if a<=va<b]
        if len(match)!=1:
            raise ValueError("BLR address not in unique validated FDE")
        a,b=match[0]
        off,graph=regions[(a,b)]
        reg=original.get("object_source_register")
        load_va=original.get("first_load_instruction_va")
        if not isinstance(reg,int) or not 0<=reg<=30 or not isinstance(load_va,int) or not a<=load_va<va:
            rows.append({
                "call_va":va, "status":"UNKNOWN_ORIGINAL_OBJECT_SOURCE",
                "candidate_matches_cfg_path":False,"cfg_reaching_writer_count":0,
                "reaching_writer_samples":[],"original_object_identity_verified":False,
            })
            continue
        idx=(load_va-a)//4
        decoded=struct.unpack_from("<I",blob,off+idx*4)[0]
        w=_register_writer(decoded,load_va)
        if (w is None or w.get("kind")!="LOAD_POINTER_FROM_REGISTER"
                or w.get("base")!=reg or w.get("dest")!=call.get("call_target_register")
                or w.get("byte_offset")!=0):
            raise ValueError("original pointer load no longer authenticated at CFG site")
        reaches=_first_writers_on_cfg_paths(blob,off,graph,idx,reg)
        writers=reaches["first_writers"]
        writer_vas={a+i*4 for i,_ in writers}
        linear = original.get("origin_writer") or {}
        location=linear.get("instruction_va")
        matches=location in writer_vas
        status=(
            "MODELED_FDE_ENTRY_CANNOT_REACH_SOURCE_LOAD" if idx not in graph["entry_reachable_indices"]
            else "LINEAR_WRITER_NOT_A_CFG_FIRST_REACHING_CANDIDATE" if location is not None and not matches
            else "MULTIPLE_OR_ENTRY_REACHING_CANDIDATES" if len(writers)!=1 or reaches["reached_entry_without_recognized_writer"]
            else "SOLE_RECOGNIZED_CFG_FIRST_WRITER_NOT_PROVEN"
        )
        rows.append({
            "call_va":va,
            "source_object_register":reg,
            "first_object_load_va":load_va,
            "cfg_entry_reaches_call":((va-a)//4 in graph["entry_reachable_indices"]),
            "cfg_entry_reaches_first_load":(idx in graph["entry_reachable_indices"]),
            "linear_nearest_writer_va":location,
            "linear_nearest_writer_is_cfg_first_reaching_candidate":matches,
            "cfg_reaching_writer_count":len(writers),
            "cfg_entry_path_without_recognized_writer":
                reaches["reached_entry_without_recognized_writer"],
            "reaching_writer_samples":[{
                "writer_va":a+i*4,"kind":w["kind"],
                "from_register":w.get("source",w.get("base")),
                "load_byte_offset":w.get("byte_offset"),
                "immediate":w.get("immediate"),
            } for i,w in writers[:12]],
            "reaching_writer_samples_truncated":len(writers)>12,
            "status":status,
            "original_object_identity_verified":False,
        })
    return {
        "status":"ORIGINAL_FDE_CFG_REACHING_WRITER_CANDIDATES_ONLY",
        "validated_regions":len(regions),
        "cfg_instruction_counts":{str(a):g["instruction_word_count"]
                                  for (a,_),(off,g) in regions.items()},
        "cfg_entry_reachable_words":{str(a):g["reachable_instruction_words"]
                                     for (a,_),(off,g) in regions.items()},
        "cfg_internal_control_edges":{str(a):g["recognized_control_transfers"]
                                      for (a,_),(off,g) in regions.items()},
        "cfg_exiting_branch_edges":{str(a):g["edges_leaving_verified_FDE"]
                                    for (a,_),(off,g) in regions.items()},
        "call_sites_checked":len(rows),
        "source_register_paths":rows,
        "linear_nearest_writers_refuted_by_cfg":sum(
            r.get("status")=="LINEAR_WRITER_NOT_A_CFG_FIRST_REACHING_CANDIDATE"
            for r in rows),
        "original_vtable_pointer_values_verified":0,
        "original_opcode_handler_mappings_verified":0,
        "original_import_authorized":False,
        "limitations":(
            "CFG only models recognized B/BCOND/CBZ/TBZ and local fallthrough, "
            "and calls are assumed to return. No global CFG, exception/unwind "
            "edges, external FDE entries, indirect branch targets, comprehensive "
            "register-write decoding, SSA dominance, memory aliases or runtime "
            "vtable contents. Recognized first reaching writers are candidates, "
            "NOT actual object pointers or numeric opcode-handler proof."
        ),
    }
