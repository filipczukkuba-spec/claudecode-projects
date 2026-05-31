# taniejkupuj — mobile app (Capacitor)

The iOS/Android apps are thin Capacitor shells that load the live site
(`https://taniejkupuj.pl`) in a native WebView (see `capacitor.config.ts`,
`server.url`). Every web deploy is reflected in the app immediately — there is
**no separate web build to ship**. The bundled `mobile-shell/index.html` is only
the offline/loading fallback shown before the remote page loads.

- App ID / package: `pl.taniejkupuj.app`
- App name: `taniejkupuj`
- Version: `versionCode 1`, `versionName "1.0"` (in `android/app/build.gradle`)
- Native projects: `android/`, `ios/` (committed; build outputs are gitignored)

## Regenerating icons + splash

Brand art lives in `public/icon.svg`. The pipeline turns it into the source
images @capacitor/assets needs, then generates every density for both platforms:

```bash
node scripts/gen-mobile-assets.mjs          # icon.svg -> assets/{icon,icon-foreground,icon-background,splash,splash-dark}.png
npx @capacitor/assets generate --android --ios
npx cap sync
```

`assets/` holds the 1024px (splash 2732px) sources; the generated launcher
icons / splashes land under `android/app/src/main/res` and the iOS asset
catalog. The adaptive icon = green background (`icon-background.png`) + the
cart/arrow art in the safe zone (`icon-foreground.png`).

## After editing config or mobile-shell

```bash
npx cap sync        # copies web assets + config into the native projects
```

## Building Android

The toolchain is installed and both builds are verified working.

- **JDK 21** — `C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot`
  (`JAVA_HOME` set at user scope). ⚠️ Capacitor 8 requires **JDK 21** — JDK 17
  fails with `invalid source release: 21`.
- **Android SDK** — `C:\Users\filip\Android\Sdk` (`ANDROID_HOME` /
  `ANDROID_SDK_ROOT` set), with `platform-tools`, **`platforms;android-36`**
  (compileSdk 36), `build-tools;35.0.0`.

Debug APK (verified → ~4.4 MB `app-debug.apk`):

```bash
npx cap sync android
cd android && ./gradlew assembleDebug        # -> app/build/outputs/apk/debug/app-debug.apk
```

If a fresh shell doesn't see `java`, set it for the session (PowerShell):

```powershell
$env:JAVA_HOME="C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot"
$env:Path="$env:JAVA_HOME\bin;$env:Path"
$env:ANDROID_HOME="C:\Users\filip\Android\Sdk"
```

### Play Store release (signed AAB)

The upload keystore + signing are already set up. `build.gradle` reads a
gitignored `android/app/key.properties` (opt-in: no file → unsigned release,
so clones/CI don't break):

- Keystore: `android/app/upload-keystore.jks`, alias `upload`
- `android/app/key.properties` holds the passwords
- **Both are gitignored — never commit them.** ⚠️ Back up the keystore +
  password off-machine; losing them means you can never ship an update to the
  same Play listing. (Password is recorded in project memory.)

Build the signed bundle (verified → ~3.2 MB signed `app-release.aab`,
`META-INF/UPLOAD.RSA`):

```bash
cd android && ./gradlew bundleRelease        # -> app/build/outputs/bundle/release/app-release.aab
```

Then:
1. Bump `versionCode` (and usually `versionName`) in `android/app/build.gradle`
   for every new upload.
2. Upload the `.aab` at https://play.google.com/console (one-time $25 dev
   account). Prepare: PL store listing, screenshots, privacy-policy URL,
   data-safety form, content rating.

## Building iOS

Requires macOS + Xcode (not available here):

```bash
npx cap open ios     # Xcode -> set Team/signing -> Product > Archive -> upload to App Store Connect
```

## Status

- [x] Capacitor Android + iOS projects scaffolded (`cap add`)
- [x] WebView points at live `taniejkupuj.pl`; offline fallback shell
- [x] Branded launcher icons + adaptive icon + splash (green / cart+arrow)
- [x] JDK 21 + Android SDK (android-36) installed; **debug APK + signed AAB build**
- [x] Upload keystore + opt-in signing config (gitignored)
- [ ] Play Store listing + first upload (needs $25 dev account + listing assets)
- [ ] iOS archive (needs macOS + Xcode)
