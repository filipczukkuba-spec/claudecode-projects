import { Metadata } from "next";
import Link from "next/link";
import { createAdminClient } from "@/lib/supabase-admin";

export const revalidate = 3600;

const STORES = ["Biedronka", "Lidl", "Kaufland", "Aldi", "Netto", "Auchan", "Carrefour"];
const STORE_STYLE: Record<string, string> = {
  Biedronka: "bg-red-500",
  Lidl: "bg-blue-500",
  Kaufland: "bg-orange-500",
  Aldi: "bg-indigo-500",
  Netto: "bg-yellow-400",
  Auchan: "bg-purple-500",
  Carrefour: "bg-sky-500",
};

export const metadata: Metadata = {
  title: "Promocje i gazetki — wszystkie sklepy spożywcze w jednym miejscu",
  description: "Aktualne promocje w Biedronce, Lidlu, Kauflandzie, Aldi, Netto, Auchanie i Carrefourze. Codzienna aktualizacja. Porównaj ceny przed zakupami.",
  keywords: [
    "promocje sklepów spożywczych",
    "gazetki promocyjne",
    "biedronka lidl kaufland promocje",
    "oferty tygodnia",
    "tanie zakupy",
  ],
  openGraph: {
    title: "Promocje i gazetki — wszystkie sklepy spożywcze w jednym miejscu",
    description: "Aktualne promocje w 7 sklepach spożywczych. Codzienna aktualizacja.",
    url: "https://taniejkupuj.pl/promocje",
    locale: "pl_PL",
    type: "website",
  },
  alternates: { canonical: "https://taniejkupuj.pl/promocje" },
};

export default async function PromocjeIndex() {
  const admin = createAdminClient();
  const today = new Date().toISOString().split("T")[0];

  // Promo count per store
  const { data: counts } = await admin
    .from("promotions" as any)
    .select("store_id, stores(name)")
    .lte("valid_from", today)
    .gte("valid_until", today);

  const byStore: Record<string, number> = {};
  for (const r of (counts ?? []) as any[]) {
    const n = r.stores?.name;
    if (!n) continue;
    byStore[n] = (byStore[n] ?? 0) + 1;
  }

  return (
    <main className="min-h-screen bg-[#f0f0eb]">
      <div className="max-w-3xl mx-auto px-4 py-8">
        <nav className="text-xs text-gray-400 mb-4">
          <Link href="/" className="hover:text-gray-600">taniejkupuj.pl</Link>
          <span className="mx-1.5">›</span>
          <span className="text-gray-600 font-semibold">promocje</span>
        </nav>

        <header className="bg-white rounded-3xl shadow-sm p-6 mb-6">
          <h1 className="text-3xl font-black text-gray-900 leading-tight">
            Promocje i gazetki — wszystkie sklepy spożywcze
          </h1>
          <p className="text-gray-500 text-sm mt-2 leading-relaxed">
            Codzienna synchronizacja promocji z 7 sklepów. Każda oferta porównana
            z cenami w pozostałych sklepach, żebyś wiedział czy to faktycznie
            najlepsza okazja.
          </p>
        </header>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {STORES.map((s) => {
            const count = byStore[s] ?? 0;
            return (
              <Link
                key={s}
                href={`/promocje/${s.toLowerCase()}`}
                className="bg-white hover:shadow-md transition-all rounded-2xl p-4 flex items-center gap-3"
              >
                <div className={`w-12 h-12 rounded-xl ${STORE_STYLE[s]} flex items-center justify-center text-white text-xl font-black shadow-sm`}>
                  {s[0]}
                </div>
                <div className="flex-1">
                  <p className="font-bold text-gray-800">{s}</p>
                  <p className="text-xs text-gray-400">
                    {count > 0 ? `${count} aktywnych promocji` : "brak aktywnych promocji"}
                  </p>
                </div>
                <span className="text-gray-300">→</span>
              </Link>
            );
          })}
        </div>

        <section className="bg-white rounded-3xl shadow-sm p-6 mt-6">
          <h2 className="text-lg font-bold text-gray-900 mb-3">Po co porównywać ceny w sklepach?</h2>
          <p className="text-gray-600 text-sm leading-relaxed mb-3">
            Polska rodzina wydaje średnio 1200-1800 zł miesięcznie na zakupy spożywcze.
            Różnice w cenach tych samych produktów między sklepami sięgają nawet 30-40%.
            Świadome porównanie cen przed zakupami może obniżyć rachunek o 200-400 zł w skali miesiąca.
          </p>
          <p className="text-gray-600 text-sm leading-relaxed">
            taniejkupuj.pl rozwiązuje to za Ciebie. Wpisujesz listę zakupów, dostajesz
            rekomendację najtańszego koszyka. <Link href="/" className="text-green-600 underline font-semibold">Spróbuj teraz</Link> — bez logowania.
          </p>
        </section>
      </div>
    </main>
  );
}
