"""Synthetic direct BL/B incoming X1 writers; no original game client bytes."""
import struct
import unittest

from test_inspect_native_novel_direct_callees import two_frame_fixture
from test_inspect_native_novel_unwind import anchors
import inspect_native_novel_unwind as unwind
import inspect_native_novel_executor_callers as callers


def fixture(kind="BL", move=True):
    binary=two_frame_fixture()
    if move:
        struct.pack_into("<I",binary,0x180,0xaa0003e1)  # MOV X1,X0
    branch=0x94000000 if kind=="BL" else 0x14000000
    diff=0x1000-0x1084
    struct.pack_into("<I",binary,0x184,branch|((diff>>2)&0x3ffffff))
    frames=unwind.find_executor_unwind_frames(binary,anchors(0x1010))
    return binary,frames


class OriginalExecutorCallerTests(unittest.TestCase):
    def test_original_fde_caller_bl_and_input_X1_copy_candidate(self):
        binary,frames=fixture()
        result=callers.inspect_direct_original_executor_callers(binary,frames)
        self.assertEqual(result["status"],
                         "ORIGINAL_EXECUTOR_FDE_DIRECT_CALLER_X1_SYNTAX_ONLY")
        self.assertEqual(result["direct_external_call_or_tail_jump_sites"],1)
        self.assertEqual(result["direct_bl_sites"],1)
        self.assertEqual(result["tail_b_candidate_sites"],0)
        self.assertEqual(result["call_sites_with_original_fde_and_cfg"],1)
        row=result["candidate_callers"][0]
        self.assertEqual(row["site_va"],0x1084)
        self.assertEqual(row["caller_fde_start_va"],0x1080)
        self.assertEqual(row["recognized_X1_writer_candidates"],[{
            "writer_va":0x1080,"writer_kind":"COPY_REGISTER",
            "from_register":0,"immediate":None,"byte_offset":None,
        }])
        self.assertFalse(row["incoming_X1_value_verified"])
        self.assertEqual(result["original_vtable_targets_verified"],0)
        self.assertEqual(result["original_opcode_handler_mappings_verified"],0)

    def test_original_tail_branch_is_not_called_verified_Cpp_method(self):
        binary,frames=fixture("B")
        report=callers.inspect_direct_original_executor_callers(binary,frames)
        self.assertEqual(report["direct_bl_sites"],0)
        self.assertEqual(report["tail_b_candidate_sites"],1)
        self.assertEqual(report["candidate_callers"][0]["kind"],
                         "DIRECT_B_TAIL_JUMP_CANDIDATE")

    def test_missing_X1_writer_is_explicitly_not_proven(self):
        binary,frames=fixture(move=False)
        report=callers.inspect_direct_original_executor_callers(binary,frames)
        item=report["candidate_callers"][0]
        self.assertEqual(item["recognized_X1_writer_candidates"],[])
        self.assertTrue(item["entry_path_without_recognized_X1_writer"])
        self.assertFalse(report["original_X1_runtime_object_verified"])

    def test_spoofed_unwind_provenance_fails_closed(self):
        binary,frames=fixture()
        frames["status"]="UNVERIFIED"
        with self.assertRaisesRegex(ValueError,"CIE/FDE reference proof"):
            callers.inspect_direct_original_executor_callers(binary,frames)

    def test_multiple_executor_CFI_regions_are_rejected(self):
        binary,frames=fixture()
        second=dict(frames["sites"][0])
        second["unwind_coverage"]=dict(second["unwind_coverage"])
        second["unwind_coverage"]["start_va"]=0x1080
        frames["sites"].append(second)
        with self.assertRaisesRegex(ValueError,"exactly one"):
            callers.inspect_direct_original_executor_callers(binary,frames)

    def test_no_direct_call_is_not_a_proven_runtime_invocation(self):
        binary,frames=fixture()
        struct.pack_into("<I",binary,0x184,0xd503201f)  # NOP
        report=callers.inspect_direct_original_executor_callers(binary,frames)
        self.assertEqual(report["direct_external_call_or_tail_jump_sites"],0)
        self.assertFalse(report["original_X1_runtime_object_verified"])


if __name__=="__main__":
    unittest.main()
