// Memory only: no token/password in localStorage, URLs, feedback or exports.
export type Session = { access_token: string; expires_in: number; user: { id: string; email: string } };
let session: Session | null = null;
let expiresAt = 0;
const listeners = new Set<() => void>();
export function setSession(value: Session | null) {
  session = value;
  expiresAt = value ? Date.now() + value.expires_in * 1000 : 0;
  for (const listener of listeners) listener();
}
export function getSession() { return session; }
export function accessToken() {
  if (session && Date.now() >= expiresAt) { setSession(null); }
  return session?.access_token ?? null;
}
export function subscribeSession(listener: () => void) {
  listeners.add(listener);
  return () => { listeners.delete(listener); };
}
