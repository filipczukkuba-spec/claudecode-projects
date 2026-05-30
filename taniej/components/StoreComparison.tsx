"use client";

import { useEffect, useState } from "react";
import { Item } from "@/types";

interface PriceRow {
  item: string;
  unit: string;
  product_id: number | null;
  store_id: number | null;
  price: number | null;
  app_price: number | null;
  promo_price: number | null;
  promo_label: string | null;
  reported_price: number | null;
  reported_at: string | null;
  reported_city: string | null;
  source: string | null;
  scraped_at: string | null;
}

function isEstimated(p: PriceRow): boolean {
  // A price is "real" if scraped, has a promo, has an app price, or has a user-reported price.
  // Otherwise treat as estimate.
  if (p.reported_price !== null) return false;
  if (p.promo_price !== null) return false;
  if (p.app_price !== null) return false;
  return p.source !== "scraped";
}

interface StoreResult {
  name: string;
  logo: string;
  prices: PriceRow[];
  total: number;
  found: number;
}

const STORE_STYLE: Record<string, { border: string; tag: string; bar: string; text: string; bg: string }> = {
  Biedronka: { border: "border-red-300",    tag: "bg-red-50 text-red-700",       bar: "bg-red-500",    text: "text-red-600",    bg: "bg-red-500" },
  Lidl:      { border: "border-blue-300",   tag: "bg-blue-50 text-blue-700",     bar: "bg-blue-500",   text: "text-blue-600",   bg: "bg-blue-500" },
  Kaufland:  { border: "border-orange-300", tag: "bg-orange-50 text-orange-700", bar: "bg-orange-500", text: "text-orange-600", bg: "bg-orange-500" },
  Aldi:      { border: "border-indigo-300", tag: "bg-indigo-50 text-indigo-700", bar: "bg-indigo-500", text: "text-indigo-600", bg: "bg-indigo-500" },
  Netto:     { border: "border-yellow-300", tag: "bg-yellow-50 text-yellow-700", bar: "bg-yellow-400", text: "text-yellow-600", bg: "bg-yellow-400" },
  Auchan:    { border: "border-purple-300", tag: "bg-purple-50 text-purple-700", bar: "bg-purple-500", text: "text-purple-600", bg: "bg-purple-500" },
  Carrefour: { border: "border-sky-300",    tag: "bg-sky-50 text-sky-700",       bar: "bg-sky-500",    text: "text-sky-600",    bg: "bg-sky-500" },
};

const DEFAULT_STYLE = { border: "border-gray-200", tag: "bg-gray-50 text-gray-700", bar: "bg-gray-400", text: "text-gray-600", bg: "bg-gray-400" };

