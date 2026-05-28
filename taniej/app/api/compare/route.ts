import { NextRequest, NextResponse } from "next/server";

export const maxDuration = 60;

interface RequestItem {
  name: string;
  unit: string;
}

interface LidlProduct {
  name: string;
  price: number;
  currency: string;
  category: string;
}

async function searchLidl(query: string): Promise<number | null> {
  try {
    const url = `https://www.lidl.pl/q/api/search?assortment=PL&locale=pl_PL&version=v2.0.0&offset=0&limit=10&sort=relevancy&query=${encodeURIComponent(query)}`;

    const res = await fetch(url, {
      headers: {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Accept-Language": "pl-PL,pl;q=0.9",
        "Referer": "https://www.lidl.pl/",
      },
      next: { revalidate: 3600 },
    });

    if (!res.ok) {
      console.error(`[Lidl] HTTP ${res.status} for "${query}"`);
      return null;
    }

    const data = await res.json();
    console.log(`[Lidl] "${query}" → total=${data.pagination?.total}, first="${data.results?.[0]?.name}"`);

    const results: LidlProduct[] = data.results ?? [];
    if (results.length === 0) return null;

    // Filter to food/grocery category — skip clothes, electronics etc.
    const foodCategories = ["spożywcze", "owoce", "warzywa", "nabiał", "pieczywo", "napoje", "mięso", "ryby", "słodycze", "przekąski", "kawa", "herbata", "oleje", "przyprawy", "chemia", "higiena"];
    const foodResults = results.filter((r) => {
      const cat = (r.category ?? "").toLowerCase();
      return foodCategories.some((fc) => cat.includes(fc));
    });

    const pool = foodResults.length > 0 ? foodResults : results;
    const prices = pool.map((r) => r.price).filter((p): p is number => typeof p === "number" && p > 0);

    if (prices.length === 0) return null;
    return Math.min(...prices);
  } catch (e) {
    console.error(`[Lidl] error for "${query}":`, e);
    return null;
  }
}

export async function POST(req: NextRequest) {
  const { items }: { items: RequestItem[] } = await req.json();

  if (!items || items.length === 0) {
    return NextResponse.json({ error: "No items provided" }, { status: 400 });
  }

  const lidlPrices = await Promise.all(items.map((item) => searchLidl(item.name)));

  const results = [
    {
      name: "Lidl",
      logo: "🛍️",
      prices: items.map((item, i) => ({
        item: item.name,
        unit: item.unit,
        price: lidlPrices[i],
      })),
    },
  ];

  return NextResponse.json({ results });
}
