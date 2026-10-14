import { useMutation } from "@tanstack/react-query";
import { CircleAlert } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useTrip } from "@/src/app/trip-context";
import { api } from "@/src/lib/api";
import { CHECKPOINT_INTERVAL_MI, CHECKPOINT_SPACING_OPTIONS_MI } from "@/src/lib/constants";
import type { CheckpointSpacingMi, RouteAnalysis } from "@/src/lib/types";

/**
 * Re-runs the analysis with a different checkpoint spacing. Route IDs change
 * on every analysis, so `onAnalyzed` should reset the selection.
 */
export function CheckpointSpacingControl({
  analysis,
  onAnalyzed,
}: {
  analysis: RouteAnalysis;
  onAnalyzed: () => void;
}) {
  const { setAnalysis } = useTrip();
  const current = analysis.trip.checkpointSpacingMi ?? CHECKPOINT_INTERVAL_MI;

  const reanalyze = useMutation({
    mutationFn: (spacing: CheckpointSpacingMi) =>
      api.analyzeRoutes(
        { ...analysis.trip, checkpointSpacingMi: spacing },
        // Keep an explicit demo run in demo; a live run that fell back retries live
        { demo: analysis.mode === "demo" && !analysis.fallback.routing },
      ),
    onSuccess: (next) => {
      setAnalysis(next);
      onAnalyzed();
    },
  });
  const pending = reanalyze.isPending ? reanalyze.variables : null;

  return (
    <section aria-label="Checkpoint spacing" className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-medium text-muted-foreground">Weather checkpoints every</h2>
        <div className="flex items-center gap-1 rounded-4xl bg-muted p-0.5 text-xs" role="group" aria-label="Checkpoint spacing">
          {CHECKPOINT_SPACING_OPTIONS_MI.map((mi) => (
            <Button
              key={mi}
              size="xs"
              variant={mi === (pending ?? current) ? "default" : "ghost"}
              aria-pressed={mi === current}
              disabled={reanalyze.isPending}
              onClick={() => mi !== current && reanalyze.mutate(mi)}
            >
              {pending === mi && <Spinner data-icon="inline-start" />}
              {mi} mi
            </Button>
          ))}
        </div>
      </div>
      {reanalyze.error && (
        <Alert variant="destructive">
          <CircleAlert />
          <AlertTitle>Couldn't re-analyze routes</AlertTitle>
          <AlertDescription>{reanalyze.error.message}</AlertDescription>
        </Alert>
      )}
    </section>
  );
}
