// Fire-and-forget event tracker. Writes to /api/track which persists in
// Supabase. Replaces @vercel/analytics's track() because custom events
// require Pro on Vercel. This is free and the data stays with us.

const SESSION_KEY = "taniejkupuj:sid";

function sid(): string | null {
  if (typeof window === "undefined") return null;
  try {
    let s = localStorage.getItem(SESSION_KEY);
    if (!s) {
      s = crypto.randomUUID();
      localStorage.setItem(SESSION_KEY, s);
    }
    return s;
  } catch {
    return null;
  }
}

export function track(event: string, properties?: Record<string, any>): void {
  if (typeof window === "undefined") return;
  const payload = JSON.stringify({
    event,
    properties: properties ?? null,
    session_id: sid(),
    path: window.location.pathname + window.location.search,
    referrer: document.referrer || null,
  });

  // Beacon is best on page-unload events; for in-app events keepalive fetch
  // is fine and lets us send a body up to 64KB.
  try {
    fetch("/api/track", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: payload,
      keepalive: true,
    }).catch(() => {});
  } catch {
    // no-op
  }
}