function fmt(n: number) {
  return n.toLocaleString("pl-PL", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Main price used for totals & ranking. ONLY uses trusted sources
// (scraped, estimated, promo, app). User-reported "shelf" prices are
// shown separately as informational only — they can't skew totals.
function effectivePrice(p: PriceRow): number | null {
  const candidates = [p.promo_price, p.app_price, p.price].filter((v): v is number => v !== null);
  return candidates.length > 0 ? Math.min(...candidates) : null;
}

function daysAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const days = Math.floor(diff / 86400000);
  if (days === 0) return "dziś";
  if (days === 1) return "wczoraj";
  return `${days} dni temu`;
}

interface ReportModalProps {
  item: string;
  storeName: string;
  productId: number;
  storeId: number;
  currentPrice: number | null;
  onClose: () => void;
  onSubmitted: (price: number) => void;
}

function ReportModal({ item, storeName, productId, storeId, currentPrice, onClose, onSubmitted }: ReportModalProps) {
  const [price, setPrice] = useState(currentPrice ? String(currentPrice).replace(".", ",") : "");
  const [city, setCity] = useState("");
  const [sending, setSending] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    const parsed = parseFloat(price.replace(",", "."));
    if (!parsed || parsed <= 0) return;
    setSending(true);
    setError(null);
    try {
      const res = await fetch("/api/report-price", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_id: productId, store_id: storeId, price: parsed, city }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error ?? "Nie udało się zapisać");
        return;
      }
      setDone(true);
      setTimeout(() => { onSubmitted(parsed); onClose(); }, 1200);
    } catch {
      setError("Błąd połączenia");
    }
    finally { setSending(false); }
  }

  return (
    <div className="fixed inset-0 bg-black/60 z-[200] flex items-end justify-center" onClick={onClose}>
      <div
        className="bg-white rounded-t-3xl w-full max-w-md p-6 pb-8"
        style={{ paddingBottom: `calc(2rem + env(safe-area-inset-bottom))` }}
        onClick={(e) => e.stopPropagation()}
      >
        {done ? (
          <div className="text-center py-4">
            <div className="text-4xl mb-3">✅</div>
            <p className="font-bold text-gray-800">Dziękujemy!</p>
            <p className="text-sm text-gray-500 mt-1">Cena zostanie zaktualizowana</p>
          </div>
        ) : (
          <>
            <div className="w-10 h-1 bg-gray-200 rounded-full mx-auto mb-5" />
            <p className="font-black text-gray-900 text-lg">Zgłoś cenę z półki</p>
            <p className="text-sm text-gray-500 mt-1 mb-5">
              <span className="font-semibold text-gray-700">{item}</span> w {storeName}
            </p>

            <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1.5">
              Cena na półce (zł)
            </label>
            <input
              type="text"
              inputMode="decimal"
              className="w-full border-2 border-gray-200 focus:border-green-400 rounded-xl px-4 py-3.5 text-xl font-bold text-gray-900 text-center outline-none transition-colors mb-4"
              placeholder="np. 9,99"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              autoFocus
            />

            <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1.5">
              Miasto (opcjonalnie)
            </label>
            <input
              type="text"
              className="w-full border border-gray-200 focus:border-gray-300 rounded-xl px-4 py-3 text-base text-gray-700 outline-none transition-colors mb-5"
              placeholder="np. Warszawa"
              value={city}
              onChange={(e) => setCity(e.target.value)}
            />

            {error && (
              <div className="mb-3 bg-red-50 border border-red-100 rounded-xl px-3 py-2 text-xs text-red-600 font-medium">
                {error}
              </div>
            )}
            <button
              onClick={submit}
              disabled={sending || !price}
              className="w-full bg-green-500 hover:bg-green-600 active:scale-[0.98] disabled:opacity-50 transition-all text-white font-black text-base rounded-2xl py-4"
            >
              {sending ? "Wysyłam..." : "Wyślij cenę"}
            </button>
            <p className="text-center text-xs text-gray-400 mt-3">
              Pomaga innym kupić taniej · 100% anonimowo
            </p>
          </>
        )}
      </div>
    </div>
  );
}

interface Props { items: Item[] }

