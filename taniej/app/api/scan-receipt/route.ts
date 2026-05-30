import { NextRequest, NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase-admin";
import { matchScore, MATCH_THRESHOLD } from "@/lib/matching";
import { createHash } from "crypto";

export const maxDuration = 60;

const MAX_RECEIPT_AGE_DAYS = 7;
const TOTAL_TOLERANCE_PLN = 2.0;
const HARD_MAX_PRICE = 500;
const OUTLIER_MULTIPLIER = 5;
const MAX_SCANS_PER_HOUR = 10;

interface ExtractedItem {
  raw_name: string;
  matched_name: string | null;   // closest known product name
  price: number;
  is_promo: boolean;             // line was discounted (coupon, * marker, RABAT line)
}

interface VisionResult {
  store: string | null;          // detected store name
  receipt_date: string | null;   // YYYY-MM-DD
  total: number | null;
  items: ExtractedItem[];
  unreadable: boolean;
}

export async function POST(req: NextRequest) {
  if (!process.env.ANTHROPIC_API_KEY) {
    return NextResponse.json({ error: "AI niedostępne" }, { status: 503 });
  }

  // Parse multipart form (image upload)
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

  // Crude IP-based rate limiting
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

  // Load reference data once
  const [{ data: products }, { data: stores }] = await Promise.all([
    admin.from("products").select("id, name, unit"),
    admin.from("stores").select("id, name"),
  ]);
  if (!products || !stores) {
    return NextResponse.json({ error: "Błąd bazy danych" }, { status: 500 });
  }

  // Convert image → base64 for the Anthropic SDK
  const bytes = new Uint8Array(await file.arrayBuffer());
  const base64 = Buffer.from(bytes).toString("base64");

  // Build a compact reference list so Claude can map abbreviated receipt lines
  // (e.g. "PATYCZKI SZAS") to canonical product names.
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
              text: `You are extracting grocery items from a Polish supermarket receipt (paragon fiskalny).

Known stores (pick one, exact spelling):
${storeList}

Known products (id: name (unit)):
${productList.slice(0, 25000)}

Receipt instructions:
- Identify the store from the header (logo or address line).
- Find the receipt date — usually printed near "DATA" or as YYYY-MM-DD at the bottom.
- Find the final total — usually labeled "SUMA PLN" or "DO ZAPŁATY".
- For each item line:
    • raw_name = the exact abbreviated text on the receipt (e.g. "PATYCZKI SZAS")
    • matched_name = the CLOSEST product name from the known list above, or null if no good match
    • price = the price for that line in PLN (the per-unit price × qty as printed)
    • is_promo = true if the line has a sale marker like "*", "RABAT", "PROMO", "1+1", "-X%", or a discount row immediately after it; false otherwise
- Coupon/loyalty discounts: if the receipt shows a separate "RABAT" or negative discount row, mark the affected items as is_promo=true and use the FINAL price after discount.
- Skip: deposit fees ("OPŁATA SKARBOWA"), bag charges, NIP lines, copy markers, blank rows.
- If the receipt is unreadable (blurry, cut off, not a Polish receipt) return unreadable=true.

Respond with ONLY a JSON object in this exact shape (no markdown):
{
  "store": "Lidl" | "Biedronka" | ... | null,
  "receipt_date": "2026-05-30" | null,
  "total": 51.86 | null,
  "items": [
    { "raw_name": "...", "matched_name": "..." | null, "price": 0.00, "is_promo": false }
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
  } catch (e) {
    return NextResponse.json(
      { error: "Nie udało się odczytać paragonu — spróbuj wyraźniejsze zdjęcie" },
      { status: 422 }
    );
  }

  // ── Validation pipeline ─────────────────────────────────────────────

  if (vision.unreadable) {
    await admin.from("receipt_scans").insert({
      status: "rejected",
      reject_reason: "unreadable",
      ip_hash: ipHash,
      city,
    });
    return NextResponse.json({ error: "Paragon nieczytelny — zrób wyraźniejsze zdjęcie" }, { status: 422 });
  }

  // Store match
  const storeRow = vision.store
    ? stores.find((s) => s.name.toLowerCase() === vision.store!.toLowerCase())
    : null;
  if (!storeRow) {
    await admin.from("receipt_scans").insert({
      status: "rejected",
      reject_reason: "unknown_store",
      extracted_total: vision.total,
      receipt_date: vision.receipt_date,
      ip_hash: ipHash,
      city,
    });
    return NextResponse.json(
      { error: `Nie rozpoznano sklepu (${vision.store ?? "nieznany"})` },
      { status: 422 }
    );
  }

  // Date check
  if (!vision.receipt_date) {
    await admin.from("receipt_scans").insert({
      status: "rejected",
      reject_reason: "no_date",
      store_id: storeRow.id,
      extracted_total: vision.total,
      ip_hash: ipHash,
      city,
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
      status: "rejected",
      reject_reason: "too_old",
      store_id: storeRow.id,
      receipt_date: vision.receipt_date,
      ip_hash: ipHash,
      city,
    });
    return NextResponse.json(
      { error: `Paragon starszy niż ${MAX_RECEIPT_AGE_DAYS} dni — pokazujemy aktualne ceny` },
      { status: 422 }
    );
  }
  if (ageDays < -1) {
    return NextResponse.json({ error: "Data paragonu jest w przyszłości" }, { status: 422 });
  }

  // Items sanity
  const items = Array.isArray(vision.items) ? vision.items : [];
  if (items.length === 0) {
    return NextResponse.json({ error: "Nie znaleziono produktów na paragonie" }, { status: 422 });
  }

  // Total reconciliation — defense against bad OCR & manipulation
  if (vision.total != null && Number.isFinite(vision.total)) {
    const sum = items.reduce((s, i) => s + (Number.isFinite(i.price) ? i.price : 0), 0);
    if (Math.abs(sum - vision.total) > TOTAL_TOLERANCE_PLN) {
      await admin.from("receipt_scans").insert({
        status: "rejected",
        reject_reason: "total_mismatch",
        store_id: storeRow.id,
        receipt_date: vision.receipt_date,
        receipt_total: vision.total,
        extracted_total: parseFloat(sum.toFixed(2)),
        item_count: items.length,
        ip_hash: ipHash,
        city,
      });
      return NextResponse.json(
        { error: `Suma produktów (${sum.toFixed(2)} zł) nie zgadza się z paragonem (${vision.total.toFixed(2)} zł)` },
        { status: 422 }
      );
    }
  }

  // Outlier reference: median price for this product across stores
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

  // Record the scan first so we can attach reports to it
  const { data: scanRow, error: scanErr } = await admin
    .from("receipt_scans")
    .insert({
      status: "ok",
      store_id: storeRow.id,
      receipt_date: vision.receipt_date,
      receipt_total: vision.total ?? null,
      extracted_total: parseFloat(items.reduce((s, i) => s + (i.price || 0), 0).toFixed(2)),
      item_count: items.length,
      ip_hash: ipHash,
      city,
    })
    .select("id")
    .single();

  if (scanErr || !scanRow) {
    return NextResponse.json({ error: "Błąd zapisu" }, { status: 500 });
  }

  // Map each line to a known product + insert into price_reports
  const reportRows: any[] = [];
  const accepted: { product: string; price: number; is_promo: boolean }[] = [];
  const rejected: { raw: string; reason: string }[] = [];

  for (const item of items) {
    if (!item || !Number.isFinite(item.price) || item.price <= 0 || item.price > HARD_MAX_PRICE) {
      rejected.push({ raw: item.raw_name ?? "?", reason: "invalid_price" });
      continue;
    }

    // Try Claude's match first, fall back to fuzzy match
    let best = item.matched_name
      ? products.find((p) => p.name.toLowerCase() === item.matched_name!.toLowerCase())
      : undefined;

    if (!best) {
      const candidates = products
        .map((p) => ({ p, score: matchScore(item.raw_name, p.name) }))
        .filter(({ score }) => score >= MATCH_THRESHOLD)
        .sort((a, b) => b.score - a.score);
      best = candidates[0]?.p;
    }

    if (!best) {
      rejected.push({ raw: item.raw_name, reason: "no_match" });
      continue;
    }

    // Outlier guard
    const median = medianByProduct.get(best.id);
    if (median && item.price >= median * OUTLIER_MULTIPLIER) {
      rejected.push({ raw: item.raw_name, reason: "outlier" });
      continue;
    }

    reportRows.push({
      product_id: best.id,
      store_id: storeRow.id,
      price: parseFloat(item.price.toFixed(2)),
      source: "receipt",
      scan_id: scanRow.id,
      is_promo: !!item.is_promo,
      city,
    });
    accepted.push({ product: best.name, price: item.price, is_promo: !!item.is_promo });
  }

  if (reportRows.length > 0) {
    await admin.from("price_reports").insert(reportRows);
  }

  return NextResponse.json({
    ok: true,
    store: storeRow.name,
    receipt_date: vision.receipt_date,
    total: vision.total,
    accepted,
    rejected,
    saved: reportRows.length,
  });
}
