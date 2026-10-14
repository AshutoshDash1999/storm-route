import { Scan } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useMap } from "@/components/ui/map";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { boundsOf, FIT_PADDING } from "@/src/lib/geo";
import type { LngLat } from "@/src/lib/types";

/** mapcn's MapControls has no fit-bounds button, so this fills the gap. */
export function FitRouteButton({ coordinates }: { coordinates: LngLat[] }) {
  const { map } = useMap();
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <Button
            variant="outline"
            size="icon-sm"
            className="absolute top-3 right-3 z-10 bg-background shadow-sm"
            aria-label="Fit map to route"
            disabled={coordinates.length === 0}
            onClick={() =>
              map?.fitBounds(boundsOf(coordinates), { padding: FIT_PADDING, duration: 600 })
            }
          />
        }
      >
        <Scan />
      </TooltipTrigger>
      <TooltipContent side="left">Fit to route</TooltipContent>
    </Tooltip>
  );
}
