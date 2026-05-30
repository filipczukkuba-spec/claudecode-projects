import { NextRequest, NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase-admin";
import { matchScore } from "@/lib/matching";
import { sendEmail } from "@/lib/email";
import { fetchViaJina, fetchViaFirecrawl } from "@/lib/price-extractor";

export const maxDuration = 60;

// ── Store pages ─────────────────────────────────────────────────────────────
// fetcher: "jina" = free, no key needed. "firecrawl" = needs FIRECRAWL_API_KEY,
// handles Cloudflare + JS-rendered product grids (500 pages/month free tier).

type StoreConfig = { urls: string[]; fetcher: "jina" | "firecrawl" };

const STORES: Record<string, StoreConfig> = {
  // Aldi: Jina works well — plain HTML offers page
  Aldi: {
    fetcher: "jina",
    urls: [
      "https://www.aldi.pl/oferty/",
      "https://www.aldi.pl/produkty/swieze-produkty/nabiał-i-jajka.html",
      "https://www.aldi.pl/produkty/swieze-produkty/mieso-i-wedliny.html",
      "https://www.aldi.pl/produkty/swieze-produkty/pieczywo.html",
    ],
  },
  // Lidl: both Jina and Firecrawl returning empty — skip until better approach found
  // Netto: Jina gazetka working
  Netto: {
    fetcher: "jina",
    urls: [
      "https://www.netto.pl/",
      "https://www.netto.pl/gazetka-tygodniowa/",
    ],
  },
  // Biedronka: every page shows mobile app overlay — skip
  // Kaufland: category pages all fail, main page intermittent — keep trying
  Kaufland: {
    fetcher: "firecrawl",
    urls: [
      "https://www.kaufland.pl/",
    ],
  },
  // Carrefour: 2 pages confirmed working — keep only those 2, drop failing category pages
  Carrefour: {
    fetcher: "firecrawl",
    urls: [
      "https://www.carrefour.pl/artykuly-spozywcze/",
      "https://www.carrefour.pl/mieso-ryby-i-owoce-morza/",
    ],
  },
  // Auchan: completely blocked — skip
};

// ── Claude extraction ────────────────────────────────────────────────────────

interface ClaudeItem {
  product: string;
  price: number;
  is_promo: boolean;
  label: string | null;
  original_price?: number | null;
}

async function claudeExtract(
  texts: string[],
  storeName: string,
): Promise<ClaudeItem[]> {
  if (!process.env.ANTHROPIC_API_KEY || texts.length === 0) return [];

  const Anthropic = (await import("@anthropic-ai/sdk")).default;
  const ai = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

  // Use all pages, up to 40000 chars total
  const combined = texts.join("\n\n---PAGE BREAK---\n\n").slice(0, 40000);

  try {
    const msg = await ai.messages.create({
      model: "claude-haiku-4-5-20251001",
      max_tokens: 8000,
      messages: [
        {
          role: "user",
          content: `You are a price extraction engine. Extract every grocery product price from this ${storeName} page.

Page content:
${combined}

Output a JSON array. Every item must have:
- "product": exact name from page (Polish, e.g. "Mleko UHT 3,2% 1L", "Pierś z kurczaka kg")
- "price": current price as decimal number (PLN), e.g. 3.49
- "is_promo": true if sale/promo price, false otherwise
- "label": promo label string like "-20%", "2+1", "Cena tygodnia", or null
- "original_price": regular price before discount as decimal, or null

Critical rules:
- Extract EVERY product with a visible price — aim for 50+ items per page
- Price must be 0.20–999 PLN range
- Use the PROMO price if both regular and promo are shown (set is_promo=true, original_price=regular)
- Include weight/volume in product name when shown (e.g. "1L", "kg", "500g")
- Skip: navigation links, store hours, delivery fees, membership fees, non-food items
- Return [] only if the page is a 404 / cookie consent / pure navigation with zero prices

Start your response directly with [ (the JSON array):`,
        },
      ],
    });

    const raw = msg.content[0].type === "text" ? msg.content[0].text : "";
    const match = raw.match(/\[[\s\S]*\]/);
    if (!match) return [];
    return JSON.parse(match[0]) as ClaudeItem[];
  } catch {
    return [];
  }
}

// ── Main handler ─────────────────────────────────────────────────────────────

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

  if (!products || !stores) {
    return NextResponse.json({ error: "DB load failed" }, { status: 500 });
  }

  const storeIdMap = Object.fromEntries(stores.map((s) => [s.name, s.id]));
  const today = new Date().toISOString().split("T")[0];
  const validUntil = new Date(Date.now() + 7 * 86400_000).toISOString().split("T")[0];
  const now = new Date().toISOString();

  const report: Record<string, {
    pagesOk: number; textChars: number; textSample: string;
    extracted: number; matched: number;
    updated: number; promos: number; error?: string;
  }> = {};

  await Promise.allSettled(
    Object.entries(STORES).map(async ([storeName, { urls, fetcher }]) => {
      const storeId = storeIdMap[storeName];
      if (!storeId) return;

      // Skip Firecrawl stores if no API key is configured
      if (fetcher === "firecrawl" && !process.env.FIRECRAWL_API_KEY) {
        report[storeName] = { pagesOk: 0, textChars: 0, textSample: "", extracted: 0, matched: 0, updated: 0, promos: 0, error: "no_firecrawl_key" };
        return;
      }

      const fetch1 = fetcher === "firecrawl" ? fetchViaFirecrawl : fetchViaJina;

      try {
        const htmlResults = await Promise.allSettled(urls.map((u) => fetch1(u)));
        const texts = htmlResults
          .filter((r): r is PromiseFulfilledResult<string> => r.status === "fulfilled" && r.value.length > 300)
          .map((r) => r.value)
          // Drop 404/block/overlay pages — they confuse Claude into extracting garbage
          .filter(t => !/(niestety nie istnieje|coś poszło nie tak|już nie istnieje|strona nie istnieje|nie możemy znaleźć strony|404 uuuups|wymagana weryfikacja|ray id:|cloudflare|pobierz aplikację i oszczędzaj)/i.test(t.slice(0, 800)));

        const pagesOk = texts.length;
        const textChars = texts.reduce((s, t) => s + t.length, 0);
        const textSample = texts[0]?.slice(0, 300) ?? "";

        if (pagesOk === 0) {
          report[storeName] = { pagesOk: 0, textChars: 0, textSample: "", extracted: 0, matched: 0, updated: 0, promos: 0, error: "all_pages_empty" };
          return;
        }

        const items = await claudeExtract(texts, storeName);

        const priceUpdates: { product_id: number; store_id: number; price: number; source: string; scraped_at: string }[] = [];
        const promoUpdates: any[] = [];
        const historyRows: { product_id: number; store_id: number; price: number; source: string }[] = [];

        for (const item of items) {
          if (!item.product || !item.price || item.price <= 0.1 || item.price > 999) continue;

          const best = products
            .map((p) => ({ p, score: matchScore(item.product, p.name) }))
            .filter(({ score }) => score >= 0.60)
            .sort((a, b) => b.score - a.score)[0];

          if (!best) continue;

          if (item.is_promo && item.original_price && item.original_price > item.price) {
            promoUpdates.push({
              product_id: best.p.id,
              store_id: storeId,
              promo_price: item.price,
              promo_label: item.label ?? null,
              valid_from: today,
              valid_until: validUntil,
            });
          } else {
            priceUpdates.push({
              product_id: best.p.id,
              store_id: storeId,
              price: item.price,
              source: "scraped",
              scraped_at: now,
            });
            historyRows.push({
              product_id: best.p.id,
              store_id: storeId,
              price: item.price,
              source: "scraped",
            });
          }
        }

        if (priceUpdates.length > 0) {
          await supabase.from("prices").upsert(priceUpdates, { onConflict: "product_id,store_id" });
        }
        if (promoUpdates.length > 0) {
          await supabase.from("promotions" as any).upsert(promoUpdates, { onConflict: "store_id,product_id" });
        }
        if (historyRows.length > 0) {
          await supabase.from("price_history" as any).insert(historyRows);
        }

        report[storeName] = { pagesOk, textChars, textSample, extracted: items.length, matched: priceUpdates.length + promoUpdates.length, updated: priceUpdates.length, promos: promoUpdates.length };
      } catch (e: any) {
        report[storeName] = { pagesOk: 0, textChars: 0, textSample: "", extracted: 0, matched: 0, updated: 0, promos: 0, error: e.message };
      }
    })
  );

  const totalUpdated = Object.values(report).reduce((s, r) => s + r.updated + r.promos, 0);
  const ok = Object.entries(report).filter(([, r]) => !r.error && r.updated + r.promos > 0).map(([n]) => n);
  const failed = Object.entries(report).filter(([, r]) => r.error || r.updated + r.promos === 0).map(([n]) => n);

  await sendEmail(
    `taniejkupuj — sync ${totalUpdated} cen (${new Date().toLocaleDateString("pl-PL")})`,
    `<h2>Sync cen zakończony</h2>
    <p><b>Łącznie zaktualizowano:</b> ${totalUpdated} cen</p>
    <p><b>Sklepy OK:</b> ${ok.join(", ") || "brak"}</p>
    ${failed.length > 0 ? `<p><b>Błędy:</b> ${failed.join(", ")}</p>` : ""}
    <pre style="background:#f5f5f5;padding:12px;border-radius:8px;font-size:11px">${JSON.stringify(report, null, 2)}</pre>
    <p style="color:#999;font-size:12px">taniejkupuj.pl · ${new Date().toLocaleString("pl-PL")}</p>`
  );

  return NextResponse.json({ ok: true, report, ran_at: new Date().toISOString() });
}

export async function GET(req: NextRequest) {
  const auth = req.headers.get("authorization");
  if (auth !== `Bearer ${process.env.CRON_SECRET}`) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  return POST(req);
}
