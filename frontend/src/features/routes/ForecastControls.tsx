import { useEffect, useState } from "react";
import { CloudOff, Clock, Pause, Play } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Spinner } from "@/components/ui/spinner";
import type { CheckpointView } from "@/src/features/routes/use-route-selection";
import { addHours, formatDateTime } from "@/src/lib/format";
import { FORECAST_HOURS } from "@/src/lib/constants";

const PLAY_STEP_MS = 700;

export function ForecastControls({
  departureAt,
  offset,
  onOffsetChange,
  view,
  onViewChange,
  loading,
  unavailable,
  error,
}: {
  departureAt: string;
  offset: number;
  onOffsetChange: (h: number) => void;
  view: CheckpointView;
  onViewChange: (v: CheckpointView) => void;
  loading: boolean;
  unavailable: boolean;
  error: Error | null;
}) {
  const [playing, setPlaying] = useState(false);

  // Advance one hour per tick; stop at the end of the forecast range
  useEffect(() => {
    if (!playing) return;
    const timer = setTimeout(() => {
      const next = Math.min(FORECAST_HOURS, offset + 1);
      onOffsetChange(next);
      if (next >= FORECAST_HOURS) setPlaying(false);
    }, PLAY_STEP_MS);
    return () => clearTimeout(timer);
  }, [playing, offset, onOffsetChange]);

  const togglePlay = () => {
    // Replay from departure when already at the end
    if (!playing && offset >= FORECAST_HOURS) onOffsetChange(0);
    setPlaying(!playing);
  };

  return (
    <section aria-label="Forecast time" className="flex flex-col gap-3 border-t bg-background px-4 py-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm">
          <Clock className="size-4 text-muted-foreground" />
          <span className="font-semibold tabular-nums">+{offset} h</span>
          <span className="text-muted-foreground">{formatDateTime(addHours(departureAt, offset))}</span>
          {loading && <Spinner className="size-3.5" />}
        </div>
        <div className="flex items-center gap-1 rounded-4xl bg-muted p-0.5 text-xs" role="group" aria-label="Checkpoint colors">
          <span className="px-2 text-muted-foreground">Checkpoints:</span>
          <Button
            size="xs"
            variant={view === "eta" ? "default" : "ghost"}
            aria-pressed={view === "eta"}
            onClick={() => onViewChange("eta")}
          >
            At arrival
          </Button>
          <Button
            size="xs"
            variant={view === "forecast" ? "default" : "ghost"}
            aria-pressed={view === "forecast"}
            onClick={() => onViewChange("forecast")}
          >
            At +{offset} h
          </Button>
        </div>
      </div>
      <div className="flex items-start gap-3">
        <Button
          size="icon-sm"
          variant="outline"
          onClick={togglePlay}
          aria-label={playing ? "Pause forecast playback" : "Play forecast"}
          aria-pressed={playing}
          className="-mt-2.5 shrink-0"
        >
          {playing ? <Pause /> : <Play />}
        </Button>
        <div className="flex min-w-0 flex-1 flex-col gap-3">
          <Slider
            value={[offset]}
            min={0}
            max={FORECAST_HOURS}
            step={1}
            onValueChange={(v) => {
              setPlaying(false);
              onOffsetChange(Array.isArray(v) ? v[0] : v);
            }}
            aria-label="Hours after departure"
          />
          <div className="flex justify-between text-xs text-muted-foreground tabular-nums">
            <span>Departure</span>
            <span>+12 h</span>
            <span>+24 h</span>
            <span>+36 h</span>
            <span>+48 h</span>
          </div>
        </div>
      </div>
      {(unavailable || error) && (
        <Alert>
          <CloudOff />
          <AlertTitle>Forecast unavailable for +{offset} h</AlertTitle>
          <AlertDescription>
            {error
              ? error.message
              : "The weather provider has no forecast this far out. The heatmap is hidden and checkpoints show No data, not Low."}
          </AlertDescription>
        </Alert>
      )}
    </section>
  );
}
