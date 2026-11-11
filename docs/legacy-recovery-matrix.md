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
