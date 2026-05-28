import { NextRequest, NextResponse } from "next/server";
import Anthropic from "@anthropic-ai/sdk";

export const maxDuration = 30;

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

export async function POST(req: NextRequest) {
  const { url } = await req.json();

  if (!url) {
    return NextResponse.json({ error: "No URL provided" }, { status: 400 });
  }

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

  // Strip HTML tags and trim to keep prompt small
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
        content: `Extract the list of ingredients from this recipe page. Return ONLY a JSON array of strings, each being a single ingredient name in Polish (translate if needed). No quantities, no units, no explanations — just ingredient names. Example: ["Jajka","Mleko","Mąka"]\n\n${text}`,
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
