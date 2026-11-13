"""Offline only tests for the owner-side pristine-XAPK recovery wrapper."""
import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import restore_bootstrap33_pinned_local as wrapper


class _FakeResponse:
    def __init__(self, payload=b"synthetic-XAPK-not-a-game", url="https://cdn.example.invalid/pinned.xapk",
                 declared=None):
        self.file = io.BytesIO(payload)
        self.headers = {} if declared is None else {"Content-Length": str(declared)}
        self.url = url

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.file.close()

    def read(self, size):
        return self.file.read(size)

    def geturl(self):
        return self.url


class _FakeOpener:
    def __init__(self, response):
        self.response = response

    def open(self, request, timeout):
        return self.response


class LocalSourceBootstrapTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.target=self.root/"new-only"

    def test_pinned_https_payload_download_and_sha1(self):
        payload=b"tiny synthetic non-game payload"
        with patch.object(wrapper.urllib.request, "build_opener",
                          return_value=_FakeOpener(_FakeResponse(payload))), (
                patch.object(wrapper, "PINNED_XAPK_SHA1",
                             hashlib.sha1(payload).hexdigest())):
            path=self.root/"candidate.xapk"
            report=wrapper.download_pinned_source(path)
        self.assertEqual(path.read_bytes(),payload)
        self.assertEqual(report["temporary_download_bytes"],len(payload))
        self.assertEqual(report["source_archive_sha1"],
                         hashlib.sha1(payload).hexdigest())

    def test_mismatched_sha_cleans_temporary_download(self):
        path=self.root/"bad.xapk"
        with patch.object(wrapper.urllib.request,"build_opener",
                          return_value=_FakeOpener(_FakeResponse())), (
                patch.object(wrapper,"PINNED_XAPK_SHA1","0"*40)):
            with self.assertRaisesRegex(ValueError,"SHA-1 mismatch"):
                wrapper.download_pinned_source(path)
        self.assertFalse(path.exists())

    def test_https_downgrade_rejected_and_no_written_file(self):
        path=self.root/"bad-redirect.xapk"
        response=_FakeResponse(url="http://cdn.example.invalid/insecure.xapk")
        with patch.object(wrapper.urllib.request,"build_opener",
                          return_value=_FakeOpener(response)):
            with self.assertRaisesRegex(ValueError,"outside HTTPS"):
                wrapper.download_pinned_source(path)
        self.assertFalse(path.exists())

    def test_oversized_declared_length_rejected_before_write(self):
        path=self.root/"oversize.xapk"
        response=_FakeResponse(declared=wrapper.MAX_XAPK_SIZE+1)
        with patch.object(wrapper.urllib.request,"build_opener",
                          return_value=_FakeOpener(response)):
            with self.assertRaisesRegex(ValueError,"size cap"):
                wrapper.download_pinned_source(path)
        self.assertFalse(path.exists())

    def test_existing_owner_xapk_never_downloaded(self):
        source=self.root/"my.xapk"
        source.write_bytes(b"synthetic")
        with patch.object(wrapper,"download_pinned_source") as download, (
                patch.object(wrapper,"stage",return_value={
                    "status":"SOURCE_EXACT_VERIFIED_DRY_RUN_NO_RESOURCE_FILES_WRITTEN",
                    "restored_resource_files":0,
                }) as stage):
            result=wrapper.restore(index=self.root/"index",output=self.target,
                                   xapk=source,apply=False)
        download.assert_not_called()
        stage.assert_called_once_with(source,self.root/"index",self.target,apply=False)
        self.assertEqual(result["source_acquisition"],"EXISTING_OWNER_FILE")
        self.assertFalse(result["downloaded_temporary_source_retained"])

    def test_default_download_discarded_even_after_successful_staging(self):
        seen=[]
        def mocked_download(path):
            path.write_bytes(b"synthetic")
            seen.append(path)
            return {"temporary_download_bytes":9}
        def mocked_stage(source,index,output,apply):
            self.assertTrue(source.exists())
            self.assertTrue(apply)
            return {"status":"PARTIAL_ORIGINAL_BOOTSTRAP33_RESTORED_NOT_IMPORTABLE",
                    "restored_resource_files":33}
        with patch.object(wrapper,"download_pinned_source",mocked_download), (
                patch.object(wrapper,"stage",mocked_stage)):
            result=wrapper.restore(index=self.root/"index",output=self.target,
                                   xapk=None,apply=True)
        self.assertEqual(result["restored_resource_files"],33)
        self.assertEqual(result["source_acquisition"],
                         "HTTPS_DOWNLOAD_EXACT_PINNED_ARCHIVE")
        self.assertFalse(seen[0].exists())
        self.assertFalse(seen[0].parent.exists())

    def test_existing_overlay_blocks_operation_before_network(self):
        self.target.mkdir()
        sentinel=self.target/"save"
        sentinel.write_text("untouched")
        with patch.object(wrapper,"download_pinned_source") as download:
            with self.assertRaisesRegex(ValueError,"refusing to replace"):
                wrapper.restore(index=self.root/"index",output=self.target,
                                xapk=None,apply=True)
        download.assert_not_called()
        self.assertEqual(sentinel.read_text(),"untouched")

    def test_https_redirect_handler_rejects_http(self):
        handler=wrapper._HttpsOnlyRedirect()
        with self.assertRaisesRegex(ValueError,"redirect is not HTTPS"):
            handler.redirect_request(None,None,302,"Redirect",{},"http://example.invalid/foo")


if __name__ == "__main__":
    unittest.main()
