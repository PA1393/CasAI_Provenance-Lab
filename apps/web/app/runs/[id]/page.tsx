"use client";
import { use, useCallback } from "react";
import { AsyncView } from "../../../components/layout/async-view";
import render from "../../../components/runs/run-detail-view";
export default function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const load = useCallback(() => render({ params: Promise.resolve({ id }) }), [id]);
  return <AsyncView load={load} />;
}
