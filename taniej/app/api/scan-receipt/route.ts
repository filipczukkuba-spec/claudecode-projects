import { NextRequest, NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase-admin";
import { matchScore } from "@/lib/matching";
import { createHash } from "crypto";

export const maxDuration = 60;

const MAX_RECEIPT_AGE_DAYS = 7;
const TOTAL_TOLERANCE_PLN = 2.0;
const HARD_MAX_PRICE = 500;
const OUTLIER_MULTIPLIER = 5;
const MAX_SCANS_PER_HOUR = 10;
const DUP_WINDOW_DAYS = 30;
const STRICT_MATCH_THRESHOLD = 0.75; // higher = less guessing

interface ExtractedItem {
  raw_name: string;
  matched_name: string | null;   // closest known product name
  quantity: number;              // 1 for piece-sold, weight in kg for loose produce
  unit_type: "szt" | "kg" | "l" | null;
  unit_price: number;            // PRICE PER UNIT (per kg, per litre, per piece)
  line_total: number;            // total paid on this line
  is_promo: boolean;             // line was discounted (coupon, * marker, RABAT line)
}

interface VisionResult {
  store: string | null;
  store_nip: string | null;        // 10-digit tax ID
  receipt_number: string | null;   // NR PARAGONU printed near the date
  receipt_date: string | null;
  total: number | null;
  items: ExtractedItem[];
  unreadable: boolean;
}

export async function POST(req: NextRequest) {
  if (!process.env.ANTHROPIC_API_KEY) {
    return NextResponse.json({ error: "AI niedostępne" }, { status: 503 });
  }

  const form = await req.formData().catch(() => null);
  const file = form?.get("receipt");
  const city = (form?.get("city") as string | null)?.trim().slice(0, 50) || null;
  if (!file || typeof file === "string") {
    return NextResponse.json({ error: "Brak zdjęcia paragonu" }, { status: 400 });
  }
  if (file.size > 8 * 1024 * 1024) {
    return NextResponse.json({ error: "Zdjęcie zbyt duże (max 8 MB)" }, { status: 400 });
  }
  const mime = file.type || "image/jpeg";
  if (!/^image\//.test(mime)) {
    return NextResponse.json({ error: "Plik nie jest obrazem" }, { status: 400 });
  }

  const admin = createAdminClient();

  // Rate limit per IP
  const ip = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? "unknown";
  const ipHash = createHash("sha256").update(ip).digest("hex").slice(0, 32);
  const hourAgo = new Date(Date.now() - 3600_000).toISOString();
  const { count: recentScans } = await admin
    .from("receipt_scans")
    .select("*", { count: "exact", head: true })
    .eq("ip_hash", ipHash)
    .gte("scanned_at", hourAgo);
  if ((recentScans ?? 0) >= MAX_SCANS_PER_HOUR) {
    return NextResponse.json(
      { error: "Zbyt wiele paragonów w ciągu godziny — spróbuj później" },
      { status: 429 }
    );
  }

  const [{ data: products }, { data: stores }] = await Promise.all([
    admin.from("products").select("id, name, unit"),
    admin.from("stores").select("id, name"),
  ]);
  if (!products || !stores) {
    return NextResponse.json({ error: "Błąd bazy danych" }, { status: 500 });
  }

  const bytes = new Uint8Array(await file.arrayBuffer());
  const base64 = Buffer.from(bytes).toString("base64");

  // Image-byte hash — same photo always produces same fingerprint regardless
  // of any OCR variance. Catches re-scans of the exact same image.
  const imageFingerprint = createHash("sha256").update(bytes).digest("hex").slice(0, 32);

  const dupSince = new Date(Date.now() - DUP_WINDOW_DAYS * 86400_000).toISOString();
  const { count: imgDupCount } = await admin
    .from("receipt_scans")
    .select("*", { count: "exact", head: true })
    .eq("status", "ok")
    .eq("fingerprint", imageFingerprint)
    .gte("scanned_at", dupSince);

  if ((imgDupCount ?? 0) > 0) {
    await admin.from("receipt_scans").insert({
      status: "rejected", reject_reason: "duplicate_image",
      ip_hash: ipHash, city,
    });
    return NextResponse.json(
      { error: "Ten paragon już został zeskanowany. Dziękujemy!" },
      { status: 409 }
    );
  }

  const productList = products
    .map((p) => `${p.id}: ${p.name}${p.unit ? ` (${p.unit})` : ""}`)
    .join("\n");
  const storeList = stores.map((s) => s.name).join(", ");

  let vision: VisionResult;
  try {
    const Anthropic = (await import("@anthropic-ai/sdk")).default;
    const ai = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
    const msg = await ai.messages.create({
      model: "claude-haiku-4-5-20251001",
      max_tokens: 4000,
      messages: [
        {
          role: "user",
          content: [
            {
              type: "image",
              source: { type: "base64", media_type: mime as "image/jpeg" | "image/png" | "image/webp", data: base64 },
            },
            {
              type: "text",
              text: `You are extracting items from a Polish supermarket receipt (paragon fiskalny).

Known stores (return exact spelling):
${storeList}

Known products catalogue (id: name (unit)):
${productList.slice(0, 25000)}

CRITICAL RULES — read carefully:

1. STORE: identify from the header, logo, or address. Use exact spelling from the list above.

2. STORE_NIP: the 10-digit tax ID printed in the header (look for "NIP" followed by 10 digits).
   Return as a plain digit string with no formatting, e.g. "7811897358". null if not visible.

3. RECEIPT_NUMBER: the unique receipt number — usually labeled "NR" or "PARAGON FISKALNY nr",
   often near the date. Return the full identifier as printed (digits, slashes, dashes ok),
   e.g. "747556" or "Z2/123/45". null if not visible.

4. DATE: find the receipt date (near "DATA" or YYYY-MM-DD format).

5. TOTAL: find the final total at "SUMA PLN" or "DO ZAPŁATY".

6. FOR EACH ITEM LINE:
   - raw_name: the exact abbreviated Polish text on the receipt
   - matched_name: the EXACT name from the catalogue above ONLY IF you are confident.
     DO NOT GUESS. If the receipt says "PATYCZKI SZAS" and there is no Patyczki product
     in the catalogue, return matched_name = null. NEVER pick a different product just
     because it has similar letters. "FILET DORSZ" must NOT be matched to "Filet z indyka".
   - quantity: how many units were bought. For piece-sold items = the count (1, 2, ...).
     For weight-sold items the receipt shows "0.63 x 14.99 = 9.44" — here quantity = 0.63 (kg).
   - unit_type: "szt" (piece), "kg" (kilogram), or "l" (litre). null if unclear.
   - unit_price: the PRICE PER UNIT as shown on the receipt — i.e. price per kg for
     weight-sold items, price per piece for piece-sold items.
       Example "0.63 x 14.99 = 9.44 papryka": unit_price = 14.99 (not 9.44!)
       Example "2 x 3.99 = 7.98 cola": unit_price = 3.99 (not 7.98)
       Example "Cebula 6.99": unit_price = 6.99, quantity = 1, unit_type = "szt"
   - line_total: the total paid on this line (used for SUMA reconciliation).
   - is_promo: true if the line shows "*", "RABAT", "PROMO", "1+1", "-X%", or has a
     discount row right after it.

7. SKIP from items: deposit fees ("OPŁATA SKARBOWA"), bag charges, copy markers, blank rows.

8. If receipt is blurry, cut off, or not a Polish receipt: return unreadable=true.

Respond with ONLY a JSON object (no markdown):
{
  "store": "Lidl" | "Biedronka" | ... | null,
  "store_nip": "7811897358" | null,
  "receipt_number": "747556" | null,
  "receipt_date": "2026-05-30" | null,
  "total": 51.86 | null,
  "items": [
    {
      "raw_name": "PAPRYKA CZERW LUZ",
      "matched_name": "Papryka" | null,
      "quantity": 0.63,
      "unit_type": "kg",
      "unit_price": 14.99,
      "line_total": 9.44,
      "is_promo": false
    }
  ],
  "unreadable": false
}`,
            },
          ],
        },
      ],
    });

    const raw = msg.content[0].type === "text" ? msg.content[0].text : "";
    const match = raw.match(/\{[\s\S]*\}/);
    if (!match) throw new Error("invalid_json");
    vision = JSON.parse(match[0]) as VisionResult;
  } catch {
    return NextResponse.json(
      { error: "Nie udało się odczytać paragonu — spróbuj wyraźniejsze zdjęcie" },
      { status: 422 }
    );
  }

  // ── Validation ──────────────────────────────────────────────────────

  if (vision.unreadable) {
    await admin.from("receipt_scans").insert({
      status: "rejected", reject_reason: "unreadable", ip_hash: ipHash, city,
    });
    return NextResponse.json({ error: "Paragon nieczytelny — zrób wyraźniejsze zdjęcie" }, { status: 422 });
  }

  const storeRow = vision.store
    ? stores.find((s) => s.name.toLowerCase() === vision.store!.toLowerCase())
    : null;
  if (!storeRow) {
    await admin.from("receipt_scans").insert({
      status: "rejected", reject_reason: "unknown_store",
      extracted_total: vision.total, receipt_date: vision.receipt_date,
      ip_hash: ipHash, city,
    });
    return NextResponse.json(
      { error: `Nie rozpoznano sklepu (${vision.store ?? "nieznany"})` },
      { status: 422 }
    );
  }

  if (!vision.receipt_date) {
    await admin.from("receipt_scans").insert({
      status: "rejected", reject_reason: "no_date",
      store_id: storeRow.id, extracted_total: vision.total, ip_hash: ipHash, city,
    });
    return NextResponse.json({ error: "Nie znaleziono daty na paragonie" }, { status: 422 });
  }
  const receiptMs = Date.parse(vision.receipt_date);
  if (!Number.isFinite(receiptMs)) {
    return NextResponse.json({ error: "Nieprawidłowa data paragonu" }, { status: 422 });
  }
  const ageDays = (Date.now() - receiptMs) / 86400_000;
  if (ageDays > MAX_RECEIPT_AGE_DAYS) {
    await admin.from("receipt_scans").insert({
      status: "rejected", reject_reason: "too_old",
      store_id: storeRow.id, receipt_date: vision.receipt_date,
      ip_hash: ipHash, city,
    });
    return NextResponse.json(
      { error: `Paragon starszy niż ${MAX_RECEIPT_AGE_DAYS} dni — pokazujemy aktualne ceny` },
      { status: 422 }
    );
  }
  if (ageDays < -1) {
    return NextResponse.json({ error: "Data paragonu jest w przyszłości" }, { status: 422 });
  }

  const items = Array.isArray(vision.items) ? vision.items : [];
  if (items.length === 0) {
    return NextResponse.json({ error: "Nie znaleziono produktów na paragonie" }, { status: 422 });
  }

  // Primary dedup: NIP + receipt number + date. Polish fiscal receipts are
  // uniquely identified by this combo — even a re-photograph of the same
  // paragon will share it. Image-hash check above already caught identical
  // bytes; this catches the same receipt photographed twice.
  const nipClean = vision.store_nip ? String(vision.store_nip).replace(/\D/g, "") : null;
  const nrClean = vision.receipt_number ? String(vision.receipt_number).trim().slice(0, 80) : null;
  const haveBoth = nipClean && nipClean.length >= 8 && nrClean && nrClean.length >= 3;

  if (haveBoth) {
    const dupSince = new Date(Date.now() - DUP_WINDOW_DAYS * 86400_000).toISOString();
    const { count: nipDupCount } = await admin
      .from("receipt_scans")
      .select("*", { count: "exact", head: true })
      .eq("status", "ok")
      .eq("store_nip", nipClean)
      .eq("receipt_number", nrClean)
      .eq("receipt_date", vision.receipt_date!)
      .gte("scanned_at", dupSince);

    if ((nipDupCount ?? 0) > 0) {
      await admin.from("receipt_scans").insert({
        status: "rejected", reject_reason: "duplicate_nip",
        store_id: storeRow.id, receipt_date: vision.receipt_date,
        store_nip: nipClean, receipt_number: nrClean,
        ip_hash: ipHash, city,
      });
      return NextResponse.json(
        { error: "Ten paragon już został zeskanowany (sprawdzamy po numerze paragonu). Dziękujemy!" },
        { status: 409 }
      );
    }
  }

  // Total reconciliation using line_total values
  if (vision.total != null && Number.isFinite(vision.total)) {
    const sum = items.reduce((s, i) => s + (Number.isFinite(i.line_total) ? i.line_total : 0), 0);
    if (Math.abs(sum - vision.total) > TOTAL_TOLERANCE_PLN) {
      await admin.from("receipt_scans").insert({
        status: "rejected", reject_reason: "total_mismatch",
        store_id: storeRow.id, receipt_date: vision.receipt_date,
        receipt_total: vision.total, extracted_total: parseFloat(sum.toFixed(2)),
        item_count: items.length, ip_hash: ipHash, city,
      });
      return NextResponse.json(
        { error: `Suma produktów (${sum.toFixed(2)} zł) nie zgadza się z paragonem (${vision.total.toFixed(2)} zł)` },
        { status: 422 }
      );
    }
  }

  // Outlier reference: median per-product price across stores
  const { data: refPrices } = await admin.from("prices").select("product_id, price");
  const medianByProduct = new Map<number, number>();
  if (refPrices) {
    const groups = new Map<number, number[]>();
    for (const r of refPrices as { product_id: number; price: number | null }[]) {
      if (r.price == null) continue;
      const arr = groups.get(r.product_id) ?? [];
      arr.push(r.price);
      groups.set(r.product_id, arr);
    }
    for (const [pid, arr] of groups) {
      arr.sort((a, b) => a - b);
      medianByProduct.set(pid, arr[Math.floor(arr.length / 2)]);
    }
  }

  // Record the scan first so we can attach reports to it.
  const { data: scanRow, error: scanErr } = await admin
    .from("receipt_scans")
    .insert({
      status: "ok",
      fingerprint: imageFingerprint,
      store_nip: nipClean,
      receipt_number: nrClean,
      store_id: storeRow.id,
      receipt_date: vision.receipt_date,
      receipt_total: vision.total ?? null,
      extracted_total: parseFloat(
        items.reduce((s, i) => s + (i.line_total || 0), 0).toFixed(2)
      ),
      item_count: items.length,
      ip_hash: ipHash,
      city,
    })
    .select("id")
    .single();

  if (scanErr || !scanRow) {
    return NextResponse.json({ error: "Błąd zapisu" }, { status: 500 });
  }

  // Process items: strict match + per-unit price
  const reportRows: any[] = [];
  const accepted: { product: string; price: number; unit_type: string | null; is_promo: boolean }[] = [];
  const rejected: { raw: string; reason: string }[] = [];

  for (const item of items) {
    const unitPrice = Number.isFinite(item.unit_price) ? item.unit_price : NaN;
    if (!Number.isFinite(unitPrice) || unitPrice <= 0 || unitPrice > HARD_MAX_PRICE) {
      rejected.push({ raw: item.raw_name ?? "?", reason: "invalid_price" });
      continue;
    }

    // Strict match: prefer Claude's matched_name; only fall back to fuzzy if very high score
    let best = item.matched_name
      ? products.find((p) => p.name.toLowerCase() === item.matched_name!.toLowerCase())
      : undefined;

    if (!best) {
      const candidates = products
        .map((p) => ({ p, score: matchScore(item.raw_name, p.name) }))
        .filter(({ score }) => score >= STRICT_MATCH_THRESHOLD)
        .sort((a, b) => b.score - a.score);
      best = candidates[0]?.p;
    }

    if (!best) {
      rejected.push({ raw: item.raw_name, reason: "no_match" });
      continue;
    }

    const median = medianByProduct.get(best.id);
    if (median && unitPrice >= median * OUTLIER_MULTIPLIER) {
      rejected.push({ raw: item.raw_name, reason: "outlier" });
      continue;
    }

    reportRows.push({
      product_id: best.id,
      store_id: storeRow.id,
      price: parseFloat(unitPrice.toFixed(2)),
      source: "receipt",
      scan_id: scanRow.id,
      is_promo: !!item.is_promo,
      city,
    });
    accepted.push({
      product: best.name,
      price: unitPrice,
      unit_type: item.unit_type ?? null,
      is_promo: !!item.is_promo,
    });
  }

  if (reportRows.length > 0) {
    await admin.from("price_reports").insert(reportRows);

    // Also write the receipt-verified prices straight into the main prices
    // table as source='community'. Non-promo lines only — promo prices go
    // through the promotions flow elsewhere. We never overwrite a fresh
    // 'scraped' price (scrapers stay authoritative).
    const { data: existing } = await admin
      .from("prices")
      .select("product_id, store_id, source")
      .in("product_id", reportRows.map((r) => r.product_id))
      .eq("store_id", storeRow.id);

    const existingMap = new Map<number, string | null>();
    for (const e of (existing ?? []) as any[]) {
      existingMap.set(e.product_id, e.source ?? null);
    }

    const mainUpdates = reportRows
      .filter((r) => !r.is_promo)
      .filter((r) => existingMap.get(r.product_id) !== "scraped")
      .map((r) => ({
        product_id: r.product_id,
        store_id: r.store_id,
        price: r.price,
        source: "community",
        scraped_at: new Date().toISOString(),
      }));

    if (mainUpdates.length > 0) {
      await admin.from("prices").upsert(mainUpdates, { onConflict: "product_id,store_id" });
    }
  }

  // ── Cross-store calibration ─────────────────────────────────────────
  // When a receipt verifies a real price for one store, it tells us this
  // product's price level — the *estimated* prices in OTHER stores that
  // were way off (e.g. cukinia 3,50 zł vs verified 8,99 zł) should be
  // brought in line using historical store multipliers.
  //
  // Rules:
  //  - Only touch rows where source = 'estimated' (never overwrite
  //    scraped or community-verified prices in other stores).
  //  - Skip if the existing estimate is already within 50% of the
  //    receipt-implied baseline (already plausible).
  //  - Don't apply for promo lines (those are one-off discounts).
  let recalibrated = 0;
  if (reportRows.length > 0) {
    const STORE_MULTIPLIER: Record<string, number> = {
      Biedronka: 1.00, Lidl: 0.97, Aldi: 0.98, Kaufland: 1.05,
      Netto: 0.99, Auchan: 1.06, Carrefour: 1.08,
    };
    const sourceFactor = STORE_MULTIPLIER[storeRow.name] ?? 1.0;

    // Pull current prices for all (product, store) we want to consider
    const productIds = [...new Set(reportRows.filter((r) => !r.is_promo).map((r) => r.product_id))];
    if (productIds.length > 0) {
      const { data: peerPrices } = await admin
        .from("prices")
        .select("product_id, store_id, price, source");

      const peerMap = new Map<string, { price: number | null; source: string | null }>();
      for (const p of (peerPrices ?? []) as any[]) {
        peerMap.set(`${p.product_id}-${p.store_id}`, { price: p.price, source: p.source });
      }

      const calibrationUpdates: { product_id: number; store_id: number; price: number; source: string }[] = [];

      for (const row of reportRows) {
        if (row.is_promo) continue;
        const baseline = row.price / sourceFactor;       // Biedronka-reference baseline

        for (const peer of stores) {
          if (peer.id === storeRow.id) continue;          // skip the source store itself
          const factor = STORE_MULTIPLIER[peer.name];
          if (!factor) continue;
          const target = parseFloat((baseline * factor).toFixed(2));

          const current = peerMap.get(`${row.product_id}-${peer.id}`);
          if (!current) continue;
          if (current.source && current.source !== "estimated") continue;  // hands off real data
          if (current.price != null) {
            // Already close enough? skip
            const ratio = current.price / target;
            if (ratio >= 0.5 && ratio <= 1.5) continue;
          }

          calibrationUpdates.push({
            product_id: row.product_id,
            store_id: peer.id,
            price: target,
            source: "estimated",
          });
        }
      }

      if (calibrationUpdates.length > 0) {
        await admin.from("prices").upsert(calibrationUpdates, { onConflict: "product_id,store_id" });
        recalibrated = calibrationUpdates.length;
      }
    }
  }

  return NextResponse.json({
    ok: true,
    store: storeRow.name,
    receipt_date: vision.receipt_date,
    total: vision.total,
    accepted,
    rejected,
    saved: reportRows.length,
    recalibrated,
  });
}
