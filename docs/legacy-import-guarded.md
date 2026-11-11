# Guarded legacy import (2024 preservation snapshot)

> **Status: experimental source-only change. Not a compatible, tested APK.**
> The original importer remains the default. Do not merge until the blocked
> assets are recovered and Android builds plus device tests pass.

## Why this change exists

The preserved contents on the AYN Thor do not match the one canonical ZIP
permitted by DanMemoRe Alpha 10 (`STRICT_CONTENT_MANIFEST=true`). The existing
importer checks the whole ZIP's length and SHA-256 and performs CRC32 during
extraction. It calculates file MD5 values but does not compare all extracted
files against the bundled reference manifest before resolving manifests.

A separately selected **Legacy Import (2024 snapshot)** action now:
1. Keeps the normal ZIP import path and exact archive checksum unchanged.
2. Permits a different top-level ZIP SHA-256 **only after user opts in**.
3. Pins all eight original `project.manifest` files by SHA-256 and their
   expected version strings. A re-packed archive does not have to preserve
   the original ZIP checksum, but must contain the pinned catalogs.
4. Checks every referenced, non-overlaid source file against the current
   or pinned historical `size + MD5` pair. Any unrecognized bytes stop import.
5. Accepts missing phase-1 source files only when their relative paths are on
   an **exact 33-path allowlist**. A different phase-1 file cannot disappear
   merely because the count is below 33.
6. Accepts missing phase-3 gacha backgrounds only when an identically named
   fallback is actually bundled. This currently covers 1,544 image filenames.
7. Leaves all other missing referenced source assets disallowed, uses existing
   ZIP entry/path/size/CRC guards, staging cache, offline overlays, atomic
   activation and rollback.

The check occurs **before** patching assets, writing the active marker or
switching active content. The original ZIP is not modified.

## Audit baseline (one preserved backup)

Source: local `danmemore_legacy_audit.json` dated 2026-11-10.
Do not commit private device contents or the 12+ GB game archive.

| Classification | Count | Meaning |
| --- | ---: | --- |
| Current/reference MD5 verified | 86,828 | Same source bytes as Alpha 10 |
| Historical manifest verified | 1 | `1/manifests/voice_episode.manifest` |
| Missing from historic catalog | 1,544 | Gacha background images, project has fallbacks |
| Missing with historic catalog entry | 33 | Opening title, BGM, UI/atlas files |
| Present but **neither** catalog's MD5 | 19 | Must not be silently accepted |

**Current outcome: the user's backup is expected to FAIL the guarded legacy
verification at the 19 unverified files.** It must remain blocked until each
file is recovered or independently validated against an authoritative source.

The 33 reviewed missing files also include boot-critical candidates:
`1/files/ui/title/bg_1.jpg`, `1/files/sound/bgm/bgm_main_theme.ogg`,
`1/files/lwf/uiLwf/home/lwf_title_logo/lwf_title_logo.lwf` and others.
An allowlist records *known missing* paths, not proof the game can boot.
Treat these as unresolved for device acceptance even if a future import passes.

A TW game installation that still shows title/music might contain useful
recovery candidates, but TW and EU content are not assumed byte-identical.
Compare candidate hashes before restoring any game file; never copy blindly.

## Scope and non-goals

- No attempt to disable CRC, bypass Android app isolation, or overwrite saves.
- No original game archive or APK in Git.
- No claim of completeness, legal entitlement, or successful offline play.
- No automatic mutation of the AYN Thor's extracted backup.
- No changes to the original import UI text or original ZIP validation.

## Source-level regression test (2026-11-11)

The source-only importer now delegates fingerprint classification and
missing-path policy to `LegacyImportPolicy.kt`, which has no Android runtime
dependency. The companion `tools/test_legacy_import_policy.kt` covers:

- Exact expected bytes, approved historic bytes, unknown bytes and wrong sizes.
- Unknown or non-historic Phase 1 missing paths.
- The 33-entry allowlist cardinality and path safety.
- An approved title background and BGM, while unrelated BGM is rejected.
- Phase 3 missing gacha images only when a bundled filename is present.
- No missing-asset exceptions for Phases 2 and 4.

A local Kotlin 1.9 JVM compiler run of an equivalent pure-policy copy passed 19
assertions; this is **not an Android build, emulator pass, or a CI run of the
repository**. Re-run the checked-in test from the repository checkout with:

```bash
kotlinc android/danmemore-launcher/app/src/main/kotlin/dev/danmemore/launcher/LegacyImportPolicy.kt \
  tools/test_legacy_import_policy.kt -include-runtime -d /tmp/danmemore-legacy-policy-test.jar
java -jar /tmp/danmemore-legacy-policy-test.jar
```

Android build still requires an externally supplied Node Mobile distribution:
`DANMEMORE_LIBNODE_DIR/bin/arm64-v8a/libnode.so` and compatible
`DANMEMORE_LIBNODE_DIR/include/node` headers. Do not assume arbitrary
Node Mobile releases are ABI-compatible with the bundled JNI bridge;
verify the required Node/V8 symbols and Android 16 KB page alignment.

## Acceptance before changing from draft PR

- [ ] Android build with Java 17, Android SDK 36, NDK 27.2.12479018,
      Gradle 8.14.3 and externally supplied Node Mobile `libnode.so`.
- [ ] Test: original verified 15.1.0 ZIP still accepts in the normal path.
- [ ] Test: random/altered ZIP fails normal exact SHA check.
- [ ] Test: historical ZIP with mismatched project.manifest SHA fails closed.
- [ ] Test: historical ZIP with a tampered file is rejected, and active data
      is preserved.
- [ ] Test: removing a 34th or unexpected Phase 1 file is rejected.
- [ ] Test: missing Phase 3 gacha file is accepted only with bundled fallback.
- [ ] Resolve or account for the 19 unverified MD5 files and 33 missing source
      files before asserting it is playable.
- [ ] Verify private-storage free space; current importer can require about
      2× ZIP size + 2 GiB. AYN Thor should not import at low free space.
- [ ] Emulator smoke tests, then AYN Thor test using disposable profiles.
- [ ] Manual code review and CI before considering merge.

## Implementation references

- `android/danmemore-launcher/app/src/main/kotlin/dev/danmemore/launcher/ContentImportService.kt`
- `android/danmemore-launcher/app/src/main/kotlin/dev/danmemore/launcher/MainActivity.kt`
- `android/danmemore-launcher/app/build.gradle.kts`
