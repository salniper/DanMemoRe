#!/usr/bin/env python3
"""Check modeled paths to earlier original AArch64 stack stores, fail closed.

Consumes only SHA-pinned original CFI/CFG stack provenance metadata. Follows
the bounded B/B.cond/CBZ/TBZ model to see whether a given store can precede
the associated SP-relative load without a *recognized* intervening write.
Tracks the stored source register's recognized prior writers, not its value.
The AArch64 XZR source is explicitly zero, never a pointer. This is NOT
full SSA, runtime memory, a proven object/vtable, or game command mapping.
Never prints game bytes, ciphertext, keys, dialogue, or executable content.
"""
from __future__ import annotations

from collections import deque
import struct

from inspect_elf_novel_xrefs import elf_segments
from inspect_native_novel_elf_sections import parse_sections
from inspect_native_novel_unwind import _va_to_file
from inspect_native_novel_cfg_paths import _cfg, _first_writers_on_cfg_paths
from inspect_native_novel_indirect_calls import _register_writer
from inspect_native_novel_stack_slots import (_stack_deltas, _stack_write,
                                               MAX_TRACKED_QUERIES)

MAX_STORES_PER_QUERY = 48
MAX_REPORTED_WRITERS = 12


def _compatible_store(word, source, byte_offset):
    return any(
        row["register"] == source and row["offset"] == byte_offset
        for row in _stack_write(word)
    )


def _suffix_without_recognized_clobber(blob, start_off, graph, sp_deltas,
                                       store_idx, load_idx, normalized_slot):
    """Test graph paths from after store to load, blocking matching stores.

    False means no path in the supported FDE CFG; True means a
    syntactic path exists, NOT that physical runtime memory is known.
    """
    successor = graph["successor"]
    pending = deque((n, 0) for n in successor[store_idx])
    visited = set()
    traversed = 0
    while pending:
        node, branch_steps = pending.popleft()
        if node in visited:
            continue
        visited.add(node)
        if node == load_idx:
            return {"modeled_unclobbered_path": True,
                    "visited_instructions": len(visited),
                    "branch_or_merge_steps": branch_steps}
        word = struct.unpack_from("<I", blob, start_off + node * 4)[0]
        writes = _stack_write(word)
        if writes:
            variants = sp_deltas[node]
            if len(variants) != 1 or None in variants:
                # Unknown stack base could clobber the same slot.
                continue
            delta = next(iter(variants))
            if any(delta + w["offset"] == normalized_slot for w in writes):
                continue
        traversed += 1
        if traversed > graph["instruction_word_count"]:
            raise ValueError("unbounded original FDE successor graph")
        next_steps = branch_steps + (len(successor[node]) > 1)
        pending.extend((child, next_steps) for child in successor[node])
    return {"modeled_unclobbered_path": False,
            "visited_instructions": len(visited),
            "branch_or_merge_steps": None}


