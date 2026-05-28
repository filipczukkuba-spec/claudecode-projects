import { ApifyClient } from "apify-client";
import { NextRequest, NextResponse } from "next/server";

export const maxDuration = 120;

const client = new ApifyClient({ token: process.env.APIFY_TOKEN });

interface RequestItem {
  name: string;
  unit: string;
}

async function searchLidl(query: string): Promise<number | null> {
  try {
    const run = await client.actor("studio-amba/lidl-scraper").call({
      searchQuery: query,
      country: "PL",
      sort: "relevancy",
      maxResults: 5,
    });

    const { items } = await client.dataset(run.defaultDatasetId).listItems();
    console.log(`[Lidl] query="${query}" items=${items?.length ?? 0}`, JSON.stringify(items?.[0] ?? {}));

    if (!items || items.length === 0) return null;

    const prices = items
      .map((item: Record<string, unknown>) => {
        const price = item.price ?? item.currentPrice ?? item.regularPrice ?? item.normalPrice;
        return typeof price === "number" ? price : null;
      })
      .filter((p): p is number => p !== null);

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

  // Search all items in parallel
  const lidlPrices = await Promise.all(
    items.map((item) => searchLidl(item.name))
  );

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
