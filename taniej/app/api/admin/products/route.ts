import { NextRequest, NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase-admin";

function checkAuth(req: NextRequest) {
  const auth = req.headers.get("authorization");
  return auth === `Bearer ${process.env.ADMIN_PASSWORD}`;
}

export async function GET(req: NextRequest) {
  if (!checkAuth(req)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const supabase = createAdminClient();

  const [{ data: products, error: pe }, { data: stores, error: se }, { data: prices, error: pre }] =
    await Promise.all([
      supabase.from("products").select("id, name, unit").order("name"),
      supabase.from("stores").select("id, name").order("name"),
      supabase.from("prices").select("product_id, store_id, price"),
    ]);

  if (pe) return NextResponse.json({ error: pe.message }, { status: 500 });
  if (se) return NextResponse.json({ error: se.message }, { status: 500 });
  if (pre) return NextResponse.json({ error: pre.message }, { status: 500 });

  return NextResponse.json({ products, stores, prices });
}
