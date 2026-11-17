import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

export async function GET() {
  try {
    // Priority 1: Check apps/web/public/demo_customers_1000.csv (Vercel production root)
    const publicPath = path.join(process.cwd(), "public", "demo_customers_1000.csv");
    // Priority 2: Check repo root storage/demo/demo_customers_1000.csv (monorepo local dev fallback)
    const rootDir = path.resolve(process.cwd(), "..", "..");
    const repoPath = path.join(rootDir, "storage", "demo", "demo_customers_1000.csv");

    const demoCsvPath = fs.existsSync(publicPath) ? publicPath : repoPath;

    if (!fs.existsSync(demoCsvPath)) {
      return NextResponse.json(
        { error: "Demo CSV file not found on server disk. Run python scripts/generate_demo_dataset.py" },
        { status: 404 }
      );
    }

    const csvContent = fs.readFileSync(demoCsvPath);

    return new Response(csvContent, {
      status: 200,
      headers: {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": 'attachment; filename="demo_customers_1000.csv"',
        "Content-Length": String(csvContent.length),
      },
    });
  } catch (err) {
    return NextResponse.json(
      { error: "Failed to read demo dataset file" },
      { status: 500 }
    );
  }
}
