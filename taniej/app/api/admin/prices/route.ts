import { NextRequest, NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase-admin";

interface PriceUpdate {
  product_id: number;
  store_id: number;
  price: number;
}

function checkAuth(req: NextRequest) {
  const auth = req.headers.get("authorization");
  return auth === `Bearer ${process.env.ADMIN_PASSWORD}`;
}

export async function PATCH(req: NextRequest) {
  if (!checkAuth(req)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { updates }: { updates: PriceUpdate[] } = await req.json();

  if (!updates || updates.length === 0) {
    return NextResponse.json({ error: "No updates provided" }, { status: 400 });
  }

  const supabase = createAdminClient();

  const { error } = await supabase
    .from("prices")
    .upsert(
      updates.map((u) => ({ product_id: u.product_id, store_id: u.store_id, price: u.price })),
      { onConflict: "product_id,store_id" }
    );

  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  return NextResponse.json({ ok: true, count: updates.length });
}
