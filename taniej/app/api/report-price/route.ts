import { NextRequest, NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase-admin";

export const maxDuration = 10;

const HARD_MAX_PRICE = 500; // No grocery item costs more than this — joke filter
const SANITY_MULTIPLIER = 3; // Reject reports >3x the known scraped/estimated price

export async function POST(req: NextRequest) {
  const { product_id, store_id, price, city } = await req.json();

  if (!product_id || !store_id || !price || price <= 0 || price > HARD_MAX_PRICE) {
    return NextResponse.json(
      { error: `Cena musi być w zakresie 0–${HARD_MAX_PRICE} zł` },
      { status: 400 }
    );
  }

  const admin = createAdminClient();

  // Sanity check against the trusted reference price (scraped/estimated/app/promo).
  const { data: ref } = await admin
    .from("prices")
    .select("price, app_price")
    .eq("product_id", product_id)
    .eq("store_id", store_id)
    .maybeSingle();

  const refPrice = ref
    ? Math.min(...[ref.price, ref.app_price].filter((v): v is number => v != null && v > 0))
    : null;

  if (refPrice && Number.isFinite(refPrice) && price > refPrice * SANITY_MULTIPLIER) {
    return NextResponse.json(
      {
        error: `Cena wygląda na pomyłkę — ${SANITY_MULTIPLIER}× wyższa niż znana cena ${refPrice.toFixed(2)} zł. Sprawdź wartość.`,
      },
      { status: 400 }
    );
  }

  const { error } = await admin.from("price_reports" as any).insert({
    product_id,
    store_id,
    price: parseFloat(parseFloat(price).toFixed(2)),
    city: city?.trim()?.slice(0, 50) || null,
  });

  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ ok: true });
}
