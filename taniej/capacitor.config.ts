import type { CapacitorConfig } from "@capacitor/cli";

// The native iOS/Android shells load the live site (taniejkupuj.pl) in a
// Capacitor WebView, so app-store builds always reflect the latest deploy with
// no separate web build. `webDir` (mobile-shell/) is only the offline fallback
// shown before the remote page loads.
const config: CapacitorConfig = {
  appId: "pl.taniejkupuj.app",
  appName: "taniejkupuj",
  webDir: "mobile-shell",
  server: {
    url: "https://taniejkupuj.pl",
    cleartext: false,
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 1200,
      backgroundColor: "#16a34a",
      showSpinner: false,
    },
    StatusBar: {
      style: "LIGHT",
      backgroundColor: "#16a34a",
    },
  },
};

export default config;
