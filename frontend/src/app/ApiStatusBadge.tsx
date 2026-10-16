import { useQuery } from "@tanstack/react-query";
import { CircleAlert, FlaskConical, Radio } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { api } from "@/src/lib/api";

/** Backend reachability and data mode, polled from `/health/` */
export function ApiStatusBadge() {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => api.getHealth({ signal }),
    refetchInterval: 60_000,
    retry: 2,
  });

  if (health.isPending) {
    return (
      <Badge variant="outline" className="text-muted-foreground">
        <Spinner />
        Connecting…
      </Badge>
    );
  }

  if (health.isError) {
    return (
      <Tooltip>
        <TooltipTrigger
          render={<Badge variant="outline" className="border-destructive/40 text-destructive" />}
        >
          <CircleAlert />
          Server offline
        </TooltipTrigger>
        <TooltipContent>{health.error.message}</TooltipContent>
      </Tooltip>
    );
  }

  const { mode, providers } = health.data;
  const live = mode === "live";
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <Badge
            variant="outline"
            className={
              live
                ? "border-emerald-600/40 text-emerald-700 dark:text-emerald-400"
                : "border-amber-600/40 text-amber-700 dark:text-amber-400"
            }
          />
        }
      >
        {live ? <Radio /> : <FlaskConical />}
        {live ? "Live data" : "Demo mode"}
      </TooltipTrigger>
      <TooltipContent>
        Routing: {providers.routing} · Weather: {providers.weather}
      </TooltipContent>
    </Tooltip>
  );
}
