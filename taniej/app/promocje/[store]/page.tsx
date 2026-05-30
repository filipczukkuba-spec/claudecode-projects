import { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { createAdminClient } from "@/lib/supabase-admin";
import { storeUrlFor } from "@/lib/store-links";

export const revalidate = 3600; // ISR — page rebuilds every hour

// Canonical store names (case + Polish-letter friendly slugs)
const STORE_SLUGS: Record<string, string> = {
  biedronka: "Biedronka",
  lidl:      "Lidl",
  kaufland:  "Kaufland",
  aldi:      "Aldi",
  netto:     "Netto",
  auchan:    "Auchan",
  carrefour: "Carrefour",
};

function slugToStore(slug: string): string | null {
  return STORE_SLUGS[slug.toLowerCase()] ?? null;
}

interface Props { params: Promise<{ store: string }> }

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { store: slug } = await params;
  const name = slugToStore(slug);
  if (!name) return { title: "Nie znaleziono" };

  const title = `Promocje ${name} ${new Date().toLocaleDateString("pl-PL", { month: "long", year: "numeric" })} — gazetka i ceny`;
  const description = `Aktualne promocje w ${name}: cena promocyjna, etykiety, daty obowiązywania. Porównaj z 6 innymi sklepami: Biedronka, Lidl, Kaufland, Aldi, Netto, Auchan, Carrefour.`;

  return {
    title,
    description,
    keywords: [
      `promocje ${name.toLowerCase()}`,
      `gazetka ${name.toLowerCase()}`,
      `${name.toLowerCase()} oferty tygodnia`,
      `${name.toLowerCase()} cena`,
      `${name.toLowerCase()} promocja`,
      "porównanie cen",
      "tanie zakupy",
    ],
    openGraph: {
      title,
      description,
      url: `https://taniejkupuj.pl/promocje/${slug.toLowerCase()}`,
      siteName: "taniejkupuj",
      locale: "pl_PL",
      type: "website",
    },
    alternates: {
      canonical: `https://taniejkupuj.pl/promocje/${slug.toLowerCase()}`,
    },
  };
}

export async function generateStaticParams() {
  return Object.keys(STORE_SLUGS).map((store) => ({ store }));
}

interface PromoRow {
  promo_price: number;
  promo_label: string | null;
  valid_from: string;
  valid_until: string;
  products: { name: string; unit: string | null } | null;
  product_id: number;
}

interface PriceRow {
  product_id: number;
  stores: { name: string } | null;
  price: number | null;
}

