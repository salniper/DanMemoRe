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
        self.assertEqual(hit["locations"][0]["address_references"]["candidate_count"], 1)

    def test_adr_literal_reference(self):
        blob = fixture()
        # ADR X0,#0x118 at PC 0x1068 => mapped 0x2180.
        # Synthetic direct ADR points to exactly the same literal as ADRP+ADD.
        # At file offset 0x100, PC=0x1000; target=0x2180 exceeds ADR range? No (0x1180).
        # immhi = displacement >> 2, immlo = displacement & 3.
        displacement = 0x2180 - 0x1000
        instruction = 0x10000000 | ((displacement & 3) << 29) | (((displacement >> 2) & 0x7ffff) << 5)
        struct.pack_into("<I", blob, 0x100, instruction)
        struct.pack_into("<I", blob, 0x104, 0xd503201f)
        hit = self.novel_hit(blob)
        refs = hit["locations"][0]["address_references"]
        self.assertEqual(refs["candidate_count"], 1)
        self.assertEqual(refs["candidates"][0]["instruction_pattern"], "ADR")

    def test_reference_beyond_first_forty_literals_is_not_dropped(self):
        blob = fixture()
        blob.extend(b"\x00" * 0x500)
        struct.pack_into("<QQ", blob, 120 + 32, 0x500, 0x500)
        for i in range(41):
            at = 0x180 + 12 * i
            blob[at:at + 12] = b"novelCommand"
        # ADRP X0,#0x2000; ADD X0,X0,#0x360 => the 41st literal.
        struct.pack_into("<I", blob, 0x104, 0x910d8000)
        hit = self.novel_hit(blob)
        self.assertEqual(hit["literal_hits"], 41)
        self.assertEqual(hit["referenced_literal_hits"], 1)
        self.assertEqual(hit["locations"][0]["file_offset"], 0x360)
        self.assertEqual(hit["locations"][0]["address_references"]["candidate_count"], 1)
        self.assertTrue(hit["truncated"])

    def test_single_pass_agrees_with_single_target_helper(self):
        blob = fixture()
        segments = m.elf_segments(blob)
        self.assertEqual(m.find_references_multi(blob, segments, (0x2180,))[0x2180],
                         m.find_references(blob, segments, 0x2180))

    def test_literal_without_reference(self):
        blob = fixture()
        struct.pack_into("<I", blob, 0x104, 0)
        self.assertEqual(self.novel_hit(blob)["locations"][0]["address_references"]["candidate_count"], 0)

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
