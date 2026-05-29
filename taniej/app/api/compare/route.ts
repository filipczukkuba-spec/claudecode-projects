import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";
import { createAdminClient } from "@/lib/supabase-admin";
import { matchScore, MATCH_THRESHOLD } from "@/lib/matching";

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
    itemNames.some((n) => matchScore(n, p.name) >= MATCH_THRESHOLD)
  );

  const matchedIds = matchedProducts.map((p) => p.id);

  const { data: prices, error: priceError } = await supabase
    .from("prices")
    .select("store_id, product_id, price, app_price, stores(name, logo), products(name, unit)")
    .in("product_id", matchedIds.length > 0 ? matchedIds : [-1]);

  if (priceError) return NextResponse.json({ error: priceError.message }, { status: 500 });

  const admin = createAdminClient();
  const today = new Date().toISOString().split("T")[0];
  const sevenDaysAgo = new Date(Date.now() - 7 * 86400000).toISOString();

  // Fetch active promotions
  const promoMap = new Map<string, { promo_price: number; promo_label: string | null }>();
  if (matchedIds.length > 0) {
    const { data: promoData } = await admin
      .from("promotions" as any)
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

  // Fetch recent user-submitted shelf prices (last 7 days)
  // Keep only the most recent report per product+store
  const reportMap = new Map<string, { price: number; submitted_at: string; city: string | null }>();
  if (matchedIds.length > 0) {
    const { data: reportData } = await admin
      .from("price_reports" as any)
      .select("store_id, product_id, price, submitted_at, city")
      .in("product_id", matchedIds)
      .gte("submitted_at", sevenDaysAgo)
      .order("submitted_at", { ascending: false });

    for (const r of (reportData ?? []) as any[]) {
      const key = `${r.store_id}-${r.product_id}`;
      if (!reportMap.has(key)) {
        reportMap.set(key, {
          price: r.price,
          submitted_at: r.submitted_at,
          city: r.city,
        });
      }
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
    const report = reportMap.get(`${sid}-${row.product_id}`) ?? null;
    storeMap[key].prices.push({
      item: row.products.name,
      unit: row.products.unit,
      product_id: row.product_id,
      store_id: sid,
      price: row.price,
      app_price: row.app_price ?? null,
      promo_price: promo?.promo_price ?? null,
      promo_label: promo?.promo_label ?? null,
      reported_price: report?.price ?? null,
      reported_at: report?.submitted_at ?? null,
      reported_city: report?.city ?? null,
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
        product_id: found?.product_id ?? null,
        store_id: found?.store_id ?? null,
        price: found?.price ?? null,
        app_price: found?.app_price ?? null,
        promo_price: found?.promo_price ?? null,
        promo_label: found?.promo_label ?? null,
        reported_price: found?.reported_price ?? null,
        reported_at: found?.reported_at ?? null,
        reported_city: found?.reported_city ?? null,
      };
    });
    return { ...store, prices: filledPrices };
  });

  return NextResponse.json({ results });
}
