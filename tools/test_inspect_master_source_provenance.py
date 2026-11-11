"""Synthetic-only provenance tests; no proprietary game assets."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import inspect_master_source_provenance as check


class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.p = Path(self.tmp.name) / "master.json"
        self.sources = {
            "lotteryWeightGroup": {
                "path": "1/master/divide_enc/lotteryWeightGroup.enc",
                "sha256": "a" * 64,
                "rows": 12,
            }
        }
        self.p.write_text(json.dumps({"version": 1, "sources": self.sources,
                                      "characters": {"x": "large payload"}}))

    def test_stream_prefix_and_missing_name(self):
        result = check.report(self.p, ["lotteryWeightGroup", "subscription"])
        self.assertEqual(result["total_export_sources"], 1)
        self.assertEqual(result["results"][0]["source_sha256"], "a" * 64)
        self.assertEqual(result["results"][0]["rows"], 12)
        self.assertEqual(result["results"][1]["status"], "NOT_IN_MASTER_EXPORT")

    def test_invalid_source_hash_is_refused(self):
        self.sources["lotteryWeightGroup"]["sha256"] = "xyz"
        self.p.write_text(json.dumps({"sources": self.sources}))
        with self.assertRaisesRegex(ValueError, "invalid source metadata"):
            check.report(self.p, ["lotteryWeightGroup"])

    def test_wrong_source_path_is_refused(self):
        self.sources["lotteryWeightGroup"]["path"] = "1/../../bad.enc"
        self.p.write_text(json.dumps({"sources": self.sources}))
        with self.assertRaisesRegex(ValueError, "invalid source metadata"):
            check.report(self.p, ["lotteryWeightGroup"])

    def test_missing_sources_field_is_refused(self):
        self.p.write_text('{"version":1,"other":{}}')
        with self.assertRaisesRegex(ValueError, "no exported sources"):
            check.report(self.p, ["lotteryWeightGroup"])

    def test_sources_must_be_object(self):
        self.p.write_text('{"sources":[] }')
        with self.assertRaisesRegex(ValueError, "not an object"):
            check.report(self.p, ["lotteryWeightGroup"])

    def test_incomplete_sources_fails(self):
        self.p.write_text('{"sources":{"not-closed":')
        with self.assertRaisesRegex(ValueError, "incomplete or malformed"):
            check.report(self.p)


if __name__ == "__main__":
    unittest.main()
