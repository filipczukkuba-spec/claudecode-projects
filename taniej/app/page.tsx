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
      <div className="max-w-md mx-auto px-4 py-8">
        <div className="flex items-end justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-green-600 tracking-tight">taniej.</h1>
            <p className="text-sm text-gray-500 mt-1">Gdzie kupisz taniej? Sprawdź.</p>
          </div>
          {items.length > 0 && (
            <button
              onClick={shareList}
              className="text-xs text-gray-400 hover:text-green-600 transition-colors flex items-center gap-1 pb-1"
            >
              {copied ? "✓ Skopiowano!" : "🔗 Udostępnij listę"}
            </button>
          )}
        </div>

        <RecipeInput items={items} setItems={setItems} />
        <ShoppingList items={items} setItems={setItems} onSearch={() => setSearched(true)} />

        {searched && items.length > 0 && <StoreComparison items={items} />}
      </div>
    </main>
  );
}
