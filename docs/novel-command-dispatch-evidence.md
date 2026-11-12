# Original EU 15.1.0 novel-command opcode-to-handler evidence

**Status (2026-11-12): 25 observed numeric opcodes; 34 named native
command implementation classes; 0 opcode IDs linked to an
independently authenticated native handler. Not yet playable.**

This note deliberately separates three independent facts. Conflating any
two would make the story player silently present the wrong effects.

## 1. What the six preserved novel scripts prove

The owner-provided six encrypted \`novelCommand*.enc\` files were verified
against the **owner's original file MD5s**, and then decoded with the
**SHA-256-pinned EU 15.1.0** native Master AES-CBC / XXTEA numeric settings
locally without uploading original bytes or plaintext to GitHub.

- 1,266 decoded command rows across six scripts.
- Four unique sequences containing **801** commands, plus **465**
  content-identical repeated rows across the two known script pairs.
- **25** observed numeric slot-2 codes:
  \`1,4,5,6,7,10,11,12,15,16,18,19,20,22,23,24,27,29,30,32,36,37,39,40,41\`.
- Slot 0 is an increasing record ID, slot 1 is the exact containing
  novel-script ID, and slots 3–9 are seven valid UTF-8 command parameters.
  The publisher's field *names* and opcode execution semantics remain unknown.
- Largest observed code population: **11 = 211/801 rows**.
  Code **15 = 81** and code **18 = 73**. Codes 20 and 29 have
  empty UTF-8 parameter slots in these four original sequences.
  None of these statistics establish what a command *does*.

The machine-checkable counts for **every code and every unique script** are in
[\`data/danmemore-novel-opcode-evidence.json\`](../data/danmemore-novel-opcode-evidence.json).
The six scripts still fail the original *reference* MD5s: this is strong
structural evidence, **not a reference-authenticity override**.

## 2. What the SHA-pinned original ARM64 binary proves

An ephemeral GitHub Actions task downloaded the independently pinned EU 15.1.0
XAPK and checked the original \`libapp.so\` SHA-256
\`e49a8cc7991f8946365a28aebad605ce566b034826dd4b34a982ab18b38303b3\`
before inspecting original native **printable function / source-file-path
metadata**. It neither executed the client nor published any native bytes.

- [Real original handler-class provenance](https://github.com/salniper/DanMemoRe/actions/runs/43213233277):
  **34** distinct source-file-backed \`NovelCommand*.cpp\` handler classes
  under \`source/UI/Novel/NovelCommand/Command/\`.
- [Original executor/parameter function-name evidence](https://github.com/salniper/DanMemoRe/actions/runs/43213856579):
  \`toybox::gui::NovelCommandExecuter::createNovel(...)\`,
  \`NovelCommandExecuter::update(float)\`-related lambda metadata,
  and \`NovelCommandParam::getActionType/getFocusType/getPositionType/\`
  \`getSoundType/getTextAppearType/getQuakeTarget\` and other
  parameter-reading helpers.

The original native class inventory includes:

| Family | Original source-file class names |
| --- | --- |
| Conversation | \`NovelCommandTalkShow\`, \`NovelCommandDescriptiveText\` |
| Characters | \`NovelCommandCharacterShow\`, \`NovelCommandCharacterHide\`, \`NovelCommandCharacterMove\`, \`NovelCommandCharacterScale\`, \`NovelCommandCharacterRotate\`, \`NovelCommandCharacterAction\`, \`NovelCommandCharacterFace\`, \`NovelCommandCharacterEffect\`, \`NovelCommandCharacterZOrder\` |
| Still/image | \`NovelCommandStillShow\`, \`NovelCommandStillHide\`, \`NovelCommandImageMove\`, \`NovelCommandImageScale\`, \`NovelCommandImageRotate\`, \`NovelCommandImageWipe\` |
| LWF animations | \`NovelCommandLwfSet\`, \`NovelCommandLwfShow\`, \`NovelCommandLwfHide\`, \`NovelCommandLwfMove\`, \`NovelCommandLwfScale\`, \`NovelCommandLwfRotate\`, \`NovelCommandLwfParent\`, \`NovelCommandLwfFlip\`, \`NovelCommandLwfZOrder\` |
| Effects/text | \`NovelCommandEffectShow\`, \`NovelCommandEffectHide\`, \`NovelCommandQuakeStart\`, \`NovelCommandAnimationTextSet\`, \`NovelCommandAnimationTextShow\`, \`NovelCommandAnimationTextMove\` |
| Control/video | \`NovelCommandGoToCommandId\`, \`NovelCommandMovieStartWait\` |

These are real **source-code class names retained in the binary**.
They do **not** establish the integer enum/tag associated with
any constructor or method. 34 classes and 25 observed numeric codes
need not have a one-to-one relationship, and their naming/order must
not be used as an assumed dispatch table.

## 3. Implemented safety boundary

\`tools/verify_novel_opcode_evidence.cjs\` validates the archived numeric
opcodes, exact per-script histograms, repeated script pairs and
34 authenticated class names. It integrates into the existing
read-only six-script diagnostic. Every observed opcode is currently
\`UNMAPPED_OPCODE_ONLY\`; unobserved inputs are rejected separately.
**All codes remain non-executable.** Tests explicitly reject adding a
\`verified_native_handler\` without established dispatch proof, and
catch a modified script even if its overall aggregate stays unchanged.
No original decrypted story text is committed or logged.

## 4. Next proof required to actually play the story

1. Locate original \`NovelCommandExecuter::createNovel\` dispatch/factory
   **machine-code control flow**, not a random string/ADR bit pattern.
2. Demonstrate specific numeric opcode values causing specific
   \`NovelCommandX\` object construction, either via original binary
   validated disassembly/call-graph evidence or a **non-mutating native
   runtime trace on a disposable emulator/profile**.
3. For each mapped handler, correlate the seven parameter positions
   against the original \`NovelCommandParam\` helpers and UI playback.
   Only then implement a minimal playback adapter without inventing
   command names or animations.
4. Independently resolve or prove reference-version compatibility
   for the **12** mismatched original archive files, then perform an
   actual import and AYN Thor runtime acceptance.

**No progress in this document relaxes the importer reference MD5
gate. PR #1 stays Draft and \`main\` remains untouched.**


## 5. Original .text source-anchored instruction references (2026-11-12)

The first direct string-reference scanner was a false-positive on
\`.rodata\`: none of the four apparent \`ADR\` sites were executable code.
This round replaces that with a fresh **source-label START-address** scan
restricted to original \`SHF_EXECINSTR\` sections, using signed AArch64
\`ADR\` and \`ADRP ... ADD\` arithmetic (maximum 12-instruction gap).
It **requires BOTH** the original XAPK SHA-1 and the SHA-256-pinned
EU 15.1.0 native \`libapp.so\` before inspecting any code.

[Actual original-client .text scan](https://github.com/salniper/DanMemoRe/actions/runs/43218408459):
**60** original C++ source-path / function-name labels have at least
one **possible executable instruction reference**, with **185** candidate
sites in total. These are actual \`.text\` instruction encodings and
not the four earlier \`.rodata\` bit-pattern matches. However, the
scanner is deliberately *not* a complete ARM64 register-value analysis;
the nonadjacent \`ADRP + ADD\` results remain **candidates** and should
not be called resolved call sites.

There are **six** .text candidate instruction sites targeting the original
\`NovelCommandExecuter.cpp\` source path or the
\`NovelCommandExecuter::createNovel(...)\` pretty-function name:

| ELF code offset (file/VA) | Original target metadata |
| ---: | --- |
| 33417776 / \`0x1FDEA30\` | \`NovelCommandExecuter.cpp\` |
| 33418232 / \`0x1FDEBF8\` | \`NovelCommandExecuter.cpp\` |
| 33418460 / \`0x1FDECDC\` | \`NovelCommandExecuter.cpp\` |
| 33418464 / \`0x1FDECE0\` | \`NovelCommandExecuter::createNovel(...)\` |
| 33418496 / \`0x1FDED00\` | \`NovelCommandExecuter.cpp\` |
| 33418500 / \`0x1FDED04\` | \`NovelCommandExecuter::createNovel(...)\` |

[Source-anchored bounded code-neighborhood run](https://github.com/salniper/DanMemoRe/actions/runs/43219302678)
checked ±4 KiB around each of these six instruction locations,
classifying nearby direct/indirect branches, calls, returns and immediate
comparisons *without exporting original code bytes*. It found many
branches and calls, including conditional comparisons for small
immediates such as 31, 34 and 44 in overlapping windows. **These
numbers are not opcode mappings.** Window overlap means event counts
cannot be added across six anchors, and a nearby comparison may be
unrelated to the actual command factory.

New tools:
- \`tools/inspect_native_novel_dispatch_seeds.py\`: source-start literal
  targets + executable-section direct/nonadjacent address candidates;
- \`tools/inspect_native_novel_executor_flow.py\`: source-anchored
  bounded control-flow instruction-class summaries;
- \`tools/probe_pristine_novel_dispatch.py\`: double-fingerprint-gated
  ephemeral XAPK analysis reporting metadata only;
- corresponding synthetic code-section, indirect-registration boundary,
  source-string and instruction-class regression tests. No actual
  game binary, original script text or decryption material is in Git.

**Next proof needed:** identify an independently validated exact
\`createNovel\` function boundary and its factory/dispatcher control
flow. Trace a **specific numeric slot-2 command value through a
verified constructor target** before filling any
\`verified_native_handler\`. The mapping stays **0/25**; no new asset
has matched required reference MD5 and no scene has run on AYN Thor.
This is reverse engineering evidence, **not** an import waiver.


## 6. Exact original unwind-covered \`createNovel\` code interval (2026-11-12)

This iteration independently parsed the original **ELF .eh_frame_hdr
binary-search table (167,411 FDE entries)** and corresponding **.eh_frame
CIE+FDE records**, with no external disassembler or third-party Python
dependencies. Source archive SHA-1 and pristine EU 15.1.0 ARM64 native
SHA-256 were reverified. **All six** .text source-label instruction
anchors in section 5 fall inside **one and the same CIE/FDE-validated
code coverage range**:

- ELF virtual start **\`0x1FDE8D0\`** (decimal 33417424)
- Exclusive end **\`0x1FDEE60\`** (decimal 33418848)
- FDE-covered instruction length **1,424 bytes / 356 AArch64 words**
- FDE virtual address **61321312**; source ARM64 FDE encoding **0x1b**
- [Real original verified FDE evidence](https://github.com/salniper/DanMemoRe/actions/runs/43222352197)

A CFI range is **actual original unwind metadata**, rather than an
arbitrary +/-4 KiB neighborhood. It is still *not*, by itself, an
independent C++ symbol that unambiguously proves the semantic
\`createNovel\` function's name and identity.

### Instruction classifications ONLY inside that one original range

A second authentic original run scanned the exact 1,424-byte region,
never the overlapping broad windows:

| Instruction category | Observed instructions |
| --- | ---: |
| Direct BL calls | **33** |
| Indirect BLR calls | **7** |
| Branches (direct, conditional, compare-zero, bit-test) | **60** |
| Conditional branches | 6 |
| Compare-zero branches | 31 |
| Bit-test branches | 8 |
| Unconditional direct branches | 15 |
| Return instructions | 1 |
| \`CMP\` immediate in the supported decode pattern | **0** |

All 60 decoded branch targets in this region fall inside this FDE
range. No directly classifiable small-integer CMP immediates were found
within the exact range; other methods of numeric dispatch (register
comparison, bit masking, computed jump, another factory, indirect call
chain) remain possible and are not covered by this conclusion.
The analyzer recorded raw *addresses, categories and counts only*;
original binary words, user story data, decrypted text and crypto keys
were not emitted or committed.

[Actual precise-region instruction metadata](https://github.com/salniper/DanMemoRe/actions/runs/43222975985).

This changes the working hypothesis: **do not assume
\`NovelCommandExecuter::createNovel\` is the numeric opcode factory**.
A region with 33 external calls but no immediate equality comparisons
could be a scene setup routine. Those calls require def-use and
target/function ownership analysis before interpreting them as
construction or command dispatch.

Added source-verified and fail-closed pure Python tools:
\`tools/inspect_native_novel_unwind.py\`, including
\`summarize_verified_fde_instructions\`, the original-XAPK wrapper,
and synthetic CIE/FDE corruption, exact-boundary and instruction-class
regression tests. Original importer reference-MD5 enforcement remains
unchanged, and **0 of 25 opcode-to-handler mappings are accepted**.
Seven of the nineteen original archive mismatches have exact repairs;
the remaining twelve continue to block full import.

**Next target:** explore actual indirect call destinations and search
the native class-construction factory independently of source-string
proximity, linking a specific decoded slot-2 opcode to the construction
of a particular \`NovelCommand*\` command object before implementing
any playback behavior.
