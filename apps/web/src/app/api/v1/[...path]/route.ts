import { NextRequest, NextResponse } from "next/server";

const TARGET_API_URL =
  process.env.BACKEND_API_URL ||
  "https://agentiq-demo-api.loca.lt/api/v1";

async function proxyRequest(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const pathStr = path ? path.join("/") : "";
  const searchParams = req.nextUrl.search;

  const cleanBase = TARGET_API_URL.replace(/\/api\/v1\/?$/, "");
  const targetUrl = `${cleanBase}/api/v1/${pathStr}${searchParams}`;

  const headers: Record<string, string> = {
    "Bypass-Tunnel-Reminder": "true",
  };

  const auth = req.headers.get("authorization");
  if (auth) headers["authorization"] = auth;

  const workspaceId = req.headers.get("x-workspace-id");
  if (workspaceId) headers["x-workspace-id"] = workspaceId;

  const contentType = req.headers.get("content-type");
  if (contentType) headers["content-type"] = contentType;

  try {
    let body: BodyInit | undefined = undefined;
    if (["POST", "PUT", "PATCH"].includes(req.method)) {
      body = await req.arrayBuffer();
    }

    const res = await fetch(targetUrl, {
      method: req.method,
      headers,
      body,
      cache: "no-store",
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
  } catch (err: any) {
    console.error("API proxy error:", err);
    return NextResponse.json(
      {
        error: {
          code: "PROXY_ERROR",
          message: err?.message || "Failed to communicate with backend service",
        },
      },
      { status: 502 }
    );
  }
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PUT = proxyRequest;
export const DELETE = proxyRequest;
export const PATCH = proxyRequest;
