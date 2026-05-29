import { NextRequest, NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase-admin";

export const maxDuration = 60;

// Category pages per store — more products than promo-only pages
const STORE_PAGES: Record<string, string[]> = {
  Biedronka: [
    "https://www.biedronka.pl/pl/products?category=nabia%C5%82-i-jajka",
    "https://www.biedronka.pl/pl/products?category=mi%C4%99so-i-w%C4%99dliny",
    "https://www.biedronka.pl/pl/products?category=pieczywo",
    "https://www.biedronka.pl/pl/products?category=napoje",
    "https://www.biedronka.pl/pl/products?category=warzywa-i-owoce",
    "https://www.biedronka.pl/pl/oferta-tygodnia",
  ],
  Lidl: [
    "https://www.lidl.pl/c/nabiaal-i-jajka/c600",
    "https://www.lidl.pl/c/mieso-i-wedliny/c800",
    "https://www.lidl.pl/c/pieczywo/c700",
    "https://www.lidl.pl/c/oferta-tygodnia/a10007519",
  ],
  Kaufland: [
    "https://www.kaufland.pl/produkty/nabiaal-i-jajka.html",
    "https://www.kaufland.pl/produkty/mieso-i-wedliny.html",
    "https://www.kaufland.pl/oferty/aktualne.html",
  ],
  Aldi: [
    "https://www.aldi.pl/oferta-tygodnia.html",
    "https://www.aldi.pl/nabiaal.html",
  ],
  Netto: [
    "https://www.netto.pl/art-spozywcze-i-napoje/nabiaal",
    "https://www.netto.pl/gazetka-i-promocje/gazetka-tygodniowa",
  ],
  Auchan: [
    "https://www.auchan.pl/pl/produkty/nabiaal-i-jajka",
    "https://www.auchan.pl/pl/promocje",
  ],
  Carrefour: [
    "https://www.carrefour.pl/marka/nabiaal-i-jajka",
    "https://www.carrefour.pl/promocje",
  ],
};

// Apify cheerio-scraper: fetches pages with rotating proxies, returns clean text
async function fetchPagesViaApify(urls: string[]): Promise<{ url: string; text: string }[]> {
  const token = process.env.APIFY_TOKEN;
  if (!token || urls.length === 0) return [];

  try {
    const res = await fetch(
      `https://api.apify.com/v2/acts/apify~cheerio-scraper/run-sync-get-dataset-items?token=${token}&timeout=45&memory=256`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          startUrls: urls.map((url) => ({ url })),
          pageFunction: `async function pageFunction(context) {
            const { $, request } = context;
            $('script, style, nav, footer, header, .menu, .navigation, .cookie, .banner').remove();
            const text = $('body').text().replace(/\\s{2,}/g, ' ').trim().slice(0, 18000);
            return { url: request.url, text };
          }`,
          maxRequestsPerCrawl: urls.length,
          maxConcurrency: 2,
          proxyConfiguration: { useApifyProxy: true, apifyProxyGroups: ["RESIDENTIAL"] },
        }),
      }
    );
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

