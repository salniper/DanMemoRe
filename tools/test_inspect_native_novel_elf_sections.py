"""Synthetic ELF section and symbol fixtures; no original code or game bytes."""
import struct
import unittest

import inspect_native_novel_elf_sections as check


def fixture():
    blob = bytearray(0x900)
    blob[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<H", blob, 18, 183)
    struct.pack_into("<Q", blob, 32, 64)
    struct.pack_into("<HH", blob, 54, 56, 2)
    struct.pack_into("<IIQQQQQQ", blob, 64, 1, 5, 0x100, 0x1000, 0,
                     0x40, 0x40, 0x1000)
    struct.pack_into("<IIQQQQQQ", blob, 120, 1, 4, 0x180, 0x2180, 0,
                     0x80, 0x80, 0x1000)
    blob[0x180:0x18c] = b"NovelCommand"
    struct.pack_into("<I", blob, 0x100, 0xb0000000)
    struct.pack_into("<I", blob, 0x104, 0x91060000)
    names = b"\x00.text\x00.rodata\x00.shstrtab\x00.strtab\x00.symtab\x00"
    blob[0x410:0x410 + len(names)] = names
    symbols = b"\x00_ZN12NovelCommand4LoadEv\x00"
    blob[0x450:0x450 + len(symbols)] = symbols
    struct.pack_into("<Q", blob, 40, 0x300)
    struct.pack_into("<HHH", blob, 58, 64, 6, 3)

    def section(i, name, typ, flags, addr, offset, size, link=0, entsize=0):
        struct.pack_into("<IIQQQQIIQQ", blob, 0x300 + 64 * i,
                         names.find(name), typ, flags, addr, offset,
                         size, link, 0, 1, entsize)
    section(1, b".text", 1, 6, 0x1000, 0x100, 0x40)
    section(2, b".rodata", 1, 2, 0x2180, 0x180, 0x80)
    section(3, b".shstrtab", 3, 0, 0, 0x410, len(names))
    section(4, b".strtab", 3, 0, 0, 0x450, len(symbols))
    section(5, b".symtab", 2, 0, 0, 0x500, 48, 4, 24)
    struct.pack_into("<IBBHQQ", blob, 0x500 + 24,
                     1, 0x12, 0, 1, 0x1000, 32)
    return blob


def fake_scan():
    return {"markers": [{"marker": "NovelCommand", "literal_hits": 1,
             "locations": [{
                 "file_offset": 0x180, "virtual_address": 0x2180,
                 "address_references": {
                     "candidate_count": 1,
                     "candidates": [{
                         "instruction_file_offset": 0x100,
                         "instruction_virtual_address": 0x1000,
                         "instruction_pattern": "ADRP_ADD",
                     }],
                 },
             }]}]}


class ElfSectionTests(unittest.TestCase):
    def test_read_expected_sections(self):
        sections = check.parse_sections(fixture())
        self.assertEqual(len(sections), 6)
        self.assertEqual(sections[1]["name"], ".text")
        self.assertEqual(sections[2]["name"], ".rodata")

    def test_classify_executable_and_literal_data(self):
        sections = check.parse_sections(fixture())
        self.assertTrue(check.containing_sections(sections, 0x100)["executable"])
        self.assertFalse(check.containing_sections(sections, 0x180)["executable"])
        self.assertEqual(check.containing_sections(sections, 0x180)["name"], ".rodata")

    def test_matching_function_symbol_without_claiming_loader(self):
        result = check.matching_symbols(fixture(), check.parse_sections(fixture()))
        self.assertEqual(result["matching_symbol_count"], 1)
        self.assertEqual(result["matching_symbol_types"]["FUNCTION"], 1)
        self.assertIn("NovelCommand", result["matching_symbol_samples"][0]["name"])

    def test_section_audit_report(self):
        result = check.inspect_sections(fixture(), fake_scan())
        self.assertEqual(result["status"], "ELF_SECTION_SYMBOL_EVIDENCE_ONLY")
        self.assertEqual(result["candidate_locations"][0]["string_section"]["name"],
                         ".rodata")
        self.assertEqual(result["candidate_locations"][0]["candidate_section"]["name"],
                         ".text")

    def test_bogus_section_table_extent_refused(self):
        blob = fixture()
        struct.pack_into("<Q", blob, 40, 0x800)
        with self.assertRaisesRegex(ValueError, "section header"):
            check.parse_sections(blob)

    def test_symbol_strtab_link_invalid(self):
        blob = fixture()
        struct.pack_into("<I", blob, 0x300 + 5 * 64 + 40, 99)
        with self.assertRaisesRegex(ValueError, "symbol table dimensions"):
            check.matching_symbols(blob, check.parse_sections(blob))

    def test_section_size_beyond_end_rejected(self):
        blob = fixture()
        struct.pack_into("<Q", blob, 0x300 + 2 * 64 + 32, 0xdeadbeef)
        with self.assertRaisesRegex(ValueError, "outside file"):
            check.parse_sections(blob)

    def test_stripped_elf_reports_no_sections_or_symbols(self):
        blob = fixture()
        struct.pack_into("<Q", blob, 40, 0)
        struct.pack_into("<HHH", blob, 58, 0, 0, 0)
        result = check.inspect_sections(blob, fake_scan())
        self.assertFalse(result["section_table_present"])
        self.assertEqual(result["named_symbols"]["matching_symbol_count"], 0)
        self.assertEqual(result["candidate_locations"][0]["candidate_section"]["name"],
                         "UNMAPPED_OR_STRIPPED")

    def test_unmapped_offset_marked_not_guessed(self):
        self.assertEqual(check.containing_sections(check.parse_sections(fixture()), 0x200)["name"],
                         "UNMAPPED_OR_STRIPPED")


if __name__ == "__main__":
    unittest.main()
