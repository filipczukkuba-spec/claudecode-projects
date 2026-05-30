import { NextRequest, NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase-admin";
import { createHash } from "crypto";

export const maxDuration = 5;

const KNOWN_EVENTS = new Set([
  "pageview",
  "search_submitted",
  "receipt_scanned",
  "receipt_scan_failed",
  "list_shared",
  "install_clicked",
  "install_accepted",
  "price_reported",
]);

// Tiny endpoint — keep it cheap. Fire-and-forget from the client.
export async function POST(req: NextRequest) {
  let body: any;
  try { body = await req.json(); } catch { return new NextResponse(null, { status: 204 }); }

  const event = String(body?.event ?? "").slice(0, 40);
  if (!event || !KNOWN_EVENTS.has(event)) {
    return new NextResponse(null, { status: 204 });
  }

  const props = body?.properties && typeof body.properties === "object" ? body.properties : null;
  const sessionId = body?.session_id ? String(body.session_id).slice(0, 40) : null;
  const path = body?.path ? String(body.path).slice(0, 200) : null;
  const referrer = body?.referrer ? String(body.referrer).slice(0, 300) : null;
  const ua = req.headers.get("user-agent")?.slice(0, 300) ?? null;

  const ip = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? "unknown";
  const ipHash = createHash("sha256").update(ip).digest("hex").slice(0, 32);

  try {
    const admin = createAdminClient();
    await admin.from("analytics_events").insert({
      event,
      properties: props,
      session_id: sessionId,
      ip_hash: ipHash,
      user_agent: ua,
      referrer,
      path,
    });
  } catch {
    // best-effort — never break the client
  }

  return new NextResponse(null, { status: 204 });
}
