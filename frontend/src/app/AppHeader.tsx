import type { ReactNode } from "react";
import { CloudLightning } from "lucide-react";
import { Link } from "react-router";


export function AppHeader({
  children,
  actions,
}: {
  /** Trip summary shown next to the logo */
  children?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-center gap-x-6 gap-y-2 border-b bg-background px-4 py-3 md:px-6">
      <Link to="/" className="flex items-center gap-2 font-semibold tracking-tight">
        <span className="flex size-8 items-center justify-center rounded-xl bg-primary text-primary-foreground">
          <CloudLightning className="size-4" />
        </span>
        StormRoute
      </Link>
      <div className="min-w-0 flex-1">{children}</div>
      <div className="flex items-center gap-2">
        {actions}
      </div>
    </header>
  );
}
