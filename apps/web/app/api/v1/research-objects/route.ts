import { NextResponse } from "next/server";
import {
  createResearchObject,
  listResearchObjects,
} from "@/lib/mock/store";

export const dynamic = "force-dynamic";

export function GET() {
  return NextResponse.json({ items: listResearchObjects() });
}

export async function POST(request: Request) {
  const body = await request.json();
  if (!body?.name || !body?.input_filename || !body?.pdb_id) {
    return NextResponse.json(
      { detail: "name, input_filename, and pdb_id are required." },
      { status: 422 },
    );
  }
  const created = createResearchObject(body);
  return NextResponse.json(created, { status: 201 });
}
