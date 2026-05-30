import { NextRequest, NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase-admin";

export const maxDuration = 10;

function checkAuth(req: NextRequest) {
  const auth = req.headers.get("authorization");
  return auth === `Bearer ${process.env.ADMIN_PASSWORD}`;
}

interface EventRow {
  event: string;
  session_id: string | null;
  ip_hash: string | null;
  created_at: string;
  properties: any;
  path: string | null;
  referrer: string | null;
}

export async function GET(req: NextRequest) {
  if (!checkAuth(req)) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const url = new URL(req.url);
  const daysParam = parseInt(url.searchParams.get("days") ?? "7", 10);
  const days = Math.max(1, Math.min(90, isNaN(daysParam) ? 7 : daysParam));
  const since = new Date(Date.now() - days * 86400_000).toISOString();

  const admin = createAdminClient();

  const { data: rows, error } = await admin
    .from("analytics_events")
    .select("event, session_id, ip_hash, created_at, properties, path, referrer")
    .gte("created_at", since)
    .order("created_at", { ascending: false })
    .limit(5000);

  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  const events = (rows ?? []) as EventRow[];

  // Aggregate by event name
  const counts: Record<string, number> = {};
  const uniqueSessions: Record<string, Set<string>> = {};
  for (const e of events) {
    counts[e.event] = (counts[e.event] ?? 0) + 1;
    if (e.session_id) {
      if (!uniqueSessions[e.event]) uniqueSessions[e.event] = new Set();
      uniqueSessions[e.event].add(e.session_id);
    }
  }

  const totalSessions = new Set(events.map((e) => e.session_id).filter(Boolean)).size;
  const totalIpHashes = new Set(events.map((e) => e.ip_hash).filter(Boolean)).size;

  // Funnel: pageview → search_submitted → receipt_scanned
  const funnel = {
    pageview:           uniqueSessions["pageview"]?.size           ?? 0,
    search_submitted:   uniqueSessions["search_submitted"]?.size   ?? 0,
    receipt_scanned:    uniqueSessions["receipt_scanned"]?.size    ?? 0,
    list_shared:        uniqueSessions["list_shared"]?.size        ?? 0,
    install_clicked:    uniqueSessions["install_clicked"]?.size    ?? 0,
  };

  // Per-day pageviews
  const byDay: Record<string, number> = {};
  for (const e of events) {
    if (e.event !== "pageview") continue;
    const day = e.created_at.slice(0, 10);
    byDay[day] = (byDay[day] ?? 0) + 1;
  }

  // Recent events tail
  const recent = events.slice(0, 50).map((e) => ({
    event: e.event,
    created_at: e.created_at,
    properties: e.properties,
    path: e.path,
    referrer: e.referrer,
  }));

  // Top referrers
  const refCounts: Record<string, number> = {};
  for (const e of events) {
    if (e.event !== "pageview") continue;
    let host = "(direct)";
    try { if (e.referrer) host = new URL(e.referrer).hostname; } catch {}
    refCounts[host] = (refCounts[host] ?? 0) + 1;
  }
  const topReferrers = Object.entries(refCounts)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 10)
    .map(([host, count]) => ({ host, count }));

  return NextResponse.json({
    days,
    total_events: events.length,
    unique_sessions: totalSessions,
    unique_ips: totalIpHashes,
    counts,
    funnel,
    by_day: byDay,
    top_referrers: topReferrers,
    recent,
  });
}
