"""Only synthetic APK ZIP entries; no publisher game files in these tests."""
import hashlib
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import stage_original_xapk_bootstrap33 as stage


class StagingOriginalAssetsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.index=self.root/"reference.json"
        self.xapk=self.root/"sample.xapk"
        self.output=self.root/"new-restored-bootstrap"
        self.assets={}
        self.entries=[]
        for i in range(33):
            relative=f"1/files/ui/title/fake_original_{i:02d}.json"
            data=("fake-only-%02d" % i).encode()
            self.assets[relative]=data
            self.entries.append({"path":relative,"size":len(data),
                "md5":hashlib.md5(data).hexdigest()})
        self.index.write_text(json.dumps({
            "format":"DANMEMORE_LEGACY_BOOTSTRAP_33_REFERENCE_V1",
            "targets":self.entries}),encoding="utf-8")
        self.write_apk()
        patcher=patch.object(stage,"inspect_xapk",return_value={
            "source_archive_sha1":"synthetic",
            "native_sha256":"synthetic",
        })
        patcher.start()
        self.addCleanup(patcher.stop)

    def write_apk(self,skip=None):
        inner=BytesIO()
        with ZipFile(inner,"w") as apk:
            for name,raw in self.assets.items():
                if name==skip:
                    continue
                apk.writestr("assets/common/"+name[2:],raw)
        with ZipFile(self.xapk,"w") as outer:
            outer.writestr("com.eu.danmemo.apk",inner.getvalue())

    def test_read_only_verification_does_not_create_assets(self):
        result=stage.stage(self.xapk,self.index,self.output,False)
        self.assertEqual(result["verified_source_resources"],33)
        self.assertEqual(result["restored_resource_files"],0)
        self.assertFalse(result["original_archive_import_authorized"])
        self.assertFalse(self.output.exists())

    def test_apply_recovers_exactly_33_files_in_new_overlay_only(self):
        original_archive=self.xapk.read_bytes()
        report=stage.stage(self.xapk,self.index,self.output,True)
        self.assertEqual(report["restored_resource_files"],33)
        self.assertEqual(report["total_resource_bytes"],sum(map(len,self.assets.values())))
        self.assertEqual(report["remaining_reference_mismatches"],12)
        self.assertFalse(report["original_archive_import_authorized"])
        self.assertEqual(self.xapk.read_bytes(),original_archive)
        for name,raw in self.assets.items():
            self.assertEqual((self.output/name).read_bytes(),raw)
        metadata=json.loads((self.output/"RECOVERY_STATUS.json").read_text())
        self.assertEqual(metadata["restored_resource_files"],33)
        self.assertEqual(metadata["missing_historical_catalog_entries_not_repaired"],1544)

    def test_refuse_to_replace_any_existing_output(self):
        self.output.mkdir()
        (self.output/"dont-touch").write_text("remain")
        with self.assertRaisesRegex(ValueError,"output already exists"):
            stage.stage(self.xapk,self.index,self.output,True)
        self.assertEqual((self.output/"dont-touch").read_text(),"remain")

    def test_missing_source_file_blocks_entire_write(self):
        missing=self.entries[1]["path"]
        self.write_apk(skip=missing)
        with self.assertRaisesRegex(ValueError,"33/33 exact source"):
            stage.stage(self.xapk,self.index,self.output,True)
        self.assertFalse(self.output.exists())

    def test_bad_md5_never_outputs_partial_overlay(self):
        self.entries[0]["md5"]="0"*32
        self.index.write_text(json.dumps({
            "format":"DANMEMORE_LEGACY_BOOTSTRAP_33_REFERENCE_V1",
            "targets":self.entries}))
        with self.assertRaisesRegex(ValueError,"33/33 exact source"):
            stage.stage(self.xapk,self.index,self.output,True)
        self.assertFalse(self.output.exists())

    def test_second_apply_never_overwrites_verified_file(self):
        stage.stage(self.xapk,self.index,self.output,True)
        with self.assertRaisesRegex(ValueError,"output already exists"):
            stage.stage(self.xapk,self.index,self.output,True)

    def test_symlink_output_refused(self):
        linked=self.root/"different"
        linked.mkdir()
        self.output.symlink_to(linked,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,"output already exists"):
            stage.stage(self.xapk,self.index,self.output,True)

    def test_mismatched_nested_apk_structure_aborts(self):
        with ZipFile(self.xapk,"w") as outer:
            outer.writestr("com.eu.danmemo.apk",b"not a valid apk")
        with self.assertRaises(Exception):
            stage.stage(self.xapk,self.index,self.output,True)
        self.assertFalse(self.output.exists())


if __name__=="__main__":
    unittest.main()
