"""Synthetic ARM64 function-neighborhood classifications, never game code."""
import struct
import unittest

import inspect_native_novel_executor_flow as flow
import inspect_native_novel_dispatch_seeds as source
from test_inspect_native_novel_dispatch_seeds import synthetic


EXECUTOR_LABEL = (
    b"/tmp/original/source/UI/Novel/NovelCommand/NovelCommandExecuter.cpp"
)


def make_executor():
    blob = synthetic()
    blob[0x180:0x200] = b"\0" * 128
    blob[0x180:0x180 + len(EXECUTOR_LABEL)] = EXECUTOR_LABEL
    blob[0x180 + len(EXECUTOR_LABEL)] = 0
    # Importantly: the instruction stream is only in .text.
    struct.pack_into("<I", blob, 0x118, 0x7100801f)  # CMP W0,#32
    struct.pack_into("<I", blob, 0x11c, 0x54000040)  # B.EQ PC+8
    struct.pack_into("<I", blob, 0x120, 0x94000002)  # BL PC+8
    struct.pack_into("<I", blob, 0x124, 0xd61f0200)  # BR X16
    struct.pack_into("<I", blob, 0x128, 0xd65f03c0)  # RET
    struct.pack_into("<I", blob, 0x12c, 0xd63f0200)  # BLR X16
    return blob


class ExecutorFlowTests(unittest.TestCase):
    def test_decoded_control_instruction_classification(self):
        self.assertEqual(flow._decode_control(0x7100801f, 0x1018),
                         ("CMP_IMMEDIATE", 32))
        self.assertEqual(flow._decode_control(0x54000040, 0x101c),
                         ("BRANCH_CONDITIONAL", 0x1024))
        self.assertEqual(flow._decode_control(0x94000002, 0x1020),
                         ("CALL_DIRECT", 0x1028))
        self.assertEqual(flow._decode_control(0xd61f0200, 0x1024),
                         ("BRANCH_INDIRECT", None))
        self.assertEqual(flow._decode_control(0xd63f0200, 0x102c),
                         ("CALL_INDIRECT", None))

    def test_metadata_never_maps_opcode_or_exposes_native_bytes(self):
        binary = make_executor()
        seed = source.inspect_original_dispatch_seeds(binary)
        result = flow.analyze_executor_neighborhoods(binary, seed)
        self.assertEqual(result["executor_site_count"], 2)
        self.assertFalse(result["original_import_authorized"])
        self.assertEqual(result["native_opcode_handler_mapping_count"], 0)
        for site in result["sites"]:
            self.assertEqual(site["small_immediate_cmp_histogram"][32], 1)
            self.assertEqual(site["instruction_classes"]["CALL_DIRECT"], 1)
            self.assertEqual(site["instruction_classes"]["BRANCH_INDIRECT"], 1)
            self.assertEqual(site["instruction_classes"]["CALL_INDIRECT"], 1)
            self.assertNotIn("original_native_binary", site)

    def test_no_source_anchors_no_pretend_dispatch(self):
        binary = make_executor()
        result = flow.analyze_executor_neighborhoods(binary, {"labels": []})
        self.assertEqual(result["status"], "NO_AUTHENTICATED_EXECUTOR_CODE_ANCHORS")
        self.assertEqual(result["executor_site_count"], 0)

    def test_rodata_source_reference_not_instruction_site(self):
        binary = make_executor()
        references = source.inspect_original_dispatch_seeds(binary)
        references["labels"][0]["instruction_sites"][0][
            "site_instruction_file_offset"] = 0x180
        with self.assertRaisesRegex(ValueError, "unique aligned executable"):
            flow.analyze_executor_neighborhoods(binary, references)

    def test_negative_conditional_branch_displacement(self):
        # B.EQ with imm19=-1 => back one instruction.
        word = 0x54000000 | (0x7ffff << 5)
        self.assertEqual(flow._decode_control(word, 0x1020),
                         ("BRANCH_CONDITIONAL", 0x101c))


if __name__ == "__main__":
    unittest.main()
