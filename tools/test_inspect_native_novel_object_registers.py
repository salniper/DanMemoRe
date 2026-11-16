"""Synthetic original-format AArch64: no original user or client content."""
import struct
import unittest

from test_inspect_native_novel_unwind import fixture, anchors
import inspect_native_novel_unwind as unwind
import inspect_native_novel_indirect_calls as indirect
import inspect_native_novel_object_registers as origins


def original_style():
    binary = fixture()
    # MOV X20,X0 ; LDR X8,[X20]; LDR X8,[X8,#16]; BLR X8
    struct.pack_into("<I", binary, 0x100, 0xaa0003f4)
    struct.pack_into("<I", binary, 0x120, 0xf9400288)
    struct.pack_into("<I", binary, 0x124, 0xf9400908)
    struct.pack_into("<I", binary, 0x128, 0xd63f0100)
    return binary


def proof(binary):
    frames = unwind.find_executor_unwind_frames(binary, anchors(0x1010))
    precise = unwind.summarize_verified_fde_instructions(binary, frames)
    calls = indirect.inspect_original_indirect_calls(binary, frames, precise)
    return frames, precise, calls


class NativeNovelObjectOriginsTests(unittest.TestCase):
    def test_first_hop_object_register_points_to_syntactic_mov(self):
        binary=original_style()
        frames, precise, calls=proof(binary)
        result=origins.inspect_object_register_origins(binary, frames, precise, calls)
        self.assertEqual(result["indirect_call_count"], 1)
        self.assertEqual(result["recognized_origin_writer_count"], 1)
        record=result["object_register_sources"][0]
        self.assertEqual(record["object_source_register"], 20)
        self.assertEqual(record["first_load_instruction_va"], 0x1020)
        self.assertEqual(record["origin_status"],"LINEAR_WRITER_CANDIDATE_NOT_CFG_PROOF")
        self.assertEqual(record["origin_writer"]["instruction_va"],0x1000)
        self.assertEqual(record["origin_writer"]["recognized_writer_kind"],"COPY_REGISTER")
        self.assertEqual(record["origin_writer"]["source_register"],0)
        self.assertFalse(record["register_flow_proven"])
        self.assertIsNone(record["verified_vtable_va"])
        self.assertEqual(result["verified_object_pointer_count"],0)
        self.assertEqual(result["verified_opcode_handler_mappings"],0)

    def test_branch_between_writer_and_use_does_not_prove_dataflow(self):
        binary=original_style()
        struct.pack_into("<I",binary,0x110,0x54000040)  # B.EQ +8
        frames, precise, calls=proof(binary)
        result=origins.inspect_object_register_origins(binary,frames,precise,calls)
        writer=result["object_register_sources"][0]["origin_writer"]
        self.assertEqual(writer["control_transfers_between_writer_and_first_load"],1)
        self.assertFalse(result["object_register_sources"][0]["register_flow_proven"])

    def test_unknown_source_writer_is_not_invented(self):
        binary=original_style()
        struct.pack_into("<I",binary,0x100,0xd503201f)
        frames,precise,calls=proof(binary)
        report=origins.inspect_object_register_origins(binary,frames,precise,calls)
        self.assertEqual(report["recognized_origin_writer_count"],0)
        self.assertEqual(report["object_register_sources"][0]["origin_status"],
                         "NO_RECOGNIZED_WRITER_IN_ORIGINAL_FDE")

    def test_spoofed_blr_instruction_is_rejected(self):
        binary=original_style()
        frames,precise,calls=proof(binary)
        struct.pack_into("<I",binary,0x128,0xd65f03c0)
        with self.assertRaisesRegex(ValueError,"BLR instruction changed"):
            origins.inspect_object_register_origins(binary,frames,precise,calls)

    def test_malformed_indirect_site_register_is_rejected(self):
        binary=original_style()
        frames,precise,calls=proof(binary)
        calls["sites"][0]["call_target_register"]=17
        with self.assertRaisesRegex(ValueError,"BLR instruction changed"):
            origins.inspect_object_register_origins(binary,frames,precise,calls)

    def test_forged_initial_pointer_load_is_rejected(self):
        binary=original_style()
        frames,precise,calls=proof(binary)
        calls["sites"][0]["earlier_register_writer_source"]=25
        with self.assertRaisesRegex(ValueError,"pointer load not verified"):
            origins.inspect_object_register_origins(binary,frames,precise,calls)

    def test_fake_fde_provenance_does_not_pass(self):
        binary=original_style()
        frames,precise,calls=proof(binary)
        frames["status"]="FAKE"
        with self.assertRaisesRegex(ValueError,"all original CFI"):
            origins.inspect_object_register_origins(binary,frames,precise,calls)

    def test_wrong_report_count_is_rejected(self):
        binary=original_style()
        frames,precise,calls=proof(binary)
        calls["original_blr_call_sites"]=9
        with self.assertRaisesRegex(ValueError,"inconsistent"):
            origins.inspect_object_register_origins(binary,frames,precise,calls)

    def test_missing_source_fails_closed(self):
        binary=original_style()
        frames,precise,calls=proof(binary)
        calls["sites"][0]["earlier_register_writer_source"]=None
        report=origins.inspect_object_register_origins(binary,frames,precise,calls)
        self.assertEqual(report["object_register_sources"][0]["origin_status"],
                         "OBJECT_REGISTER_UNAVAILABLE")
        self.assertFalse(report["original_import_authorized"])


if __name__=="__main__":
    unittest.main()
