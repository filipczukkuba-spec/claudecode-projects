"use client";

import { useState, useRef, useEffect } from "react";
import { Item } from "@/types";

const COMMON_PRODUCTS = [
  "Mleko", "Chleb", "Masło", "Jajka", "Ser żółty", "Ser biały", "Jogurt naturalny",
  "Śmietana", "Kefir", "Maślanka", "Ryż", "Makaron", "Mąka", "Cukier", "Sól",
  "Olej słonecznikowy", "Oliwa z oliwek", "Ocet", "Ketchup", "Musztarda", "Majonez",
  "Pomidory", "Ogórki", "Papryka", "Cebula", "Czosnek", "Ziemniaki", "Marchew",
  "Sałata", "Szpinak", "Brokuły", "Kalafior", "Kapusta", "Por", "Pietruszka",
  "Jabłka", "Banany", "Pomarańcze", "Cytryny", "Truskawki", "Winogrona", "Gruszki",
  "Kurczak", "Pierś z kurczaka", "Mielone wołowe", "Kiełbasa", "Parówki", "Szynka",
  "Łosoś", "Tuńczyk w puszce", "Makrela wędzona", "Krewetki",
  "Woda mineralna", "Sok pomarańczowy", "Sok jabłkowy", "Cola", "Herbata", "Kawa",
  "Chipsy", "Paluszki", "Czekolada", "Wafelki", "Ciastka", "Dżem", "Miód",
  "Płatki owsiane", "Musli", "Kasza gryczana", "Kasza jaglana", "Soczewica", "Fasola",
  "Proszek do prania", "Płyn do naczyń", "Papier toaletowy", "Ręczniki papierowe",
];

interface Props {
  items: Item[];
  setItems: (items: Item[]) => void;
  onSearch: () => void;
}

export default function ShoppingList({ items, setItems, onSearch }: Props) {
  const [input, setInput] = useState("");
  const [suggestions, setSuggestions] = useState<string[]>([]);
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
        p.toLowerCase().startsWith(q) &&
        !items.find((i) => i.name.toLowerCase() === p.toLowerCase())
    ).slice(0, 6);
    setSuggestions(matches);
  }, [input, items]);

  function addItem(name?: string) {
    const value = (name ?? input).trim();
    if (!value) return;
    if (items.find((i) => i.name.toLowerCase() === value.toLowerCase())) return;
    setItems([...items, { id: crypto.randomUUID(), name: value }]);
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
                key={s}
                onMouseDown={() => addItem(s)}
                className="px-4 py-3 text-gray-800 hover:bg-green-50 cursor-pointer text-sm border-b border-gray-50 last:border-0 transition-colors"
              >
                {s}
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
            <span className="text-gray-800">{item.name}</span>
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
