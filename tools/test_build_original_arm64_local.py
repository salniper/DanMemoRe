"""Tests only use generated fake XAPK splits, never copied game files."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import build_original_arm64_local as builder


def fake_xapk(path):
    with zipfile.ZipFile(path, "w") as bundle:
        for name in builder.client.ARM64_APKS:
            bundle.writestr(name, ("FAKE-SPLIT-ONLY-" + name).encode())
    return hashlib.sha256(path.read_bytes()).hexdigest()


class OriginalBuildGuardTests(unittest.TestCase):
    def test_reject_missing_source(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "Missing"):
                builder.verify_source(Path(temp)/"unavailable.xapk")

    def test_reject_sha_mismatch_before_unzipping(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/"bad.xapk"
            source.write_bytes(b"not a game or zip")
            with self.assertRaisesRegex(ValueError, "Unknown XAPK SHA-256"):
                builder.verify_source(source)

    def test_reject_symlink(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            real=root/"real.xapk"
            real.write_bytes(b"something")
            link=root/"link.xapk"
            link.symlink_to(real)
            with self.assertRaisesRegex(ValueError, "symlinked"):
                builder.verify_source(link)

    def test_verify_synthetic_pinned_split_inventory(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/"synthetic.xapk"
            digest=fake_xapk(source)
            with (patch.object(builder.client,"ARM64_XAPK_SHA256",digest),
                  patch.object(builder,"inspect_xapk",return_value={
                      "source_archive_sha1":"TEST-ONLY",
                      "native_sha256":"TEST-ONLY"})):
                result=builder.verify_source(source)
            self.assertEqual(result["original_split_count"],6)
            self.assertEqual(result["xapk_sha256"],digest)
            self.assertFalse(result["source_gameplay_acceptance"])

    def test_duplicate_split_name_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/"duplicate.xapk"
            with zipfile.ZipFile(source,"w") as bundle:
                for name in builder.client.ARM64_APKS:
                    bundle.writestr(name,b"TEST")
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore",UserWarning)
                    bundle.writestr(builder.client.ARM64_APKS[0],b"ANOTHER")
            digest=hashlib.sha256(source.read_bytes()).hexdigest()
            with (patch.object(builder.client,"ARM64_XAPK_SHA256",digest),
                  patch.object(builder,"inspect_xapk",return_value={
                      "source_archive_sha1":"TEST",
                      "native_sha256":"TEST"})):
                with self.assertRaisesRegex(ValueError,"exactly one"):
                    builder.verify_source(source)

    def test_synthetic_local_split_build_keeps_archive_and_secrets_private(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            source=root/"original.xapk"
            digest=fake_xapk(source)
            original=source.read_bytes()
            work=root/"work"
            work.mkdir()
            output=root/"output"
            def signed_fake(source_apk,output_apk,primary,tools,key,password):
                output_apk.parent.mkdir(parents=True,exist_ok=True)
                output_apk.write_bytes(b"SIGNED TEST ONLY " + source_apk.name.encode())
                return ([{"member":"TEST"}], "TEST-PINNED-CERT")
            with (patch.object(builder.client,"ARM64_XAPK_SHA256",digest),
                  patch.object(builder.client,"WORK",work),
                  patch.object(builder,"inspect_xapk",return_value={
                      "source_archive_sha1":"TEST-ONLY",
                      "native_sha256":"TEST-ONLY"}),
                  patch.object(builder,"android_build_tools",return_value=tuple(
                      root / n for n in ("zipalign","aapt","signer.jar","java","keytool","adb"))),
                  patch.object(builder,"_local_signer",return_value=(root/"mock-key", "PRIVATE")),
                  patch.object(builder.client,"patch_and_sign_apk",side_effect=signed_fake)):
                report=builder.build_original_arm64(source,output)
            self.assertEqual(len(report["signed_split_apks"]),6)
            self.assertEqual(report["package"],"com.eu.danmore")
            self.assertEqual(report["outstanding_reference_mismatches"],12)
            self.assertFalse(report["ayn_thor_runtime_verified"])
            self.assertEqual(original,source.read_bytes())
            self.assertEqual(len(list(output.glob("*.apk"))),6)
            metadata=(output/"BUILD-METADATA.json").read_text()
            self.assertNotIn("PRIVATE",metadata)
            self.assertNotIn("FAKE-SPLIT",metadata)
            self.assertEqual(json.loads(metadata)["signer_certificate_sha256"],
                             "TEST-PINNED-CERT")

    def test_no_partial_published_apks_if_signing_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            source=root/"source.xapk"
            digest=fake_xapk(source)
            work=root/"work"
            work.mkdir()
            output=root/"out"
            counter=[0]
            def fail_second(source_apk,output_apk,primary,tools,key,password):
                counter[0]+=1
                if counter[0]==2:
                    raise ValueError("unsupported original patch pattern")
                output_apk.parent.mkdir(parents=True,exist_ok=True)
                output_apk.write_bytes(b"TEST")
                return ([],"CERT")
            with (patch.object(builder.client,"ARM64_XAPK_SHA256",digest),
                  patch.object(builder.client,"WORK",work),
                  patch.object(builder,"inspect_xapk",return_value={
                      "source_archive_sha1":"TEST","native_sha256":"TEST"}),
                  patch.object(builder,"android_build_tools",return_value=tuple(
                      root/n for n in ("zipalign","aapt","signer","java","keytool","adb"))),
                  patch.object(builder,"_local_signer",return_value=(root/"mock","SECRET")),
                  patch.object(builder.client,"patch_and_sign_apk",side_effect=fail_second)):
                with self.assertRaisesRegex(ValueError,"unsupported original"):
                    builder.build_original_arm64(source,output)
            self.assertEqual(list(output.glob("*.apk")),[])


if __name__ == "__main__":
    unittest.main()
