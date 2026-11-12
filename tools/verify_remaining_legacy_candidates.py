#!/usr/bin/env python3
"""Compare exactly 12 DanMemoRe legacy blockers against pinned catalog hashes.

Read-only. It never copies candidate assets, decrypts data, changes imports,
or treats a mirror of the same backup as independent historical provenance.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
from pathlib import Path
import re
import struct

from inspect_legacy_mismatches import png_crc_valid

PHASES = tuple(f"1/manifests/phase.manifest.{i}" for i in (1, 2, 3, 4, 6, 7, 8))
STORIES = tuple(
    f"1/master/divide_novel_command_enc/novelCommand{i}.enc"
    for i in (751040548, 751040550, 751040806, 751040815, 751041273, 751041275)
)
MASTERS = tuple(
    f"1/master/divide_enc/{name}.enc"
    for name in ("adventureMission", "downloadVoicePhase",
                 "lotteryWeightGroup", "subscription")
)
PNG = "1/files/font/number.png"
ATLAS = "3/files/ui_atlas/home_gacha/gacha_top_move_parts_text.json"
REMAINING = STORIES + MASTERS + (PNG, ATLAS)
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_PAYLOAD_BYTES = 48 * 1024 * 1024
HASH = re.compile(r"^[0-9a-f]{32}$")


def md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def audit_entries(audit: dict) -> dict:
    if not isinstance(audit, dict) or not isinstance(audit.get("issues"), list):
        raise ValueError("invalid audit structure")
    unverified = [x for x in audit["issues"] if isinstance(x, dict)
                  and x.get("status") == "unverified_bytes"]
    expected = set(PHASES + REMAINING)
    names = [x.get("path") for x in unverified]
    if len(names) != 19 or len(set(names)) != 19 or set(names) != expected:
        raise ValueError("audit must contain exactly the known 19 mismatches")
    result = {}
    for row in unverified:
        path = row["path"]
        expected_size = row.get("reference_size")
        if not isinstance(expected_size, int) or isinstance(expected_size, bool) or not 0 < expected_size <= MAX_FILE_BYTES:
            raise ValueError(f"invalid reference size: {path}")
        if row.get("actual_size") != expected_size or row.get("historical_size") != expected_size:
            raise ValueError(f"incompatible audit sizes: {path}")
        ref = row.get("reference_md5")
        old = row.get("actual_md5")
        if (not isinstance(ref, str) or not HASH.fullmatch(ref) or
                not isinstance(old, str) or not HASH.fullmatch(old) or
                row.get("historical_md5") != ref or ref == old):
            raise ValueError(f"incompatible audit MD5s: {path}")
        result[path] = row
    return result


def payload_candidates(payload_path: Path) -> dict:
    if payload_path.stat().st_size > MAX_PAYLOAD_BYTES:
        raise ValueError("payload JSON exceeds bounded input size")
    root = json.loads(payload_path.read_text(encoding="utf-8"))
    if not isinstance(root, dict) or not isinstance(root.get("files"), list):
        raise ValueError("invalid payload")
    output = {}
    for row in root["files"]:
        if not isinstance(row, dict) or row.get("path") not in REMAINING:
            continue
        path = row["path"]
        if path in output:
            raise ValueError(f"duplicate payload path: {path}")
        encoded = row.get("data_base64")
        if not isinstance(encoded, str) or len(encoded) > (MAX_FILE_BYTES + 2) * 4 // 3 + 4:
            raise ValueError(f"invalid or oversized payload bytes: {path}")
        try:
            data = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError(f"invalid base64 for {path}") from exc
        if len(data) > MAX_FILE_BYTES:
            raise ValueError(f"decoded asset too large: {path}")
        output[path] = data
    return output


def directory_candidates(root: Path) -> dict:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("candidate root must be a real directory")
    root = root.resolve(strict=True)
    result = {}
    for name in REMAINING:
        at = root
        missing = False
        for part in name.split("/"):
            at = at / part
            if at.is_symlink():
                raise ValueError(f"symlinked source refused: {name}")
            if not at.exists():
                missing = True
                break
        if missing:
            continue
        if not at.is_file() or not at.resolve().is_relative_to(root):
            raise ValueError(f"invalid candidate path: {name}")
        if at.stat().st_size > MAX_FILE_BYTES:
            raise ValueError(f"oversized candidate: {name}")
        result[name] = at.read_bytes()
    return result


def format_probe(name: str, data: bytes) -> str:
    if name.endswith(".enc"):
        return "BLOCK_ALIGNED_ONLY" if data and len(data) % 16 == 0 else "NOT_16_BYTE_ALIGNED"
    if name == PNG:
        if not png_crc_valid(data):
            return "INVALID_PNG_OR_CRC"
        if len(data) < 33:
            return "INVALID_PNG_HEADER"
        width, height, depth, mode = struct.unpack_from(">IIBB", data, 16)
        return "PNG_109x179_LA8" if (width, height, depth, mode) == (109, 179, 8, 4) else "VALID_PNG_OTHER_GEOMETRY"
    if name == ATLAS:
        try:
            doc = json.loads(data.decode("utf-8"))
        except (ValueError, UnicodeError):
            return "INVALID_JSON"
        if not isinstance(doc, dict) or not isinstance(doc.get("root"), dict):
            return "JSON_UNEXPECTED_ROOT"
        root = doc["root"]
        nodes = root.get("childs")
        if not isinstance(nodes, list):
            return "JSON_UNEXPECTED_CHILDREN"
        tags = [x.get("tag") for x in nodes if isinstance(x, dict)]
        pictures = [x.get("image") for x in nodes if isinstance(x, dict)]
        if (root.get("class") == "Node" and len(nodes) == 13 and
                sorted(tags) == list(range(1, 14)) and
                sorted(pictures) == sorted(f"{i}.png" for i in range(1, 14)) and
                all(x.get("class") == "Sprite" for x in nodes if isinstance(x, dict))):
            return "JSON_13_SPRITES_STRUCTURALLY_CONSISTENT"
        return "JSON_PARSED_LAYOUT_NOT_CONFIRMED"
    raise ValueError(f"unsupported residual asset: {name}")


def compare(audit: dict, candidates: dict) -> dict:
    rows = audit_entries(audit)
    output = []
    counts = {"REFERENCE_EXACT": 0, "SAME_AS_UNVERIFIED_BACKUP": 0,
              "OTHER_UNVERIFIED": 0, "WRONG_SIZE": 0, "ABSENT": 0}
    for name in REMAINING:
        ref = rows[name]
        data = candidates.get(name)
        if data is None:
            output.append({"path": name, "status": "ABSENT"})
            counts["ABSENT"] += 1
            continue
        if not isinstance(data, bytes) or len(data) > MAX_FILE_BYTES:
            raise ValueError(f"invalid candidate data for {name}")
        actual_md5 = md5(data)
        if len(data) != ref["reference_size"]:
            status = "WRONG_SIZE"
        elif actual_md5 == ref["reference_md5"]:
            status = "REFERENCE_EXACT"
        elif actual_md5 == ref["actual_md5"]:
            status = "SAME_AS_UNVERIFIED_BACKUP"
        else:
            status = "OTHER_UNVERIFIED"
        counts[status] += 1
        output.append({"path": name, "status": status, "size": len(data),
                       "md5": actual_md5,
                       "sha256": hashlib.sha256(data).hexdigest(),
                       "format_probe": format_probe(name, data)})
    return {
        "verdict": "NO_IMPORT_AUTHORIZATION",
        "checked_files": len(REMAINING),
        "reference_exact_count": counts["REFERENCE_EXACT"],
        "categories": counts, "files": output,
        "warning": ("Only exact reference size+MD5 proves byte identity for a given asset. "
                    "Structural checks, reused backups, or matching decoded data are not authorization. "
                    "Even 12/12 reference-exact candidates require a separate complete import/runtime acceptance.")
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--payload", type=Path, help="locally saved 19-file JSON payload; read-only")
    source.add_argument("--candidates", type=Path, help="independent candidate contents root; read-only")
    args = parser.parse_args()
    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    candidates = payload_candidates(args.payload) if args.payload else directory_candidates(args.candidates)
    print(json.dumps(compare(audit, candidates), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
