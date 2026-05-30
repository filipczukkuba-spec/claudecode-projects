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

2. DATE: find the receipt date (near "DATA" or YYYY-MM-DD format).

3. TOTAL: find the final total at "SUMA PLN" or "DO ZAPŁATY".

4. FOR EACH ITEM LINE:
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

5. SKIP: deposit fees ("OPŁATA SKARBOWA"), bag charges, NIP, copy markers, blank rows.

6. If receipt is blurry, cut off, or not a Polish receipt: return unreadable=true.

Respond with ONLY a JSON object (no markdown):
{
  "store": "Lidl" | "Biedronka" | ... | null,
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

  // Duplicate detection — fingerprint = store + date + total + sorted line totals
  const fingerprintInput =
    `${storeRow.id}|${vision.receipt_date}|${(vision.total ?? 0).toFixed(2)}|` +
    items
      .map((i) => (Number.isFinite(i.line_total) ? i.line_total : 0).toFixed(2))
      .sort()
      .join(",");
  const fingerprint = createHash("sha256").update(fingerprintInput).digest("hex").slice(0, 32);

  const dupSince = new Date(Date.now() - DUP_WINDOW_DAYS * 86400_000).toISOString();
  const { count: dupCount } = await admin
    .from("receipt_scans")
    .select("*", { count: "exact", head: true })
    .eq("status", "ok")
    .eq("fingerprint", fingerprint)
    .gte("scanned_at", dupSince);

  if ((dupCount ?? 0) > 0) {
    await admin.from("receipt_scans").insert({
      status: "rejected", reject_reason: "duplicate",
      store_id: storeRow.id, receipt_date: vision.receipt_date,
      ip_hash: ipHash, city,
    });
    return NextResponse.json(
      { error: "Ten paragon już został zeskanowany. Dziękujemy!" },
      { status: 409 }
    );
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
      fingerprint,
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
