#!/usr/bin/env python3
"""Read-only forensic triage for 19 unverified DanMemoRe preservation assets.

Use the original audit as a *claim*, not as a trust anchor. This script never
changes, deletes, or re-classifies game bytes, and does not weaken the importer.
It emits metadata only, not proprietary source content.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib


def kind(path):
    if path.startswith("1/manifests/phase.manifest."):
        return "phase_metadata"
    if path.startswith("1/master/divide_novel_command_enc/"):
        return "story_command"
    if path.startswith("1/master/divide_enc/"):
        return "game_catalog"
    if path == "1/files/font/number.png":
        return "font_png"
    if path == "3/files/ui_atlas/home_gacha/gacha_top_move_parts_text.json":
        return "gacha_json"
    raise ValueError(f"unexpected mismatch path in audit: {path}")


def png_crc_valid(data):
    """Check PNG framing and per-chunk CRCs; no third-party imaging library."""
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return False
    pos = 8
    seen_ihdr = seen_iend = False
    while pos + 12 <= len(data):
        length = struct.unpack_from(">I", data, pos)[0]
        if length > len(data) - pos - 12:
            return False
        name = data[pos + 4:pos + 8]
        payload = data[pos + 8:pos + 8 + length]
        crc = struct.unpack_from(">I", data, pos + 8 + length)[0]
        if zlib.crc32(name + payload) & 0xFFFFFFFF != crc:
            return False
        if name == b"IHDR":
            if seen_ihdr or pos != 8 or length != 13:
                return False
            seen_ihdr = True
        if name == b"IEND":
            seen_iend = True
            pos += 12 + length
            break
        pos += 12 + length
    return seen_ihdr and seen_iend and pos == len(data)


def safe_relative(name):
    if not isinstance(name, str) or "\\" in name or name.startswith("/"):
        raise ValueError(f"unsafe report path: {name!r}")
    parts = name.split("/")
    if len(parts) < 3 or any(p in ("", ".", "..") for p in parts):
        raise ValueError(f"unsafe report path: {name!r}")
    return Path(*parts)


def inspect(audit_path, contents=None):
    report = json.loads(Path(audit_path).read_text(encoding="utf-8"))
    issues = [i for i in report["issues"] if i.get("status") == "unverified_bytes"]
    if len(issues) != 19:
        raise ValueError(f"expected exactly 19 unverified audit entries; got {len(issues)}")
    root = Path(contents).resolve(strict=True) if contents is not None else None
    if root is not None and not root.is_dir():
        raise ValueError(f"not a contents directory: {root}")
    out = []
    seen = set()
    for entry in issues:
        name = entry["path"]
        relative = safe_relative(name)
        category = kind(name)
        if name in seen:
            raise ValueError(f"duplicate mismatch entry: {name}")
        seen.add(name)
        size = entry["reference_size"]
        original = entry["reference_md5"].lower()
        actual_audit = entry["actual_md5"].lower()
        if (entry["historical_md5"].lower() != original or
                entry["historical_size"] != size or entry["actual_size"] != size or
                len(original) != 32 or len(actual_audit) != 32 or
                any(c not in "0123456789abcdef" for c in original + actual_audit) or
                original == actual_audit):
            raise ValueError(f"unexpected fingerprint relationship: {name}")
        item = {
            "path": name, "category": category, "size": size,
            "reference_and_historical_md5": original,
            "audited_md5": actual_audit,
            "source_status": "UNVERIFIED",
        }
        if root is not None:
            target = root.joinpath(relative)
            # Never follow symlinks, including in any parent directory.
            current = root
            for part in relative.parts:
                current = current / part
                if current.is_symlink():
                    raise ValueError(f"symlink refused: {name}")
            if not target.is_file():
                raise ValueError(f"missing mismatch candidate: {name}")
            data = target.read_bytes()
            real_md5 = hashlib.md5(data).hexdigest()
            item["on_device_sha256"] = hashlib.sha256(data).hexdigest()
            item["audit_recheck"] = (
                "MATCH" if len(data) == size and real_md5 == actual_audit
                else "CHANGED_SINCE_AUDIT"
            )
            if category == "font_png":
                item["structural_check"] = "VALID_PNG_CRC" if png_crc_valid(data) else "BAD_PNG_CRC_OR_FORMAT"
            elif category == "gacha_json":
                try:
                    decoded = json.loads(data.decode("utf-8"))
                    item["structural_check"] = "VALID_JSON" if isinstance(decoded, (dict, list)) else "JSON_SCALAR"
                except (UnicodeError, ValueError):
                    item["structural_check"] = "INVALID_JSON"
            elif category == "phase_metadata":
                try:
                    parsed = json.loads(data.decode("utf-8"))
                    item["structural_check"] = "JSON_OBJECT" if isinstance(parsed, dict) else "OTHER_JSON"
                    if isinstance(parsed, dict):
                        item["json_keys"] = sorted(parsed.keys())
                except (UnicodeError, ValueError):
                    item["structural_check"] = "NON_JSON_OR_BINARY"
            elif category in ("story_command", "game_catalog"):
                item["structural_check"] = "OPAQUE_ENCRYPTED_FILE_NOT_AUTHENTICATED"
                item["aligned_16_bytes"] = len(data) % 16 == 0
        out.append(item)
    categories = {group: sum(x["category"] == group for x in out)
                  for group in ("phase_metadata", "story_command", "game_catalog", "font_png", "gacha_json")}
    return {
        "verdict": "DO_NOT_IMPORT_UNVERIFIED_BYTES",
        "source_audit": Path(audit_path).name,
        "asset_count": len(out),
        "bytes_with_mismatched_md5": sum(x["size"] for x in out),
        "all_mismatch_sizes_equal_reference": True,
        "reference_and_historical_catalogs_agree_for_all_19": True,
        "categories": categories,
        "inspection": "ON_DEVICE_REHASH" if root is not None else "AUDIT_METADATA_ONLY",
        "items": out,
        "notice": "A valid PNG CRC or JSON syntax is NOT proof of a trusted game asset.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--contents", type=Path, help="optional extracted game root; read-only")
    parser.add_argument("--output", type=Path, help="optional JSON report output, NOT inside game contents")
    args = parser.parse_args()
    result = inspect(args.audit, args.contents)
    body = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output is None:
        sys.stdout.write(body)
    else:
        if args.contents is not None:
            parent = args.contents.resolve(strict=True)
            if args.output.resolve(strict=False).is_relative_to(parent):
                parser.error("--output must not be inside the source contents directory")
        if args.output.exists():
            parser.error("--output already exists; refusing to overwrite")
        args.output.write_text(body, encoding="utf-8")
        print(f"Wrote diagnostic metadata: {args.output}")


if __name__ == "__main__":
    main()
