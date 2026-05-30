"use client";

import { useState, useRef } from "react";

interface Product { id: number; name: string; unit: string; }
interface Store { id: number; name: string; }
interface PriceMeta { source: "scraped" | "estimated" | string; scraped_at: string | null; }

type EditMode = "price" | "app_price";

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("pl-PL", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function timeAgo(iso: string | null): string {
  if (!iso) return "nigdy";
  const diffMs = Date.now() - new Date(iso).getTime();
  const h = Math.floor(diffMs / 3_600_000);
  if (h < 1) return "<1h temu";
  if (h < 24) return `${h}h temu`;
  return `${Math.floor(h / 24)}d temu`;
}

export default function AdminPage() {
  const [password, setPassword] = useState("");
  const [authed, setAuthed] = useState(false);
  const [authError, setAuthError] = useState(false);

  const [products, setProducts] = useState<Product[]>([]);
  const [stores, setStores] = useState<Store[]>([]);
  const [priceMap, setPriceMap] = useState<Map<string, number>>(new Map());
  const [appPriceMap, setAppPriceMap] = useState<Map<string, number>>(new Map());
  const [metaMap, setMetaMap] = useState<Map<string, PriceMeta>>(new Map());
  const [edits, setEdits] = useState<Map<string, number>>(new Map());
  const [editMode, setEditMode] = useState<EditMode>("price");

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<string | null>(null);
  const [savedCount, setSavedCount] = useState(0);
  const [search, setSearch] = useState("");

  const token = useRef("");

  async function loadData() {
    setLoading(true);
    const res = await fetch("/api/admin/products", {
      headers: { Authorization: `Bearer ${token.current}` },
    });
    if (!res.ok) { setLoading(false); return; }
    const data = await res.json();
    setProducts(data.products ?? []);
    setStores(data.stores ?? []);
    const pMap = new Map<string, number>();
    const aMap = new Map<string, number>();
    const mMap = new Map<string, PriceMeta>();
    for (const p of data.prices ?? []) {
      const key = `${p.product_id}-${p.store_id}`;
      if (p.price != null) pMap.set(key, p.price);
      if (p.app_price != null) aMap.set(key, p.app_price);
      mMap.set(key, { source: p.source ?? "estimated", scraped_at: p.scraped_at ?? null });
    }
    setPriceMap(pMap);
    setAppPriceMap(aMap);
    setMetaMap(mMap);
    setLoading(false);
  }

  async function login(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setAuthError(false);
    const res = await fetch("/api/admin/products", {
      headers: { Authorization: `Bearer ${password}` },
    });
    if (!res.ok) {
      setAuthError(true);
      setLoading(false);
      return;
    }
    token.current = password;
    await loadData();
    setAuthed(true);
  }

  function currentMap(): Map<string, number> {
    return editMode === "price" ? priceMap : appPriceMap;
  }

  function handlePriceChange(productId: number, storeId: number, value: string) {
    const num = parseFloat(value.replace(",", "."));
    const key = `${productId}-${storeId}`;
    if (!isNaN(num) && num > 0) {
      setEdits((prev) => new Map(prev).set(key, Math.round(num * 100) / 100));
    } else if (value === "") {
      setEdits((prev) => { const m = new Map(prev); m.delete(key); return m; });
    }
  }

  async function saveAll() {
    if (edits.size === 0) return;
    setSaving(true);

    const field = editMode === "price" ? "price" : "app_price";
    const updates = Array.from(edits.entries()).map(([key, val]) => {
      const [product_id, store_id] = key.split("-").map(Number);
      return { product_id, store_id, [field]: val };
    });

    const res = await fetch("/api/admin/prices", {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token.current}`,
      },
      body: JSON.stringify({ updates, field }),
    });

    if (res.ok) {
      if (editMode === "price") {
        setPriceMap((prev) => {
          const m = new Map(prev);
          for (const [k, v] of edits) m.set(k, v);
          return m;
        });
      } else {
        setAppPriceMap((prev) => {
          const m = new Map(prev);
          for (const [k, v] of edits) m.set(k, v);
          return m;
        });
      }
      setSavedCount(edits.size);
      setEdits(new Map());
      setTimeout(() => setSavedCount(0), 3000);
    }
    setSaving(false);
  }

  function switchMode(mode: EditMode) {
    if (edits.size > 0 && !confirm("Masz niezapisane zmiany. Odrzucić?")) return;
    setEditMode(mode);
    setEdits(new Map());
  }

  async function triggerSync() {
    setSyncing(true);
    setSyncResult(null);
    try {
      const res = await fetch("/api/admin/sync", {
        method: "POST",
        headers: { Authorization: `Bearer ${token.current}` },
      });
      const data = await res.json();
      if (data.ok) {
        const total = Object.values(
          data.report as Record<string, { updated: number; promos: number }>
        ).reduce((sum, s) => sum + s.updated + s.promos, 0);
        setSyncResult(`✓ Zaktualizowano ${total} cen`);
      } else {
        setSyncResult(`Błąd: ${data.error ?? "nieznany"}`);
      }
    } catch {
      setSyncResult("Błąd połączenia");
    }
    setSyncing(false);
  }

  const filtered = search
    ? products.filter((p) => p.name.toLowerCase().includes(search.toLowerCase()))
    : products;

  // Stores that have loyalty apps (show in app_price mode)
  const APP_STORES = ["Biedronka", "Lidl", "Kaufland"];

  if (!authed) {
    return (
      <main className="min-h-screen bg-[#f0f0eb] flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-sm p-8 w-full max-w-sm">
          <h1 className="text-2xl font-black text-gray-900 mb-1">Admin</h1>
          <p className="text-gray-400 text-sm mb-6">Panel zarządzania cenami</p>
          <form onSubmit={login} className="space-y-3">
            <input
              type="password"
              placeholder="Hasło"
              value={password}
              onChange={(e) => { setPassword(e.target.value); setAuthError(false); }}
              className={`w-full border rounded-xl px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-green-500 ${
                authError ? "border-red-300 bg-red-50" : "border-gray-200"
              }`}
            />
            {authError && <p className="text-red-500 text-xs">Nieprawidłowe hasło</p>}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-green-500 hover:bg-green-600 disabled:opacity-60 text-white font-bold py-3 rounded-xl text-sm transition-all"
            >
              {loading ? "Ładowanie..." : "Zaloguj"}
            </button>
          </form>
        </div>
      </main>
    );
  }

  const activeMap = currentMap();

  // Per-store scrape status
  const storeStats = stores.map((store) => {
    let scraped = 0;
    let estimated = 0;
    let latestScrape: string | null = null;
    for (const product of products) {
      const meta = metaMap.get(`${product.id}-${store.id}`);
      if (!meta) continue;
      if (meta.source === "scraped") {
        scraped++;
        if (meta.scraped_at && (!latestScrape || meta.scraped_at > latestScrape)) {
          latestScrape = meta.scraped_at;
        }
      } else {
        estimated++;
      }
    }
    const total = scraped + estimated;
    const pct = total > 0 ? Math.round((scraped / total) * 100) : 0;
    let status: "good" | "partial" | "blocked";
    if (pct >= 50) status = "good";
    else if (pct > 0) status = "partial";
    else status = "blocked";
    return { name: store.name, scraped, estimated, total, pct, latestScrape, status };
  });

  return (
    <main className="min-h-screen bg-[#f0f0eb] p-4">
      <div className="max-w-7xl mx-auto">

        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div>
            <h1 className="text-2xl font-black text-gray-900">Panel cen</h1>
            <p className="text-gray-400 text-sm">
              {products.length} produktów · {stores.length} sklepów ·{" "}
              <a href="/admin/events" className="text-green-600 hover:underline font-semibold">
                Analityka →
              </a>
            </p>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            {savedCount > 0 && (
              <span className="text-green-600 text-sm font-semibold">✓ Zapisano {savedCount}</span>
            )}
            {syncResult && (
              <span className={`text-sm font-semibold ${syncResult.startsWith("✓") ? "text-blue-600" : "text-red-500"}`}>
                {syncResult}
              </span>
            )}
            <button
              onClick={loadData}
              disabled={loading}
              className="bg-gray-500 hover:bg-gray-600 disabled:opacity-40 text-white font-bold px-4 py-2.5 rounded-xl text-sm transition-all"
            >
              {loading ? "Ładowanie..." : "Odśwież"}
            </button>
            <button
              onClick={triggerSync}
              disabled={syncing}
              className="bg-blue-500 hover:bg-blue-600 disabled:opacity-40 text-white font-bold px-4 py-2.5 rounded-xl text-sm transition-all"
            >
              {syncing ? "Syncowanie..." : "Sync ceny"}
            </button>
            <button
              onClick={saveAll}
              disabled={edits.size === 0 || saving}
              className="bg-green-500 hover:bg-green-600 disabled:opacity-40 text-white font-bold px-5 py-2.5 rounded-xl text-sm transition-all"
            >
              {saving ? "Zapisywanie..." : edits.size > 0 ? `Zapisz ${edits.size} zmian` : "Brak zmian"}
            </button>
          </div>
        </div>

        {/* Store scrape status */}
        {storeStats.length > 0 && (
          <div className="bg-white rounded-2xl shadow-sm p-4 mb-4">
            <div className="flex items-center justify-between mb-3">
              <div>
                <p className="text-xs font-bold text-gray-400 uppercase tracking-widest">Status scrapowania</p>
                <p className="text-xs text-gray-400 mt-0.5">
                  Ile cen pochodzi z prawdziwego scrapowania vs szacunków
                </p>
              </div>
              <div className="text-right">
                <p className="text-2xl font-black text-gray-900 leading-none">
                  {storeStats.reduce((s, x) => s + x.scraped, 0)}
                </p>
                <p className="text-xs text-gray-400">scraped / {storeStats.reduce((s, x) => s + x.total, 0)}</p>
              </div>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-2">
              {storeStats.map((s) => {
                const color =
                  s.status === "good" ? "bg-green-500" :
                  s.status === "partial" ? "bg-amber-400" :
                  "bg-gray-300";
                const textColor =
                  s.status === "good" ? "text-green-600" :
                  s.status === "partial" ? "text-amber-600" :
                  "text-gray-400";
                return (
                  <div key={s.name} className="border border-gray-100 rounded-xl p-3">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-bold text-sm text-gray-800 truncate">{s.name}</span>
                      <span className={`w-2 h-2 rounded-full ${color} shrink-0`} title={s.status} />
                    </div>
                    <p className={`text-lg font-black leading-none ${textColor}`}>{s.pct}%</p>
                    <p className="text-[10px] text-gray-400 mt-1 leading-tight">
                      {s.scraped} scraped<br/>
                      {s.estimated} szac.
                    </p>
                    <p className="text-[10px] text-gray-300 mt-1">
                      {s.latestScrape ? timeAgo(s.latestScrape) : "nigdy"}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Mode toggle + Search */}
        <div className="flex gap-3 mb-3">
          <div className="flex bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
            <button
              onClick={() => switchMode("price")}
              className={`px-4 py-2.5 text-sm font-semibold transition-colors ${
                editMode === "price" ? "bg-green-500 text-white" : "text-gray-500 hover:bg-gray-50"
              }`}
            >
              Ceny regularne
            </button>
            <button
              onClick={() => switchMode("app_price")}
              className={`px-4 py-2.5 text-sm font-semibold transition-colors ${
                editMode === "app_price" ? "bg-blue-500 text-white" : "text-gray-500 hover:bg-gray-50"
              }`}
            >
              Z aplikacją
            </button>
          </div>
          <input
            type="text"
            placeholder="Szukaj produktu..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="flex-1 border border-gray-200 rounded-xl px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-green-500 bg-white shadow-sm"
          />
        </div>

        {editMode === "app_price" && (
          <p className="text-xs text-blue-600 mb-2 bg-blue-50 rounded-xl px-4 py-2">
            Tryb cen z aplikacją — wypełnij ceny dla Biedronka (app), Lidl Plus, Kaufland Card
          </p>
        )}

        <div className="flex flex-wrap items-center gap-3 mb-2 text-xs">
          <span className="text-amber-600">Żółte = niezapisane zmiany</span>
          {editMode === "price" && (
            <>
              <span className="flex items-center gap-1 text-green-600">
                <span className="w-2 h-2 rounded-full bg-green-500" /> scraped
              </span>
              <span className="flex items-center gap-1 text-gray-400">
                <span className="w-2 h-2 rounded-full bg-gray-300" /> szacowane
              </span>
            </>
          )}
          <span className="text-gray-400">· Hover na pole = data ostatniego scrapowania</span>
        </div>

        {/* Table */}
        <div className="bg-white rounded-2xl shadow-sm overflow-auto">
          <table className="w-full text-sm" style={{ minWidth: `${200 + 48 + stores.length * 110}px` }}>
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="text-left px-4 py-3 font-semibold text-gray-500 sticky left-0 bg-gray-50 min-w-[200px]">
                  Produkt
                </th>
                <th className="text-left px-3 py-3 font-semibold text-gray-500 w-12">Jedn.</th>
                {stores.map((s) => {
                  const isAppStore = APP_STORES.includes(s.name);
                  return (
                    <th key={s.id} className="text-center px-2 py-3 font-semibold text-gray-500 w-[110px]">
                      <span>{s.name}</span>
                      {editMode === "app_price" && isAppStore && (
                        <span className="block text-xs text-blue-400 font-normal">z app</span>
                      )}
                      {editMode === "app_price" && !isAppStore && (
                        <span className="block text-xs text-gray-300 font-normal">brak app</span>
                      )}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {filtered.map((product, i) => (
                <tr
                  key={product.id}
                  className={`border-b border-gray-50 ${i % 2 === 0 ? "" : "bg-gray-50/40"}`}
                >
                  <td className={`px-4 py-2 font-medium text-gray-800 sticky left-0 ${i % 2 === 0 ? "bg-white" : "bg-gray-50/40"}`}>
                    {product.name}
                  </td>
                  <td className="px-3 py-2 text-gray-400 text-xs">{product.unit}</td>
                  {stores.map((store) => {
                    const key = `${product.id}-${store.id}`;
                    const isAppStore = APP_STORES.includes(store.name);
                    const disabled = editMode === "app_price" && !isAppStore;
                    const current = activeMap.get(key);
                    const isDirty = edits.has(key);
                    const displayValue = isDirty ? edits.get(key) : current;
                    const meta = metaMap.get(key);
                    const isScraped = editMode === "price" && meta?.source === "scraped";
                    const isEstimate = editMode === "price" && meta && meta.source !== "scraped";

                    return (
                      <td key={store.id} className="px-2 py-1.5 text-center">
                        <div className="relative inline-block">
                          <input
                            type="number"
                            step="0.01"
                            min="0"
                            value={disabled ? "" : (displayValue ?? "")}
                            placeholder={disabled ? "—" : "—"}
                            disabled={disabled}
                            onChange={(e) => handlePriceChange(product.id, store.id, e.target.value)}
                            title={
                              disabled ? "Brak aplikacji" :
                              isDirty ? "Niezapisana zmiana" :
                              isScraped ? `Scraped · ${fmtDate(meta!.scraped_at)}` :
                              isEstimate ? "Szacowana cena" : ""
                            }
                            className={`w-[90px] text-center text-sm border rounded-lg px-2 py-1 outline-none transition-colors ${
                              disabled
                                ? "bg-gray-50 border-gray-100 text-gray-200 cursor-not-allowed"
                                : isDirty
                                ? "border-amber-300 bg-amber-50 focus:ring-1 focus:ring-amber-400"
                                : isScraped
                                ? "border-green-200 bg-green-50/40 hover:border-green-300 focus:ring-1 focus:ring-green-500"
                                : isEstimate
                                ? "border-gray-100 bg-transparent text-gray-400 hover:border-gray-300 focus:ring-1 focus:ring-green-500"
                                : "border-gray-100 bg-transparent hover:border-gray-300 focus:ring-1 focus:ring-green-500"
                            }`}
                          />
                          {!disabled && editMode === "price" && current !== undefined && (
                            <span
                              className={`absolute -top-1 -right-1 w-2 h-2 rounded-full ${
                                isScraped ? "bg-green-500" : "bg-gray-300"
                              }`}
                              title={isScraped ? "Scraped" : "Szacowana"}
                            />
                          )}
                        </div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="text-center text-xs text-gray-300 mt-4">
          {filtered.length} z {products.length} produktów
        </p>
      </div>
    </main>
  );
}
