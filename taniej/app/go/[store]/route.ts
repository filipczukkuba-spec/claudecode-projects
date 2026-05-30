import { NextRequest, NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase-admin";
import { storeUrlFor } from "@/lib/store-links";
import { createHash } from "crypto";

export const maxDuration = 5;

// Forwards the user to the destination store, logs the click first so we
// can measure CTR per store. Fire-and-forget logging — if the DB write
// fails we still redirect (better UX than 500).
export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ store: string }> }
) {
  const { store } = await params;
  const url = new URL(req.url);
  const q = url.searchParams.get("q") ?? undefined;
  const target = storeUrlFor(store, q);

  if (!target) {
    return NextResponse.redirect(new URL("/", req.url));
  }

  try {
    const admin = createAdminClient();
    const ip = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? "unknown";
    const ipHash = createHash("sha256").update(ip).digest("hex").slice(0, 32);
    await admin.from("analytics_events").insert({
      event: "store_click",
      properties: { store, q: q ?? null },
      ip_hash: ipHash,
      user_agent: req.headers.get("user-agent")?.slice(0, 300) ?? null,
      referrer: req.headers.get("referer")?.slice(0, 300) ?? null,
      path: `/go/${store}`,
    });
  } catch {
    // best-effort — never block the redirect
  }

  return NextResponse.redirect(target, { status: 302 });
}
