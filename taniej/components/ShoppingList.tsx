"use client";

import { useState, useRef, useEffect } from "react";
import { Item } from "@/types";

interface Product {
  name: string;
  unit: string;
}

const COMMON_PRODUCTS: Product[] = [
  { name: "Mleko", unit: "1L" },
  { name: "Mleko sojowe", unit: "1L" },
  { name: "Mleko owsiane", unit: "1L" },
  { name: "Mleko migdałowe", unit: "1L" },
  { name: "Chleb", unit: "1 bochenek" },
  { name: "Chleb razowy", unit: "500g" },
  { name: "Chleb tostowy", unit: "500g" },
  { name: "Bagietka", unit: "1 szt." },
  { name: "Bułki", unit: "5 szt." },
  { name: "Rogaliki", unit: "6 szt." },
  { name: "Pumpernikiel", unit: "500g" },
  { name: "Masło", unit: "200g" },
  { name: "Masło orzechowe", unit: "350g" },
  { name: "Jajka", unit: "10 szt." },
  { name: "Białka jajek", unit: "500ml" },
  { name: "Ser żółty", unit: "1kg" },
  { name: "Ser biały", unit: "250g" },
  { name: "Ser Gouda", unit: "200g" },
  { name: "Ser Edam", unit: "200g" },
  { name: "Ser feta", unit: "200g" },
  { name: "Mozzarella", unit: "125g" },
  { name: "Parmezan", unit: "100g" },
  { name: "Twaróg", unit: "200g" },
  { name: "Serek wiejski", unit: "200g" },
  { name: "Serek Philadelphia", unit: "150g" },
  { name: "Jogurt naturalny", unit: "400g" },
  { name: "Jogurt grecki", unit: "400g" },
  { name: "Śmietana", unit: "200ml" },
  { name: "Śmietana 18%", unit: "200ml" },
  { name: "Śmietana 30%", unit: "200ml" },
  { name: "Śmietanka kremówka", unit: "200ml" },
  { name: "Śmietanka do kawy", unit: "200ml" },
  { name: "Kefir", unit: "1L" },
  { name: "Maślanka", unit: "1L" },
  { name: "Ryż", unit: "1kg" },
  { name: "Ryż brązowy", unit: "1kg" },
  { name: "Ryż jaśminowy", unit: "1kg" },
  { name: "Ryż basmati", unit: "1kg" },
  { name: "Makaron", unit: "500g" },
  { name: "Makaron penne", unit: "500g" },
  { name: "Makaron spaghetti", unit: "500g" },
  { name: "Makaron lasagne", unit: "500g" },
  { name: "Mąka", unit: "1kg" },
  { name: "Skrobia ziemniaczana", unit: "500g" },
  { name: "Bułka tarta", unit: "500g" },
  { name: "Cukier", unit: "1kg" },
  { name: "Cukier puder", unit: "400g" },
  { name: "Cukier waniliowy", unit: "32g" },
  { name: "Sól", unit: "1kg" },
  { name: "Pieprz czarny", unit: "50g" },
  { name: "Papryka mielona", unit: "30g" },
  { name: "Cynamon", unit: "20g" },
  { name: "Oregano", unit: "10g" },
  { name: "Bazylia", unit: "10g" },
  { name: "Kurkuma", unit: "50g" },
  { name: "Imbir", unit: "100g" },
  { name: "Olej słonecznikowy", unit: "1L" },
  { name: "Olej rzepakowy", unit: "1L" },
  { name: "Olej kokosowy", unit: "250ml" },
  { name: "Oliwa z oliwek", unit: "500ml" },
  { name: "Ocet", unit: "500ml" },
  { name: "Ocet jabłkowy", unit: "500ml" },
  { name: "Sos sojowy", unit: "200ml" },
  { name: "Sos BBQ", unit: "300ml" },
  { name: "Ketchup", unit: "450g" },
  { name: "Musztarda", unit: "185g" },
  { name: "Majonez", unit: "400ml" },
  { name: "Majonez light", unit: "400ml" },
  { name: "Hummus", unit: "200g" },
  { name: "Pesto", unit: "190g" },
  { name: "Koncentrat pomidorowy", unit: "200g" },
  { name: "Pomidory w puszce", unit: "400g" },
  { name: "Kukurydza w puszce", unit: "400g" },
  { name: "Fasola w puszce", unit: "400g" },
  { name: "Groszek konserwowy", unit: "400g" },
  { name: "Mleko kokosowe", unit: "400ml" },
  { name: "Bulion warzywny", unit: "4 szt." },
  { name: "Zupa w proszku", unit: "60g" },
  { name: "Miód", unit: "400g" },
  { name: "Dżem", unit: "280g" },
  { name: "Nutella", unit: "400g" },
  { name: "Proszek do pieczenia", unit: "30g" },
  { name: "Soda oczyszczona", unit: "200g" },
  { name: "Drożdże", unit: "100g" },
  { name: "Pomidory", unit: "1kg" },
  { name: "Ogórki", unit: "1kg" },
  { name: "Papryka", unit: "1kg" },
  { name: "Cebula", unit: "1kg" },
  { name: "Czosnek", unit: "1 główka" },
  { name: "Ziemniaki", unit: "1kg" },
  { name: "Batat", unit: "1kg" },
  { name: "Marchew", unit: "1kg" },
  { name: "Sałata", unit: "1 szt." },
  { name: "Szpinak", unit: "300g" },
  { name: "Brokuły", unit: "1 szt." },
  { name: "Kapusta biała", unit: "1kg" },
  { name: "Por", unit: "1 szt." },
  { name: "Pietruszka", unit: "1 pęczek" },
  { name: "Seler korzeniowy", unit: "1 szt." },
  { name: "Burak", unit: "1kg" },
  { name: "Cukinia", unit: "1 szt." },
  { name: "Bakłażan", unit: "1 szt." },
  { name: "Szparagi", unit: "300g" },
  { name: "Pieczarki", unit: "400g" },
  { name: "Groszek mrożony", unit: "400g" },
  { name: "Mrożone warzywa mix", unit: "400g" },
  { name: "Mrożone frytki", unit: "1kg" },
  { name: "Jabłka", unit: "1kg" },
  { name: "Banany", unit: "1kg" },
  { name: "Pomarańcze", unit: "1kg" },
  { name: "Cytryny", unit: "1kg" },
  { name: "Grejpfrut", unit: "1kg" },
  { name: "Kiwi", unit: "1kg" },
  { name: "Truskawki", unit: "500g" },
  { name: "Maliny", unit: "250g" },
  { name: "Borówki", unit: "250g" },
  { name: "Porzeczki", unit: "500g" },
  { name: "Winogrona", unit: "1kg" },
  { name: "Gruszki", unit: "1kg" },
  { name: "Śliwki", unit: "1kg" },
  { name: "Nektarynki", unit: "1kg" },
  { name: "Brzoskwinie", unit: "1kg" },
  { name: "Mango", unit: "1 szt." },
  { name: "Awokado", unit: "1 szt." },
  { name: "Mrożone truskawki", unit: "500g" },
  { name: "Pierś z kurczaka", unit: "1kg" },
  { name: "Udka z kurczaka", unit: "1kg" },
  { name: "Filet z indyka", unit: "1kg" },
  { name: "Mielone wołowe", unit: "500g" },
  { name: "Schab", unit: "1kg" },
  { name: "Boczek", unit: "200g" },
  { name: "Kiełbasa", unit: "1kg" },
  { name: "Parówki", unit: "500g" },
  { name: "Szynka", unit: "300g" },
  { name: "Wędlina drobiowa", unit: "300g" },
  { name: "Wątroba drobiowa", unit: "500g" },
  { name: "Łosoś świeży", unit: "1kg" },
  { name: "Łosoś wędzony", unit: "100g" },
  { name: "Makrela wędzona", unit: "250g" },
  { name: "Śledź", unit: "300g" },
  { name: "Tuńczyk w puszce", unit: "170g" },
  { name: "Sardynki w puszce", unit: "120g" },
  { name: "Paluszki rybne", unit: "400g" },
  { name: "Krewetki", unit: "500g" },
  { name: "Filet z dorsza", unit: "1kg" },
  { name: "Pierogi mrożone", unit: "500g" },
  { name: "Mrożona pizza", unit: "1 szt." },
  { name: "Lody", unit: "500ml" },
  { name: "Woda mineralna", unit: "1.5L" },
  { name: "Woda gazowana", unit: "1.5L" },
  { name: "Sok pomarańczowy", unit: "1L" },
  { name: "Sok jabłkowy", unit: "1L" },
  { name: "Sok z cytryny", unit: "200ml" },
  { name: "Cola", unit: "1.5L" },
  { name: "Piwo", unit: "0.5L" },
  { name: "Wino", unit: "0.75L" },
  { name: "Herbata", unit: "100 torebek" },
  { name: "Herbata zielona", unit: "50 torebek" },
  { name: "Kawa mielona", unit: "250g" },
  { name: "Kawa ziarnista", unit: "250g" },
  { name: "Kawa instant", unit: "100g" },
  { name: "Kakao", unit: "200g" },
  { name: "Płatki owsiane", unit: "500g" },
  { name: "Płatki kukurydziane", unit: "500g" },
  { name: "Musli", unit: "500g" },
  { name: "Kasza gryczana", unit: "500g" },
  { name: "Kasza jaglana", unit: "500g" },
  { name: "Kasza bulgur", unit: "500g" },
  { name: "Soczewica", unit: "500g" },
  { name: "Ciecierzyca", unit: "500g" },
  { name: "Fasola sucha", unit: "500g" },
  { name: "Komosa ryżowa", unit: "500g" },
  { name: "Nasiona chia", unit: "200g" },
  { name: "Siemię lniane", unit: "500g" },
  { name: "Otręby pszenne", unit: "500g" },
  { name: "Orzechy włoskie", unit: "200g" },
  { name: "Orzechy nerkowca", unit: "150g" },
  { name: "Migdały", unit: "200g" },
  { name: "Rodzynki", unit: "200g" },
  { name: "Czekolada", unit: "100g" },
  { name: "Czekolada gorzka", unit: "100g" },
  { name: "Chipsy", unit: "150g" },
  { name: "Ciastka", unit: "200g" },
  { name: "Baton czekoladowy", unit: "50g" },
  { name: "Żelki", unit: "100g" },
  { name: "Popcorn", unit: "100g" },
  { name: "Precelki", unit: "150g" },
  { name: "Papier toaletowy", unit: "8 rolek" },
  { name: "Ręczniki papierowe", unit: "2 rolki" },
  { name: "Płyn do naczyń", unit: "1L" },
  { name: "Proszek do prania", unit: "3kg" },
  { name: "Płyn do podłóg", unit: "1L" },
  { name: "Proszek do zmywarki", unit: "1kg" },
  { name: "Worki na śmieci", unit: "20 szt." },
  { name: "Szampon", unit: "400ml" },
  { name: "Mydło w kostce", unit: "100g" },
  { name: "Pasta do zębów", unit: "75ml" },
  { name: "Nachos", unit: "200g" },
  { name: "Krakersy", unit: "100g" },
  { name: "Paluszki chlebowe", unit: "200g" },
  { name: "Wafelki", unit: "150g" },
  { name: "Wafle ryżowe", unit: "130g" },
  { name: "Chrupki kukurydziane", unit: "100g" },
  { name: "Orzeszki solone", unit: "200g" },
  { name: "Pistacje", unit: "150g" },
  { name: "Mix orzechów", unit: "200g" },
  { name: "Biszkopty", unit: "200g" },
  { name: "Budyń", unit: "40g" },
  { name: "Kisiel", unit: "77g" },
  { name: "Galaretka", unit: "75g" },
  { name: "Pierniki", unit: "400g" },
  { name: "Wafle", unit: "200g" },
  { name: "Ptasie mleczko", unit: "340g" },
  { name: "Lody na patyku", unit: "110ml" },
  { name: "Karmelki", unit: "100g" },
  { name: "Sos tzatziki", unit: "200g" },
  { name: "Sos chilli", unit: "200ml" },
  { name: "Tahini", unit: "250g" },
  { name: "Tofu", unit: "200g" },
  { name: "Sos Worcester", unit: "150ml" },
  { name: "Pasta curry", unit: "100g" },
  { name: "Zupka instant", unit: "65g" },
  { name: "Makaron instant", unit: "70g" },
  { name: "Tortilla wrap", unit: "8 szt." },
  { name: "Naleśniki mrożone", unit: "400g" },
  { name: "Placki ziemniaczane mrożone", unit: "400g" },
  { name: "Kopytka mrożone", unit: "500g" },
  { name: "Gołąbki mrożone", unit: "500g" },
  { name: "Red Bull", unit: "250ml" },
  { name: "Sprite", unit: "1.5L" },
  { name: "Fanta", unit: "1.5L" },
  { name: "Pepsi", unit: "1.5L" },
  { name: "Sok multivitaminowy", unit: "1L" },
  { name: "Syrop owocowy", unit: "400ml" },
  { name: "Napój izotoniczny", unit: "500ml" },
  { name: "Ser topiony", unit: "140g" },
  { name: "Koktajl mleczny", unit: "400ml" },
  { name: "Karma dla psa", unit: "400g" },
  { name: "Karma dla kota", unit: "400g" },
  { name: "Drożdżówka", unit: "1 szt." },
  { name: "Pączek", unit: "1 szt." },
  { name: "Croissant", unit: "1 szt." },
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
    if (!name) return;
    if (items.find((i) => i.name.toLowerCase() === name.toLowerCase())) return;
    // Try to find a matching unit from the product list even for manual entries
    const matched = COMMON_PRODUCTS.find(
      (p) => p.name.toLowerCase() === name.toLowerCase()
    );
    const unit = product?.unit ?? matched?.unit ?? "";
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
