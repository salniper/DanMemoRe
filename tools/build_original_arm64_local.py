#!/usr/bin/env python3
"""Build an original-looking DanMemoRe ARM64 game client LOCALLY.

This keeps the publisher's original rendering/UI binary and routes its retired
endpoints to DanMemoRe's loopback server. It is *not* the 18 KiB demo and does
not bundle the user's archived assets or make incomplete gameplay work.

The caller must supply the unmodified, SHA-pinned EU 15.1.0 XAPK.
Never commit/upload proprietary APKs, locally signed outputs, signing secrets,
decrypted dialogue or the ~14 GB original content archive to the repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import stat
import tempfile
import zipfile

import offline_client as client
from verify_pristine_arm64_xapk import inspect_xapk

MAX_XAPK = 1024 * 1024 * 1024
MAX_SPLIT = 512 * 1024 * 1024


def verify_source(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size < MAX_XAPK:
        raise ValueError("Missing, symlinked or oversized original XAPK; no output generated")
    # Match BOTH original-project SHA256 and the independent preservation
    # provenance verifier (XAPK SHA1 + original libapp.so SHA256).
    source_sha = client.sha256(path)
    if source_sha != client.ARM64_XAPK_SHA256:
        raise ValueError("Unknown XAPK SHA-256; refuse to alter an unsupported version")
    verified = inspect_xapk(path, scan=False)
    with zipfile.ZipFile(path, "r") as bundle:
        members = bundle.infolist()
        by_name = {}
        for member in members:
            by_name.setdefault(member.filename, []).append(member)
        sizes = {}
        for name in client.ARM64_APKS:
            choices = by_name.get(name, [])
            if len(choices) != 1:
                raise ValueError("Expected exactly one original split: " + name)
            member = choices[0]
            if (member.is_dir() or stat.S_ISLNK(member.external_attr >> 16)
                    or not 0 < member.file_size <= MAX_SPLIT):
                raise ValueError("Untrusted original split archive member: " + name)
            sizes[name] = member.file_size
    return {
        "status": "ORIGINAL_ARM64_XAPK_PINNED_AND_VERIFIED",
        "xapk_sha256": source_sha,
        "xapk_sha1": verified["source_archive_sha1"],
        "native_sha256": verified["native_sha256"],
        "original_split_count": len(sizes),
        "split_names_and_unpacked_sizes": sizes,
        "source_gameplay_acceptance": False,
    }


def android_build_tools():
    candidates = [Path(p) for p in
                  (os.getenv("ANDROID_HOME"), os.getenv("ANDROID_SDK_ROOT")) if p]
    candidates.extend([Path.home() / "Android/Sdk",
                       Path.home() / "AppData/Local/Android/Sdk"])
    sdk = next((p for p in candidates if (p / "build-tools").is_dir()), None)
    if sdk is None:
        raise FileNotFoundError("Android SDK missing: set ANDROID_HOME")
    suites = sorted((p for p in (sdk / "build-tools").iterdir()
                     if p.is_dir()), reverse=True)
    exe = ".exe" if os.name == "nt" else ""
    for suite in suites:
        zipalign, aapt, signer = (suite / ("zipalign" + exe),
                                  suite / ("aapt" + exe),
                                  suite / "lib/apksigner.jar")
        if all(x.is_file() for x in (zipalign, aapt, signer)):
            break
    else:
        raise FileNotFoundError("Need Android SDK zipalign, aapt and apksigner.jar")
    java_home = os.getenv("JAVA_HOME")
    java = (Path(java_home) / "bin" / ("java"+exe)) if java_home else None
    keytool = (Path(java_home) / "bin" / ("keytool"+exe)) if java_home else None
    java = java if java and java.is_file() else shutil.which("java")
    keytool = keytool if keytool and keytool.is_file() else shutil.which("keytool")
    adb = (sdk / "platform-tools" / ("adb"+exe))
    if not java or not keytool:
        raise FileNotFoundError("Java 17 and keytool are required")
    # adb is not used by the build; return a placeholder if unavailable.
    return (zipalign, aapt, signer, Path(java), Path(keytool),
            adb if adb.is_file() else Path("adb"))


def _local_signer() -> tuple[Path, str]:
    # Persist the signing identity across local rebuilds, so an installed
    # original-looking game can be updated without uninstalling/save loss.
    root = client.WORK / "original-arm64-signing"
    root.mkdir(parents=True, exist_ok=True)
    password_path = root / "password.txt"
    key_path = root / "original-arm64-local.p12"
    if password_path.exists() != key_path.exists():
        raise ValueError("Incomplete signing identity; refuse to replace it silently")
    if not key_path.exists():
        password = secrets.token_hex(24)
        with password_path.open("x", encoding="ascii") as secret:
            secret.write(password + "\n")
        if os.name != "nt":
            os.chmod(password_path, 0o600)
        try:
            _, _, _, _, keytool, _ = android_build_tools()
            env = os.environ | {"DANMEMORE_KEY_PASSWORD": password}
            client.run([
                keytool, "-genkeypair", "-keystore", key_path, "-storetype",
                "PKCS12", "-alias", "danmemore-original-local",
                "-storepass:env", "DANMEMORE_KEY_PASSWORD",
                "-keyalg", "RSA", "-keysize", "2048", "-validity", "3650",
                "-dname", "CN=DanMemoRe original client local build",
            ], env=env)
            if os.name != "nt":
                os.chmod(key_path, 0o600)
        except BaseException:
            password_path.unlink(missing_ok=True)
            key_path.unlink(missing_ok=True)
            raise
    return key_path, password_path.read_text(encoding="ascii").strip()


def build_original_arm64(source: Path, out: Path) -> dict:
    verified = verify_source(source)
    tools = android_build_tools()
    client.WORK.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    key, password = _local_signer()
    patches, signer = [], None
    # Extract original splits in a temporary ignored private directory.
    # The source XAPK is user-supplied and never rewritten.
    with tempfile.TemporaryDirectory(prefix="danmemore-original-", dir=client.WORK) as tmp:
        location = Path(tmp)
        with zipfile.ZipFile(source, "r") as bundle:
            for name in client.ARM64_APKS:
                member = bundle.getinfo(name)
                with bundle.open(member, "r") as reader, (location / name).open("wb") as writer:
                    shutil.copyfileobj(reader, writer, length=1024*1024)
        # Stage every split first; publish only after all signatures agree.
        assembled = location / "signed"
        assembled.mkdir()
        for name in client.ARM64_APKS:
            changes, digest = client.patch_and_sign_apk(
                location / name, assembled / name,
                name == "com.eu.danmemo.apk",
                tools[:5], key, password,
            )
            if signer is not None and digest != signer:
                raise ValueError("Different signer for original game split: " + name)
            signer = digest
            patches.append({
                "split": name,
                "bytes": (assembled / name).stat().st_size,
                "sha256": client.sha256(assembled / name),
                "changed_archive_member_count": len(changes),
            })
        for record in patches:
            shutil.copy2(assembled / record["split"], out / record["split"])
    output = {
        "status": "ORIGINAL_CLIENT_SPLIT_BUILD_COMPLETE_NOT_PLAYABILITY_PROOF",
        "package": client.PRIVATE_PACKAGE,
        "loopback_endpoint": client.ENDPOINT,
        "original_xapk_sha256": verified["xapk_sha256"],
        "native_sha256": verified["native_sha256"],
        "signer_certificate_sha256": signer,
        "signed_split_apks": patches,
        "requires_offline_listener": True,
        "requires_verified_owner_content_archive": True,
        "outstanding_reference_mismatches": 12,
        "ayn_thor_runtime_verified": False,
        "full_original_gameplay_verified": False,
    }
    # Output only hashes/metadata; never write private signing password.
    (out / "BUILD-METADATA.json").write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xapk", type=Path, default=client.ARM64_XAPK,
                        help="Untouched local EU 15.1.0 XAPK, not committed to Git")
    parser.add_argument("--output-dir", type=Path, default=client.ARM64_OUTPUT,
                        help="Private local output for six signed APK splits")
    parser.add_argument("--verify-only", action="store_true",
                        help="Verify fingerprints and ZIP members without writing anything")
    args = parser.parse_args()
    try:
        info = (verify_source(args.xapk) if args.verify_only else
                build_original_arm64(args.xapk, args.output_dir))
    except (OSError, RuntimeError, ValueError, zipfile.BadZipFile) as exc:
        parser.error(str(exc))
    print(json.dumps(info, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
