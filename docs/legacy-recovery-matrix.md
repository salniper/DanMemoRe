# Legacy preservation: unresolved-asset triage

Evidence: user's 2026-11-10 `danmemore_legacy_audit.json` (no game bytes committed).
This is a *recovery checklist*, not permission to bypass verification.

## Audit overview

- 86,828 assets match the Alpha 10 reference exactly.
- 1 `1/manifests/voice_episode.manifest` matches the pinned historical snapshot.
- 1,544 Phase 3 gacha background names are absent from the old catalog;
  the Launcher carries bundled replacements, subject to actual import testing.
- 33 Phase 1 files are absent but appear in both reference and historical
  catalogs (the exact allowlist lives in `LegacyImportPolicy.kt`).
- 19 present files fail both reference and pinned historical fingerprints.
  **The current legacy importer must reject this archive.**

## 19 present but unverified bytes

| Class | Count | Paths | Priority |
| --- | ---: | --- | --- |
| Phase manifest metadata | 7 | `1/manifests/phase.manifest.{1,2,3,4,6,7,8}` | P0: determine format/version relationships |
| Encrypted game catalogs | 4 | `1/master/divide_enc/{adventureMission,downloadVoicePhase,lotteryWeightGroup,subscription}.enc` | P0: backend/runtime consistency |
| Encrypted story commands | 6 | `1/master/divide_novel_command_enc/novelCommand{751040548,751040550,751040806,751040815,751041273,751041275}.enc` | P0 before story acceptance |
| Font texture | 1 | `1/files/font/number.png` | P1: visual/runtime check |
| Gacha atlas JSON | 1 | `3/files/ui_atlas/home_gacha/gacha_top_move_parts_text.json` | P1: compare structured content |

**Never** bless a mismatched file just because it has the expected length.
The eight historical `project.manifest` file SHA-256 values and per-file MD5
values are already pinned in the importer.

## 33 missing Phase 1 files

- 6 LWF logo/animation objects for regular/iPhone X home/title paths.
- 2 title backgrounds: `files/ui/title/bg_1.jpg` and
  `files/ui/title/iphone_x/bg_1.jpg`.
- 1 soundtrack: `files/sound/bgm/bgm_main_theme.ogg`.
- 24 UI atlas, network, modal, profile, settings and `textures.0.plist`
  definitions (see `LegacyImportPolicy.allowedPhase1Missing`).

The 33 file paths total far less than the preserved game archive. The main
difficulty is authenticity and runtime compatibility, not download bandwidth.

## Verified source for all 33 missing files (2026-11-11)

The preserved public Google Drive backup includes the original
`com.eu.danmemo_2023-12-22.apk` (80,881,609 bytes). This **EU** APK has been
inspected directly, rather than assuming Taiwanese assets are interchangeable.

Pinned source APK SHA-256:
`36713f18a6e9fec3302384b8d67383b12761f782d73932cb62b31b230053c3b6`

**Result: all 33 missing files are present in the APK and all 33 match the
reference *and historical* MD5 and size.**
- 32 files live under `assets/common/<path-without-phase>`.
- `1/files/sound/bgm/bgm_main_theme.ogg` lives under
  `assets/files/sound/bgm/bgm_main_theme.ogg`.
- Combined verified size: **3,323,167 bytes**.
- The checked files include logo animation, normal and iPhone X title
  backgrounds, BGM and UI/atlas JSON and plist data.

The tool `tools/recover_legacy_apk_assets.py` uses the original APK on
the user's own device. It does not commit, redistribute or re-download
game assets. It defaults to a **dry run**; `--apply` can add only files
that are absent and match pinned per-file MD5 + size. It will not
silently replace existing files. It also pins the user's historical
`contents/1/project.manifest` SHA-256.

```bash
python3 tools/recover_legacy_apk_assets.py \
  --apk /path/to/com.eu.danmemo_2023-12-22.apk \
  --audit /path/to/danmemore_legacy_audit.json \
  --contents /path/to/contents
# Add --apply ONLY after inspecting dry-run output.
```

**The 19 unrelated mismatches remain a hard blocker** for strict Legacy
Import. Recovering these 33 assets does not make the archive bootable.
Keep the original six RAR parts untouched.

## 19 mismatches: audited facts and next forensic pass (2026-11-11)

Compared the actual user audit metadata to both historical and reference
fingerprints and searched the original 2023-12-22 EU APK's entries for exact
expected MD5 and size.

| Finding | Result |
| --- | --- |
| Unknown local file fingerprints | **19** |
| Sum of these 19 file lengths | **104,886 bytes** |
| Actual lengths equal referenced lengths | **19/19** |
| Reference MD5 equals pinned historical MD5 | **19/19** |
| Exact MD5+size matches among candidate files in original EU APK | **0/19** |

Breakdown: **7 phase metadata**, **6 encrypted story commands**,
**4 encrypted game catalogs**, **1 PNG font texture**, **1 gacha UI JSON**.

Matching size does **not** establish correctness. Identical reference and
historical hashes rule out automatic acceptance as a known different pinned
snapshot. A different encryption key/IV, changed in-place content, or storage
corruption are hypotheses, **not** confirmed causes.

The EU APK genuinely contains all previously absent 33 assets, but does
**not** furnish byte-exact replacements for these 19 mismatches.

### Device-side read-only diagnostic

The new `tools/inspect_legacy_mismatches.py` is intentionally separate from
the recovery writer. Use the original audit and the preserved extraction:

```bash
python3 tools/inspect_legacy_mismatches.py \
  --audit /storage/emulated/0/Download/danmemore_legacy_audit.json \
  --contents /storage/emulated/0/Download/contents \
  --output /storage/emulated/0/Download/danmemore_mismatch_triage.json
```

This checks actual bytes against the audit again and reports SHA-256
fingerprints, PNG chunk CRCs, JSON parsing where applicable, and whether
opaque `.enc` files have a 16-byte-aligned length. **None of these format
checks authorize mismatched bytes**. No game content is included in the JSON
result. All source paths are only read; output must be outside `contents`
and will refuse to overwrite a pre-existing report.

Without `--contents`, only audit-metadata classification is possible;
this cannot distinguish legitimate content changes from data corruption.

