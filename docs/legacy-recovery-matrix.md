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
