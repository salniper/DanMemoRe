#!/usr/bin/env python3
"""Stage only the 33 authenticated missing bootstrap files into a NEW folder.

Input source: independently pinned original EU 15.1.0 XAPK (SHA-1 and
native ARM64 libapp SHA-256), not a different app version or untrusted archive.
Proprietary original resource bytes stay exclusively on the operator's
machine; this program never uploads them, commits them or prints their content.
Default is dry-run; --apply writes a fresh, independent partial overlay only.

It does not repair remaining 12 reference mismatches, 1544 missing Phase-3
catalog entries, or turn the original game into a playable build.
"""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import shutil
import tempfile
import zipfile

from audit_original_xapk_bootstrap33 import (
    load_index, member_safe, scan_original_xapk_members,
)
from verify_pristine_arm64_xapk import inspect_xapk, MAX_SPLIT_SIZE

MAX_ASSET_TOTAL = 16 * 1024 * 1024


def stage(xapk: Path, reference_index: Path, output: Path, apply: bool = False) -> dict:
    original = inspect_xapk(xapk)  # authenticated source archive + native ELF
    targets = load_index(reference_index)
    scan = scan_original_xapk_members(xapk, targets)
    if (scan["expected_path_exact_count"] != 33
            or scan["verified_reference_index_count"] != 33):
        raise ValueError("33/33 exact source resource paths must validate")
    expected = {}
    for target in targets:
        row = scan["targets"][target["path"]]
        source = row["exact_md5_at_expected_apk_path"]
        if len(source) != 1:
            raise ValueError("ambiguous/missing exact original member: " + target["path"])
        expected[target["path"]] = (target, source[0])

    out = output.expanduser()
    if out.exists() or out.is_symlink():
        raise ValueError("output already exists; original backups must not be overwritten")
    parent = out.parent
    if not parent.is_dir() or parent.is_symlink():
        raise ValueError("output parent must be an existing real directory")
    parent = parent.resolve(strict=True)
    final = out.resolve(strict=False)
    if final.parent != parent or final == xapk.resolve(strict=True):
        raise ValueError("output must be an immediately nested new folder")
    if not apply:
        return {
            "status": "SOURCE_EXACT_VERIFIED_DRY_RUN_NO_RESOURCE_FILES_WRITTEN",
            "source_xapk_sha1": original["source_archive_sha1"],
            "source_native_sha256": original["native_sha256"],
            "verified_source_resources": len(expected),
            "restored_resource_files": 0,
            "remaining_reference_mismatches": 12,
            "missing_historical_catalog_entries_not_repaired": 1544,
            "original_archive_import_authorized": False,
            "output": str(final),
        }

    # Reopen source and revalidate selected members before making ANY output.
    by_apk = {}
    for name,(target,source) in expected.items():
        by_apk.setdefault(source["apk"],[]).append((name,target,source))
    original_bytes={}
    overall_bytes=0
    with zipfile.ZipFile(xapk) as outer:
        for apk_name, entries in by_apk.items():
            infos=[info for info in outer.infolist()
                   if info.filename==apk_name and member_safe(info)]
            if len(infos)!=1 or not 0<infos[0].file_size<=MAX_SPLIT_SIZE:
                raise ValueError("ambiguous or oversized original nested APK")
            with outer.open(infos[0]) as member:
                contents = member.read(MAX_SPLIT_SIZE+1)
            if len(contents)!=infos[0].file_size:
                raise ValueError("nested source APK changed before extraction")
            with zipfile.ZipFile(BytesIO(contents)) as apk:
                for filename,target,source in entries:
                    matched=[info for info in apk.infolist()
                             if member_safe(info)
                             and info.filename==source["zip_member_path"]]
                    if len(matched)!=1 or matched[0].file_size!=target["size"]:
                        raise ValueError("original source path or size changed: "+filename)
                    with apk.open(matched[0]) as read:
                        bytes_ = read.read(target["size"]+1)
                    if (len(bytes_)!=target["size"] or
                            hashlib.md5(bytes_).hexdigest()!=target["md5"]):
                        raise ValueError("reference MD5/size mismatch: "+filename)
                    original_bytes[filename]=bytes_
                    overall_bytes+=len(bytes_)
                    if overall_bytes>MAX_ASSET_TOTAL:
                        raise ValueError("too many resources staged")
    if len(original_bytes)!=33:
        raise ValueError("source no longer contains all 33 target resources")

    tmp = Path(tempfile.mkdtemp(prefix=".danmemore-bootstrap33-",dir=parent))
    try:
        for filename,raw in sorted(original_bytes.items()):
            parts=filename.split("/")
            if (len(parts)<3 or parts[0]!="1" or parts[1]!="files"
                    or any(p in ("",".","..") for p in parts)):
                raise ValueError("unsafe original game destination")
            destination=tmp.joinpath(*parts)
            destination.parent.mkdir(parents=True,exist_ok=True)
            with destination.open("xb") as outstream:
                outstream.write(raw)
                outstream.flush()
                os.fsync(outstream.fileno())
            if hashlib.md5(destination.read_bytes()).hexdigest()!=expected[filename][0]["md5"]:
                raise ValueError("staged output changed during verification")
        summary={
            "status":"PARTIAL_ORIGINAL_BOOTSTRAP33_RESTORED_NOT_IMPORTABLE",
            "source_xapk_sha1":original["source_archive_sha1"],
            "source_native_sha256":original["native_sha256"],
            "verified_source_resources":33,
            "restored_resource_files":33,
            "total_resource_bytes":overall_bytes,
            "restored_paths":sorted(original_bytes),
            "remaining_reference_mismatches":12,
            "missing_historical_catalog_entries_not_repaired":1544,
            "original_archive_import_authorized":False,
            "instructions":"Keep this overlay separate from original game archive. Do not mark import complete.",
        }
        (tmp/"RECOVERY_STATUS.json").write_text(
            json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        if final.exists() or final.is_symlink():
            raise ValueError("output appeared during staging; refusing to overwrite")
        os.rename(tmp,final)  # same parent, atomic on the same filesystem
    except BaseException:
        shutil.rmtree(tmp,ignore_errors=True)
        raise
    return {**summary,"output":str(final)}


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--xapk",required=True,type=Path)
    p.add_argument("--index",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--apply",action="store_true")
    args=p.parse_args()
    result=stage(args.xapk,args.index,args.output,apply=args.apply)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
