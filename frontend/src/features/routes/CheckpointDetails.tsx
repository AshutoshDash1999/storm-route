import { CloudRain, CloudOff, Gauge, Radio, Snowflake, Wind, FlaskConical } from "lucide-react";
import type { ReactNode } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { RiskBadge } from "@/src/features/routes/RiskBadge";
import { formatDateTime, formatMeasure, formatMiles } from "@/src/lib/format";
import type { Checkpoint, CheckpointWeather, ConditionClass, DataSource } from "@/src/lib/types";

const SOURCE: Record<DataSource, { label: string; icon: typeof Radio; className: string }> = {
  live: { label: "Live", icon: Radio, className: "text-emerald-700 dark:text-emerald-400" },
  simulated: { label: "Simulated", icon: FlaskConical, className: "text-amber-700 dark:text-amber-400" },
  unavailable: { label: "Unavailable", icon: CloudOff, className: "text-muted-foreground" },
};

export function SourceBadge({ source }: { source: DataSource }) {
  const s = SOURCE[source];
  const Icon = s.icon;
  return (
    <Badge variant="outline" className={s.className}>
      <Icon />
      {s.label}
    </Badge>
  );
}

function Measurement({ icon, label, condition }: { icon: ReactNode; label: string; condition: ConditionClass }) {
  return (
    <div className="flex items-center gap-3 py-2">
      <span className="flex size-8 shrink-0 items-center justify-center rounded-xl bg-muted text-muted-foreground">
        {icon}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="font-medium tabular-nums">{formatMeasure(condition.value, condition.unit)}</p>
      </div>
      <RiskBadge risk={condition.risk} />
    </div>
  );
}

export function CheckpointDetails({
  checkpoint,
  weather,
  weatherLabel,
}: {
  checkpoint: Checkpoint;
  /** Weather to show; defaults to the checkpoint's ETA weather */
  weather?: CheckpointWeather;
  /** What time the weather describes, e.g. "At arrival" or "Forecast +12 h" */
  weatherLabel: string;
}) {
  const w = weather ?? checkpoint.weather;
  const missing = w.source === "unavailable";

  return (
    <div className="flex flex-col gap-4 text-sm">
      <dl className="grid grid-cols-2 gap-3">
        <div>
          <dt className="text-xs text-muted-foreground">Distance from origin</dt>
          <dd className="font-medium">{formatMiles(checkpoint.mileFromOrigin)}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Estimated arrival</dt>
          <dd className="font-medium">{formatDateTime(checkpoint.etaAt)}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Location</dt>
          <dd className="font-medium">{checkpoint.place}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Data source</dt>
          <dd>
            <SourceBadge source={w.source} />
          </dd>
        </div>
      </dl>

      <Separator />

      <div className="flex items-center justify-between gap-2">
        <div>
          <p className="text-xs text-muted-foreground">Overall risk · {weatherLabel}</p>
          <p className="text-base font-semibold">Checkpoint {checkpoint.index + 1}</p>
        </div>
        <RiskBadge risk={w.overall} className="h-6 px-2.5 text-sm" />
      </div>

      {missing ? (
        <Alert>
          <CloudOff />
          <AlertTitle>No weather data for this checkpoint</AlertTitle>
          <AlertDescription>
            Outside forecast coverage or not reported by the provider. This checkpoint is Unknown,
            never treated as Low, and its miles are scored as Severe.
          </AlertDescription>
        </Alert>
      ) : (
        <div className="divide-y">
          <Measurement icon={<Wind className="size-4" />} label="Wind speed" condition={w.wind} />
          <Measurement icon={<CloudRain className="size-4" />} label="Rain intensity" condition={w.rain} />
          <Measurement icon={<Snowflake className="size-4" />} label="Snowfall intensity" condition={w.snow} />
        </div>
      )}

      {w.triggers.length > 0 && !missing && (
        <div>
          <p className="mb-1.5 text-xs font-medium text-muted-foreground">Why this risk level</p>
          <ul className="list-disc space-y-1 pl-5">
            {w.triggers.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        </div>
      )}

      <div>
        <p className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
          <Gauge className="size-3.5" /> Load-dependent rules
        </p>
        {w.appliedRules.length > 0 ? (
          <ul className="list-disc space-y-1 pl-5">
            {w.appliedRules.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        ) : (
          <p className="text-muted-foreground">
            {missing ? "Not evaluated without weather data." : "Standard thresholds; no load adjustments applied."}
          </p>
        )}
      </div>
    </div>
  );
}
