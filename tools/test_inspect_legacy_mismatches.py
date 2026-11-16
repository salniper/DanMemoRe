"""Synthetic read-only tests for historical mismatch diagnostics (no game assets)."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zlib
import struct

import inspect_legacy_mismatches as forensic


def crc_chunk(kind, payload):
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(
        ">I", zlib.crc32(kind + payload) & 0xFFFFFFFF
    )


def tiny_png():
    raw = b"\x00\xff\x00\x00\xff"
    return (b"\x89PNG\r\n\x1a\n"
            + crc_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
            + crc_chunk(b"IDAT", zlib.compress(raw))
            + crc_chunk(b"IEND", b""))


FILES = (
    ["1/manifests/phase.manifest." + x for x in ("1", "2", "3", "4", "6", "7", "8")]
    + ["1/master/divide_novel_command_enc/novelCommand" + x + ".enc"
       for x in ("751040548", "751040550", "751040806", "751040815", "751041273", "751041275")]
    + ["1/master/divide_enc/" + x + ".enc"
       for x in ("adventureMission", "downloadVoicePhase", "lotteryWeightGroup", "subscription")]
    + ["1/files/font/number.png", "3/files/ui_atlas/home_gacha/gacha_top_move_parts_text.json"]
)


class TestMismatchTriage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.contents = self.base / "contents"
        self.contents.mkdir()
        self.audit = self.base / "audit.json"
        self.rows = []
        for path in FILES:
            if path.endswith(".png"):
                data = tiny_png()
            elif path.endswith(".json"):
                data = b'{"atlas": {"test": true}}'
            elif "/manifests/" in path:
                data = b'{"version":"2024","md5":"x"}'
            else:
                data = b"synthetic 16-byte payload" + b"\x00" * 8
            file = self.contents / path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(data)
            reference_bytes = b"X" * len(data)
            self.rows.append({
                "path": path, "status": "unverified_bytes",
                "reference_md5": hashlib.md5(reference_bytes).hexdigest(),
                "historical_md5": hashlib.md5(reference_bytes).hexdigest(),
                "actual_md5": hashlib.md5(data).hexdigest(),
                "reference_size": len(data),
                "historical_size": len(data),
                "actual_size": len(data),
            })
        self.audit.write_text(json.dumps({"issues": self.rows}), encoding="utf-8")

    def test_19_groups_and_metadata_only(self):
        r = forensic.inspect(self.audit)
        self.assertEqual(r["asset_count"], 19)
        self.assertEqual(r["verdict"], "DO_NOT_IMPORT_UNVERIFIED_BYTES")
        self.assertEqual(r["categories"], {
            "phase_metadata": 7, "story_command": 6, "game_catalog": 4,
            "font_png": 1, "gacha_json": 1
        })
        self.assertFalse(any("on_device_sha256" in x for x in r["items"]))

    def test_recheck_file_integrity_and_formats(self):
        before = [(r["path"], (self.contents / r["path"]).read_bytes()) for r in self.rows]
        result = forensic.inspect(self.audit, self.contents)
        self.assertEqual(len(result["items"]), 19)
        self.assertTrue(all(x["audit_recheck"] == "MATCH" for x in result["items"]))
        self.assertEqual(next(x for x in result["items"] if x["category"] == "font_png")["structural_check"], "VALID_PNG_CRC")
        self.assertEqual(next(x for x in result["items"] if x["category"] == "gacha_json")["structural_check"], "VALID_JSON")
        self.assertEqual(before, [(p, (self.contents / p).read_bytes()) for p, _ in before])

    def test_changed_since_audit_detected(self):
        (self.contents / FILES[0]).write_bytes(b"different")
        result = forensic.inspect(self.audit, self.contents)
        self.assertEqual(result["items"][0]["audit_recheck"], "CHANGED_SINCE_AUDIT")

    def test_invalid_png_crc_detected(self):
        name = "1/files/font/number.png"
        data = bytearray((self.contents / name).read_bytes())
        data[-5] ^= 0x7F
        (self.contents / name).write_bytes(data)
        result = forensic.inspect(self.audit, self.contents)
        item = next(x for x in result["items"] if x["category"] == "font_png")
        self.assertEqual(item["structural_check"], "BAD_PNG_CRC_OR_FORMAT")

    def test_symlink_refused(self):
        name = FILES[0]
        p = self.contents / name
        p.unlink()
        p.symlink_to(self.audit)
        with self.assertRaisesRegex(ValueError, "symlink refused"):
            forensic.inspect(self.audit, self.contents)

    def test_path_traversal_refused(self):
        self.rows[0]["path"] = "1/../secret"
        self.audit.write_text(json.dumps({"issues": self.rows}))
        with self.assertRaisesRegex(ValueError, "unsafe report path"):
            forensic.inspect(self.audit)

    def test_unpinned_historical_hash_refused(self):
        self.rows[0]["historical_md5"] = "a" * 32
        self.audit.write_text(json.dumps({"issues": self.rows}))
        with self.assertRaisesRegex(ValueError, "fingerprint relationship"):
            forensic.inspect(self.audit)

    def test_unexpected_count_refused(self):
        self.audit.write_text(json.dumps({"issues": self.rows[:18]}))
        with self.assertRaisesRegex(ValueError, "expected exactly 19"):
            forensic.inspect(self.audit)

    def test_duplicate_refused(self):
        self.rows[-1]["path"] = self.rows[0]["path"]
        self.audit.write_text(json.dumps({"issues": self.rows}))
        with self.assertRaisesRegex(ValueError, "duplicate mismatch"):
            forensic.inspect(self.audit)


if __name__ == "__main__":
    unittest.main()
