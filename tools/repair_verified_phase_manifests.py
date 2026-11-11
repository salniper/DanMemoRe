#!/usr/bin/env python3
"""Recover only TWO independently byte-verified phase manifests into a separate directory.

No proprietary game bytes are bundled. By default this is READ-ONLY. Never
modifies the user's source contents, and never bypasses the 17 other mismatches.
"""
import argparse
import hashlib
import json
from pathlib import Path

SOURCE_VERSION = b"582a6b5539f7766be40c5d2e36aca01b"
REFERENCE_VERSION = b"4ab12a6c3f219553661ff647ae79e322"
# Actual source hashes from AYN Thor's uploaded files; targets independently
# pinned by the reference and historical project.manifest.1 indexes.
REPAIRS = {
    "1/manifests/phase.manifest.6": {
        "size": 354,
        "source_sha256": "a456eac9be274d4f9e3748feeeea0c5e3101e0b0e95d4ab5b8d81bdec0733412",
        "repaired_sha256": "72433426fc9c74f79535843974433a55b0c1b89152c0ff4cda95c69bb8c31ba0",
        "reference_md5": "978673603b2d29df0ef9b53447ba0bcd",
    },
    "1/manifests/phase.manifest.7": {
        "size": 355,
        "source_sha256": "d83cc4961eb8cccd0145527e4b39f9618ed867ef8707ac7cba45d5b74a5c517f",
        "repaired_sha256": "bf0385f55c6c1040951b32acf06062b543263509a10345608e2b07f75f662697",
        "reference_md5": "3bc336eab43c1c16350aab4a9a0ee5f4",
    },
}


def hexdigest(data: bytes, name: str) -> str:
    return hashlib.new(name, data).hexdigest()


def verified_repair(name: str, data: bytes, spec: dict) -> bytes:
    if len(data) != spec["size"] or hexdigest(data, "sha256") != spec["source_sha256"]:
        raise ValueError(f"unrecognized source bytes: {name}")
    if data.count(SOURCE_VERSION) != 3:
        raise ValueError(f"unexpected version field count: {name}")
    try:
        parsed = json.loads(data.decode("utf-8"))
    except (ValueError, UnicodeError) as error:
        raise ValueError(f"invalid JSON: {name}") from error
    if not isinstance(parsed, dict) or parsed.get("assets") != {}:
        raise ValueError(f"unexpected phase manifest contents: {name}")
    fixed = data.replace(SOURCE_VERSION, REFERENCE_VERSION)
    if len(fixed) != len(data):
        raise ValueError(f"version replacement changed file size: {name}")
    if (hexdigest(fixed, "sha256") != spec["repaired_sha256"]
            or hexdigest(fixed, "md5") != spec["reference_md5"]):
        raise ValueError(f"repaired bytes do not match pinned reference: {name}")
    return fixed


def run(contents: Path, output_dir: Path | None, apply: bool) -> list[str]:
    if apply and output_dir is None:
        raise ValueError("--apply requires --output-dir")
    src = contents.resolve(strict=True)
    if not src.is_dir():
        raise ValueError(f"contents source is not a directory: {src}")
    if output_dir is not None:
        dst = output_dir.resolve(strict=False)
        if dst == src or dst.is_relative_to(src) or src.is_relative_to(dst):
            raise ValueError("output directory must be separate from source contents")
    prepared = {}
    for name, spec in REPAIRS.items():
        path = src / name
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(src):
            raise ValueError(f"source file missing, symlinked or outside contents: {name}")
        prepared[name] = verified_repair(name, path.read_bytes(), spec)
    if output_dir is not None:
        for name in prepared:
            path = output_dir / name
            if path.exists() or path.is_symlink():
                raise ValueError(f"refusing to overwrite: {path}")
    if apply:
        for name, data in prepared.items():
            path = output_dir / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as handle:
                handle.write(data)
    return list(prepared)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contents", type=Path, required=True,
                        help="read-only source /Download/contents")
    parser.add_argument("--output-dir", type=Path, help="distinct output directory")
    parser.add_argument("--apply", action="store_true",
                        help="create only verified fixed files, never overwrite")
    args = parser.parse_args()
    names = run(args.contents, args.output_dir, args.apply)
    print(f"Verified {len(names)} phase manifests against reference SHA-256 and MD5.")
    print("Created separate output copies." if args.apply else "DRY RUN; no files changed.")
    print("17 OTHER ASSETS STILL UNVERIFIED. Do not import these as a complete fix.")


if __name__ == "__main__":
    main()
