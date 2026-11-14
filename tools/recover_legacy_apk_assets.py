#!/usr/bin/env python3
"""Read-only by default: recover 33 exact EU APK asset bytes from a pinned APK.

No original game binaries/assets are distributed by this repository.
The original RAR backup and installed game are never modified.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from zipfile import ZipFile

KNOWN_APK_SHA256 = "36713f18a6e9fec3302384b8d67383b12761f782d73932cb62b31b230053c3b6"
KNOWN_PHASE1_MANIFEST_SHA256 = "0052a4af6f0a8ebb128ff63585cfa1fa342a3c3e5e0104993d74e9b7f44dba35"


def digest(path: Path, algorithm: str = "sha256") -> str:
    h = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def load_targets(path: Path):
    report = json.loads(path.read_text(encoding="utf-8"))
    issues = [i for i in report.get("issues", [])
              if i.get("status") == "missing_with_historical_entry"]
    if len(issues) != 33:
        raise ValueError(f"expected exactly 33 known missing entries, got {len(issues)}")
    targets = {}
    for issue in issues:
        name = issue["path"]
        parts = Path(name).parts
        if (len(parts) < 3 or parts[0] != "1" or parts[1] != "files"
                or any(part in ("", ".", "..") for part in parts)):
            raise ValueError(f"unsafe or unexpected target: {name}")
        if name in targets:
            raise ValueError(f"duplicate target: {name}")
        if (issue["reference_size"] != issue["historical_size"]
                or issue["reference_md5"] != issue["historical_md5"]):
            raise ValueError(f"reference and historical fingerprints disagree: {name}")
        targets[name] = (int(issue["reference_size"]), issue["reference_md5"])
    return targets


def check_manifest(root: Path, targets):
    path = root / "1/project.manifest"
    if digest(path) != KNOWN_PHASE1_MANIFEST_SHA256:
        raise ValueError("contents/1/project.manifest is not the pinned historical snapshot")
    assets = json.loads(path.read_text(encoding="utf-8"))["assets"]
    for name, (size, expected) in targets.items():
        entry = assets.get(name.removeprefix("1/"))
        if not entry or entry["size"] != size or entry["md5"].lower() != expected:
            raise ValueError(f"manifest fingerprint mismatch: {name}")


def recover(apk: Path, audit: Path, contents: Path | None, apply: bool):
    if apply and contents is None:
        raise ValueError("--apply requires --contents")
    if digest(apk) != KNOWN_APK_SHA256:
        raise ValueError("APK SHA-256 differs from the verified EU 2023-12-22 backup")
    targets = load_targets(audit)
    if contents is not None:
        if not contents.is_dir():
            raise ValueError(f"contents root does not exist: {contents}")
        check_manifest(contents, targets)
    recovered = {}
    with ZipFile(apk, "r") as archive:
        paths = set(archive.namelist())
        for name, (size, expected) in targets.items():
            relative = name.removeprefix("1/")
            candidates = (f"assets/common/{relative}", f"assets/{relative}")
            valid = []
            for candidate in candidates:
                if candidate not in paths:
                    continue
                data = archive.read(candidate)
                if len(data) == size and md5(data) == expected:
                    valid.append((candidate, data))
            if len(valid) != 1:
                raise ValueError(f"expected one MD5-matching APK resource, got {len(valid)}: {name}")
            recovered[name] = valid[0]
    print(f"Verified {len(recovered)}/33 recovered APK assets (all MD5 + sizes match).")
    if contents is None:
        print("Read-only verification complete. Use --contents to check destinations.")
        return
    base = contents.resolve(strict=True)
    pending = []
    for name, (_, data) in recovered.items():
        destination = contents / name
        destination.resolve(strict=False).relative_to(base)
        if destination.exists() or destination.is_symlink():
            if not destination.is_file() or destination.stat().st_size != len(data) or digest(destination, "md5") != md5(data):
                raise ValueError(f"existing file differs; refusing to overwrite: {destination}")
        else:
            pending.append((destination, data))
    print(f"Already valid: {len(recovered) - len(pending)}. Missing: {len(pending)}.")
    if not apply:
        print("DRY RUN: no files changed. Add --apply to create only verified missing files.")
        return
    for destination, data in pending:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() or destination.is_symlink():
            raise ValueError(f"target appeared during recovery; refusing overwrite: {destination}")
        # Temporary file stays in destination directory so rename is atomic.
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".legacy-", delete=False) as handle:
                temp_path = Path(handle.name)
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            if md5(temp_path.read_bytes()) != md5(data):
                raise ValueError(f"temporary copy corrupted: {destination}")
            if destination.exists() or destination.is_symlink():
                raise ValueError(f"target appeared during recovery: {destination}")
            os.rename(temp_path, destination)
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
    print(f"Created {len(pending)} verified files in contents. Original APK/RARs were not modified.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apk", type=Path, required=True, help="original com.eu.danmemo_2023-12-22.apk")
    parser.add_argument("--audit", type=Path, required=True, help="danmemore_legacy_audit.json")
    parser.add_argument("--contents", type=Path, help="extracted preserved contents root")
    parser.add_argument("--apply", action="store_true", help="write ONLY absent, verified targets")
    args = parser.parse_args()
    recover(args.apk, args.audit, args.contents, args.apply)


if __name__ == "__main__":
    main()