def inspect_stack_store_paths(blob, frame_report, precise_report, cfg_report,
                              stack_report):
    if (frame_report.get("status") !=
            "ORIGINAL_CFI_FDE_COVERAGE_ONLY_NOT_DISPATCH_PROOF"
            or precise_report.get("status") !=
            "EXACT_CFI_REGION_INSTRUCTION_CLASS_METADATA_NO_OPCODE_PROOF"
            or cfg_report.get("status") !=
            "ORIGINAL_FDE_CFG_REACHING_WRITER_CANDIDATES_ONLY"
            or stack_report.get("status") !=
            "ORIGINAL_CFG_STACK_STORE_PROVENANCE_CANDIDATES_ONLY"):
        raise ValueError("authenticated original CFI CFG stack reports required")
    queries = stack_report.get("queried_sources")
    if not isinstance(queries, list) or len(queries) > MAX_TRACKED_QUERIES:
        raise ValueError("unbounded original stack source queries")
    verified = {
        (item["unwind_coverage"]["start_va"],
         item["unwind_coverage"]["end_va_exclusive"])
        for item in frame_report.get("sites", [])
        if item.get("status") == "VALIDATED_ORIGINAL_UNWIND_COVERAGE"
    }
    segments, sections = elf_segments(blob), parse_sections(blob)
    regions = {}
    for region in precise_report.get("regions", []):
        a, b = region["validated_unwind_start_va"], region["validated_unwind_end_va_exclusive"]
        executable = [s for s in sections if s["type"] == 1 and s["flags"] & 4
                      and s["addr"] <= a and b <= s["addr"] + s["size"]]
        offset = _va_to_file(segments, a)
        if (a,b) not in verified or len(executable) != 1 or offset is None:
            raise ValueError("stack store does not belong to validated executable CFI")
        graph = _cfg(blob, executable[0], a, b, offset)
        deltas = _stack_deltas(blob, offset, graph)
        regions[(a,b)] = (offset, graph, deltas)
    results=[]
    for query in queries:
        load_va = query.get("source_writer_va")
        call_va = query.get("call_va")
        if not isinstance(load_va, int) or not isinstance(call_va, int):
            raise ValueError("invalid original stack source addresses")
        bounds=[(a,b) for a,b in regions if a <= load_va < b and a <= call_va < b]
        if len(bounds) != 1:
            raise ValueError("original stack source outside uniquely verified FDE")
        a,b=bounds[0]
        off,graph,deltas=regions[(a,b)]
        load_idx=(load_va-a)//4
        if load_va%4 or call_va%4 or load_idx not in graph["entry_reachable_indices"]:
            raise ValueError("original load not reachable/aligned in supported CFG")
        candidates = query.get("known_store_candidates", [])
        if not isinstance(candidates,list) or len(candidates)>MAX_STORES_PER_QUERY:
            raise ValueError("unbounded original stores")
        if candidates and query.get("kind") != "STACK_SLOT_VALUE_READ":
            raise ValueError("no store can prove address-of-stack object value")
        normalized=query.get("entry_sp_normalized_byte_offset")
        store_rows=[]
        for original in candidates:
            store_va=original.get("store_va")
            reg=original.get("stored_register")
            byte_offset=original.get("sp_relative_byte_offset_at_store")
            if (not isinstance(store_va,int) or not a<=store_va<load_va
                    or (store_va-a)%4 or not isinstance(reg,int)
                    or not 0 <= reg <= 31 or not isinstance(byte_offset,int)):
                raise ValueError("invalid original candidate stack store")
            idx=(store_va-a)//4
            word=struct.unpack_from("<I", blob, off+idx*4)[0]
            if (idx not in graph["entry_reachable_indices"]
                    or not _compatible_store(word, reg, byte_offset)):
                raise ValueError("unreachable/forged original stack store source")
            sp_values=deltas[idx]
            if (not isinstance(normalized,int) or len(sp_values)!=1
                    or None in sp_values
                    or next(iter(sp_values))+byte_offset!=normalized):
                raise ValueError("original store/load normalized SP slot differs")
            # Distinguish known constant-zero stores from opaque saved pointers.
            if reg == 31:
                source={"kind":"XZR_CONSTANT_ZERO_NOT_A_VTABLE",
                        "candidate_register_writers":[],
                        "entry_path_without_register_writer":False}
            else:
                prev = _first_writers_on_cfg_paths(blob,off,graph,idx,reg)
                source={
                    "kind":"REGISTER_VALUE_UNKNOWN_CFG_WRITER_CANDIDATES",
                    "candidate_register_writers":[{
                        "writer_va":a+i*4,
                        "writer_kind":w["kind"],
                        "source_register":w.get("source",w.get("base")),
                        "byte_offset":w.get("byte_offset"),
                        "immediate":w.get("immediate"),
                    } for i,w in prev["first_writers"][:MAX_REPORTED_WRITERS]],
                    "candidate_writers_truncated":
                        len(prev["first_writers"])>MAX_REPORTED_WRITERS,
                    "entry_path_without_register_writer":
                        prev["reached_entry_without_recognized_writer"],
                }
            suffix = _suffix_without_recognized_clobber(
                blob,off,graph,deltas,idx,load_idx,normalized)
            store_rows.append({
                "store_va":store_va,
                "stored_register":reg,
                "store_source":source,
                "modeled_entry_reaches_store":True,
                "modeled_path_to_load_without_recognized_rewrite":
                    suffix["modeled_unclobbered_path"],
                "path_model_visited_words":suffix["visited_instructions"],
                "runtime_store_execution_verified":False,
            })
        results.append({
            "call_va":call_va,"source_load_va":load_va,
            "normalized_sp_offset":normalized,
            "recognized_candidate_stores":len(store_rows),
            "stores":store_rows,
            "all_candidates_unproven":True,
        })
    return {
        "status":"ORIGINAL_CFG_STACK_STORES_SOURCE_PATH_CANDIDATES_ONLY",
        "query_count":len(results),
        "source_paths":results,
        "stores_with_modeled_unclobbered_suffix":sum(
            bool(item["modeled_path_to_load_without_recognized_rewrite"])
            for q in results for item in q["stores"]),
        "confirmed_runtime_stack_objects":0,
        "confirmed_vtable_targets":0,
        "verified_numeric_opcode_handlers":0,
        "import_authorized":False,
        "limitations":(
            "CFG branch semantics and SP normalization are modeled only for a "
            "restricted AArch64 instruction subset. Register writers do not "
            "establish SSA dominance or actual values; unrecognized memory "
            "clobbers, aliases, exceptions and other FDE entries may change "
            "the slot. XZR does encode constant zero, not a vtable. No gameplay "
            "execution or reference-MD5 exception is authorized."
        ),
    }
