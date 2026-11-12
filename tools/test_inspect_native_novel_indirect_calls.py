"""Synthetic ARM64 BLR register-writer fixtures; no original game bytes."""
import struct
import unittest

import inspect_native_novel_indirect_calls as indirect
import inspect_native_novel_unwind as unwind
from test_inspect_native_novel_unwind import fixture, anchors


def fake_report(binary):
    frames = unwind.find_executor_unwind_frames(binary, anchors(0x1010))
    exact = unwind.summarize_verified_fde_instructions(binary, frames)
    return frames, exact


class OriginalIndirectCallTests(unittest.TestCase):
    def test_two_original_style_blr_loads_are_not_vtable_proof(self):
        binary = fixture()
        struct.pack_into("<I", binary, 0x124, 0xf9400928)  # LDR X8,[X9,#16]
        struct.pack_into("<I", binary, 0x128, 0xd63f0100)  # BLR X8
        struct.pack_into("<I", binary, 0x134, 0xf9400010)  # LDR X16,[X0]
        struct.pack_into("<I", binary, 0x138, 0xd63f0200)  # BLR X16
        frames, exact = fake_report(binary)
        result = indirect.inspect_original_indirect_calls(binary, frames, exact)
        self.assertEqual(result["original_blr_call_sites"], 2)
        self.assertEqual(result["call_target_nearest_writer_kinds"],
                         {"LOAD_POINTER_FROM_REGISTER": 2})
        first, second = result["sites"]
        self.assertEqual(first["call_target_register"], 8)
        self.assertEqual(first["nearest_writer_source_register"], 9)
        self.assertEqual(first["nearest_writer_byte_offset"], 16)
        self.assertEqual(second["call_target_register"], 16)
        self.assertEqual(second["nearest_writer_source_register"], 0)
        self.assertIsNone(first["resolved_function_target_va"])
        self.assertFalse(first["proven_virtual_dispatch"])
        self.assertFalse(second["original_novel_handler_verified"])
        self.assertEqual(result["verified_numeric_opcode_handler_mappings"], 0)
        self.assertFalse(result["original_import_authorized"])

    def test_virtual_call_two_load_shape_still_no_verified_vtable(self):
        binary = fixture()
        struct.pack_into("<I", binary, 0x120, 0xf9400008)  # LDR X8,[X0]
        struct.pack_into("<I", binary, 0x124, 0xf9400908)  # LDR X8,[X8,#16]
        struct.pack_into("<I", binary, 0x128, 0xd63f0100)  # BLR X8
        frames, exact = fake_report(binary)
        result = indirect.inspect_original_indirect_calls(binary, frames, exact)
        self.assertEqual(result["original_blr_call_sites"], 1)
        self.assertEqual(result["two_load_virtual_call_shaped_sites"], 1)
        site = result["sites"][0]
        self.assertEqual(site["earlier_register_writer_kind"], "LOAD_POINTER_FROM_REGISTER")
        self.assertEqual(site["earlier_register_writer_source"], 0)
        self.assertEqual(site["earlier_register_writer_byte_offset"], 0)
        self.assertTrue(site["two_pointer_loads_syntactically_adjacent_in_register"])
        self.assertFalse(site["proven_virtual_dispatch"])
        self.assertEqual(result["verified_vtable_targets"], 0)
        self.assertEqual(result["verified_numeric_opcode_handler_mappings"], 0)

    def test_register_copy_is_classified_without_assuming_dataflow(self):
        word = 0xaa0003e0 | (8 << 16) | 16  # MOV X16,X8
        hint = indirect._register_writer(word, 0x1000)
        self.assertEqual(hint["kind"], "COPY_REGISTER")
        self.assertEqual(hint["dest"], 16)
        self.assertEqual(hint["source"], 8)

    def test_pc_relative_literal_and_page_are_syntax_only(self):
        literal = indirect._register_writer(0x58000048, 0x1000)
        self.assertEqual(literal["kind"], "LOAD_POINTER_FROM_LITERAL")
        self.assertEqual(literal["dest"], 8)
        self.assertEqual(literal["literal_va"], 0x1008)
        page = indirect._register_writer(0x90000000, 0x1120)
        self.assertEqual(page["kind"], "PAGE_ADDRESS")
        self.assertEqual(page["page_va"], 0x1000)

    def test_branch_barrier_never_becomes_reaching_definition(self):
        binary = fixture()
        struct.pack_into("<I", binary, 0x120, 0xf9400928)
        struct.pack_into("<I", binary, 0x124, 0x14000000)
        struct.pack_into("<I", binary, 0x128, 0xd63f0100)
        frames, exact = fake_report(binary)
        result = indirect.inspect_original_indirect_calls(binary, frames, exact)
        self.assertEqual(result["original_blr_call_sites"], 1)
        self.assertEqual(result["sites"][0]["preceding_control_transfers_since_writer"], 1)
        self.assertIn("NOT_REACHING_DEFINITION",
                      result["sites"][0]["evidence_level"])

    def test_unknown_writer_is_not_guessed(self):
        binary = fixture()
        struct.pack_into("<I", binary, 0x100, 0xd63f0120)  # BLR X9
        frames, exact = fake_report(binary)
        result = indirect.inspect_original_indirect_calls(binary, frames, exact)
        self.assertEqual(result["original_blr_call_sites"], 1)
        self.assertEqual(result["sites"][0]["nearest_writer_kind"],
                         "NONE_IN_BOUNDED_WINDOW")

    def test_fake_verified_region_rejected(self):
        binary = fixture()
        frames, exact = fake_report(binary)
        exact["regions"][0]["validated_unwind_start_va"] = 0x1020
        with self.assertRaisesRegex(ValueError, "unverified"):
            indirect.inspect_original_indirect_calls(binary, frames, exact)

    def test_no_unwind_validation_is_rejected(self):
        binary = fixture()
        frames, exact = fake_report(binary)
        frames["status"] = "FAKE"
        with self.assertRaisesRegex(ValueError, "mandatory"):
            indirect.inspect_original_indirect_calls(binary, frames, exact)

    def test_counts_must_match_original_code(self):
        binary = fixture()
        frames, exact = fake_report(binary)
        exact["regions"][0]["instruction_class_counts"]["CALL_INDIRECT"] = 1
        with self.assertRaisesRegex(ValueError, "counts disagree"):
            indirect.inspect_original_indirect_calls(binary, frames, exact)


if __name__ == "__main__":
    unittest.main()
