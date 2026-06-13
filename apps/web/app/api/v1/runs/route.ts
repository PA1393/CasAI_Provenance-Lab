import { NextResponse } from "next/server";
import { createRun, listRuns } from "@/lib/mock/store";

export const dynamic = "force-dynamic";

export function GET() {
  return NextResponse.json({ items: listRuns() });
}

export async function POST(request: Request) {
  const body = await request.json();
  if (!body?.research_object_id || !body?.prompt) {
    return NextResponse.json(
      { detail: "research_object_id and prompt are required." },
      { status: 422 },
    );
  }
  const created = createRun(body);
  return NextResponse.json(created, { status: 201 });
}
