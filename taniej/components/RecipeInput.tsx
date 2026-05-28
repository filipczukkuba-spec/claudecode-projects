"use client";

import { useState } from "react";
import { Item } from "@/types";

const COMMON_PRODUCTS = [
  { name: "Mleko", unit: "1L" }, { name: "Chleb", unit: "1 bochenek" },
  { name: "Masło", unit: "200g" }, { name: "Jajka", unit: "10 szt." },
  { name: "Ser żółty", unit: "1kg" }, { name: "Ser biały", unit: "250g" },
  { name: "Jogurt naturalny", unit: "400g" }, { name: "Śmietana", unit: "200ml" },
  { name: "Ryż", unit: "1kg" }, { name: "Makaron", unit: "500g" },
  { name: "Mąka", unit: "1kg" }, { name: "Cukier", unit: "1kg" },
  { name: "Sól", unit: "1kg" }, { name: "Olej słonecznikowy", unit: "1L" },
  { name: "Ketchup", unit: "450g" }, { name: "Majonez", unit: "400ml" },
  { name: "Pomidory", unit: "1kg" }, { name: "Cebula", unit: "1kg" },
  { name: "Ziemniaki", unit: "1kg" }, { name: "Marchew", unit: "1kg" },
  { name: "Jabłka", unit: "1kg" }, { name: "Banany", unit: "1kg" },
  { name: "Pierś z kurczaka", unit: "1kg" }, { name: "Kiełbasa", unit: "1kg" },
  { name: "Parówki", unit: "500g" }, { name: "Tuńczyk w puszce", unit: "170g" },
  { name: "Woda mineralna", unit: "1.5L" }, { name: "Sok pomarańczowy", unit: "1L" },
  { name: "Płatki owsiane", unit: "500g" }, { name: "Płyn do naczyń", unit: "1L" },
  { name: "Papier toaletowy", unit: "8 rolek" },
];

interface Props {
  items: Item[];
  setItems: (items: Item[]) => void;
}

export default function RecipeInput({ items, setItems }: Props) {
  const [open, setOpen] = useState(false);
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [added, setAdded] = useState<string[]>([]);

  async function handleExtract() {
    if (!url.trim()) return;
    setLoading(true);
    setError("");
    setAdded([]);

    try {
      const res = await fetch("/api/recipe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim() }),
      });
      const data = await res.json();
      if (!res.ok) { setError(data.error || "Błąd podczas pobierania przepisu"); return; }

      const newItems: Item[] = [];
      const addedNames: string[] = [];

      for (const ingredient of data.ingredients as string[]) {
        if (items.find((i) => i.name.toLowerCase() === ingredient.toLowerCase())) continue;
        if (newItems.find((i) => i.name.toLowerCase() === ingredient.toLowerCase())) continue;

        const matched = COMMON_PRODUCTS.find(
          (p) =>
            p.name.toLowerCase() === ingredient.toLowerCase() ||
            ingredient.toLowerCase().includes(p.name.toLowerCase()) ||
            p.name.toLowerCase().includes(ingredient.toLowerCase())
        );

        newItems.push({ id: crypto.randomUUID(), name: matched?.name ?? ingredient, unit: matched?.unit ?? "" });
        addedNames.push(matched?.name ?? ingredient);
      }

      setItems([...items, ...newItems]);
      setAdded(addedNames);
      setUrl("");
    } catch {
      setError("Nie udało się połączyć z serwerem");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-white rounded-2xl shadow-sm mb-4 overflow-hidden">
      <button
        className="w-full flex items-center justify-between p-5 text-left"
        onClick={() => setOpen((o) => !o)}
      >
        <div>
          <p className="text-sm font-semibold text-gray-800">Wklej przepis z internetu</p>
          <p className="text-xs text-gray-400 mt-0.5">Automatycznie wyciągniemy składniki</p>
        </div>
        <span className="text-gray-300 text-sm ml-3">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="px-5 pb-5 border-t border-gray-50">
          <div className="flex gap-2 mt-4">
            <input
              className="flex-1 border border-gray-200 rounded-xl px-4 py-3 text-base text-gray-900 placeholder-gray-400 focus:outline-none focus:border-green-400 transition-colors"
              placeholder="https://..."
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleExtract()}
              disabled={loading}
              type="url"
              inputMode="url"
            />
            <button
              onClick={handleExtract}
              disabled={loading || !url.trim()}
              className="bg-green-500 hover:bg-green-600 active:bg-green-700 disabled:bg-gray-100 disabled:text-gray-400 text-white rounded-xl px-4 py-3 text-sm font-semibold transition-all whitespace-nowrap"
            >
              {loading ? "..." : "Dodaj"}
            </button>
          </div>

          {error && <p className="text-red-500 text-xs mt-2">{error}</p>}

          {added.length > 0 && (
            <div className="mt-3 bg-green-50 rounded-xl p-3">
              <p className="text-green-700 text-xs font-medium">
                Dodano {added.length} składnik{added.length === 1 ? "" : added.length < 5 ? "i" : "ów"}
              </p>
              <p className="text-green-600 text-xs mt-0.5">{added.join(", ")}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
