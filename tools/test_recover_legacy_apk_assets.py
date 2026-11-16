"""No proprietary game assets needed: synthetic tests for APK recovery safeguards."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

import recover_legacy_apk_assets as recovery


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.contents = root / "contents"
        (self.contents / "1").mkdir(parents=True)
        self.apk = root / "original.apk"
        self.audit = root / "audit.json"
        self.targets = {}
        manifest = {"assets": {}}
        issues = []
        with ZipFile(self.apk, "w") as out:
            for index in range(33):
                relative = f"files/ui/title/synthetic_{index:02d}.dat"
                target = f"1/{relative}"
                data = f"synthetic fixture #{index}".encode()
                size = len(data)
                md5 = hashlib.md5(data).hexdigest()
                self.targets[target] = data
                out.writestr(f"assets/common/{relative}", data)
                manifest["assets"][relative] = {"size": size, "md5": md5}
                issues.append({
                    "path": target,
                    "status": "missing_with_historical_entry",
                    "reference_md5": md5,
                    "reference_size": size,
                    "historical_md5": md5,
                    "historical_size": size,
                })
        self.audit.write_text(json.dumps({"issues": issues}), encoding="utf-8")
        self.manifest_path = self.contents / "1/project.manifest"
        self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        old_apk = recovery.KNOWN_APK_SHA256
        old_manifest = recovery.KNOWN_PHASE1_MANIFEST_SHA256
        recovery.KNOWN_APK_SHA256 = recovery.digest(self.apk)
        recovery.KNOWN_PHASE1_MANIFEST_SHA256 = recovery.digest(self.manifest_path)
        self.addCleanup(setattr, recovery, "KNOWN_APK_SHA256", old_apk)
        self.addCleanup(setattr, recovery, "KNOWN_PHASE1_MANIFEST_SHA256", old_manifest)

    def invoke(self, apply=False, contents=True):
        with contextlib.redirect_stdout(io.StringIO()):
            recovery.recover(self.apk, self.audit,
                             self.contents if contents else None, apply)

    def test_read_only_without_contents(self):
        self.invoke(contents=False)
        self.assertFalse(any((self.contents / p).exists() for p in self.targets))

    def test_dry_run_does_not_write(self):
        self.invoke()
        self.assertFalse(any((self.contents / p).exists() for p in self.targets))

    def test_apply_only_missing_and_idempotent(self):
        self.invoke(apply=True)
        self.invoke(apply=True)
        for name, expected in self.targets.items():
            self.assertEqual((self.contents / name).read_bytes(), expected)

    def test_refuse_overwrite_of_existing_different_bytes(self):
        self.invoke(apply=True)
        name = next(iter(self.targets))
        path = self.contents / name
        path.write_bytes(b"do not overwrite this")
        with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
            self.invoke(apply=True)
        self.assertEqual(path.read_bytes(), b"do not overwrite this")

    def test_reject_changed_audit_fingerprint(self):
        report = json.loads(self.audit.read_text())
        report["issues"][0]["reference_md5"] = "f" * 32
        self.audit.write_text(json.dumps(report))
        with self.assertRaises(ValueError):
            self.invoke(apply=True)
        self.assertFalse(any((self.contents / p).exists() for p in self.targets))

    def test_reject_path_traversal(self):
        report = json.loads(self.audit.read_text())
        report["issues"][0]["path"] = "1/files/../../escape.bin"
        self.audit.write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, "unsafe or unexpected"):
            self.invoke(apply=True)

    def test_reject_modified_apk_checksum(self):
        with self.apk.open("ab") as handle:
            handle.write(b"tampered")
        with self.assertRaisesRegex(ValueError, "APK SHA-256"):
            self.invoke(apply=True)

    def test_apply_requires_contents(self):
        with self.assertRaisesRegex(ValueError, "requires --contents"):
            self.invoke(apply=True, contents=False)


if __name__ == "__main__":
    unittest.main()
