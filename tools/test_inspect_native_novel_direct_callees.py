"""Original-format synthetic ELF only. No game client or proprietary code."""
import struct
import unittest

from test_inspect_native_novel_unwind import fixture, anchors
import inspect_native_novel_unwind as unwind
import inspect_native_novel_direct_callees as callees


LABEL = "/source/UI/Novel/NovelCommand/Command/NovelCommandTalkShow.cpp"


def two_frame_fixture(callee=0x1080, has_second=True):
    blob = fixture()
    # Direct BL at virtual 0x1024, inside synthetic original caller FDE.
    delta = callee - 0x1024
    if delta % 4:
        raise ValueError("misaligned test BL target")
    struct.pack_into("<I", blob, 0x124, 0x94000000 | ((delta >> 2) & 0x03ffffff))
    if has_second:
        # CIE begins at file 0x800 VA 0x3000, new FDE at file 0x824 VA 0x3024.
        struct.pack_into("<I", blob, 0x824, 12)
        struct.pack_into("<I", blob, 0x828, 0x28)
        struct.pack_into("<i", blob, 0x82c, 0x1080 - 0x302c)
        struct.pack_into("<i", blob, 0x830, 0x30)
        # Original-format .eh_frame_hdr datarel sdata4 sorted index.
        struct.pack_into("<I", blob, 0x908, 2)
        struct.pack_into("<i", blob, 0x914, 0x1080 - 0x4000)
        struct.pack_into("<i", blob, 0x918, 0x3024 - 0x4000)
    return blob


def caller_reports(blob):
    frames = unwind.find_executor_unwind_frames(blob, anchors(0x1010))
    precise = unwind.summarize_verified_fde_instructions(blob, frames)
    return frames, precise


def source_report(label_va=0x1088):
    return {"labels": [{
        "kind": "ORIGINAL_HANDLER_CPP_PATH",
        "label": LABEL,
        "instruction_sites": [{
            "site_instruction_va": label_va,
            "pattern": "ADRP_ADD_CANDIDATE",
        }],
    }]}


class OriginalDirectCalleeTests(unittest.TestCase):
    def test_original_callee_unwind_and_source_metadata_same_region(self):
        blob = two_frame_fixture()
        frames, precise = caller_reports(blob)
        result = callees.inspect_direct_callees(blob, source_report(),
                                                frames, precise)
        self.assertEqual(result["status"], "ORIGINAL_BL_CALLEE_FDE_ASSOCIATIONS_ONLY")
        self.assertEqual(result["original_caller_direct_bl_sites"], 1)
        self.assertEqual(result["unique_direct_bl_targets"], 1)
        target = result["callees"][0]
        self.assertEqual(target["target_va"], 0x1080)
        self.assertEqual(target["source_call_sites"], [0x1024])
        self.assertEqual(target["fde_status"], "VALIDATED_EXECUTABLE_CALLEE_FDE")
        self.assertTrue(target["target_is_fde_entry"])
        self.assertEqual(target["unwind_start_va"], 0x1080)
        self.assertEqual(target["unwind_end_va_exclusive"], 0x10b0)
        self.assertEqual(target["novel_source_label_candidates_in_same_fde"], 1)
        self.assertEqual(target["novel_source_label_samples"][0]["label"], LABEL)
        self.assertFalse(target["constructor_or_dispatch_proven"])
        self.assertEqual(result["numeric_opcode_to_native_handler_proven"], 0)
        self.assertFalse(result["original_import_authorized"])

    def test_original_callee_without_novel_source_candidate_stays_unknown(self):
        blob = two_frame_fixture()
        frames, precise = caller_reports(blob)
        result = callees.inspect_direct_callees(blob, source_report(0x1050),
                                                frames, precise)
        self.assertEqual(result["callees"][0]["novel_source_label_candidates_in_same_fde"], 0)

    def test_nonexecutable_direct_call_destination_is_rejected(self):
        blob = two_frame_fixture(callee=0x2000)
        frames, precise = caller_reports(blob)
        result = callees.inspect_direct_callees(blob, source_report(), frames, precise)
        self.assertEqual(result["callees"][0]["fde_status"],
                         "TARGET_NOT_EXECUTABLE_ELF_SECTION")
        self.assertIsNone(result["callees"][0]["unwind_start_va"])

    def test_executable_target_outside_fde_remains_unmapped(self):
        blob = two_frame_fixture(callee=0x10e0)
        frames, precise = caller_reports(blob)
        result = callees.inspect_direct_callees(blob, source_report(), frames, precise)
        self.assertEqual(result["callees"][0]["fde_status"],
                         "NO_FDE_COVERAGE_AT_TARGET")
        self.assertEqual(result["numeric_opcode_to_native_handler_proven"], 0)

    def test_corrupt_original_second_fde_not_promoted(self):
        blob = two_frame_fixture()
        struct.pack_into("<I", blob, 0x828, 0x7fffff)
        frames, precise = caller_reports(blob)
        result = callees.inspect_direct_callees(blob, source_report(), frames, precise)
        self.assertEqual(result["callees"][0]["fde_status"], "UNVERIFIED_CALLEE_FDE")

    def test_truncated_call_report_rejected(self):
        blob = two_frame_fixture()
        frames, precise = caller_reports(blob)
        precise["regions"][0]["direct_call_sites_truncated"] = True
        with self.assertRaisesRegex(ValueError, "truncated"):
            callees.inspect_direct_callees(blob, source_report(), frames, precise)

    def test_corrupted_caller_fde_not_promoted(self):
        blob = two_frame_fixture()
        frames, precise = caller_reports(blob)
        frames["status"] = "NOT_PROVEN"
        with self.assertRaisesRegex(ValueError, "verified caller"):
            callees.inspect_direct_callees(blob, source_report(), frames, precise)

    def test_unverified_mapping_only_metadata(self):
        blob = two_frame_fixture()
        frames, precise = caller_reports(blob)
        result = callees.inspect_direct_callees(blob, source_report(), frames, precise)
        self.assertNotIn("proven_handler", result["callees"][0])
        self.assertTrue(all(not row["constructor_or_dispatch_proven"]
                            for row in result["callees"]))


if __name__ == "__main__":
    unittest.main()
