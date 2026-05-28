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

interface Props {
  items: Item[];
}

export default function StoreComparison({ items }: Props) {
  const [results, setResults] = useState<StoreResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
            const total = store.prices.reduce(
              (sum, p) => sum + (p.price ?? 0),
              0
            );
            return {
              ...store,
              total: parseFloat(total.toFixed(2)),
              found,
            };
          }
        );

        processed.sort((a, b) => a.total - b.total);
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
  const savingsPct =
    mostExpensive.total > 0
      ? ((savings / mostExpensive.total) * 100).toFixed(0)
      : "0";

  return (
    <div className="space-y-3">
      {results.length > 1 && (
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
      )}

      {results.map((store, i) => {
        const diffPct =
          cheapest.total > 0
            ? (((store.total - cheapest.total) / cheapest.total) * 100).toFixed(0)
            : "0";
        const isCheapest = i === 0;

        return (
          <div
            key={store.name}
            className={`bg-white rounded-2xl shadow-sm p-5 border ${
              isCheapest ? "border-green-300" : "border-transparent"
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="text-xl">{store.logo}</span>
                <span className="font-semibold text-gray-800">{store.name}</span>
                {isCheapest && results.length > 1 && (
                  <span className="bg-green-100 text-green-700 text-xs font-semibold px-2 py-0.5 rounded-full">
                    Najtaniej
                  </span>
                )}
              </div>
              <div className="text-right">
                <p className="font-bold text-lg text-gray-900">{store.total} zł</p>
                {!isCheapest && results.length > 1 && (
                  <p className="text-xs text-red-400 font-medium">+{diffPct}% drożej</p>
                )}
              </div>
            </div>

            <div className="space-y-1">
              {store.prices.map((p) => (
                <div
                  key={p.item}
                  className="flex justify-between text-sm text-gray-500"
                >
                  <div>
                    <span>{p.item}</span>
                    {p.unit && (
                      <span className="text-gray-300 text-xs ml-1">({p.unit})</span>
                    )}
                  </div>
                  {p.price !== null ? (
                    <span>{p.price.toFixed(2)} zł</span>
                  ) : (
                    <span className="text-gray-300 text-xs">brak danych</span>
                  )}
                </div>
              ))}
            </div>

            {store.found < items.length && (
              <p className="text-xs text-amber-500 mt-2">
                Znaleziono {store.found} z {items.length} produktów
              </p>
            )}
          </div>
        );
      })}

      <p className="text-center text-xs text-gray-400 py-2">
        Ceny z Lidl.pl • aktualizowane na żywo
      </p>
    </div>
  );
}