Nine synthetic negative/positive Python regression tests run in the
`Legacy Import policy` workflow, alongside recovery and Kotlin tests.

**Next decision gate:** review on-device report, then look for a
*second independently preserved EU dump* or another trusted asset source
for exact SHA/MD5 recovery. Do not patch original data or bypass the 19
file-level checks on the strength of metadata alone.

## Cross-check of the user's on-device triage (2026-11-11)

The AYN Thor produced a full 19-item `ON_DEVICE_REHASH` report:
every item had `audit_recheck=MATCH` against the prior local audit.
The result means unchanged **unverified** bytes, not a match to the
official reference or historically pinned manifest.

Structural read-only checks on the device reported:
- 7/7 phase manifests parse as JSON objects;
- `1/files/font/number.png` has valid PNG chunk CRCs;
- `3/files/ui_atlas/home_gacha/gacha_top_move_parts_text.json`
  parses as JSON;
- all ten opaque `.enc` files have lengths divisible by 16 bytes,
  which does not authenticate their encryption or plaintext.

### Public loose-file mirror comparison

A [public asset folder](https://drive.google.com/drive/folders/1xqzfdevOO7ph1ppck9t8TiwzJVXpr4Yb)
contains the same EU backup assets as separate files. Independently
fetched **13 of the 19** mismatches and recomputed their MD5 and SHA-256.
All thirteen matched the user's reported on-device fingerprints exactly:

| Compared category | Identical bytes | Additional observation |
| --- | ---: | --- |
| `1/manifests/phase.manifest.{1,2,3,4,6,7,8}` | 7/7 | Valid JSON, empty `assets`; `version` is `582a6b5539f7766be40c5d2e36aca01b phased` |
| `1/master/divide_enc/{adventureMission,downloadVoicePhase,lotteryWeightGroup,subscription}.enc` | 4/4 | 16-byte-aligned opaque data; high byte entropy is consistent with ciphertext, not proof of correctness |
| `1/files/font/number.png` | 1/1 | 109×179 PNG |
| `3/files/ui_atlas/home_gacha/gacha_top_move_parts_text.json` | 1/1 | Valid JSON with a `root` object |
| Six `novelCommand*.enc` files | **not independently fetched** | Their AYN Thor rehash checks all match the original audit |

The same folder's `phase.manifest.5`, which is not among the 19
mismatches, instead reports `4ab12a6c3f219553661ff647ae79e322 phased`.
This points toward a mixed or phased version state in the preserved
dataset; it does **not** establish that the seven mismatches are safe to
accept. Their reference MD5 checks still fail.

**Important provenance limitation:** The public loose-file folder and the
user's six-part RAR dump appear to be mirrors of one preservation
collection (the APK and Directory.txt are also the same). Thus the
matching hashes corroborate stability, but do **not** constitute a
second independently captured build. None of these 13 mismatches is
promoted to verified status, and all original import guards remain in place.

Next evidence needed: a truly independent EU-version game cache,
or a reproducible decryption/semantic comparison from original client
logic. Filename or 16-byte alignment alone is not an acceptance
criterion. Continue with read-only checks; never rewrite the originals.

## AYN Thor on-device mismatch triage: received 2026-11-11

The user ran `tools/inspect_legacy_mismatches.py` on their AYN Thor and
supplied `danmemore_mismatch_triage 2(1).json`. Source content was not
uploaded to the repository; this section records only verified metadata.

- `inspection: ON_DEVICE_REHASH`, `verdict: DO_NOT_IMPORT_UNVERIFIED_BYTES`
- **19/19** `audit_recheck: MATCH`. This means the device's bytes are
  unchanged since the previous mismatch audit, **not** that they match
  trusted expected MD5.
- Every actual file length equals the reference length. Total: **104,886
  bytes**. Reference and historical MD5 agree for all 19, but differ
  from the on-device contents.
- **7/7** phase manifest files parse as JSON objects, all exposing the
  same seven keys: `assets`, `engineVersion`, `packageUrl`,
  `remoteManifestUrl`, `remoteVersionUrl`, `size`, `version`.
  No actual field values were included in the report; the cause of the
  mismatch has not yet been determined.
- **10/10** opaque `.enc` files are 16-byte aligned. This is a weak format
  property, **not** decryption, integrity, authenticity, or compatibility
  confirmation.
- `1/files/font/number.png` has valid PNG chunk framing and CRCs;
  `3/files/ui_atlas/home_gacha/gacha_top_move_parts_text.json` is
  syntactically valid JSON. Neither establishes trusted original content.

**Triage conclusion:** There is no evidence of further byte changes on
the device since the earlier audit, but there is **no new authorization**
to import any of the 19 mismatching files. No bypass or allowlisting.
Next: obtain *actual bytes* of only the seven small phase manifests
(~2.5 KB total) for safe structured comparison, then inspect the remaining
12 files separately against independent authoritative sources. Avoid
sharing the whole 12+ GB game backup unnecessarily.

## Actual 19-file byte analysis and verified repair (2026-11-11)

Source: user-supplied `danmemore_19_payload.json`, decoded and independently
compared against the earlier `danmemore_legacy_audit.json`. **No game bytes
or Base64 payload are stored in Git.** All 19 decoded source MD5s matched
their previous audited MD5s and sizes.

### Three source-verified phase manifests can be restored exactly

The files `1/manifests/phase.manifest.6` (354 bytes) and
`1/manifests/phase.manifest.7` (355 bytes) contain three occurrences each
of the 32-character version token
`582a6b5539f7766be40c5d2e36aca01b`. Replacing **all three**
occurrences with `4ab12a6c3f219553661ff647ae79e322` preserves file
length and produces the **exact MD5 pinned independently by both reference
and historical project catalogs**.

A third file, `phase.manifest.3` (356 bytes), also requires correcting
its numeric `size` field from `2911947083` to `2912187403`
(**+240,320**). This was found by comparing actual source bytes against
the independently pinned expected MD5, then fully reverified.

| File | Audited original MD5 | Verified repaired MD5 |
| --- | --- | --- |
| `phase.manifest.3` | `9c8a8af335450ae14b0801cd6db867af` | `a7aeb999419e537e585f08eaaddb2128` |
| `phase.manifest.6` | `cf8ddbb794e32996e5445473a65601e0` | `978673603b2d29df0ef9b53447ba0bcd` |
| `phase.manifest.7` | `deb4b0c78a04b83afce86b73d94909a0` | `3bc336eab43c1c16350aab4a9a0ee5f4` |

All three repairs were **actually reproduced from the uploaded source bytes**
with the expected MD5, not merely inferred. All three repaired SHA-256
digests are also pinned in
`tools/repair_verified_phase_manifests.py`, which checks the original
SHA-256 and writes repaired files to a **separate output folder** only on
explicit `--apply` (dry run by default). It refuses to overwrite files or
write inside the source `contents` directory.

The **four other** differing phase manifests (`.1`, `.2`, `.4`, `.8`)
have matching JSON keys but did **not** match their expected MD5 under the
same version token replacement. A bounded search modifying only their
numeric `size` field also failed: within ±1,000,000 of source sizes for
all four, and within ±10,000,000 for `.4` and `.8` (±20,000,000 for `.2`).
This does **not** establish that their intended content is different in
other fields; it only limits this particular recovery hypothesis. Do not
infer those four target byte strings from the three successful examples.

### Remaining 12 bytesets are not independently authenticated

- Ten `.enc` assets have 16-byte-aligned lengths, no duplicate 16-byte
  blocks within each file, and byte entropies around 7.55–7.99 bits/byte
  (the smallest 480-byte sample has the lowest entropy). These features
  are **consistent with** opaque ciphertext, but reveal no authenticated
  plaintext, key, or root cause of the mismatch. Do not rewrite or bypass.
- `number.png` is an independently decodable 109 × 179 PNG (LA mode,
  valid chunk CRC), with EXIF and text metadata including creation
  timestamps from 2023-04-17. Validity does not prove pixel identity with
  the trusted original image, and no reference pixel hash is available.
- `gacha_top_move_parts_text.json` is parseable JSON with a `root`
  object and CRLF line endings. No authenticated original JSON bytes are
  available for comparison; JSON validity does not prove equivalence.

**Updated status: 3/19 mismatches have a proven byte-exact repair,
16/19 remain unresolved.** The preserved source still does **not** pass
strict Legacy Import until the other 17 are resolved; do not merge or
activate based on this partial recovery.



### Original EU APK's `divide_bundled_enc` is not a replacement cache

Independently inspected the original 2023-12-22 EU APK. Under
`assets/common/master/divide_bundled_enc/` it contains 431 `.enc`
entries: 413 are 32 bytes long, and 404 have **identical 32-byte contents**
(MD5 `41513d9806ee3f9f2425765856a2a8e1`).
The four named bundled files `adventureMission`,
`downloadVoicePhase`, `lotteryWeightGroup`, and `subscription`
are all among these 404 identical 32-byte files.

The four *actual* legacy `divide_enc` sources are instead 480–8,272
bytes each. Their source bytes are not recovered by taking the same-named
APK bundled entries. This is consistent with APK-resident default/stub
data, but the exact client-side fallback semantics have not been proven.
None of these four pass the reference MD5 and none may be substituted.

## Authentic master-data provenance: two encrypted files (2026-11-12)

The upstream `tools/decode_master_data.cjs` is a native-client-derived
AES-256-CBC, zlib and FlatBuffers decoder. It reads the original
`contents/1/master/divide_enc/<name>.enc` bytes and records each input
SHA-256 and decoded row count under the `sources` object of
`data/danmemore-master.json`.

We verified this against the published source export using a read-only
GitHub Actions check:
[run 43057238235](https://github.com/salniper/DanMemoRe/actions/runs/43057238235).
The check parses only the compact source-fingerprint JSON prefix;
it does not publish game data or decryption keys.

The CI job additionally enforces exact, **fail-closed** SHA-256 matches
for `lotteryWeightGroup` and `subscription` against the independently
rehashed source SHA-256 fingerprints from the supplied AYN Thor audit. A missing export entry or a
changed source SHA must fail the job; six synthetic tests also exercise
invalid metadata and five new positive/negative expected-hash checks.
This is a provenance regression guard, **not a change in import policy**.

| File | Uploaded AYN Thor SHA-256 vs upstream source | Exported rows |
| --- | --- | ---: |
| `lotteryWeightGroup.enc` | **exact match:** `0217c8b751ec3baa5a33089a8db1c5b6123bd9301962fa806f450f14d88cbd2a` | 90 |
| `subscription.enc` | **exact match:** `45e0a9c947fe45e8b9b4122e0e5f88d46cc5ef58e44e559d8fc082870d64e1fb` | 2 |
| `adventureMission.enc` | not included in upstream's decoded master export | unknown |
| `downloadVoicePhase.enc` | not included in upstream's decoded master export | unknown |

The two matching sources have much stronger provenance than length/entropy
alone: the published export associates their **exact source bytes** with
decoded master records. The other two were **not exported by this tool**;
absence here is not a failed decryption test, nor proof of corruption.

**Critical distinction:** both matching files still differ from the
reference and historical `project.manifest` MD5. A successfully decoded
source export is not the same as authenticated compatibility with the
strict preserved ZIP import. We have **not** changed the import policy to
accept these alternative hashes.

Current classification:
- 3/19 files have byte-exact reference-MD5 repair (phase manifests 3, 6, 7)
- 2/19 additional files have independent upstream decode-source provenance,
  but **remain MD5 mismatches** (lotteryWeightGroup, subscription)
- 14/19 lack either proof: phase manifests 1, 2, 4, 8 (4);
  story commands (6); other master data (2); image and gacha JSON (2)

The original user's archive is **still expected to be rejected**. No
APK import or AYN Thor runtime smoke test has occurred.

## Separate verified-recovery overlay (2026-11-12)

The 33 absent Phase-1 resources were rechecked against the user's actual
`com.eu.danmemo_2023-12-22.apk` and original audit: **33/33 exact reference
MD5 and byte size matches**, independently from the initial detection.
The three known-restorable phase manifests (`.3`, `.6`, `.7`) were
also reverified directly from the uploaded source payload:
**3/3 restored bytes match both the pinned reference MD5 and the repaired
SHA-256**.

`tools/prepare_legacy_recovery_overlay.py` combines these 36 assets
without touching the extracted `contents`:

- Checks the original EU APK's pinned SHA-256.
- Checks `contents/1/project.manifest` against the pinned historical
  project SHA-256; cross-checks its 33 entries against the audit.
- Fails unless there are exactly 19 original mismatch audit entries.
- Rechecks exact original and corrected fingerprints for all 3 phase
  manifests; rejects changes since the user's first audit.
- Rejects unexpected, differing files at any of the 33 missing targets.
- Defaults to **dry-run**. On `--apply`, creates **only a new, distinct**
  output directory with 36 individually checked files. Never overwrites a
  source game file, ZIP, APK, previous output, or cached game installation.
- Reports **16 still unverified files**, and deliberately refuses to
  describe the partial overlay as a playable or importable game.

Example on the owner's private device, **only after** locating the actual
2023-12-22 EU APK and original audit:

```bash
python3 tools/prepare_legacy_recovery_overlay.py \
  --apk /storage/emulated/0/Download/com.eu.danmemo_2023-12-22.apk \
  --audit /storage/emulated/0/Download/danmemore_legacy_audit.json \
  --contents /storage/emulated/0/Download/contents \
  --output-dir /storage/emulated/0/Download/danmemore_verified_overlay
```

Add `--apply` **only to create a new isolated overlay** after a successful
dry run. The overlay is **not** yet a valid complete Legacy Import archive;
do not attempt to install/import it as such. The original historical
content, backup RARs and source APK remain unchanged.

### Reference project asset totals are not phase-header size values

The independent current `data/manifests/project.manifest.{1,2,4,8}`
asset totals are **629,644,526**, **403,167,299**, **1,381,743,123** and
**279,819,434** bytes respectively. Tested substituting these as the
`size` field of the user's four remaining phase manifests, along with
the known version-token substitution. **0/4** matched the expected phase
MD5. This rules out the naive `size = sum(current project assets)`
repair for those four files, but does not establish the right values.
Do not auto-regenerate or trust a phase manifest solely from present
project asset totals.

## Recovery sequence

1. **Search for authentic EU-version assets first** from a legitimately
   preserved APK/extracted game cache or another archived dump.
2. A Taiwanese installation still rendering title and playing the music is
   an additional *candidate* source. Taiwanese and EU packages are not
   automatically interchangeable. Do not remove or reset the working install.
3. Validate each recovered candidate against the exact target path's reference
   MD5 + byte size (or independently documented historical manifest entry).
4. Separately analyze the seven phase manifests: they may describe a different
   download state; do not overwrite them with fabricated values.
5. Repack a *copy* of source data only when verified. Keep six original RAR
   parts and the extracted `contents` untouched.
6. Run safe import and emulator acceptance tests before asking an AYN Thor
   device to ingest tens of gigabytes.

## Clear stop/go conditions

- **Stop:** any unverified source bytes remain; the current strict importer
  rejects them by design.
- **Stop:** an unknown missing path appears or a pinned manifest changes.
- **Stop:** APK compilation/installation or Android JNI runtime not validated.
- **Go to *limited* smoke test only when** all fingerprint gates pass,
  opening/title resources are verified or genuinely handled, adequate
  storage exists, and a disposable save is used.
- **Do not claim full offline play** after a successful login or title screen;
  story, battle, gacha and persistence require separate verification.


## Six encrypted story commands: bounded read-only decoder probe (2026-11-12)

New diagnostic: `tools/inspect_story_command_compat.cjs`; synthetic checks:
`tools/test_inspect_story_command_compat.cjs`.

- It requires the six exact `novelCommand*.enc` audit entries, rehashes
  each source against the audit, rejects symlinked paths, and reports SHA-256.
- With no original client binary, it makes **no** decryption claim.
- Optionally, with the independently SHA-256-pinned pristine 15.1.0 ARM64
  image, it uses the existing native-derived master AES-256-CBC/zlib
  decoder as a **hypothesis probe**, not a demonstrated story loader.
- It never writes decrypted bytes or original assets. Success at inflate
  establishes only compatibility with that candidate cipher/decompression
  path; it does not prove story command schema, semantic correctness,
  reference MD5, runtime acceptance or import eligibility.
- All six remain `UNVERIFIED_DO_NOT_IMPORT` regardless of probe outcome.
  There is no run against the user's six actual command bytes here.

Example on a **separate offline research checkout**, not the AYN Thor:
```bash
node tools/inspect_story_command_compat.cjs \
  --audit /path/to/danmemore_legacy_audit.json \
  --contents /path/to/extracted/contents
# Optional only if the pristine 15.1.0 ARM64 image is already locally available:
#   --native-binary /path/to/original/arm64.so
```

Next proof gate: identify the native novel-command loader and actual decoded
schema; cross-check with an independently archived compatible EU asset version.
Do not infer these six are authenticated from AES/zlib probe success.


### Pinned six-file observed snapshot (not reference authentication)

The owner's 2026-11-11 read-only on-device triage reported these six bytesets,
independently of the *expected* reference MD5. These SHA-256 values are for
tracking the **observed unverified backup**, not an alternative import allowlist.

| Story command ID | Observed bytes | Observed SHA-256 |
| --- | ---: | --- |
| 751040548 | 8,464 | `d53a86d5cd262d1079b689cacad417f72a6440b3510718a9d0f04713f005c944` |
| 751040550 | 17,376 | `d9faa5a25ad4b3c840a97983c621b42eb3311a9580c0a90589803c3a7576cd73` |
| 751040806 | 7,632 | `8798ef7781b21b499f60e8c839680fd16f2fe99a108382e6a81bddc22f8f6d03` |
| 751040815 | 17,600 | `753baa9da840dec0d9b517ab25ad9b0fb5b8b7a717cb81c9ebf08c3dc2d6c4d5` |
| 751041273 | 8,464 | `def70d37c83ecac2baf017dc804e12b05bfbb8aef42b973bdef00d81b384da5d` |
| 751041275 | 17,376 | `43273430625a751ffacda93f60a7cb6469e971c7f066322d0ee71208936cd644` |

The equal-length pairs (548/1273 and 550/1275) have **different
SHA-256s**. Equal length alone does not demonstrate identical commands or
a shared schema. All six remain reference-MD5 mismatches.


## Native novel-command loader discovery: bounded static evidence pass (2026-11-12)

Review of existing repository source found an independently pinned native-derived
**master** decoder (`tools/decode_master_data.cjs`) for AES-256-CBC, zlib
and FlatBuffers master tables. That implementation reads from
`1/master/divide_enc/`, **not**
`1/master/divide_novel_command_enc/`. The existing offline-client
bootstrap reaches an interactive opening story in an ARM64 emulator,
but this is **not evidence** that the six mismatched preserved story
commands parse or load.

New tool: `tools/inspect_native_novel_loader_markers.py`.

- Accepts only the pristine original 15.1.0 ARM64 binary whose exact
  SHA-256 is already pinned in `decode_master_data.cjs`.
- Performs literal, read-only scans for likely novel-command loader
  path/name markers and reports only hit counts and bounded *file offsets*.
  Outputs neither binary bytes, decrypted text, keys nor game assets.
- Filesystem symlinks, wrong SHA-256, empty or oversized binaries fail
  closed. Six synthetic regression tests cover matches, absent markers,
  truncation, wrong hash, symlink and input bounds.
- Literal matches are **not** function boundaries, virtual addresses,
  call references, native parser proof or authenticity evidence.
  No literal match is likewise not evidence the loader does not exist.
- **No actual original ARM64 image was scanned during this research pass**;
  the results must remain `NOT_RUN` until an independently pinned
  binary is made available to the analysis environment.

Offline usage on an existing research checkout with the intact binary:
```bash
python3 tools/inspect_native_novel_loader_markers.py \
  --binary /path/to/pristine_15.1.0_arm64.so
```

Next native proof gate: correlate any candidate literal file offsets with
ELF segment mapping and real AArch64 code references; document the
file-open, decrypt/decompress and parser chain from the actual native
client. Afterward, separately check the six observed encrypted bytes
against that verified chain, with schema/semantic validation and the
reference MD5 barrier kept intact. No AYN Thor install or import is
justified by this scan alone.


## Native ELF64 AArch64 cross-reference candidates (2026-11-12)

Added `tools/inspect_elf_novel_xrefs.py`, with six synthetic ELF
regression tests, extending the simple literal scan into **bounded
static candidate discovery**:

1. Verify the existing pinned pristine 15.1.0 ARM64 image SHA-256
   before reading/processing it.
2. Parse little-endian ELF64 AArch64 `PT_LOAD` program headers.
   Map literal file offsets to unique virtual addresses.
3. In executable load segments, look only for **adjacent** ADRP+ADD
   instruction pairs that compute a literal's mapped address.
4. Report bounded candidate instruction file offsets and virtual
   addresses, never the original binary bytes or cryptographic material.

This is deliberately conservative and incomplete: compilers can use
indirect data references, GOT relocations, register moves or other
address-construction sequences, and a candidate ADRP+ADD does not
identify a function, runtime invocation, parser or decryption routine.
Absence of a match is not negative compatibility evidence.

Six synthetic tests passed locally for valid mapping/reference,
unreferenced literal, wrong architecture, malformed program-header
bounds, malformed load segment and unmapped literal. The CI job is
configured but has **not** yet been confirmed green for the latest
GitHub branch.

No actual original 15.1.0 ARM64 binary was available in the analysis
environment for scanning. **There are no verified native story loader
addresses or genuine six-file decode results at this point.**
No source data, import policy, APK installation or main branch changes.

Usage on a pre-existing isolated research checkout:
```bash
python3 tools/inspect_elf_novel_xrefs.py \
  --binary /path/to/pristine_15.1.0_arm64.so
```

Next gate: inspect candidate code using an actual ARM64 disassembler,
tracing its string-building/file-open and decrypt/decompress calls
through the real native loader. Only after the complete call chain is
verified should the six observed novel command files be tested against
the verified decoder and schema. Reference MD5 restrictions remain.


## Real compiler evidence: ADR was previously missed (2026-11-12)

A minimal C source returning the literal strings `divide_novel_command_enc`
and `novelCommand` was compiled locally using Clang with
`--target=aarch64-linux-gnu -fPIC -O2 -fuse-ld=lld -nostdlib -shared`.
The resulting synthetic AArch64 ELF was independently inspected using
`llvm-objdump` and the segment mapping analyzer:

- `divide_novel_command_enc`: compiler emitted single `ADR` at
  ELF file offset `0x310` (virtual address `0x10310`) to literal
  virtual address `0x290`. The previous adjacent-ADRP+ADD-only scanner
  reported **zero candidates** for this genuine reference.
- `novelCommand`: compiler emitted adjacent `ADRP + ADD` at
  virtual addresses `0x10318` and `0x1031c`; the previous scanner
  found this candidate correctly.
- The scanner now also recognizes direct `ADR` PC-relative immediates;
  a synthetic ADR fixture tests this instruction path.

These are **compiler-generated synthetic fixtures**, not original game
binary addresses. The result establishes a real false-negative class,
not the actual novel loader, encryption path, or six-file compatibility.
Additional compiler idioms (GOT indirections, LDR literals, multi-step
register flows) remain outside this bounded scanner. A no-hit result
must never be treated as proof of loader absence.

The new test's CI conclusion remains a separate verification requirement.
No import guard, game content, Android install, or `main` branch was changed.


## All seven phase manifests byte-exactly recovered (2026-11-12)

Using the owner's previously uploaded `danmemore_19_payload.json` and
`danmemore_legacy_audit 3(1).json`, all seven Phase-1 phase manifest
mismatches are now recoverable to **the exact current-and-historical
reference MD5** without bypassing validation. Before repair, all source
byte lengths and actual MD5s were independently rechecked against the
uploaded audit. The repair consists solely of all three known 32-character
version-token occurrences, and (where needed) the one numeric `size`
field; repaired byte length stays unchanged.

The four new numeric values were found by bounded numeric MD5 search of
the pinned template, **then independently reconstructed and verified**.
The older `.3`, `.6`, `.7` repairs remain unchanged.

| File suffix | Original `size` | Verified `size` | Reference MD5 | Corrected SHA-256 |
| --- | ---: | ---: | --- | --- |
| `.1` | 536818947 | 623213094 | `48301e64e3fba6508ba6033e4e7b2742` | `ec0e35a630e80cecdcdde75dd249ea753b42535b0cd3812556d72ee5ba9930f6` |
| `.2` | 628755188 | 728637082 | `6dc83eeac2c38e1787e78bc8b02d305a` | `ac798e3544caa70311b854051931dd16319f6cfd1b90f2b3004b0bfb44e756d1` |
| `.3` | 2911947083 | 2912187403 | `a7aeb999419e537e585f08eaaddb2128` | `5eac0e62ba84234a421e06ce6acd2f1e07bdfe3aaf2cb25880be5d8bca242a09` |
| `.4` | 1065258112 | 1745645577 | `6fa0e9aaed2304b6f366fecc9cab72c2` | `b18989f02a2eac6ac5003db92dfd7ec1b396b635b8379e2e27245e6b70f121ee` |
| `.6` | 28523720 | 28523720 | `978673603b2d29df0ef9b53447ba0bcd` | `72433426fc9c74f79535843974433a55b0c1b89152c0ff4cda95c69bb8c31ba0` |
| `.7` | 173322256 | 173322256 | `3bc336eab43c1c16350aab4a9a0ee5f4` | `bf0385f55c6c1040951b32acf06062b543263509a10345608e2b07f75f662697` |
| `.8` | 176585414 | 280990034 | `7eff0561c5239786ceaa7eb0fd08bd71` | `303f8d28afdab031e26c3f5f92660db917e24ed779ac7e85df2e33fc042a6966` |

`tools/repair_verified_phase_manifests.py` now pins the seven input
SHA-256s, output SHA-256s, exact reference MD5s, length and expected
field transformations. Default is read-only. Explicit `--apply`
writes **separate output copies**, never edits the originals.
`tools/prepare_legacy_recovery_overlay.py` can now stage **40
verified files**: 33 original-EU-APK assets + seven corrected manifests.
No proprietary bytes were committed.

**Remaining 12 mismatches**: six encrypted novel commands, four encrypted
master catalogs (two have previously documented decode-source provenance
but still mismatch reference MD5), `1/files/font/number.png`, and
`3/files/ui_atlas/home_gacha/gacha_top_move_parts_text.json`.
A partial overlay is still NOT importable or playable. The existing
legacy checksum gate remains strict, PR #1 remains Draft, and no AYN
Thor installation or game import has been performed.


## Remaining twelve: independent rehash and bounded structural analysis (2026-11-12)

Re-examined the owner's **actual** `danmemore_19_payload.json` bytes
against their prior `danmemore_legacy_audit 3(1).json`. This was a
local read-only analysis, **not** a rerun of the Android runtime.

- **12/12 actual MD5s and sizes** still match the owner's recorded
  audit, and **0/12** match the independently pinned current/historical
  reference MD5. The twelve source files sum to 102,400 bytes.
- `1/files/font/number.png`: 7,381 bytes; valid PNG chunk CRC and
  full pixel decode, 109 x 179, 8-bit grayscale+alpha (`LA`).
  The source includes 2023-04-17 ancillary timestamp/EXIF metadata.
  Without original reference pixels/bytes there is **no defensible
  byte-exact image correction**.
- `3/files/ui_atlas/home_gacha/gacha_top_move_parts_text.json`:
  4,267 bytes; valid UTF-8 JSON with CRLF line endings and a
  `root` Node containing 13 Sprite children, distinct tags 1–13
  and local image labels `1.png` through `13.png`.
  Syntax/structure alone does not confirm image availability,
  rendering, version compatibility, or reference byte identity.
- **10 encrypted files**: all sizes are positive multiples of 16
  bytes and every 16-byte block is unique *within its source file*;
  measured byte entropies are ~7.55–7.99 bits/byte.
  None of this authenticates ciphertext, identifies a key/IV, or
  proves successful novel command parsing.
- The two previously sourced master entries
  `lotteryWeightGroup.enc` and `subscription.enc` retain their
  upstream decoded-source SHA-256 provenance, but **still remain
  strict reference-MD5 blockers**.

New `tools/verify_remaining_legacy_candidates.py` checks all
twelve **without writing files**, against the exact historical/current
reference MD5 + size in the owner's audit. It accepts either the
existing owner-supplied 19-file Base64 JSON (for local comparison),
or a *separately acquired* candidate `contents` directory. It labels
each candidate as `REFERENCE_EXACT`,
`SAME_AS_UNVERIFIED_BACKUP`, `OTHER_UNVERIFIED`,
`WRONG_SIZE`, or `ABSENT`. It rejects changed audit structure,
unknown 19-file mismatch sets, path symlinks, duplicate payload
entries, bad Base64 and overlarge inputs. Metadata-only output
never publishes candidate bytes, decrypts archives or changes the
importer's strict gate.

Example (no device operation needed if the already uploaded payload
and audit are on the analyst's local research computer):

```bash
python3 tools/verify_remaining_legacy_candidates.py \
  --audit "/path/to/danmemore_legacy_audit.json" \
  --payload "/path/to/danmemore_19_payload.json"

# Later, if a distinct authentic EU game cache is discovered:
python3 tools/verify_remaining_legacy_candidates.py \
  --audit "/path/to/danmemore_legacy_audit.json" \
  --candidates "/path/to/alternate/contents"
```

**Evidence gate remains unchanged: 7/19 byte-exact corrected, 12/19
still not reference authenticated.** A mirrored copy of the owner's
same preservation collection is not an independent historical capture.
Neither the inspected original bytes nor their decoded data were
committed. Keep PR #1 Draft; **do not merge or claim the ZIP can import**.


## Pinned source discovery: EU 15.1.0 ARM64 bundle (2026-11-12)

Research identified a **different** APKPure release variant from the already
pinned 32-bit-only EU APK:

- Package: \`com.eu.danmemo\`, version \`15.1.0\`, versionCode \`170316722\`.
- Original universal XAPK archive (Dec 28, 2023): **SHA-1**
  \`37894ddb200914278a5f8780e0c6e3da2d750b7c\`, 79.4 MB as listed by
  APKPure. The bundle is described as base \`com.eu.danmemo.apk\` and
  \`config.arm64_v8a\` plus locale/asset splits.
- The separate standard ARMv7 APK released Dec 31, 2023 is **not** the
  native ARM64 target. Its independently previously verified SHA-256 is
  \`36713f18a6e9fec3302384b8d67383b12761f782d73932cb62b31b230053c3b6\`.
- Trusted ELF image SHA-256 remains independently pinned to
  \`e49a8cc7991f8946365a28aebad605ce566b034826dd4b34a982ab18b38303b3\`.

Public listing: https://apkpure.net/danmachi-memoria-freese/com.eu.danmemo/download

The download CDN could not be reached from the current analysis environment.
**No actual binary has been fetched or scanned in this research round.**
The archive's published SHA-1 is a candidate fingerprint, not on its own
sufficient proof of game-binary identity or trustworthiness.

\`tools/verify_pristine_arm64_xapk.py\` adds a bounded, **read-only** source
workflow. It first checks the XAPK fingerprint, then finds exactly one
\`com.eu.danmemo.apk\`, one \`config.arm64_v8a.apk\` and one
\`lib/arm64-v8a/libapp.so\` in the nested split, rejects malformed/duplicated
and oversized contents, and verifies the library's **full SHA-256** against
the already pinned original. Only after both independent checks may
\`--scan\` execute the existing ELF ADR/ADRP+ADD candidate scan.
The source archive or library are never extracted to disk or committed.

Run from a repository checkout **only if that already-authenticated 15.1.0
XAPK is available outside Git**:

\`\`\`bash
python3 tools/verify_pristine_arm64_xapk.py \
  --xapk .work/danmemo-15.1.0-arm64.xapk --scan
\`\`\`

The output would show literal address references, **not** an authenticated
novel-command decryptor, parser, or six-file compatibility proof. No files
among the twelve remaining mismatches are newly accepted. The PR stays Draft.


## First authentic 15.1.0 ARM64 scan and exhaustive direct-xref correction (2026-11-12)

The isolated GitHub Actions runner fetched the EU 15.1.0 ARM64 XAPK
and authenticated its archive SHA-1 and the nested untouched
\`lib/arm64-v8a/libapp.so\` SHA-256 against the independent pinned
\`e49a8cc7991f8946365a28aebad605ce566b034826dd4b34a982ab18b38303b3\`.
**Real original-client source evidence has therefore been obtained**;
the binary was inspected in a temporary runner directory and deleted
without uploading it to the repository.

- [First authenticated source and literal scan](https://github.com/salniper/DanMemoRe/actions/runs/43186364344):
  502 literal occurrences reported. The older analyzer inspected at most
  40 locations for each marker and initially found only **one** direct
  ADR/ADRP+ADD candidate. That count was incomplete and is superseded.
- [Complete bounded single-pass original-ELF scan](https://github.com/salniper/DanMemoRe/actions/runs/43187346224):
  all 502 literal occurrences were indexed, with **four** direct
  ADR/ADRP+ADD instruction/address candidates.
- The rewritten analyzer inspects all bounded marker occurrences
  (limit 8,192 total per marker, failing closed above that limit) and
  scans executable PT_LOAD segments **once**. The bounded output now
  prioritizes references instead of dropping matches past the first
  40 literal locations. New synthetic regression covers a reference
  to the 41st same-name literal.
- [Regression workflow](https://github.com/salniper/DanMemoRe/actions/runs/43187346227)
  covers the optimized scanner and never downloads client bytes.

### Actual native string and reference counts

| Source literal | String occurrences | Direct static reference candidates |
| --- | ---: | ---: |
| \`divide_novel_command_enc\` | 0 | 0 |
| \`novelCommand\` | 1 | 0 |
| \`NovelCommand\` | 499 | 4 |
| \`novel_command\` | 2 | 0 |

The four reported candidates, from the exact original ARM64 binary,
are all direct **ADR** references to \`NovelCommand\` string literals.
ELF file offsets equal virtual addresses for these specific mappings:

| ADR instruction file/virtual offset (decimal) | Literal file/virtual offset (decimal) |
| ---: | ---: |
| 54283152 | 54965593 |
| 54069236 | 54980219 |
| 54086404 | 54997387 |
| 54231964 | 55013931 |

The absence of the literal \`divide_novel_command_enc\` is a valid
negative **literal-search** result, **not** proof the loader is absent.
Paths can be constructed dynamically or reached indirectly. Four ADR
references to strings are **not** a verified decryption routine,
load path, engine invocation, control-flow proof, or validation of six
encrypted novelCommand assets. GOT/indirect references and other ARM64
addressing idioms remain outside scope. Next research: correlate these
four instruction sites with bounded disassembly, nearby functions and
actual file-loading behavior on a disposable original-client test
environment before claiming format compatibility.

**No contents import, native gameplay, or AYN Thor testing occurred.**
There are still **12 original mismatches without reference authentication**;
all strict import checks remain active, and the PR must remain Draft.


## Authenticated four-site ARM64 control-flow neighborhoods (2026-11-12)

[Real original-client bounded context run](https://github.com/salniper/DanMemoRe/actions/runs/43189563885)
used the **same source archive SHA-1 and pristine native SHA-256** as the
preceding evidence. No original source bytes, disassembly or private files
were uploaded or included in Git.

The new \`tools/inspect_native_novel_xref_context.py\` analyzes a bounded
code window around each of the four previously reported ADR target-address
candidates. It emits only instruction *categories and addresses*, never
native code bytes, and requires the already authenticated original via
\`tools/verify_pristine_arm64_xapk.py --scan --context\`.

### Real observed context

| ADR site file offset | Literal context | Nearby direct call/branch/return | Conventional frame marker within 2 KiB |
| ---: | --- | --- | --- |
| 54283152 | embedded inside longer printable string | none within ±192 B | not found |
| 54069236 | embedded inside longer printable string | none within ±192 B | not found |
| 54086404 | embedded inside longer printable string | none within ±192 B | not found |
| 54231964 | embedded inside longer printable string | none within ±192 B | not found |

No first return was found within the bounded forward 2 KiB at these
sites. **These observations are not a comprehensive disassembly and do
not prove that the sites are inert or unrelated.** Frame pointers may
be omitted, external/indirect calls may be far from the scan window, and
the ADR pattern might occur incidentally in executable-region data.

**Correction to earlier wording:** the four results are strictly
\`ADR\` immediate address *matches* for string substrings. They should
**not** be described as four proven code-to-loader references, nor as
an actual novel-command function/call chain. The larger string context
and absence of nearby branch evidence make a false-positive or
reflection/string-metadata explanation plausible. Further evidence
must determine the actual consumers of \`NovelCommand\` or identify
the file loader through other symbol/data-flow sources.

[Full PR policy CI](https://github.com/salniper/DanMemoRe/actions/runs/43189563884):
nine jobs passed, including new synthetic ARM64 context and input-gate
tests. Those synthetic tests do not independently prove gameplay.

The original client's \`divide_novel_command_enc\` literal still has
zero direct string hits, **not** proof that the path or loader is absent.
The six encrypted novel files have not been decrypted or authenticated
to the source reference. **12 legacy mismatches remain blocked**. The
launcher was not installed, imported, or run on the AYN Thor in this pass.


## Confirmed false positives: no executable NovelCommand direct xrefs (2026-11-12)

**Important correction of the preceding 4-site investigation.** A verified
[EU 15.1.0 XAPK binary run](https://github.com/salniper/DanMemoRe/actions/runs/43190879017)
inspected the original ARM64 ELF **section headers** as well as the
larger \`PT_LOAD\` segment flags:

- All **four** ADR arithmetic bit-pattern matches previously reported at
  offsets 54283152, 54069236, 54086404 and 54231964 are in the ELF
  **\`.rodata\`** section, whose \`SHF_EXECINSTR\` flag is **not** set.
- The four literal targets are also in \`.rodata\`. A coarser \`PT_LOAD\`
  \`PF_X\` flag included these data addresses, causing the previous
  scanner to decode arbitrary data bytes as AArch64 instructions.
- The original ELF has 26 section headers; 14,424 ELF symbol entries were
  examined, with **zero symbols named with the selected
  \`NovelCommand\` substrings**. This does not exclude stripped, internal,
  dynamically constructed or other named loader functions.
- These matches are **not code references** and must be excluded from
  callable-function or data-flow assertions. The earlier count of four
  was a false-positive count, not evidence of four real call sites.

\`tools/inspect_elf_novel_xrefs.py\` now consults validated section
headers and counts **only \`SHF_EXECINSTR\` instruction locations** when
section headers are present. It reports rejected noncode arithmetic
patterns separately. A missing/stripped section table retains a
separate \`PF_X_ONLY_UNVERIFIED_NO_SECTION_HEADERS\` status: results from
that fallback cannot substantiate genuine code references.
Synthetic regression explicitly reproduces a \`.rodata\` pattern inside
a \`PF_X\` segment and verifies it is refused.

[Second authenticated original-client scan after the correction](https://github.com/salniper/DanMemoRe/actions/runs/43191351680):
- \`elf_code_gate=SHF_EXECINSTR_FILTERED\`
- \`excluded_data_adr_bit_patterns=4\`
- \`novel_marker_address_candidates_total=0\`
- \`native_context_site_count=0\`
- \`novel_named_symbols=0\`

This is a **negative finding for the narrowly supported direct
ADR/adjacent-ADRP+ADD xref patterns**, not proof that the game has no
story loader. True data references may use GOT indirection, LDR
literals, pointer arrays, string construction or other addressing
sequences, none of which have been fully traced.

[Updated synthetic policy CI](https://github.com/salniper/DanMemoRe/actions/runs/43191351795)
includes section parser, code-gated xrefs, device-source validation,
and existing import security checks. No original binary or decrypted
client content was committed.

**No remaining content asset was newly authenticated.** The original
seven phase repairs remain valid; **12/19 mismatches** still require
reference authentication. This PR remains Draft, with no Android
installation, original game import, gameplay acceptance or merge.


## Original EU 15.1.0 XAPK cross-archive recovery check (2026-11-12)

After the correct original native was cryptographically authenticated, a
read-only scan checked **all 6 nested APK splits** of the exact pinned EU
15.1.0 XAPK for the **12 remaining reference-mismatched assets**, comparing
exact expected **size and MD5**. No APK, original .enc file, novel content
or keys were committed or uploaded.

[Original source scan log](https://github.com/salniper/DanMemoRe/actions/runs/43195596616)
reports \`original_xapk_nested_apks=6\` and
\`reference_exact_asset_targets_in_original_xapk=0\`.

| Expected blocked asset group | Same-basename files found among APK members | Reference-exact size/MD5 |
| --- | ---: | ---: |
| Four \`1/master/divide_enc/*.enc\` files | Four, one for each basename | **0** — all four have a DIFFERENT byte size |
| Six \`novelCommand*.enc\` files | None | 0 |
| \`1/files/font/number.png\` | None | 0 |
| \`3/files/ui_atlas/home_gacha/gacha_top_move_parts_text.json\` | None | 0 |

This result is genuine negative evidence for **visible ZIP members of the
authenticated XAPK's nested APKs**. It is not proof that matching source
bytes do not exist elsewhere: remotely downloaded final content, OBB data,
differently named encoded archives or independent preserved cache snapshots
were not searched. The four installer-bundled master files must **not**
be substituted for later content-manifest versions solely by name.

New \`tools/audit_original_xapk_asset_candidates.py\` pins the twelve
reference MD5s/sizes and checks candidates without exporting bytes.
Its CLI requires the original XAPK and embedded ARM64 library SHA checks
to succeed first, then opens bounded nested APK members. It refuses
malformed archives, excessive duplicate names and oversize members.
[Synthetic audit regression job](https://github.com/salniper/DanMemoRe/actions/runs/43195596605)
passed alongside the other policy checks.

**Impact:** The source XAPK does not directly repair any of the twelve
remaining mismatches. The seven already exact phase-manifest repairs and
33 separately verified Phase-1 APK assets are unchanged. Next recovery
focus should be **independent complete 15.1.0 EU content caches** or
native master/story compatibility analysis on the owner's actual six
ciphertexts, without weakening the import MD5 gate.

**Do not merge** PR #1; no original archive/AYN Thor mutation, real legacy
import, or native story/battle/gacha acceptance occurred.
