"use client";

import { useState, useRef, useEffect } from "react";
import { Item } from "@/types";

interface Product {
  name: string;
  unit: string;
}

const COMMON_PRODUCTS: Product[] = [
  { name: "Mleko", unit: "1L" },
  { name: "Chleb", unit: "1 bochenek" },
  { name: "Masło", unit: "200g" },
  { name: "Jajka", unit: "10 szt." },
  { name: "Ser żółty", unit: "1kg" },
  { name: "Ser biały", unit: "250g" },
  { name: "Jogurt naturalny", unit: "400g" },
  { name: "Śmietana", unit: "200ml" },
  { name: "Kefir", unit: "1L" },
  { name: "Maślanka", unit: "1L" },
  { name: "Ryż", unit: "1kg" },
  { name: "Makaron", unit: "500g" },
  { name: "Mąka", unit: "1kg" },
  { name: "Cukier", unit: "1kg" },
  { name: "Sól", unit: "1kg" },
  { name: "Olej słonecznikowy", unit: "1L" },
  { name: "Oliwa z oliwek", unit: "500ml" },
  { name: "Ocet", unit: "500ml" },
  { name: "Ketchup", unit: "450g" },
  { name: "Musztarda", unit: "185g" },
  { name: "Majonez", unit: "400ml" },
  { name: "Pomidory", unit: "1kg" },
  { name: "Ogórki", unit: "1kg" },
  { name: "Papryka", unit: "1kg" },
  { name: "Cebula", unit: "1kg" },
  { name: "Czosnek", unit: "1 główka" },
  { name: "Ziemniaki", unit: "1kg" },
  { name: "Marchew", unit: "1kg" },
  { name: "Sałata", unit: "1 szt." },
  { name: "Szpinak", unit: "300g" },
  { name: "Brokuły", unit: "1 szt." },
  { name: "Kalafior", unit: "1 szt." },
  { name: "Kapusta", unit: "1kg" },
  { name: "Por", unit: "1 szt." },
  { name: "Pietruszka", unit: "1 pęczek" },
  { name: "Jabłka", unit: "1kg" },
  { name: "Banany", unit: "1kg" },
  { name: "Pomarańcze", unit: "1kg" },
  { name: "Cytryny", unit: "1kg" },
  { name: "Truskawki", unit: "500g" },
  { name: "Winogrona", unit: "1kg" },
  { name: "Gruszki", unit: "1kg" },
  { name: "Kurczak cały", unit: "1 szt. ~1.2kg" },
  { name: "Pierś z kurczaka", unit: "1kg" },
  { name: "Mielone wołowe", unit: "500g" },
  { name: "Kiełbasa", unit: "1kg" },
  { name: "Parówki", unit: "500g" },
  { name: "Szynka", unit: "300g" },
  { name: "Łosoś", unit: "1kg" },
  { name: "Tuńczyk w puszce", unit: "170g" },
  { name: "Makrela wędzona", unit: "250g" },
  { name: "Woda mineralna", unit: "1.5L" },
  { name: "Sok pomarańczowy", unit: "1L" },
  { name: "Sok jabłkowy", unit: "1L" },
  { name: "Cola", unit: "1.5L" },
  { name: "Herbata", unit: "100 torebek" },
  { name: "Kawa", unit: "250g" },
  { name: "Chipsy", unit: "150g" },
  { name: "Czekolada", unit: "100g" },
  { name: "Ciastka", unit: "200g" },
  { name: "Dżem", unit: "280g" },
  { name: "Miód", unit: "400g" },
  { name: "Płatki owsiane", unit: "500g" },
  { name: "Musli", unit: "500g" },
  { name: "Kasza gryczana", unit: "500g" },
  { name: "Kasza jaglana", unit: "500g" },
  { name: "Soczewica", unit: "500g" },
  { name: "Fasola", unit: "500g" },
  { name: "Proszek do prania", unit: "3kg" },
  { name: "Płyn do naczyń", unit: "1L" },
  { name: "Papier toaletowy", unit: "8 rolek" },
  { name: "Ręczniki papierowe", unit: "2 rolki" },
];

