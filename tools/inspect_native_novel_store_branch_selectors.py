#!/usr/bin/env python3
"""Find *modeled* branch selectors between two original stack-store candidates.

Takes SHA-pinned original ELF and independently FDE-verified stack-store
provenance. Rebuilds the bounded intraprocedural CFG to look for branches
dominating both stores and whose two arms reach different first stores.
Only branch instruction syntax, addresses and register-writer metadata
are reported. Flags and runtime execution are NOT reconstructed.
No original native bytes, scripts, keys or opcode-handler mappings.
"""
from __future__ import annotations

from collections import deque
import struct

from inspect_elf_novel_xrefs import elf_segments
from inspect_native_novel_elf_sections import parse_sections
from inspect_native_novel_unwind import _va_to_file
from inspect_native_novel_cfg_paths import _cfg, _first_writers_on_cfg_paths
from inspect_native_novel_executor_flow import _decode_control
from inspect_native_novel_stack_slots import _stack_deltas, _stack_write

MAX_BRANCHES_PER_QUERY = 128
MAX_SELECTED_BRANCHES = 16
MAX_STORES = 8

AARCH64_CONDITION_CODES = (
    "EQ", "NE", "CS", "CC", "MI", "PL", "VS", "VC",
    "HI", "LS", "GE", "LT", "GT", "LE", "AL", "NV",
)


def _reaches(graph, source, destination, forbidden=frozenset()):
    if source in forbidden or destination in forbidden:
        return False
    pending=[source]
    visited=set()
    while pending:
        i=pending.pop()
        if i==destination:
            return True
        if i in visited or i in forbidden:
            continue
        visited.add(i)
        pending.extend(graph["successor"][i]-visited-forbidden)
    return False


def _first_store_encountered(graph, first, store_indices, load_index):
    pending=deque([first])
    seen=set()
    found=set()
    saw_load_without_candidate=False
    while pending:
        at=pending.popleft()
        if at in seen:
            continue
        seen.add(at)
        if at == load_index:
            saw_load_without_candidate=True
            continue
        if at in store_indices:
            found.add(store_indices[at])
            continue
        pending.extend(graph["successor"][at]-seen)
    return found, saw_load_without_candidate


def _branch_condition(word, kind):
    if kind == "BRANCH_CONDITIONAL":
        return {"kind":"NZCV_FLAG_CONDITION",
                "condition":AARCH64_CONDITION_CODES[word & 15],
                "tested_register":None, "tested_bit":None}
    if kind == "BRANCH_COMPARE_ZERO":
        is_nonzero=bool((word>>24)&1)
        return {"kind":"CBNZ" if is_nonzero else "CBZ",
                "condition":"register != 0" if is_nonzero else "register == 0",
                "tested_register":word&31,"tested_bit":None}
    if kind == "BRANCH_BIT_TEST":
        is_nonzero=bool((word>>24)&1)
        bit=((word>>31)&1)*32 + ((word>>19)&31)
        return {"kind":"TBNZ" if is_nonzero else "TBZ",
                "condition":"bit != 0" if is_nonzero else "bit == 0",
                "tested_register":word&31,"tested_bit":bit}
    raise ValueError("not a recognized conditional ARM64 branch")


