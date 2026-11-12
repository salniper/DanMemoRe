#!/usr/bin/env python3
"""Run the existing *candidate* master AES-CBC/zlib probe on six preserved
novelCommand assets, using an independently pinned original ARM64 XAPK.

No original bytes, decryption keys, plaintext or APKs are ever committed or
emitted. Temporary staging is deleted. This is not proof of original novel
loader compatibility and never authorizes bypassing reference MD5 checks.
"""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile

from verify_pristine_arm64_xapk import (
    ARM64_SPLIT, LIBAPP_PATH, MAX_SPLIT_SIZE, PINNED_SHA256,
    inspect_xapk, one_member,
)
from verify_remaining_legacy_candidates import STORIES, audit_entries, payload_candidates

MAX_NATIVE_BYTES = 512 * 1024 * 1024


def probe(xapk: Path, audit_path: Path, payload_path: Path,
          *, node: str = "node", project_root: Path | None = None) -> dict:
    # SHA-1 original XAPK AND SHA-256 nested libapp must match before touching
    # the six user-provided files. The original client is never executed.
    verified = inspect_xapk(xapk)
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    entries = audit_entries(audit)
    samples = payload_candidates(payload_path)
    if any(path not in samples for path in STORIES):
        raise ValueError("payload must contain all six original story ciphers")
    for path in STORIES:
        sample = samples[path]
        row = entries[path]
        if (len(sample) != row["actual_size"] or
                hashlib.md5(sample).hexdigest() != row["actual_md5"]):
            raise ValueError(f"cipher data changed since owner audit: {path}")

    project = (project_root or Path(__file__).resolve().parents[1]).resolve()
    script = (project / "tools/inspect_story_command_compat.cjs").resolve()
    if not script.is_file():
        raise ValueError("missing original read-only story compatibility probe")
    original_umask = os.umask(0o077)
    try:
        with tempfile.TemporaryDirectory(prefix="danmemore-story-probe-") as work:
            root = Path(work)
            so_path = root / "pristine_original_arm64.so"
            with zipfile.ZipFile(xapk) as bundle:
                split = one_member(bundle, ARM64_SPLIT, MAX_SPLIT_SIZE)
                with bundle.open(split) as stream:
                    apk_bytes = stream.read(MAX_SPLIT_SIZE + 1)
            if len(apk_bytes) != split.file_size:
                raise ValueError("original ARM64 nested split has changed")
            with zipfile.ZipFile(BytesIO(apk_bytes)) as apk:
                so = one_member(apk, LIBAPP_PATH, MAX_NATIVE_BYTES)
                with apk.open(so) as stream:
                    native = stream.read(MAX_NATIVE_BYTES + 1)
            if (len(native) != so.file_size or
                    hashlib.sha256(native).hexdigest() != PINNED_SHA256):
                raise ValueError("original client ELF no longer matches pinned SHA-256")
            so_path.write_bytes(native)
            del native
            contents = root / "contents"
            for name in STORIES:
                destination = contents / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(samples[name])
            # Existing JS tool returns metadata only (never plaintext/keys).
            command = [node, str(script), "--audit", str(audit_path.resolve()),
                       "--contents", str(contents), "--native-binary", str(so_path)]
            completed = subprocess.run(command, capture_output=True, text=True,
                                       check=False, timeout=45, cwd=str(project))
            if completed.returncode:
                raise ValueError("story compatibility probe failed (no source output recorded)")
            report = json.loads(completed.stdout)
            if report.get("file_count") != 6 or len(report.get("results", [])) != 6:
                raise ValueError("story tool reported an incomplete six-file set")
            if report.get("verdict") != "DO_NOT_IMPORT_UNVERIFIED_BYTES":
                raise ValueError("story compatibility probe unexpectedly authorized import")
            return {
                "status": "ACTUAL_OWNER_STORY_CIPHER_MASTER_PROBE_ONLY",
                "original_arm64_sha256": verified["native_sha256"],
                "original_xapk_sha1": verified["source_archive_sha1"],
                "six_story_probe": report,
                "import_authorized": False,
                "warning": (
                    "Master AES-CBC/zlib trial is NOT proof of the original novel loader. "
                    "Even an inflate success never authenticates a mismatched asset "
                    "or permits guarded import."
                ),
            }
    finally:
        os.umask(original_umask)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xapk", required=True, type=Path)
    parser.add_argument("--audit", required=True, type=Path)
    parser.add_argument("--payload", required=True, type=Path)
    parser.add_argument("--node", default="node")
    args = parser.parse_args()
    result = probe(args.xapk, args.audit, args.payload, node=args.node)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
