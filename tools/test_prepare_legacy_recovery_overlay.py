"""Synthetic tests for isolated 36-file legacy recovery overlay.

Fixtures contain no game assets, private keys, or third-party binary content.
"""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import prepare_legacy_recovery_overlay as overlay
import recover_legacy_apk_assets as recovery
import repair_verified_phase_manifests as repair


def md5(data):
    return hashlib.md5(data).hexdigest()


def sha(data):
    return hashlib.sha256(data).hexdigest()


class OverlayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.contents = root / "contents"
        self.contents.mkdir()
        self.apk = root / "eu.apk"
        self.audit = root / "audit.json"
        self.out = root / "overlay"
        self.assets = {}
        self.repairs = {}
        issues = []
        for i in range(33):
            name = f"1/files/asset{i}.bin"
            data = f"sample-asset-{i}".encode()
            self.assets[name] = data
            issues.append({
                "status": "missing_with_historical_entry", "path": name,
                "reference_size": len(data), "historical_size": len(data),
                "reference_md5": md5(data), "historical_md5": md5(data)
            })
        project = {"assets": {
            name.removeprefix("1/"): {"size": len(data), "md5": md5(data)}
            for name, data in self.assets.items()
        }}
        manifest = self.contents / "1/project.manifest"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps(project), encoding="utf-8")
        self.patch_manifest = patch.object(recovery, "KNOWN_PHASE1_MANIFEST_SHA256",
                                           sha(manifest.read_bytes()))
        self.patch_manifest.start()
        self.addCleanup(self.patch_manifest.stop)
        for n in (3, 6, 7):
            name = f"1/manifests/phase.manifest.{n}"
            old = repair.SOURCE_VERSION.decode()
            obj = {"assets": {}, "version": old,
                   "remoteManifestUrl": "/phase/" + old,
                   "remoteVersionUrl": "/version/" + old}
            source = json.dumps(obj).encode()
            fixed = source.replace(repair.SOURCE_VERSION, repair.REFERENCE_VERSION)
            target = self.contents / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source)
            self.repairs[name] = {
                "size": len(source),
                "source_sha256": sha(source),
                "repaired_sha256": sha(fixed),
                "reference_md5": md5(fixed)
            }
            issues.append({"status": "unverified_bytes", "path": name,
                           "reference_size": len(source), "reference_md5": md5(fixed),
                           "actual_md5": md5(source)})
        for i in range(16):
            issues.append({"status": "unverified_bytes", "path": f"1/files/unknown{i}.enc",
                           "reference_size": 16, "reference_md5": "0" * 32,
                           "actual_md5": "1" * 32})
        self.audit.write_text(json.dumps({"issues": issues}))
        with ZipFile(self.apk, "w") as archive:
            for name, data in self.assets.items():
                archive.writestr("assets/common/" + name.removeprefix("1/"), data)
        self.patch_apk = patch.object(overlay, "KNOWN_APK_SHA256", sha(self.apk.read_bytes()))
        self.patch_apk.start()
        self.addCleanup(self.patch_apk.stop)
        self.patch_repairs = patch.object(overlay, "REPAIRS", self.repairs)
        self.patch_repairs.start()
        self.addCleanup(self.patch_repairs.stop)

    def call(self, apply=False, out=None):
        return overlay.prepare(
            self.apk, self.audit, self.contents,
            out if out is not None else self.out, apply
        )

    def test_dry_run_keeps_source_intact(self):
        before = (self.contents / "1/project.manifest").read_bytes()
        result = self.call()
        self.assertEqual(result["verified_original_apk_assets"], 33)
        self.assertEqual(result["verified_repaired_phase_manifests"], 3)
        self.assertEqual(result["remaining_unverified_mismatches"], 16)
        self.assertFalse(result["applied"])
        self.assertFalse(self.out.exists())
        self.assertEqual((self.contents / "1/project.manifest").read_bytes(), before)

    def test_apply_creates_exact_36_byte_verified_copies(self):
        result = self.call(True)
        self.assertTrue(result["applied"])
        self.assertEqual(len([p for p in self.out.rglob("*") if p.is_file()]), 36)
        for name, data in self.assets.items():
            self.assertEqual((self.out / name).read_bytes(), data)
            self.assertFalse((self.contents / name).exists())
        for name in self.repairs:
            source = (self.contents / name).read_bytes()
            self.assertEqual((self.out / name).read_bytes(),
                             source.replace(repair.SOURCE_VERSION, repair.REFERENCE_VERSION))
            self.assertEqual(sha(source), self.repairs[name]["source_sha256"])

    def test_existing_folder_refused_even_dry_run(self):
        self.out.mkdir()
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.call(False)

    def test_output_inside_original_refused(self):
        with self.assertRaisesRegex(ValueError, "must be separate"):
            self.call(True, self.contents / "overlay")
        self.assertFalse((self.contents / "overlay").exists())

    def test_parent_of_original_refused(self):
        with self.assertRaisesRegex(ValueError, "must be separate"):
            self.call(True, self.contents.parent)

    def test_mutated_original_phase_rejected_before_write(self):
        path = self.contents / "1/manifests/phase.manifest.6"
        path.write_bytes(path.read_bytes() + b"X")
        with self.assertRaisesRegex(ValueError, "changed since audit"):
            self.call(True)
        self.assertFalse(self.out.exists())

    def test_unknown_apk_rejected_before_write(self):
        with self.apk.open("ab") as handle:
            handle.write(b"tampered")
        with self.assertRaisesRegex(ValueError, "APK SHA-256"):
            self.call(True)
        self.assertFalse(self.out.exists())

    def test_missing_source_reference_file_rejected(self):
        (self.contents / "1/project.manifest").unlink()
        with self.assertRaises((ValueError, FileNotFoundError)):
            self.call(True)
        self.assertFalse(self.out.exists())

    def test_changed_audit_count_rejected(self):
        data = json.loads(self.audit.read_text())
        data["issues"] = data["issues"][:-1]
        self.audit.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "exactly 19"):
            self.call(True)
        self.assertFalse(self.out.exists())

    def test_source_symlink_rejected(self):
        first = self.contents / "1/manifests/phase.manifest.3"
        copy = first.read_bytes()
        first.unlink()
        other = self.contents / "other-file"
        other.write_bytes(copy)
        first.symlink_to(other)
        with self.assertRaisesRegex(ValueError, "symlink refused"):
            self.call(True)
        self.assertFalse(self.out.exists())

    def test_existing_unexpected_asset_refused(self):
        name = next(iter(self.assets))
        path = self.contents / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"wrong")
        with self.assertRaisesRegex(ValueError, "unexpected source file"):
            self.call(True)
        self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main()
