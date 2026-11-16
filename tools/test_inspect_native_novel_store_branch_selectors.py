"""Synthetic AArch64 CFI/CFG branch selector tests, no original game bytes."""
import struct
import unittest

from test_inspect_native_novel_stack_store_paths import (
    competing_stp_fixture, reports,
)
import inspect_native_novel_stack_store_paths as paths
import inspect_native_novel_store_branch_selectors as selector


def evaluate(binary):
    frames,precise,cfg,stack=reports(binary)
    trail=paths.inspect_stack_store_paths(binary,frames,precise,cfg,stack)
    return selector.inspect_original_stack_store_branch_conditions(
        binary,frames,precise,cfg,stack,trail)


class OriginalStoreBranchSelectorTests(unittest.TestCase):
    def test_conditional_split_selects_distinct_first_stores(self):
        result=evaluate(competing_stp_fixture())
        self.assertEqual(result["status"],
                         "ORIGINAL_EXECUTOR_STACK_BRANCH_SELECTOR_SYNTAX_ONLY")
        self.assertEqual(result["alternative_store_queries"],1)
        self.assertEqual(result["queries_with_modeled_selector"],1)
        row=result["queries"][0]
        self.assertEqual(row["status"],
                         "MODELED_DISTINCT_ARM_STORE_SELECTOR_CANDIDATE")
        self.assertEqual(row["store_vas"],[0x1008,0x1014])
        self.assertEqual(row["modeled_selector_branch_count"],1)
        branch=row["selector_branch_candidates"][0]
        self.assertEqual(branch["branch_va"],0x1004)
        self.assertEqual(branch["branch_condition"]["kind"],"NZCV_FLAG_CONDITION")
        self.assertEqual(branch["branch_condition"]["condition"],"EQ")
        self.assertEqual({arm["edge_role"] for arm in branch["arms"]},
                         {"TAKEN","FALLTHROUGH"})
        self.assertEqual(
            {tuple(arm["first_candidate_store_vas"]) for arm in branch["arms"]},
            {(0x1008,),(0x1014,)})
        self.assertTrue(branch["recognized_cfg_branch_dominates_both_stores"])
        self.assertFalse(branch["actual_branch_executed"])
        self.assertFalse(branch["runtime_condition_verified"])
        self.assertFalse(row["physical_store_value_verified"])
        self.assertEqual(result["vtable_addresses_verified"],0)
        self.assertEqual(result["numeric_opcode_handler_pairs_verified"],0)
        self.assertFalse(result["original_import_authorized"])

    def test_cbz_register_condition_is_syntax_only(self):
        binary=competing_stp_fixture()
        # CBZ X1 to 0x1014 from PC 0x1004, imm19=4.
        struct.pack_into("<I",binary,0x104,0xb4000081)
        result=evaluate(binary)
        branch=result["queries"][0]["selector_branch_candidates"][0]
        self.assertEqual(branch["branch_condition"]["kind"],"CBZ")
        self.assertEqual(branch["branch_condition"]["tested_register"],1)
        self.assertEqual(branch["branch_condition"]["condition"],"register == 0")
        self.assertFalse(branch["actual_branch_executed"])

    def test_no_conditional_split_no_verified_selector(self):
        binary=competing_stp_fixture()
        # Nonconditional direct jump bypasses first STP; upstream report
        # will then contain only one recognized possible store.
        struct.pack_into("<I",binary,0x104,0x14000004)
        result=evaluate(binary)
        self.assertEqual(result["alternative_store_queries"],0)
        self.assertEqual(result["queries_with_modeled_selector"],0)

    def test_fake_stack_store_instruction_fails_closed(self):
        binary=competing_stp_fixture()
        frames,precise,cfg,stack=reports(binary)
        trail=paths.inspect_stack_store_paths(binary,frames,precise,cfg,stack)
        struct.pack_into("<I",binary,0x108,0xd503201f)
        with self.assertRaisesRegex(ValueError,"branch-store byte/CFG/SP"):
            selector.inspect_original_stack_store_branch_conditions(
                binary,frames,precise,cfg,stack,trail)

    def test_forged_evidence_status_fails_closed(self):
        binary=competing_stp_fixture()
        frames,precise,cfg,stack=reports(binary)
        trail=paths.inspect_stack_store_paths(binary,frames,precise,cfg,stack)
        trail["status"]="GUESS"
        with self.assertRaisesRegex(ValueError,"authenticated original"):
            selector.inspect_original_stack_store_branch_conditions(
                binary,frames,precise,cfg,stack,trail)

    def test_unrelated_branch_has_no_specific_selector(self):
        binary=competing_stp_fixture()
        # Add earlier B.EQ whose both arms feed original fork.
        struct.pack_into("<I",binary,0x100,0x54000040)  # B.EQ 0x1008
        # This makes first X20 STP reachable via both arms, but bypasses
        # later split for one path, defeating dominance by original fork.
        result=evaluate(binary)
        self.assertEqual(result["queries_with_modeled_selector"],0)

    def test_bit_test_decodes_bit_position_and_register(self):
        # TBZ X3,#4 with positive branch displacement syntax.
        word=0x36000000 | (4<<19) | (3)
        c=selector._branch_condition(word,"BRANCH_BIT_TEST")
        self.assertEqual(c["kind"],"TBZ")
        self.assertEqual(c["tested_register"],3)
        self.assertEqual(c["tested_bit"],4)

    def test_empty_paths_not_mapped_to_opcodes(self):
        binary=competing_stp_fixture()
        result=evaluate(binary)
        self.assertEqual(result["numeric_opcode_handler_pairs_verified"],0)
        self.assertEqual(result["native_object_identity_verified"],0)


if __name__=="__main__":
    unittest.main()
