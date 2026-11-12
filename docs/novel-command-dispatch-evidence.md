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
