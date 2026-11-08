"use client";

import { useEffect, useState, type ReactNode } from "react";
import { getSession, subscribeSession, accessToken } from "../../lib/auth-session";
import { signIn, signOut } from "../../lib/api/client";

export function AuthGate({ children }: { children: ReactNode }) {
  const [session, setCurrent] = useState(getSession);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => subscribeSession(() => setCurrent(getSession())), []);
  useEffect(() => {
    const timer = setInterval(() => { accessToken(); }, 10_000);
    return () => clearInterval(timer);
  }, []);
  if (!session) return <main id="main-content" className="mx-auto max-w-md px-6 py-20">
    <h1 className="font-serif-display text-4xl">Sign in to CasAI</h1>
    <p className="mt-4 text-sm text-text-secondary">Your research, folders and runs stay in your account. Existing shared demo records are not imported.</p>
    <form className="mt-8 grid gap-4" onSubmit={async event => {
      event.preventDefault(); if (busy) return; setBusy(true); setError("");
      try { await signIn(email.trim(), password); setPassword(""); }
      catch (caught) { setError(caught instanceof Error ? caught.message : "Sign-in unavailable"); }
      finally { setBusy(false); }
    }}>
      <label>Email<input autoComplete="username" type="email" required maxLength={254} disabled={busy} value={email} onChange={e => setEmail(e.target.value)} className="mt-2 w-full rounded-lg border border-border bg-bg-card p-3" /></label>
      <label>Password<input autoComplete="current-password" type="password" required maxLength={1024} disabled={busy} value={password} onChange={e => setPassword(e.target.value)} className="mt-2 w-full rounded-lg border border-border bg-bg-card p-3" /></label>
      {error && <p role="alert" className="text-sm text-accent-amber">{error}</p>}
      <button disabled={busy} className="rounded-lg bg-accent p-3 font-semibold text-bg disabled:opacity-40">{busy ? "Signing in…" : "Sign in"}</button>
    </form>
    <p className="mt-5 text-xs leading-6 text-muted">For this demo, ask the administrator for an account or a password reset. Sign-in lasts for this app session; closing or reloading signs you out. Use public or synthetic inputs only.</p>
  </main>;
  return <div key={session.user.id}>
    <div className="flex flex-wrap items-center justify-end gap-4 border-b border-border px-6 py-2 text-xs">
      <span>{session.user.email}</span><button disabled={busy} onClick={async () => {
        setBusy(true); try { await signOut(); } catch { /* Local session is always cleared. */ }
        finally { setBusy(false); }
      }} className="text-accent">Sign out</button>
    </div>{children}
  </div>;
}
