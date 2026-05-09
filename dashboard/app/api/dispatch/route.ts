import { NextRequest, NextResponse } from "next/server";
import { dispatchSingle } from "../../../lib/api";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const result = await dispatchSingle(body);
  return NextResponse.json(result.body, { status: result.status });
}
