"""Synthetic tests only: no proprietary APK, ARM64 image, or game data."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import inspect_native_novel_loader_markers as native


class NativeMarkerTests(unittest.TestCase):
    def test_literal_offset_and_missing_marker(self):
        report = native.scan(b"abc-novelCommand-xyz-novelCommand", ("novelCommand", "divide_enc"))
        self.assertEqual(report["results"][0]["file_offsets_decimal"], [4, 21])
        self.assertEqual(report["results"][0]["literal_count"], 2)
        self.assertEqual(report["results"][1]["literal_count"], 0)
        self.assertIn("not virtual addresses", report["warning"])

    def test_many_matches_are_bounded(self):
        report = native.scan(b".enc" * 30, (".enc",))
        self.assertEqual(report["results"][0]["literal_count"], 30)
        self.assertEqual(len(report["results"][0]["file_offsets_decimal"]), 20)
        self.assertTrue(report["results"][0]["offset_list_truncated"])

    def test_pinned_hash_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            image = Path(d) / "image.so"
            image.write_bytes(b"not-a-real-image")
            with self.assertRaisesRegex(ValueError, "not the independently pinned"):
                native.inspect_binary(image)

    def test_hash_validated_scan_via_synthetic_pin(self):
        with tempfile.TemporaryDirectory() as d:
            image = Path(d) / "image.so"
            sample = b"ELF-test-novelCommand"
            image.write_bytes(sample)
            with patch.object(native, "PINNED_SHA256", hashlib.sha256(sample).hexdigest()):
                report = native.inspect_binary(image)
            self.assertEqual(report["results"][2]["literal_count"], 1)
            self.assertEqual(report["binary_bytes"], len(sample))

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            image = Path(d) / "sample"
            image.write_bytes(b"test")
            alias = Path(d) / "alias"
            alias.symlink_to(image)
            with self.assertRaisesRegex(ValueError, "refusing symlink"):
                native.inspect_binary(alias)

    def test_empty_and_oversize_rejected_before_hash(self):
        with tempfile.TemporaryDirectory() as d:
            image = Path(d) / "empty"
            image.touch()
            with self.assertRaisesRegex(ValueError, "bounded size"):
                native.inspect_binary(image)
            with patch.object(native, "MAX_BINARY_SIZE", 2):
                image.write_bytes(b"long")
                with self.assertRaisesRegex(ValueError, "bounded size"):
                    native.inspect_binary(image)


if __name__ == "__main__":
    unittest.main()
