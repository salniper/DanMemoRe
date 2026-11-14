#!/usr/bin/env python3
"""Path-bounded stack-slot store candidates in SHA-verified AArch64 FDE code.

Recognizes a small exact whitelist of 64-bit SP-based loads/stores and
stack-pointer changes. CFG uses existing bounded B/B.cond/CBZ/TBZ model.
It never claims memory aliasing, constructor ownership, vtable addresses,
original script compatibility, or numeric opcode-handler assignments.
Only numeric addresses, stack offsets and register names are reported.
"""
from __future__ import annotations
from collections import deque
import struct

from inspect_elf_novel_xrefs import elf_segments, sign_extend
from inspect_native_novel_elf_sections import parse_sections
from inspect_native_novel_unwind import _va_to_file
from inspect_native_novel_cfg_paths import _cfg
from inspect_native_novel_indirect_calls import _register_writer

MAX_REGIONS = 12
MAX_SP_DELTA_VALUES = 12
MAX_ABS_SP_DELTA = 1024 * 1024
MAX_STORE_SAMPLES = 48
MAX_TRACKED_QUERIES = 32


def _simm7(word):
    return sign_extend((word >> 15) & 127, 7) * 8


def _stack_write(word):
    """Return recognized SP-relative 64-bit store lanes, or [].

    Post/pre-index pair stores are excluded here because address uses
    changing SP and would need precise before/after phase tracking.
    Their SP mutation is still modeled by _sp_change().
    """
    if (word & 0xffc00000) == 0xf9000000 and (word >> 5) & 31 == 31:
        return [{"kind":"STR64_SP_UNSIGNED","offset":((word>>10)&4095)*8,
                 "register":word&31}]
    if (word & 0xffe00c00) == 0xf8000000 and (word >> 5) & 31 == 31:
        return [{"kind":"STUR64_SP_SIGNED","offset":sign_extend((word>>12)&511,9),
                 "register":word&31}]
    if (word & 0xffc00000) == 0xa9000000 and (word >> 5) & 31 == 31:
        off=_simm7(word)
        return [{"kind":"STP64_SP_OFFSET","offset":off,"register":word&31},
                {"kind":"STP64_SP_OFFSET","offset":off+8,"register":(word>>10)&31}]
    return []


def _sp_change(word):
    """Return SP delta, zero if no recognized SP write, None if unmodeled."""
    # ADD/SUB immediate to SP. (AArch64 SP is register field 31 here.)
    top=word & 0xff000000
    if top in (0x91000000, 0xd1000000) and (word&31)==31:
        if ((word>>5)&31)!=31:
            return None
        immediate=((word>>10)&4095) << (12 if (word>>22)&1 else 0)
        return immediate if top==0x91000000 else -immediate
    # Common stack frame STP/LDP pre/post indexed.
    pair=word & 0xffc00000
    if pair in (0xa9800000,0xa8800000,0xa9c00000,0xa8c00000):
        if (word>>5)&31==31:
            return _simm7(word)
    # Single 64-bit STR/LDR pre/post indexed.
    if (word & 0xffe00c00) in (0xf8000c00,0xf8000400,0xf8400c00,0xf8400400):
        if (word>>5)&31==31:
            return sign_extend((word>>12)&511,9)
    # Other register-based arithmetic writing the SP is unsupported:
    # return unknown rather than assuming a stable stack offset.
    if top in (0x8b000000,0xcb000000) and (word&31)==31:
        return None
    return 0


def _stack_deltas(blob, start_off, graph):
    n=graph["instruction_word_count"]
    incoming=[set() for _ in range(n)]
    incoming[0].add(0)
    todo=deque([0])
    in_queue={0}
    while todo:
        i=todo.popleft()
        in_queue.discard(i)
        deltas=incoming[i]
        word=struct.unpack_from("<I",blob,start_off+4*i)[0]
        change=_sp_change(word)
        outgoing=set()
        for delta in deltas:
            if delta is None or change is None:
                outgoing.add(None)
            else:
                proposed=delta+change
                outgoing.add(proposed if abs(proposed)<=MAX_ABS_SP_DELTA else None)
        for nxt in graph["successor"][i]:
            new=incoming[nxt] | outgoing
            if len(new)>MAX_SP_DELTA_VALUES:
                new={None}
            if None in new:
                new={None}
            if new!=incoming[nxt]:
                incoming[nxt]=new
                if nxt not in in_queue:
                    todo.append(nxt)
                    in_queue.add(nxt)
    return incoming


def _backtrack_slot(blob, start_off, graph, deltas, load_idx, normalized_slot):
    reachable=graph["entry_reachable_indices"]
    pending=list(graph["predecessor"][load_idx] & reachable)
    visited=set()
    stores=[]
    entry_without_store=False
    unknown_stack_offset_paths=0
    while pending:
        i=pending.pop()
        if i in visited:
            continue
        visited.add(i)
        word=struct.unpack_from("<I",blob,start_off+4*i)[0]
        recorded=False
        writes=_stack_write(word)
        for store in writes:
            possible=deltas[i]
            if len(possible)!=1 or None in possible:
                unknown_stack_offset_paths+=1
                continue
            absolute=next(iter(possible))+store["offset"]
            if absolute == normalized_slot:
                if len(stores)>=MAX_STORE_SAMPLES:
                    raise ValueError("too many original stack store candidates")
                stores.append((i,store))
                recorded=True
        if recorded:
            continue
        if i==0:
            entry_without_store=True
        pending.extend((graph["predecessor"][i] & reachable)-visited)
    return {
        "stores":sorted(stores,key=lambda pair:pair[0]),
        "entry_without_known_store":entry_without_store,
        "unresolved_sp_offset_writes":unknown_stack_offset_paths,
    }


