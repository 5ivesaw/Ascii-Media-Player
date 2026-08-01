# ASCII Media Player v2.2.1 — FiveSaw Edition

This release fixes the Android build and establishes the original FiveSaw/FiveCut product language across the website, PWA, Android shell, artwork, and release assets.

## Android fixes

- Uses `WebSettings.setSafeBrowsingEnabled(true)` on API 26 and newer.
- Renames the private immersive helper so it no longer conflicts with `Activity.setImmersive(boolean)`.
- Uses the configured Android SDK action with API 36 and Build Tools 36.0.0.
- Keeps the existing persistent release-signing key, allowing future APK updates over v2.2.1.

## FiveSaw visual system

- Black, signal-red, and warm-white palette.
- Hard cuts, diagonal corners, technical index labels, and dense industrial typography.
- Rebuilt logo, wordmark, social card, app icons, Android launcher icons, and error page.
- Four player treatments: FiveSaw Red, White Cut, Night Signal, and Terminal.

## Distribution

Tagging `v2.2.1` builds Windows x64, Linux x64, Linux ARM64, Android APK, macOS Intel, and macOS Apple Silicon artifacts and publishes them to one GitHub Release with checksums.
