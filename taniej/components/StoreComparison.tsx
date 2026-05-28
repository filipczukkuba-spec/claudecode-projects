"use client";

import { useEffect, useState } from "react";
import { Item, StoreResult } from "@/types";

interface Props {
  items: Item[];
}

// Mock price data — will be replaced with real scraper data later
function getMockResults(items: Item[]): StoreResult[] {
  const stores = [
    { name: "Biedronka", logo: "🛒", color: "bg-red-50 border-red-200" },
    { name: "Lidl", logo: "🛍️", color: "bg-yellow-50 border-yellow-200" },
    { name: "Kaufland", logo: "🏪", color: "bg-red-50 border-red-100" },
  ];

  return stores.map((store) => {
    const prices = items.map((item) => ({
      item: item.name,
      price: parseFloat((Math.random() * 8 + 1.5).toFixed(2)),
    }));
    const total = prices.reduce((sum, p) => sum + (p.price ?? 0), 0);
    return { ...store, prices, total: parseFloat(total.toFixed(2)), available: items.length };
  });
}

export default function StoreComparison({ items }: Props) {
  const [results, setResults] = useState<StoreResult[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    // Simulate API delay
    const t = setTimeout(() => {
      const r = getMockResults(items);
      r.sort((a, b) => a.total - b.total);
      setResults(r);
      setLoading(false);
    }, 1200);
    return () => clearTimeout(t);
  }, [items]);

  if (loading) {
    return (
      <div className="bg-white rounded-2xl shadow-sm p-8 text-center">
        <div className="text-3xl mb-3 animate-bounce">🔍</div>
        <p className="text-gray-500 text-sm">Sprawdzam ceny w sklepach...</p>
      </div>
    );
  }

  const cheapest = results[0];
  const mostExpensive = results[results.length - 1];
  const savings = mostExpensive.total - cheapest.total;
  const savingsPct = ((savings / mostExpensive.total) * 100).toFixed(0);

  return (
    <div className="space-y-3">
      <div className="bg-green-500 rounded-2xl p-5 text-white">
        <p className="text-green-100 text-xs font-semibold uppercase tracking-widest mb-1">
          Najlepsza opcja
        </p>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-2xl font-bold">{cheapest.name}</p>
            <p className="text-green-100 text-sm mt-0.5">
              Oszczędzasz {savings.toFixed(2)} zł ({savingsPct}%) vs najdroższy
            </p>
          </div>
          <p className="text-3xl font-bold">{cheapest.total} zł</p>
        </div>
      </div>

      {results.map((store, i) => {
        const diffPct = (((store.total - cheapest.total) / cheapest.total) * 100).toFixed(0);
        const isCheapest = i === 0;

        return (
          <div
            key={store.name}
            className={`bg-white rounded-2xl shadow-sm p-5 border ${isCheapest ? "border-green-300" : "border-transparent"}`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="text-xl">{store.logo}</span>
                <span className="font-semibold text-gray-800">{store.name}</span>
                {isCheapest && (
                  <span className="bg-green-100 text-green-700 text-xs font-semibold px-2 py-0.5 rounded-full">
                    Najtaniej
                  </span>
                )}
              </div>
              <div className="text-right">
                <p className="font-bold text-lg text-gray-900">{store.total} zł</p>
                {!isCheapest && (
                  <p className="text-xs text-red-400 font-medium">+{diffPct}% drożej</p>
                )}
              </div>
            </div>

            <div className="space-y-1">
              {store.prices.map((p) => (
                <div key={p.item} className="flex justify-between text-sm text-gray-500">
                  <span>{p.item}</span>
                  <span>{p.price?.toFixed(2)} zł</span>
                </div>
              ))}
            </div>
          </div>
        );
      })}

      <p className="text-center text-xs text-gray-400 py-2">
        * Ceny poglądowe — integracja ze sklepami w toku
      </p>
    </div>
  );
}