def inspect_stack_slot_sources(blob, frames, precise, cfg_report):
    if (frames.get("status")!="ORIGINAL_CFI_FDE_COVERAGE_ONLY_NOT_DISPATCH_PROOF"
            or precise.get("status")!="EXACT_CFI_REGION_INSTRUCTION_CLASS_METADATA_NO_OPCODE_PROOF"
            or cfg_report.get("status")!="ORIGINAL_FDE_CFG_REACHING_WRITER_CANDIDATES_ONLY"):
        raise ValueError("verified original FDE/CFG evidence is mandatory")
    expected={(x["unwind_coverage"]["start_va"],x["unwind_coverage"]["end_va_exclusive"])
              for x in frames.get("sites",[])
              if x.get("status")=="VALIDATED_ORIGINAL_UNWIND_COVERAGE"}
    if not expected:
        raise ValueError("no validated original unwind regions")
    sec=parse_sections(blob)
    seg=elf_segments(blob)
    ranges={}
    if not 1<=len(precise.get("regions",[]))<=MAX_REGIONS:
        raise ValueError("unbounded original FDE region count")
    for r in precise["regions"]:
        a,b=r["validated_unwind_start_va"],r["validated_unwind_end_va_exclusive"]
        executable=[s for s in sec if s["type"]==1 and s["flags"]&4
                    and s["addr"]<=a and b<=s["addr"]+s["size"]]
        off=_va_to_file(seg,a)
        if (a,b) not in expected or len(executable)!=1 or off is None:
            raise ValueError("missing validated original executable FDE")
        graph=_cfg(blob,executable[0],a,b,off)
        ranges[(a,b)]=(off,graph,_stack_deltas(blob,off,graph))
    queries=[]
    source_rows=cfg_report.get("source_register_paths",[])
    if len(source_rows)>32:
        raise ValueError("too many authenticated original CFG call sites")
    for row in source_rows:
        call=row.get("call_va")
        if not isinstance(call,int):
            raise ValueError("invalid original BLR call")
        matches=[(a,b) for a,b in ranges if a<=call<b]
        if len(matches)!=1:
            raise ValueError("original call has no unique FDE")
        a,b=matches[0]
        off,graph,deltas=ranges[(a,b)]
        for candidate in row.get("reaching_writer_samples",[]):
            # SP=31 denotes stack pointer in these LDR / ADD forms.
            if candidate.get("from_register")!=31:
                continue
            writer_va=candidate["writer_va"]
            if not isinstance(writer_va,int) or not a<=writer_va<b or (writer_va-a)%4:
                raise ValueError("candidate is outside authenticated FDE")
            idx=(writer_va-a)//4
            word=struct.unpack_from("<I",blob,off+4*idx)[0]
            decoded=_register_writer(word,writer_va)
            access_kind=candidate.get("kind")
            if (decoded is None or decoded.get("kind")!=access_kind or
                    decoded.get("source",decoded.get("base"))!=31):
                raise ValueError("candidate stack access changed or is not original")
            if access_kind=="LOAD_POINTER_FROM_REGISTER":
                slot=decoded["byte_offset"]
                mode="STACK_SLOT_VALUE_READ"
            elif access_kind=="ADD_REGISTER_IMMEDIATE":
                slot=decoded["immediate"]
                mode="ADDRESS_OF_STACK_SLOT_NOT_CONTENT_READ"
            else:
                continue
            incoming=deltas[idx]
            if len(incoming)!=1 or None in incoming:
                queries.append({
                    "call_va":call,"source_writer_va":writer_va,"kind":mode,
                    "sp_relative_byte_offset_at_use":slot,
                    "status":"AMBIGUOUS_OR_UNMODELED_SP_BASE",
                    "known_store_candidates":[],"stack_value_verified":False})
                continue
            normalized=next(iter(incoming))+slot
            found=_backtrack_slot(blob,off,graph,deltas,idx,normalized)
            candidates=[{
                "store_va":a+i*4,"kind":store["kind"],
                "stored_register":store["register"],
                "sp_relative_byte_offset_at_store":store["offset"],
            } for i,store in found["stores"]]
            queries.append({
                "call_va":call,"source_writer_va":writer_va,
                "kind":mode,
                "sp_relative_byte_offset_at_use":slot,
                "entry_sp_normalized_byte_offset":normalized,
                "status":("POSSIBLE_CFG_STACK_STORE_SOURCES_NO_ALIAS_PROOF"
                          if candidates else "NO_RECOGNIZED_FIRST_STORE_IN_CFG"),
                "known_store_candidates":candidates,
                "entry_path_without_known_store":found["entry_without_known_store"],
                "unresolved_sp_offset_writes":found["unresolved_sp_offset_writes"],
                "stack_value_verified":False,
            })
            if len(queries)>MAX_TRACKED_QUERIES:
                raise ValueError("too many original stack slots")
    return {
        "status":"ORIGINAL_CFG_STACK_STORE_PROVENANCE_CANDIDATES_ONLY",
        "stack_slot_queries":len(queries),"queried_sources":queries,
        "queries_with_recognized_store_candidates":sum(
            bool(q["known_store_candidates"]) for q in queries),
        "stack_values_authenticated":0,
        "original_vtable_addresses_proven":0,
        "original_numeric_opcode_handlers_proven":0,
        "import_authorized":False,
        "limitations":(
            "Only 64-bit SP-relative STR/STUR/STP(offset) stores with recognized "
            "SP arithmetic are tracked. No 32-bit/NEON stores, alias writes, "
            "indirect stores, full SP/FP tracking, global CFG, exception paths, "
            "constructor identity, vtable values or numeric opcode semantics. "
            "ADD SP+offset creates an address and does NOT itself read a pointer."
        ),
    }
