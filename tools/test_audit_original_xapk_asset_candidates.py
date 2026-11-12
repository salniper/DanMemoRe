"""Synthetic-only provenance checks: no original game bytes or APK committed."""
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import audit_original_xapk_asset_candidates as audit


def archive(entries):
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as out:
        for name, payload in entries:
            out.writestr(name, payload)
    return stream.getvalue()


class OriginalXapkCandidateTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.file = Path(temp.name) / "original.xapk"

    def make_xapk(self, nested=None):
        if nested is None:
            nested = {"com.eu.danmemo.apk": archive([
                ("assets/common/files/font/number.png", b"synthetic candidate"),
            ])}
        self.file.write_bytes(archive(nested.items()))

    def test_no_matching_hash_means_no_proof(self):
        self.make_xapk()
        result = audit.scan_members(self.file)
        self.assertEqual(result["reference_exact_target_count"], 0)
        self.assertEqual(result["targets"]["1/files/font/number.png"]
                         ["basename_occurrences"], 1)
        self.assertFalse(result["legacy_import_authorized"])

    def test_exact_hash_with_patched_synthetic_reference(self):
        payload = b"synthetic font"
        import hashlib
        self.make_xapk({"com.eu.danmemo.apk": archive([
            ("assets/common/files/font/number.png", payload),
        ])})
        with patch.dict(audit.REFERENCE, {
            "1/files/font/number.png": (len(payload),
                                        hashlib.md5(payload).hexdigest())
        }):
            result = audit.scan_members(self.file)
        self.assertEqual(result["reference_exact_target_count"], 1)
        record = result["targets"]["1/files/font/number.png"]
        self.assertEqual(record["reference_exact_occurrences"], 1)
        self.assertEqual(record["reference_exact_locations"][0]["apk"],
                         "com.eu.danmemo.apk")
        self.assertFalse(result["legacy_import_authorized"])

    def test_size_mismatch_is_not_a_hash_match(self):
        self.make_xapk({"config.arm64_v8a.apk": archive([
            ("files/font/number.png", b"bad"),
        ])})
        result = audit.scan_members(self.file)
        row = result["targets"]["1/files/font/number.png"]
        self.assertEqual(row["wrong_size_occurrences"], 1)
        self.assertEqual(row["reference_exact_occurrences"], 0)

    def test_unknown_name_not_promoted(self):
        self.make_xapk({"config.arm64_v8a.apk": archive([
            ("assets/nope.png", b"anything"),
        ])})
        result = audit.scan_members(self.file)
        self.assertEqual(sum(x["basename_occurrences"]
                             for x in result["targets"].values()), 0)

    def test_missing_nested_apk_rejected(self):
        self.file.write_bytes(archive([("metadata.json", b"{}")]))
        with self.assertRaisesRegex(ValueError, "nested APK count"):
            audit.scan_members(self.file)

    def test_oversize_nested_apk_rejected(self):
        self.make_xapk()
        with patch.object(audit, "MAX_SPLIT_SIZE", 10):
            with self.assertRaisesRegex(ValueError, "safety bound"):
                audit.scan_members(self.file)

    def test_invalid_nested_zip_rejected(self):
        self.make_xapk({"config.arm64_v8a.apk": b"not a ZIP"})
        with self.assertRaises(zipfile.BadZipFile):
            audit.scan_members(self.file)

    def test_validation_is_separate_and_mandatory_in_cli(self):
        # Pure scan_members is testable with synthetic ZIPs; main() must
        # authenticate the original XAPK SHA and native SHA before scanning.
        self.make_xapk()
        argv = ["tool", "--xapk", str(self.file)]
        with patch("sys.argv", argv):
            with patch.object(audit, "inspect_xapk",
                              side_effect=ValueError("wrong original SHA")):
                with self.assertRaisesRegex(ValueError, "wrong original SHA"):
                    audit.main()

    def test_symlink_nested_candidate_ignored(self):
        self.make_xapk()
        with zipfile.ZipFile(self.file) as outer:
            apk = outer.read("com.eu.danmemo.apk")
        with zipfile.ZipFile(BytesIO(apk)) as inner:
            info = inner.getinfo("assets/common/files/font/number.png")
        info.external_attr = 0o120777 << 16
        stream = BytesIO()
        with zipfile.ZipFile(stream, "w") as target:
            target.writestr(info, b"synthetic candidate")
        self.make_xapk({"com.eu.danmemo.apk": stream.getvalue()})
        self.assertEqual(audit.scan_members(self.file)
                         ["targets"]["1/files/font/number.png"]
                         ["basename_occurrences"], 0)


if __name__ == "__main__":
    unittest.main()
