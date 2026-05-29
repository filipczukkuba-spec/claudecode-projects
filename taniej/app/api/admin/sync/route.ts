import { NextRequest, NextResponse } from "next/server";
import { POST as cronPost } from "@/app/api/cron/update-prices/route";

function checkAuth(req: NextRequest) {
  return req.headers.get("authorization") === `Bearer ${process.env.ADMIN_PASSWORD}`;
}

export async function POST(req: NextRequest) {
  if (!checkAuth(req)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  // Forward to the cron handler with server-side secret — CRON_SECRET never touches client
  const cronReq = new NextRequest(req.url, {
    method: "POST",
    headers: new Headers({ authorization: `Bearer ${process.env.CRON_SECRET}` }),
  });

  return cronPost(cronReq);
}
