"use client";
import { AsyncView } from "../../components/layout/async-view";
import load from "../../components/research-objects/research-list-view";
export default function Page() { return <AsyncView load={load} />; }