function norm(s: string): string {
  return s
    .toLowerCase()
    .replace(/ą/g, "a").replace(/ć/g, "c").replace(/ę/g, "e")
    .replace(/ł/g, "l").replace(/ń/g, "n").replace(/ó/g, "o")
    .replace(/ś/g, "s").replace(/ź/g, "z").replace(/ż/g, "z")
    .normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function matchScore(query: string, target: string): number {
  const q = norm(query);
  const t = norm(target);
  if (q === t) return 1;
  if (t.includes(q) || q.includes(t)) return 0.9;
  const qTokens = q.split(" ").filter(Boolean);
  const tTokens = t.split(" ").filter(Boolean);
  const matched = qTokens.filter((qt) => tTokens.some((tt) => tt.includes(qt) || qt.includes(tt)));
  return matched.length / qTokens.length;
}

async function extractPrices(
  pageTexts: { url: string; text: string }[],
  storeName: string,
  knownProducts: string[]
): Promise<{ product: string; price: number; is_promo: boolean; label?: string | null }[]> {
  const Anthropic = (await import("@anthropic-ai/sdk")).default;
  const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

  const combined = pageTexts.map((p) => `[${p.url}]\n${p.text}`).join("\n\n---\n\n").slice(0, 25000);
  const knownList = knownProducts.slice(0, 300).join(", ");

  try {
    const msg = await anthropic.messages.create({
      model: "claude-haiku-4-5-20251001",
      max_tokens: 2000,
      messages: [
        {
          role: "user",
          content: `You are extracting grocery prices from a Polish supermarket (${storeName}).

Known products in our database:
${knownList}

Page content from ${storeName}:
${combined}

Extract prices for as many known products as possible.
Return ONLY a JSON array, no explanation:
[{"product":"exact name from known list","price":4.99,"is_promo":false,"label":null}]

Rules:
- "product" must be the exact string from the known products list
- "price" is a decimal number (use the lowest/sale price if multiple)
- "is_promo" is true if it's a promotional/sale price
- "label" is the promo label (e.g. "-20%", "2+1") or null
- Skip products not in the known list
- Return [] if nothing matches`,
        },
      ],
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

  const supabase = createAdminClient();

  const [{ data: products }, { data: stores }] = await Promise.all([
    supabase.from("products").select("id, name"),
    supabase.from("stores").select("id, name"),
  ]);

  if (!products || !stores) return NextResponse.json({ error: "DB load failed" }, { status: 500 });

  const storeIdMap = Object.fromEntries(stores.map((s) => [s.name, s.id]));
  const productNames = products.map((p) => p.name);
  const today = new Date().toISOString().split("T")[0];
  const validUntil = new Date(Date.now() + 7 * 86400000).toISOString().split("T")[0];

  const report: Record<string, { pages: number; extracted: number; updated: number; promos: number; error?: string }> = {};

  // Process stores in batches of 2 to stay within 60s
  const storeEntries = Object.entries(STORE_PAGES);

  for (const [storeName, urls] of storeEntries) {
    const storeId = storeIdMap[storeName];
    if (!storeId) continue;

    try {
      // Fetch pages via Apify
      const pageTexts = await fetchPagesViaApify(urls.slice(0, 3)); // max 3 pages per store per run

      if (pageTexts.length === 0) {
        report[storeName] = { pages: 0, extracted: 0, updated: 0, promos: 0, error: "fetch_failed" };
        continue;
      }

      // Extract prices with Claude
      const items = await extractPrices(pageTexts, storeName, productNames);
      let updated = 0;
      let promos = 0;

      const priceUpdates: { product_id: number; store_id: number; price: number }[] = [];
      const promoUpdates: any[] = [];

      for (const item of items) {
        const best = products
          .map((p) => ({ p, score: matchScore(item.product, p.name) }))
          .filter(({ score }) => score >= 0.7)
          .sort((a, b) => b.score - a.score)[0];

        if (!best) continue;

        if (item.is_promo) {
          promoUpdates.push({
            product_id: best.p.id,
            store_id: storeId,
            promo_price: item.price,
            promo_label: item.label ?? null,
            valid_from: today,
            valid_until: validUntil,
          });
          promos++;
        } else {
          priceUpdates.push({ product_id: best.p.id, store_id: storeId, price: item.price });
          updated++;
        }
      }

      // Bulk upsert
      if (priceUpdates.length > 0) {
        await supabase.from("prices").upsert(priceUpdates, { onConflict: "product_id,store_id" });
      }
      if (promoUpdates.length > 0) {
        await (supabase as any).from("promotions").upsert(promoUpdates, { onConflict: "store_id,product_id" });
      }

      report[storeName] = { pages: pageTexts.length, extracted: items.length, updated, promos };
    } catch (e: any) {
      report[storeName] = { pages: 0, extracted: 0, updated: 0, promos: 0, error: e.message };
    }
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
