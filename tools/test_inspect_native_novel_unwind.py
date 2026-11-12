"""All synthetic AArch64 EH-CFI records; no original game bytes."""
import struct
import unittest

import inspect_native_novel_unwind as m
from inspect_native_novel_elf_sections import parse_sections


def fixture():
    blob=bytearray(0xb00)
    blob[:6]=b"\x7fELF\x02\x01"
    struct.pack_into("<H",blob,18,183)
    struct.pack_into("<Q",blob,32,64)
    struct.pack_into("<HH",blob,54,56,2)
    struct.pack_into("<IIQQQQQQ",blob,64,1,5,0x100,0x1000,0,0x100,0x100,0x1000)
    struct.pack_into("<IIQQQQQQ",blob,120,1,4,0x200,0x2000,0,0x100,0x100,0x1000)
    names=b"\x00.text\x00.rodata\x00.shstrtab\x00.eh_frame\x00.eh_frame_hdr\x00"
    blob[0x700:0x700+len(names)]=names
    struct.pack_into("<Q",blob,40,0x300)
    struct.pack_into("<HHH",blob,58,64,6,3)
    def sec(i,name,typ,flags,va,off,size):
        struct.pack_into("<IIQQQQIIQQ",blob,0x300+64*i,
                         names.find(name),typ,flags,va,off,size,0,0,1,0)
    sec(1,b".text",1,6,0x1000,0x100,0x100)
    sec(2,b".rodata",1,2,0x2000,0x200,0x100)
    sec(3,b".shstrtab",3,0,0,0x700,len(names))
    sec(4,b".eh_frame",1,2,0x3000,0x400,0x100)
    sec(5,b".eh_frame_hdr",1,2,0x4000,0x500,0x100)
    # AArch64 CIE version1 with zR, pcrel sdata4.
    struct.pack_into("<I",blob,0x400,16)
    struct.pack_into("<I",blob,0x404,0)
    blob[0x408:0x414]=bytes([1])+b"zR\x00"+bytes([1,0x78,30,1,0x1b,0,0,0])
    # FDE covering .text [0x1000,0x1040).
    struct.pack_into("<I",blob,0x414,12)
    struct.pack_into("<I",blob,0x418,0x18)
    struct.pack_into("<i",blob,0x41c,0x1000-0x301c)
    struct.pack_into("<i",blob,0x420,0x40)
    blob[0x500:0x504]=bytes([1,0x1b,0x03,0x3b])
    struct.pack_into("<i",blob,0x504,0x3000-0x4004)
    struct.pack_into("<I",blob,0x508,1)
    struct.pack_into("<i",blob,0x50c,0x1000-0x4000)
    struct.pack_into("<i",blob,0x510,0x3014-0x4000)
    return blob


def anchors(*values):
    return {"labels":[{
        "label":"void toybox::gui::NovelCommandExecuter::createNovel(",
        "instruction_sites":[{"site_instruction_va":n} for n in values],
    }]}


class OriginalUnwindTests(unittest.TestCase):
    def test_exact_cie_fde_coverage(self):
        blob=fixture()
        info=m.find_executor_unwind_frames(blob,anchors(0x1010,0x103c))
        self.assertEqual(info["fde_index_entries"],1)
        self.assertEqual(info["executor_source_anchors"],2)
        self.assertEqual(info["exact_fde_coverage_count"],2)
        self.assertTrue(all(x["status"]=="VALIDATED_ORIGINAL_UNWIND_COVERAGE"
                            for x in info["sites"]))
        self.assertEqual(info["sites"][0]["unwind_coverage"]["start_va"],0x1000)
        self.assertEqual(info["sites"][0]["unwind_coverage"]["end_va_exclusive"],0x1040)
        self.assertEqual(info["mapped_opcodes"],0)
        self.assertFalse(info["original_import_authorized"])

    def test_fde_ends_before_anchor(self):
        info=m.find_executor_unwind_frames(fixture(),anchors(0x1040))
        self.assertEqual(info["exact_fde_coverage_count"],0)
        self.assertEqual(info["sites"][0]["status"],"NOT_WITHIN_PRECEDING_FDE")

    def test_corrupt_cie_refuses_verification(self):
        blob=fixture()
        struct.pack_into("<I",blob,0x418,0x1234567)
        info=m.find_executor_unwind_frames(blob,anchors(0x1010))
        self.assertEqual(info["sites"][0]["status"],"UNWIND_RECORD_NOT_VERIFIED")
        self.assertEqual(info["exact_fde_coverage_count"],0)

    def test_zero_fde_range_rejected(self):
        blob=fixture()
        struct.pack_into("<i",blob,0x420,0)
        info=m.find_executor_unwind_frames(blob,anchors(0x1010))
        self.assertEqual(info["sites"][0]["status"],"UNWIND_RECORD_NOT_VERIFIED")

    def test_wrong_eh_index_pointer_fails(self):
        blob=fixture()
        struct.pack_into("<i",blob,0x504,0)
        with self.assertRaisesRegex(ValueError,"unexpected frame"):
            m.find_executor_unwind_frames(blob,anchors(0x1010))

    def test_unexpected_eh_index_version_fails(self):
        blob=fixture()
        blob[0x500]=2
        with self.assertRaisesRegex(ValueError,"version"):
            m.parse_hdr(blob,parse_sections(blob))

    def test_huge_index_count_rejected(self):
        blob=fixture()
        struct.pack_into("<I",blob,0x508,m.MAX_FDE_ENTRIES+1)
        with self.assertRaisesRegex(ValueError,"table size"):
            m.parse_hdr(blob,parse_sections(blob))

    def test_signed_and_unsigned_eh_pointer_formats(self):
        blob=fixture()
        section=next(x for x in parse_sections(blob)
                     if x["name"]==".eh_frame_hdr")
        self.assertEqual(m._encoded(blob,0x504,0x1b,section)[0],0x3000)
        self.assertEqual(m._encoded(blob,0x508,0x03,section)[0],1)
        self.assertEqual(m._encoded(blob,0x50c,0x3b,section)[0],0x1000)

    def test_no_anchor_remains_unmapped(self):
        info=m.find_executor_unwind_frames(fixture(),anchors())
        self.assertEqual(info["exact_fde_coverage_count"],0)
        self.assertEqual(info["mapped_opcodes"],0)

    def test_aarch64_source_binary_rejected_if_bad(self):
        blob=fixture()
        blob[18]=62
        with self.assertRaisesRegex(ValueError,"AArch64"):
            m.find_executor_unwind_frames(blob,anchors(0x1010))


if __name__=="__main__":
    unittest.main()