function fmt(n: number) {
  return n.toLocaleString("pl-PL", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default async function StorePromoPage({ params }: Props) {
  const { store: slug } = await params;
  const name = slugToStore(slug);
  if (!name) notFound();

  const admin = createAdminClient();
  const today = new Date().toISOString().split("T")[0];

  const { data: storeRow } = await admin
    .from("stores").select("id").eq("name", name).single();
  if (!storeRow) notFound();

  // Active promotions for this store
  const { data: promosRaw } = await admin
    .from("promotions" as any)
    .select("promo_price, promo_label, valid_from, valid_until, product_id, products(name, unit)")
    .eq("store_id", storeRow.id)
    .lte("valid_from", today)
    .gte("valid_until", today)
    .order("promo_price", { ascending: true });

  const promos = (promosRaw ?? []) as unknown as PromoRow[];

  // Compare against cheapest price across all stores for the same product
  const productIds = [...new Set(promos.map((p) => p.product_id))];
  let altMinByProduct = new Map<number, { price: number; store: string }>();
  if (productIds.length > 0) {
    const { data: alts } = await admin
      .from("prices")
      .select("product_id, price, stores(name)")
      .in("product_id", productIds);
    for (const r of (alts ?? []) as unknown as PriceRow[]) {
      if (r.price == null || !r.stores) continue;
      if (r.stores.name === name) continue;
      const cur = altMinByProduct.get(r.product_id);
      if (!cur || r.price < cur.price) {
        altMinByProduct.set(r.product_id, { price: r.price, store: r.stores.name });
      }
    }
  }

  const storeUrl = storeUrlFor(name);

  return (
    <main className="min-h-screen bg-[#f0f0eb]">
      <div className="max-w-3xl mx-auto px-4 py-8">
        <nav className="text-xs text-gray-400 mb-4">
          <Link href="/" className="hover:text-gray-600">taniejkupuj.pl</Link>
          <span className="mx-1.5">›</span>
          <Link href="/promocje" className="hover:text-gray-600">promocje</Link>
          <span className="mx-1.5">›</span>
          <span className="text-gray-600 font-semibold">{name}</span>
        </nav>

        <header className="bg-white rounded-3xl shadow-sm p-6 mb-6">
          <h1 className="text-3xl font-black text-gray-900 leading-tight">
            Promocje {name} — aktualna gazetka i ceny
          </h1>
          <p className="text-gray-500 text-sm mt-2 leading-relaxed">
            {promos.length > 0
              ? `Mamy ${promos.length} aktywnych promocji w ${name} dziś (${new Date().toLocaleDateString("pl-PL")}). Każdą porównujemy z cenami w 6 innych sklepach (Biedronka, Lidl, Kaufland, Aldi, Netto, Auchan, Carrefour) żebyś wiedział, czy to faktycznie najlepsza oferta.`
              : `Aktualnie nie mamy aktywnych promocji w ${name}. Sprawdź pełną porównywarkę cen produktów spożywczych w 7 sklepach.`}
          </p>
          {storeUrl && (
            <a
              href={`/go/${encodeURIComponent(name)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 mt-4 bg-green-500 hover:bg-green-600 text-white font-bold text-sm rounded-xl px-4 py-2.5"
            >
              Otwórz {name} →
            </a>
          )}
        </header>

        {promos.length > 0 ? (
          <div className="bg-white rounded-3xl shadow-sm overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  <th className="text-left px-5 py-3 text-xs font-bold text-gray-500 uppercase tracking-widest">Produkt</th>
                  <th className="text-right px-5 py-3 text-xs font-bold text-gray-500 uppercase tracking-widest">Cena promo</th>
                  <th className="text-right px-5 py-3 text-xs font-bold text-gray-500 uppercase tracking-widest hidden sm:table-cell">Gdzie taniej?</th>
                </tr>
              </thead>
              <tbody>
                {promos.map((p, i) => {
                  const alt = altMinByProduct.get(p.product_id);
                  const cheaperElsewhere = alt && alt.price < p.promo_price;
                  return (
                    <tr key={i} className="border-b border-gray-50 last:border-0">
                      <td className="px-5 py-3">
                        <p className="font-semibold text-gray-800 text-sm">{p.products?.name ?? "—"}</p>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          {p.products?.unit && <span className="text-xs text-gray-400">{p.products.unit}</span>}
                          {p.promo_label && (
                            <span className="text-[10px] bg-orange-100 text-orange-600 font-bold px-1.5 py-0.5 rounded-full leading-none">
                              {p.promo_label}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-5 py-3 text-right">
                        <p className="font-black text-orange-600 text-base">{fmt(p.promo_price)} zł</p>
                      </td>
                      <td className="px-5 py-3 text-right hidden sm:table-cell">
                        {cheaperElsewhere ? (
                          <div>
                            <p className="text-xs text-green-600 font-bold">{alt!.store}</p>
                            <p className="text-xs text-gray-500">{fmt(alt!.price)} zł</p>
                          </div>
                        ) : (
                          <p className="text-xs text-gray-400">{name} najtańsza</p>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="bg-white rounded-3xl shadow-sm p-8 text-center">
            <p className="text-5xl mb-3">📭</p>
            <p className="text-gray-700 font-semibold">Brak aktywnych promocji</p>
            <p className="text-gray-400 text-sm mt-2 leading-relaxed">
              Codziennie skanujemy gazetki online. Wróć jutro lub zobacz <Link href="/" className="text-green-600 underline">aktualne ceny we wszystkich sklepach</Link>.
            </p>
          </div>
        )}

        <section className="bg-white rounded-3xl shadow-sm p-6 mt-6">
          <h2 className="text-lg font-bold text-gray-900 mb-3">Dlaczego ceny w {name} warto porównywać?</h2>
          <p className="text-gray-600 text-sm leading-relaxed mb-3">
            {name} prowadzi cotygodniową gazetkę z promocjami, ale to nie zawsze znaczy najtaniej.
            Często ten sam produkt jest tańszy w innym sklepie nawet w cenie regularnej.
            taniejkupuj.pl codziennie skanuje ceny w 7 sklepach (Biedronka, Lidl, Kaufland, Aldi, Netto, Auchan, Carrefour)
            i pokazuje Ci która oferta jest faktycznie najlepsza dla Twojej listy zakupów.
          </p>
          <p className="text-gray-600 text-sm leading-relaxed">
            Wpisz listę zakupów na <Link href="/" className="text-green-600 underline">stronie głównej</Link> żeby porównać pełny koszyk.
          </p>
        </section>

        <nav className="bg-white rounded-3xl shadow-sm p-6 mt-6">
          <h2 className="text-sm font-bold text-gray-400 uppercase tracking-widest mb-3">Promocje w innych sklepach</h2>
          <div className="flex flex-wrap gap-2">
            {Object.entries(STORE_SLUGS)
              .filter(([s]) => s !== slug.toLowerCase())
              .map(([s, n]) => (
                <Link
                  key={s}
                  href={`/promocje/${s}`}
                  className="text-sm font-semibold text-gray-700 bg-gray-50 hover:bg-gray-100 rounded-full px-4 py-2"
                >
                  {n}
                </Link>
              ))}
          </div>
        </nav>
      </div>
    </main>
  );
}
