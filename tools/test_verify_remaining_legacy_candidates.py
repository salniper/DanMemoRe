"""Synthetic, fail-closed tests; no proprietary source bytes are committed."""
import base64
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
