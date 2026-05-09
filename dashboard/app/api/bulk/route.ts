import { NextRequest, NextResponse } from "next/server";
import { dispatchBulk } from "../../../lib/api";

export async function POST(req: NextRequest) {
  const { leads, throttle_ms } = await req.json();
  const result = await dispatchBulk(leads ?? [], throttle_ms);
  return NextResponse.json(result.body, { status: result.status });
}
