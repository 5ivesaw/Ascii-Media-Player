# Android wrapper

This directory builds the browser player as a native Android APK. The app uses an Android WebView and packages the current `docs/` directory into the APK, so local audio selection and ASCII visualization work without a network connection.

The release workflow builds the APK automatically. A stable signing key is supplied through repository secrets when `scripts/release-termux.sh` is used. If those secrets are absent, Gradle falls back to a debug signing key and the resulting APK remains installable but should not be used as a long-term update channel.

Local build requirements:

```bash
gradle -p android :app:assembleRelease
```
