import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

export const maxDuration = 60;

const STORE_PAGES: { store: string; url: string }[] = [
  { store: "Biedronka", url: "https://www.biedronka.pl/pl/oferta-tygodnia" },
  { store: "Lidl",      url: "https://www.lidl.pl/c/oferta-tygodnia/a10007519" },
  { store: "Kaufland",  url: "https://www.kaufland.pl/oferty/aktualne.html" },
  { store: "Aldi",      url: "https://www.aldi.pl/oferta-tygodnia.html" },
  { store: "Netto",     url: "https://www.netto.pl/gazetka-i-promocje/gazetka-tygodniowa" },
  { store: "Auchan",    url: "https://www.auchan.pl/pl/promocje" },
  { store: "Carrefour", url: "https://www.carrefour.pl/promocje" },
];

async function fetchPageText(url: string): Promise<string | null> {
  try {
    const res = await fetch(url, {
      headers: {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "pl-PL,pl;q=0.9",
        "Accept": "text/html,application/xhtml+xml",
      },
      signal: AbortSignal.timeout(8000),
    });
    if (!res.ok) return null;
    const html = await res.text();
    // Strip tags, collapse whitespace, keep only price-relevant lines
    return html
      .replace(/<script[\s\S]*?<\/script>/gi, "")
      .replace(/<style[\s\S]*?<\/style>/gi, "")
      .replace(/<[^>]+>/g, " ")
      .replace(/\s{2,}/g, " ")
      .slice(0, 12000); // keep first 12k chars for Claude
  } catch {
    return null;
  }
}

async function extractPricesWithClaude(
  storeText: string,
  storeName: string,
  knownProducts: string[]
): Promise<{ product: string; price: number; is_promo: boolean; label?: string }[]> {
  const knownList = knownProducts.slice(0, 150).join(", ");

  const message = await anthropic.messages.create({
    model: "claude-haiku-4-5",
    max_tokens: 1024,
    messages: [
      {
        role: "user",
        content: `You are extracting grocery prices from a Polish supermarket (${storeName}) webpage text.

Known products in our database (match to these exactly when possible):
${knownList}

Webpage text:
${storeText}

Extract all product-price pairs you can find. Return ONLY valid JSON array, no explanation:
[{"product":"exact product name from known list or closest match","price":4.99,"is_promo":true,"label":"-20%"}]

Rules:
- price must be a number (e.g. 4.99, not "4,99 zł")
- is_promo = true if it's a sale/promotion, false if regular price
- label = discount label if visible (e.g. "-20%", "2+1", null if not available)
- only include items with a clear price
- return [] if nothing found`,
      },
    ],
  });

  try {
    const text = message.content[0].type === "text" ? message.content[0].text : "";
    const jsonMatch = text.match(/\[[\s\S]*\]/);
    if (!jsonMatch) return [];
    return JSON.parse(jsonMatch[0]);
  } catch {
    return [];
  }
}

export async function POST(req: NextRequest) {
  const secret = req.headers.get("authorization")?.replace("Bearer ", "");
  if (secret !== process.env.CRON_SECRET && secret !== process.env.VERCEL_CRON_SECRET) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  // Load all products + stores from DB
  const Anthropic = (await import("@anthropic-ai/sdk")).default;
  const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

  const [{ data: products }, { data: stores }] = await Promise.all([
    supabase.from("products").select("id, name"),
    supabase.from("stores").select("id, name"),
  ]);

  if (!products || !stores) {
    return NextResponse.json({ error: "Failed to load DB" }, { status: 500 });
  }

  const storeIdMap = Object.fromEntries(stores.map((s) => [s.name, s.id]));
  const productNames = products.map((p) => p.name);

  const report: { store: string; fetched: boolean; extracted: number; updated: number; promotions: number }[] = [];
  const today = new Date().toISOString().split("T")[0];
  // promotions valid for 7 days (typical weekly flyer cycle)
  const validUntil = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split("T")[0];

  for (const { store, url } of STORE_PAGES) {
    const storeId = storeIdMap[store];
    if (!storeId) continue;

    const pageText = await fetchPageText(url);
    if (!pageText) {
      report.push({ store, fetched: false, extracted: 0, updated: 0, promotions: 0 });
      continue;
    }

    const extracted = await extractPricesWithClaude(pageText, store, productNames);

    let updated = 0;
    let promotions = 0;

    for (const item of extracted) {
      // Find matching product in DB (fuzzy)
      const dbProduct = products.find((p) =>
        p.name.toLowerCase() === item.product.toLowerCase() ||
        p.name.toLowerCase().includes(item.product.toLowerCase()) ||
        item.product.toLowerCase().includes(p.name.toLowerCase())
      );
      if (!dbProduct) continue;

      if (!item.is_promo) {
        // Update regular price
        const { error } = await supabase
          .from("prices")
          .update({ price: item.price, updated_at: new Date().toISOString() })
          .eq("store_id", storeId)
          .eq("product_id", dbProduct.id);
        if (!error) updated++;
      } else {
        // Insert promotion (upsert by store+product, keep newest)
        await supabase.from("promotions").upsert(
          {
            product_id: dbProduct.id,
            store_id: storeId,
            promo_price: item.price,
            promo_label: item.label ?? null,
            valid_from: today,
            valid_until: validUntil,
          },
          { onConflict: "store_id,product_id" }
        );
        promotions++;
      }
    }

    report.push({ store, fetched: true, extracted: extracted.length, updated, promotions });
  }

  return NextResponse.json({ ok: true, report, ran_at: new Date().toISOString() });
}

// Vercel Cron calls GET
export async function GET(req: NextRequest) {
  const authHeader = req.headers.get("authorization");
  if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  return POST(req);
}
