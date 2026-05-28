import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

export const maxDuration = 60;

// Called daily by Vercel Cron (see vercel.json)
// Also callable manually: POST /api/cron/update-prices with { secret: CRON_SECRET }
export async function POST(req: NextRequest) {
  const secret = req.headers.get("authorization")?.replace("Bearer ", "");
  if (secret !== process.env.CRON_SECRET && secret !== process.env.VERCEL_CRON_SECRET) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  // --- Plug in your real price source here ---
  // Example: fetch from Apify, a price API, or a Google Sheet
  // const prices = await fetchFromApify();
  //
  // Each entry should look like:
  // { store_id: 1, product_id: 5, price: 4.99 }
  //
  // Then upsert:
  // await supabase.from("prices").upsert(prices, { onConflict: "store_id,product_id" });
  // -------------------------------------------

  // For now: just return the last-updated timestamps so you can see when prices were set
  const { data } = await supabase
    .from("prices")
    .select("updated_at")
    .order("updated_at", { ascending: false })
    .limit(1);

  return NextResponse.json({
    ok: true,
    last_updated: data?.[0]?.updated_at ?? null,
    message: "Cron ran — connect a price source in this file to update prices automatically",
  });
}

// Vercel Cron calls GET
export async function GET(req: NextRequest) {
  const authHeader = req.headers.get("authorization");
  if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  return POST(req);
}
