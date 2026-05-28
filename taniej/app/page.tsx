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
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <main className="min-h-screen bg-[#f0f0eb] font-sans">
      <div className="max-w-md mx-auto px-4 pt-8 pb-16">

        {/* Hero */}
        <div className="relative overflow-hidden bg-gradient-to-br from-green-500 via-green-600 to-emerald-700 text-white rounded-3xl mb-5 p-7 shadow-lg">
          <div className="absolute -top-6 -right-6 w-36 h-36 rounded-full bg-white/10" />
          <div className="absolute -bottom-8 -left-4 w-28 h-28 rounded-full bg-white/10" />
          <div className="absolute top-1/2 right-12 w-10 h-10 rounded-full bg-white/10" />

          <div className="relative">
            <div className="flex items-start justify-between">
              <div>
                <h1 className="text-5xl font-black tracking-tight leading-none">taniejkupuj</h1>
                <p className="text-green-100 text-base font-medium mt-2">
                  Najtańszy koszyk zakupów w Polsce
                </p>
                <p className="text-green-200 text-xs mt-1">
                  Porównujemy 7 sklepów jednocześnie
                </p>
              </div>
              {items.length > 0 && (
                <button
                  onClick={shareList}
                  className="bg-white/20 hover:bg-white/30 transition-colors text-white text-xs px-3 py-2 rounded-xl font-medium"
                >
                  {copied ? "✓" : "🔗"}
                </button>
              )}
            </div>

            <div className="flex gap-3 mt-6">
              {[
                { value: "7", label: "sklepów" },
                { value: "140+", label: "produktów" },
                { value: "0 zł", label: "za darmo" },
              ].map((s) => (
                <div key={s.label} className="bg-white/20 rounded-2xl px-4 py-2.5 text-center flex-1">
                  <div className="text-xl font-black leading-none">{s.value}</div>
                  <div className="text-green-100 text-xs mt-0.5">{s.label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* How it works */}
        <div className="bg-white rounded-2xl shadow-sm p-5 mb-4">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-4">
            Jak to działa
          </p>
          <div className="grid grid-cols-3 gap-2">
            {[
              { icon: "📝", title: "Dodaj produkty", desc: "Wpisz lub wklej przepis" },
              { icon: "🔍", title: "Porównaj", desc: "Sprawdzamy 7 sklepów" },
              { icon: "🏆", title: "Oszczędzaj", desc: "Idź do najtańszego" },
            ].map((s, i) => (
              <div key={i} className="text-center bg-gray-50 rounded-2xl p-3">
                <div className="text-2xl mb-1.5">{s.icon}</div>
                <div className="text-xs font-bold text-gray-700 leading-tight">{s.title}</div>
                <div className="text-xs text-gray-400 mt-0.5 leading-tight">{s.desc}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Store strip */}
        <div className="bg-white rounded-2xl shadow-sm p-5 mb-5">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">
            Porównujemy
          </p>
          <div className="flex flex-wrap gap-2">
            {STORES.map((store) => (
              <div key={store.name} className="flex items-center gap-1.5 bg-gray-50 rounded-full px-3 py-1.5 border border-gray-100">
                <div className={`w-2 h-2 rounded-full ${store.color} shrink-0`} />
                <span className="text-xs text-gray-600 font-medium">{store.name}</span>
              </div>
            ))}
          </div>
        </div>

        {/* App */}
        <ProductLookup />
        <RecipeInput items={items} setItems={setItems} />
        <ShoppingList items={items} setItems={setItems} onSearch={() => setSearched(true)} />
        {searched && items.length > 0 && <StoreComparison items={items} />}

        <p className="text-center text-xs text-gray-300 mt-10">
          taniejkupuj · porównywarka cen w polskich sklepach
        </p>
      </div>
    </main>
  );
}
