"use client";

import { useState, useRef, useEffect } from "react";
import { Item } from "@/types";
import { norm } from "@/lib/matching";

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
  { name: "Bułka tarta", unit: "500g" },
  { name: "Cukier", unit: "1kg" },
  { name: "Cukier puder", unit: "400g" },
  { name: "Sól", unit: "1kg" },
  { name: "Pieprz czarny", unit: "50g" },
  { name: "Papryka mielona", unit: "30g" },
  { name: "Cynamon", unit: "20g" },
  { name: "Oregano", unit: "10g" },
  { name: "Bazylia", unit: "10g" },
  { name: "Kurkuma", unit: "50g" },
  { name: "Olej słonecznikowy", unit: "1L" },
  { name: "Olej rzepakowy", unit: "1L" },
  { name: "Oliwa z oliwek", unit: "500ml" },
  { name: "Ocet", unit: "500ml" },
  { name: "Sos sojowy", unit: "200ml" },
  { name: "Ketchup", unit: "450g" },
  { name: "Musztarda", unit: "185g" },
  { name: "Majonez", unit: "400ml" },
  { name: "Hummus", unit: "200g" },
  { name: "Pesto", unit: "190g" },
  { name: "Koncentrat pomidorowy", unit: "200g" },
  { name: "Pomidory w puszce", unit: "400g" },
  { name: "Kukurydza w puszce", unit: "400g" },
  { name: "Fasola w puszce", unit: "400g" },
  { name: "Groszek konserwowy", unit: "400g" },
  { name: "Mleko kokosowe", unit: "400ml" },
  { name: "Miód", unit: "400g" },
  { name: "Dżem", unit: "280g" },
  { name: "Nutella", unit: "400g" },
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
  { name: "Pieczarki", unit: "400g" },
  { name: "Groszek mrożony", unit: "400g" },
  { name: "Mrożone warzywa mix", unit: "400g" },
  { name: "Mrożone frytki", unit: "1kg" },
  { name: "Jabłka", unit: "1kg" },
  { name: "Banany", unit: "1kg" },
  { name: "Pomarańcze", unit: "1kg" },
  { name: "Cytryny", unit: "1kg" },
  { name: "Kiwi", unit: "1kg" },
  { name: "Truskawki", unit: "500g" },
  { name: "Maliny", unit: "250g" },
  { name: "Borówki", unit: "250g" },
  { name: "Winogrona", unit: "1kg" },
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
  { name: "Łosoś świeży", unit: "1kg" },
  { name: "Łosoś wędzony", unit: "100g" },
  { name: "Tuńczyk w puszce", unit: "170g" },
  { name: "Sardynki w puszce", unit: "120g" },
  { name: "Pierogi mrożone", unit: "500g" },
  { name: "Mrożona pizza", unit: "1 szt." },
  { name: "Lody", unit: "500ml" },
  { name: "Woda mineralna", unit: "1.5L" },
  { name: "Woda gazowana", unit: "1.5L" },
  { name: "Sok pomarańczowy", unit: "1L" },
  { name: "Sok jabłkowy", unit: "1L" },
  { name: "Cola", unit: "1.5L" },
  { name: "Piwo", unit: "0.5L" },
  { name: "Herbata", unit: "100 torebek" },
  { name: "Kawa mielona", unit: "250g" },
  { name: "Kawa instant", unit: "100g" },
  { name: "Kakao", unit: "200g" },
  { name: "Płatki owsiane", unit: "500g" },
  { name: "Płatki kukurydziane", unit: "500g" },
  { name: "Musli", unit: "500g" },
  { name: "Kasza gryczana", unit: "500g" },
  { name: "Kasza jaglana", unit: "500g" },
  { name: "Soczewica", unit: "500g" },
  { name: "Ciecierzyca", unit: "500g" },
  { name: "Orzechy włoskie", unit: "200g" },
  { name: "Migdały", unit: "200g" },
  { name: "Chipsy", unit: "150g" },
  { name: "Ciastka", unit: "200g" },
  { name: "Czekolada", unit: "100g" },
  { name: "Nachos", unit: "200g" },
  { name: "Krakersy", unit: "100g" },
  { name: "Granola", unit: "400g" },
  { name: "Papier toaletowy", unit: "8 rolek" },
  { name: "Płyn do naczyń", unit: "1L" },
  { name: "Proszek do prania", unit: "3kg" },
  { name: "Szampon", unit: "400ml" },
  { name: "Pasta do zębów", unit: "75ml" },
  { name: "Tortilla wrap", unit: "8 szt." },
  { name: "Red Bull", unit: "250ml" },
  { name: "Sprite", unit: "1.5L" },
  { name: "Fanta", unit: "1.5L" },
  { name: "Pepsi", unit: "1.5L" },
  { name: "Karma dla psa", unit: "400g" },
  { name: "Karma dla kota", unit: "400g" },
  // Brands
  { name: "Lay's Papryka", unit: "130g" },
  { name: "Lay's Solone", unit: "130g" },
  { name: "Lay's Zesty BBQ", unit: "130g" },
  { name: "Lay's Ser i Cebula", unit: "130g" },
  { name: "Lay's Max Papryka", unit: "120g" },
  { name: "Pringles Original", unit: "165g" },
  { name: "Pringles Paprika", unit: "165g" },
  { name: "Pringles Sour Cream", unit: "165g" },
  { name: "Pringles BBQ", unit: "165g" },
  { name: "Snickers", unit: "50g" },
  { name: "Twix", unit: "50g" },
  { name: "Mars", unit: "51g" },
  { name: "Bounty", unit: "57g" },
  { name: "Kit Kat", unit: "41g" },
  { name: "Kinder Bueno", unit: "43g" },
  { name: "Kinder czekolada", unit: "100g" },
  { name: "Lion", unit: "42g" },
  { name: "Prince Polo", unit: "35g" },
  { name: "Milka Mleczna", unit: "100g" },
  { name: "Milka Oreo", unit: "100g" },
  { name: "Milka Karmel", unit: "100g" },
  { name: "Wedel Czekolada", unit: "100g" },
  { name: "Wawel Czekolada Mleczna", unit: "100g" },
  { name: "Ferrero Rocher", unit: "3 szt." },
  { name: "Raffaello", unit: "3 szt." },
  { name: "Toblerone", unit: "100g" },
  { name: "Oreo", unit: "176g" },
  { name: "Oreo Double Stuf", unit: "157g" },
  { name: "Leibniz", unit: "200g" },
  { name: "BelVita", unit: "225g" },
  { name: "Activia jogurt", unit: "150g" },
  { name: "Actimel", unit: "100ml" },
  { name: "Danio serek", unit: "140g" },
  { name: "Łaciate mleko", unit: "1L" },
  { name: "President masło", unit: "200g" },
  { name: "Alpro sojowe", unit: "1L" },
  { name: "Oatly owsiane", unit: "1L" },
  { name: "Coca-Cola", unit: "0.5L" },
  { name: "Coca-Cola Zero", unit: "0.5L" },
  { name: "Pepsi Max", unit: "0.5L" },
  { name: "Monster Energy", unit: "500ml" },
  { name: "Tiger Energy", unit: "250ml" },
  { name: "Tymbark sok", unit: "1L" },
  { name: "Hortex sok", unit: "1L" },
  { name: "Cisowianka", unit: "1.5L" },
  { name: "Żywiec Zdrój", unit: "1.5L" },
  { name: "Lotus Biscoff", unit: "400g" },
  { name: "Magnum Classic", unit: "110ml" },
  { name: "Magnum Almond", unit: "110ml" },
  { name: "Ben & Jerry's", unit: "465ml" },
  { name: "Winiary majonez", unit: "400ml" },
  { name: "Kielecki majonez", unit: "400ml" },
  { name: "Heinz ketchup", unit: "450g" },
  { name: "Hellmann's majonez", unit: "400ml" },
  { name: "Knorr zupa", unit: "68g" },
  { name: "Maggi zupa", unit: "68g" },
  // ── Polish dairy brands ──
  { name: "Mlekovita ser", unit: "250g" },
  { name: "Mlekovita masło", unit: "200g" },
  { name: "Piątnica twaróg", unit: "250g" },
  { name: "Piątnica śmietana", unit: "400g" },
  { name: "Hochland ser topiony", unit: "200g" },
  { name: "Hochland Almette", unit: "150g" },
  { name: "Bakoma jogurt", unit: "150g" },
  { name: "Bakoma Mus", unit: "100g" },
  { name: "Zott Jogobella", unit: "150g" },
  { name: "Zott Monte", unit: "100g" },
  { name: "Müller jogurt", unit: "150g" },
  { name: "Skyr Pilos", unit: "150g" },
  { name: "Mleko UHT Łaciate 3,2%", unit: "1L" },
  { name: "Mleko UHT Łaciate 2%", unit: "1L" },
  { name: "Mleko Wypasione", unit: "1L" },
  // ── Polish meat / cold cuts ──
  { name: "Sokołów szynka", unit: "300g" },
  { name: "Sokołów kiełbasa", unit: "1kg" },
  { name: "Tarczyński kabanosy", unit: "120g" },
  { name: "Kabanos Drobimex", unit: "120g" },
  { name: "Indykpol indyk", unit: "1kg" },
  { name: "Krakus szynka", unit: "300g" },
  // ── Polish chips / snacks ──
  { name: "Crunchips Paprika", unit: "140g" },
  { name: "Crunchips Solone", unit: "140g" },
  { name: "Star Chipsy", unit: "150g" },
  { name: "Cheetos", unit: "85g" },
  { name: "Doritos", unit: "180g" },
  { name: "Paluszki Lajkonik", unit: "300g" },
  { name: "Tartinki Wasa", unit: "200g" },
  // ── Polish sweets ──
  { name: "Wedel Ptasie Mleczko", unit: "380g" },
  { name: "Wedel Pawełek", unit: "100g" },
  { name: "Wawel Tiki Taki", unit: "280g" },
  { name: "Wawel Michałki", unit: "280g" },
  { name: "Goplana Grześki", unit: "36g" },
  { name: "Goplana Czekolada Mleczna", unit: "100g" },
  { name: "Delicje Szampańskie", unit: "147g" },
  { name: "Krówki", unit: "300g" },
  { name: "Toffifee", unit: "125g" },
  { name: "Merci czekoladki", unit: "250g" },
  { name: "Lindt Lindor", unit: "200g" },
  { name: "Lindt Excellence", unit: "100g" },
  { name: "Ritter Sport", unit: "100g" },
  { name: "Tic Tac", unit: "16g" },
  { name: "Mentos", unit: "38g" },
  { name: "Skittles", unit: "38g" },
  { name: "Haribo Goldbären", unit: "100g" },
  // ── Polish drinks ──
  { name: "Frugo", unit: "330ml" },
  { name: "Kubuś Waterrr", unit: "330ml" },
  { name: "Kubuś sok", unit: "1L" },
  { name: "Cappy sok", unit: "330ml" },
  { name: "Hoop Cola", unit: "1.5L" },
  { name: "Tymbark Mleczny szejk", unit: "250ml" },
  { name: "Pepsi Wild Cherry", unit: "0.5L" },
  { name: "Lipton Ice Tea", unit: "1.5L" },
  { name: "Nestea", unit: "1.5L" },
  { name: "Sprite", unit: "0.5L" },
  { name: "Schweppes", unit: "1L" },
  { name: "Muszynianka", unit: "1.5L" },
  { name: "Nałęczowianka", unit: "1.5L" },
  { name: "Kropla Beskidu", unit: "1.5L" },
  { name: "Pepsi Twist", unit: "1.5L" },
  // ── Polish beer ──
  { name: "Tyskie", unit: "0.5L" },
  { name: "Żywiec piwo", unit: "0.5L" },
  { name: "Lech", unit: "0.5L" },
  { name: "Warka", unit: "0.5L" },
  { name: "Książęce", unit: "0.5L" },
  { name: "Okocim", unit: "0.5L" },
  { name: "Heineken", unit: "0.5L" },
  { name: "Carlsberg", unit: "0.5L" },
  { name: "Desperados", unit: "0.4L" },
  { name: "Somersby", unit: "0.4L" },
  // ── Polish bread / staples ──
  { name: "Łowicki ketchup", unit: "450g" },
  { name: "Pudliszki ketchup", unit: "480g" },
  { name: "Pudliszki passata", unit: "500g" },
  { name: "Develey musztarda", unit: "270g" },
  { name: "Lubella makaron", unit: "500g" },
  { name: "Malma makaron", unit: "500g" },
  { name: "Britta makaron", unit: "500g" },
  { name: "Łowicz dżem", unit: "280g" },
  { name: "Łowicz konfitura", unit: "300g" },
  // ── Frozen ──
  { name: "Hortex frytki", unit: "1kg" },
  { name: "Hortex truskawki mrożone", unit: "450g" },
  { name: "Iglotex pierogi", unit: "450g" },
  { name: "Bonduelle kukurydza", unit: "340g" },
  { name: "Pierogi Madej Wróbel", unit: "500g" },
  { name: "Mrożone warzywa Hortex", unit: "450g" },
  // ── Personal care ──
  { name: "Nivea krem", unit: "75ml" },
  { name: "Nivea żel pod prysznic", unit: "250ml" },
  { name: "Garnier szampon", unit: "400ml" },
  { name: "Schwarzkopf szampon", unit: "400ml" },
  { name: "Head & Shoulders", unit: "400ml" },
  { name: "Dove żel pod prysznic", unit: "250ml" },
  { name: "Old Spice dezodorant", unit: "150ml" },
  { name: "Rexona dezodorant", unit: "150ml" },
  { name: "Colgate pasta", unit: "100ml" },
  { name: "Signal pasta", unit: "75ml" },
  { name: "Sensodyne pasta", unit: "75ml" },
  { name: "Listerine", unit: "500ml" },
  { name: "Gillette żyletki", unit: "4 szt." },
  { name: "Bella podpaski", unit: "10 szt." },
  { name: "Always podpaski", unit: "12 szt." },
  // ── Household cleaning ──
  { name: "Persil proszek", unit: "3kg" },
  { name: "Ariel proszek", unit: "3kg" },
  { name: "Vizir kapsułki", unit: "30 szt." },
  { name: "Lenor płyn", unit: "1.5L" },
  { name: "Domestos", unit: "1.25L" },
  { name: "Cif krem", unit: "750ml" },
  { name: "Cillit Bang", unit: "750ml" },
  { name: "Ludwik płyn do naczyń", unit: "1L" },
  { name: "Fairy płyn do naczyń", unit: "900ml" },
  { name: "Pronto do mebli", unit: "250ml" },
  { name: "Velvet papier toaletowy", unit: "8 rolek" },
  { name: "Regina papier toaletowy", unit: "8 rolek" },
  { name: "Foliopak worki", unit: "30 szt." },
];

