import { NextRequest, NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase-admin";
import { matchScore } from "@/lib/matching";
import { sendEmail } from "@/lib/email";
import {
  fetchPage,
  extractFromJsonLd,
  extractFromNextData,
  extractFromApiJson,
  cleanHtml,
  dedup,
  type ExtractedItem,
} from "@/lib/price-extractor";

export const maxDuration = 60;

// ── Store URL configs ──────────────────────────────────────────────────────
// Each entry: [url, type] — type 'page' = HTML scrape, 'api' = JSON endpoint

type UrlEntry = [string, "page" | "api"];

const STORE_URLS: Record<string, UrlEntry[]> = {
  Biedronka: [
    ["https://www.biedronka.pl/pl/oferta-tygodnia", "page"],
    ["https://www.biedronka.pl/pl/products?category=nabia%C5%82-i-jajka", "page"],
    ["https://www.biedronka.pl/pl/products?category=mi%C4%99so-i-w%C4%99dliny", "page"],
    ["https://www.biedronka.pl/pl/products?category=warzywa-i-owoce", "page"],
    ["https://www.biedronka.pl/pl/products?category=napoje", "page"],
    ["https://www.biedronka.pl/pl/products?category=s%C5%82odycze-i-przek%C4%85ski", "page"],
    ["https://www.biedronka.pl/pl/products?category=chemia-domowa-i-higiena", "page"],
  ],
  Lidl: [
    ["https://www.lidl.pl/c/oferta-tygodnia/a10007519", "page"],
    ["https://www.lidl.pl/c/nabiaal-i-jajka/c600", "page"],
    ["https://www.lidl.pl/c/mieso-i-wedliny/c800", "page"],
    ["https://www.lidl.pl/c/warzywa-i-owoce/c700", "page"],
    ["https://www.lidl.pl/c/napoje/c1100", "page"],
    ["https://www.lidl.pl/c/slodycze-i-przek-ski/c900", "page"],
    ["https://www.lidl.pl/c/chemia-domowa/c1300", "page"],
  ],
  Kaufland: [
    ["https://www.kaufland.pl/oferty/aktualne.html", "page"],
    ["https://www.kaufland.pl/produkty/nabiaal-i-jajka.html", "page"],
    ["https://www.kaufland.pl/produkty/mieso-i-rybny.html", "page"],
    ["https://www.kaufland.pl/produkty/warzywa-i-owoce.html", "page"],
    ["https://www.kaufland.pl/produkty/napoje.html", "page"],
    ["https://www.kaufland.pl/produkty/slodycze-i-przekaski.html", "page"],
  ],
  Aldi: [
    ["https://www.aldi.pl/oferta-tygodnia.html", "page"],
    ["https://www.aldi.pl/nabiaal.html", "page"],
    ["https://www.aldi.pl/mieso.html", "page"],
    ["https://www.aldi.pl/napoje.html", "page"],
    ["https://www.aldi.pl/slodycze-i-przekaski.html", "page"],
  ],
  Netto: [
    ["https://www.netto.pl/gazetka-i-promocje/gazetka-tygodniowa", "page"],
    ["https://www.netto.pl/art-spozywcze-i-napoje/nabiaal", "page"],
    ["https://www.netto.pl/art-spozywcze-i-napoje/mieso-i-wedliny", "page"],
    ["https://www.netto.pl/art-spozywcze-i-napoje/napoje", "page"],
    ["https://www.netto.pl/slodycze-i-przekaski", "page"],
  ],
  Auchan: [
    ["https://www.auchan.pl/pl/promocje", "page"],
    ["https://www.auchan.pl/pl/produkty/nabiaal-i-jajka", "page"],
    ["https://www.auchan.pl/pl/produkty/mieso-i-wedliny", "page"],
    ["https://www.auchan.pl/pl/produkty/warzywa-i-owoce", "page"],
    ["https://www.auchan.pl/pl/produkty/napoje", "page"],
    ["https://www.auchan.pl/pl/produkty/slodycze-i-przekaski", "page"],
  ],
  Carrefour: [
    ["https://www.carrefour.pl/promocje", "page"],
    ["https://www.carrefour.pl/marka/nabiaal-i-jajka", "page"],
    ["https://www.carrefour.pl/marka/mieso-i-wedliny", "page"],
    ["https://www.carrefour.pl/marka/warzywa-i-owoce", "page"],
    ["https://www.carrefour.pl/marka/napoje", "page"],
    ["https://www.carrefour.pl/marka/slodycze-i-przekaski", "page"],
  ],
};

// ── Claude fallback (last resort only) ────────────────────────────────────

async function claudeExtract(
  texts: string[],
  storeName: string,
  knownProducts: string[]
): Promise<ExtractedItem[]> {
  if (!process.env.ANTHROPIC_API_KEY || texts.length === 0) return [];
  try {
    const Anthropic = (await import("@anthropic-ai/sdk")).default;
    const ai = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
    const combined = texts.join("\n\n---\n\n").slice(0, 22000);
    const knownList = knownProducts.slice(0, 300).join(", ");

    const msg = await ai.messages.create({
      model: "claude-haiku-4-5-20251001",
      max_tokens: 2000,
      messages: [
        {
          role: "user",
          content: `Extract current grocery prices from Polish supermarket "${storeName}".

Known products (use exact names from this list only):
${knownList}

Page content:
${combined}

Return ONLY a JSON array. Rules:
- product = exact string from known list above
- price = decimal number (use promo price if shown)
- is_promo = true if promotional
- label = promo label like "-20%", "2+1" or null
- Skip products not in the known list
- Return [] if nothing found

[{"product":"exact name","price":4.99,"is_promo":false,"label":null}]`,
        },
      ],
    });

    const raw = msg.content[0].type === "text" ? msg.content[0].text : "";
    const match = raw.match(/\[[\s\S]*\]/);
    if (!match) return [];
    const parsed: { product: string; price: number; is_promo: boolean; label?: string | null }[] =
      JSON.parse(match[0]);
    return parsed.map((p) => ({
      name: p.product,
      price: p.price,
      isPromo: p.is_promo,
      promoLabel: p.label ?? undefined,
      confidence: "low" as const,
      source: "regex" as const,
    }));
  } catch {
    return [];
  }
}

// ── Scrape one store ───────────────────────────────────────────────────────

async function scrapeStore(
  storeName: string,
  urlEntries: UrlEntry[],
  scraperApiKey: string | undefined
): Promise<{
  items: ExtractedItem[];
  pagesOk: number;
  method: string;
  rawTexts: string[];
}> {
  const allItems: ExtractedItem[] = [];
  const rawTexts: string[] = [];
  let pagesOk = 0;

  const results = await Promise.allSettled(
    urlEntries.map(async ([url, type]) => {
      const html = await fetchPage(url, scraperApiKey);
      if (!html) return null;

      if (type === "api") {
        try {
          const json = JSON.parse(html);
          return { items: extractFromApiJson(json), text: "" };
        } catch {}
      }

      const jsonLdItems = extractFromJsonLd(html);
      if (jsonLdItems.length >= 3) return { items: jsonLdItems, text: "" };

      const nextItems = extractFromNextData(html);
      if (nextItems.length >= 3) return { items: nextItems, text: "" };

      // Neither structured method worked — save text for Claude fallback
      const text = cleanHtml(html);
      return { items: [] as ExtractedItem[], text };
    })
  );

  for (const r of results) {
    if (r.status === "fulfilled" && r.value) {
      pagesOk++;
      allItems.push(...r.value.items);
      if (r.value.text.length > 500) rawTexts.push(r.value.text.slice(0, 6000));
    }
  }

  const method = scraperApiKey ? "scraperapi" : "direct";
  return { items: dedup(allItems), pagesOk, method, rawTexts };
}

// ── Main handler ───────────────────────────────────────────────────────────

export async function POST(req: NextRequest) {
  const secret = req.headers.get("authorization")?.replace("Bearer ", "");
  if (secret !== process.env.CRON_SECRET && secret !== process.env.VERCEL_CRON_SECRET) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const supabase = createAdminClient();
  const scraperApiKey = process.env.SCRAPERAPI_KEY || undefined;

  const [{ data: products }, { data: stores }] = await Promise.all([
    supabase.from("products").select("id, name"),
    supabase.from("stores").select("id, name"),
  ]);

  if (!products || !stores) {
    return NextResponse.json({ error: "DB load failed" }, { status: 500 });
  }

  const storeIdMap = Object.fromEntries(stores.map((s) => [s.name, s.id]));
  const productNames = products.map((p) => p.name);
  const today = new Date().toISOString().split("T")[0];
  const validUntil = new Date(Date.now() + 7 * 86400_000).toISOString().split("T")[0];

  const report: Record<
    string,
    {
      pagesOk: number;
      extracted: number;
      matched: number;
      updated: number;
      promos: number;
      method: string;
      usedClaude: boolean;
      error?: string;
    }
  > = {};

  // Scrape all stores in parallel
  const storeResults = await Promise.allSettled(
    Object.entries(STORE_URLS).map(async ([storeName, urlEntries]) => {
      const storeId = storeIdMap[storeName];
      if (!storeId) return null;

      try {
        let { items, pagesOk, method, rawTexts } = await scrapeStore(
          storeName,
          urlEntries,
          scraperApiKey
        );

        let usedClaude = false;

        // Claude fallback: only if structured extraction found <5 items AND we have text
        if (items.length < 5 && rawTexts.length > 0) {
          usedClaude = true;
          const claudeItems = await claudeExtract(rawTexts.slice(0, 3), storeName, productNames);
          items = dedup([...items, ...claudeItems]);
        }

        // Match items to known products
        const priceUpdates: { product_id: number; store_id: number; price: number; source: string; scraped_at: string }[] = [];
        const promoUpdates: any[] = [];
        const historyRows: { product_id: number; store_id: number; price: number; source: string }[] = [];

        for (const item of items) {
          const best = products
            .map((p) => ({ p, score: matchScore(item.name, p.name) }))
            .filter(({ score }) => score >= 0.65)
            .sort((a, b) => b.score - a.score)[0];

          if (!best) continue;

          if (item.isPromo && item.originalPrice) {
            promoUpdates.push({
              product_id: best.p.id,
              store_id: storeId,
              promo_price: item.price,
              promo_label: item.promoLabel ?? null,
              valid_from: today,
              valid_until: validUntil,
            });
          } else {
            priceUpdates.push({
              product_id: best.p.id,
              store_id: storeId,
              price: item.price,
              source: "scraped",
              scraped_at: new Date().toISOString(),
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
          await supabase
            .from("prices")
            .upsert(priceUpdates, { onConflict: "product_id,store_id" });
        }
        if (promoUpdates.length > 0) {
          await supabase
            .from("promotions" as any)
            .upsert(promoUpdates, { onConflict: "store_id,product_id" });
        }
        if (historyRows.length > 0) {
          await supabase.from("price_history" as any).insert(historyRows);
        }

        report[storeName] = {
          pagesOk,
          extracted: items.length,
          matched: priceUpdates.length + promoUpdates.length,
          updated: priceUpdates.length,
          promos: promoUpdates.length,
          method,
          usedClaude,
        };
      } catch (e: any) {
        report[storeName] = {
          pagesOk: 0,
          extracted: 0,
          matched: 0,
          updated: 0,
          promos: 0,
          method: "error",
          usedClaude: false,
          error: e.message,
        };
      }

      return storeName;
    })
  );

  void storeResults; // we already wrote to report in the callbacks

  const totalUpdated = Object.values(report).reduce((s, r) => s + r.updated + r.promos, 0);
  const ok = Object.entries(report).filter(([, r]) => !r.error).map(([n]) => n);
  const failed = Object.entries(report).filter(([, r]) => r.error).map(([n]) => n);

  await sendEmail(
    `taniejkupuj — sync ${totalUpdated} cen (${new Date().toLocaleDateString("pl-PL")})`,
    `<h2>Sync cen zakończony</h2>
    <p><b>Łącznie zaktualizowano:</b> ${totalUpdated} cen</p>
    <p><b>Proxy:</b> ${scraperApiKey ? "ScraperAPI ✓" : "direct (bez proxy)"}</p>
    <p><b>Sklepy OK:</b> ${ok.join(", ") || "brak"}</p>
    ${failed.length > 0 ? `<p><b>Błędy:</b> ${failed.join(", ")}</p>` : ""}
    <pre style="background:#f5f5f5;padding:12px;border-radius:8px;font-size:11px">${JSON.stringify(report, null, 2)}</pre>
    <p style="color:#999;font-size:12px">taniejkupuj.pl · ${new Date().toLocaleString("pl-PL")}</p>`
  );

  return NextResponse.json({ ok: true, report, scraperProxy: !!scraperApiKey, ran_at: new Date().toISOString() });
}

export async function GET(req: NextRequest) {
  const auth = req.headers.get("authorization");
  if (auth !== `Bearer ${process.env.CRON_SECRET}`) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  return POST(req);
}
