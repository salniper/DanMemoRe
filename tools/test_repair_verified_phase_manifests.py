"""Synthetic regression tests; no game source bytes are redistributed."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import repair_verified_phase_manifests as fix


class VerifiedPhaseRepairTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.source = root / "contents"
        self.output = root / "fixed"
        self.filename = "1/manifests/phase.manifest.6"
        path = self.source / self.filename
        path.parent.mkdir(parents=True)
        old = fix.SOURCE_VERSION.decode()
        example = {
            "assets": {},
            "remoteManifestUrl": "/old/" + old,
            "remoteVersionUrl": "/old/" + old,
            "version": old + " phased",
        }
        self.original = json.dumps(example).encode()
        self.repaired = self.original.replace(fix.SOURCE_VERSION, fix.REFERENCE_VERSION)
        path.write_bytes(self.original)
        self.path = path
        item = {
            "size": len(self.original),
            "source_sha256": hashlib.sha256(self.original).hexdigest(),
            "repaired_sha256": hashlib.sha256(self.repaired).hexdigest(),
            "reference_md5": hashlib.md5(self.repaired).hexdigest(),
        }
        override = patch.object(fix, "REPAIRS", {self.filename: item})
        override.start()
        self.addCleanup(override.stop)

    def test_dry_run_no_write(self):
        self.assertEqual(fix.run(self.source, self.output, False), [self.filename])
        self.assertFalse(self.output.exists())

    def test_apply_to_separate_folder_only(self):
        fix.run(self.source, self.output, True)
        self.assertEqual((self.output / self.filename).read_bytes(), self.repaired)
        self.assertEqual(self.path.read_bytes(), self.original)

    def test_refuse_overwrite(self):
        fix.run(self.source, self.output, True)
        with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
            fix.run(self.source, self.output, True)

    def test_mismatched_source_rejected(self):
        self.path.write_bytes(self.original + b"modified")
        with self.assertRaisesRegex(ValueError, "unrecognized source bytes"):
            fix.run(self.source, self.output, True)
        self.assertFalse(self.output.exists())

    def test_cannot_write_inside_source(self):
        with self.assertRaisesRegex(ValueError, "must be separate"):
            fix.run(self.source, self.source / "repaired", True)

    def test_cannot_write_into_ancestor_of_source(self):
        with self.assertRaisesRegex(ValueError, "must be separate"):
            fix.run(self.source, self.source.parent, True)

    def test_apply_requires_output_folder(self):
        with self.assertRaisesRegex(ValueError, "requires --output-dir"):
            fix.run(self.source, None, True)

    def test_source_has_exactly_three_version_occurrences(self):
        changed = self.original.replace(fix.SOURCE_VERSION, fix.REFERENCE_VERSION, 1)
        spec = {
            "size": len(changed),
            "source_sha256": hashlib.sha256(changed).hexdigest(),
            "repaired_sha256": hashlib.sha256(self.repaired).hexdigest(),
            "reference_md5": hashlib.md5(self.repaired).hexdigest(),
        }
        with self.assertRaisesRegex(ValueError, "version field count"):
            fix.verified_repair(self.filename, changed, spec)


if __name__ == "__main__":
    unittest.main()
