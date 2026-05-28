import { NextRequest, NextResponse } from "next/server";
import Anthropic from "@anthropic-ai/sdk";
import { supabase } from "@/lib/supabase";

export const maxDuration = 30;

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

export async function POST(req: NextRequest) {
  const { url } = await req.json();

  if (!url) {
    return NextResponse.json({ error: "No URL provided" }, { status: 400 });
  }

  // Fetch known products so Claude can map to exact names
  const { data: products } = await supabase.from("products").select("name");
  const knownProducts = products?.map((p) => p.name) ?? [];

  let html: string;
  try {
    const res = await fetch(url, {
      headers: { "User-Agent": "Mozilla/5.0 (compatible; RecipeBot/1.0)" },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    html = await res.text();
  } catch (e: any) {
    return NextResponse.json({ error: `Could not fetch URL: ${e.message}` }, { status: 400 });
  }

  const text = html
    .replace(/<script[\s\S]*?<\/script>/gi, "")
    .replace(/<style[\s\S]*?<\/style>/gi, "")
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .slice(0, 8000);

  const message = await client.messages.create({
    model: "claude-haiku-4-5-20251001",
    max_tokens: 512,
    messages: [
      {
        role: "user",
        content: `You are a grocery matching assistant. Extract ingredients from this recipe and map each one to the closest product from the known list below.

Known products: ${knownProducts.join(", ")}

Rules:
- Return ONLY a JSON array of product names from the known list above
- If an ingredient matches a known product closely, use the exact known product name
- If no match exists, include the original ingredient name in Polish
- No quantities, no units, no explanations

Recipe page text:
${text}`,
      },
    ],
  });

  const raw = (message.content[0] as any).text as string;

  let ingredients: string[];
  try {
    const match = raw.match(/\[[\s\S]*\]/);
    if (!match) throw new Error("No array found");
    ingredients = JSON.parse(match[0]);
  } catch {
    return NextResponse.json({ error: "Could not parse ingredients from AI response" }, { status: 500 });
  }

  return NextResponse.json({ ingredients });
}
