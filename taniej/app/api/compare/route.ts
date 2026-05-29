import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

export const maxDuration = 10;

interface RequestItem {
  name: string;
  unit: string;
}

// Remove Polish diacritics and normalise to lowercase a-z0-9 tokens
function norm(s: string): string {
  return s
    .toLowerCase()
    .replace(/ą/g, "a").replace(/ć/g, "c").replace(/ę/g, "e")
    .replace(/ł/g, "l").replace(/ń/g, "n").replace(/ó/g, "o")
    .replace(/ś/g, "s").replace(/ź/g, "z").replace(/ż/g, "z")
    .normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function matchScore(query: string, target: string): number {
  const q = norm(query);
  const t = norm(target);
  if (q === t) return 1;
  if (t.includes(q) || q.includes(t)) return 0.9;
  const qTokens = q.split(" ").filter(Boolean);
  const tTokens = t.split(" ").filter(Boolean);
  const matched = qTokens.filter((qt) =>
    tTokens.some((tt) => tt.includes(qt) || qt.includes(tt))
  );
  return matched.length / qTokens.length;
}

const MATCH_THRESHOLD = 0.6;

export async function POST(req: NextRequest) {
  const { items }: { items: RequestItem[] } = await req.json();

  if (!items || items.length === 0) {
    return NextResponse.json({ error: "No items provided" }, { status: 400 });
  }

  const itemNames = items.map((i) => i.name.toLowerCase());

  const { data: products, error: prodError } = await supabase
    .from("products")
    .select("id, name, unit");

  if (prodError) return NextResponse.json({ error: prodError.message }, { status: 500 });

  const matchedProducts = products!.filter((p) =>
    itemNames.some((n) => matchScore(n, p.name) >= MATCH_THRESHOLD)
  );

  const matchedIds = matchedProducts.map((p) => p.id);

  const { data: prices, error: priceError } = await supabase
    .from("prices")
    .select("store_id, product_id, price, app_price, stores(name, logo), products(name, unit)")
    .in("product_id", matchedIds.length > 0 ? matchedIds : [-1]);

  if (priceError) return NextResponse.json({ error: priceError.message }, { status: 500 });

  // Fetch active promotions separately (non-blocking — silently skip if unavailable)
  const promoMap = new Map<string, { promo_price: number; promo_label: string | null }>();
  if (matchedIds.length > 0) {
    const today = new Date().toISOString().split("T")[0];
    const { data: promoData } = await (supabase as any)
      .from("promotions")
      .select("store_id, product_id, promo_price, promo_label")
      .in("product_id", matchedIds)
      .lte("valid_from", today)
      .gte("valid_until", today);

    for (const p of (promoData ?? []) as any[]) {
      promoMap.set(`${p.store_id}-${p.product_id}`, {
        promo_price: p.promo_price,
        promo_label: p.promo_label,
      });
    }
  }

  // Group by store
  const storeMap: Record<string, { name: string; logo: string; prices: any[] }> = {};

  for (const row of prices as any[]) {
    const sid: number = row.store_id;
    const key = String(sid);
    if (!storeMap[key]) {
      storeMap[key] = { name: row.stores.name, logo: row.stores.logo, prices: [] };
    }
    const promo = promoMap.get(`${sid}-${row.product_id}`) ?? null;
    storeMap[key].prices.push({
      item: row.products.name,
      unit: row.products.unit,
      price: row.price,
      app_price: row.app_price ?? null,
      promo_price: promo?.promo_price ?? null,
      promo_label: promo?.promo_label ?? null,
    });
  }

  const results = Object.values(storeMap).map((store) => {
    const filledPrices = items.map((item) => {
      const found = store.prices
        .map((p: any) => ({ p, score: matchScore(item.name, p.item) }))
        .filter(({ score }) => score >= MATCH_THRESHOLD)
        .sort((a: any, b: any) => b.score - a.score)[0]?.p;
      return {
        item: item.name,
        unit: item.unit || found?.unit || "",
        price: found?.price ?? null,
        app_price: found?.app_price ?? null,
        promo_price: found?.promo_price ?? null,
        promo_label: found?.promo_label ?? null,
      };
    });
    return { ...store, prices: filledPrices };
  });

  return NextResponse.json({ results });
}
