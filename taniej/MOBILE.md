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

## Building Android (tooling NOT installed on the current machine)

This machine has no JDK and no Android SDK (`java` not on PATH, `ANDROID_HOME`
unset), so the APK/AAB can't be built here. Install once:

- **JDK 17** (Temurin/Adoptium) → set `JAVA_HOME`
- **Android Studio** + Android SDK → set `ANDROID_HOME` (e.g.
  `%LOCALAPPDATA%\Android\Sdk`)

Then:

```bash
npx cap sync android
npx cap open android                         # open in Android Studio, or:
cd android && ./gradlew assembleDebug        # -> app/build/outputs/apk/debug/app-debug.apk
```

### Play Store release (signed AAB)

1. Create an upload keystore once (back it up — losing it blocks future updates):
   ```bash
   keytool -genkey -v -keystore upload-keystore.jks -keyalg RSA -keysize 2048 \
     -validity 9125 -alias upload
   ```
2. Reference it from `android/app/build.gradle` via a `key.properties` file.
   **Never commit the keystore or passwords** (add both to `.gitignore`).
3. Bump `versionCode` (and usually `versionName`) for every upload.
4. Build the bundle:
   ```bash
   cd android && ./gradlew bundleRelease      # -> app/build/outputs/bundle/release/app-release.aab
   ```
5. Upload the `.aab` at https://play.google.com/console (one-time $25 dev
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
- [ ] Build APK/AAB — blocked: JDK 17 + Android SDK not installed here
- [ ] Upload keystore + signing config
- [ ] Play Store listing + first upload
- [ ] iOS archive (needs macOS)