interface Props {
  items: Item[];
  setItems: (items: Item[]) => void;
  onSearch: () => void;
}

export default function ShoppingList({ items, setItems, onSearch }: Props) {
  const [input, setInput] = useState("");
  const [suggestions, setSuggestions] = useState<Product[]>([]);
  const [focused, setFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (input.trim().length === 0) {
      setSuggestions([]);
      return;
    }
    const q = input.toLowerCase();
    const matches = COMMON_PRODUCTS.filter(
      (p) =>
        p.name.toLowerCase().startsWith(q) &&
        !items.find((i) => i.name.toLowerCase() === p.name.toLowerCase())
    ).slice(0, 6);
    setSuggestions(matches);
  }, [input, items]);

  function addItem(product?: Product) {
    const name = product?.name ?? input.trim();
    const unit = product?.unit ?? "";
    if (!name) return;
    if (items.find((i) => i.name.toLowerCase() === name.toLowerCase())) return;
    setItems([...items, { id: crypto.randomUUID(), name, unit }]);
    setInput("");
    setSuggestions([]);
    inputRef.current?.focus();
  }

  function removeItem(id: string) {
    setItems(items.filter((i) => i.id !== id));
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "Enter") addItem();
    if (e.key === "Escape") setSuggestions([]);
  }

  return (
    <div className="bg-white rounded-2xl shadow-sm p-5 mb-4">
      <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-widest mb-4">
        Twoja lista
      </h2>

      <div className="relative mb-4">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            className="flex-1 border border-gray-200 rounded-xl px-4 py-3 text-base text-gray-900 placeholder-gray-400 focus:outline-none focus:border-green-400 transition-colors"
            placeholder="Np. mleko, chleb, jajka..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
            onFocus={() => setFocused(true)}
            onBlur={() => setTimeout(() => setFocused(false), 150)}
            autoComplete="off"
          />
          <button
            onClick={() => addItem()}
            className="bg-green-500 hover:bg-green-600 text-white rounded-xl px-4 py-3 text-xl font-bold transition-colors"
          >
            +
          </button>
        </div>

        {focused && suggestions.length > 0 && (
          <ul className="absolute left-0 right-10 top-full mt-1 bg-white border border-gray-100 rounded-xl shadow-lg z-10 overflow-hidden">
            {suggestions.map((s) => (
              <li
                key={s.name}
                onMouseDown={() => addItem(s)}
                className="flex items-center justify-between px-4 py-3 hover:bg-green-50 cursor-pointer border-b border-gray-50 last:border-0 transition-colors"
              >
                <span className="text-gray-800 text-sm">{s.name}</span>
                <span className="text-gray-400 text-xs ml-2">{s.unit}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {items.length === 0 && (
        <p className="text-gray-400 text-sm text-center py-4">
          Dodaj produkty, żeby porównać ceny
        </p>
      )}

      <ul className="space-y-2 mb-4">
        {items.map((item) => (
          <li
            key={item.id}
            className="flex items-center justify-between bg-gray-50 rounded-xl px-4 py-3"
          >
            <div>
              <span className="text-gray-800 text-sm">{item.name}</span>
              {item.unit && (
                <span className="text-gray-400 text-xs ml-2">{item.unit}</span>
              )}
            </div>
            <button
              onClick={() => removeItem(item.id)}
              className="text-gray-300 hover:text-red-400 transition-colors text-lg leading-none"
            >
              ×
            </button>
          </li>
        ))}
      </ul>

      {items.length > 0 && (
        <button
          onClick={onSearch}
          className="w-full bg-green-500 hover:bg-green-600 text-white font-semibold rounded-xl py-4 transition-colors text-base"
        >
          Porównaj ceny →
        </button>
      )}
    </div>
  );
}
