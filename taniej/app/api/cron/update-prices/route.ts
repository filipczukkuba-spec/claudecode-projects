import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

export const maxDuration = 60;

// Store search URLs — these are public-facing search pages / APIs
const STORE_SEARCH: Record<string, (q: string) => string> = {
  Biedronka: (q) => `https://www.biedronka.pl/pl/products?phrase=${encodeURIComponent(q)}&page=1`,
  Lidl:      (q) => `https://www.lidl.pl/p/s?q=${encodeURIComponent(q)}`,
  Kaufland:  (q) => `https://www.kaufland.pl/search?search_value=${encodeURIComponent(q)}`,
  Netto:     (q) => `https://www.netto.pl/wyszukaj?query=${encodeURIComponent(q)}`,
};

const PROMO_PAGES: Record<string, string> = {
  Biedronka: "https://www.biedronka.pl/pl/oferta-tygodnia",
  Lidl:      "https://www.lidl.pl/c/oferta-tygodnia/a10007519",
  Kaufland:  "https://www.kaufland.pl/oferty/aktualne.html",
  Aldi:      "https://www.aldi.pl/oferta-tygodnia.html",
  Netto:     "https://www.netto.pl/gazetka-i-promocje/gazetka-tygodniowa",
  Auchan:    "https://www.auchan.pl/pl/promocje",
  Carrefour: "https://www.carrefour.pl/promocje",
};

const FETCH_HEADERS = {
  "User-Agent": "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36",
  "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.5",
  "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
  "Accept-Encoding": "gzip, deflate, br",
  "Cache-Control": "no-cache",
};

async function fetchText(url: string): Promise<string | null> {
  try {
    const res = await fetch(url, {
      headers: FETCH_HEADERS,
      signal: AbortSignal.timeout(7000),
    });
    if (!res.ok) return null;
    const html = await res.text();
    return html
      .replace(/<script[\s\S]*?<\/script>/gi, "")
      .replace(/<style[\s\S]*?<\/style>/gi, "")
      .replace(/<[^>]+>/g, " ")
      .replace(/\s{2,}/g, " ")
      .slice(0, 15000);
  } catch {
    return null;
  }
}

async function extractPricesWithClaude(text: string, storeName: string, knownProducts: string[]): Promise<{ product: string; price: number; is_promo: boolean; label?: string }[]> {
  const Anthropic = (await import("@anthropic-ai/sdk")).default;
  const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

  const knownList = knownProducts.slice(0, 200).join(", ");

  try {
    const msg = await anthropic.messages.create({
      model: "claude-haiku-4-5",
      max_tokens: 1500,
      messages: [{
        role: "user",
        content: `Extract grocery prices from this ${storeName} page. Known products: ${knownList}

Page text: ${text}

Return ONLY a JSON array (no explanation):
[{"product":"exact name from known list","price":4.99,"is_promo":false,"label":null}]

Rules: price is a number, is_promo=true if sale/promotion, label = discount label or null, return [] if nothing found.`,
      }],
    });

    const raw = msg.content[0].type === "text" ? msg.content[0].text : "";
    const match = raw.match(/\[[\s\S]*\]/);
    if (!match) return [];
    return JSON.parse(match[0]);
  } catch {
    return [];
  }
}

export async function POST(req: NextRequest) {
  const secret = req.headers.get("authorization")?.replace("Bearer ", "");
  if (secret !== process.env.CRON_SECRET && secret !== process.env.VERCEL_CRON_SECRET) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const [{ data: products }, { data: stores }] = await Promise.all([
    supabase.from("products").select("id, name"),
    supabase.from("stores").select("id, name"),
  ]);

  if (!products || !stores) return NextResponse.json({ error: "DB load failed" }, { status: 500 });

  const storeIdMap = Object.fromEntries(stores.map((s) => [s.name, s.id]));
  const productNames = products.map((p) => p.name);
  const today = new Date().toISOString().split("T")[0];
  const validUntil = new Date(Date.now() + 7 * 86400000).toISOString().split("T")[0];

  const report: Record<string, { fetched: boolean; extracted: number; updated: number; promos: number }> = {};

  for (const [storeName, promoUrl] of Object.entries(PROMO_PAGES)) {
    const storeId = storeIdMap[storeName];
    if (!storeId) continue;

    const text = await fetchText(promoUrl);
    if (!text) { report[storeName] = { fetched: false, extracted: 0, updated: 0, promos: 0 }; continue; }

    const items = await extractPricesWithClaude(text, storeName, productNames);
    let updated = 0, promos = 0;

    for (const item of items) {
      const dbProduct = products.find((p) =>
        p.name.toLowerCase() === item.product.toLowerCase() ||
        p.name.toLowerCase().includes(item.product.toLowerCase()) ||
        item.product.toLowerCase().includes(p.name.toLowerCase())
      );
      if (!dbProduct) continue;

      if (item.is_promo) {
        await (supabase as any).from("promotions").upsert(
          { product_id: dbProduct.id, store_id: storeId, promo_price: item.price, promo_label: item.label ?? null, valid_from: today, valid_until: validUntil },
          { onConflict: "store_id,product_id" }
        );
        promos++;
      } else {
        await supabase.from("prices")
          .update({ price: item.price })
          .eq("store_id", storeId)
          .eq("product_id", dbProduct.id);
        updated++;
      }
    }

    report[storeName] = { fetched: true, extracted: items.length, updated, promos };
  }

  return NextResponse.json({ ok: true, report, ran_at: new Date().toISOString() });
}

export async function GET(req: NextRequest) {
  const authHeader = req.headers.get("authorization");
  if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  return POST(req);
}
