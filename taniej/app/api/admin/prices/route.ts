import { NextRequest, NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase-admin";

interface PriceUpdate {
  product_id: number;
  store_id: number;
  price?: number;
  app_price?: number;
}

function checkAuth(req: NextRequest) {
  return req.headers.get("authorization") === `Bearer ${process.env.ADMIN_PASSWORD}`;
}

export async function PATCH(req: NextRequest) {
  if (!checkAuth(req)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { updates, field = "price" }: { updates: PriceUpdate[]; field?: "price" | "app_price" } =
    await req.json();

  if (!updates || updates.length === 0) {
    return NextResponse.json({ error: "No updates" }, { status: 400 });
  }

  if (field !== "price" && field !== "app_price") {
    return NextResponse.json({ error: "Invalid field" }, { status: 400 });
  }

  const supabase = createAdminClient();

  const rows = updates.map((u) => ({
    product_id: u.product_id,
    store_id: u.store_id,
    [field]: u[field],
  }));

  const { error } = await supabase
    .from("prices")
    .upsert(rows, { onConflict: "product_id,store_id" });

  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  return NextResponse.json({ ok: true, count: updates.length, field });
}
