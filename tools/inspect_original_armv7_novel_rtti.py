#!/usr/bin/env python3
"""Read-only EU 15.1.0 ARMv7 NovelCommand RTTI evidence.

Only authentic SHA-pinned original ELF bytes are accepted. This enumerates
type names and their read-only ELF data references, NOT opcode dispatch
bindings or functional playback. Does not export binary or game content.
No original client, user saves or extracted archives are modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import zipfile

APK_SHA256 = "36713f18a6e9fec3302384b8d67383b12761f782d73932cb62b31b230053c3b6"
ARMV7_SHA256 = "2a1ad4cafd41252bae3e105b885adb66cd2158ecc9a275b5c5098b3a74108457"
ARMV7_MEMBER = "lib/armeabi-v7a/libapp.so"
MAX_APK_BYTES = 128 * 1024 * 1024
MAX_NATIVE_BYTES = 64 * 1024 * 1024
TYPE_NAME = re.compile(rb"\x00N6toybox3gui(\d+)(NovelCommand[A-Za-z0-9_]+)E\x00")
EXPECTED_RTTI_TYPES = 55


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def elf_sections(blob: bytes) -> dict:
    if (len(blob) < 52 or blob[:4] != b"\x7fELF"
            or blob[4] != 1 or blob[5] != 1):
        raise ValueError("not the expected little-endian ELF32")
    shoff = struct.unpack_from("<I", blob, 0x20)[0]
    entsize, count, string_index = struct.unpack_from("<HHH", blob, 0x2e)
    if (entsize != 40 or not 0 < count < 100 or string_index >= count
            or shoff > len(blob) or count * entsize > len(blob) - shoff):
        raise ValueError("ELF section directory outside bounds")
    rows = []
    for i in range(count):
        row = struct.unpack_from("<10I", blob, shoff + i * entsize)
        if row[4] > len(blob) or row[5] > len(blob) - row[4]:
            raise ValueError("ELF section payload outside bounds")
        rows.append(row)
    strings = rows[string_index]
    names = blob[strings[4]:strings[4] + strings[5]]
    out = {}
    for row in rows:
        offset = row[0]
        if offset >= len(names):
            raise ValueError("ELF section name outside string table")
        end = names.find(b"\x00", offset)
        if end < 0:
            raise ValueError("unterminated ELF section name")
        name = names[offset:end].decode("ascii")
        if name in out:
            raise ValueError("duplicate ELF section name")
        out[name] = {"addr": row[3], "offset": row[4], "size": row[5]}
    return out


def inspect_native(blob: bytes) -> dict:
    if sha256(blob) != ARMV7_SHA256:
        raise ValueError("original EU ARMv7 native SHA-256 mismatch")
    sections = elf_sections(blob)
    if ".rodata" not in sections or ".data.rel.ro" not in sections:
        raise ValueError("expected original native sections are missing")
    ro = sections[".rodata"]
    data = sections[".data.rel.ro"]
    raw_strings = blob[ro["offset"]:ro["offset"] + ro["size"]]
    raw_data = blob[data["offset"]:data["offset"] + data["size"]]
    types = {}
    for hit in TYPE_NAME.finditer(raw_strings):
        name = hit.group(2).decode("ascii")
        if int(hit.group(1)) != len(name):
            continue
        if name in types:
            raise ValueError("duplicate original class name")
        name_rva = ro["addr"] + hit.start() + 1
        address_bytes = struct.pack("<I", name_rva)
        offsets = []
        pos = 0
        while (pos := raw_data.find(address_bytes, pos)) >= 0:
            if pos % 4 == 0:
                offsets.append(data["addr"] + pos)
            pos += 1
        if len(offsets) != 1:
            raise ValueError("original RTTI class name reference is not unique: " + name)
        types[name] = {
            "type_name_rva": name_rva,
            "type_name_reference_rva": offsets[0],
        }
    if len(types) != EXPECTED_RTTI_TYPES:
        raise ValueError("original RTTI class count differs from pinned research")
    return {
        "status": "ORIGINAL_ARMV7_RTTI_TYPES_ONLY_NO_OPCODE_MAPPING",
        "original_armv7_libapp_sha256": ARMV7_SHA256,
        "authenticated_novel_command_types": len(types),
        "types": {k: types[k] for k in sorted(types)},
        "verified_numeric_opcode_handler_mappings": 0,
        "original_game_import_authorized": False,
        "original_story_playback_verified": False,
        "note": "ELF class-name pointers do not prove constructor dispatch, numeric opcode meaning or runtime execution.",
    }


def inspect_apk(apk: Path) -> dict:
    if apk.is_symlink() or not apk.is_file() or apk.stat().st_size > MAX_APK_BYTES:
        raise ValueError("source must be a bounded regular original APK")
    h = hashlib.sha256()
    with apk.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    if h.hexdigest() != APK_SHA256:
        raise ValueError("original EU APK SHA-256 mismatch")
    with zipfile.ZipFile(apk) as zf:
        entries = [info for info in zf.infolist() if info.filename == ARMV7_MEMBER]
        if len(entries) != 1 or not 0 < entries[0].file_size <= MAX_NATIVE_BYTES:
            raise ValueError("original ARMv7 ELF missing or ambiguous")
        if entries[0].flag_bits & 1:
            raise ValueError("encrypted ARMv7 ELF")
        with zf.open(entries[0]) as stream:
            native = stream.read(MAX_NATIVE_BYTES + 1)
        if len(native) != entries[0].file_size:
            raise ValueError("original ARMv7 ELF size mismatch")
    report = inspect_native(native)
    report["original_eu_apk_sha256"] = APK_SHA256
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apk", type=Path, required=True,
                        help="authentic original 2023-12-22 EU APK (read-only)")
    args = parser.parse_args()
    print(json.dumps(inspect_apk(args.apk), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
