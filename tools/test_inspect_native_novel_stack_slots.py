"""Synthetic ARM64 SP slot store/CFG tests; no original game bytes."""
import struct
import unittest

from test_inspect_native_novel_object_registers import original_style, proof
import inspect_native_novel_object_registers as objects
import inspect_native_novel_cfg_paths as cfg
import inspect_native_novel_stack_slots as stack


def prepare(binary):
    frames,precise,indirect=proof(binary)
    origins=objects.inspect_object_register_origins(binary,frames,precise,indirect)
    paths=cfg.inspect_cfg_object_paths(binary,frames,precise,indirect,origins)
    return frames,precise,paths


def memory_fixture():
    binary=original_style()
    struct.pack_into("<I",binary,0x100,0xd503201f) # NOP
    struct.pack_into("<I",binary,0x104,0xf90023e0) # STR X0,[SP,#64]
    struct.pack_into("<I",binary,0x110,0xf94023f4) # LDR X20,[SP,#64]
    return binary


class NativeStackOriginTests(unittest.TestCase):
    def test_sp_stack_store_resolves_syntactic_candidate_not_value(self):
        binary=memory_fixture()
        frames,precise,paths=prepare(binary)
        report=stack.inspect_stack_slot_sources(binary,frames,precise,paths)
        self.assertEqual(report["status"],"ORIGINAL_CFG_STACK_STORE_PROVENANCE_CANDIDATES_ONLY")
        self.assertEqual(report["stack_slot_queries"],1)
        self.assertEqual(report["queries_with_recognized_store_candidates"],1)
        row=report["queried_sources"][0]
        self.assertEqual(row["call_va"],0x1028)
        self.assertEqual(row["sp_relative_byte_offset_at_use"],64)
        self.assertEqual(row["entry_sp_normalized_byte_offset"],64)
        self.assertEqual(row["known_store_candidates"],[{
            "store_va":0x1004,"kind":"STR64_SP_UNSIGNED",
            "stored_register":0,"sp_relative_byte_offset_at_store":64}])
        self.assertFalse(row["stack_value_verified"])
        self.assertEqual(report["original_vtable_addresses_proven"],0)
        self.assertEqual(report["original_numeric_opcode_handlers_proven"],0)
        self.assertFalse(report["import_authorized"])

    def test_sp_delta_normalization_honors_stack_frame_adjustment(self):
        binary=memory_fixture()
        struct.pack_into("<I",binary,0x100,0xd10083ff) # SUB SP,SP,#32
        frames,precise,paths=prepare(binary)
        row=stack.inspect_stack_slot_sources(binary,frames,precise,paths)["queried_sources"][0]
        self.assertEqual(row["entry_sp_normalized_byte_offset"],32)
        self.assertEqual(len(row["known_store_candidates"]),1)

    def test_sp_delta_change_between_store_and_load_not_aliased(self):
        binary=memory_fixture()
        struct.pack_into("<I",binary,0x108,0x910043ff) # ADD SP,SP,#16
        frames,precise,paths=prepare(binary)
        row=stack.inspect_stack_slot_sources(binary,frames,precise,paths)["queried_sources"][0]
        self.assertEqual(row["entry_sp_normalized_byte_offset"],80)
        self.assertEqual(row["known_store_candidates"],[])
        self.assertEqual(row["status"],"NO_RECOGNIZED_FIRST_STORE_IN_CFG")

    def test_two_branch_stores_are_both_candidates(self):
        binary=original_style()
        struct.pack_into("<I",binary,0x100,0x54000080) # B.EQ 0x1010
        struct.pack_into("<I",binary,0x104,0xf90023e0) # STR X0,[SP,#64]
        struct.pack_into("<I",binary,0x108,0x14000003) # B 0x1014
        struct.pack_into("<I",binary,0x110,0xf90023e1) # STR X1,[SP,#64]
        struct.pack_into("<I",binary,0x114,0xf94023f4) # LDR X20,[SP,#64]
        frames,precise,paths=prepare(binary)
        row=stack.inspect_stack_slot_sources(binary,frames,precise,paths)["queried_sources"][0]
        self.assertEqual(len(row["known_store_candidates"]),2)
        self.assertEqual({c["store_va"] for c in row["known_store_candidates"]},
                         {0x1004,0x1010})
        self.assertFalse(row["stack_value_verified"])

    def test_stp_offset_two_register_lanes(self):
        word=0xa9000000 | (8 << 15) | (2<<10) | (31<<5) | 1
        stores=stack._stack_write(word)
        self.assertEqual([s["offset"] for s in stores],[64,72])
        self.assertEqual([s["register"] for s in stores],[1,2])
        self.assertEqual(stack._sp_change(word),0)

    def test_stur_negative_offset(self):
        word=0xf8000000 | ((-8 & 511)<<12) | (31<<5) | 3
        self.assertEqual(stack._stack_write(word)[0]["offset"],-8)

    def test_stack_pointer_preindex_update_is_accounted(self):
        stp=0xa9800000 | ((-4 & 127)<<15) | (30<<10) | (31<<5) | 29
        self.assertEqual(stack._sp_change(stp),-32)

    def test_address_of_stack_slot_is_not_pointer_load(self):
        binary=original_style()
        struct.pack_into("<I",binary,0x100,0x910083f4) # ADD X20,SP,#32
        frames,precise,paths=prepare(binary)
        row=stack.inspect_stack_slot_sources(binary,frames,precise,paths)["queried_sources"][0]
        self.assertEqual(row["kind"],"ADDRESS_OF_STACK_SLOT_NOT_CONTENT_READ")
        self.assertEqual(row["entry_sp_normalized_byte_offset"],32)
        self.assertFalse(row["stack_value_verified"])

    def test_unverified_original_cfg_report_rejected(self):
        binary=memory_fixture()
        frames,precise,paths=prepare(binary)
        paths["status"]="FORGED"
        with self.assertRaisesRegex(ValueError,"verified original FDE/CFG"):
            stack.inspect_stack_slot_sources(binary,frames,precise,paths)

    def test_no_known_store_is_not_a_proven_object(self):
        binary=memory_fixture()
        struct.pack_into("<I",binary,0x104,0xd503201f)
        frames,precise,paths=prepare(binary)
        row=stack.inspect_stack_slot_sources(binary,frames,precise,paths)["queried_sources"][0]
        self.assertEqual(row["known_store_candidates"],[])
        self.assertTrue(row["entry_path_without_known_store"])


if __name__=="__main__":
    unittest.main()
