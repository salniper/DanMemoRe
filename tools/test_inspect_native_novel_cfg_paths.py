"""Synthetic original-style ARM64 FDE CFG tests; never original native bytes."""
import struct
import unittest

from test_inspect_native_novel_object_registers import original_style, proof
import inspect_native_novel_object_registers as origins
import inspect_native_novel_cfg_paths as paths


def run(binary):
    frame, exact, indirect = proof(binary)
    origin = origins.inspect_object_register_origins(binary, frame, exact, indirect)
    return paths.inspect_cfg_object_paths(binary, frame, exact, indirect, origin)


class OriginalNovelCfgPathTests(unittest.TestCase):
    def test_single_recognized_writer_on_modeled_entry_path(self):
        report=run(original_style())
        self.assertEqual(report["status"],
                         "ORIGINAL_FDE_CFG_REACHING_WRITER_CANDIDATES_ONLY")
        self.assertEqual(report["call_sites_checked"],1)
        site=report["source_register_paths"][0]
        self.assertTrue(site["cfg_entry_reaches_first_load"])
        self.assertTrue(site["cfg_entry_reaches_call"])
        self.assertTrue(site["linear_nearest_writer_is_cfg_first_reaching_candidate"])
        self.assertEqual(site["cfg_reaching_writer_count"],1)
        self.assertEqual(site["reaching_writer_samples"][0]["writer_va"],0x1000)
        self.assertEqual(site["status"],"SOLE_RECOGNIZED_CFG_FIRST_WRITER_NOT_PROVEN")
        self.assertFalse(site["original_object_identity_verified"])
        self.assertEqual(report["original_vtable_pointer_values_verified"],0)
        self.assertEqual(report["original_opcode_handler_mappings_verified"],0)
        self.assertFalse(report["original_import_authorized"])

    def test_unreachable_linear_nearest_writer_is_not_cfg_first_writer(self):
        binary=original_style()
        # Entry jumps to X20 from X0; 0x1018 jumps over a later
        # X20 from X1. Linear backwards scan would choose unreachable X1.
        struct.pack_into("<I",binary,0x100,0x14000004)  # B 0x1010
        struct.pack_into("<I",binary,0x110,0xaa0003f4)  # MOV X20,X0
        struct.pack_into("<I",binary,0x118,0x14000002)  # B 0x1020
        struct.pack_into("<I",binary,0x11c,0xaa0103f4)  # MOV X20,X1
        report=run(binary)
        site=report["source_register_paths"][0]
        self.assertEqual(site["linear_nearest_writer_va"],0x101c)
        self.assertEqual(site["cfg_reaching_writer_count"],1)
        self.assertEqual(site["reaching_writer_samples"][0]["writer_va"],0x1010)
        self.assertFalse(site["linear_nearest_writer_is_cfg_first_reaching_candidate"])
        self.assertEqual(site["status"],
                         "LINEAR_WRITER_NOT_A_CFG_FIRST_REACHING_CANDIDATE")
        self.assertEqual(report["linear_nearest_writers_refuted_by_cfg"],1)

    def test_two_branches_produce_two_reaching_candidate_writers(self):
        binary=original_style()
        struct.pack_into("<I",binary,0x100,0x54000080)  # B.EQ 0x1010
        struct.pack_into("<I",binary,0x104,0xaa0003f4)  # MOV X20,X0
        struct.pack_into("<I",binary,0x108,0x14000006)  # B 0x1020
        struct.pack_into("<I",binary,0x110,0xaa0103f4)  # MOV X20,X1
        report=run(binary)
        site=report["source_register_paths"][0]
        self.assertEqual(site["cfg_reaching_writer_count"],2)
        self.assertEqual({x["writer_va"] for x in site["reaching_writer_samples"]},
                         {0x1004,0x1010})
        self.assertEqual(site["status"],"MULTIPLE_OR_ENTRY_REACHING_CANDIDATES")
        self.assertFalse(site["original_object_identity_verified"])

    def test_cyclic_branch_graph_terminates(self):
        binary=original_style()
        # Adds a backward conditional edge; no infinite scanning.
        struct.pack_into("<I",binary,0x110,0x54ffff80)  # B.EQ -16
        report=run(binary)
        self.assertEqual(report["call_sites_checked"],1)
        self.assertTrue(report["source_register_paths"][0]["cfg_entry_reaches_call"])

    def test_invalid_original_call_metadata_fails_closed(self):
        binary=original_style()
        frame, exact, indirect = proof(binary)
        origin=origins.inspect_object_register_origins(binary,frame,exact,indirect)
        indirect["sites"][0]["call_instruction_va"]+=4
        with self.assertRaisesRegex(ValueError,"inconsistent original call"):
            paths.inspect_cfg_object_paths(binary,frame,exact,indirect,origin)

    def test_unverified_region_fails_closed(self):
        binary=original_style()
        frame, exact, indirect = proof(binary)
        origin=origins.inspect_object_register_origins(binary,frame,exact,indirect)
        frame["status"]="unverified"
        with self.assertRaisesRegex(ValueError,"authenticated original"):
            paths.inspect_cfg_object_paths(binary,frame,exact,indirect,origin)

    def test_missing_source_does_not_generate_vtable_identity(self):
        binary=original_style()
        frame, exact, indirect = proof(binary)
        origin=origins.inspect_object_register_origins(binary,frame,exact,indirect)
        origin["object_register_sources"][0]["object_source_register"]=None
        result=paths.inspect_cfg_object_paths(binary,frame,exact,indirect,origin)
        self.assertEqual(result["source_register_paths"][0]["status"],
                         "UNKNOWN_ORIGINAL_OBJECT_SOURCE")
        self.assertEqual(result["original_vtable_pointer_values_verified"],0)


if __name__=="__main__":
    unittest.main()
