import type { AnchorHTMLAttributes } from "react";
import { routePath } from "./navigation";

export default function Link({ href, children, ...props }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) {
  const internal = routePath(`#${href}`) === href;
  return <a {...props} href={internal ? `#${href}` : "#/"}>{children}</a>;
}