interface Props {
  items: Item[];
  setItems: (items: Item[]) => void;
}

export default function ShoppingList({ items, setItems }: Props) {
  const [input, setInput] = useState("");
  const [suggestions, setSuggestions] = useState<Product[]>([]);
  const [focused, setFocused] = useState(false);
  const [highlight, setHighlight] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (input.trim().length === 0) { setSuggestions([]); setHighlight(-1); return; }
    const q = norm(input);
    const matches = COMMON_PRODUCTS.filter(
      (p) =>
        (norm(p.name).startsWith(q) || norm(p.name).includes(q)) &&
        !items.find((i) => i.name.toLowerCase() === p.name.toLowerCase())
    )
      .sort((a, b) => {
        const an = norm(a.name), bn = norm(b.name);
        const aStarts = an.startsWith(q) ? 0 : 1;
        const bStarts = bn.startsWith(q) ? 0 : 1;
        return aStarts - bStarts;
      })
      .slice(0, 6);
    setSuggestions(matches);
    setHighlight(matches.length > 0 ? 0 : -1);
  }, [input, items]);

  function addItem(product?: Product) {
    const name = product?.name ?? input.trim();
    if (!name) return;
    if (items.find((i) => i.name.toLowerCase() === name.toLowerCase())) return;
    const matched = COMMON_PRODUCTS.find((p) => p.name.toLowerCase() === name.toLowerCase());
    const unit = product?.unit ?? matched?.unit ?? "";
    setItems([...items, { id: crypto.randomUUID(), name, unit }]);
    setInput("");
    setSuggestions([]);
    setHighlight(-1);
    inputRef.current?.focus();
  }

  function removeItem(id: string) {
    setItems(items.filter((i) => i.id !== id));
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown" && suggestions.length > 0) {
      e.preventDefault();
      setHighlight((h) => (h + 1) % suggestions.length);
      return;
    }
    if (e.key === "ArrowUp" && suggestions.length > 0) {
      e.preventDefault();
      setHighlight((h) => (h <= 0 ? suggestions.length - 1 : h - 1));
      return;
    }
    if (e.key === "Enter") {
      if (highlight >= 0 && suggestions[highlight]) {
        e.preventDefault();
        addItem(suggestions[highlight]);
      } else {
        addItem();
      }
      return;
    }
    if (e.key === "Escape") {
      setSuggestions([]);
      setHighlight(-1);
    }
  }

  return (
    <div className="bg-white rounded-2xl shadow-sm overflow-visible mb-4">
      <div className="p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-widest">
            Twoja lista
          </h2>
          {items.length > 1 && (
            <button
              onClick={() => setItems([])}
              className="text-xs text-gray-300 hover:text-red-400 transition-colors"
            >
              Wyczyść
            </button>
          )}
        </div>

        {/* Input */}
        <div className="relative mb-3">
          <div className="flex gap-2">
            <input
              ref={inputRef}
              className="flex-1 border border-gray-200 rounded-xl px-4 py-3 text-base text-gray-900 placeholder-gray-400 focus:outline-none focus:border-green-400 transition-colors"
              placeholder="Np. mleko, chleb, Lay's..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              onFocus={() => setFocused(true)}
              onBlur={() => setTimeout(() => setFocused(false), 150)}
              autoComplete="off"
              autoCorrect="off"
              autoCapitalize="off"
            />
            <button
              onClick={() => addItem()}
              className="bg-green-500 hover:bg-green-600 active:bg-green-700 active:scale-95 text-white rounded-xl px-4 py-3 text-xl font-bold transition-all"
            >
              +
            </button>
          </div>

          {focused && suggestions.length > 0 && (
            <ul className="absolute left-0 right-10 top-full mt-1 bg-white border border-gray-100 rounded-xl shadow-xl z-20 overflow-hidden">
              {suggestions.map((s, idx) => (
                <li
                  key={s.name}
                  onMouseDown={() => addItem(s)}
                  onMouseEnter={() => setHighlight(idx)}
                  className={`flex items-center justify-between px-4 py-3 cursor-pointer border-b border-gray-50 last:border-0 transition-colors ${
                    idx === highlight ? "bg-green-50" : "hover:bg-green-50"
                  }`}
                >
                  <span className="text-gray-800 text-sm font-medium">{s.name}</span>
                  <span className="text-gray-400 text-xs">{s.unit}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Empty state */}
        {items.length === 0 && (
          <div className="text-center py-8">
            <p className="text-2xl mb-2">🛒</p>
            <p className="text-gray-400 text-sm">Dodaj produkty, żeby porównać ceny</p>
            <p className="text-gray-300 text-xs mt-1">Wpisz nazwę lub wklej przepis powyżej</p>
          </div>
        )}

        {/* Items */}
        {items.length > 0 && (
          <ul className="space-y-1.5">
            {items.map((item, idx) => (
              <li
                key={item.id}
                className="flex items-center justify-between bg-gray-50 hover:bg-gray-100 rounded-xl px-4 py-2.5 transition-colors animate-slide-up"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="w-1.5 h-1.5 rounded-full bg-green-400 shrink-0" />
                  <span className="text-gray-800 text-sm font-medium truncate">{item.name}</span>
                  {item.unit && (
                    <span className="text-gray-400 text-xs shrink-0">{item.unit}</span>
                  )}
                </div>
                <button
                  onClick={() => removeItem(item.id)}
                  className="text-gray-300 hover:text-red-400 active:text-red-600 active:scale-90 transition-all text-xl ml-2 shrink-0 min-w-[44px] min-h-[44px] flex items-center justify-center rounded-xl"
                  aria-label="Usuń"
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}

      </div>
    </div>
  );
}
