# DanMemoRe Offline Preview — independently installable APK

This is **not a repaired original Memoria Freese client**. It is a standalone
Android app specifically meant to get an immediate install/interaction test
on AYN Thor while the source-game recovery work remains blocked.

## What you can really do

- Start the Android app fully offline, without a game archive or Node runtime.
- Navigate the Chinese (Traditional) home/story/battle/gacha/save screens.
- Read four short **original placeholder story** scenes.
- Play a simple one-hero/one-enemy turn-based **placeholder battle**.
- Simulate 1x/10x gacha with **placeholder original-character names** and
  self-adjustable, fake test currency. No payment or network request.
- Close/reopen and verify story progress, battle state, collection and currency
  remain saved locally; reset the isolated preview save if desired.

## Not yet supported

The actual **Memoria Freese** story playback, source combat logic, original
character art/music/voice, historical gacha rates, import of the preserved
archive, and compatibility with the original app's save data are **not** in
this APK. None of the outstanding reference-MD5 checks are bypassed. This
APK uses package ID `dev.danmemore.preview` to avoid overwriting the original
game or the recovery launcher.

The APK requires Android 8.0+ (including AYN Thor) and requests **no Internet
permission** and no storage permission. It contains no copied game assets.

## Build / download

A GitHub Actions pull-request job named **DanMemoRe Offline Preview APK**
compiles the separate Gradle project, verifies APK signing and offline
permissions, and attaches the installable file as the
`DanMemoRe-Offline-Preview-APK` workflow artifact. Download the artifact ZIP,
extract `DanMemoRe-Offline-Preview-0.1.apk`, copy it to AYN Thor and open it
using Android's package installer. Allow app installs from the file manager
if Android asks; do not uninstall the original game.

For local builds with Android SDK 35 and Java 17:

```sh
gradle -p android/danmemore-preview :app:assembleDebug
```

The output is
`android/danmemore-preview/app/build/outputs/apk/debug/app-debug.apk`.
This isolated test project does **not** depend on the main launcher,
`libnode.so`, proprietary original APKs or contents ZIPs.

## Acceptance checklist

1. App launches with airplane mode on and shows the offline-preview warning.
2. Story progress survives app restart.
3. Battle attacks, defense, healing, victory and defeat work.
4. Gacha draws debit test currency, reveal a result and save the collection.
5. Edit fake currency; close and reopen; edited balance persists.
6. Reset the test save; original DanMemoRe client remains unaffected.

**Do not mark full-game acceptance passed based on this preview.**
