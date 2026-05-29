"use client";

import { useEffect, useState } from "react";
import { Item } from "@/types";

interface PriceRow {
  item: string;
  unit: string;
  price: number | null;
  app_price: number | null;
  promo_price: number | null;
  promo_label: string | null;
}

interface StoreResult {
  name: string;
  logo: string;
  prices: PriceRow[];
  total: number;
  found: number;
}

const STORE_STYLE: Record<string, { border: string; tag: string; bar: string; text: string; bg: string }> = {
  Biedronka: { border: "border-red-200",    tag: "bg-red-50 text-red-700",       bar: "bg-red-500",    text: "text-red-600",    bg: "bg-red-500" },
  Lidl:      { border: "border-blue-200",   tag: "bg-blue-50 text-blue-700",     bar: "bg-blue-500",   text: "text-blue-600",   bg: "bg-blue-500" },
  Kaufland:  { border: "border-orange-200", tag: "bg-orange-50 text-orange-700", bar: "bg-orange-500", text: "text-orange-600", bg: "bg-orange-500" },
  Aldi:      { border: "border-indigo-200", tag: "bg-indigo-50 text-indigo-700", bar: "bg-indigo-500", text: "text-indigo-600", bg: "bg-indigo-500" },
  Netto:     { border: "border-yellow-200", tag: "bg-yellow-50 text-yellow-700", bar: "bg-yellow-400", text: "text-yellow-600", bg: "bg-yellow-400" },
  Auchan:    { border: "border-purple-200", tag: "bg-purple-50 text-purple-700", bar: "bg-purple-500", text: "text-purple-600", bg: "bg-purple-500" },
  Carrefour: { border: "border-sky-200",    tag: "bg-sky-50 text-sky-700",       bar: "bg-sky-500",    text: "text-sky-600",    bg: "bg-sky-500" },
};

const DEFAULT_STYLE = { border: "border-gray-200", tag: "bg-gray-50 text-gray-700", bar: "bg-gray-400", text: "text-gray-600", bg: "bg-gray-400" };

