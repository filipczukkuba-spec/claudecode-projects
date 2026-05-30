// Price extraction utilities: JSON-LD → __NEXT_DATA__ → regex
// No AI needed for structured pages; Claude used only as last resort.

export interface ExtractedItem {
  name: string;
  price: number;
  originalPrice?: number;
  isPromo: boolean;
  promoLabel?: string;
  confidence: "high" | "medium" | "low";
  source: "jsonld" | "nextdata" | "regex";
}

// ── Fetch ──────────────────────────────────────────────────────────────────

// Firecrawl: handles Cloudflare + JS rendering. Free tier = 500 pages/month.
// Sign up at firecrawl.dev, add FIRECRAWL_API_KEY to Vercel env vars.
export async function fetchViaFirecrawl(url: string): Promise<string> {
  const key = process.env.FIRECRAWL_API_KEY;
  if (!key) return "";
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 40000);
    const res = await fetch("https://api.firecrawl.dev/v1/scrape", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${key}`,
      },
      body: JSON.stringify({
        url,
        formats: ["markdown"],
        onlyMainContent: true,
        waitFor: 5000,
      }),
      signal: ctrl.signal,
    });
    clearTimeout(t);
    if (!res.ok) return "";
    const data = await res.json();
    const text: string = data?.data?.markdown ?? "";
    return text.length > 300 ? text.slice(0, 22000) : "";
  } catch {
    return "";
  }
}

// Jina.ai reader: renders JS, returns clean text. Free tier, no key needed.
// With JINA_API_KEY env var: higher rate limits (get free key at jina.ai).
export async function fetchViaJina(url: string): Promise<string> {
  const jinaKey = process.env.JINA_API_KEY;
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 35000);
    const res = await fetch(`https://r.jina.ai/${url}`, {
      headers: {
        ...(jinaKey ? { Authorization: `Bearer ${jinaKey}` } : {}),
        "X-Return-Format": "text",
        "X-Timeout": "25",
        "Accept": "text/plain",
      },
      signal: ctrl.signal,
    });
    clearTimeout(t);
    if (!res.ok) return "";
    const text = await res.text();
    return text.length > 300 ? text.slice(0, 22000) : "";
  } catch {
    return "";
  }
}

// Direct fetch fallback (no proxy, may get blocked)
export async function fetchPage(url: string): Promise<string> {
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 20000);
    const res = await fetch(url, {
      headers: {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.7",
        Accept: "text/html,application/xhtml+xml,*/*;q=0.8",
      },
      signal: ctrl.signal,
      redirect: "follow",
    });
    clearTimeout(t);
    if (!res.ok) return "";
    const text = await res.text();
    return text.length > 800 ? text : "";
  } catch {
    return "";
  }
}

// ── JSON-LD (Schema.org) ───────────────────────────────────────────────────

export function extractFromJsonLd(html: string): ExtractedItem[] {
  const out: ExtractedItem[] = [];
  const blocks = html.matchAll(
    /<script[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi
  );
  for (const b of blocks) {
    try {
      const raw = JSON.parse(b[1].trim());
      walkLd(Array.isArray(raw) ? raw : [raw], out);
    } catch {}
  }
  return out;
}

function walkLd(nodes: any[], out: ExtractedItem[]): void {
  for (const n of nodes) {
    if (!n || typeof n !== "object") continue;
    const type = n["@type"];

    if (type === "Product") {
      const name = n.name || n.title;
      const offer = n.offers ?? n;
      const price = toNum(offer?.price ?? offer?.lowPrice);
      const hi = toNum(offer?.highPrice);
      if (name && price > 0.01 && price < 2000) {
        out.push({
          name,
          price: hi > price ? price : price,
          originalPrice: hi > price ? hi : undefined,
          isPromo: hi > price,
          confidence: "high",
          source: "jsonld",
        });
      }
    }

    if (type === "ItemList" && Array.isArray(n.itemListElement)) {
      walkLd(n.itemListElement.map((e: any) => e.item ?? e), out);
    }
    if (Array.isArray(n["@graph"])) walkLd(n["@graph"], out);
  }
}

// ── __NEXT_DATA__ (Next.js SSR hydration) ─────────────────────────────────

export function extractFromNextData(html: string): ExtractedItem[] {
  const out: ExtractedItem[] = [];
  const m = html.match(/<script id="__NEXT_DATA__" type="application\/json">([\s\S]*?)<\/script>/);
  if (!m) return out;
  try {
    walkObj(JSON.parse(m[1]), out, 0);
  } catch {}
  return out;
}

const PRODUCT_KEYS = new Set([
  "products", "items", "offers", "catalog", "results", "data",
  "categories", "productList", "categoryProducts", "pageProps",
  "productItems", "hits", "documents", "list", "product",
]);

function walkObj(obj: any, out: ExtractedItem[], depth: number): void {
  if (depth > 14 || !obj || typeof obj !== "object") return;

  if (Array.isArray(obj)) {
    for (const item of obj.slice(0, 300)) walkObj(item, out, depth + 1);
    return;
  }

  const name: string | undefined =
    obj.name ?? obj.title ?? obj.productName ?? obj.nazwaHandlowa ?? obj.label;
  const price =
    obj.price ?? obj.currentPrice ?? obj.regularPrice ??
    obj.priceValue ?? obj.cena ?? obj.salePrice ??
    obj.unitPrice ?? obj.normalPrice ?? obj.basePrice;

  if (name && typeof name === "string" && name.length >= 2 && name.length <= 150) {
    const priceNum = toNum(price);
    if (priceNum > 0.01 && priceNum < 2000) {
      const promoRaw = obj.promoPrice ?? obj.promotionPrice ?? obj.discountedPrice ?? obj.specialPrice;
      const promoNum = toNum(promoRaw);
      const usePromo = promoNum > 0 && promoNum < priceNum;
      out.push({
        name,
        price: usePromo ? promoNum : priceNum,
        originalPrice: usePromo ? priceNum : undefined,
        isPromo: usePromo,
        promoLabel: obj.promoLabel ?? obj.badgeText ?? undefined,
        confidence: "medium",
        source: "nextdata",
      });
    }
  }

  for (const k of Object.keys(obj)) {
    if (PRODUCT_KEYS.has(k) && obj[k] != null) walkObj(obj[k], out, depth + 1);
  }
}

// ── Auchan / Carrefour JSON API ────────────────────────────────────────────

export function extractFromApiJson(json: any): ExtractedItem[] {
  const out: ExtractedItem[] = [];
  walkObj(json, out, 0);
  return out;
}

// ── Regex fallback ─────────────────────────────────────────────────────────

export function cleanHtml(html: string): string {
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
    .slice(0, 30000);
}

// ── Dedup ──────────────────────────────────────────────────────────────────

export function dedup(items: ExtractedItem[]): ExtractedItem[] {
  const best = new Map<string, ExtractedItem>();
  const rank = { high: 3, medium: 2, low: 1 };
  for (const item of items) {
    const key = item.name.toLowerCase().trim();
    const existing = best.get(key);
    if (!existing || rank[item.confidence] > rank[existing.confidence]) {
      best.set(key, item);
    }
  }
  return [...best.values()];
}

// ── Helpers ────────────────────────────────────────────────────────────────

function toNum(v: unknown): number {
  if (typeof v === "number") return v;
  if (typeof v === "string") {
    const cleaned = v.replace(/\s/g, "").replace(",", ".");
    const n = parseFloat(cleaned);
    return isNaN(n) ? 0 : n;
  }
  return 0;
}
