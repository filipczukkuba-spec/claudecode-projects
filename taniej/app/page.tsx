"use client";

import { useState, useEffect } from "react";
import ShoppingList from "@/components/ShoppingList";
import StoreComparison from "@/components/StoreComparison";
import RecipeInput from "@/components/RecipeInput";
import ProductLookup from "@/components/ProductLookup";
import { Item } from "@/types";

const STORES = [
  { name: "Biedronka", color: "bg-red-500" },
  { name: "Lidl",      color: "bg-blue-500" },
  { name: "Kaufland",  color: "bg-orange-500" },
  { name: "Aldi",      color: "bg-indigo-500" },
  { name: "Netto",     color: "bg-yellow-400" },
  { name: "Auchan",    color: "bg-purple-500" },
  { name: "Carrefour", color: "bg-sky-500" },
];

export default function Home() {
  const [items, setItems] = useState<Item[]>([]);
  const [searched, setSearched] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const encoded = params.get("l");
    if (!encoded) return;
    try {
      const decoded = JSON.parse(atob(encoded));
      if (Array.isArray(decoded) && decoded.length > 0) {
        setItems(decoded);
        setSearched(true);
      }
    } catch {}
  }, []);

  function shareList() {
    const encoded = btoa(JSON.stringify(items));
    const url = `${window.location.origin}/?l=${encoded}`;
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    });
  }

  function handleSearch() {
    setSearched(true);
    setTimeout(() => {
      document.getElementById("wyniki")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 100);
  }

  return (
    <main className="min-h-screen bg-[#f0f0eb] font-sans">
      <div className="max-w-md mx-auto px-4 pt-6 pb-36">

        {/* ── App Header ── */}
        <div className="relative overflow-hidden bg-gradient-to-br from-green-500 via-green-600 to-emerald-700 rounded-3xl p-6 mb-4 shadow-lg shadow-green-500/25">
          <div className="absolute -top-5 -right-5 w-28 h-28 rounded-full bg-white/10 pointer-events-none" />
          <div className="absolute -bottom-8 -left-3 w-24 h-24 rounded-full bg-white/10 pointer-events-none" />
          <div className="absolute top-1/2 right-14 w-8 h-8 rounded-full bg-white/10 pointer-events-none" />

          <div className="relative flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h1 className="text-4xl font-black text-white tracking-tight leading-none">taniejkupuj</h1>
              <p className="text-green-100 text-sm mt-1.5 font-medium">Najtańszy koszyk zakupów w Polsce</p>
              <div className="flex flex-wrap gap-1.5 mt-3">
                {[
                  { v: "7", l: "sklepów" },
                  { v: "400+", l: "produktów" },
                  { v: "0 zł", l: "za darmo" },
                ].map((s) => (
                  <div key={s.l} className="bg-white/20 rounded-full px-2.5 py-1 flex items-center gap-1">
                    <span className="text-white font-bold text-xs">{s.v}</span>
                    <span className="text-green-100 text-xs">{s.l}</span>
                  </div>
                ))}
              </div>
            </div>
            {items.length > 0 && (
              <button
                onClick={shareList}
                className="bg-white/20 hover:bg-white/30 active:scale-95 transition-all text-white w-10 h-10 rounded-2xl flex items-center justify-center text-base shrink-0 mt-0.5"
                title="Udostępnij listę"
              >
                {copied ? "✓" : "🔗"}
              </button>
            )}
          </div>
        </div>

        {/* ── Store pills ── */}
        <div className="flex flex-wrap gap-1.5 mb-4 px-0.5">
          {STORES.map((s) => (
            <div key={s.name} className="flex items-center gap-1.5 bg-white rounded-full px-2.5 py-1.5 shadow-sm border border-white/80">
              <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${s.color}`} />
              <span className="text-xs text-gray-600 font-medium leading-none">{s.name}</span>
            </div>
          ))}
        </div>

        {/* ── Product lookup ── */}
        <ProductLookup />

        {/* ── Recipe input ── */}
        <RecipeInput items={items} setItems={setItems} />

        {/* ── Shopping list ── */}
        <ShoppingList items={items} setItems={setItems} onSearch={handleSearch} />

        {/* ── Results ── */}
        {searched && items.length > 0 && (
          <div id="wyniki">
            <StoreComparison items={items} />
          </div>
        )}

        <p className="text-center text-xs text-gray-300 mt-10 pb-2">
          taniejkupuj · porównywarka cen w polskich sklepach
        </p>
      </div>

      {/* ── Floating Compare CTA ── */}
      {items.length > 0 && !searched && (
        <div className="fixed bottom-0 inset-x-0 pointer-events-none z-50">
          <div className="max-w-md mx-auto px-4 pointer-events-auto"
               style={{ paddingBottom: `calc(1.5rem + env(safe-area-inset-bottom))` }}>
            <div className="h-8 bg-gradient-to-t from-[#f0f0eb] to-transparent -mb-1" />
            <button
              onClick={handleSearch}
              className="w-full bg-green-500 hover:bg-green-600 active:bg-green-700 active:scale-[0.98] text-white font-bold rounded-2xl py-4 text-base transition-all shadow-2xl shadow-green-500/40"
            >
              Porównaj ceny w {STORES.length} sklepach →
            </button>
          </div>
        </div>
      )}
    </main>
  );
}
