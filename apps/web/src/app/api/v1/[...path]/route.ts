import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;

const CANDIDATES = [
  process.env.BACKEND_API_URL,
  "https://salty-foxes-win.loca.lt",
  "https://agentiq-demo-api.loca.lt",
].filter(Boolean) as string[];

async function proxyRequest(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const pathStr = path ? path.join("/") : "";
  const searchParams = req.nextUrl.search;

  const headers: Record<string, string> = {
    "Bypass-Tunnel-Reminder": "true",
  };

  const auth = req.headers.get("authorization");
  if (auth) headers["authorization"] = auth;

  const workspaceId = req.headers.get("x-workspace-id");
  if (workspaceId) headers["x-workspace-id"] = workspaceId;

  const contentType = req.headers.get("content-type");
  if (contentType) headers["content-type"] = contentType;

  let body: ArrayBuffer | undefined = undefined;
  if (["POST", "PUT", "PATCH"].includes(req.method)) {
    body = await req.arrayBuffer();
  }

  for (const base of CANDIDATES) {
    const cleanBase = base.replace(/\/api\/v1\/?$/, "");
    const targetUrl = `${cleanBase}/api/v1/${pathStr}${searchParams}`;

    try {
      const res = await fetch(targetUrl, {
        method: req.method,
        headers,
        body,
        cache: "no-store",
        signal: AbortSignal.timeout(10000),
      });

      const resHeaders = new Headers();
      res.headers.forEach((val, key) => {
        if (!["content-encoding", "transfer-encoding"].includes(key.toLowerCase())) {
          resHeaders.set(key, val);
        }
      });

      const data = await res.arrayBuffer();
      return new NextResponse(data, {
        status: res.status,
        statusText: res.statusText,
        headers: resHeaders,
      });
    } catch {
      // try next candidate
    }
  }

  return NextResponse.json(
    {
      error: {
        code: "PROXY_ERROR",
        message: "Failed to communicate with backend service",
      },
    },
    { status: 502 }
  );
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PUT = proxyRequest;
export const PATCH = proxyRequest;
export const DELETE = proxyRequest;
