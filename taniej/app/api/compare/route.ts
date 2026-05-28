import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

export const maxDuration = 10;

interface RequestItem {
  name: string;
  unit: string;
}

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
    itemNames.some((n) => p.name.toLowerCase().includes(n) || n.includes(p.name.toLowerCase()))
  );

  const matchedIds = matchedProducts.map((p) => p.id);

  const [pricesResult, promosResult] = await Promise.all([
    supabase
      .from("prices")
      .select("store_id, product_id, price, stores(name, logo), products(name, unit)")
      .in("product_id", matchedIds.length > 0 ? matchedIds : [-1]),
    supabase
      .from("promotions")
      .select("store_id, product_id, promo_price, promo_label")
      .in("product_id", matchedIds.length > 0 ? matchedIds : [-1])
      .lte("valid_from", new Date().toISOString().split("T")[0])
      .gte("valid_until", new Date().toISOString().split("T")[0]),
  ]);

  if (pricesResult.error) return NextResponse.json({ error: pricesResult.error.message }, { status: 500 });

  // Build promo lookup: store_id -> product_id -> { promo_price, promo_label }
  const promoMap: Record<number, Record<number, { promo_price: number; promo_label: string | null }>> = {};
  for (const row of (promosResult.data ?? []) as any[]) {
    if (!promoMap[row.store_id]) promoMap[row.store_id] = {};
    promoMap[row.store_id][row.product_id] = {
      promo_price: row.promo_price,
      promo_label: row.promo_label,
    };
  }

  // Group by store
  const storeMap: Record<number, { name: string; logo: string; prices: { item: string; unit: string; price: number | null; promo_price: number | null; promo_label: string | null; product_id: number }[] }> = {};

  for (const row of pricesResult.data as any[]) {
    const storeId: number = row.store_id;
    if (!storeMap[storeId]) {
      storeMap[storeId] = { name: row.stores.name, logo: row.stores.logo, prices: [] };
    }
    const promo = promoMap[storeId]?.[row.product_id] ?? null;
    storeMap[storeId].prices.push({
      item: row.products.name,
      unit: row.products.unit,
      price: row.price,
      promo_price: promo?.promo_price ?? null,
      promo_label: promo?.promo_label ?? null,
      product_id: row.product_id,
    });
  }

  const results = Object.values(storeMap).map((store) => {
    const filledPrices = items.map((item) => {
      const found = store.prices.find((p) =>
        p.item.toLowerCase().includes(item.name.toLowerCase()) ||
        item.name.toLowerCase().includes(p.item.toLowerCase())
      );
      return {
        item: item.name,
        unit: item.unit || found?.unit || "",
        price: found?.price ?? null,
        promo_price: found?.promo_price ?? null,
        promo_label: found?.promo_label ?? null,
      };
    });
    return { ...store, prices: filledPrices };
  });

  return NextResponse.json({ results, _debug: { matchedIds, promoCount: (promosResult.data ?? []).length, promoError: promosResult.error?.message ?? null } });
}
