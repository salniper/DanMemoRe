"""Synthetic AArch64 ELF only; no original game/client bytes included."""
import struct
import unittest

import inspect_native_novel_dispatch_seeds as d
from test_inspect_native_novel_elf_sections import fixture


LABEL = b"/tmp/original/source/UI/Novel/NovelCommand/Command/NovelCommandTalkShow.cpp"


def synthetic():
    blob = fixture()
    blob[0x180:0x200] = b"\0" * 128
    blob[0x180:0x180 + len(LABEL)] = LABEL
    blob[0x180 + len(LABEL)] = 0
    # Executable .text section at file 0x100 VA 0x1000, original path
    # is at file 0x180 VA 0x2180.
    struct.pack_into("<I", blob, 0x100, 0xb0000000)  # ADRP X0,#0x2000
    struct.pack_into("<I", blob, 0x104, 0xd503201f)  # NOP
    struct.pack_into("<I", blob, 0x108, 0x91060000)  # ADD X0,X0,#0x180
    displacement = 0x2180 - 0x1010
    adr = 0x10000000 | ((displacement & 3) << 29) | (
        ((displacement >> 2) & 0x7ffff) << 5) | 2
    struct.pack_into("<I", blob, 0x110, adr)
    return blob


class NativeNovelDispatchSeedTests(unittest.TestCase):
    def test_original_source_path_and_two_instruction_candidates(self):
        result = d.inspect_original_dispatch_seeds(synthetic())
        self.assertEqual(result["status"],
                         "ORIGINAL_EXECUTABLE_TO_NOVEL_METADATA_CANDIDATES_ONLY")
        self.assertEqual(result["labels_checked"], 1)
        self.assertEqual(result["original_code_site_candidate_count"], 2)
        evidence = result["labels"][0]
        self.assertEqual(evidence["kind"], "ORIGINAL_HANDLER_CPP_PATH")
        self.assertEqual(evidence["string_va"], 0x2180)
        patterns = [hit["pattern"] for hit in evidence["instruction_sites"]]
        self.assertEqual(patterns, ["ADRP_ADD_CANDIDATE", "ADR_DIRECT"])
        self.assertEqual(evidence["instruction_sites"][0]["adrp_add_instruction_gap"],2)
        self.assertFalse(result["original_integer_opcode_dispatch_verified"])
        self.assertFalse(result["original_import_authorized"])

    def test_nonexecutable_rodata_is_not_scanned_as_instructions(self):
        blob = synthetic()
        # Put a valid-looking ADR *bit pattern* in .rodata: no new code xref.
        pc = 0x2180 + 0x70
        target = 0x2180
        delta = (target - pc) & ((1 << 21) - 1)
        word = 0x10000000 | ((delta & 3) << 29) | (
            ((delta >> 2) & 0x7ffff) << 5)
        struct.pack_into("<I", blob, 0x1f0, word)
        self.assertEqual(d.inspect_original_dispatch_seeds(blob)
                         ["original_code_site_candidate_count"], 2)

    def test_target_middle_of_long_string_does_not_count(self):
        blob = synthetic()
        # ADR targets beginning of handler class substring, but correct
        # original source-path target is the beginning of the full literal.
        substring_pos = LABEL.index(b"NovelCommandTalkShow")
        target = 0x2180 + substring_pos
        delta = target - 0x1010
        word = 0x10000000 | ((delta & 3) << 29) | (
            ((delta >> 2) & 0x7ffff) << 5) | 2
        struct.pack_into("<I", blob, 0x110, word)
        result = d.inspect_original_dispatch_seeds(blob)
        self.assertEqual(result["original_code_site_candidate_count"], 1)

    def test_adrp_add_gap_beyond_bound_not_evidence(self):
        blob = synthetic()
        struct.pack_into("<I", blob, 0x108, 0xd503201f)
        # Insert ADD more than twelve instructions away, within .text.
        # The original synthetic .text section has only 16 instruction slots.
        struct.pack_into("<I", blob, 0x138, 0x91060000)
        struct.pack_into("<I", blob, 0x110, 0xd503201f)
        result = d.inspect_original_dispatch_seeds(blob)
        self.assertEqual(result["original_code_site_candidate_count"], 0)

    def test_no_labels_fails_closed(self):
        blob = synthetic()
        blob[0x180:0x180+len(LABEL)] = b"_" * len(LABEL)
        with self.assertRaisesRegex(ValueError, "no original NovelCommand"):
            d.inspect_original_dispatch_seeds(blob)

    def test_wrong_binary_format_fails_closed(self):
        blob = synthetic()
        blob[:4] = b"FAIL"
        with self.assertRaisesRegex(ValueError, "ELF"):
            d.inspect_original_dispatch_seeds(blob)

    def test_no_exact_target_without_reference(self):
        blob = synthetic()
        for at in (0x100, 0x108, 0x110):
            struct.pack_into("<I", blob, at, 0xd503201f)
        evidence = d.inspect_original_dispatch_seeds(blob)
        self.assertEqual(evidence["labels_checked"],1)
        self.assertEqual(evidence["original_code_site_candidate_count"],0)


if __name__ == "__main__":
    unittest.main()
