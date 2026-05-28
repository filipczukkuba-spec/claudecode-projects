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

  // Find matching products (case-insensitive)
  const { data: products, error: prodError } = await supabase
    .from("products")
    .select("id, name, unit");

  if (prodError) return NextResponse.json({ error: prodError.message }, { status: 500 });

  const matchedProducts = products!.filter((p) =>
    itemNames.some((n) => p.name.toLowerCase().includes(n) || n.includes(p.name.toLowerCase()))
  );

  const matchedIds = matchedProducts.map((p) => p.id);

  // Get all prices + store info for matched products
  const { data: prices, error: priceError } = await supabase
    .from("prices")
    .select("store_id, product_id, price, stores(name, logo), products(name, unit)")
    .in("product_id", matchedIds.length > 0 ? matchedIds : [-1]);

  if (priceError) return NextResponse.json({ error: priceError.message }, { status: 500 });

  // Group by store
  const storeMap: Record<number, { name: string; logo: string; prices: { item: string; unit: string; price: number | null }[] }> = {};

  for (const row of prices as any[]) {
    const storeId: number = row.store_id;
    if (!storeMap[storeId]) {
      storeMap[storeId] = {
        name: row.stores.name,
        logo: row.stores.logo,
        prices: [],
      };
    }
    storeMap[storeId].prices.push({
      item: row.products.name,
      unit: row.products.unit,
      price: row.price,
    });
  }

  // For each requested item, if no match in DB mark as null
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
      };
    });
    return { ...store, prices: filledPrices };
  });

  return NextResponse.json({ results });
}
