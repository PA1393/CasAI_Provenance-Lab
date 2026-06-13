import { NextResponse } from "next/server";
import { getResearchObject } from "@/lib/mock/store";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const ro = getResearchObject(id);
  if (!ro) {
    return NextResponse.json(
      { detail: "Research object not found." },
      { status: 404 },
    );
  }
  return NextResponse.json(ro);
}
