"use client";

import { useState, useRef } from "react";

interface Product { id: number; name: string; unit: string; }
interface Store { id: number; name: string; }

export default function AdminPage() {
  const [password, setPassword] = useState("");
  const [authed, setAuthed] = useState(false);
  const [authError, setAuthError] = useState(false);

  const [products, setProducts] = useState<Product[]>([]);
  const [stores, setStores] = useState<Store[]>([]);
  const [priceMap, setPriceMap] = useState<Map<string, number>>(new Map());
  const [edits, setEdits] = useState<Map<string, number>>(new Map());
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [savedCount, setSavedCount] = useState(0);
  const [search, setSearch] = useState("");

  const token = useRef("");

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
    const data = await res.json();
    setProducts(data.products ?? []);
    setStores(data.stores ?? []);
    const map = new Map<string, number>();
    for (const p of data.prices ?? []) {
      map.set(`${p.product_id}-${p.store_id}`, p.price);
    }
    setPriceMap(map);
    setAuthed(true);
    setLoading(false);
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
    const updates = Array.from(edits.entries()).map(([key, price]) => {
      const [product_id, store_id] = key.split("-").map(Number);
      return { product_id, store_id, price };
    });
    const res = await fetch("/api/admin/prices", {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token.current}`,
      },
      body: JSON.stringify({ updates }),
    });
    if (res.ok) {
      setPriceMap((prev) => {
        const m = new Map(prev);
        for (const [k, v] of edits) m.set(k, v);
        return m;
      });
      setSavedCount(edits.size);
      setEdits(new Map());
      setTimeout(() => setSavedCount(0), 3000);
    }
    setSaving(false);
  }

  const filtered = search
    ? products.filter((p) => p.name.toLowerCase().includes(search.toLowerCase()))
    : products;

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

  return (
    <main className="min-h-screen bg-[#f0f0eb] p-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-black text-gray-900">Panel cen</h1>
            <p className="text-gray-400 text-sm">
              {products.length} produktów · {stores.length} sklepów
            </p>
          </div>
          <div className="flex items-center gap-3">
            {savedCount > 0 && (
              <span className="text-green-600 text-sm font-semibold animate-pulse">
                ✓ Zapisano {savedCount}
              </span>
            )}
            <button
              onClick={saveAll}
              disabled={edits.size === 0 || saving}
              className="bg-green-500 hover:bg-green-600 disabled:opacity-40 text-white font-bold px-5 py-2.5 rounded-xl text-sm transition-all"
            >
              {saving ? "Zapisywanie..." : edits.size > 0 ? `Zapisz ${edits.size} zmian` : "Brak zmian"}
            </button>
          </div>
        </div>

        {/* Search */}
        <input
          type="text"
          placeholder="Szukaj produktu..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-green-500 mb-3 bg-white"
        />

        <p className="text-xs text-amber-600 mb-2">
          Żółte pola = niezapisane zmiany · Kliknij &quot;Zapisz&quot; żeby zatwierdzić
        </p>

        {/* Table */}
        <div className="bg-white rounded-2xl shadow-sm overflow-auto">
          <table className="w-full text-sm" style={{ minWidth: `${180 + 48 + stores.length * 110}px` }}>
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="text-left px-4 py-3 font-semibold text-gray-500 sticky left-0 bg-gray-50 min-w-[180px]">
                  Produkt
                </th>
                <th className="text-left px-3 py-3 font-semibold text-gray-500 w-12 min-w-[48px]">
                  Jedn.
                </th>
                {stores.map((s) => (
                  <th key={s.id} className="text-center px-2 py-3 font-semibold text-gray-500 w-[110px]">
                    {s.name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((product, i) => (
                <tr
                  key={product.id}
                  className={`border-b border-gray-50 ${i % 2 === 0 ? "" : "bg-gray-50/40"}`}
                >
                  <td
                    className={`px-4 py-2 font-medium text-gray-800 sticky left-0 ${
                      i % 2 === 0 ? "bg-white" : "bg-gray-50/40"
                    }`}
                  >
                    {product.name}
                  </td>
                  <td className="px-3 py-2 text-gray-400 text-xs">{product.unit}</td>
                  {stores.map((store) => {
                    const key = `${product.id}-${store.id}`;
                    const current = priceMap.get(key);
                    const isDirty = edits.has(key);
                    const displayValue = isDirty ? edits.get(key) : current;
                    return (
                      <td key={store.id} className="px-2 py-1.5 text-center">
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          value={displayValue ?? ""}
                          placeholder="—"
                          onChange={(e) => handlePriceChange(product.id, store.id, e.target.value)}
                          className={`w-[90px] text-center text-sm border rounded-lg px-2 py-1 outline-none focus:ring-1 focus:ring-green-500 transition-colors ${
                            isDirty
                              ? "border-amber-300 bg-amber-50"
                              : "border-gray-100 bg-transparent hover:border-gray-300"
                          }`}
                        />
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="text-center text-xs text-gray-300 mt-4">
          Showing {filtered.length} of {products.length} products
        </p>
      </div>
    </main>
  );
}
