"use client";

import { useEffect } from "react";

// Registers the service worker. Required for PWA installability — without a
// registered SW with a fetch handler, Chrome never fires beforeinstallprompt,
// so the install banner can't appear.
export default function ServiceWorkerRegister() {
  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;
    const onLoad = () => {
      navigator.serviceWorker.register("/sw.js").catch(() => {
        // best-effort — app works fine without it
      });
    };
    if (document.readyState === "complete") onLoad();
    else window.addEventListener("load", onLoad);
    return () => window.removeEventListener("load", onLoad);
  }, []);

  return null;
}
