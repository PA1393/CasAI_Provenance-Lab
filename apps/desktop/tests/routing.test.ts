import { expect, test } from "bun:test";
import { routePath } from "../src/compat/navigation";

test("hash routes preserve internal navigation without requiring a Next server", () => {
  expect(routePath("")).toBe("/");
  expect(routePath("#/research-objects/new")).toBe("/research-objects/new");
  expect(routePath("#/runs/a-b-123")).toBe("/runs/a-b-123");
});

test("navigation never treats external protocols or protocol-relative URLs as local", () => {
  for (const hash of ["#https://example.org", "#javascript:alert(1)", "#//evil.example", "#/\\evil.example", "#/\nmalformed"]) {
    expect(routePath(hash)).toBe("/");
  }
});
