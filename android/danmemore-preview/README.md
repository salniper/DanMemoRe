# DanMemoRe Offline Preview 0.2 — AYN Thor landscape test

**Independent offline Android interaction prototype — NOT the original repaired Memoria Freese game.**

## Version 0.2 improvements

- Large landscape screens (screenWidthDp ≥ 600) use a persistent left-side navigation rail and a right-hand scrollable play area.
- Smaller/portrait displays use a compact horizontal tab strip.
- New original, procedurally drawn fantasy portal art; no imported proprietary game assets.
- Controller mappings: L1/R1 change tabs, A confirms the focused or default action, B goes back to Home. Actual AYN Thor button mapping requires device testing.
- Story progression, health bars and battle log, gacha result presentation, persistent simulated card collection and customizable virtual currency (0 to 100 million).
- Local-only operation. No INTERNET or file-storage permissions.

## Important: the old 0.1 installation stays intact

The 0.2 package ID is **dev.danmemore.preview.v2**. The installed 0.1
package ID is **dev.danmemore.preview**. A separate ID avoids debug-signature
conflicts between different CI builds and means both apps can be installed
side-by-side.

The old 0.1 local save remains in the 0.1 app, but **does not automatically
migrate to the 0.2 app**. The new preview starts with its own test save.
Do not delete the old installation if you want to retain its progress.

## Install on AYN Thor

1. Download the verified DanMemoRe-Offline-Preview-0.2.apk from the chat
   or GitHub Actions artifact.
2. Open APK using Android Package Installer; grant only the file manager
   permission to install unknown apps if Android prompts.
3. Launch the separately titled DanMemoRe 離線測試 0.2 app.
4. Test the new landscape rail, story, battle, gacha, and Save pages.

## Build

Requires Java 17, Android SDK 35 and Gradle 8.14.3.
Build with: gradle -p android/danmemore-preview :app:assembleDebug

Build output: android/danmemore-preview/app/build/outputs/apk/debug/app-debug.apk

The GitHub Actions DanMemoRe Offline Preview APK workflow verifies package
name, launchable activity, debug signing and no INTERNET permission, then
publishes the DanMemoRe-Offline-Preview-0.2-APK artifact.

## Device acceptance checklist

- [ ] 0.2 installs side by side with 0.1 without removing old save.
- [ ] Landscape: rail left, play screen right, buttons reachable.
- [ ] Portrait/resized screen: tabs and content remain usable.
- [ ] Controller L1/R1/A/B and DPAD work on actual AYN Thor.
- [ ] Story progress persists, one-time reward is not duplicated.
- [ ] Battle attack/guard/heal/victory/reset changes bars and saved wins.
- [ ] Gacha 1× and 10× results, character inventory and currency persist.
- [ ] Custom currency input is validated and saved.
- [ ] Resetting 0.2 does not touch 0.1 or the original game.

The restored source story, actual battles, original cast, audio, gacha rates
and game archive imports are **not implemented** in this preview.
**Device acceptance remains unverified until manually tested on AYN Thor.**
