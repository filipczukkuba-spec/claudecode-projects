"use client";

import { useState } from "react";
import { Item } from "@/types";

interface Props {
  items: Item[];
  setItems: (items: Item[]) => void;
  onSearch: () => void;
}

export default function ShoppingList({ items, setItems, onSearch }: Props) {
  const [input, setInput] = useState("");

  function addItem() {
    const trimmed = input.trim();
    if (!trimmed) return;
    setItems([...items, { id: crypto.randomUUID(), name: trimmed }]);
    setInput("");
  }

  function removeItem(id: string) {
    setItems(items.filter((i) => i.id !== id));
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "Enter") addItem();
  }

  return (
    <div className="bg-white rounded-2xl shadow-sm p-5 mb-4">
      <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-widest mb-4">
        Twoja lista
      </h2>

      <div className="flex gap-2 mb-4">
        <input
          className="flex-1 border border-gray-200 rounded-xl px-4 py-3 text-base focus:outline-none focus:border-green-400 transition-colors"
          placeholder="Np. mleko, chleb, jajka..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
        />
        <button
          onClick={addItem}
          className="bg-green-500 hover:bg-green-600 text-white rounded-xl px-4 py-3 text-xl font-bold transition-colors"
        >
          +
        </button>
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
