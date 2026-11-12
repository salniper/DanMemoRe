#!/usr/bin/env python3
"""Check SHA-pinned original XAPK for real executable references to novel metadata.

Outputs addresses and source/function-string names only, never original
ELF bytes, decrypted content, keys or gameplay text. Does NOT infer
numeric opcode -> original native handler mapping.
"""
import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import zipfile

from inspect_native_novel_dispatch_seeds import inspect_original_dispatch_seeds
from inspect_native_novel_executor_flow import analyze_executor_neighborhoods
from inspect_native_novel_unwind import find_executor_unwind_frames
from inspect_native_novel_elf_sections import parse_sections
from verify_pristine_arm64_xapk import (
    inspect_xapk, ARM64_SPLIT, LIBAPP_PATH, MAX_SPLIT_SIZE, MAX_LIBAPP_SIZE,
    PINNED_SHA256, one_member,
)


def inspect_original_source(path):
    verified = inspect_xapk(path)
    with zipfile.ZipFile(path) as source:
        split = one_member(source, ARM64_SPLIT, MAX_SPLIT_SIZE)
        with source.open(split) as member:
            contents = member.read(MAX_SPLIT_SIZE + 1)
        if len(contents) != split.file_size:
            raise ValueError("original split changed during read")
    with zipfile.ZipFile(BytesIO(contents)) as apk:
        native = one_member(apk, LIBAPP_PATH, MAX_LIBAPP_SIZE)
        with apk.open(native) as member:
            original = member.read(MAX_LIBAPP_SIZE + 1)
        if len(original) != native.file_size:
            raise ValueError("original native changed during read")
    if hashlib.sha256(original).hexdigest() != PINNED_SHA256:
        raise ValueError("original native SHA no longer matches the pinned source")
    # Identify real binary-provided unwind frame evidence before treating
    # any nearby branch as an original function boundary.
    sections = parse_sections(original)
    unwind = {
        row["name"]: {"file_bytes": row["size"], "virtual_address": row["addr"]}
        for row in sections
        if row["name"] in (".eh_frame", ".eh_frame_hdr", ".debug_frame",
                           ".gcc_except_table", ".ARM.exidx", ".text")
    }
    report = inspect_original_dispatch_seeds(original)
    executor_flow = analyze_executor_neighborhoods(original, report)
    unwind_frames = find_executor_unwind_frames(original, report)
    with_candidates = [
        {
            "kind": r["kind"],
            "original_label": r["label"],
            "label_file_offset": r["string_file_offset"],
            "instruction_site_count": r["instruction_site_count"],
            "instruction_sites": r["instruction_sites"],
        }
        for r in report["labels"] if r["instruction_site_count"]
    ]
    return {
        "status": report["status"],
        "validated_original_libapp_sha256": verified["native_sha256"],
        "original_source_labels_checked": report["labels_checked"],
        "native_instruction_words_checked": report["instruction_words_checked"],
        "code_referenced_original_labels":
            report["original_source_labels_with_instruction_candidates"],
        "code_site_candidates": report["original_code_site_candidate_count"],
        "original_executor_neighborhoods": executor_flow,
        "original_executor_unwind_frames": unwind_frames,
        "original_unwind_section_evidence": unwind,
        "candidate_referenced_labels": with_candidates[:60],
        "candidate_labels_truncated": len(with_candidates) > 60,
        "numeric_opcode_to_handler_mappings_verified": 0,
        "import_authorized": False,
        "original_gameplay_verified": False,
        "warning": report["limitations"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xapk", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(inspect_original_source(args.xapk), ensure_ascii=False))
