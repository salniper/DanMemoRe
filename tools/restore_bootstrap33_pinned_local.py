#!/usr/bin/env python3
"""Recover 33 source-verified Phase-1 bootstrap files without overwriting game data.

Convenience wrapper for an owner's local computer/Termux environment:
- Without --xapk, HTTPS-download the *one* pinned EU 15.1.0 XAPK into a
  temporary directory, checking the original archive SHA-1 while streaming.
- With --xapk, use the owner's existing untouched archive (no download).
- Call the established independent XAPK + nested-native SHA256 verifier and
  strict 33-entry source size/MD5 scanner; --apply requires explicit consent.
- Never alter, delete, install, upload or repack the existing game.
- Downloaded temporary source APK is erased when the command exits.
No game bytes/keys are embedded in the repository or printed in logs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import urllib.parse
import urllib.request

from stage_original_xapk_bootstrap33 import stage
from verify_pristine_arm64_xapk import MAX_XAPK_SIZE, PINNED_XAPK_SHA1

OFFICIAL_MIRROR_CANDIDATE = (
    "https://d.apkpure.net/b/XAPK/com.eu.danmemo"
    "?nc=&sv=19&versionCode=170316722"
)
CHUNK = 1 << 20


class _HttpsOnlyRedirect(urllib.request.HTTPRedirectHandler):
    """Do not follow an HTTPS original resource download to HTTP."""

    def redirect_request(self, request, fp, code, msg, headers, newurl):
        if urllib.parse.urlparse(newurl).scheme != "https":
            raise ValueError("original source redirect is not HTTPS")
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def download_pinned_source(destination: Path) -> dict:
    if destination.exists() or destination.is_symlink():
        raise ValueError("temporary source path already exists")
    if not destination.parent.is_dir():
        raise ValueError("temporary source directory unavailable")
    opener = urllib.request.build_opener(_HttpsOnlyRedirect)
    request = urllib.request.Request(
        OFFICIAL_MIRROR_CANDIDATE,
        headers={"User-Agent": "DanMemoRe-Preservation-Verify/1.0",
                 "Accept-Encoding": "identity"},
    )
    length = 0
    digest = hashlib.sha1()
    try:
        with opener.open(request, timeout=90) as remote:
            if urllib.parse.urlparse(remote.geturl()).scheme != "https":
                raise ValueError("source download ended outside HTTPS")
            declared = remote.headers.get("Content-Length")
            if declared is not None and int(declared) > MAX_XAPK_SIZE:
                raise ValueError("original XAPK exceeds size cap")
            with destination.open("xb") as output:
                while True:
                    chunk = remote.read(CHUNK)
                    if not chunk:
                        break
                    length += len(chunk)
                    if length > MAX_XAPK_SIZE:
                        raise ValueError("original XAPK exceeds size cap")
                    output.write(chunk)
                    digest.update(chunk)
        if length <= 0 or digest.hexdigest() != PINNED_XAPK_SHA1:
            raise ValueError("downloaded original XAPK SHA-1 mismatch")
        return {"temporary_download_bytes": length,
                "source_archive_sha1": digest.hexdigest()}
    except BaseException:
        destination.unlink(missing_ok=True)
        raise


def restore(*, index: Path, output: Path, xapk: Path | None,
            apply: bool) -> dict:
    if output.exists() or output.is_symlink():
        raise ValueError("refusing to replace an existing source/recovery folder")
    if xapk is not None:
        result = stage(xapk, index, output, apply=apply)
        return {**result, "source_acquisition": "EXISTING_OWNER_FILE",
                "downloaded_temporary_source_retained": False}
    with tempfile.TemporaryDirectory(prefix="danmemore-pinned-source-") as t:
        source = Path(t) / "verified-candidate.xapk"
        download = download_pinned_source(source)
        result = stage(source, index, output, apply=apply)
    return {
        **result,
        "source_acquisition": "HTTPS_DOWNLOAD_EXACT_PINNED_ARCHIVE",
        "downloaded_temporary_source_retained": False,
        "source_download_bytes": download["temporary_download_bytes"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--xapk", type=Path,
                        help="optional already-owned exact original source archive")
    parser.add_argument("--apply", action="store_true",
                        help="write 33 verified files into a new folder only")
    args = parser.parse_args()
    status = restore(index=args.index, output=args.output,
                     xapk=args.xapk, apply=args.apply)
    print(json.dumps(status, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
