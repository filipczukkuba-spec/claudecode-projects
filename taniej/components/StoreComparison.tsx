"use client";

import { useEffect, useState } from "react";
import { Item } from "@/types";

interface PriceRow {
  item: string;
  unit: string;
  price: number | null;
}

interface StoreResult {
  name: string;
  logo: string;
  prices: PriceRow[];
  total: number;
  found: number;
}

const STORE_STYLE: Record<string, { border: string; tag: string; bar: string; text: string }> = {
  Biedronka: { border: "border-red-200",    tag: "bg-red-50 text-red-700",      bar: "bg-red-500",    text: "text-red-600" },
  Lidl:      { border: "border-blue-200",   tag: "bg-blue-50 text-blue-700",    bar: "bg-blue-500",   text: "text-blue-600" },
  Kaufland:  { border: "border-orange-200", tag: "bg-orange-50 text-orange-700",bar: "bg-orange-500", text: "text-orange-600" },
  Aldi:      { border: "border-indigo-200", tag: "bg-indigo-50 text-indigo-700",bar: "bg-indigo-500", text: "text-indigo-600" },
  Netto:     { border: "border-yellow-200", tag: "bg-yellow-50 text-yellow-700",bar: "bg-yellow-400", text: "text-yellow-600" },
  Auchan:    { border: "border-purple-200", tag: "bg-purple-50 text-purple-700",bar: "bg-purple-500", text: "text-purple-600" },
  Carrefour: { border: "border-sky-200",    tag: "bg-sky-50 text-sky-700",      bar: "bg-sky-500",    text: "text-sky-600" },
};

const DEFAULT_STYLE = { border: "border-gray-200", tag: "bg-gray-50 text-gray-700", bar: "bg-gray-400", text: "text-gray-600" };

interface Props { items: Item[] }

export default function StoreComparison({ items }: Props) {
  const [results, setResults] = useState<StoreResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  useEffect(() => {
    setLoading(true);
    setError(null);

    fetch("/api/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ items }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.error) throw new Error(data.error);

        const processed: StoreResult[] = data.results.map(
          (store: { name: string; logo: string; prices: PriceRow[] }) => {
            const found = store.prices.filter((p) => p.price !== null).length;
            const total = store.prices.reduce((sum, p) => sum + (p.price ?? 0), 0);
            return { ...store, total: parseFloat(total.toFixed(2)), found };
          }
        );

        processed.sort((a, b) => a.total - b.total);

        // auto-expand the cheapest store
        if (processed.length > 0) {
          setExpanded({ [processed[0].name]: true });
        }

        setResults(processed);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [items]);

  if (loading) {
    return (
      <div className="bg-white rounded-2xl shadow-sm p-8 text-center">
        <div className="text-3xl mb-3 animate-bounce">🔍</div>
        <p className="text-gray-700 font-medium text-sm">Sprawdzam ceny w sklepach...</p>
        <p className="text-gray-400 text-xs mt-1">To może zająć chwilę</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 rounded-2xl p-6 text-center border border-red-100">
        <p className="text-red-500 font-medium text-sm">Coś poszło nie tak</p>
        <p className="text-red-400 text-xs mt-1">{error}</p>
      </div>
    );
  }

  if (results.length === 0) return null;

  const cheapest = results[0];
  const mostExpensive = results[results.length - 1];
  const savings = mostExpensive.total - cheapest.total;
  const savingsPct = mostExpensive.total > 0
    ? ((savings / mostExpensive.total) * 100).toFixed(0)
    : "0";

  // cheapest price per item across all stores
  const cheapestPerItem: Record<string, number> = {};
  for (const store of results) {
    for (const p of store.prices) {
      if (p.price !== null) {
        if (cheapestPerItem[p.item] === undefined || p.price < cheapestPerItem[p.item]) {
          cheapestPerItem[p.item] = p.price;
        }
      }
    }
  }

  const maxTotal = mostExpensive.total || 1;

  return (
    <div className="space-y-3">
      {/* Winner banner */}
      {results.length > 1 && (
        <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-2xl p-5 text-white shadow-sm">
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
      )}

      {/* Price bar chart */}
      <div className="bg-white rounded-2xl shadow-sm p-5">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">
          Porównanie
        </p>
        <div className="space-y-2.5">
          {results.map((store, i) => {
            const style = STORE_STYLE[store.name] ?? DEFAULT_STYLE;
            const widthPct = maxTotal > 0 ? (store.total / maxTotal) * 100 : 0;
            return (
              <div key={store.name} className="flex items-center gap-3">
                <span className="text-xs text-gray-500 w-20 shrink-0 truncate">{store.name}</span>
                <div className="flex-1 bg-gray-100 rounded-full h-2.5 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${style.bar}`}
                    style={{ width: `${widthPct}%` }}
                  />
                </div>
                <span className={`text-xs font-bold w-16 text-right shrink-0 ${i === 0 ? "text-green-600" : "text-gray-500"}`}>
                  {store.total} zł
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Store cards */}
      {results.map((store, i) => {
        const style = STORE_STYLE[store.name] ?? DEFAULT_STYLE;
        const isCheapest = i === 0;
        const diffPct = cheapest.total > 0
          ? (((store.total - cheapest.total) / cheapest.total) * 100).toFixed(0)
          : "0";
        const isOpen = expanded[store.name] ?? false;

        return (
          <div
            key={store.name}
            className={`bg-white rounded-2xl shadow-sm border ${isCheapest ? style.border : "border-transparent"} overflow-hidden`}
          >
            {/* Card header — always visible, tap to expand */}
            <button
              className="w-full flex items-center justify-between p-5 text-left"
              onClick={() => setExpanded((e) => ({ ...e, [store.name]: !e[store.name] }))}
            >
              <div className="flex items-center gap-2">
                <span className="text-lg">{store.logo}</span>
                <span className="font-semibold text-gray-800">{store.name}</span>
                {isCheapest && results.length > 1 && (
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${style.tag}`}>
                    Najtaniej
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3">
                <div className="text-right">
                  <p className="font-bold text-lg text-gray-900">{store.total} zł</p>
                  {!isCheapest && results.length > 1 && (
                    <p className="text-xs text-red-400 font-medium">+{diffPct}% drożej</p>
                  )}
                </div>
                <span className="text-gray-300 text-sm">{isOpen ? "▲" : "▼"}</span>
              </div>
            </button>

            {/* Expandable item list */}
            {isOpen && (
              <div className="px-5 pb-4 border-t border-gray-50">
                <div className="space-y-1.5 mt-3">
                  {store.prices.map((p) => {
                    const isCheapestItem = p.price !== null && p.price === cheapestPerItem[p.item];
                    return (
                      <div key={p.item} className="flex justify-between text-sm">
                        <div className="text-gray-600">
                          <span>{p.item}</span>
                          {p.unit && <span className="text-gray-300 text-xs ml-1">({p.unit})</span>}
                        </div>
                        {p.price !== null ? (
                          <span className={`font-medium ${isCheapestItem ? "text-green-600" : "text-gray-500"}`}>
                            {p.price.toFixed(2)} zł
                          </span>
                        ) : (
                          <span className="text-gray-300 text-xs">brak danych</span>
                        )}
                      </div>
                    );
                  })}
                </div>
                {store.found < items.length && (
                  <p className="text-xs text-amber-500 mt-2">
                    Znaleziono {store.found} z {items.length} produktów
                  </p>
                )}
              </div>
            )}
          </div>
        );
      })}

      <p className="text-center text-xs text-gray-400 py-2">
        Przybliżone ceny • aktualizowane regularnie
      </p>
    </div>
  );
}
