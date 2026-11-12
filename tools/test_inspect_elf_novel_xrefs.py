"""Synthetic ELF64/AArch64 fixtures only; no proprietary game binary."""
import struct
import unittest

import inspect_elf_novel_xrefs as m


def fixture():
    blob = bytearray(0x220)
    blob[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<H", blob, 18, 183)
    struct.pack_into("<Q", blob, 32, 64)
    struct.pack_into("<HH", blob, 54, 56, 2)
    struct.pack_into("<IIQQQQQQ", blob, 64, 1, 5, 0x100, 0x1000, 0, 0x40, 0x40, 0x1000)
    struct.pack_into("<IIQQQQQQ", blob, 120, 1, 4, 0x180, 0x2180, 0, 0x80, 0x80, 0x1000)
    blob[0x180:0x18c] = b"novelCommand"
    struct.pack_into("<I", blob, 0x100, 0xB0000000)  # ADRP X0, 0x2000
    struct.pack_into("<I", blob, 0x104, 0x91060000)  # ADD X0,X0,#0x180
    return blob


class ElfNovelReferenceTests(unittest.TestCase):
    def novel_hit(self, blob):
        return next(row for row in m.inspect(blob)["markers"] if row["marker"] == "novelCommand")

    def test_elf_mapping_and_candidate(self):
        hit = self.novel_hit(fixture())
        self.assertEqual(hit["literal_hits"], 1)
        self.assertEqual(hit["locations"][0]["virtual_address"], 0x2180)
        self.assertEqual(hit["locations"][0]["adrp_add"]["candidate_count"], 1)

    def test_literal_without_reference(self):
        blob = fixture()
        struct.pack_into("<I", blob, 0x104, 0)
        self.assertEqual(self.novel_hit(blob)["locations"][0]["adrp_add"]["candidate_count"], 0)

    def test_wrong_architecture(self):
        blob = fixture()
        blob[18] = 62
        with self.assertRaisesRegex(ValueError, "AArch64"):
            m.inspect(blob)

    def test_program_table_out_of_bounds(self):
        blob = fixture()
        struct.pack_into("<Q", blob, 32, 999999)
        with self.assertRaisesRegex(ValueError, "program header"):
            m.inspect(blob)

    def test_segment_out_of_bounds(self):
        blob = fixture()
        struct.pack_into("<Q", blob, 64 + 32, 9999999)
        with self.assertRaisesRegex(ValueError, "load segment"):
            m.inspect(blob)

    def test_unmapped_literal(self):
        blob = fixture()
        blob[0x180:0x18c] = b"____________"
        blob[0x210:0x21c] = b"novelCommand"
        self.assertIsNone(self.novel_hit(blob)["locations"][0]["virtual_address"])


if __name__ == "__main__":
    unittest.main()
