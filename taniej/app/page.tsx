"use client";

import { useState, useEffect } from "react";
import ShoppingList from "@/components/ShoppingList";
import StoreComparison from "@/components/StoreComparison";
import RecipeInput from "@/components/RecipeInput";
import { Item } from "@/types";

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
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <main className="min-h-screen bg-[#f5f5f0] font-sans">
      <div className="max-w-md mx-auto px-4 pt-10 pb-16">

        {/* Header */}
        <div className="mb-8">
          <div className="flex items-end justify-between">
            <div>
              <h1 className="text-4xl font-black text-green-500 tracking-tight leading-none">
                taniej<span className="text-green-400">.</span>
              </h1>
              <p className="text-sm text-gray-400 mt-1.5">
                Znajdź najtańszy koszyk zakupów
              </p>
            </div>
            {items.length > 0 && (
              <button
                onClick={shareList}
                className="text-xs text-gray-400 hover:text-green-500 transition-colors flex items-center gap-1 pb-1"
              >
                {copied ? "✓ Skopiowano!" : "🔗 Udostępnij"}
              </button>
            )}
          </div>

          {/* Feature pills */}
          <div className="flex gap-2 mt-4 flex-wrap">
            {["7 sklepów", "AI z przepisów", "Porównaj koszyk"].map((f) => (
              <span
                key={f}
                className="text-xs bg-white text-gray-500 px-3 py-1 rounded-full shadow-sm border border-gray-100"
              >
                {f}
              </span>
            ))}
          </div>
        </div>

        <RecipeInput items={items} setItems={setItems} />
        <ShoppingList items={items} setItems={setItems} onSearch={() => setSearched(true)} />

        {searched && items.length > 0 && <StoreComparison items={items} />}

        {/* Footer */}
        <p className="text-center text-xs text-gray-300 mt-10">
          taniej. · porównywarka cen w polskich sklepach
        </p>
      </div>
    </main>
  );
}