export default function StoreComparison({ items }: Props) {
  const [results, setResults] = useState<StoreResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [shared, setShared] = useState(false);
  const [reportTarget, setReportTarget] = useState<{ row: PriceRow; storeName: string } | null>(null);

  function load() {
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
        // Sort by: most products found first, then by total. A store with
        // zero priced items must never win — its 0,00 zł is "no data", not free.
        processed.sort((a, b) => {
          if (a.found !== b.found) return b.found - a.found;
          return a.total - b.total;
        });
        const firstWithData = processed.find((s) => s.found > 0);
        if (firstWithData) setExpanded({ [firstWithData.name]: true });
        setResults(processed);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, [items]);

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
            <div key={i} className={`w-2.5 h-2.5 rounded-full ${c} animate-bounce`} style={{ animationDelay: `${i * 80}ms` }} />
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
    <div className="bg-white rounded-2xl shadow-sm p-8 text-center">
      <p className="text-3xl mb-3">😕</p>
      <p className="text-gray-700 font-semibold text-sm">Brak wyników</p>
      <p className="text-gray-400 text-xs mt-1.5 leading-relaxed">
        Spróbuj użyć prostszych nazw (np. &quot;chipsy&quot; zamiast &quot;Lay&apos;s Max&quot;).
      </p>
    </div>
  );

  // Cheapest = the first store with at least one priced product.
  // Stores with `found === 0` have no data and must not be ranked as winners.
  const withData = results.filter((s) => s.found > 0);
  const cheapest = withData[0] ?? results[0];
  const mostExpensive = withData[withData.length - 1] ?? results[results.length - 1];
  const savings = mostExpensive.total - cheapest.total;
  const savingsPct = mostExpensive.total > 0 ? ((savings / mostExpensive.total) * 100).toFixed(0) : "0";
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

  const totalReports = results.reduce((n, s) => n + s.prices.filter(p => p.reported_price !== null).length, 0);

  return (
    <div className="space-y-3">
      {reportTarget && (
        <ReportModal
          item={reportTarget.row.item}
          storeName={reportTarget.storeName}
          productId={reportTarget.row.product_id!}
          storeId={reportTarget.row.store_id!}
          currentPrice={effectivePrice(reportTarget.row)}
          onClose={() => setReportTarget(null)}
          onSubmitted={() => { setReportTarget(null); setTimeout(load, 500); }}
        />
      )}

      {/* Winner banner */}
      {withData.length > 0 && (
        <div className={`relative overflow-hidden rounded-2xl p-5 text-white shadow-md ${cheapestStyle.bg}`}>
          <div className="absolute -top-4 -right-4 w-20 h-20 rounded-full bg-white/10 pointer-events-none" />
          <div className="absolute -bottom-6 -left-2 w-16 h-16 rounded-full bg-white/10 pointer-events-none" />
          <div className="relative">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-white/80 text-xs font-bold uppercase tracking-widest">Najlepsza opcja</span>
              <span className="text-base">🏆</span>
              {totalReports > 0 && (
                <span className="text-xs bg-white/25 text-white font-bold px-2 py-0.5 rounded-full">
                  {totalReports} cen z półki
                </span>
              )}
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
                  {cheapest.found} z {items.length} produktów
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

      {/* Bar chart */}
      <div className="bg-white rounded-2xl shadow-sm p-5">
        <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-4">Porównanie cen koszyka</p>
        <div className="space-y-3">
          {results.map((store) => {
            const style = STORE_STYLE[store.name] ?? DEFAULT_STYLE;
            const isWinner = store.name === cheapest.name && store.found > 0;
            const noData = store.found === 0;
            const diff = store.total - cheapest.total;
            const widthPct = noData ? 5 : Math.max(20, (store.total / (mostExpensive.total || 1)) * 100);
            const hasPromos = store.prices.some(p => p.promo_price !== null);
            const hasApp = store.prices.some(p => p.app_price !== null);
            const hasReports = store.prices.some(p => p.reported_price !== null);
            const pricedRows = store.prices.filter(p => effectivePrice(p) !== null);
            const allEstimated = pricedRows.length > 0 && pricedRows.every(isEstimated);
            return (
              <div key={store.name}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-semibold text-gray-700 w-20 shrink-0 truncate">{store.name}</span>
                  <div className="flex items-center gap-1 ml-auto">
                    {allEstimated && <span className="text-[10px] bg-gray-100 text-gray-500 font-bold px-1.5 py-0.5 rounded-full leading-none" title="Ceny szacowane — sklep blokuje scraping">~ szac.</span>}
                    {hasReports && <span className="text-[10px] bg-green-100 text-green-700 font-bold px-1.5 py-0.5 rounded-full leading-none">z półki</span>}
                    {hasPromos && <span className="text-[10px] bg-orange-100 text-orange-600 font-bold px-1.5 py-0.5 rounded-full leading-none">PROMO</span>}
                    {hasApp && <span className="text-[10px] bg-blue-100 text-blue-600 font-bold px-1.5 py-0.5 rounded-full leading-none">APP</span>}
                    <span className={`text-xs font-black ${noData ? "text-gray-300" : isWinner ? "text-green-600" : "text-gray-500"}`}>
                      {noData ? "brak danych" : `${allEstimated ? "~" : ""}${fmt(store.total)} zł`}
                    </span>
                    {!noData && !isWinner && diff > 0.01 && (
                      <span className="text-[10px] text-red-400 font-bold">+{fmt(diff)}</span>
                    )}
                    {isWinner && <span className="text-[10px] text-green-600 font-bold">✓</span>}
                  </div>
                </div>
                <div className="bg-gray-100 rounded-full h-2 overflow-hidden">
                  <div className={`h-full rounded-full transition-all duration-700 ease-out ${noData ? "bg-gray-200" : style.bar}`} style={{ width: `${widthPct}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Store cards */}
      {results.map((store) => {
        const style = STORE_STYLE[store.name] ?? DEFAULT_STYLE;
        const isCheapest = store.name === cheapest.name && store.found > 0;
        const noData = store.found === 0;
        const diff = store.total - cheapest.total;
        const diffPct = cheapest.total > 0 ? (((store.total - cheapest.total) / cheapest.total) * 100).toFixed(0) : "0";
        const isOpen = expanded[store.name] ?? false;
        const promoCount = store.prices.filter(p => p.promo_price !== null).length;
        const reportCount = store.prices.filter(p => p.reported_price !== null).length;
        const storePricedRows = store.prices.filter(p => effectivePrice(p) !== null);
        const storeAllEstimated = storePricedRows.length > 0 && storePricedRows.every(isEstimated);
        const estimatedCount = store.prices.filter(p => effectivePrice(p) !== null && isEstimated(p)).length;

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
                      <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${style.tag}`}>Najtaniej</span>
                    )}
                    {storeAllEstimated && (
                      <span className="text-[10px] bg-gray-100 text-gray-500 font-bold px-1.5 py-0.5 rounded-full" title="Sklep blokuje scraping — ceny są szacowane">
                        ~ ceny szacowane
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {store.found}/{items.length} produktów
                    {promoCount > 0 && ` · ${promoCount} w promocji`}
                    {reportCount > 0 && ` · ${reportCount} z półki`}
                    {!storeAllEstimated && estimatedCount > 0 && ` · ${estimatedCount} szacowane`}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="text-right">
                  {noData ? (
                    <p className="font-bold text-sm text-gray-300 leading-tight">brak danych</p>
                  ) : (
                    <>
                      <p className="font-black text-xl text-gray-900 leading-tight">{storeAllEstimated ? "~" : ""}{fmt(store.total)} zł</p>
                      {!isCheapest && results.length > 1 && diff > 0.01 && (
                        <p className="text-xs text-red-400 font-semibold leading-tight">+{fmt(diff)} zł ({diffPct}%)</p>
                      )}
                    </>
                  )}
                </div>
                <span className="text-gray-300">{isOpen ? "▲" : "▼"}</span>
              </div>
            </button>

            {isOpen && (
              <div className="px-5 pb-5 border-t border-gray-50">
                <div className="space-y-0 mt-3">
                  {store.prices.map((p) => {
                    const ep = effectivePrice(p);
                    const isCheapestItem = ep !== null && ep === cheapestPerItem[p.item];
                    const hasPromo = p.promo_price !== null;
                    const hasApp = p.app_price !== null;
                    const hasReport = p.reported_price !== null;
                    const promoIsBetter = hasPromo && (!hasApp || p.promo_price! <= (p.app_price ?? Infinity));
                    const estimated = ep !== null && isEstimated(p);

                    return (
                      <div key={p.item} className="py-2.5 border-b border-gray-50 last:border-0">
                        <div className="flex justify-between items-start gap-2">
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-1.5 flex-wrap">
                              <span className="text-sm text-gray-700 font-medium truncate max-w-[160px]">{p.item}</span>
                              {p.unit && <span className="text-gray-300 text-xs">({p.unit})</span>}
                            </div>
                            <div className="flex items-center gap-1 mt-0.5 flex-wrap">
                              {hasReport && (
                                <span className="text-[10px] bg-green-100 text-green-700 font-bold px-1.5 py-0.5 rounded-full leading-none">
                                  z półki · {daysAgo(p.reported_at!)}
                                  {p.reported_city && ` · ${p.reported_city}`}
                                </span>
                              )}
                              {hasPromo && (
                                <span className="text-[10px] bg-orange-100 text-orange-600 font-bold px-1.5 py-0.5 rounded-full leading-none">
                                  {p.promo_label ?? "PROMO"}
                                </span>
                              )}
                              {hasApp && !hasReport && (
                                <span className="text-[10px] bg-blue-100 text-blue-600 font-bold px-1.5 py-0.5 rounded-full leading-none">
                                  z aplikacją
                                </span>
                              )}
                              {estimated && (
                                <span className="text-[10px] bg-gray-100 text-gray-500 font-bold px-1.5 py-0.5 rounded-full leading-none" title="Cena szacowana — sklep blokuje scraping">
                                  ~ szac.
                                </span>
                              )}
                            </div>
                          </div>

                          <div className="flex items-center gap-2 shrink-0">
                            {ep !== null ? (
                              <div className="flex flex-col items-end gap-0.5">
                                {(hasPromo || hasApp || hasReport) && p.price !== null && ep < p.price && (
                                  <span className="text-xs text-gray-300 line-through leading-none">{fmt(p.price)} zł</span>
                                )}
                                <span className={`font-black text-base leading-none ${
                                  promoIsBetter ? "text-orange-600" :
                                  hasApp ? "text-blue-600" :
                                  estimated ? "text-gray-400" :
                                  isCheapestItem ? "text-green-600" :
                                  "text-gray-700"
                                }`}>
                                  {estimated ? "~" : ""}{fmt(ep)} zł
                                </span>
                                {hasReport && (
                                  <span className="text-[10px] text-green-600 font-semibold leading-none" title={`Zgłoszono ${daysAgo(p.reported_at!)}${p.reported_city ? ` z ${p.reported_city}` : ""}`}>
                                    półka: {fmt(p.reported_price!)} zł
                                  </span>
                                )}
                              </div>
                            ) : hasReport ? (
                              <div className="flex flex-col items-end gap-0.5">
                                <span className="text-[10px] text-gray-400 leading-none">tylko z półki</span>
                                <span className="font-bold text-sm text-green-600 leading-none" title={`Zgłoszono ${daysAgo(p.reported_at!)}${p.reported_city ? ` z ${p.reported_city}` : ""}`}>
                                  ≈ {fmt(p.reported_price!)} zł
                                </span>
                              </div>
                            ) : (
                              <span className="text-gray-300 text-xs">brak</span>
                            )}
                            {p.product_id && p.store_id && (
                              <button
                                onClick={() => setReportTarget({ row: p, storeName: store.name })}
                                className="text-gray-300 hover:text-green-500 transition-colors text-lg leading-none"
                                title="Zgłoś cenę z półki"
                              >
                                ✏️
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {store.found < items.length && (
                  <div className="mt-3 bg-amber-50 rounded-xl px-3 py-2 text-xs text-amber-600 font-medium">
                    Brak danych dla {items.length - store.found} produktów
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}

      {/* Share + CTA */}
      <div className="bg-white rounded-2xl shadow-sm p-4 space-y-3">
        <button
          onClick={shareResults}
          className="w-full flex items-center justify-center gap-2 bg-gray-900 hover:bg-gray-800 active:scale-[0.98] transition-all text-white font-bold text-sm rounded-xl py-3"
        >
          <span>{shared ? "✓ Skopiowano!" : "Udostępnij wyniki"}</span>
          {!shared && <span>🔗</span>}
        </button>
        <p className="text-center text-xs text-gray-400 leading-relaxed">
          Widzisz inną cenę w sklepie? Kliknij ✏️ przy produkcie i zgłoś cenę z półki — pomożesz innym kupić taniej.
        </p>
      </div>

      <div className="bg-amber-50 border border-amber-100 rounded-xl px-4 py-3 space-y-1.5">
        <p className="text-xs text-amber-700 leading-relaxed">
          <span className="font-bold">Skąd są ceny?</span> Carrefour, Aldi, Netto, Kaufland — codzienna synchronizacja z gazetek online.
          Biedronka i Lidl blokują scraping — pokazujemy szacowane ceny rynkowe (oznaczone <span className="font-bold">~</span> i etykietą &quot;szac.&quot;).
        </p>
        <p className="text-xs text-amber-700 leading-relaxed">
          Ceny z półki <span className="font-bold text-green-700">(zielone)</span> są zgłaszane przez użytkowników i pokazywane informacyjnie — <span className="font-bold">nie wpływają na koszt koszyka</span>, żeby nikt nie zepsuł porównania.
          Zawsze sprawdź aktualną cenę w sklepie przed zakupem.
        </p>
      </div>

    </div>
  );
}
