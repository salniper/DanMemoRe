"""Synthetic original-format AArch64 CFG/stack writer tests only."""
import copy
import struct
import unittest

from test_inspect_native_novel_object_registers import original_style, proof
from test_inspect_native_novel_stack_slots import memory_fixture, prepare
import inspect_native_novel_stack_slots as stacks
import inspect_native_novel_stack_store_paths as paths


def reports(binary):
    frames, precise, cfg = prepare(binary)
    source = stacks.inspect_stack_slot_sources(binary, frames, precise, cfg)
    return frames, precise, cfg, source


def competing_stp_fixture():
    blob=original_style()
    # X20 initially takes incoming X0. Two mutually exclusive stores to
    # the same normalized SP+64 slot: X20 versus constant XZR.
    struct.pack_into("<I",blob,0x104,0x54000080)  # B.EQ +16 => 0x114
    store_x20 = 0xa9000000 | (8<<15) | (31<<10) | (31<<5) | 20
    store_xzr = 0xa9000000 | (8<<15) | (0<<10) | (31<<5) | 31
    struct.pack_into("<I",blob,0x108,store_x20)
    struct.pack_into("<I",blob,0x10c,0x14000003)  # B 0x118
    struct.pack_into("<I",blob,0x114,store_xzr)
    struct.pack_into("<I",blob,0x118,0xf94023f4)  # LDR X20,[SP,#64]
    return blob


class OriginalStackStorePathTests(unittest.TestCase):
    def test_branch_alternative_x20_vs_zero_sources(self):
        binary=competing_stp_fixture()
        frames,precise,cfg,source=reports(binary)
        result=paths.inspect_stack_store_paths(binary,frames,precise,cfg,source)
        self.assertEqual(result["status"],
                         "ORIGINAL_CFG_STACK_STORES_SOURCE_PATH_CANDIDATES_ONLY")
        self.assertEqual(result["query_count"],1)
        self.assertEqual(result["stores_with_modeled_unclobbered_suffix"],2)
        stores=result["source_paths"][0]["stores"]
        self.assertEqual({s["store_va"] for s in stores},{0x1008,0x1014})
        for s in stores:
            self.assertTrue(s["modeled_path_to_load_without_recognized_rewrite"])
            self.assertFalse(s["runtime_store_execution_verified"])
        reg=next(s for s in stores if s["stored_register"]==20)
        zero=next(s for s in stores if s["stored_register"]==31)
        self.assertEqual(reg["store_source"]["kind"],
                         "REGISTER_VALUE_UNKNOWN_CFG_WRITER_CANDIDATES")
        self.assertEqual(
            [w["writer_va"] for w in reg["store_source"]["candidate_register_writers"]],
            [0x1000])
        self.assertEqual(reg["store_source"]["candidate_register_writers"][0]["source_register"],0)
        self.assertEqual(zero["store_source"]["kind"],
                         "XZR_CONSTANT_ZERO_NOT_A_VTABLE")
        self.assertEqual(zero["store_source"]["candidate_register_writers"],[])
        self.assertEqual(result["confirmed_runtime_stack_objects"],0)
        self.assertEqual(result["confirmed_vtable_targets"],0)
        self.assertEqual(result["verified_numeric_opcode_handlers"],0)
        self.assertFalse(result["import_authorized"])

    def test_sequential_earlier_store_is_shadowed_by_later_store(self):
        binary=memory_fixture()
        struct.pack_into("<I",binary,0x108,0xf90023e1) # STR X1,[SP,#64]
        frames,precise,cfg,source=reports(binary)
        self.assertEqual(source["queried_sources"][0]["known_store_candidates"][0]["store_va"],
                         0x1008)
        # Fake upstream insertion of the earlier store must not be
        # misreported as still feeding the load.
        source["queried_sources"][0]["known_store_candidates"].append({
            "store_va":0x1004,"kind":"STR64_SP_UNSIGNED",
            "stored_register":0,"sp_relative_byte_offset_at_store":64})
        result=paths.inspect_stack_store_paths(binary,frames,precise,cfg,source)
        by_va={s["store_va"]:s for s in result["source_paths"][0]["stores"]}
        self.assertTrue(by_va[0x1008]["modeled_path_to_load_without_recognized_rewrite"])
        self.assertFalse(by_va[0x1004]["modeled_path_to_load_without_recognized_rewrite"])

    def test_no_store_is_reported_as_unknown(self):
        binary=memory_fixture()
        struct.pack_into("<I",binary,0x104,0xd503201f)
        frames,precise,cfg,source=reports(binary)
        result=paths.inspect_stack_store_paths(binary,frames,precise,cfg,source)
        self.assertEqual(result["source_paths"][0]["recognized_candidate_stores"],0)
        self.assertEqual(result["confirmed_runtime_stack_objects"],0)

    def test_forged_stp_source_register_is_rejected(self):
        binary=competing_stp_fixture()
        frames,precise,cfg,source=reports(binary)
        source["queried_sources"][0]["known_store_candidates"][0]["stored_register"]=18
        with self.assertRaisesRegex(ValueError,"forged original stack store"):
            paths.inspect_stack_store_paths(binary,frames,precise,cfg,source)

    def test_mismatched_stack_base_is_rejected(self):
        binary=competing_stp_fixture()
        frames,precise,cfg,source=reports(binary)
        source["queried_sources"][0]["entry_sp_normalized_byte_offset"]+=8
        with self.assertRaisesRegex(ValueError,"normalized SP slot differs"):
            paths.inspect_stack_store_paths(binary,frames,precise,cfg,source)

    def test_forged_cfi_report_is_rejected(self):
        binary=competing_stp_fixture()
        frames,precise,cfg,source=reports(binary)
        frames["status"]="FORGED"
        with self.assertRaisesRegex(ValueError,"authenticated original"):
            paths.inspect_stack_store_paths(binary,frames,precise,cfg,source)

    def test_address_of_stack_cannot_claim_store_as_pointer(self):
        binary=memory_fixture()
        frames,precise,cfg,source=reports(binary)
        source["queried_sources"][0]["kind"]="ADDRESS_OF_STACK_SLOT_NOT_CONTENT_READ"
        with self.assertRaisesRegex(ValueError,"no store can prove address-of-stack"):
            paths.inspect_stack_store_paths(binary,frames,precise,cfg,source)


if __name__=="__main__":
    unittest.main()
