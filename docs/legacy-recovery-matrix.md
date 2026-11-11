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
