"""Synthetic ARM64 code neighborhoods only; no proprietary binary included."""
import struct
import unittest

import inspect_native_novel_xref_context as context


def test_blob():
    blob = bytearray(0x240)
    blob[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<H", blob, 18, 183)
    struct.pack_into("<Q", blob, 32, 64)
    struct.pack_into("<HH", blob, 54, 56, 2)
    struct.pack_into("<IIQQQQQQ", blob, 64, 1, 5, 0x100, 0x1000,
                     0, 0x60, 0x60, 0x1000)
    struct.pack_into("<IIQQQQQQ", blob, 120, 1, 4, 0x180, 0x2180,
                     0, 0x80, 0x80, 0x1000)
    blob[0x180:0x18c] = b"NovelCommand"
    struct.pack_into("<I", blob, 0x100, 0xa9bf7bfd)  # STP X29,X30,[SP,#-16]!
    # ADR X0, target=0x2180 from PC=0x1004
    delta = 0x2180 - 0x1004
    adr = 0x10000000 | ((delta & 3) << 29) | (((delta >> 2) & 0x7ffff) << 5)
    struct.pack_into("<I", blob, 0x104, adr)
    struct.pack_into("<I", blob, 0x108, 0x94000002)  # BL +8
    struct.pack_into("<I", blob, 0x110, 0xd65f03c0)  # RET
    return blob


def scan():
    return {"markers": [{
        "marker": "NovelCommand",
        "locations": [{
            "file_offset": 0x180,
            "virtual_address": 0x2180,
            "address_references": {
                "candidate_count": 1,
                "candidates": [{
                    "instruction_file_offset": 0x104,
                    "instruction_virtual_address": 0x1004,
                    "instruction_pattern": "ADR",
                }],
            },
        }],
    }]}


class ContextTests(unittest.TestCase):
    def test_direct_forward_call(self):
        self.assertEqual(context.decode_metadata(0x94000002, 0x1008),
                         ("CALL_DIRECT", 0x1010))

    def test_signed_backward_call(self):
        self.assertEqual(context.decode_metadata(0x97fffffe, 0x1008),
                         ("CALL_DIRECT", 0x1000))

    def test_direct_branch_and_indirect_call(self):
        self.assertEqual(context.decode_metadata(0x14000002, 0x1008),
                         ("BRANCH_DIRECT", 0x1010))
        self.assertEqual(context.decode_metadata(0xd63f0000, 0x1008),
                         ("CALL_INDIRECT", None))

    def test_frame_prologue_and_return(self):
        self.assertEqual(context.decode_metadata(0xa9bf7bfd, 0x1000),
                         ("FRAME_PROLOGUE_CANDIDATE", None))
        self.assertEqual(context.decode_metadata(0xd65f03c0, 0x1010),
                         ("RETURN", None))

    def test_literal_boundary_classification(self):
        self.assertEqual(context.classify_literal(b"\x00NovelCommand\x00", 1, "NovelCommand"),
                         "DELIMITED_OR_NONPRINTABLE_STRING")
        self.assertEqual(context.classify_literal(b"XNovelCommandMore", 1, "NovelCommand"),
                         "EMBEDDED_PRINTABLE_STRING")

    def test_genuine_executable_context(self):
        result = context.inspect_context(test_blob(), scan())
        self.assertEqual(result["candidate_site_count"], 1)
        site = result["sites"][0]
        self.assertEqual(site["possible_frame_start_offset"], 0x100)
        self.assertEqual(site["first_following_return_offset"], 0x110)
        events = site["window_control_flow_events"]
        self.assertIn({"offset": 0x108, "kind": "CALL_DIRECT", "target_va": 0x1010}, events)
        self.assertEqual(site["function_boundary_status"],
                         "HEURISTIC_ONLY_NOT_VALIDATED")

    def test_invalid_unmapped_site_fails_closed(self):
        original = scan()
        original["markers"][0]["locations"][0]["address_references"]["candidates"][0]["instruction_file_offset"] = 0x180
        with self.assertRaisesRegex(ValueError, "unmapped executable"):
            context.inspect_context(test_blob(), original)

    def test_no_native_code_bytes_are_emitted(self):
        result = context.inspect_context(test_blob(), scan())
        site = result["sites"][0]
        self.assertNotIn("bytes", site)
        self.assertNotIn("instructions", site)
        self.assertEqual(result["status"], "STATIC_NEIGHBORHOOD_ONLY_NOT_LOADER_PROOF")


if __name__ == "__main__":
    unittest.main()
