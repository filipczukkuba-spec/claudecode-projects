import { NextRequest, NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase-admin";

export const maxDuration = 30;

const MIN_REPORTS = 2;                // need 2+ receipts to trust a price
const REPORT_WINDOW_DAYS = 30;        // look at last 30 days of receipts
const AGREEMENT_TOLERANCE = 0.30;     // reports must agree within ±30%
const HARD_MAX_PRICE = 500;

// Promotes community-verified receipt prices into the main `prices` table.
// A (product, store) gets updated when 2+ recent receipts agree on the price.
//
// Single source: `source = 'community'` so the UI knows it's user-verified
// (and the existing scraper still wins when it has fresh data).
export async function POST(req: NextRequest) {
  const secret = req.headers.get("authorization")?.replace("Bearer ", "");
  if (secret !== process.env.CRON_SECRET && secret !== process.env.VERCEL_CRON_SECRET) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const admin = createAdminClient();
  const since = new Date(Date.now() - REPORT_WINDOW_DAYS * 86400_000).toISOString();

  const { data: reports, error } = await admin
    .from("price_reports")
    .select("product_id, store_id, price, source, is_promo, submitted_at")
    .gte("submitted_at", since)
    .limit(20000);

  if (error || !reports) {
    return NextResponse.json({ error: error?.message ?? "load_failed" }, { status: 500 });
  }

  // Group by product+store (only non-promo, source='receipt' reports count
  // toward "regular shelf price")
  const groups = new Map<string, number[]>();
  for (const r of reports as any[]) {
    if (r.is_promo) continue;
    if (r.source && r.source !== "receipt" && r.source !== "manual") continue;
    if (!Number.isFinite(r.price) || r.price <= 0 || r.price > HARD_MAX_PRICE) continue;
    const key = `${r.product_id}-${r.store_id}`;
    const arr = groups.get(key) ?? [];
    arr.push(r.price);
    groups.set(key, arr);
  }

  // Fetch current prices to know what we're updating
  const { data: currentPrices } = await admin
    .from("prices")
    .select("product_id, store_id, price, source");
  const currentMap = new Map<string, { price: number | null; source: string | null }>();
  for (const p of (currentPrices ?? []) as any[]) {
    currentMap.set(`${p.product_id}-${p.store_id}`, { price: p.price, source: p.source });
  }

  let promoted = 0;
  let skipped = 0;
  const updates: { product_id: number; store_id: number; price: number; source: string }[] = [];

  for (const [key, prices] of groups) {
    if (prices.length < MIN_REPORTS) { skipped++; continue; }

    prices.sort((a, b) => a - b);
    const median = prices[Math.floor(prices.length / 2)];

    // Reports must agree — at least 2 within ±30% of median
    const agreeing = prices.filter(
      (p) => Math.abs(p - median) / median <= AGREEMENT_TOLERANCE
    );
    if (agreeing.length < MIN_REPORTS) { skipped++; continue; }

    // Don't overwrite a fresh scraped price (it's authoritative)
    const current = currentMap.get(key);
    if (current?.source === "scraped") { skipped++; continue; }

    const [product_id, store_id] = key.split("-").map(Number);
    const finalPrice = parseFloat(
      (agreeing.reduce((s, p) => s + p, 0) / agreeing.length).toFixed(2)
    );

    updates.push({ product_id, store_id, price: finalPrice, source: "community" });
    promoted++;
  }

  if (updates.length > 0) {
    await admin.from("prices").upsert(updates, { onConflict: "product_id,store_id" });
  }

  return NextResponse.json({
    ok: true,
    groups_examined: groups.size,
    promoted,
    skipped,
    ran_at: new Date().toISOString(),
  });
}

export async function GET(req: NextRequest) {
  return POST(req);
}
