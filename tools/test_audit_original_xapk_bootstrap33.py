"""Synthetic original-XAPK Phase1 reference scanner tests. No game bytes."""
import hashlib
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

import audit_original_xapk_bootstrap33 as scanner


def target(name, content):
    return {"path":name,"size":len(content),
            "md5":hashlib.md5(content).hexdigest()}


def fake_catalogue():
    return [
        target("1/files/ui/title/synthetic_%02d.png" % i,
               ("synthetic fake content %02d" % i).encode("utf-8"))
        for i in range(33)
    ]


def build_xapk(path, members):
    inner=BytesIO()
    with zipfile.ZipFile(inner,"w") as apk:
        for name,content in members:
            apk.writestr(name,content)
    with zipfile.ZipFile(path,"w") as outer:
        outer.writestr("com.eu.danmemo.apk",inner.getvalue())


class BootstrapOriginalSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.xapk=self.root/"fake.xapk"
        self.targets=fake_catalogue()
        self.index=self.root/"targets.json"
        self.index.write_text(json.dumps({
            "format":"DANMEMORE_LEGACY_BOOTSTRAP_33_REFERENCE_V1",
            "targets":self.targets,
        }),encoding="utf-8")

    def test_exact_expected_path_and_md5(self):
        first=self.targets[0]
        content=b"synthetic fake content 00"
        build_xapk(self.xapk,[("assets/common/files/ui/title/synthetic_00.png",content)])
        report=scanner.scan_original_xapk_members(self.xapk,scanner.load_index(self.index))
        self.assertEqual(report["verified_reference_index_count"],33)
        self.assertEqual(report["nested_apks_scanned"],1)
        self.assertEqual(report["expected_path_exact_count"],1)
        self.assertEqual(report["alternate_path_exact_count"],0)
        self.assertEqual(report["any_md5_exact_count"],1)
        self.assertEqual(len(report["targets"][first["path"]]["exact_md5_at_expected_apk_path"]),1)
        self.assertFalse(report["original_asset_bytes_written"])
        self.assertFalse(report["original_import_authorized"])

    def test_alternate_path_is_never_autoclassified_expected_path(self):
        content=b"synthetic fake content 00"
        build_xapk(self.xapk,[("assets/foreign/synthetic_00.png",content)])
        report=scanner.scan_original_xapk_members(self.xapk,scanner.load_index(self.index))
        self.assertEqual(report["expected_path_exact_count"],0)
        self.assertEqual(report["alternate_path_exact_count"],1)
        self.assertFalse(report["original_import_authorized"])

    def test_wrong_size_and_same_size_other_bytes_are_separate(self):
        build_xapk(self.xapk,[("assets/files/ui/title/synthetic_00.png",b"other")])
        result=scanner.scan_original_xapk_members(self.xapk,scanner.load_index(self.index))
        self.assertEqual(result["any_md5_exact_count"],0)
        self.assertEqual(result["targets"][self.targets[0]["path"]]["wrong_size_entries"],1)
        original=b"synthetic fake content 00"
        build_xapk(self.xapk,[("assets/files/ui/title/synthetic_00.png",b"Z"*len(original))])
        result=scanner.scan_original_xapk_members(self.xapk,scanner.load_index(self.index))
        self.assertEqual(result["targets"][self.targets[0]["path"]]["same_size_wrong_md5_entries"],1)

    def test_same_md5_in_other_path_is_not_a_valid_expected_name(self):
        # Two expected paths may share the same MD5 and same basename.
        content=b"same original-style placeholder"
        self.targets[1]=target("1/files/other/synthetic_00.png",content)
        self.targets[0]=target("1/files/ui/title/synthetic_00.png",content)
        self.index.write_text(json.dumps({
            "format":"DANMEMORE_LEGACY_BOOTSTRAP_33_REFERENCE_V1",
            "targets":self.targets
        }))
        build_xapk(self.xapk,[("assets/common/files/ui/title/synthetic_00.png",content)])
        r=scanner.scan_original_xapk_members(self.xapk,scanner.load_index(self.index))
        self.assertEqual(r["expected_path_exact_count"],1)
        self.assertEqual(r["alternate_path_exact_count"],1)

    def test_reject_duplicate_catalogue_path(self):
        self.targets[1]=dict(self.targets[0])
        self.index.write_text(json.dumps({
            "format":"DANMEMORE_LEGACY_BOOTSTRAP_33_REFERENCE_V1",
            "targets":self.targets
        }))
        with self.assertRaisesRegex(ValueError,"unsafe or duplicate"):
            scanner.load_index(self.index)

    def test_reject_catalogue_traversal(self):
        self.targets[0]["path"]="1/files/../../secrets.txt"
        self.index.write_text(json.dumps({
            "format":"DANMEMORE_LEGACY_BOOTSTRAP_33_REFERENCE_V1",
            "targets":self.targets
        }))
        with self.assertRaisesRegex(ValueError,"unsafe or duplicate"):
            scanner.load_index(self.index)

    def test_symlink_entry_is_not_scanned(self):
        first=self.targets[0]
        fake=zipfile.ZipInfo("assets/common/files/ui/title/synthetic_00.png")
        fake.create_system=3
        fake.external_attr=(0o120777<<16)
        inner=BytesIO()
        with zipfile.ZipFile(inner,"w") as apk:
            apk.writestr(fake,b"synthetic fake content 00")
        with zipfile.ZipFile(self.xapk,"w") as outer:
            outer.writestr("com.eu.danmemo.apk",inner.getvalue())
        report=scanner.scan_original_xapk_members(self.xapk,scanner.load_index(self.index))
        self.assertEqual(report["any_md5_exact_count"],0)
        self.assertEqual(report["targets"][first["path"]]["same_basename_entries"],0)

    def test_bad_nested_apk_is_rejected(self):
        with zipfile.ZipFile(self.xapk,"w") as outer:
            outer.writestr("com.eu.danmemo.apk",b"not an APK")
        with self.assertRaises(zipfile.BadZipFile):
            scanner.scan_original_xapk_members(self.xapk,scanner.load_index(self.index))

    def test_no_nested_apk_is_rejected(self):
        with zipfile.ZipFile(self.xapk,"w") as outer:
            outer.writestr("readme.txt",b"test")
        with self.assertRaisesRegex(ValueError,"unexpected number"):
            scanner.scan_original_xapk_members(self.xapk,scanner.load_index(self.index))


if __name__=="__main__":
    unittest.main()
