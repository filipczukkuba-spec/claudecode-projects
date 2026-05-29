import { NextRequest, NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase-admin";
import { matchScore } from "@/lib/matching";
import { sendEmail } from "@/lib/email";
import { fetchViaJina } from "@/lib/price-extractor";

export const maxDuration = 60;

// ── Store pages ─────────────────────────────────────────────────────────────
// Use the pages most likely to have many products with prices visible.
// Keep to 2 per store so all 14 requests finish within 60s.

const STORE_URLS: Record<string, string[]> = {
  Biedronka: [
    "https://www.biedronka.pl/pl/oferta-tygodnia",
    "https://www.biedronka.pl/pl/products?category=nabia%C5%82-i-jajka",
    "https://www.biedronka.pl/pl/products?category=napoje",
  ],
  Lidl: [
    "https://www.lidl.pl/c/oferta-tygodnia/a10007519",
    "https://www.lidl.pl/c/nabiaal-i-jajka/c600",
    "https://www.lidl.pl/c/napoje/c1100",
  ],
  Kaufland: [
    "https://www.kaufland.pl/oferty/aktualne.html",
    "https://www.kaufland.pl/produkty/nabiaal-i-jajka.html",
    "https://www.kaufland.pl/produkty/napoje.html",
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

  const combined = texts.join("\n\n---\n\n").slice(0, 24000);

  try {
    const msg = await ai.messages.create({
      model: "claude-haiku-4-5-20251001",
      max_tokens: 4000,
      messages: [
        {
          role: "user",
          content: `Extract ALL grocery product prices from this ${storeName} page content.

Page content (rendered text from store website):
${combined}

Return a JSON array of every product+price pair you can find. Use Polish product names as shown on the page.

Each object:
- product: product name as shown (Polish, e.g. "Mleko 3,2% 1L", "Pierś z kurczaka")
- price: current price as number (e.g. 3.49) — use promo/sale price if available
- is_promo: true if this is a promotional/sale price
- label: promo label like "-20%", "2+1", "Okazja tygodnia", or null
- original_price: regular price before discount as number, or null

Rules:
- Extract EVERYTHING with a clear price — do not limit to specific products
- Prices must be in PLN (złoty), typically 0.50–500 range
- Skip items that are clearly not grocery products (store hours, addresses, etc.)
- Return [] if the page has no product prices (e.g. cookie consent / error page)

[{"product":"Mleko 3,2% 1L","price":3.49,"is_promo":false,"label":null,"original_price":null}]`,
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
  const productNames = products.map((p) => p.name);
  const today = new Date().toISOString().split("T")[0];
  const validUntil = new Date(Date.now() + 7 * 86400_000).toISOString().split("T")[0];
  const now = new Date().toISOString();

  const report: Record<string, {
    pagesOk: number; textChars: number; textSample: string;
    extracted: number; matched: number;
    updated: number; promos: number; error?: string;
  }> = {};

  // Fetch all stores in parallel (Jina renders JS automatically)
  await Promise.allSettled(
    Object.entries(STORE_URLS).map(async ([storeName, urls]) => {
      const storeId = storeIdMap[storeName];
      if (!storeId) return;

      try {
        // Fetch all pages for this store in parallel
        const htmlResults = await Promise.allSettled(urls.map((u) => fetchViaJina(u)));
        const texts = htmlResults
          .filter((r): r is PromiseFulfilledResult<string> => r.status === "fulfilled" && r.value.length > 300)
          .map((r) => r.value);

        const pagesOk = texts.length;
        const textChars = texts.reduce((s, t) => s + t.length, 0);

        const textSample = texts[0]?.slice(0, 300) ?? "";

        if (pagesOk === 0) {
          report[storeName] = { pagesOk: 0, textChars: 0, textSample: "", extracted: 0, matched: 0, updated: 0, promos: 0, error: "all_pages_empty" };
          return;
        }

        // Claude extracts prices from the page text
        const items = await claudeExtract(texts, storeName);

        const priceUpdates: { product_id: number; store_id: number; price: number; source: string; scraped_at: string }[] = [];
        const promoUpdates: any[] = [];
        const historyRows: { product_id: number; store_id: number; price: number; source: string }[] = [];

        for (const item of items) {
          if (!item.product || !item.price || item.price <= 0 || item.price > 2000) continue;

          const best = products
            .map((p) => ({ p, score: matchScore(item.product, p.name) }))
            .filter(({ score }) => score >= 0.65)
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

        report[storeName] = {
          pagesOk,
          textChars,
          textSample,
          extracted: items.length,
          matched: priceUpdates.length + promoUpdates.length,
          updated: priceUpdates.length,
          promos: promoUpdates.length,
        };
      } catch (e: any) {
        report[storeName] = { pagesOk: 0, textChars: 0, textSample: "", extracted: 0, matched: 0, updated: 0, promos: 0, error: e.message };
      }
    })
  );

  const totalUpdated = Object.values(report).reduce((s, r) => s + r.updated + r.promos, 0);
  const ok = Object.entries(report).filter(([, r]) => !r.error).map(([n]) => n);
  const failed = Object.entries(report).filter(([, r]) => r.error).map(([n]) => n);

  await sendEmail(
    `taniejkupuj — sync ${totalUpdated} cen (${new Date().toLocaleDateString("pl-PL")})`,
    `<h2>Sync cen zakończony</h2>
    <p><b>Łącznie zaktualizowano:</b> ${totalUpdated} cen</p>
    <p><b>Metoda:</b> Jina.ai reader + Claude Haiku</p>
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
