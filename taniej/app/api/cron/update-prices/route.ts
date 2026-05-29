import { NextRequest, NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase-admin";
import { matchScore } from "@/lib/matching";
import { sendEmail } from "@/lib/email";

export const maxDuration = 60;

// Browser-like headers to avoid bot detection
const HEADERS = {
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
  "Accept": "text/html,application/xhtml+xml,application/xhtml+xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
  "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
  "Accept-Encoding": "gzip, deflate, br",
  "Cache-Control": "no-cache",
  "Pragma": "no-cache",
};

// Pages to fetch per store — start with lightweight promotion pages
const STORE_PAGES: Record<string, string[]> = {
  Biedronka: [
    "https://www.biedronka.pl/pl/oferta-tygodnia",
    "https://www.biedronka.pl/pl/products?category=nabia%C5%82-i-jajka",
    "https://www.biedronka.pl/pl/products?category=mi%C4%99so-i-w%C4%99dliny",
  ],
  Lidl: [
    "https://www.lidl.pl/c/oferta-tygodnia/a10007519",
    "https://www.lidl.pl/c/nabiaal-i-jajka/c600",
    "https://www.lidl.pl/c/mieso-i-wedliny/c800",
  ],
  Kaufland: [
    "https://www.kaufland.pl/oferty/aktualne.html",
    "https://www.kaufland.pl/produkty/nabiaal-i-jajka.html",
  ],
  Aldi: [
    "https://www.aldi.pl/oferta-tygodnia.html",
    "https://www.aldi.pl/nabiaal.html",
  ],
  Netto: [
    "https://www.netto.pl/gazetka-i-promocje/gazetka-tygodniowa",
    "https://www.netto.pl/art-spozywcze-i-napoje/nabiaal",
  ],
  Auchan: [
    "https://www.auchan.pl/pl/promocje",
    "https://www.auchan.pl/pl/produkty/nabiaal-i-jajka",
  ],
  Carrefour: [
    "https://www.carrefour.pl/promocje",
    "https://www.carrefour.pl/marka/nabiaal-i-jajka",
  ],
};

async function fetchPage(url: string): Promise<string> {
  try {
    const ctrl = new AbortController();
    const timeout = setTimeout(() => ctrl.abort(), 12000);
    const res = await fetch(url, {
      headers: HEADERS,
      signal: ctrl.signal,
      redirect: "follow",
    });
    clearTimeout(timeout);
    if (!res.ok) return "";
    const html = await res.text();
    // Strip tags, collapse whitespace, cap at 20k chars
    return html
      .replace(/<script[\s\S]*?<\/script>/gi, "")
      .replace(/<style[\s\S]*?<\/style>/gi, "")
      .replace(/<[^>]+>/g, " ")
      .replace(/&nbsp;/g, " ")
      .replace(/&amp;/g, "&")
      .replace(/&lt;/g, "<")
      .replace(/&gt;/g, ">")
      .replace(/\s{2,}/g, " ")
      .trim()
      .slice(0, 20000);
  } catch {
    return "";
  }
}

// If direct fetch fails, try Apify as fallback (requires paid plan)
async function fetchViaApify(urls: string[]): Promise<{ url: string; text: string }[]> {
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
            $('script, style, nav, footer, header, .menu, .navigation, .cookie').remove();
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
          content: `Extract grocery prices from Polish supermarket "${storeName}".

Known products (use exact names):
${knownList}

Page content:
${combined}

Return ONLY a JSON array:
[{"product":"exact name from list","price":4.99,"is_promo":false,"label":null}]

Rules:
- product = exact string from known list above
- price = decimal number, use promo/sale price if shown
- is_promo = true if promotional/sale price
- label = promo label like "-20%", "2+1", or null
- Skip products not in the known list
- Return [] if nothing found`,
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

  const report: Record<string, {
    pages: number; fetched: number; extracted: number;
    updated: number; promos: number; method: string; error?: string;
  }> = {};

  const storeEntries = Object.entries(STORE_PAGES);

  for (const [storeName, urls] of storeEntries) {
    const storeId = storeIdMap[storeName];
    if (!storeId) continue;

    try {
      // Try direct fetch first (free, no proxy needed)
      let pageTexts: { url: string; text: string }[] = [];
      let method = "direct";

      const directResults = await Promise.all(
        urls.slice(0, 2).map(async (url) => {
          const text = await fetchPage(url);
          return text ? { url, text } : null;
        })
      );

      pageTexts = directResults.filter((r): r is { url: string; text: string } => r !== null && r.text.length > 500);

      // Fallback to Apify if direct fetch got nothing useful
      if (pageTexts.length === 0) {
        method = "apify";
        pageTexts = await fetchViaApify(urls.slice(0, 2));
      }

      if (pageTexts.length === 0) {
        report[storeName] = { pages: 0, fetched: 0, extracted: 0, updated: 0, promos: 0, method, error: "fetch_failed" };
        continue;
      }

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

      if (priceUpdates.length > 0) {
        await supabase.from("prices").upsert(priceUpdates, { onConflict: "product_id,store_id" });
      }
      if (promoUpdates.length > 0) {
        await supabase.from("promotions" as any).upsert(promoUpdates, { onConflict: "store_id,product_id" });
      }

      report[storeName] = {
        pages: urls.slice(0, 2).length,
        fetched: pageTexts.length,
        extracted: items.length,
        updated,
        promos,
        method,
      };
    } catch (e: any) {
      report[storeName] = { pages: 0, fetched: 0, extracted: 0, updated: 0, promos: 0, method: "error", error: e.message };
    }
  }

  const totalUpdated = Object.values(report).reduce((s, r) => s + r.updated + r.promos, 0);
  const successStores = Object.entries(report).filter(([, r]) => !r.error).map(([n]) => n);
  const failedStores = Object.entries(report).filter(([, r]) => r.error).map(([n]) => n);

  await sendEmail(
    `taniejkupuj — sync zakończony (${totalUpdated} cen)`,
    `<h2>Sync cen zakończony</h2>
    <p><b>Zaktualizowano:</b> ${totalUpdated} cen</p>
    <p><b>Sklepy OK:</b> ${successStores.join(", ") || "brak"}</p>
    ${failedStores.length > 0 ? `<p><b>Błędy:</b> ${failedStores.join(", ")}</p>` : ""}
    <pre style="background:#f5f5f5;padding:12px;border-radius:8px;font-size:12px">${JSON.stringify(report, null, 2)}</pre>
    <p style="color:#999;font-size:12px">taniejkupuj.pl · ${new Date().toLocaleString("pl-PL")}</p>`
  );

  return NextResponse.json({ ok: true, report, ran_at: new Date().toISOString() });
}

export async function GET(req: NextRequest) {
  const authHeader = req.headers.get("authorization");
  if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  return POST(req);
}
