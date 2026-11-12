"""Synthetic XAPK fingerprint and split-location tests; no game binaries included."""
import hashlib
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import verify_pristine_arm64_xapk as source


def apk_bytes(library: bytes, *, native_name=source.LIBAPP_PATH, duplicates=False):
    buf = BytesIO()
    with ZipFile(buf, "w") as archive:
        archive.writestr(native_name, library)
        if duplicates:
            archive.writestr(native_name, library)
    return buf.getvalue()


def xapk_bytes(split: bytes | None, *, split_name=source.ARM64_SPLIT, base=True):
    buf = BytesIO()
    with ZipFile(buf, "w") as archive:
        if base:
            archive.writestr(source.BASE_APK, b"synthetic-base")
        if split is not None:
            archive.writestr(split_name, split)
    return buf.getvalue()


class PristineArm64XapkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "original.xapk"
        self.library = b"synthetic NOT a real native binary"
        self.build(xapk_bytes(apk_bytes(self.library)))

    def build(self, payload: bytes):
        self.path.write_bytes(payload)
        self.archive_hash = hashlib.sha1(payload).hexdigest()

    def check(self, **kwargs):
        return source.inspect_xapk(
            self.path, archive_sha1=self.archive_hash,
            library_sha256=hashlib.sha256(self.library).hexdigest(), **kwargs
        )

    def test_exactly_pinned_synthetic_archive_and_native(self):
        result = self.check()
        self.assertEqual(result["native_sha256"], hashlib.sha256(self.library).hexdigest())
        self.assertFalse(result["import_authorized"])
        self.assertFalse(result.get("story_address_candidates"))
        self.assertEqual(result["remaining_legacy_mismatches"], 12)

    def test_no_scan_without_flag(self):
        with patch.object(source, "inspect") as scanner:
            self.check()
        scanner.assert_not_called()

    def test_scan_uses_authenticated_native_only(self):
        with patch.object(source, "inspect", return_value={"marker": "synthetic"}) as scanner:
            report = self.check(scan=True)
        scanner.assert_called_once_with(self.library)
        self.assertEqual(report["story_address_candidates"], {"marker": "synthetic"})
        self.assertFalse(report["import_authorized"])

    def test_context_requires_explicit_scan(self):
        with self.assertRaisesRegex(ValueError, "requires --scan"):
            self.check(context=True)

    def test_context_after_both_fingerprints_match(self):
        from unittest.mock import patch
        import inspect_native_novel_xref_context as context
        scan_result = {"markers": [], "status": "synthetic"}
        with patch.object(source, "inspect", return_value=scan_result) as scanner:
            with patch.object(context, "inspect_context",
                              return_value={"status": "bounded"}) as tracer:
                report = self.check(scan=True, context=True)
        scanner.assert_called_once_with(self.library)
        tracer.assert_called_once_with(self.library, scan_result)
        self.assertEqual(report["story_code_context"]["status"], "bounded")
        self.assertFalse(report["import_authorized"])

    def test_wrong_native_hash_cannot_reach_context(self):
        from unittest.mock import patch
        import inspect_native_novel_xref_context as context
        with patch.object(context, "inspect_context") as tracer:
            with self.assertRaisesRegex(ValueError, "libapp.so SHA-256"):
                source.inspect_xapk(self.path, archive_sha1=self.archive_hash,
                                    library_sha256="0" * 64, scan=True, context=True)
            tracer.assert_not_called()

    def test_wrong_archive_fingerprint_rejected(self):
        with self.assertRaisesRegex(ValueError, "XAPK fingerprint mismatch"):
            source.inspect_xapk(self.path, archive_sha1="0" * 40,
                                library_sha256=hashlib.sha256(self.library).hexdigest())

    def test_wrong_original_native_sha256_rejected(self):
        with self.assertRaisesRegex(ValueError, "libapp.so SHA-256"):
            source.inspect_xapk(self.path, archive_sha1=self.archive_hash,
                                library_sha256="0" * 64)

    def test_armv7_split_not_accepted_as_arm64(self):
        self.build(xapk_bytes(apk_bytes(self.library),
                              split_name="config.armeabi_v7a.apk"))
        with self.assertRaisesRegex(ValueError, "config.arm64_v8a"):
            self.check()

    def test_missing_base_apk_refused(self):
        self.build(xapk_bytes(apk_bytes(self.library), base=False))
        with self.assertRaisesRegex(ValueError, "com.eu.danmemo.apk"):
            self.check()

    def test_missing_native_library_refused(self):
        self.build(xapk_bytes(apk_bytes(self.library, native_name="lib/armeabi-v7a/libapp.so")))
        with self.assertRaisesRegex(ValueError, "lib/arm64-v8a/libapp.so"):
            self.check()

    def test_oversized_native_library_rejected(self):
        with patch.object(source, "MAX_LIBAPP_SIZE", len(self.library) - 1):
            with self.assertRaisesRegex(ValueError, "oversized"):
                self.check()

    def test_symlinked_archive_refused(self):
        link = self.path.parent / "link.xapk"
        link.symlink_to(self.path)
        with self.assertRaisesRegex(ValueError, "symlinked"):
            source.inspect_xapk(link)

    def test_non_zip_with_matched_fingerprint_still_rejected(self):
        self.build(b"NOT AN XAPK")
        with self.assertRaisesRegex(Exception, "zip"):
            self.check()

    def test_duplicate_libapp_rejected(self):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            self.build(xapk_bytes(apk_bytes(self.library, duplicates=True)))
        with self.assertRaisesRegex(ValueError, "exactly one lib/arm64-v8a/libapp.so"):
            self.check()


if __name__ == "__main__":
    unittest.main()