function fmt(n: number) {
  return n.toLocaleString("pl-PL", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function effectivePrice(p: PriceRow): number | null {
  const candidates = [p.promo_price, p.app_price, p.price].filter((v): v is number => v !== null);
  return candidates.length > 0 ? Math.min(...candidates) : null;
}

interface Props { items: Item[] }

export default function StoreComparison({ items }: Props) {
  const [results, setResults] = useState<StoreResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [shared, setShared] = useState(false);

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
            const found = store.prices.filter((p) => effectivePrice(p) !== null).length;
            const total = store.prices.reduce((sum, p) => sum + (effectivePrice(p) ?? 0), 0);
            return { ...store, total: parseFloat(total.toFixed(2)), found };
          }
        );

        processed.sort((a, b) => a.total - b.total);

        if (processed.length > 0) {
          setExpanded({ [processed[0].name]: true });
        }

        setResults(processed);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [items]);

  function shareResults() {
    const encoded = btoa(JSON.stringify(items));
    const url = `${window.location.origin}/?l=${encoded}`;
    navigator.clipboard.writeText(url).then(() => {
      setShared(true);
      setTimeout(() => setShared(false), 2500);
    });
  }

  if (loading) {
    return (
      <div className="bg-white rounded-2xl shadow-sm p-8 text-center">
        <div className="flex justify-center gap-1.5 mb-4">
          {["bg-red-400", "bg-blue-400", "bg-orange-400", "bg-indigo-400", "bg-yellow-400", "bg-purple-400", "bg-sky-400"].map((c, i) => (
            <div
              key={i}
              className={`w-2.5 h-2.5 rounded-full ${c} animate-bounce`}
              style={{ animationDelay: `${i * 80}ms` }}
            />
          ))}
        </div>
        <p className="text-gray-700 font-semibold text-sm">Sprawdzam ceny w 7 sklepach...</p>
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

  if (results.length === 0) return (
    <div className="bg-white rounded-2xl shadow-sm p-8 text-center animate-slide-up">
      <p className="text-3xl mb-3">😕</p>
      <p className="text-gray-700 font-semibold text-sm">Brak wyników</p>
      <p className="text-gray-400 text-xs mt-1.5 leading-relaxed">
        Nie znaleźliśmy cen tych produktów w bazie.<br />
        Spróbuj użyć prostszych nazw (np. &quot;chipsy&quot; zamiast &quot;Lay&apos;s Max&quot;).
      </p>
    </div>
  );

  const cheapest = results[0];
  const mostExpensive = results[results.length - 1];
  const savings = mostExpensive.total - cheapest.total;
  const savingsPct = mostExpensive.total > 0
    ? ((savings / mostExpensive.total) * 100).toFixed(0)
    : "0";
  const cheapestStyle = STORE_STYLE[cheapest.name] ?? DEFAULT_STYLE;

  const cheapestPerItem: Record<string, number> = {};
  for (const store of results) {
    for (const p of store.prices) {
      const ep = effectivePrice(p);
      if (ep !== null) {
        if (cheapestPerItem[p.item] === undefined || ep < cheapestPerItem[p.item]) {
          cheapestPerItem[p.item] = ep;
        }
      }
    }
  }

  return (
    <div className="space-y-3">

      {/* Winner banner */}
      {results.length > 1 && (
        <div className={`relative overflow-hidden rounded-2xl p-5 text-white shadow-md ${cheapestStyle.bg}`}>
          <div className="absolute -top-4 -right-4 w-20 h-20 rounded-full bg-white/10 pointer-events-none" />
          <div className="absolute -bottom-6 -left-2 w-16 h-16 rounded-full bg-white/10 pointer-events-none" />
          <div className="relative">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-white/80 text-xs font-bold uppercase tracking-widest">Najlepsza opcja</span>
              <span className="text-base">🏆</span>
            </div>
            <div className="flex items-end justify-between gap-2">
              <div>
                <p className="text-3xl font-black leading-none">{cheapest.name}</p>
                {savings > 0.01 && (
                  <p className="text-white/85 text-sm mt-1.5 font-medium">
                    Oszczędzasz <span className="text-white font-black">{fmt(savings)} zł</span> vs najdroższy
                    <span className="text-white/70 ml-1">({savingsPct}%)</span>
                  </p>
                )}
                <p className="text-white/70 text-xs mt-1">
                  {cheapest.found} z {items.length} produktów znalezionych
                </p>
              </div>
              <div className="text-right shrink-0">
                <p className="text-4xl font-black leading-none">{fmt(cheapest.total)}</p>
                <p className="text-white/80 text-sm font-medium">złotych</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Bar chart with +X zł labels */}
      <div className="bg-white rounded-2xl shadow-sm p-5">
        <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-4">
          Porównanie cen koszyka
        </p>
        <div className="space-y-3">
          {results.map((store, i) => {
            const style = STORE_STYLE[store.name] ?? DEFAULT_STYLE;
            const diff = store.total - cheapest.total;
            const widthPct = cheapest.total > 0
              ? Math.max(20, (store.total / (mostExpensive.total || 1)) * 100)
              : 20;
            const hasPromos = store.prices.some(p => p.promo_price !== null);
            const hasApp = store.prices.some(p => p.app_price !== null);
            return (
              <div key={store.name}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-semibold text-gray-700 w-20 shrink-0 truncate">
                    {store.name}
                  </span>
                  <div className="flex items-center gap-1 ml-auto">
                    {hasPromos && (
                      <span className="text-[10px] bg-orange-100 text-orange-600 font-bold px-1.5 py-0.5 rounded-full leading-none">
                        PROMO
                      </span>
                    )}
                    {hasApp && (
                      <span className="text-[10px] bg-blue-100 text-blue-600 font-bold px-1.5 py-0.5 rounded-full leading-none">
                        APP
                      </span>
                    )}
                    <span className={`text-xs font-black ${i === 0 ? "text-green-600" : "text-gray-500"}`}>
                      {fmt(store.total)} zł
                    </span>
                    {i > 0 && diff > 0.01 && (
                      <span className="text-[10px] text-red-400 font-bold">
                        +{fmt(diff)}
                      </span>
                    )}
                    {i === 0 && (
                      <span className="text-[10px] text-green-600 font-bold">✓</span>
                    )}
                  </div>
                </div>
                <div className="bg-gray-100 rounded-full h-2 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-700 ease-out ${style.bar}`}
                    style={{ width: `${widthPct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Store cards */}
      {results.map((store, i) => {
        const style = STORE_STYLE[store.name] ?? DEFAULT_STYLE;
        const isCheapest = i === 0;
        const diff = store.total - cheapest.total;
        const diffPct = cheapest.total > 0
          ? (((store.total - cheapest.total) / cheapest.total) * 100).toFixed(0)
          : "0";
        const isOpen = expanded[store.name] ?? false;
        const promoCount = store.prices.filter(p => p.promo_price !== null).length;

        return (
          <div
            key={store.name}
            className={`bg-white rounded-2xl shadow-sm border transition-all ${isCheapest ? `${style.border} border-2` : "border-transparent border"} overflow-hidden`}
          >
            <button
              className="w-full flex items-center justify-between px-5 py-4 text-left"
              onClick={() => setExpanded((e) => ({ ...e, [store.name]: !e[store.name] }))}
            >
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-xl ${style.bg} flex items-center justify-center text-white text-base font-black shadow-sm shrink-0`}>
                  {store.name[0]}
                </div>
                <div>
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="font-bold text-gray-800">{store.name}</span>
                    {isCheapest && results.length > 1 && (
                      <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${style.tag}`}>
                        Najtaniej
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {store.found}/{items.length} produktów
                    {promoCount > 0 && ` · ${promoCount} w promocji`}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="text-right">
                  <p className="font-black text-xl text-gray-900 leading-tight">{fmt(store.total)} zł</p>
                  {!isCheapest && results.length > 1 && diff > 0.01 && (
                    <p className="text-xs text-red-400 font-semibold leading-tight">
                      +{fmt(diff)} zł ({diffPct}%)
                    </p>
                  )}
                </div>
                <span className="text-gray-300">{isOpen ? "▲" : "▼"}</span>
              </div>
            </button>

            {isOpen && (
              <div className="px-5 pb-5 border-t border-gray-50">
                <div className="space-y-2 mt-4">
                  {store.prices.map((p) => {
                    const ep = effectivePrice(p);
                    const isCheapestItem = ep !== null && ep === cheapestPerItem[p.item];
                    const hasPromo = p.promo_price !== null;
                    const hasApp = p.app_price !== null;
                    const promoIsBetter = hasPromo && (!hasApp || p.promo_price! <= (p.app_price ?? Infinity));
                    const appIsBetter = hasApp && (!hasPromo || p.app_price! < p.promo_price!);

                    return (
                      <div key={p.item} className={`flex justify-between items-center text-sm py-1 border-b border-gray-50 last:border-0`}>
                        <div className="text-gray-600 flex items-center gap-1.5 flex-wrap min-w-0 mr-2">
                          <span className="truncate max-w-[140px]">{p.item}</span>
                          {p.unit && <span className="text-gray-300 text-xs shrink-0">({p.unit})</span>}
                          {hasPromo && (
                            <span className="text-[10px] bg-orange-100 text-orange-600 font-bold px-1.5 py-0.5 rounded-full leading-none shrink-0">
                              {p.promo_label ?? "PROMO"}
                            </span>
                          )}
                          {appIsBetter && (
                            <span className="text-[10px] bg-blue-100 text-blue-600 font-bold px-1.5 py-0.5 rounded-full leading-none shrink-0">
                              APP
                            </span>
                          )}
                        </div>
                        {ep !== null ? (
                          <div className="flex flex-col items-end gap-0.5 shrink-0">
                            {(hasPromo || hasApp) && p.price !== null && (
                              <span className="text-xs text-gray-300 line-through leading-none">
                                {fmt(p.price)} zł
                              </span>
                            )}
                            <span className={`font-bold leading-none ${
                              promoIsBetter ? "text-orange-600" :
                              appIsBetter ? "text-blue-600" :
                              isCheapestItem ? "text-green-600" :
                              "text-gray-700"
                            }`}>
                              {fmt(ep)} zł
                            </span>
                          </div>
                        ) : (
                          <span className="text-gray-300 text-xs shrink-0">brak danych</span>
                        )}
                      </div>
                    );
                  })}
                </div>
                {store.found < items.length && (
                  <div className="mt-3 bg-amber-50 rounded-xl px-3 py-2 text-xs text-amber-600 font-medium">
                    Brak danych dla {items.length - store.found} produktu/ów
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}

      {/* Share + disclaimer */}
      <div className="bg-white rounded-2xl shadow-sm p-4 flex items-center gap-3">
        <button
          onClick={shareResults}
          className="flex-1 flex items-center justify-center gap-2 bg-gray-900 hover:bg-gray-800 active:scale-[0.98] transition-all text-white font-bold text-sm rounded-xl py-3"
        >
          <span>{shared ? "✓ Skopiowano!" : "Udostępnij wyniki"}</span>
          {!shared && <span className="text-base">🔗</span>}
        </button>
      </div>

      <div className="bg-amber-50 border border-amber-100 rounded-xl px-4 py-3">
        <p className="text-xs text-amber-700 font-medium leading-relaxed">
          <span className="font-bold">Ceny orientacyjne.</span> Aktualizowane co tydzień ze sklepowych gazetki i aplikacji.
          Przed zakupem sprawdź aktualną cenę w sklepie.
          <span className="block mt-1 text-amber-600">Promocje zaznaczono na pomarańczowo · Ceny z aplikacji na niebiesko</span>
        </p>
      </div>

    </div>
  );
}
