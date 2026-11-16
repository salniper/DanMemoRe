"""Pure synthetic 1,544-entry audit fixture, no archived game images."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import audit_phase3_lottery_background_files as checker


class Phase3PhysicalPresenceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.contents = self.root / "owner"
        self.contents.mkdir()
        self.audit = self.root / "audit.json"
        self.entries = []
        for i in range(1544):
            payload = ("fake image number %04d" % i).encode()
            self.entries.append({
                "phase": 3,
                "path": "3/files/lottery/background/%09d.png" % i,
                "status": "missing_from_historical_catalog",
                "reference_size": len(payload),
                "reference_md5": hashlib.md5(payload).hexdigest(),
            })
        self.write_index()

    def write_index(self):
        self.audit.write_text(json.dumps({"issues": self.entries}),
                              encoding="utf-8")

    def write_asset(self, index, data=None):
        item = self.entries[index]
        name = self.contents / item["path"]
        name.parent.mkdir(parents=True, exist_ok=True)
        name.write_bytes(("fake image number %04d" % index).encode()
                         if data is None else data)
        return name

    def test_exact_file_and_truly_absent_others_are_distinct(self):
        a = self.write_asset(0)
        report = checker.audit_phase3_files(self.audit, self.contents)
        self.assertEqual(report["reference_catalogue_only_count"], 1544)
        self.assertEqual(report["actual_reference_exact_file_count"], 1)
        self.assertEqual(report["known_absent_at_reference_path_count"], 1543)
        self.assertTrue(a.exists())
        self.assertFalse(report["owner_files_modified"])
        self.assertFalse(report["game_assets_import_authorized"])

    def test_md5_mismatch_and_size_mismatch_separately_reported(self):
        original = ("fake image number %04d" % 1).encode()
        self.write_asset(1, data=b"Z" * len(original))
        self.write_asset(2, data=b"fewer")
        report = checker.audit_phase3_files(self.audit, self.contents)
        self.assertEqual(report["result_counts"]["REFERENCE_MD5_MISMATCH"], 1)
        self.assertEqual(report["result_counts"]["REFERENCE_SIZE_MISMATCH"], 1)
        self.assertEqual(report["known_absent_at_reference_path_count"], 1542)
        self.assertFalse(report["game_assets_import_authorized"])

    def test_symlink_file_is_refused_even_if_target_matches(self):
        source = self.root / "copy.png"
        source.write_bytes(b"fake image number 0000")
        target = self.contents / self.entries[0]["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(source)
        report = checker.audit_phase3_files(self.audit, self.contents)
        self.assertEqual(report["result_counts"]["SYMLINK_PATH_REFUSED"], 1)
        self.assertEqual(report["actual_reference_exact_file_count"], 0)

    def test_bad_reference_md5_is_invalid_not_accepted(self):
        self.entries[0]["reference_md5"] = "0" * 31
        self.write_index()
        with self.assertRaisesRegex(ValueError, "unsafe or inconsistent"):
            checker.audit_phase3_files(self.audit, self.contents)

    def test_traversal_in_audit_is_rejected(self):
        self.entries[0]["path"] = "3/files/lottery/background/../../vault.png"
        self.write_index()
        with self.assertRaisesRegex(ValueError, "unsafe or inconsistent"):
            checker.audit_phase3_files(self.audit, self.contents)

    def test_duplicate_reference_is_rejected(self):
        self.entries[1]["path"] = self.entries[0]["path"]
        self.write_index()
        with self.assertRaisesRegex(ValueError, "unsafe or inconsistent"):
            checker.audit_phase3_files(self.audit, self.contents)

    def test_missing_entry_is_rejected(self):
        self.entries.pop()
        self.write_index()
        with self.assertRaisesRegex(ValueError, "exactly 1544"):
            checker.audit_phase3_files(self.audit, self.contents)

    def test_directory_at_expected_file_location_is_not_a_png(self):
        target = self.contents / self.entries[0]["path"]
        target.mkdir(parents=True)
        report = checker.audit_phase3_files(self.audit, self.contents)
        self.assertEqual(report["result_counts"]["NOT_REGULAR_FILE"], 1)
        self.assertEqual(report["actual_reference_exact_file_count"], 0)


if __name__ == "__main__":
    unittest.main()
