import { NextRequest, NextResponse } from "next/server";
import { fetchViaJina } from "@/lib/price-extractor";

function checkAuth(req: NextRequest) {
  return req.headers.get("authorization") === `Bearer ${process.env.ADMIN_PASSWORD}`;
}

// GET /api/admin/debug-scrape?url=https://www.biedronka.pl/pl/oferta-tygodnia
export async function GET(req: NextRequest) {
  if (!checkAuth(req)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const url = req.nextUrl.searchParams.get("url");
  if (!url) {
    return NextResponse.json({ error: "url param required" }, { status: 400 });
  }

  const text = await fetchViaJina(url);

  return NextResponse.json({
    url,
    chars: text.length,
    preview: text.slice(0, 2000),
    hasPrices: /\d+[,.]\d{2}\s*z[łl]/i.test(text),
  });
}
