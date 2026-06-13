import { NextResponse } from "next/server";
import { getRun } from "@/lib/mock/store";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const run = getRun(id);
  if (!run) {
    return NextResponse.json({ detail: "Run not found." }, { status: 404 });
  }
  return NextResponse.json(run);
}
