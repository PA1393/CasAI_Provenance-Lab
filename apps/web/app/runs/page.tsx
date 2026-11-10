"use client";
import { AsyncView } from "../../components/layout/async-view";
import load from "../../components/runs/run-list-view";
export default function Page() { return <AsyncView load={load} />; }
