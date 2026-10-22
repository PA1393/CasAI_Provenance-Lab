import { lazy, Suspense, type ComponentType } from "react";

// Desktop is entirely client-rendered: Next's ssr:false has no server equivalent.
export default function dynamic<P extends object>(
  loader: () => Promise<ComponentType<P>>,
  _options?: { ssr?: boolean },
): ComponentType<P> {
  const Component = lazy(async () => ({ default: await loader() }));
  return function LazyDesktopComponent(props: P) {
    return <Suspense fallback={<p role="status">Loading molecular viewer…</p>}><Component {...props} /></Suspense>;
  };
}
