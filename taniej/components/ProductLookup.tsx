"use client";

import { useState, useRef, useEffect } from "react";

const STORE_STYLE: Record<string, { bar: string; bg: string }> = {
  Biedronka: { bar: "bg-red-500",    bg: "bg-red-500" },
  Lidl:      { bar: "bg-blue-500",   bg: "bg-blue-500" },
  Kaufland:  { bar: "bg-orange-500", bg: "bg-orange-500" },
  Aldi:      { bar: "bg-indigo-500", bg: "bg-indigo-500" },
  Netto:     { bar: "bg-yellow-400", bg: "bg-yellow-400" },
  Auchan:    { bar: "bg-purple-500", bg: "bg-purple-500" },
  Carrefour: { bar: "bg-sky-500",    bg: "bg-sky-500" },
};
const DEFAULT_STYLE = { bar: "bg-gray-400", bg: "bg-gray-400" };

interface StorePrice {
  name: string;
  logo: string;
  price: number | null;
  app_price: number | null;
  promo_price: number | null;
  promo_label: string | null;
}

function fmt(n: number) {
  return n.toLocaleString("pl-PL", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function effectivePrice(p: StorePrice): number | null {
  const candidates = [p.promo_price, p.app_price, p.price].filter((v): v is number => v !== null);
  return candidates.length > 0 ? Math.min(...candidates) : null;
}

function bestLabel(p: StorePrice): { tag: string; color: string } | null {
  if (p.promo_price !== null && (p.app_price === null || p.promo_price <= p.app_price)) {
    return { tag: p.promo_label ?? "PROMO", color: "text-orange-600 bg-orange-100" };
  }
  if (p.app_price !== null) {
    return { tag: "z aplikacją", color: "text-blue-600 bg-blue-100" };
  }
  return null;
}

export default function ProductLookup() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<StorePrice[] | null>(null);
  const [productName, setProductName] = useState("");
  const [loading, setLoading] = useState(false);
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
          app_price: s.prices[0]?.app_price ?? null,
          promo_price: s.prices[0]?.promo_price ?? null,
          promo_label: s.prices[0]?.promo_label ?? null,
        }));
        prices.sort((a, b) => (effectivePrice(a) ?? 9999) - (effectivePrice(b) ?? 9999));
        setProductName(data.results[0]?.prices[0]?.item || q);
        setResults(prices);
      } else {
        setResults([]);
      }
    } catch {}
    finally { setLoading(false); }
  }

  const withPrice = results?.filter(r => effectivePrice(r) !== null) ?? [];
  const cheapest = withPrice[0];
  const maxPrice = Math.max(...withPrice.map(r => effectivePrice(r)!), 0.01);

  return (
    <div className="bg-white rounded-2xl shadow-sm mb-4 overflow-hidden">
      <div className="p-4">
        <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Szybkie wyszukiwanie</p>
        <div className="relative">
          <input
            className="w-full border border-gray-200 rounded-xl pl-4 pr-10 py-3 text-base text-gray-900 placeholder-gray-400 focus:outline-none focus:border-green-400 transition-colors bg-gray-50 focus:bg-white"
            placeholder="Np. mleko, Coca-Cola, Lay's..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoComplete="off"
            autoCorrect="off"
          />
          {loading ? (
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              <div className="w-4 h-4 border-2 border-green-400 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : query ? (
            <button
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-300 hover:text-gray-500 transition-colors text-lg leading-none"
              onClick={() => { setQuery(""); setResults(null); }}
            >
              ×
            </button>
          ) : (
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-300 text-base">🔍</span>
          )}
        </div>
      </div>

      {!loading && results !== null && results.length === 0 && (
        <div className="px-4 pb-4 text-center">
          <p className="text-xs text-gray-400">Brak wyników dla &quot;{query}&quot;</p>
        </div>
      )}

      {!loading && results && results.length > 0 && (
        <div className="border-t border-gray-50">
          {/* Product name header */}
          <div className="px-4 pt-3 pb-2 flex items-center justify-between">
            <p className="text-sm font-bold text-gray-700 truncate">{productName}</p>
            {cheapest && (
              <span className={`text-xs font-bold px-2 py-1 rounded-full shrink-0 ml-2 ${
                cheapest.promo_price !== null ? "bg-orange-100 text-orange-700" :
                cheapest.app_price !== null ? "bg-blue-100 text-blue-700" :
                "bg-green-100 text-green-700"
              }`}>
                od {fmt(effectivePrice(cheapest)!)} zł
              </span>
            )}
          </div>

          <div className="px-4 pb-4 space-y-2.5">
            {results.map((store, i) => {
              const style = STORE_STYLE[store.name] ?? DEFAULT_STYLE;
              const ep = effectivePrice(store);
              const isCheapest = i === 0 && ep !== null;
              const widthPct = ep ? (ep / maxPrice) * 100 : 0;
              const label = bestLabel(store);
              return (
                <div key={store.name} className="flex items-center gap-2.5">
                  <div className={`w-7 h-7 rounded-lg ${style.bg} flex items-center justify-center text-white text-xs font-black shrink-0 shadow-sm`}>
                    {store.name[0]}
                  </div>
                  <span className="text-xs font-medium text-gray-600 w-18 shrink-0 truncate" style={{ width: "72px" }}>{store.name}</span>
                  <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${style.bar}`}
                      style={{ width: `${widthPct}%` }}
                    />
                  </div>
                  {ep !== null ? (
                    <div className="flex items-center gap-1 shrink-0" style={{ minWidth: "80px", justifyContent: "flex-end" }}>
                      {store.price !== null && label && (
                        <span className="text-xs text-gray-300 line-through">{fmt(store.price)}</span>
                      )}
                      <span className={`text-xs font-black ${
                        label ? (label.tag === "z aplikacją" ? "text-blue-600" : "text-orange-600") :
                        isCheapest ? "text-green-600" : "text-gray-500"
                      }`}>
                        {fmt(ep)} zł
                      </span>
                      {label && (
                        <span className={`text-[9px] font-bold px-1 py-0.5 rounded leading-none ${label.color}`}>
                          {label.tag.startsWith("-") || label.tag === "PROMO" ? label.tag : label.tag === "z aplikacją" ? "APP" : label.tag}
                        </span>
                      )}
                      {isCheapest && !label && (
                        <span className="text-green-500 text-xs">✓</span>
                      )}
                    </div>
                  ) : (
                    <span className="text-xs text-gray-300 shrink-0" style={{ minWidth: "80px", textAlign: "right" }}>brak</span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
