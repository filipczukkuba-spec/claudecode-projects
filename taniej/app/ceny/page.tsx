import { Metadata } from "next";
import Link from "next/link";
import { createAdminClient } from "@/lib/supabase-admin";
import { slugify } from "@/lib/slug";

export const revalidate = 3600;

const BASE = "https://taniejkupuj.pl";

export const metadata: Metadata = {
  title: "Ceny produktów spożywczych — porównaj w 7 sklepach | taniejkupuj",
  description:
    "Lista wszystkich produktów z porównywarką cen: Biedronka, Lidl, Kaufland, Aldi, Netto, Auchan, Carrefour. Sprawdź gdzie najtaniej. Aktualizowane codziennie.",
  alternates: { canonical: `${BASE}/ceny` },
  openGraph: {
    title: "Ceny produktów spożywczych — porównaj w 7 sklepach",
    description: "Sprawdź gdzie najtaniej kupisz produkty spożywcze w Polsce.",
    url: `${BASE}/ceny`,
    siteName: "taniejkupuj",
    locale: "pl_PL",
    type: "website",
  },
};

interface Product { id: number; name: string }

export default async function CenyIndexPage() {
  const admin = createAdminClient();
  const { data } = await admin.from("products").select("id, name").order("name");
  const products = (data ?? []) as Product[];

  return (
    <main className="min-h-screen bg-[#f0f0eb]">
      <div className="max-w-3xl mx-auto px-4 py-8">
        <nav className="text-xs text-gray-400 mb-4">
          <Link href="/" className="hover:text-gray-600">taniejkupuj.pl</Link>
          <span className="mx-1.5">›</span>
          <span className="text-gray-600 font-semibold">ceny produktów</span>
        </nav>

        <header className="bg-white rounded-3xl shadow-sm p-6 mb-6">
          <h1 className="text-3xl font-black text-gray-900 leading-tight">
            Ceny produktów spożywczych
          </h1>
          <p className="text-gray-500 text-sm mt-2 leading-relaxed">
            Porównujemy ceny {products.length} produktów w 7 sklepach codziennie. Kliknij produkt, żeby zobaczyć,
            gdzie jest najtaniej, lub wpisz całą listę zakupów na <Link href="/" className="text-green-600 underline">stronie głównej</Link>.
          </p>
        </header>

        <div className="bg-white rounded-3xl shadow-sm p-6">
          <ul className="grid sm:grid-cols-2 gap-x-6 gap-y-1">
            {products.map((p) => (
              <li key={p.id}>
                <Link
                  href={`/cena/${slugify(p.name)}`}
                  className="block text-sm text-gray-700 hover:text-green-600 py-1.5 border-b border-gray-50"
                >
                  {p.name}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </main>
  );
}