def inspect_original_stack_store_branch_conditions(blob, frames, precise,
                                                    cfg_report, stack_report,
                                                    path_report):
    if (frames.get("status")!="ORIGINAL_CFI_FDE_COVERAGE_ONLY_NOT_DISPATCH_PROOF"
        or precise.get("status")!="EXACT_CFI_REGION_INSTRUCTION_CLASS_METADATA_NO_OPCODE_PROOF"
        or cfg_report.get("status")!="ORIGINAL_FDE_CFG_REACHING_WRITER_CANDIDATES_ONLY"
        or stack_report.get("status")!="ORIGINAL_CFG_STACK_STORE_PROVENANCE_CANDIDATES_ONLY"
        or path_report.get("status")!="ORIGINAL_CFG_STACK_STORES_SOURCE_PATH_CANDIDATES_ONLY"):
        raise ValueError("authenticated original CFI CFG store-path evidence required")
    valid={(r["unwind_coverage"]["start_va"],r["unwind_coverage"]["end_va_exclusive"])
           for r in frames.get("sites",[])
           if r.get("status")=="VALIDATED_ORIGINAL_UNWIND_COVERAGE"}
    source_paths=path_report.get("source_paths")
    if not isinstance(source_paths,list) or len(source_paths)>32:
        raise ValueError("invalid original stack-store path report")
    sections=parse_sections(blob)
    segments=elf_segments(blob)
    ranges={}
    for row in precise.get("regions",[]):
        a,b=row["validated_unwind_start_va"],row["validated_unwind_end_va_exclusive"]
        matches=[s for s in sections if s["type"]==1 and s["flags"]&4
                 and s["addr"]<=a and b<=s["addr"]+s["size"]]
        off=_va_to_file(segments,a)
        if (a,b) not in valid or len(matches)!=1 or off is None:
            raise ValueError("original CFI code range not independently authenticated")
        graph=_cfg(blob,matches[0],a,b,off)
        ranges[(a,b)]=(off,graph,_stack_deltas(blob,off,graph))
    results=[]
    for row in source_paths:
        stores=row.get("stores",[])
        if len(stores)<2:
            continue
        if len(stores)>MAX_STORES:
            raise ValueError("too many original alternative store candidates")
        load=row.get("source_load_va")
        call=row.get("call_va")
        bounds=[(a,b) for a,b in ranges if a<=load<b and a<=call<b]
        if len(bounds)!=1:
            raise ValueError("store selector load outside one validated original FDE")
        a,b=bounds[0]
        off,graph,deltas=ranges[(a,b)]
        load_idx=(load-a)//4
        incoming=deltas[load_idx]
        normalized=row.get("normalized_sp_offset")
        if not isinstance(normalized,int) or not incoming or (
                not 0<=load_idx<graph["instruction_word_count"]):
            raise ValueError("bad original normalized stack source")
        store_indices={}
        for store in stores:
            va=store.get("store_va")
            reg=store.get("stored_register")
            if not isinstance(va,int) or not a<=va<load or (va-a)%4:
                raise ValueError("invalid original branch-store address")
            index=(va-a)//4
            word=struct.unpack_from("<I",blob,off+4*index)[0]
            if (index not in graph["entry_reachable_indices"]
                or len(deltas[index])!=1 or None in deltas[index]
                or not any(w["register"]==reg and
                           next(iter(deltas[index]))+w["offset"]==normalized
                           for w in _stack_write(word))):
                raise ValueError("original branch-store byte/CFG/SP evidence inconsistent")
            store_indices[index]=va
        if len(store_indices)!=len(stores):
            raise ValueError("duplicate original store addresses")
        potential=[]
        for index in sorted(graph["entry_reachable_indices"]):
            following=graph["successor"][index]
            if len(following)!=2:
                continue
            pc=a+index*4
            word=struct.unpack_from("<I",blob,off+4*index)[0]
            kind,target=_decode_control(word,pc)
            if kind not in ("BRANCH_CONDITIONAL","BRANCH_COMPARE_ZERO",
                            "BRANCH_BIT_TEST"):
                continue
            # Require this branch in every modeled entry->store path.
            if any(_reaches(graph,0,store_idx,{index}) for store_idx in store_indices):
                continue
            arms=[]
            for next_index in sorted(following):
                first,skip=_first_store_encountered(
                    graph,next_index,store_indices,load_idx)
                arms.append({
                    "edge_target_va":a+next_index*4,
                    "edge_role":"TAKEN" if a+next_index*4==target else "FALLTHROUGH",
                    "first_candidate_store_vas":sorted(first),
                    "can_reach_load_without_these_stores":skip,
                })
            potential.append((index,word,kind,arms))
            if len(potential)>MAX_BRANCHES_PER_QUERY:
                raise ValueError("too many conditional branch selector candidates")
        eligible=[]
        for index,word,kind,arms in potential:
            split=(all(len(arm["first_candidate_store_vas"])==1 and
                       not arm["can_reach_load_without_these_stores"]
                       for arm in arms)
                   and arms[0]["first_candidate_store_vas"] !=
                       arms[1]["first_candidate_store_vas"])
            if not split:
                continue
            condition=_branch_condition(word,kind)
            reg=condition["tested_register"]
            source_writers=[]
            if reg is not None and reg!=31:
                previous=_first_writers_on_cfg_paths(blob,off,graph,index,reg)
                source_writers=[{
                    "writer_va":a+i*4,
                    "writer_kind":writer["kind"],
                    "source_register":writer.get("source",writer.get("base")),
                    "immediate":writer.get("immediate"),
                    "byte_offset":writer.get("byte_offset"),
                } for i,writer in previous["first_writers"][:12]]
            eligible.append({
                "branch_va":a+index*4,
                "branch_condition":condition,
                "arms":arms,
                "tested_register_writer_candidates":source_writers,
                "recognized_cfg_branch_dominates_both_stores":True,
                "both_arms_have_distinct_first_candidate_stores":True,
                "actual_branch_executed":False,
                "runtime_condition_verified":False,
            })
        if len(eligible)>MAX_SELECTED_BRANCHES:
            eligible=eligible[:MAX_SELECTED_BRANCHES]
        results.append({
            "call_va":call,
            "source_load_va":load,
            "normalized_sp_offset":normalized,
            "store_vas":sorted(store_indices.values()),
            "modeled_selector_branch_count":len(eligible),
            "selector_branch_candidates":eligible,
            "status":("MODELED_DISTINCT_ARM_STORE_SELECTOR_CANDIDATE"
                      if eligible else "NO_UNAMBIGUOUS_SELECTOR_IN_SUPPORTED_CFG"),
            "physical_store_value_verified":False,
        })
    return {
        "status":"ORIGINAL_EXECUTOR_STACK_BRANCH_SELECTOR_SYNTAX_ONLY",
        "alternative_store_queries":len(results),
        "queries_with_modeled_selector":sum(bool(x["modeled_selector_branch_count"])
                                            for x in results),
        "queries":results,
        "native_object_identity_verified":0,
        "vtable_addresses_verified":0,
        "numeric_opcode_handler_pairs_verified":0,
        "original_import_authorized":False,
        "limitations":(
            "Branch dominance and first-store reachability are restricted to "
            "recognized AArch64 CFG branches, not runtime path conditions. "
            "Unknown aliases, flags provenance, register writes, exception "
            "edges, external FDE entries and indirect targets are missing. "
            "No virtual-call target or numeric script opcode mapping proven."
        ),
    }
