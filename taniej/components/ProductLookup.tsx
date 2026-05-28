"use client";

import { useState, useRef, useEffect } from "react";

const STORE_STYLE: Record<string, { bar: string; text: string }> = {
  Biedronka: { bar: "bg-red-500",    text: "text-red-600" },
  Lidl:      { bar: "bg-blue-500",   text: "text-blue-600" },
  Kaufland:  { bar: "bg-orange-500", text: "text-orange-600" },
  Aldi:      { bar: "bg-indigo-500", text: "text-indigo-600" },
  Netto:     { bar: "bg-yellow-400", text: "text-yellow-600" },
  Auchan:    { bar: "bg-purple-500", text: "text-purple-600" },
  Carrefour: { bar: "bg-sky-500",    text: "text-sky-600" },
};
const DEFAULT_STYLE = { bar: "bg-gray-400", text: "text-gray-600" };

interface StorePrice { name: string; logo: string; price: number | null }

export default function ProductLookup() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<StorePrice[] | null>(null);
  const [productName, setProductName] = useState("");
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!query.trim()) { setResults(null); return; }
    if (debounce.current) clearTimeout(debounce.current);
    debounce.current = setTimeout(() => search(query.trim()), 400);
  }, [query]);

  async function search(q: string) {
    setLoading(true);
    try {
      const res = await fetch("/api/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ items: [{ name: q, unit: "" }] }),
      });
      const data = await res.json();
      if (data.results?.length > 0) {
        const prices: StorePrice[] = data.results.map((s: any) => ({
          name: s.name,
          logo: s.logo,
          price: s.prices[0]?.price ?? null,
        }));
        prices.sort((a, b) => (a.price ?? 999) - (b.price ?? 999));
        const found = prices.find(p => p.price !== null);
        setProductName(data.results[0]?.prices[0]?.item || q);
        setResults(prices);
      } else {
        setResults([]);
      }
    } catch {}
    finally { setLoading(false); }
  }

  const withPrice = results?.filter(r => r.price !== null) ?? [];
  const cheapest = withPrice[0];
  const maxPrice = Math.max(...withPrice.map(r => r.price!), 0.01);

  return (
    <div className="bg-white rounded-2xl shadow-sm mb-4 overflow-hidden">
      <button
        className="w-full flex items-center justify-between p-5 text-left"
        onClick={() => setOpen(o => !o)}
      >
        <div>
          <p className="text-sm font-semibold text-gray-800">Szukaj ceny produktu</p>
          <p className="text-xs text-gray-400 mt-0.5">Sprawdź cenę jednego produktu we wszystkich sklepach</p>
        </div>
        <span className="text-gray-300 text-sm ml-3">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="px-5 pb-5 border-t border-gray-50">
          <input
            className="w-full border border-gray-200 rounded-xl px-4 py-3 text-base text-gray-900 placeholder-gray-400 focus:outline-none focus:border-green-400 transition-colors mt-4"
            placeholder="Np. Lay's Papryka, Milka, Coca-Cola..."
            value={query}
            onChange={e => setQuery(e.target.value)}
            autoComplete="off"
          />

          {loading && (
            <p className="text-xs text-gray-400 mt-3 text-center">Szukam...</p>
          )}

          {!loading && results !== null && results.length === 0 && (
            <p className="text-xs text-gray-400 mt-3 text-center">Brak wyników</p>
          )}

          {!loading && results && results.length > 0 && (
            <div className="mt-4">
              <p className="text-xs font-semibold text-gray-500 mb-3">{productName}</p>
              <div className="space-y-2.5">
                {results.map((store, i) => {
                  const style = STORE_STYLE[store.name] ?? DEFAULT_STYLE;
                  const isCheapest = i === 0 && store.price !== null;
                  const widthPct = store.price ? (store.price / maxPrice) * 100 : 0;
                  return (
                    <div key={store.name} className="flex items-center gap-3">
                      <div className={`w-7 h-7 rounded-lg ${style.bar} flex items-center justify-center text-white text-xs font-black shrink-0`}>
                        {store.name[0]}
                      </div>
                      <span className="text-xs text-gray-600 w-20 shrink-0 truncate">{store.name}</span>
                      <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${style.bar} transition-all duration-500`}
                          style={{ width: `${widthPct}%` }}
                        />
                      </div>
                      {store.price !== null ? (
                        <span className={`text-xs font-bold w-14 text-right shrink-0 ${isCheapest ? "text-green-600" : "text-gray-500"}`}>
                          {store.price.toFixed(2)} zł
                          {isCheapest && " ✓"}
                        </span>
                      ) : (
                        <span className="text-xs text-gray-300 w-14 text-right shrink-0">brak</span>
                      )}
                    </div>
                  );
                })}
              </div>
              {cheapest && (
                <p className="text-xs text-green-600 font-medium mt-3 text-center">
                  Najtaniej w {cheapest.name} — {cheapest.price?.toFixed(2)} zł
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
