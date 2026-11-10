export const DEMO_REVIEW_VERSION = "demo-review-1";
const categories = ["usability", "input", "run", "viewer", "export", "other"];

export function buildDemoFeedback(input: {
  category: string; expected: string; actual: string; context: string; platform: string;
}, now = new Date()) {
  if (!categories.includes(input.category)) throw new Error("Choose a feedback category.");
  if (!input.actual.trim()) throw new Error("Describe what happened before saving feedback.");
  if (input.expected.length > 2000 || input.actual.length > 2000) throw new Error("Keep each description under 2,000 characters.");
  const context = /^(?:\/|\/(?:research-objects|runs)(?:\/(?:new|[A-Za-z0-9_-]{1,128}))?)$/.test(input.context)
    ? input.context : "/";
  return {
    schema_version: "casai.demo-feedback.v1", app_version: DEMO_REVIEW_VERSION,
    created_at: now.toISOString(), platform: input.platform.slice(0, 100), context,
    category: input.category, expected: input.expected.trim(), actual: input.actual.trim(),
  };
}
