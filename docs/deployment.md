# Deployment

This deploys a **public demo** where users hit a hosted backend that holds the
OpenAI key server-side. Usage draws down the account behind that key. The key is
stored in the host's secret store — **never in this repo**.

Architecture:

```
Browser → Frontend (Vercel, Next.js) → Backend (Render, FastAPI) → OpenAI + Supabase
                                              ^ holds OPENAI_API_KEY as a secret
```

## 1. Backend on Render (holds the OpenAI key)

1. Push this repo to GitHub (already done for the `KavAddon` branch).
2. Render Dashboard → **New → Blueprint** → select this repo. Render reads
   `render.yaml` and creates the `casai-provenance-api` web service.
3. In the service's **Environment** tab, set these (they are `sync: false`, so
   they live only in Render, not the repo):
   - `OPENAI_API_KEY` — your OpenAI key (this is what powers the demo).
   - `SUPABASE_URL` — your Supabase project URL.
   - `SUPABASE_SERVICE_KEY` — your Supabase service role key.
   - `CORS_ORIGIN` — your frontend URL, e.g. `https://your-app.vercel.app`.
   - `OPENAI_CHAT_MODEL` — optional, defaults to `gpt-4o-mini`.
4. Deploy. Confirm health at `https://<your-service>.onrender.com/health`.

## 2. Frontend on Vercel

1. Vercel → **New Project** → import this repo.
2. Set **Root Directory** to `apps/web`.
3. Environment variable:
   - `NEXT_PUBLIC_API_BASE_URL` = your Render backend URL
     (e.g. `https://casai-provenance-api.onrender.com`).
4. Deploy. Then set the backend's `CORS_ORIGIN` (step 1.3) to this Vercel URL and
   redeploy the backend.

## Rotating / protecting the key

- The key lives only in Render's secret store. To rotate it, update
  `OPENAI_API_KEY` in Render and redeploy — no code change.
- Set usage limits in the OpenAI dashboard (Billing → Limits) to cap demo spend.
- Never paste the key into source files; GitHub push protection will block it and
  OpenAI will auto-revoke any key found in a public repo.

## Local development

See `docs/setup.md`. Locally the key comes from `apps/api/.env` (gitignored); copy
`apps/api/.env.example` to `apps/api/.env` and fill in values.
