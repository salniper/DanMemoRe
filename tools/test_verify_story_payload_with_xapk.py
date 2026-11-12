"""Synthetic-only tests for private six-cipher original XAPK probe.

No native game binary, original story ciphertext or decryption key included.
"""
from io import BytesIO
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import verify_story_payload_with_xapk as m


def zip_data(files):
    output = BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return output.getvalue()


class OwnerStoryMasterProbeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.project = self.root / "project"
        (self.project / "tools").mkdir(parents=True)
        (self.project / "tools" / "inspect_story_command_compat.cjs").write_text(
            "// fake CLI entrypoint; never executes original app"
        )
        self.xapk = self.root / "pristine.xapk"
        self.native = b"synthetic ELF placeholder, not real ARM64"
        self.build(self.native)
        self.audit = self.root / "audit.json"
        self.audit.write_text(json.dumps({"issues": []}), encoding="utf-8")
        self.payload = self.root / "payload.json"
        self.payload.write_text(json.dumps({"files": []}), encoding="utf-8")
        self.samples = {name: ("fake " + str(index)).encode()
                        for index, name in enumerate(m.STORIES)}
        self.entries = {name: {
            "actual_size": len(data),
            "actual_md5": hashlib.md5(data).hexdigest(),
        } for name, data in self.samples.items()}
        self.verified = {
            "native_sha256": hashlib.sha256(self.native).hexdigest(),
            "source_archive_sha1": "synthetic test SHA",
        }
        self.report = {"file_count": 6, "results": [
            {"path": key, "decode_probe": "AES_CBC_ZLIB_INFLATE_FAILED"}
            for key in m.STORIES
        ], "verdict": "DO_NOT_IMPORT_UNVERIFIED_BYTES"}
        self.patcher = [
            patch.object(m, "inspect_xapk", return_value=self.verified),
            patch.object(m, "PINNED_SHA256", self.verified["native_sha256"]),
            patch.object(m, "audit_entries", return_value=self.entries),
            patch.object(m, "payload_candidates", return_value=self.samples),
        ]
        for item in self.patcher:
            item.start()
            self.addCleanup(item.stop)

    def build(self, native):
        nested = zip_data({m.LIBAPP_PATH: native})
        self.xapk.write_bytes(zip_data({m.ARM64_SPLIT: nested}))

    def run_probe(self, response=None):
        with patch.object(m.subprocess, "run", return_value=(
            response or subprocess.CompletedProcess(
                [], 0, json.dumps(self.report), ""
            )
        )) as exec_mock:
            result = m.probe(self.xapk, self.audit, self.payload,
                             project_root=self.project)
        return result, exec_mock

    def test_valid_synthetic_staging_and_no_import(self):
        root_is_clean_before = list(self.root.iterdir())
        result, command = self.run_probe()
        self.assertFalse(result["import_authorized"])
        self.assertEqual(result["six_story_probe"]["file_count"], 6)
        self.assertTrue(command.called)
        self.assertEqual(list(self.root.iterdir()), root_is_clean_before)
        args, kwargs = command.call_args
        self.assertEqual(kwargs["timeout"], 45)
        self.assertTrue(kwargs["capture_output"])

    def test_temp_contains_exact_six_cipher_paths_and_verified_native(self):
        def inspect_command(command, **_):
            native_path = Path(command[-1])
            self.assertEqual(native_path.read_bytes(), self.native)
            contents = Path(command[command.index("--contents") + 1])
            for path in m.STORIES:
                self.assertEqual((contents / path).read_bytes(), self.samples[path])
            self.assertEqual(len(list(contents.rglob("*.enc"))), 6)
            return subprocess.CompletedProcess(command, 0,
                                               json.dumps(self.report), "")
        with patch.object(m.subprocess, "run", side_effect=inspect_command):
            result = m.probe(self.xapk, self.audit, self.payload,
                             project_root=self.project)
        self.assertFalse(result["import_authorized"])

    def test_changed_audit_bytes_rejected(self):
        self.entries[m.STORIES[0]]["actual_md5"] = "0" * 32
        with patch.object(m.subprocess, "run") as command:
            with self.assertRaisesRegex(ValueError, "changed since owner audit"):
                m.probe(self.xapk, self.audit, self.payload, project_root=self.project)
            command.assert_not_called()

    def test_missing_story_cipher_refused(self):
        del self.samples[m.STORIES[0]]
        with self.assertRaisesRegex(ValueError, "must contain all six"):
            self.run_probe()

    def test_bad_original_xapk_never_stages_ciphers(self):
        with patch.object(m, "inspect_xapk", side_effect=ValueError("SHA mismatch")):
            with patch.object(m, "payload_candidates") as payloads:
                with self.assertRaisesRegex(ValueError, "SHA mismatch"):
                    self.run_probe()
                payloads.assert_not_called()

    def test_second_native_hash_check_refuses_changed_split(self):
        self.build(b"tampered original native")
        with patch.object(m.subprocess, "run") as command:
            with self.assertRaisesRegex(ValueError, "no longer matches"):
                m.probe(self.xapk, self.audit, self.payload,
                        project_root=self.project)
            command.assert_not_called()

    def test_node_nonzero_fails_closed(self):
        response = subprocess.CompletedProcess([], 1, "", "private internal error")
        with self.assertRaisesRegex(ValueError, "probe failed"):
            self.run_probe(response)

    def test_wrong_node_verdict_fails_closed(self):
        fake = dict(self.report, verdict="IMPORT_ALLOWED")
        response = subprocess.CompletedProcess([], 0, json.dumps(fake), "")
        with self.assertRaisesRegex(ValueError, "unexpectedly authorized"):
            self.run_probe(response)

    def test_missing_story_result_fails_closed(self):
        fake = dict(self.report, results=[])
        response = subprocess.CompletedProcess([], 0, json.dumps(fake), "")
        with self.assertRaisesRegex(ValueError, "incomplete six-file"):
            self.run_probe(response)


if __name__ == "__main__":
    unittest.main()
