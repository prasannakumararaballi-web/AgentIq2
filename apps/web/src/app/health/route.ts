import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;

const CANDIDATES = [
  process.env.BACKEND_API_URL,
  "https://salty-foxes-win.loca.lt",
  "https://agentiq-demo-api.loca.lt",
].filter(Boolean) as string[];

export async function GET() {
  for (const base of CANDIDATES) {
    const cleanBase = base.replace(/\/api\/v1\/?$/, "");
    try {
      const res = await fetch(`${cleanBase}/health`, {
        headers: { "Bypass-Tunnel-Reminder": "true" },
        cache: "no-store",
        signal: AbortSignal.timeout(4000),
      });
      if (res.ok) {
        const data = await res.json();
        return NextResponse.json(data, { status: 200 });
      }
    } catch {
      // try next candidate
    }
  }

  return NextResponse.json(
    { status: "degraded", version: "0.1.0", database: "unreachable" },
    { status: 502 }
  );
}
