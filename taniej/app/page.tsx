"use client";

import { useState } from "react";
import ShoppingList from "@/components/ShoppingList";
import StoreComparison from "@/components/StoreComparison";
import { Item } from "@/types";

export default function Home() {
  const [items, setItems] = useState<Item[]>([]);
  const [searched, setSearched] = useState(false);

  return (
    <main className="min-h-screen bg-[#f5f5f0] font-sans">
      <div className="max-w-md mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-green-600 tracking-tight">taniej.</h1>
          <p className="text-sm text-gray-500 mt-1">Gdzie kupisz taniej? Sprawdź.</p>
        </div>

        <ShoppingList items={items} setItems={setItems} onSearch={() => setSearched(true)} />

        {searched && items.length > 0 && (
          <StoreComparison items={items} />
        )}
      </div>
    </main>
  );
}
