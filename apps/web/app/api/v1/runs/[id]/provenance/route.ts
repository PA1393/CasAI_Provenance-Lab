import { NextResponse } from "next/server";
import { listProvenance } from "@/lib/mock/store";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  return NextResponse.json({ items: listProvenance(id) });
}
