import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { CheckpointDetails } from "@/src/features/routes/CheckpointDetails";
import { formatMiles } from "@/src/lib/format";
import type { Checkpoint, CheckpointWeather, Route } from "@/src/lib/types";

export function CheckpointDrawer({
  route,
  checkpoint,
  weather,
  weatherLabel,
  onClose,
}: {
  route: Route;
  checkpoint: Checkpoint | null;
  weather?: CheckpointWeather;
  weatherLabel: string;
  onClose: () => void;
}) {
  return (
    <Sheet open={checkpoint !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" className="w-full sm:max-w-md">
        {checkpoint && (
          <>
            <SheetHeader>
              <SheetTitle>Checkpoint at {formatMiles(checkpoint.mileFromOrigin)}</SheetTitle>
              <SheetDescription>{route.name}</SheetDescription>
            </SheetHeader>
            <ScrollArea className="min-h-0 flex-1 px-4 pb-6">
              <CheckpointDetails checkpoint={checkpoint} weather={weather} weatherLabel={weatherLabel} />
            </ScrollArea>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
