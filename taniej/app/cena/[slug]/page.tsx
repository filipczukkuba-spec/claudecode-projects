import { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { createAdminClient } from "@/lib/supabase-admin";
import { storeUrlFor } from "@/lib/store-links";
import { slugify } from "@/lib/slug";

export const revalidate = 3600; // ISR — rebuild hourly

const BASE = "https://taniejkupuj.pl";

function fmt(n: number) {
  return n.toLocaleString("pl-PL", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

interface Product { id: number; name: string; unit: string | null }

// Resolve a slug back to a product by slugifying every product name.
// Cached per build/ISR window via the page's revalidate.
async function loadProducts(): Promise<Product[]> {
  const admin = createAdminClient();
  const { data } = await admin.from("products").select("id, name, unit");
  return (data ?? []) as Product[];
}

function findBySlug(products: Product[], slug: string): Product | null {
  const s = slug.toLowerCase();
  return products.find((p) => slugify(p.name) === s) ?? null;
}

interface PriceRow {
  store_id: number;
  price: number | null;
  app_price: number | null;
  source: string | null;
  stores: { name: string } | null;
}

interface StorePrice {
  store: string;
  price: number;
  isPromo: boolean;
  promoLabel: string | null;
  isEstimate: boolean;
}

async function loadStorePrices(productId: number): Promise<StorePrice[]> {
  const admin = createAdminClient();
  const today = new Date().toISOString().split("T")[0];

  const [{ data: pricesRaw }, { data: promosRaw }] = await Promise.all([
    admin
      .from("prices")
      .select("store_id, price, app_price, source, stores(name)")
      .eq("product_id", productId),
    admin
      .from("promotions" as any)
      .select("store_id, promo_price, promo_label")
      .eq("product_id", productId)
      .lte("valid_from", today)
      .gte("valid_until", today),
  ]);

  interface PromoSel { store_id: number; promo_price: number; promo_label: string | null }
  const promoByStore = new Map<number, { price: number; label: string | null }>();
  for (const p of (promosRaw ?? []) as unknown as PromoSel[]) {
    promoByStore.set(p.store_id, { price: p.promo_price, label: p.promo_label });
  }

  const out: StorePrice[] = [];
  for (const r of (pricesRaw ?? []) as unknown as PriceRow[]) {
    if (!r.stores) continue;
    const promo = promoByStore.get(r.store_id);
    const base = r.price ?? r.app_price;
    if (promo) {
      out.push({ store: r.stores.name, price: promo.price, isPromo: true, promoLabel: promo.label, isEstimate: false });
    } else if (base != null) {
      out.push({ store: r.stores.name, price: base, isPromo: false, promoLabel: null, isEstimate: r.source !== "scraped" });
    }
  }
  return out.sort((a, b) => a.price - b.price);
}

interface Props { params: Promise<{ slug: string }> }

export async function generateStaticParams() {
  const products = await loadProducts();
  return products.map((p) => ({ slug: slugify(p.name) }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const products = await loadProducts();
  const product = findBySlug(products, slug);
  if (!product) return { title: "Nie znaleziono produktu" };

  const prices = await loadStorePrices(product.id);
  const cheapest = prices[0];
  const priceStr = cheapest ? `od ${fmt(cheapest.price)} zł` : "porównaj ceny";

  const title = `${product.name} — najniższa cena ${priceStr} | taniejkupuj`;
  const description = cheapest
    ? `Najtańszy ${product.name} to ${fmt(cheapest.price)} zł w ${cheapest.store}. Porównaj ceny w 7 sklepach: Biedronka, Lidl, Kaufland, Aldi, Netto, Auchan, Carrefour. Aktualizowane codziennie.`
    : `Porównaj ceny ${product.name} w 7 sklepach: Biedronka, Lidl, Kaufland, Aldi, Netto, Auchan, Carrefour. Aktualizowane codziennie.`;

  const url = `${BASE}/cena/${slug}`;
  return {
    title,
    description,
    keywords: [
      `${product.name.toLowerCase()} cena`,
      `${product.name.toLowerCase()} najtaniej`,
      `najtańszy ${product.name.toLowerCase()}`,
      `${product.name.toLowerCase()} promocja`,
      "porównanie cen",
      "tanie zakupy",
    ],
    openGraph: { title, description, url, siteName: "taniejkupuj", locale: "pl_PL", type: "website" },
    alternates: { canonical: url },
  };
}

export default async function ProductPricePage({ params }: Props) {
  const { slug } = await params;
  const products = await loadProducts();
  const product = findBySlug(products, slug);
  if (!product) notFound();

  const prices = await loadStorePrices(product.id);
  const cheapest = prices[0];

  // A handful of other products to interlink — helps crawlers discover the
  // full /cena/* set and keeps users browsing. Deterministic (id-based offset)
  // so the render is pure and stable across ISR rebuilds.
  const others = products.filter((p) => p.id !== product.id);
  const start = others.length > 0 ? (product.id * 7) % others.length : 0;
  const related = Array.from({ length: Math.min(12, others.length) }, (_, i) =>
    others[(start + i) % others.length]
  );

  // Product + offers structured data for rich snippets.
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Product",
    name: product.name,
    ...(product.unit ? { description: `${product.name} (${product.unit}) — porównanie cen w 7 sklepach` } : {}),
    ...(prices.length > 0
      ? {
          offers: {
            "@type": "AggregateOffer",
            priceCurrency: "PLN",
            lowPrice: prices[0].price.toFixed(2),
            highPrice: prices[prices.length - 1].price.toFixed(2),
            offerCount: prices.length,
            offers: prices.map((p) => ({
              "@type": "Offer",
              price: p.price.toFixed(2),
              priceCurrency: "PLN",
              seller: { "@type": "Organization", name: p.store },
            })),
          },
        }
      : {}),
  };

  const searchUrl = cheapest ? storeUrlFor(cheapest.store, product.name) : null;

  return (
    <main className="min-h-screen bg-[#f0f0eb]">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <div className="max-w-3xl mx-auto px-4 py-8">
        <nav className="text-xs text-gray-400 mb-4">
          <Link href="/" className="hover:text-gray-600">taniejkupuj.pl</Link>
          <span className="mx-1.5">›</span>
          <Link href="/ceny" className="hover:text-gray-600">ceny produktów</Link>
          <span className="mx-1.5">›</span>
          <span className="text-gray-600 font-semibold">{product.name}</span>
        </nav>

        <header className="bg-white rounded-3xl shadow-sm p-6 mb-6">
          <h1 className="text-3xl font-black text-gray-900 leading-tight">
            {product.name} — gdzie najtaniej?
          </h1>
          {product.unit && <p className="text-gray-400 text-sm mt-1">{product.unit}</p>}
          <p className="text-gray-500 text-sm mt-3 leading-relaxed">
            {cheapest
              ? `Najtańszy ${product.name} dziś (${new Date().toLocaleDateString("pl-PL")}) to ${fmt(cheapest.price)} zł w ${cheapest.store}. Porównujemy ceny w 7 sklepach codziennie.`
              : `Porównujemy ceny ${product.name} w 7 sklepach codziennie. Wpisz pełną listę zakupów na stronie głównej.`}
          </p>
          {cheapest && (
            <div className="mt-4 flex items-baseline gap-2">
              <span className="text-4xl font-black text-green-600">{fmt(cheapest.price)} zł</span>
              <span className="text-sm font-semibold text-gray-500">w {cheapest.store}</span>
            </div>
          )}
          {searchUrl && (
            <a
              href={`/go/${encodeURIComponent(cheapest!.store)}?q=${encodeURIComponent(product.name)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 mt-4 bg-green-500 hover:bg-green-600 text-white font-bold text-sm rounded-xl px-4 py-2.5"
            >
              Kup w {cheapest!.store} →
            </a>
          )}
        </header>

        {prices.length > 0 ? (
          <div className="bg-white rounded-3xl shadow-sm overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  <th className="text-left px-5 py-3 text-xs font-bold text-gray-500 uppercase tracking-widest">Sklep</th>
                  <th className="text-right px-5 py-3 text-xs font-bold text-gray-500 uppercase tracking-widest">Cena</th>
                </tr>
              </thead>
              <tbody>
                {prices.map((p, i) => (
                  <tr key={p.store} className="border-b border-gray-50 last:border-0">
                    <td className="px-5 py-3">
                      <span className="font-semibold text-gray-800 text-sm">{p.store}</span>
                      {i === 0 && (
                        <span className="ml-2 text-[10px] bg-green-100 text-green-700 font-bold px-1.5 py-0.5 rounded-full leading-none">
                          najtaniej
                        </span>
                      )}
                      {p.isPromo && (
                        <span className="ml-2 text-[10px] bg-orange-100 text-orange-600 font-bold px-1.5 py-0.5 rounded-full leading-none">
                          {p.promoLabel ?? "promocja"}
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <span className={`font-black text-base ${i === 0 ? "text-green-600" : "text-gray-800"}`}>
                        {fmt(p.price)} zł
                      </span>
                      {p.isEstimate && <span className="block text-[10px] text-gray-400">szacowana</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="bg-white rounded-3xl shadow-sm p-8 text-center">
            <p className="text-5xl mb-3">🔍</p>
            <p className="text-gray-700 font-semibold">Brak cen dla tego produktu</p>
            <p className="text-gray-400 text-sm mt-2">
              Zobacz <Link href="/" className="text-green-600 underline">pełną porównywarkę</Link>.
            </p>
          </div>
        )}

        <section className="bg-white rounded-3xl shadow-sm p-6 mt-6">
          <h2 className="text-lg font-bold text-gray-900 mb-3">Jak porównujemy ceny {product.name}?</h2>
          <p className="text-gray-600 text-sm leading-relaxed">
            Codziennie skanujemy gazetki i ceny online w 7 największych sieciach w Polsce
            (Biedronka, Lidl, Kaufland, Aldi, Netto, Auchan, Carrefour) i pokazujemy, gdzie {product.name} jest
            najtańszy. Chcesz porównać cały koszyk? Wpisz listę zakupów na <Link href="/" className="text-green-600 underline">stronie głównej</Link>.
          </p>
        </section>

        <nav className="bg-white rounded-3xl shadow-sm p-6 mt-6">
          <h2 className="text-sm font-bold text-gray-400 uppercase tracking-widest mb-3">Sprawdź ceny innych produktów</h2>
          <div className="flex flex-wrap gap-2">
            {related.map((p) => (
              <Link
                key={p.id}
                href={`/cena/${slugify(p.name)}`}
                className="text-sm font-semibold text-gray-700 bg-gray-50 hover:bg-gray-100 rounded-full px-4 py-2"
              >
                {p.name}
              </Link>
            ))}
          </div>
        </nav>
      </div>
    </main>
  );
}
