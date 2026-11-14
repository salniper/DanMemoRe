"""Synthetic, fail-closed tests; no proprietary source bytes are committed."""
import base64
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile
import zlib

import verify_remaining_legacy_candidates as checker


def md5(data):
    return hashlib.md5(data).hexdigest()


def chunk(kind, payload):
    return (struct.pack(">I", len(payload)) + kind + payload +
            struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff))


def png():
    ihdr = struct.pack(">IIBBBBB", 109, 179, 8, 4, 0, 0, 0)
    rows = (b"\x00" + b"\x00\xff" * 109) * 179
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")


def layout():
    return json.dumps({"root": {"class": "Node",
        "childs": [{"class": "Sprite", "tag": i, "image": f"{i}.png"}
                   for i in range(1, 14)]}}).encode()


class CandidateAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.contents = self.root / "candidates"
        self.contents.mkdir()
        self.audit = {"issues": []}
        self.original = {}
        self.reference = {}
        for n, name in enumerate(checker.PHASES + checker.REMAINING):
            if name == checker.PNG:
                old = png()
            elif name == checker.ATLAS:
                old = layout()
            else:
                old = bytes([(n % 200) + 1]) * 32
            expected = b"Z" * len(old)
            self.original[name] = old
            self.reference[name] = expected
            self.audit["issues"].append({
                "path": name, "status": "unverified_bytes",
                "reference_size": len(old), "historical_size": len(old),
                "actual_size": len(old), "reference_md5": md5(expected),
                "historical_md5": md5(expected), "actual_md5": md5(old)
            })

    def test_realistic_payload_is_not_auto_verified(self):
        data = {"files": [{"path": name, "data_base64": base64.b64encode(value).decode()}
                          for name, value in self.original.items()]}
        source = self.root / "payload.json"
        source.write_text(json.dumps(data), encoding="utf-8")
        result = checker.compare(self.audit, checker.payload_candidates(source))
        self.assertEqual(result["reference_exact_count"], 0)
        self.assertEqual(result["categories"]["SAME_AS_UNVERIFIED_BACKUP"], 12)
        self.assertEqual(result["verdict"], "NO_IMPORT_AUTHORIZATION")
        by_path = {item["path"]: item for item in result["files"]}
        self.assertEqual(by_path[checker.PNG]["format_probe"], "PNG_109x179_LA8")
        self.assertEqual(by_path[checker.ATLAS]["format_probe"], "JSON_13_SPRITES_STRUCTURALLY_CONSISTENT")
        self.assertEqual(by_path[checker.STORIES[0]]["format_probe"], "BLOCK_ALIGNED_ONLY")

    def test_exact_candidate_verified_but_import_still_blocked(self):
        name = checker.STORIES[0]
        dest = self.contents / name
        dest.parent.mkdir(parents=True)
        dest.write_bytes(self.reference[name])
        result = checker.compare(self.audit, checker.directory_candidates(self.contents))
        self.assertEqual(result["reference_exact_count"], 1)
        self.assertEqual(result["categories"]["ABSENT"], 11)
        self.assertEqual(result["verdict"], "NO_IMPORT_AUTHORIZATION")

    def test_other_candidate_wrong_size(self):
        name = checker.PNG
        target = self.contents / name
        target.parent.mkdir(parents=True)
        target.write_bytes(b"not a png")
        result = checker.compare(self.audit, checker.directory_candidates(self.contents))
        by_path = {item["path"]: item for item in result["files"]}
        self.assertEqual(by_path[name]["status"], "WRONG_SIZE")

    def test_other_candidate_unknown_md5(self):
        name = checker.MASTERS[0]
        target = self.contents / name
        target.parent.mkdir(parents=True)
        target.write_bytes(b"q" * 32)
        result = checker.compare(self.audit, checker.directory_candidates(self.contents))
        by_path = {item["path"]: item for item in result["files"]}
        self.assertEqual(by_path[name]["status"], "OTHER_UNVERIFIED")

    def test_invalid_audit_missing_path_rejected(self):
        self.audit["issues"].pop()
        with self.assertRaisesRegex(ValueError, "exactly the known 19"):
            checker.compare(self.audit, self.original)

    def test_conflicting_historical_fingerprint_rejected(self):
        self.audit["issues"][0]["historical_md5"] = "0" * 32
        with self.assertRaisesRegex(ValueError, "incompatible audit MD5s"):
            checker.compare(self.audit, self.original)

    def test_duplicate_payload_fails_closed(self):
        name = checker.PNG
        entry = {"path": name, "data_base64": base64.b64encode(self.original[name]).decode()}
        p = self.root / "payload.json"
        p.write_text(json.dumps({"files": [entry, entry]}))
        with self.assertRaisesRegex(ValueError, "duplicate payload"):
            checker.payload_candidates(p)

    def test_invalid_base64_fails_closed(self):
        p = self.root / "payload.json"
        p.write_text(json.dumps({"files": [{"path": checker.PNG, "data_base64": "***"}]}))
        with self.assertRaisesRegex(ValueError, "invalid base64"):
            checker.payload_candidates(p)

    def test_candidate_symlink_fails_closed(self):
        name = checker.STORIES[0]
        target = self.contents / name
        target.parent.mkdir(parents=True)
        external = self.root / "external"
        external.write_bytes(b"secret")
        target.symlink_to(external)
        with self.assertRaisesRegex(ValueError, "symlinked source"):
            checker.directory_candidates(self.contents)

    def test_source_not_modified_by_checks(self):
        name = checker.STORIES[1]
        target = self.contents / name
        target.parent.mkdir(parents=True)
        target.write_bytes(self.original[name])
        checker.compare(self.audit, checker.directory_candidates(self.contents))
        self.assertEqual(target.read_bytes(), self.original[name])


    def test_zip_candidates_root_and_contents_prefix(self):
        archive = self.root / "snapshot.zip"
        first = checker.STORIES[0]
        second = checker.PNG
        with zipfile.ZipFile(archive, "w") as out:
            out.writestr(first, self.reference[first])
            out.writestr("contents/" + second, self.original[second])
            out.writestr("unrelated/huge-file", b"do-not-use")
        original_sha = hashlib.sha256(archive.read_bytes()).hexdigest()
        values = checker.zip_candidates(archive)
        result = checker.compare(self.audit, values)
        self.assertEqual(result["reference_exact_count"], 1)
        self.assertEqual(result["categories"]["SAME_AS_UNVERIFIED_BACKUP"], 1)
        self.assertEqual(result["categories"]["ABSENT"], 10)
        self.assertEqual(result["verdict"], "NO_IMPORT_AUTHORIZATION")
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), original_sha)

    def test_zip_rejects_duplicate_logical_path(self):
        archive = self.root / "duplicate.zip"
        name = checker.MASTERS[0]
        with zipfile.ZipFile(archive, "w") as out:
            out.writestr(name, self.reference[name])
            out.writestr("contents/" + name, self.reference[name])
        with self.assertRaisesRegex(ValueError, "duplicate target"):
            checker.zip_candidates(archive)

    def test_zip_rejects_symlink_target(self):
        archive = self.root / "symlink.zip"
        name = checker.STORIES[1]
        entry = zipfile.ZipInfo(name)
        entry.create_system = 3
        entry.external_attr = (0o120777 << 16)
        with zipfile.ZipFile(archive, "w") as out:
            out.writestr(entry, b"../secret")
        with self.assertRaisesRegex(ValueError, "unsafe ZIP member"):
            checker.zip_candidates(archive)

    def test_zip_ignores_basename_matches_elsewhere(self):
        archive = self.root / "other.zip"
        name = checker.STORIES[2]
        with zipfile.ZipFile(archive, "w") as out:
            out.writestr("random/" + name, self.reference[name])
            out.writestr("../" + name, self.reference[name])
        self.assertEqual(checker.zip_candidates(archive), {})

    def test_zip_rejects_symlink_archive(self):
        archive = self.root / "actual.zip"
        with zipfile.ZipFile(archive, "w") as out:
            out.writestr(checker.PNG, self.reference[checker.PNG])
        alias = self.root / "alias.zip"
        alias.symlink_to(archive)
        with self.assertRaisesRegex(ValueError, "non-symlink"):
            checker.zip_candidates(alias)

    def test_zip_rejects_member_count_beyond_bound(self):
        archive = self.root / "few.zip"
        with zipfile.ZipFile(archive, "w") as out:
            out.writestr(checker.PNG, self.reference[checker.PNG])
        old = checker.MAX_ZIP_ENTRIES
        try:
            checker.MAX_ZIP_ENTRIES = 0
            with self.assertRaisesRegex(ValueError, "too many entries"):
                checker.zip_candidates(archive)
        finally:
            checker.MAX_ZIP_ENTRIES = old

    def test_zip_rejects_total_uncompressed_budget(self):
        archive = self.root / "budget.zip"
        with zipfile.ZipFile(archive, "w") as out:
            out.writestr(checker.MASTERS[0], b"12345678")
        old = checker.MAX_SELECTED_ZIP_BYTES
        try:
            checker.MAX_SELECTED_ZIP_BYTES = 4
            with self.assertRaisesRegex(ValueError, "total read bound"):
                checker.zip_candidates(archive)
        finally:
            checker.MAX_SELECTED_ZIP_BYTES = old


    def test_discover_renamed_reference_exact_and_old_backup(self):
        archive = self.root / "independent.zip"
        exact = checker.STORIES[0]
        old = checker.PNG
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("export/renamed.story", self.reference[exact])
            zf.writestr("unrelated/number_from_backup.bin", self.original[old])
            zf.writestr("unrelated/file.bin", b"unrelated data")
        sha = hashlib.sha256(archive.read_bytes()).hexdigest()
        report = checker.discover_zip_reference_bytes(self.audit, archive)
        targets = {r["target"]: r for r in report["targets"]}
        # Synthetic reference bytes are intentionally reused across
        # several 32-byte fixtures. One renamed candidate therefore
        # legitimately proves byte identity for multiple target hashes.
        self.assertGreaterEqual(report["reference_exact_target_count"], 1)
        self.assertEqual(report["candidate_zip_entries_hashed"], 2)
        self.assertEqual(targets[exact]["reference_exact_hits"], 1)
        self.assertEqual(targets[exact]["sample_locations"], ["export/renamed.story"])
        self.assertEqual(targets[old]["same_as_old_unverified_backup_hits"], 1)
        self.assertEqual(targets[old]["reference_exact_hits"], 0)
        self.assertEqual(report["verdict"], "DISCOVERY_ONLY_NO_IMPORT_AUTHORIZATION")
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), sha)

    def test_discover_rejects_unsafe_size_matching_path(self):
        archive = self.root / "unsafe.zip"
        data = self.reference[checker.STORIES[0]]
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("../malicious.enc", data)
        with self.assertRaisesRegex(ValueError, "unsafe size-matching"):
            checker.discover_zip_reference_bytes(self.audit, archive)

    def test_discover_rejects_symlink_matching_asset(self):
        archive = self.root / "symlink-discovery.zip"
        entry = zipfile.ZipInfo("other/asset")
        entry.create_system = 3
        entry.external_attr = 0o120777 << 16
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr(entry, self.reference[checker.STORIES[0]])
        with self.assertRaisesRegex(ValueError, "unsafe size-matching"):
            checker.discover_zip_reference_bytes(self.audit, archive)

    def test_discover_rejects_too_many_decompressed_bytes(self):
        archive = self.root / "bounded.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("alternate/name.enc", self.reference[checker.STORIES[0]])
        budget = checker.MAX_DISCOVERY_ZIP_BYTES
        try:
            checker.MAX_DISCOVERY_ZIP_BYTES = 1
            with self.assertRaisesRegex(ValueError, "read bound"):
                checker.discover_zip_reference_bytes(self.audit, archive)
        finally:
            checker.MAX_DISCOVERY_ZIP_BYTES = budget

    def test_discover_rejects_changed_reference_catalogue(self):
        archive = self.root / "known.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("renamed.dat", self.reference[checker.STORIES[0]])
        self.audit["issues"][0]["historical_md5"] = "0" * 32
        with self.assertRaisesRegex(ValueError, "incompatible audit MD5s"):
            checker.discover_zip_reference_bytes(self.audit, archive)


if __name__ == "__main__":
    unittest.main()
