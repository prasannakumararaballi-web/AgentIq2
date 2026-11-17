import { NextResponse } from "next/server";
import crypto from "crypto";

const TEST_SECRET = process.env.SUPABASE_JWT_SECRET || "test-secret-key-for-agentiq-pytest-environment-at-least-32-chars";

function base64UrlEncode(str: string): string {
  return Buffer.from(str)
    .toString("base64")
    .replace(/=/g, "")
    .replace(/\+/g, "-")
    .replace(/\//g, "_");
}

function signJwt(payload: Record<string, unknown>, secret: string): string {
  const header = { alg: "HS256", typ: "JWT" };
  const encodedHeader = base64UrlEncode(JSON.stringify(header));
  const encodedPayload = base64UrlEncode(JSON.stringify(payload));
  const signature = crypto
    .createHmac("sha256", secret)
    .update(`${encodedHeader}.${encodedPayload}`)
    .digest("base64")
    .replace(/=/g, "")
    .replace(/\+/g, "-")
    .replace(/\//g, "_");

  return `${encodedHeader}.${encodedPayload}.${signature}`;
}

export async function POST(req: Request) {
  try {
    // In production, allow demo token only for staging or when live Supabase is not configured
    const isLiveSupabase = Boolean(
      process.env.NEXT_PUBLIC_SUPABASE_URL &&
      !process.env.NEXT_PUBLIC_SUPABASE_URL.includes("placeholder") &&
      !process.env.NEXT_PUBLIC_SUPABASE_URL.includes("local")
    );
    if (process.env.NODE_ENV === "production" && isLiveSupabase && process.env.ENABLE_DEMO_AUTH !== "true") {
      return NextResponse.json(
        { error: "Demo authentication is disabled in production with live Supabase." },
        { status: 403 }
      );
    }

    const body = await req.json().catch(() => ({}));
    const role = body.role || "admin";

    // Well-known test user UUIDs and RFC-compliant email domains for Pydantic EmailStr compatibility
    let userId = "00000000-0000-0000-0000-000000000099"; // Admin
    let email = "admin@example.com";
    let fullName = "Demo Administrator";

    if (role === "reviewer") {
      userId = "00000000-0000-0000-0000-000000000088";
      email = "reviewer@example.com";
      fullName = "Demo Reviewer";
    } else if (role === "viewer") {
      userId = "00000000-0000-0000-0000-000000000077";
      email = "viewer@example.com";
      fullName = "Demo Viewer";
    }

    const now = Math.floor(Date.now() / 1000);
    const payload = {
      sub: userId,
      email,
      aud: "authenticated",
      role: "authenticated",
      user_metadata: {
        full_name: fullName,
      },
      iat: now,
      exp: now + 3600 * 24, // 24 hours
    };

    const token = signJwt(payload, TEST_SECRET);

    return NextResponse.json({
      token,
      user_id: userId,
      email,
      role,
      workspace_id: "00000000-0000-0000-0000-000000000001",
    });
  } catch (err) {
    return NextResponse.json(
      { error: "Failed to generate demo session token" },
      { status: 500 }
    );
  }
}
