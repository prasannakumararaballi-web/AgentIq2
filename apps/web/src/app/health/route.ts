import { NextResponse } from "next/server";

const TARGET_API_URL =
  process.env.BACKEND_API_URL ||
  "https://salty-foxes-win.loca.lt";

export async function GET() {
  const cleanBase = TARGET_API_URL.replace(/\/api\/v1\/?$/, "");
  const targetUrl = `${cleanBase}/health`;

  try {
    const res = await fetch(targetUrl, {
      headers: {
        "Bypass-Tunnel-Reminder": "true",
      },
      cache: "no-store",
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err: any) {
    return NextResponse.json(
      {
        status: "degraded",
        version: "0.1.0",
        database: "unreachable",
        error: err?.message,
      },
      { status: 502 }
    );
  }
}
