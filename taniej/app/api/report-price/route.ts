import { NextRequest, NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase-admin";

export const maxDuration = 10;

export async function POST(req: NextRequest) {
  const { product_id, store_id, price, city } = await req.json();

  if (!product_id || !store_id || !price || price <= 0 || price > 9999) {
    return NextResponse.json({ error: "Invalid input" }, { status: 400 });
  }

  const admin = createAdminClient();
  const { error } = await admin.from("price_reports" as any).insert({
    product_id,
    store_id,
    price: parseFloat(parseFloat(price).toFixed(2)),
    city: city?.trim()?.slice(0, 50) || null,
  });

  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ ok: true });
}
