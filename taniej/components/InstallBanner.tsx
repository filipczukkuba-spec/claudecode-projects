"use client";

import { useState, useEffect } from "react";

export default function InstallBanner() {
  const [prompt, setPrompt] = useState<any>(null);
  const [show, setShow] = useState(false);
  const [installed, setInstalled] = useState(false);

  useEffect(() => {
    // Don't show if already installed (standalone mode)
    if (window.matchMedia("(display-mode: standalone)").matches) return;
    // Don't show if dismissed before
    if (sessionStorage.getItem("install-dismissed")) return;

    const handler = (e: Event) => {
      e.preventDefault();
      setPrompt(e);
      // Small delay so it doesn't pop up immediately
      setTimeout(() => setShow(true), 3000);
    };

    window.addEventListener("beforeinstallprompt", handler as EventListener);
    window.addEventListener("appinstalled", () => setInstalled(true));

    return () => window.removeEventListener("beforeinstallprompt", handler as EventListener);
  }, []);

  function dismiss() {
    sessionStorage.setItem("install-dismissed", "1");
    setShow(false);
  }

  async function install() {
    if (!prompt) return;
    prompt.prompt();
    const { outcome } = await prompt.userChoice;
    if (outcome === "accepted") setInstalled(true);
    setShow(false);
  }

  if (!show || installed) return null;

  return (
    <div className="fixed top-4 inset-x-4 z-50 max-w-md mx-auto animate-slide-up">
      <div className="bg-gray-900 text-white rounded-2xl p-4 shadow-2xl flex items-center gap-3">
        <div className="w-10 h-10 bg-green-500 rounded-xl flex items-center justify-center text-white font-black text-lg shrink-0">
          t
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold leading-tight">Dodaj do ekranu głównego</p>
          <p className="text-xs text-gray-400 mt-0.5">Szybszy dostęp, działa jak aplikacja</p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={install}
            className="bg-green-500 hover:bg-green-600 active:bg-green-700 text-white text-xs font-bold px-3 py-2 rounded-xl transition-colors"
          >
            Dodaj
          </button>
          <button
            onClick={dismiss}
            className="text-gray-500 hover:text-gray-300 text-lg leading-none px-1"
          >
            ×
          </button>
        </div>
      </div>
    </div>
  );
}
