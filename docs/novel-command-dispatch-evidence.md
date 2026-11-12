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


## 7. Verified original first-hop and second-hop function calls (2026-11-12)

Following the independently pinned **EU 15.1.0** XAPK SHA-1 and native
\`libapp.so\` SHA-256 validation, a new analyzer used the **exact
1,424-byte CIE/FDE-covered code interval** from section 6 rather than
merely searching string literals. Every \`BL\` destination was
cross-checked against the real ELF executable section and, where
available, an independent indexed CIE/FDE unwind record.

### First-hop results — actual pinned native

[First-hop original ELF source run](https://github.com/salniper/DanMemoRe/actions/runs/43238189679):

| Metric | Verified result |
| --- | ---: |
| \`BL\` call sites in the original executor FDE | **33** |
| Distinct direct call targets | **15** |
| Targets covered by CIE/FDE and located at exact FDE starts | **10** |
| Executable \`.plt\` linker-trampoline targets without FDE | **5** |
| Target FDE regions containing a confirmed command-class source label | **0** |
| Verified numeric-opcode → original handler mappings | **0** |

**Correction to an incomplete interpretation:** The five targets with
\`NO_PRECEDING_FDE\` are **all within the ELF \`.plt\` executable
section**. They are not automatically corrupt or invalid functions.
They are linker trampoline locations and cannot be interpreted as
ordinary \`.text\` methods merely from absence of FDE coverage.

### First-hop callee machine-code *shapes*

A fresh [original ELF callee code run](https://github.com/salniper/DanMemoRe/actions/runs/43238704998)
then inspected only the 10 verified callee unwind ranges and their
immediate downstream \`BL\` addresses. One **9,096-byte region**
(virtual start 33432704, end 33441800) stands out:

- 2,274 4-byte AArch64 words
- **75 \`BL\` calls to 74 distinct immediate targets**
- 428 zero-test branches, 141 direct branches, 2 conditional branches
- 2 indirect calls and 1 indirect branch
- One immediate comparison with **73** (which is *not* one of the
  25 decoded command opcodes in this owner's sample)

This region may contain highly branched construction/dispatch logic,
but neither the numeric constant 73 nor the call count independently
proves a novel-command factory. Other verified FDE code regions had
small immediate comparisons such as 7 and 23, but those numerical
coincidences are **not opcode→handler evidence**.

### Second-hop call graph — actual pinned native

[Two-hop original ELF run](https://github.com/salniper/DanMemoRe/actions/runs/43239296367):

| Metric | Verified result |
| --- | ---: |
| \`BL\` sites in the 10 original first-hop FDEs | **158** |
| Unique second-hop direct-call targets | **119** |
| Second-hop destinations with valid executable CIE/FDE | **104** |
| Second-hop destinations without preceding FDE | **15** |
| Second-hop destinations in whose FDE a previously identified \`NovelCommand*.cpp\` source-label reference is found | **0** |
| Verified numeric-opcode → handler mappings | **0** |

The \`NovelCommand*.cpp\` source-path matches are **heuristic source
metadata**, not a full RTTI/vtable/symbol/constructor register-flow
analysis. Zero source-label associations does not mean the original
handlers are absent or that the 119 targets cannot be involved in
their construction. In particular, optimized native classes may not
retain their source filenames in the constructor functions.

Added \`tools/inspect_native_novel_direct_callees.py\` with independent
FDE source-gating, exact \`.text\` vs \`.plt\` section discrimination,
one-hop code-shape classification and second-hop C++ source-label
associations. The synthetic regression suite verifies boundaries,
damaged CIE records, non-executable destinations, misleading C++
metadata, counts, and **strictly disallows granting original numeric
opcode mappings**.

**Research decision:** Stop promoting class-source-name proximity into
constructor identity. For the large 9,096-byte region and its 74
targets, the next meaningful evidence should come from actual
control/data-flow, relocation/vtable targets or independently
identified native construction functions — particularly following
the seven indirect calls in the 1,424-byte original executor FDE.
Keep the original asset-reference MD5 guard intact: exactly
**7/19** repaired; **12** mismatches and original device playback
remain unverified. PR stays Draft; do not merge.


## 8. Seven original indirect calls: two pointer loads, same vtable-shaped slot (2026-11-13)

The next original-client pass inspected **only the independently verified
1,424-byte CIE/FDE-covered ELF executable region** using the same
cryptographically pinned EU 15.1.0 ARM64 source. It classified \`BLR\`
register targets and their nearest *syntactically identifiable*
preceding 64-bit load instructions. Source code and original game bytes
were never emitted.

[Actual SHA-authenticated BLR provenance](https://github.com/salniper/DanMemoRe/actions/runs/43264838249):

- **7/7 \`BLR\` calls** use **X8**.
- Each **immediately preceding instruction** has the exact decoded
  form \`LDR X8, [X8, #16]\`.
- In each case, the nearest earlier **writer of X8** is a
  \`LDR X8, [Xobject, #0]\` whose base register is one of
  X19, X20, X21 or X24.
- For the bounded 24-instruction backward window,
  **no recognized control-transfer barrier** intervened between
  the source load and the final call. These are *linear syntactic*
  observations, not full SSA or runtime pointers.
- All seven form the classic *vtable-shaped* pattern
  \`LDR X8,[Xobject]; LDR X8,[X8,#16]; BLR X8\`.
  The object identity, memory contents and actual function pointer
  address are still unknown.

| Original call VA | Source of first pointer | Final pointer load | Interpretation |
| ---: | --- | --- | --- |
| 33417672 | X24 + 0 | X8 + 16 | Candidate virtual-call shape |
| 33418048 | X20 + 0 | X8 + 16 | Candidate virtual-call shape |
| 33418076 | X24 + 0 | X8 + 16 | Candidate virtual-call shape |
| 33418388 | X19 + 0 | X8 + 16 | Candidate virtual-call shape |
| 33418712 | X21 + 0 | X8 + 16 | Candidate virtual-call shape |
| 33418764 | X20 + 0 | X8 + 16 | Candidate virtual-call shape |
| 33418828 | X20 + 0 | X8 + 16 | Candidate virtual-call shape |

The offset \`#16\` is **relative to the pointer currently in X8**;
it is **not** a proven physical vtable start, method number, or
\`NovelCommand\` opcode. C++ ABIs can use vtable address-point
adjustments, and the register contents might still be something else.
The decoded static instructions do not prove that those virtual
dispatches occur during story playback.

The new
[\`tools/inspect_native_novel_indirect_calls.py\`](../tools/inspect_native_novel_indirect_calls.py)
uses a strict whitelist of common AArch64 register-load/ADR/MOV
patterns and explicitly labels every proposed earlier register
definition \`LINEAR_SYNTAX_ONLY_NOT_REACHING_DEFINITION\`.
Synthetic tests include literal/page addressing, register copies,
branch barriers, unrecognized writers, malformed CFI coverage,
and metadata-count mismatches.
No original client binary, owner assets or keys are committed.

**Implication for the next research pass:** Track the lifetime/origin
of X19, X20, X21, X24 and original construction/assignment sites,
or perform controlled runtime logging of the actual vtable pointer
contents on a disposable original-client environment. A verified
call-target identity and numeric slot-2 opcode flow are required
before registering any of the 25 opcode handlers.

**No opcode-to-handler mapping was authorized (0/25); no playback
implemented; reference MD5 import blockers remain 12/19.** PR #1
continues as Draft with \`main\` and owner backups untouched.
